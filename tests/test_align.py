from pathlib import Path

from typer.testing import CliRunner

from skalspeech.cli import app


runner = CliRunner()


def test_align_passes_mfa_arguments_and_options(monkeypatch):
    calls = []

    def fake_run(command, check):
        calls.append((command, check))
        return type("Result", (), {"returncode": 0})()

    monkeypatch.setattr("skalspeech.commands.mfa.subprocess.run", fake_run)

    result = runner.invoke(
        app,
        [
            "align",
            "corpus",
            "dictionary.dict",
            "english.zip",
            "output",
            "--clean",
            "--single_speaker",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert calls == [
        (
            [
                "mfa",
                "align",
                str(Path("corpus")),
                str(Path("dictionary.dict")),
                str(Path("english.zip")),
                str(Path("output")),
                "--clean",
                "--single_speaker",
            ],
            False,
        )
    ]


def test_align_returns_mfa_exit_code(monkeypatch):
    def fake_run(command, check):
        return type("Result", (), {"returncode": 7})()

    monkeypatch.setattr("skalspeech.commands.mfa.subprocess.run", fake_run)

    result = runner.invoke(
        app,
        [
            "align",
            "corpus",
            "dictionary.dict",
            "english.zip",
            "output",
        ],
    )

    assert result.exit_code == 7