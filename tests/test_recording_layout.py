from pathlib import Path
import csv
import yaml
from praatio import textgrid
from praatio.data_classes.interval_tier import IntervalTier
from praatio.utilities.constants import Interval
from typer.testing import CliRunner
from skalspeech.cli import app
from skalspeech.commands import corpus_pipelines
from skalspeech.commands.corpus_architecture import template_snapshot
from skalspeech.commands.recording_layout import architecture_files, recordings_for

def _speaker(root):
    speaker = root / "CMF21"
    for rid, kind in (("rainbow", "speech"), ("silent", "reference")):
        folder = speaker / "recordings" / rid
        folder.mkdir(parents=True)
        (folder / "speech.wav").write_bytes(b"wav")
        (folder / "pos.txt").write_text("Ch1_X\n1\n2\n")
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


def test_architecture_honors_recording_sensor_file_override(tmp_path):
    speaker = _speaker(tmp_path)
    manifest = yaml.safe_load((speaker / "corpus.yaml").read_text())
    manifest["architecture"] = template_snapshot({})
    (speaker / "corpus.yaml").write_text(yaml.safe_dump(manifest))
    recording_yaml = speaker / "recordings" / "rainbow" / "recording.yaml"
    recording_metadata = yaml.safe_load(recording_yaml.read_text())
    recording_metadata["files"] = {"data": "pos.txt"}
    recording_yaml.write_text(yaml.safe_dump(recording_metadata))

    recording, folder, metadata = recordings_for(speaker, "rainbow")[0]
    paths = architecture_files(speaker, recording, metadata)

    assert paths["sensors"] == folder / "pos.txt"


def test_whisper_uses_recording_annotation_dir(tmp_path, monkeypatch):
    speaker = _speaker(tmp_path)
    manifest_path = speaker / "corpus.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    manifest["architecture"] = template_snapshot({})
    manifest["architecture"]["files"]["transcription"] = "annotations/custom_transcript.TextGrid"
    manifest["architecture"]["files"]["alignment"] = "annotations/custom_alignment.TextGrid"
    manifest_path.write_text(yaml.safe_dump(manifest))
    calls = []

    def fake(wav, out, settings):
        calls.append((wav, out))
        generated = out / "speech.TextGrid"
        generated.write_text("transcript")
        return generated

    monkeypatch.setattr(corpus_pipelines, "transcribe_audio", fake)
    config = tmp_path / "config.yaml"
    config.write_text("whisperx: {}\n")
    result = CliRunner().invoke(app, ["pipeline", "whisper", str(speaker), "-c", str(config)])
    assert result.exit_code == 0, result.output
    assert calls == [(speaker / "recordings/rainbow/speech.wav", speaker / "recordings/rainbow/annotations")]
    assert (speaker / "recordings/rainbow/annotations/custom_transcript.TextGrid").is_file()
    assert not (speaker / "recordings/rainbow/annotations/speech.TextGrid").exists()


def test_mfa_and_process_csv_use_architecture_annotation_filenames(tmp_path, monkeypatch):
    speaker = _speaker(tmp_path)
    manifest_path = speaker / "corpus.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    manifest["architecture"] = template_snapshot({})
    manifest["architecture"]["files"]["transcription"] = "annotations/custom_transcript.TextGrid"
    manifest["architecture"]["files"]["alignment"] = "annotations/custom_alignment.TextGrid"
    manifest_path.write_text(yaml.safe_dump(manifest))

    transcript = speaker / "recordings/rainbow/annotations/custom_transcript.TextGrid"
    transcript.parent.mkdir(parents=True)
    grid = textgrid.Textgrid()
    grid.addTier(IntervalTier("words", [Interval(0, 1, "rainbow")], 0, 1))
    grid.save(str(transcript), format="long_textgrid", includeBlankSpaces=True)

    def fake_mfa(command, arguments):
        staging = Path(arguments[0])
        output = Path(arguments[3])
        output.mkdir(parents=True, exist_ok=True)
        (output / "speech.TextGrid").write_bytes((staging / "speech.TextGrid").read_bytes())
        return 0

    monkeypatch.setattr(corpus_pipelines, "run_mfa_process", fake_mfa)
    config = tmp_path / "mfa.yaml"
    config.write_text("mfa:\n  dictionary: dict\n  acoustic_model: model\n")
    result = CliRunner().invoke(
        app, ["pipeline", "mfa", str(speaker), "-c", str(config)]
    )
    assert result.exit_code == 0, result.output
    alignment = speaker / "recordings/rainbow/annotations/custom_alignment.TextGrid"
    assert alignment.is_file()
    assert not (speaker / "recordings/rainbow/annotations/speech.TextGrid").exists()

    csv_config = tmp_path / "process.yaml"
    csv_config.write_text("corpus:\n  frequency: 2\ntextgrid:\n  tiers: [words]\n")
    result = CliRunner().invoke(
        app, ["pipeline", "process-csv", str(speaker), "-c", str(csv_config)]
    )
    assert result.exit_code == 0, result.output
    assert (speaker / "recordings/rainbow/processed.csv").is_file()

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
    assert rows[0] == ["tongue_x", "time_s", "word"]
    assert len(rows) == 3
    assert not (speaker / "recordings/silent/processed").exists()


def test_sensor_only_exports_reference_with_inherited_column_names(tmp_path):
    speaker = _speaker(tmp_path)
    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump({"textgrid": {"tiers": ["words"], "instances": False}}))
    result = CliRunner().invoke(app, ["pipeline", "process-csv", str(speaker), "-c", str(config), "--recording", "silent", "--sensor-only"])
    assert result.exit_code == 0, result.output
    with (speaker / "recordings/silent/processed/merged.csv").open(newline="") as f:
        rows = list(csv.reader(f))
    assert rows == [["tongue_x", "time_s"], ["1", "0.0"], ["2", "0.5"]]


def test_sensor_only_all_includes_reference_and_speech(tmp_path):
    speaker = _speaker(tmp_path)
    config = tmp_path / "config.yaml"
    config.write_text("corpus:\\n  frequency: 2\\n".replace("\\\\n", "\\n"))
    result = CliRunner().invoke(app, ["pipeline", "process-csv", str(speaker), "-c", str(config), "--sensor-only"])
    assert result.exit_code == 0, result.output
    assert (speaker / "recordings/silent/processed/merged.csv").is_file()
    assert (speaker / "recordings/rainbow/processed/merged.csv").is_file()


def test_process_csv_custom_recording_paths(tmp_path):
    speaker = _speaker(tmp_path)
    folder = speaker / "recordings" / "silent"
    (folder / "custom_pos.txt").write_text("Ch1_X\n3\n4\n")
    (folder / "recording.yaml").write_text(yaml.safe_dump({
        "id": "silent", "type": "reference",
        "files": {"data": "custom_pos.txt"},
        "process_csv": {"output": "exports/reference.csv"},
    }))
    config = tmp_path / "config.yaml"
    config.write_text("process_csv:\n  output: processed/shared.csv\n")
    result = CliRunner().invoke(app, ["pipeline", "process-csv", str(speaker),
        "-c", str(config), "--recording", "silent", "--sensor-only"])
    assert result.exit_code == 0, result.output
    with (folder / "exports/reference.csv").open(newline="") as f:
        assert list(csv.reader(f)) == [["tongue_x", "time_s"], ["3", "0.0"], ["4", "0.5"]]
