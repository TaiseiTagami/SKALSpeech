from pathlib import Path
import yaml
from skalspeech.commands.collect import collect_subject

def test_yaml_only_preserves_existing_files(tmp_path):
    source = tmp_path / "source" / "CMF23_2026" / "EMA" / "pos"
    source.mkdir(parents=True)
    (source / "rainbow.wav").write_bytes(b"original")
    (source / "rainbow.txt").write_text("Ch1_X\n1\n")
    settings = dict(wav_name="speech.wav", pos_name="pos.txt", group="Control", frequency=250)
    target = collect_subject("CMF23", tmp_path / "source", "EMA/pos", "rainbow", tmp_path / "out", settings)
    meta = yaml.safe_load((target / "corpus.yaml").read_text())
    meta["columns"] = {"Ch1_X": "jaw_x"}
    (target / "corpus.yaml").write_text(yaml.safe_dump(meta))
    (target / "recordings" / "rainbow" / "speech.wav").write_bytes(b"preserve")
    (target / "info.txt").write_text("preserve")
    collect_subject("CMF23", tmp_path / "source", "EMA/pos", "rainbow", tmp_path / "out", settings, yaml_only=True)
    assert (target / "recordings" / "rainbow" / "speech.wav").read_bytes() == b"preserve"
    assert (target / "info.txt").read_text() == "preserve"
    assert yaml.safe_load((target / "corpus.yaml").read_text())["columns"] == {"Ch1_X": "jaw_x"}
