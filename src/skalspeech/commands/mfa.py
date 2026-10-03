import shutil
import subprocess

import typer

from .environment import _configured_environment


def run_mfa(command_name: str, arguments: list[str]) -> None:
    """Run an MFA command and return its exit code to the caller."""
    mfa_command = ["mfa", command_name, *arguments]
    environment = _configured_environment()
    conda = shutil.which("conda")
    if environment and conda:
        mfa_command = [
            conda,
            "run",
            "--no-capture-output",
            "--name",
            environment,
            *mfa_command,
        ]

    try:
        result = subprocess.run(mfa_command, check=False)
    except FileNotFoundError:
        raise typer.BadParameter(
            "MFA was not found. Install MFA in the configured Conda environment "
            "or ensure the 'mfa' command is on PATH."
        )

    raise typer.Exit(result.returncode)


def mfa_command(ctx: typer.Context, command_name: str) -> None:
    """Pass any MFA command and its arguments through to MFA."""
    run_mfa(command_name, list(ctx.args))