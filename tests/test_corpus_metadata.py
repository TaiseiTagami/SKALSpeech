import csv
from pathlib import Path

import yaml
from praatio import textgrid
from praatio.data_classes.interval_tier import IntervalTier
from praatio.utilities.constants import Interval
from typer.testing import CliRunner

from skalspeech.cli import app
from skalspeech.commands.collect import collect_subject


def test_collect_writes_corpus_yaml(tmp_path):
    source = tmp_path / "source" / "CMF23_2026" / "EMA" / "pos"
    source.mkdir(parents=True)
    (source / "rainbow.wav").write_bytes(b"wav")
    (source / "rainbow.txt").write_text("Ch1_X\n1\n2\n")
    dest = collect_subject("CMF23", tmp_path / "source", "EMA/pos", "rainbow", tmp_path / "out",
                           {"wav_name": "speech.wav", "pos_name": "pos.txt", "group": "Control", "frequency": 2})
    metadata = yaml.safe_load((dest / "corpus.yaml").read_text())
    assert metadata["group"] == "Control"
    assert metadata["corpus"]["frequency"] == 2
    assert metadata["source"]["wav"] == str((source / "rainbow.wav").resolve())
    assert metadata["recordings"] == [{"id": "rainbow", "type": "speech"}]
    assert (dest / "recordings" / "rainbow" / "speech.wav").is_file()
    assert (dest / "recordings" / "rainbow" / "sensors.txt").is_file()
    assert metadata["columns"] == {}


def test_process_csv_uses_individual_frequency_and_columns(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("corpus:\n  frequency: 10\ntextgrid:\n  tiers: [words]\n  instances: false\ncolumns:\n  time: time_s\n  words: word\n", encoding="utf-8")
    for name, label in [("A", "tongue_tip_x"), ("B", "jaw_x")]:
        folder = tmp_path / name
        (folder / "input").mkdir(parents=True)
        (folder / "output").mkdir()
        (folder / "input" / "pos.txt").write_text("Ch1_X\n1\n2\n", encoding="utf-8")
        grid = textgrid.Textgrid()
        grid.addTier(IntervalTier("words", [Interval(0, 1, "rainbow")], 0, 1))
        grid.save(str(folder / "output" / "speech.TextGrid"), format="long_textgrid", includeBlankSpaces=True)
        (folder / "corpus.yaml").write_text(yaml.safe_dump({"corpus": {"frequency": 2}, "columns": {"Ch1_X": label}}))
    result = CliRunner().invoke(app, ["pipeline", "process-csv", "A", "B", "-c", str(config), "-r", str(tmp_path)])
    assert result.exit_code == 0, result.output
    for name, label in [("A", "tongue_tip_x"), ("B", "jaw_x")]:
        with (tmp_path / name / "processed" / "merged.csv").open(newline="") as handle:
            rows = list(csv.reader(handle))
        assert rows[0] == ["time_s", "word", label]
        assert len(rows) == 3
