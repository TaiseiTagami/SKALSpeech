import csv
from pathlib import Path

from typer.testing import CliRunner

from skalspeech.cli import app


runner = CliRunner()


def write_csv(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        csv.writer(file).writerows(rows)


def read_csv(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.reader(file))


def test_insert_defaults_to_all_source_columns_at_beginning(tmp_path: Path):
    source = tmp_path / "source.csv"
    destination = tmp_path / "destination.csv"
    output = tmp_path / "output.csv"
    write_csv(source, [["source_a", "source_b"], ["1", "2"], ["3", "4"]])
    write_csv(destination, [["destination"], ["x"], ["y"]])

    result = runner.invoke(app, ["csv", "insert", str(source), str(destination), str(output)])

    assert result.exit_code == 0, result.stdout
    assert read_csv(output) == [
        ["source_a", "source_b", "destination"],
        ["1", "2", "x"],
        ["3", "4", "y"],
    ]


def test_insert_selected_column_at_end(tmp_path: Path):
    source = tmp_path / "source.csv"
    destination = tmp_path / "destination.csv"
    output = tmp_path / "output.csv"
    write_csv(source, [["source_a", "source_b"], ["1", "2"]])
    write_csv(destination, [["destination"], ["x"]])

    result = runner.invoke(
        app,
        [
            "csv",
            "insert",
            str(source),
            str(destination),
            str(output),
            "--column",
            "1",
            "--position",
            "-1",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert read_csv(output) == [["destination", "source_b"], ["x", "2"]]


def test_insert_can_insert_before_header(tmp_path: Path):
    source = tmp_path / "source.csv"
    destination = tmp_path / "destination.csv"
    output = tmp_path / "output.csv"
    write_csv(source, [["source"], ["1"]])
    write_csv(destination, [["left", "right"], ["a", "b"]])

    result = runner.invoke(
        app,
        [
            "csv",
            "insert",
            str(source),
            str(destination),
            str(output),
            "--before-header",
            "right",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert read_csv(output) == [["left", "source", "right"], ["a", "1", "b"]]