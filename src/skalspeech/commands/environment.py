import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import typer


environment_app = typer.Typer(help="Configure and open a Conda environment.")


def _config_path() -> Path:
    app_data = os.environ.get("APPDATA")
    config_directory = (
        Path(app_data) / "skalspeech" if app_data else Path.home() / ".skalspeech"
    )
    return config_directory / "config.json"


def _configured_environment() -> Optional[str]:
    path = _config_path()
    if not path.exists():
        return None
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    environment = settings.get("environment")
    return environment if isinstance(environment, str) and environment else None


@environment_app.command("set")
def set_environment(environment: str) -> None:
    """Set the Conda environment used by `environment open`."""
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"environment": environment}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Saved environment: {environment}")


@environment_app.command("open")
def open_environment() -> None:
    """Open a new PowerShell window with the configured Conda environment active."""
    environment = _configured_environment()
    if environment is None:
        raise typer.BadParameter(
            "No environment is configured. Run: "
            "skalspeech environment set <name>"
        )

    conda = shutil.which("conda")
    if conda is None:
        raise typer.BadParameter(
            "Conda was not found on PATH. Install Miniconda or Miniforge first."
        )

    command = (
        f"(& '{conda}' 'shell.powershell' 'hook') | Out-String | Invoke-Expression; "
        f"conda activate '{environment}'"
    )
    subprocess.Popen(
        [
            "powershell.exe",
            "-NoExit",
            "-Command",
            command,
        ],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )
    print(f"Opened PowerShell with Conda environment: {environment}")