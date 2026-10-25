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
