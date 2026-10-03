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