"""Loading and reading the shared SKALSpeech YAML config.

The config is split into top-level sections so it can grow without commands
confusing each other's settings. Sections currently used:

    corpus:    general info about the sample/instrument (e.g. frequency)
    files:     input/output paths (used by `pipeline from-config`)
    data:      how to read the sensor data (e.g. delimiter)
    textgrid:  how to sample the TextGrid (tiers, instances)
    columns:   original column name -> new name (null keeps the name)
    mfa:       `dictionary`, `acoustic_model`, and `options` (flag -> value;
               true = bare flag) used by `align-config`

Unknown sections are ignored.
"""

from pathlib import Path
from typing import Any, Dict, Optional

import typer
import yaml


def load_config(path: Path) -> Dict[str, Any]:
    try:
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise typer.BadParameter(f"Config file does not exist: {path}")
    except (OSError, yaml.YAMLError) as error:
        raise typer.BadParameter(f"Could not read config file: {error}")
    if config is None:
        return {}
    if not isinstance(config, dict):
        raise typer.BadParameter("Config file must be a YAML mapping of sections.")
    return config


def get_section(config: Dict[str, Any], name: str) -> Dict[str, Any]:
    section = config.get(name)
    if section is None:
        return {}
    if not isinstance(section, dict):
        raise typer.BadParameter(f"Config section '{name}' must be a mapping.")
    return section


def get_columns(config: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """Return the `columns` section: original name -> new name (or None)."""
    section = get_section(config, "columns")
    columns: Dict[str, Optional[str]] = {}
    for name, new_name in section.items():
        if new_name is not None and not isinstance(new_name, str):
            raise typer.BadParameter(
                f"New name for column '{name}' must be text or empty."
            )
        columns[str(name)] = new_name
    return columns


# Only this directory supplies built-in command defaults. Never silently
# recreate missing values in Python when a default YAML was edited/deleted.
DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "default"


def _merge_config(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_config(result[key], value)
        else:
            result[key] = value
    return result


def _required_keys(config: Dict[str, Any], schema: Dict[str, Any], prefix: str = "") -> None:
    for key, value in schema.items():
        label = f"{prefix}.{key}" if prefix else key
        if key not in config:
            raise typer.BadParameter(f"Missing required default config key: {label}")
        if isinstance(value, dict):
            if not isinstance(config[key], dict):
                raise typer.BadParameter(f"Default config key must be a mapping: {label}")
            _required_keys(config[key], value, label)


# Schemas are intentionally explicit: a deleted required default is an error,
# even when a user-provided override happens to define the same key.
DEFAULT_REQUIRED = {
    "collect": {"collect": {"root": None, "audio_subdir": None, "identifier": None,
        "output": None, "group": None, "frequency": None, "folders": None,
        "wav_name": None, "pos_name": None, "recording_id": None, "recording_type": None}},
    "mfa": {"mfa": {"dictionary": None, "acoustic_model": None, "options": {},
        "root": None, "corpora": None, "input_dir": None, "output_dir": None,
        "wav_name": None, "transcript_tiers": None}},
    "whisper": {"whisperx": {"model": None, "align_model": None, "language": None,
        "device": None, "compute_type": None, "keep_json": None,
        "executable": None, "options": {}, "root": None, "corpora": None,
        "input_dir": None, "wav_name": None}},
    "process_csv": {"corpus": {"frequency": None}, "textgrid": {"tiers": None, "instances": None},
        "data": {"delimiter": None}, "columns": {}, "process_csv": {
        "root": None, "corpora": None, "input_dir": None, "mfa_output_dir": None,
        "textgrid_name": None, "data_name": None, "output": None,
        "textgrid": None, "data": None, "column_template": None}},
    "pipeline": {"corpus": {"frequency": None}, "textgrid": {"tiers": None, "instances": None},
        "data": {"delimiter": None}, "columns": {}, "files": {
        "textgrid": None, "data": None, "output": None}},
    "csv": {"columns": {}},
}


def load_command_config(command: str, override: Optional[Path] = None) -> Dict[str, Any]:
    if command not in DEFAULT_REQUIRED:
        raise typer.BadParameter(f"Unknown default configuration: {command}")
    default_path = DEFAULT_CONFIG_DIR / f"{command}.yaml"
    defaults = load_config(default_path)
    _required_keys(defaults, DEFAULT_REQUIRED[command])
    if override is None:
        return defaults
    return _merge_config(defaults, load_config(override))
