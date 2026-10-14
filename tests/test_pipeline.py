import csv
from pathlib import Path

from praatio import textgrid
from praatio.utilities.constants import Interval
from praatio.data_classes.interval_tier import IntervalTier
from typer.testing import CliRunner

from skalspeech.cli import app


runner = CliRunner()

CONFIG = """\
corpus:
  frequency: 2
textgrid:
  tiers: [words]
  instances: false
columns:
  time: t
  words:
  Ch1_X: tongue_x
mfa:
  ignored: true
"""


def read_csv(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.reader(file))


def write_textgrid(path: Path) -> None:
    grid = textgrid.Textgrid()
    grid.addTier(
        IntervalTier(
            "words",
            [Interval(0.0, 1.0, "hello"), Interval(1.0, 2.0, "world")],
            0.0,
            2.0,
        )
    )
    grid.save(str(path), format="long_textgrid", includeBlankSpaces=True)


def test_pipeline_run_merges_txt_data_and_selects_columns(tmp_path: Path):
    grid = tmp_path / "a.TextGrid"
    data = tmp_path / "data.txt"
    config = tmp_path / "config.yaml"
    output = tmp_path / "out" / "result.csv"
    write_textgrid(grid)
    data.write_text("Ch1_X\tCh1_Y\n1\t2\n3\t4\n5\t6\n7\t8\n", encoding="utf-8")
    config.write_text(CONFIG, encoding="utf-8")

    result = runner.invoke(
        app, ["pipeline", "run", str(grid), str(data), str(output), str(config)]
    )

    assert result.exit_code == 0, result.stdout
    assert read_csv(output) == [
        ["t", "words", "tongue_x"],
        ["0.0", "hello", "1"],
        ["0.5", "hello", "3"],
        ["1.0", "world", "5"],
        ["1.5", "world", "7"],
    ]


def test_pipeline_from_config_accepts_csv_and_relative_paths(tmp_path: Path):
    write_textgrid(tmp_path / "a.TextGrid")
    (tmp_path / "data.csv").write_text(
        "Ch1_X,Ch1_Y\n1,2\n3,4\n5,6\n7,8\n", encoding="utf-8"
    )
    config = tmp_path / "config.yaml"
    config.write_text(
        CONFIG
        + "files:\n  textgrid: a.TextGrid\n  data: data.csv\n  output: result.csv\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["pipeline", "from-config", str(config)])

    assert result.exit_code == 0, result.stdout
    assert read_csv(tmp_path / "result.csv")[0] == ["t", "words", "tongue_x"]


def test_pipeline_errors_on_row_count_mismatch(tmp_path: Path):
    grid = tmp_path / "a.TextGrid"
    data = tmp_path / "data.csv"
    config = tmp_path / "config.yaml"
    write_textgrid(grid)
    data.write_text("Ch1_X\n1\n2\n", encoding="utf-8")
    config.write_text(CONFIG, encoding="utf-8")

    result = runner.invoke(
        app,
        ["pipeline", "run", str(grid), str(data), str(tmp_path / "o.csv"), str(config)],
    )

    assert result.exit_code != 0
    assert not (tmp_path / "o.csv").exists()


def test_pipeline_requires_frequency(tmp_path: Path):
    grid = tmp_path / "a.TextGrid"
    data = tmp_path / "data.csv"
    config = tmp_path / "config.yaml"
    write_textgrid(grid)
    data.write_text("Ch1_X\n1\n", encoding="utf-8")
    config.write_text("columns:\n  Ch1_X:\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["pipeline", "run", str(grid), str(data), str(tmp_path / "o.csv"), str(config)],
    )

    assert result.exit_code != 0
