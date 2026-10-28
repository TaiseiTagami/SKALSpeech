"""Collect one wav + position file per subject folder into the project layout.

For each subject ID the output is:

    <output>/<ID>/info.txt
    <output>/<ID>/input/<wav_name>
    <output>/<ID>/input/<pos_name>

Settings live in the `collect` config section; folders, identifier and output
can also be given on the command line.
"""

import re
import shutil
from pathlib import Path
from typing import List, Optional

import typer
import yaml

from ..config import get_section, load_config, load_command_config


def _find_one(parent: Path, matches, description: str) -> Path:
    found = [entry for entry in parent.iterdir() if entry.is_dir() and matches(entry.name)]
    if not found:
        raise ValueError(f"No {description} found in {parent}")
    if len(found) > 1:
        names = ", ".join(entry.name for entry in found)
        raise ValueError(f"Multiple {description} found in {parent}: {names}")
    return found[0]


def _subject_folder(root: Path, subject: str) -> Path:
    pattern = re.compile(rf"^{re.escape(subject)}(?![A-Za-z0-9])", re.IGNORECASE)
    return _find_one(root, pattern.match, f"folder starting with '{subject}'")


def _audio_directory(subject_folder: Path, audio_subdir: str) -> Path:
    """Walk the audio path; a part like 'EMA' may match 'CMF17_07242024_EMA'."""
    current = subject_folder
    for part in Path(audio_subdir).parts:
        exact = current / part
        if exact.is_dir():
            current = exact
        else:
            current = _find_one(
                current,
                lambda name, part=part: name.lower().endswith(part.lower()),
                f"folder ending with '{part}'",
            )
    return current


def _wav_file(audio_directory: Path, identifier: str) -> Path:
    found = [
        entry
        for entry in audio_directory.iterdir()
        if entry.suffix.lower() == ".wav" and identifier.lower() in entry.stem.lower()
    ]
    if not found:
        raise ValueError(f"No wav containing '{identifier}' in {audio_directory}")
    if len(found) > 1:
        names = ", ".join(entry.name for entry in found)
        raise ValueError(f"Multiple wavs containing '{identifier}': {names}")
    return found[0]


