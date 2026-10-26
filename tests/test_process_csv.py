import csv
from pathlib import Path

from praatio import textgrid
from praatio.data_classes.interval_tier import IntervalTier
from praatio.utilities.constants import Interval
from typer.testing import CliRunner

from skalspeech.cli import app


def test_process_csv_batch_mfa_and_whisper(tmp_path: Path):
    corpus = tmp_path / "CMF23"
    (corpus / "input").mkdir(parents=True)
    (corpus / "output").mkdir()
    (corpus / "input" / "pos.txt").write_text("Ch1_X\n1\n2\n", encoding="utf-8")
    for folder in ("input", "output"):
        grid = textgrid.Textgrid()
        grid.addTier(IntervalTier("words", [Interval(0, 1, "rainbow")], 0, 1))
        grid.save(str(corpus / folder / "speech.TextGrid"), format="long_textgrid", includeBlankSpaces=True)
    config = tmp_path / "config.yaml"
    config.write_text("corpus:\n  frequency: 2\ntextgrid:\n  tiers: [words]\n  instances: false\ncolumns:\n  time: time_s\n  words: word\n  Ch1_X: sensor\n", encoding="utf-8")
    runner = CliRunner()
    for source in ("mfa", "whisper"):
        result = runner.invoke(app, ["pipeline", "process-csv", "CMF23", "-c", str(config), "--root", str(tmp_path), "--source", source])
        assert result.exit_code == 0, result.stdout
        with (corpus / "processed" / "merged.csv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.reader(handle))
        assert rows == [["time_s", "word", "sensor"], ["0.0", "rainbow", "1"], ["0.5", "rainbow", "2"]]


def test_process_csv_reports_missing_files(tmp_path: Path):
    (tmp_path / "A").mkdir()
    config = tmp_path / "config.yaml"
    config.write_text("corpus:\n  frequency: 250\n", encoding="utf-8")
    result = CliRunner().invoke(app, ["pipeline", "process-csv", "A", "-c", str(config), "-r", str(tmp_path)])
    assert result.exit_code == 1
    assert "SKIPPED" in result.output
