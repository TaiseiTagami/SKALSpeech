"""Immutable per-corpus layout snapshots and safe path resolution."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Optional
import json

import typer

from ..config import DEFAULT_CONFIG_DIR, get_section, load_config

_REQUIRED = ("audio", "sensors", "transcription", "alignment", "processed")
_DEFAULT_TEMPLATE = DEFAULT_CONFIG_DIR / "corpus_architecture.yaml"


def _safe_relative(value: str, field: str, **variables) -> Path:
    if not isinstance(value, str) or not value:
        raise typer.BadParameter(f"Architecture {field} must be a nonempty relative path")
    try:
        expanded = value.format(**variables)
    except (KeyError, ValueError) as exc:
        raise typer.BadParameter(f"Invalid architecture placeholder in {field}: {exc}")
    path = Path(expanded)
    if path.is_absolute() or any(part in (".", "..") for part in path.parts) or "\\" in expanded or ":" in expanded:
        raise typer.BadParameter(f"Unsafe architecture path for {field}: {value}")
    return path


def validate_architecture(architecture: dict) -> dict:
    if not isinstance(architecture, dict):
        raise typer.BadParameter("Architecture must be a YAML mapping")
    corpus = get_section(architecture, "corpus")
    recordings = get_section(architecture, "recordings")
    files = get_section(architecture, "files")
    for key in ("directory", "metadata"):
        if key not in corpus or key not in recordings:
            raise typer.BadParameter(f"Architecture missing corpus/recordings.{key}")
    for key in _REQUIRED:
        if key not in files:
            raise typer.BadParameter(f"Architecture missing files.{key}")
    for field, value in (("corpus.directory", corpus["directory"]), ("corpus.metadata", corpus["metadata"]),
                         ("recordings.directory", recordings["directory"]), ("recordings.metadata", recordings["metadata"])):
        _safe_relative(value, field, corpus_id="CMF21", recording_id="rainbow")
    for key in _REQUIRED:
        _safe_relative(files[key], f"files.{key}", corpus_id="CMF21", recording_id="rainbow")
    if not isinstance(architecture.get("version"), int):
        raise typer.BadParameter("Architecture version must be an integer")
    return architecture


def template_snapshot(config: dict, config_file: Optional[Path] = None) -> dict:
    template = config.get("architecture_template") or str(_DEFAULT_TEMPLATE)
    path = Path(template)
    if not path.is_absolute():
        base = config_file.parent if config_file else DEFAULT_CONFIG_DIR
        path = base / path
    raw = load_config(path)
    architecture = deepcopy(validate_architecture(get_section(raw, "architecture")))
    architecture["template"] = str(path.resolve())
    architecture["checksum"] = sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()
    return architecture


def saved_architecture(speaker: Path) -> Optional[dict]:
    manifest = speaker / "corpus.yaml"
    if not manifest.is_file():
        return None
    architecture = load_config(manifest).get("architecture")
    return validate_architecture(architecture) if architecture is not None else None


def recording_path(speaker: Path, recording_id: str, architecture: dict) -> Path:
    return speaker / _safe_relative(architecture["recordings"]["directory"], "recordings.directory",
                                   corpus_id=speaker.name, recording_id=recording_id)


def file_paths(speaker: Path, recording_id: str, architecture: dict, overrides: Optional[dict] = None) -> dict:
    folder = recording_path(speaker, recording_id, architecture)
    files = {**architecture["files"], **get_section(overrides or {}, "files")}
    return {key: folder / _safe_relative(files[key], f"files.{key}", corpus_id=speaker.name,
                                          recording_id=recording_id) for key in _REQUIRED}
