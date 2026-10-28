"""Versioned speaker/recording layout with legacy compatibility."""
from pathlib import Path
from typing import Optional

import typer

from ..config import load_config, get_section
from .corpus_architecture import saved_architecture, recording_path, file_paths


def recordings_for(speaker: Path, recording: Optional[str] = None, include_reference: bool = False):
    """Return (id, directory, metadata) for selected recordings."""
    manifest = speaker / "corpus.yaml"
    metadata = load_config(manifest) if manifest.is_file() else {}
    entries = metadata.get("recordings", [])
    if entries and not isinstance(entries, list):
        raise typer.BadParameter(f"{manifest}: recordings must be a list")
    if (speaker / "recordings").is_dir() or entries:
        if not entries:
            entries = [{"id": p.name, "type": "speech"} for p in sorted((speaker / "recordings").iterdir()) if p.is_dir()]
        result = []
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
                raise typer.BadParameter(f"{manifest}: invalid recording entry")
            rid = entry["id"]
            if not rid or rid in (".", "..") or Path(rid).name != rid or "/" in rid or "\\" in rid:
                raise typer.BadParameter(f"Unsafe recording ID: {rid}")
            if recording and rid != recording:
                continue
            if not include_reference and entry.get("type", "speech") != "speech":
                continue
            architecture = saved_architecture(speaker)
            folder = recording_path(speaker, rid, architecture) if architecture else speaker / "recordings" / rid
            local = load_config(folder / "recording.yaml") if (folder / "recording.yaml").is_file() else {}
            result.append((rid, folder, {**entry, **local}))
        if recording and not result:
            raise typer.BadParameter(f"Recording {recording} not found or excluded in {speaker}")
        return result
    if recording and recording not in ("legacy", "rainbow"):
        raise typer.BadParameter(f"Legacy speaker {speaker} has no recording {recording}")
    return [("legacy", speaker, {"type": "speech", "legacy": True})]


def recording_paths(folder: Path, meta: dict, stage: str):
    """Resolve standard stage paths, keeping legacy directories usable."""
    if meta.get("legacy"):
        return folder / "input", folder / "output", folder / "processed"
    return folder, folder / "annotations", folder / "processed"


def recording_config(shared: dict, speaker: Path, folder: Path, metadata: dict, config_file: Path):
    """Merge global, speaker, template, and recording overrides."""
    from ..config import get_columns
    config = dict(shared)
    speaker_config = load_config(speaker / "corpus.yaml") if (speaker / "corpus.yaml").is_file() else {}
    recording_settings = load_config(folder / "recording.yaml") if (folder / "recording.yaml").is_file() else {}
    for part in ("corpus", "textgrid", "data"):
        config[part] = {**get_section(shared, part), **get_section(speaker_config, part), **get_section(recording_settings, part)}
    template = recording_settings.get("column_template", speaker_config.get("column_template", get_section(shared, "process_csv").get("column_template")))
    columns = get_columns(shared)
    if template:
        origin = folder if "column_template" in recording_settings else speaker if "column_template" in speaker_config else config_file.parent
        template_path = Path(template)
        if not template_path.is_absolute():
            template_path = origin / template_path
        columns.update(get_columns(load_config(template_path)))
    columns.update(get_columns(speaker_config))
    columns.update(get_columns(recording_settings))
    if columns:
        config["columns"] = columns
    return config


def recording_file_names(folder: Path, metadata: dict, settings: dict):
    """Use recording metadata first, then command defaults."""
    files = get_section(metadata, "files")
    wav = files.get("wav") or settings["wav_name"]
    pos = files.get("data") or settings.get("pos_name", "sensors.txt")
    for name in (wav, pos):
        if not isinstance(name, str) or not name or Path(name).name != name:
            raise typer.BadParameter(f"Invalid recording filename: {name}")
    return wav, pos


def architecture_files(speaker: Path, recording_id: str, metadata: dict):
    """Resolve files from saved corpus architecture and recording overrides."""
    architecture = saved_architecture(speaker)
    if architecture is None:
        return None
    return file_paths(speaker, recording_id, architecture, metadata.get("architecture") if isinstance(metadata.get("architecture"), dict) else None)
