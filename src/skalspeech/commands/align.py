from pathlib import Path

import typer

from .mfa import run_mfa


def align_command(
    ctx: typer.Context,
    corpus_directory: Path,
    dictionary_path: Path,
    acoustic_model_path: Path,
    output_directory: Path,
) -> None:
    """Alias for `mfa align` with named positional arguments."""
    run_mfa(
        "align",
        [
        str(corpus_directory),
        str(dictionary_path),
        str(acoustic_model_path),
        str(output_directory),
        *ctx.args,
        ],
    )