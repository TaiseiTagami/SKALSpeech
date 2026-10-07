from typer.testing import CliRunner

from skalspeech.cli import app


runner = CliRunner()


def test_mfa_forwards_any_command_and_arguments(monkeypatch):
    calls = []

    def fake_run(command, check):
        calls.append((command, check))
        return type("Result", (), {"returncode": 0})()

    monkeypatch.setattr("skalspeech.commands.mfa.subprocess.run", fake_run)

    result = runner.invoke(
        app,
        ["mfa", "validate", "corpus", "dictionary.dict", "--verbose"],
    )

    assert result.exit_code == 0, result.stdout
    assert calls == [
        (["mfa", "validate", "corpus", "dictionary.dict", "--verbose"], False)
    ]


def test_mfa_runs_in_configured_conda_environment(monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text('{"environment": "aligner"}', encoding="utf-8")
    monkeypatch.setattr(
        "skalspeech.commands.environment._config_path", lambda: config_path
    )
    monkeypatch.setattr(
        "skalspeech.commands.mfa.shutil.which",
        lambda name: "C:\\Miniforge3\\conda.exe" if name == "conda" else None,
    )
    calls = []

    def fake_run(command, check):
        calls.append((command, check))
        return type("Result", (), {"returncode": 0})()

    monkeypatch.setattr("skalspeech.commands.mfa.subprocess.run", fake_run)

    result = runner.invoke(app, ["mfa", "version"])

    assert result.exit_code == 0, result.stdout
    assert calls == [
        (
            [
                "C:\\Miniforge3\\conda.exe",
                "run",
                "--no-capture-output",
                "--name",
                "aligner",
                "mfa",
                "version",
            ],
            False,
        )
    ]