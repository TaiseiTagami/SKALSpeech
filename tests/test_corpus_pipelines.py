from pathlib import Path

from praatio import textgrid
from typer.testing import CliRunner

from skalspeech.cli import app
from skalspeech.commands import corpus_pipelines

runner = CliRunner()


def _make_corpus(corpus: Path) -> None:
    input_directory = corpus / "input"
    input_directory.mkdir(parents=True)
    (input_directory / "speech.wav").write_bytes(b"wav")
    (input_directory / "pos.txt").write_text("pos")
    grid = textgrid.Textgrid()
    for name in ("words", "sentences"):
        grid.addTier(textgrid.IntervalTier(name, [(0, 1, "hi")], 0, 1))
    grid.save(str(input_directory / "speech.TextGrid"), "long_textgrid", True)


def _config(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_mfa_pipeline_runs_each_corpus_and_skips_failures(tmp_path, monkeypatch):
    for name in ("A", "B"):
        _make_corpus(tmp_path / name)
    calls = []

    def fake_run(command_name, arguments):
        staged = sorted(path.name for path in Path(arguments[0]).iterdir())
        calls.append((command_name, arguments, staged))
        return 3 if Path(arguments[3]).parent.name == "B" else 0

    monkeypatch.setattr(corpus_pipelines, "run_mfa_process", fake_run)
    config = _config(
        tmp_path,
        "mfa:\n  dictionary: d.dict\n  acoustic_model: m.zip\n  options: {clean: true}\n",
    )

    result = runner.invoke(
        app,
        [
            "pipeline", "mfa",
            str(tmp_path / "A"), str(tmp_path / "B"), str(tmp_path / "C"),
            "-c", str(config),
        ],
    )

    assert result.exit_code == 1
    assert [call[0] for call in calls] == ["align", "align"]
    assert calls[0][2] == ["speech.TextGrid", "speech.wav"]
    assert calls[0][1][1:] == [
        "d.dict",
        "m.zip",
        str(tmp_path / "A" / "output"),
        "--clean",
    ]


def test_mfa_pipeline_uses_config_corpora(tmp_path, monkeypatch):
    _make_corpus(tmp_path / "A")
    calls = []
    monkeypatch.setattr(
        corpus_pipelines, "run_mfa_process", lambda *args: calls.append(args) or 0
    )
    config = _config(
        tmp_path,
        f"mfa:\n  dictionary: d\n  acoustic_model: m\n  corpora: ['{tmp_path / 'A'}']\n",
    )

    result = runner.invoke(app, ["pipeline", "mfa", "-c", str(config)])

    assert result.exit_code == 0
    assert len(calls) == 1


def test_mfa_pipeline_resolves_names_under_root(tmp_path, monkeypatch):
    _make_corpus(tmp_path / "ctl" / "A")
    calls = []
    monkeypatch.setattr(
        corpus_pipelines, "run_mfa_process", lambda *args: calls.append(args) or 0
    )
    config = _config(
        tmp_path,
        f"mfa:\n  dictionary: d\n  acoustic_model: m\n  root: '{tmp_path / 'ctl'}'\n  corpora: [A]\n",
    )

    result = runner.invoke(app, ["pipeline", "mfa", "-c", str(config)])

    assert result.exit_code == 0
    assert calls[0][1][3] == str(tmp_path / "ctl" / "A" / "output")


def test_mfa_pipeline_stages_only_configured_tiers(tmp_path, monkeypatch):
    _make_corpus(tmp_path / "A")
    seen = []

    def fake_run(command_name, arguments):
        grid = textgrid.openTextgrid(str(Path(arguments[0]) / "speech.TextGrid"), True)
        seen.append(tuple(grid.tierNames))
        return 0

    monkeypatch.setattr(corpus_pipelines, "run_mfa_process", fake_run)
    config = _config(tmp_path, "mfa:\n  dictionary: d\n  acoustic_model: m\n")
    runner.invoke(app, ["pipeline", "mfa", str(tmp_path / "A"), "-c", str(config)])

    config = _config(
        tmp_path,
        "mfa:\n  dictionary: d\n  acoustic_model: m\n  transcript_tiers: [sentences]\n",
    )
    runner.invoke(app, ["pipeline", "mfa", str(tmp_path / "A"), "-c", str(config)])

    assert seen == [("words",), ("sentences",)]


def test_whisper_pipeline_transcribes_wav_next_to_textgrid(tmp_path, monkeypatch):
    (tmp_path / "A" / "input").mkdir(parents=True)
    wav = tmp_path / "A" / "input" / "speech.wav"
    wav.write_bytes(b"")
    calls = []

    def fake_transcribe(audio_path, output_directory, settings):
        calls.append((audio_path, output_directory))
        return output_directory / "speech.TextGrid"

    monkeypatch.setattr(corpus_pipelines, "transcribe_audio", fake_transcribe)
    config = _config(tmp_path, "whisperx: {}\n")

    result = runner.invoke(
        app,
        ["pipeline", "whisper", str(tmp_path / "A"), str(tmp_path / "B"), "-c", str(config)],
    )

    assert result.exit_code == 1
    assert calls == [(wav, wav.parent)]
