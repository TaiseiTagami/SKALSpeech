import csv
from pathlib import Path
from typing import List, Optional

import typer
import pandas as pd


csv_app = typer.Typer(help="Commands for working with CSV files.")


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
    if not input_txt.exists():
        raise typer.BadParameter(f"Text file does not exist: {input_txt}")
    if not delimiter:
        raise typer.BadParameter("Delimiter cannot be empty.")

    try:
        data = pd.read_csv(
            input_txt,
            sep=delimiter,
            dtype=str,
            keep_default_na=False,
        )
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as error:
        raise typer.BadParameter(f"Could not read text table: {error}")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(output_csv, index=False)
    print(f"Wrote: {output_csv} ({len(data)} rows, {len(data.columns)} columns)")


def _read_csv(path: Path) -> List[List[str]]:
    try:
        with path.open(newline="", encoding="utf-8") as file:
            return list(csv.reader(file))
    except FileNotFoundError:
        raise typer.BadParameter(f"CSV file does not exist: {path}")


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
    source_rows = _read_csv(source_csv)
    destination_rows = _read_csv(destination_csv)
    if not source_rows or not destination_rows:
        raise typer.BadParameter("Both CSV files must contain a header row.")

    source_headers, source_data = source_rows[0], source_rows[1:]
    destination_headers, destination_data = (
        destination_rows[0],
        destination_rows[1:],
    )
    if len(source_data) != len(destination_data):
        raise typer.BadParameter(
            "Source and destination CSV files must have the same number of data rows."
        )
    _validate_row_widths(source_data, len(source_headers), "Source")
    _validate_row_widths(destination_data, len(destination_headers), "Destination")

    selected = _selected_columns(source_headers, column_numbers)
    insertion_index = _insertion_index(
        destination_headers, position, before_header
    )
    inserted_headers = [source_headers[number] for number in selected]
    rows = []
    for source_row, destination_row in zip(source_data, destination_data):
        inserted_values = [source_row[number] for number in selected]
        rows.append(
            destination_row[:insertion_index]
            + inserted_values
            + destination_row[insertion_index:]
        )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            destination_headers[:insertion_index]
            + inserted_headers
            + destination_headers[insertion_index:]
        )
        writer.writerows(rows)

    print(f"Wrote: {output_csv} ({len(rows)} rows)")