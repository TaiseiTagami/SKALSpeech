from pathlib import Path
import csv
import yaml
from praatio import textgrid
from praatio.data_classes.interval_tier import IntervalTier
from praatio.utilities.constants import Interval
from typer.testing import CliRunner
from skalspeech.cli import app
from skalspeech.commands import corpus_pipelines
from skalspeech.commands.recording_layout import recordings_for

def _speaker(root):
    speaker = root / "CMF21"
    for rid, kind in (("rainbow", "speech"), ("silent", "reference")):
        folder = speaker / "recordings" / rid
        folder.mkdir(parents=True)
        (folder / "speech.wav").write_bytes(b"wav")
        (folder / "sensors.txt").write_text("Ch1_X\n1\n2\n")
        (folder / "recording.yaml").write_text(yaml.safe_dump({"id": rid, "type": kind}))
    (speaker / "corpus.yaml").write_text(yaml.safe_dump({
        "schema_version": 2, "corpus": {"frequency": 2},
        "recordings": [{"id": "rainbow", "type": "speech"}, {"id": "silent", "type": "reference"}],
        "columns": {"time": "time_s", "words": "word", "Ch1_X": "tongue_x"}}))
    return speaker

def test_recording_selection_skips_reference(tmp_path):
    speaker = _speaker(tmp_path)
    assert [rid for rid, _, _ in recordings_for(speaker)] == ["rainbow"]
    assert len(recordings_for(speaker, include_reference=True)) == 2

def test_whisper_uses_recording_annotation_dir(tmp_path, monkeypatch):
    speaker = _speaker(tmp_path)
    calls = []
    def fake(wav, out, settings):
        calls.append((wav, out))
        return out / "speech.TextGrid"
    monkeypatch.setattr(corpus_pipelines, "transcribe_audio", fake)
    config = tmp_path / "config.yaml"
    config.write_text("whisperx: {}\n")
    result = CliRunner().invoke(app, ["pipeline", "whisper", str(speaker), "-c", str(config)])
    assert result.exit_code == 0, result.output
    assert calls == [(speaker / "recordings/rainbow/speech.wav", speaker / "recordings/rainbow/annotations")]

def test_process_csv_recording_layout(tmp_path):
    speaker = _speaker(tmp_path)
    folder = speaker / "recordings" / "rainbow"
    (folder / "annotations/mfa").mkdir(parents=True)
    grid = textgrid.Textgrid()
    grid.addTier(IntervalTier("words", [Interval(0, 1, "rainbow")], 0, 1))
    grid.save(str(folder / "annotations/mfa/speech.TextGrid"), format="long_textgrid", includeBlankSpaces=True)
    config = tmp_path / "config.yaml"
    config.write_text("textgrid:\n  tiers: [words]\n  instances: false\n")
    result = CliRunner().invoke(app, ["pipeline", "process-csv", str(speaker), "-c", str(config)])
    assert result.exit_code == 0, result.output
    with (folder / "processed/merged.csv").open(newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["time_s", "word", "tongue_x"]
    assert len(rows) == 3
    assert not (speaker / "recordings/silent/processed").exists()
