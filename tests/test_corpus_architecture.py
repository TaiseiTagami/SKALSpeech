from pathlib import Path
import yaml
import pytest

from skalspeech.commands.collect import collect_subject
from skalspeech.commands.corpus_architecture import (
    template_snapshot, saved_architecture, recording_path, file_paths,
)


def test_architecture_snapshot_and_second_recording(tmp_path):
    source = tmp_path / "source" / "CMF21_2026" / "EMA" / "pos"
    source.mkdir(parents=True)
    for name in ("rainbow", "silent"):
        (source / f"{name}.wav").write_bytes(name.encode())
        (source / f"{name}.txt").write_text("Ch1_X\n1\n")
    settings = {"group": "Control", "frequency": 250,
                "wav_name": "speech.wav", "pos_name": "pos.txt"}
    root = tmp_path / "out"
    collect_subject("CMF21", tmp_path / "source", "EMA/pos", "rainbow", root,
                    settings, recording_id="rainbow")
    speaker = root / "CMF21"
    original = saved_architecture(speaker)
    assert original["files"]["sensors"] == "data/sensors.txt"
    assert (speaker / "recordings/rainbow/data/sensors.txt").is_file()
    collect_subject("CMF21", tmp_path / "source", "EMA/pos", "silent", root,
                    settings, recording_id="silent_reference", recording_type="reference")
    assert saved_architecture(speaker) == original
    assert (speaker / "recordings/silent_reference/data/sensors.txt").is_file()
    metadata = yaml.safe_load((speaker / "recordings/silent_reference/recording.yaml").read_text())
    assert metadata["source"]["identifier"] == "silent"
    assert metadata["source"]["wav"].endswith("silent.wav")
    assert [x["id"] for x in yaml.safe_load((speaker / "corpus.yaml").read_text())["recordings"]] == [
        "rainbow", "silent_reference"]


def test_recording_override_paths(tmp_path):
    speaker = tmp_path / "AF18"
    architecture = template_snapshot({})
    target = file_paths(speaker, "rainbow", architecture,
                        {"files": {"sensors": "raw/ema.txt"}})
    assert target["sensors"] == speaker / "recordings/rainbow/raw/ema.txt"
    assert target["alignment"] == speaker / "recordings/rainbow/annotations/alignment.TextGrid"


def test_rejects_unsafe_architecture_paths():
    architecture = template_snapshot({})
    architecture["files"]["sensors"] = "../outside.txt"
    from skalspeech.commands.corpus_architecture import validate_architecture
    with pytest.raises(Exception, match="Unsafe architecture"):
        validate_architecture(architecture)