def collect_subject(
    subject: str,
    root: Path,
    audio_subdir: str,
    identifier: str,
    output: Path,
    settings: dict,
    yaml_only: bool = False,
    column_template: Optional[str] = None,
    recording_id: str = "rainbow",
    recording_type: str = "speech",
) -> Path:
    subject_output = output / subject
    if yaml_only and not subject_output.is_dir():
        raise ValueError(f"Existing collected corpus not found: {subject_output}")
    try:
        wav = _wav_file(_audio_directory(_subject_folder(root, subject), audio_subdir), identifier)
    except (ValueError, OSError):
        if not yaml_only:
            raise
        info = subject_output / "info.txt"
        if not info.is_file():
            raise ValueError(f"Original source unavailable and {info} is missing")
        match = re.search(r'"([^"]+\.wav)"', info.read_text(encoding="utf-8"), re.I)
        if not match:
            raise ValueError(f"No original WAV path found in {info}")
        wav = Path(match.group(1))
    pos = wav.with_suffix(".txt")
    if not yaml_only and not pos.is_file():
        raise ValueError(f"Position file not found: {pos}")

    recording_dir = subject_output / "recordings" / recording_id
    recording_yaml = recording_dir / "recording.yaml"
    existing_recording = load_config(recording_yaml) if recording_yaml.is_file() else {}
    existing_source = get_section(existing_recording, "source")
    input_directory = recording_dir
    if yaml_only:
        if existing_source.get("wav") and Path(existing_source["wav"]) != wav:
            raise ValueError(f"Existing {recording_id} source differs: {existing_source['wav']} != {wav}. Recollect explicitly.")
        for name in ("speech.wav", "sensors.txt"):
            if not (input_directory / name).is_file():
                raise ValueError(f"Existing collected file missing: {input_directory / name}")
    else:
        if existing_source.get("wav") and Path(existing_source["wav"]) != wav:
            raise ValueError(f"Recording {recording_id} already belongs to {existing_source['wav']}; refusing to overwrite.")
        input_directory.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(wav, input_directory / "speech.wav")
        shutil.copyfile(pos, input_directory / "sensors.txt")
    metadata = {
        "schema_version": 2,
        "subject": subject,
        "group": settings["group"],
        "corpus": {"frequency": settings["frequency"]},
        "source": {
            "wav": str(wav.resolve()),
            "position": str(pos.resolve()),
            "subject_directory": str(wav.parent.resolve()),
            "identifier": identifier,
        },
        "recordings": [{"id": recording_id, "type": recording_type}],
        "columns": {},  # Fill in the subject-specific sensor/channel names.
    }
    if column_template is not None:
        metadata["column_template"] = column_template
    metadata_path = subject_output / "corpus.yaml"
    if metadata_path.is_file():
        existing = load_config(metadata_path)
        # Preserve curated subject-specific values (particularly columns).
        for key in ("corpus", "source", "files", "columns"):
            if key in existing:
                metadata[key] = {**metadata.get(key, {}), **get_section(existing, key)}
        for key, value in existing.items():
            if key not in metadata:
                metadata[key] = value
        for key, value in existing.items():
            if key not in metadata:
                metadata[key] = value
        if isinstance(existing.get("recordings"), list):
            metadata["recordings"] = existing["recordings"]
    if metadata_path.is_file():
        current = {item["id"]: item for item in metadata.get("recordings", [])}
        current[recording_id] = {"id": recording_id, "type": recording_type}
        metadata["recordings"] = list(current.values())
    metadata_path.write_text(
        yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    recording_metadata = {"id": recording_id, "type": recording_type,
        "task": recording_id, "source": metadata["source"], "columns": {}}
    if existing_recording:
        recording_metadata = {**existing_recording, **recording_metadata}
        recording_metadata["columns"] = get_section(existing_recording, "columns")
    recording_yaml.write_text(yaml.safe_dump(recording_metadata, sort_keys=False), encoding="utf-8")
    if not yaml_only:
        (subject_output / "info.txt").write_text(
        f'{settings["group"]}, {subject}: "{wav}"\nFrequency: {settings["frequency"]}\n',
        encoding="utf-8",
    )
    return subject_output


def collect_command(
    folders: Optional[List[str]] = typer.Argument(
        None, help="Subject folder prefixes, e.g. CMF17 CMF18."
    ),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Optional YAML overrides; defaults in config/default/collect.yaml."),
    identifier: Optional[str] = typer.Option(
        None, "--identifier", "-i", help="Keyword in the wav name, e.g. rainbow."
    ),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
    yaml_only: bool = typer.Option(False, "--yaml-only", help="Only write corpus.yaml for existing collected subjects."),
    column_template: Optional[Path] = typer.Option(None, "--column-template", help="Shared YAML column template to reference from each corpus.yaml."),
    recording_id: Optional[str] = typer.Option(None, "--recording-id", help="Recording ID (default: collect.identifier)."),
    recording_type: Optional[str] = typer.Option(None, "--recording-type", help="speech or reference."),
) -> None:
    """Copy each subject's keyword wav and pos file into the project layout.

    Subjects with no, or more than one, matching folder or wav are skipped
    with an error; the command exits non-zero if any were skipped.
    """
    settings = get_section(load_command_config("collect", config), "collect")
    subjects = folders or settings.get("folders") or []
    identifier = identifier or settings.get("identifier")
    output = output or (Path(settings["output"]) if settings.get("output") else None)
    root = settings.get("root")
    missing = [
        name
        for name, value in (
            ("folders", subjects),
            ("identifier", identifier),
            ("output", output),
            ("root", root),
        )
        if not value
    ]
    if missing:
        raise typer.BadParameter(f"Missing: {', '.join(missing)} (CLI or config).")

    recording_type = recording_type or settings["recording_type"]
    if recording_type not in ("speech", "reference"):
        raise typer.BadParameter("--recording-type must be speech or reference")
    rid = recording_id or settings["recording_id"] or identifier
    if not rid or Path(rid).name != rid or "/" in rid or "\\" in rid or rid in (".", ".."):
        raise typer.BadParameter("Invalid recording ID")
    template_ref = None
    if column_template is not None:
        template_path = column_template.resolve()
        if not template_path.is_file():
            raise typer.BadParameter(f"Column template not found: {template_path}")
        from ..config import get_columns
        get_columns(load_config(template_path))
        template_ref = str(template_path)
    failures = 0
    for subject in subjects:
        try:
            done = collect_subject(
                subject, Path(root), settings["audio_subdir"], identifier, output, settings, yaml_only=yaml_only, column_template=template_ref, recording_id=rid, recording_type=recording_type
            )
            typer.echo(f"{subject}: wrote {done}")
        except (ValueError, OSError) as error:
            failures += 1
            typer.echo(f"{subject}: SKIPPED - {error}", err=True)
    raise typer.Exit(1 if failures else 0)
