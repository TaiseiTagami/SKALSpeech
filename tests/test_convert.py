import csv
from pathlib import Path

from typer.testing import CliRunner

from skalspeech.cli import app


runner = CliRunner()
FIXTURE = Path(__file__).parent / "data" / "rainbow" / "output" / "rainbow.TextGrid"


def test_convert_writes_sampled_tier_csv(tmp_path: Path):
    output = tmp_path / "phones.csv"

    result = runner.invoke(
        app,
        [
            "textgrid-to-csv",
            "2",
            str(FIXTURE),
            str(output),
            "--tier",
            "phones",
        ],
    )

    assert result.exit_code == 0, result.stdout
    with output.open(newline="", encoding="utf-8") as file:
        rows = list(csv.reader(file))
    assert rows[0] == ["time", "phones"]
    assert len(rows) == 96


def test_convert_writes_legacy_interval_csv(tmp_path: Path):
    output = tmp_path / "intervals.csv"

    result = runner.invoke(
        app,
        [
            "convert",
            "0",
            str(FIXTURE),
            str(output),
            "--intervals",
            "--tier",
            "phones",
        ],
    )

    assert result.exit_code == 0, result.stdout
    with output.open(newline="", encoding="utf-8") as file:
        rows = list(csv.reader(file))
    assert rows[0] == ["tier", "start", "end", "label"]
    assert len(rows) == 237