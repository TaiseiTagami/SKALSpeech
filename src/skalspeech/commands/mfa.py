import subprocess

import typer


def run_mfa(command_name: str, arguments: list[str]) -> None:
    """Run an MFA command and return its exit code to the caller."""
    try:
        result = subprocess.run(
            ["mfa", command_name, *arguments],
            check=False,
        )
    except FileNotFoundError:
        raise typer.BadParameter(
            "MFA was not found. Install MFA and ensure the 'mfa' command is on PATH."
        )

    raise typer.Exit(result.returncode)


def mfa_command(ctx: typer.Context, command_name: str) -> None:
    """Pass any MFA command and its arguments through to MFA."""
    run_mfa(command_name, list(ctx.args))