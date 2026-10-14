import csv
from pathlib import Path
from typing import Dict, List, Optional

import typer
import pandas as pd

from ..config import get_columns, load_config


csv_app = typer.Typer(help="Commands for working with CSV files.")


def read_txt_table(input_txt: Path, delimiter: str) -> pd.DataFrame:
    if not input_txt.exists():
        raise typer.BadParameter(f"Text file does not exist: {input_txt}")
    if not delimiter:
        raise typer.BadParameter("Delimiter cannot be empty.")

    try:
        return pd.read_csv(
            input_txt,
            sep=delimiter,
            dtype=str,
            keep_default_na=False,
        )
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as error:
        raise typer.BadParameter(f"Could not read text table: {error}")


@csv_app.command("from-txt")
def from_txt_command(
    input_txt: Path,
    output_csv: Path,
    delimiter: str = typer.Option(
        "\t",
        "--delimiter",
        "-d",
        help="Input column delimiter. Defaults to a tab character.",
    ),
) -> None:
    """Convert a delimited text table into a CSV file."""
    data = read_txt_table(input_txt, delimiter)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(output_csv, index=False)
    print(f"Wrote: {output_csv} ({len(data)} rows, {len(data.columns)} columns)")


def _read_csv(path: Path) -> List[List[str]]:
    try:
        with path.open(newline="", encoding="utf-8") as file:
            return list(csv.reader(file))
    except FileNotFoundError:
        raise typer.BadParameter(f"CSV file does not exist: {path}")


def read_table_rows(path: Path, delimiter: str = "\t") -> List[List[str]]:
    """Read a .csv or delimited text table as header + data rows of strings."""
    if path.suffix.lower() == ".csv":
        return _read_csv(path)
    table = read_txt_table(path, delimiter)
    return [list(table.columns)] + table.values.tolist()


def _selected_columns(
    headers: List[str], column_numbers: Optional[List[int]]
) -> List[int]:
    selected = column_numbers or list(range(len(headers)))
    invalid = [number for number in selected if number < 0 or number >= len(headers)]
    if invalid:
        raise typer.BadParameter(
            f"Source column number out of range: {invalid[0]} "
            f"(source has {len(headers)} columns)"
        )
    return selected


def _validate_row_widths(rows: List[List[str]], column_count: int, label: str) -> None:
    for row_number, row in enumerate(rows, start=2):
        if len(row) < column_count:
            raise typer.BadParameter(
                f"{label} row {row_number} has {len(row)} columns; "
                f"expected at least {column_count}."
            )


def _insertion_index(
    destination_headers: List[str], position: int, before_header: Optional[str]
) -> int:
    if before_header is not None:
        if position != 0:
            raise typer.BadParameter(
                "Use either --position or --before-header, not both."
            )
        try:
            return destination_headers.index(before_header)
        except ValueError:
            raise typer.BadParameter(
                f"Destination header not found: {before_header}"
            )

    if position == -1:
        return len(destination_headers)
    if position < 0 or position > len(destination_headers):
        raise typer.BadParameter(
            f"Position must be 0, -1, or a column number from 0 to "
            f"{len(destination_headers)}."
        )
    return position


def select_and_rename_columns(
    rows: List[List[str]], renames: Dict[str, Optional[str]]
) -> List[List[str]]:
    """Keep only the named columns, renaming those given a new name."""
    if not rows:
        raise typer.BadParameter("CSV file must contain a header row.")
    headers, data = rows[0], rows[1:]
    missing = [name for name in renames if name not in headers]
    if missing:
        raise typer.BadParameter(f"Column not found in CSV: {missing[0]}")
    _validate_row_widths(data, len(headers), "CSV")

    selected = [headers.index(name) for name in renames]
    new_headers = [new or name for name, new in renames.items()]
    return [new_headers] + [[row[number] for number in selected] for row in data]


@csv_app.command("select")
def select_command(
    input_csv: Path,
    output_csv: Path,
    config_file: Path,
) -> None:
    """Copy INPUT_CSV to OUTPUT_CSV keeping only the columns in CONFIG_FILE.

    CONFIG_FILE is a YAML file whose `columns` section maps original column
    names to new names. An empty new name keeps the original name:

        columns:
          start: begin
          label:
    """
    renames = get_columns(load_config(config_file))
    if not renames:
        raise typer.BadParameter("Config file's 'columns' section names no columns.")
    rows = select_and_rename_columns(_read_csv(input_csv), renames)

    write_rows(output_csv, rows)
    print(f"Wrote: {output_csv} ({len(rows) - 1} rows, {len(rows[0])} columns)")


def write_rows(output_csv: Path, rows: List[List[str]]) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as file:
        csv.writer(file).writerows(rows)


def insert_columns(
    source_rows: List[List[str]],
    destination_rows: List[List[str]],
    column_numbers: Optional[List[int]] = None,
    position: int = 0,
    before_header: Optional[str] = None,
) -> List[List[str]]:
    """Insert source columns into the destination rows, header included."""
    if not source_rows or not destination_rows:
        raise typer.BadParameter("Both CSV files must contain a header row.")

    source_headers, source_data = source_rows[0], source_rows[1:]
    destination_headers, destination_data = (
        destination_rows[0],
        destination_rows[1:],
    )
    if len(source_data) != len(destination_data):
        raise typer.BadParameter(
            "Source and destination CSV files must have the same number of data rows "
            f"(source has {len(source_data)}, destination has {len(destination_data)})."
        )
    _validate_row_widths(source_data, len(source_headers), "Source")
    _validate_row_widths(destination_data, len(destination_headers), "Destination")

    selected = _selected_columns(source_headers, column_numbers)
    insertion_index = _insertion_index(
        destination_headers, position, before_header
    )
    inserted_headers = [source_headers[number] for number in selected]
    rows = [
        destination_headers[:insertion_index]
        + inserted_headers
        + destination_headers[insertion_index:]
    ]
    for source_row, destination_row in zip(source_data, destination_data):
        inserted_values = [source_row[number] for number in selected]
        rows.append(
            destination_row[:insertion_index]
            + inserted_values
            + destination_row[insertion_index:]
        )
    return rows


@csv_app.command("insert")
def insert_command(
    source_csv: Path,
    destination_csv: Path,
    output_csv: Path,
    column_numbers: Optional[List[int]] = typer.Option(
        None,
        "--column",
        "-c",
        help="Source column number to insert. Repeat to select multiple columns.",
    ),
    position: int = typer.Option(
        0,
        "--position",
        "-p",
        help="Destination position: 0 for beginning, -1 for end, or a column number.",
    ),
    before_header: Optional[str] = typer.Option(
        None,
        "--before-header",
        help="Insert before this destination header instead of using --position.",
    ),
) -> None:
    """Insert columns from SOURCE_CSV into DESTINATION_CSV."""
    rows = insert_columns(
        _read_csv(source_csv),
        _read_csv(destination_csv),
        column_numbers,
        position,
        before_header,
    )
    write_rows(output_csv, rows)
    print(f"Wrote: {output_csv} ({len(rows) - 1} rows)")