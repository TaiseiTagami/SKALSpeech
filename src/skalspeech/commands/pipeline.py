import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer

from ..config import get_columns, get_section, load_config
from .corpus_pipelines import mfa_pipeline_command, whisper_pipeline_command
from .process_csv import process_csv_command
from .convert import _read_textgrid, _selected_tiers, _write_sampled_csv
from .csv_commands import (
    insert_columns,
    read_table_rows,
    select_and_rename_columns,
    write_rows,
    _read_csv,
)

pipeline_app = typer.Typer(
    help="Process MFA output and sensor data into one CSV in a single step."
)


def _frequency(config: Dict[str, Any]) -> float:
    frequency = get_section(config, "corpus").get("frequency")
    if isinstance(frequency, bool) or not isinstance(frequency, (int, float)):
        raise typer.BadParameter(
            "Config must set a numeric 'frequency' in the 'corpus' section."
        )
    if frequency <= 0:
        raise typer.BadParameter("Frequency must be greater than zero.")
    return float(frequency)


def run_pipeline(
    textgrid_file: Path,
    data_file: Path,
    output_csv: Path,
    config: Dict[str, Any],
) -> None:
    """Sample the TextGrid, merge it with the sensor data, and select columns."""
    if not textgrid_file.exists():
        raise typer.BadParameter(f"TextGrid file does not exist: {textgrid_file}")
    if not data_file.exists():
        raise typer.BadParameter(f"Data file does not exist: {data_file}")

    frequency = _frequency(config)
    textgrid_options = get_section(config, "textgrid")
    tiers = textgrid_options.get("tiers")
    if tiers is not None and not (
        isinstance(tiers, list) and all(isinstance(tier, str) for tier in tiers)
    ):
        raise typer.BadParameter("'textgrid.tiers' must be a list of tier names.")
    include_instances = bool(textgrid_options.get("instances", True))
    delimiter = get_section(config, "data").get("delimiter", "\t")
    if not isinstance(delimiter, str):
        raise typer.BadParameter("'data.delimiter' must be text.")

    intervals_by_tier = _read_textgrid(textgrid_file)
    selected_tiers = _selected_tiers(list(intervals_by_tier), tiers)
    total_time = max(
        (end for values in intervals_by_tier.values() for _, end, _ in values),
        default=0.0,
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        sampled_csv = Path(temp_dir) / "textgrid.csv"
        _write_sampled_csv(
            sampled_csv,
            intervals_by_tier,
            selected_tiers,
            frequency,
            total_time,
            include_instances,
        )
        textgrid_rows = _read_csv(sampled_csv)

    merged = insert_columns(
        textgrid_rows, read_table_rows(data_file, delimiter)
    )

    renames = get_columns(config)
    if renames:
        merged = select_and_rename_columns(merged, renames)

    write_rows(output_csv, merged)
    print(
        f"Wrote: {output_csv} ({len(merged) - 1} rows, {len(merged[0])} columns)"
    )


@pipeline_app.command("run")
def run_command(
    textgrid_file: Path,
    data_file: Path,
    output_csv: Path,
    config_file: Path,
) -> None:
    """Merge a sampled TextGrid with sensor data (.txt or .csv) into OUTPUT_CSV.

    Frequency, tiers, delimiter and the column select/rename list are read
    from CONFIG_FILE (YAML).
    """
    run_pipeline(textgrid_file, data_file, output_csv, load_config(config_file))


def _config_path(base: Path, files: Dict[str, Any], key: str) -> Path:
    value: Optional[Any] = files.get(key)
    if not isinstance(value, str) or not value:
        raise typer.BadParameter(f"Config 'files' section must set '{key}'.")
    path = Path(value)
    return path if path.is_absolute() else base / path


@pipeline_app.command("from-config")
def from_config_command(config_file: Path) -> None:
    """Run the whole pipeline from one YAML file.

    The 'files' section gives 'textgrid', 'data' and 'output' paths, resolved
    relative to the YAML file's folder.
    """
    config = load_config(config_file)
    files = get_section(config, "files")
    base = config_file.resolve().parent
    run_pipeline(
        _config_path(base, files, "textgrid"),
        _config_path(base, files, "data"),
        _config_path(base, files, "output"),
        config,
    )


pipeline_app.command("whisper")(whisper_pipeline_command)
pipeline_app.command("mfa")(mfa_pipeline_command)

pipeline_app.command("process-csv")(process_csv_command)
