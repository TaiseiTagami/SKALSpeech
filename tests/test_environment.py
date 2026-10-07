import json
import subprocess

from typer.testing import CliRunner

from skalspeech.cli import app


runner = CliRunner()


def test_set_environment_writes_configuration(monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(
        "skalspeech.commands.environment._config_path", lambda: config_path
    )

    result = runner.invoke(app, ["environment", "set", "aligner"])

    assert result.exit_code == 0, result.stdout
    assert json.loads(config_path.read_text(encoding="utf-8")) == {
        "environment": "aligner"
    }


def test_open_environment_starts_powershell(monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text('{"environment": "aligner"}', encoding="utf-8")
    monkeypatch.setattr(
        "skalspeech.commands.environment._config_path", lambda: config_path
    )
    monkeypatch.setattr(
        "skalspeech.commands.environment.shutil.which",
        lambda name: "C:\\Miniforge3\\conda.bat" if name == "conda" else None,
    )
    calls = []
    monkeypatch.setattr(
        "skalspeech.commands.environment.subprocess.Popen",
        lambda command, creationflags: calls.append((command, creationflags)),
    )

    result = runner.invoke(app, ["environment", "open"])

    assert result.exit_code == 0, result.stdout
    assert calls[0][0][0:3] == ["powershell.exe", "-NoExit", "-Command"]
    assert "conda activate 'aligner'" in calls[0][0][-1]
    assert calls[0][1] == getattr(subprocess, "CREATE_NEW_CONSOLE", 0)