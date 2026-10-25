from pathlib import Path
from typing import Any, Dict, List

import typer

from ..config import get_section, load_config
from .mfa import run_mfa


def _option_arguments(options: Dict[str, Any]) -> List[str]:
    """Turn the `mfa.options` mapping into MFA command-line flags."""
    arguments: List[str] = []
    for name, value in options.items():
        flag = f"--{name}"
        if value is None or value is False:
            continue
        if value is True:
            arguments.append(flag)
        elif isinstance(value, list):
            for item in value:
                arguments.extend([flag, str(item)])
        else:
            arguments.extend([flag, str(value)])
    return arguments


def align_config_command(
    corpus_directory: Path,
    output_directory: Path,
    config: Path = typer.Option(
        ..., "--config", "-c", help="YAML config with an `mfa` section."
    ),
) -> None:
    """Run `mfa align` with settings from a YAML config.

    Only the corpus and output folders are given on the command line.
    """
    mfa = get_section(load_config(config), "mfa")
    for key in ("dictionary", "acoustic_model"):
        if not mfa.get(key):
            raise typer.BadParameter(f"Config section 'mfa' needs '{key}'.")
    options = mfa.get("options") or {}
    if not isinstance(options, dict):
        raise typer.BadParameter("Config 'mfa.options' must be a mapping.")

    run_mfa(
        "align",
        [
            str(corpus_directory),
            str(mfa["dictionary"]),
            str(mfa["acoustic_model"]),
            str(output_directory),
            *_option_arguments(options),
        ],
    )
