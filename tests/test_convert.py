import csv
from pathlib import Path

from typer.testing import CliRunner

from skalspeech.cli import app
from skalspeech.commands.convert import _write_sampled_csv


runner = CliRunner()
FIXTURE = Path(__file__).parent / "local" / "rainbow" / "output" / "rainbow.TextGrid"


INTERVALS = {
    "words": [
        (0.0, 0.5, ""),
        (0.5, 1.0, "rainbow"),
        (1.0, 1.5, ""),
        (1.5, 2.0, "rainbow"),
    ],
    "phones": [
        (0.0, 0.25, "R"),
        (0.25, 0.5, "EY"),
        (0.5, 0.75, "R"),
    ],
}


def test_sampled_csv_writes_interval_numbers_and_instances(tmp_path: Path):
    output = tmp_path / "sampled.csv"

    rows = _write_sampled_csv(
        output, INTERVALS, ["words", "phones"], 2, 2.0, include_instances=True
    )

    assert rows == 4
    with output.open(newline="", encoding="utf-8") as file:
        csv_rows = list(csv.reader(file))
    assert csv_rows[0] == [
        "time",
        "words",
        "words_int",
        "words_instance",
        "phones",
        "phones_int",
        "phones_instance",
    ]
    assert csv_rows[1] == ["0.0", "", "0", "", "R", "0", "0"]
    assert csv_rows[2] == ["0.5", "rainbow", "1", "0", "R", "2", "1"]
    assert csv_rows[3] == ["1.0", "", "2", "", "", "", ""]
    assert csv_rows[4] == ["1.5", "rainbow", "3", "1", "", "", ""]


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
    assert rows[0] == ["time", "phones", "phones_int"]
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
    assert len(rows) == 362