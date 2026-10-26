import csv
import yaml
from pathlib import Path
from praatio import textgrid
from praatio.data_classes.interval_tier import IntervalTier
from praatio.utilities.constants import Interval
from typer.testing import CliRunner
from skalspeech.cli import app

def test_template_and_per_corpus_override(tmp_path):
    template = tmp_path / "template.yaml"
    template.write_text("columns:\n  time: t\n  words: word\n  Ch1_X: tongue_x\n  Ch1_Y: tongue_y\n")
    config = tmp_path / "config.yaml"
    config.write_text("corpus:\n  frequency: 2\ntextgrid:\n  tiers: [words]\n  instances: false\n")
    for name, override in (("A", {}), ("B", {"Ch1_X": "jaw_x"})):
        corpus = tmp_path / name
        (corpus / "input").mkdir(parents=True)
        (corpus / "output").mkdir()
        (corpus / "input" / "pos.txt").write_text("Ch1_X\tCh1_Y\n1\t2\n3\t4\n")
        grid = textgrid.Textgrid()
        grid.addTier(IntervalTier("words", [Interval(0, 1, "rainbow")], 0, 1))
        grid.save(str(corpus / "output" / "speech.TextGrid"), format="long_textgrid", includeBlankSpaces=True)
        (corpus / "corpus.yaml").write_text(yaml.safe_dump({"column_template": "../template.yaml", "columns": override}))
    result = CliRunner().invoke(app, ["pipeline", "process-csv", "A", "B", "-c", str(config), "-r", str(tmp_path)])
    assert result.exit_code == 0, result.output
    for name, expected in (("A", "tongue_x"), ("B", "jaw_x")):
        with (tmp_path / name / "processed" / "merged.csv").open(newline="") as f:
            rows = list(csv.reader(f))
        assert rows[0] == ["t", "word", expected, "tongue_y"]
