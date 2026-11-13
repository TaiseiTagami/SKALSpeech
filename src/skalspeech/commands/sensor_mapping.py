"""Infer per-speaker sensor column mappings from populated EMA channels."""
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

import typer
import yaml

from ..config import DEFAULT_CONFIG_DIR, get_section, load_config
from .corpus_pipelines import _corpora
from .recording_layout import architecture_files, recordings_for

_DEFAULT_CONFIG = DEFAULT_CONFIG_DIR / "sensor_mapping.yaml"
_MAPPING_PATH = Path("column_templates") / "sensor_columns.yaml"
_CHANNEL_HEADER = re.compile(r"^Ch(?P<channel>\d+)_(?P<field>[^_]+)$")


def _mapping_settings(config: Dict[str, Any]) -> Dict[str, Any]:
    settings = get_section(config, "sensor_mapping")
    sensor_order = settings.get("sensor_order")
    fields = settings.get("fields")
    annotation_columns = settings.get("annotation_columns")
    delimiter = settings.get("delimiter")

    if not isinstance(sensor_order, list) or not sensor_order:
        raise typer.BadParameter("sensor_mapping.sensor_order must be a nonempty list.")
    if any(not isinstance(name, str) or not name for name in sensor_order):
        raise typer.BadParameter("sensor_mapping.sensor_order entries must be nonempty strings.")
    if len(set(sensor_order)) != len(sensor_order):
        raise typer.BadParameter("sensor_mapping.sensor_order entries must be unique.")
    if not isinstance(fields, dict) or not fields:
        raise typer.BadParameter("sensor_mapping.fields must be a nonempty mapping.")
    if any(not isinstance(source, str) or not source or not isinstance(target, str) or not target
           for source, target in fields.items()):
        raise typer.BadParameter("sensor_mapping.fields must map nonempty source fields to suffixes.")
    if len(set(fields.values())) != len(fields):
        raise typer.BadParameter("sensor_mapping.fields suffixes must be unique.")
    if not isinstance(annotation_columns, list) or any(
        not isinstance(name, str) or not name for name in annotation_columns
    ):
        raise typer.BadParameter("sensor_mapping.annotation_columns must be a list of names.")
    if len(set(annotation_columns)) != len(annotation_columns):
        raise typer.BadParameter("sensor_mapping.annotation_columns entries must be unique.")
    if not isinstance(delimiter, str) or len(delimiter) != 1:
        raise typer.BadParameter("sensor_mapping.delimiter must be one character.")

    return {
        "sensor_order": sensor_order,
        "fields": fields,
        "annotation_columns": annotation_columns,
        "delimiter": delimiter,
    }


def _read_probe_rows(path: Path, delimiter: str) -> Tuple[List[str], List[List[str]]]:
    """Read the header and first three nonblank data rows only."""
    header: Optional[List[str]] = None
    rows: List[List[str]] = []
    try:
        with path.open(newline="", encoding="utf-8-sig") as file:
            for row in csv.reader(file, delimiter=delimiter):
                if not row or not any(cell.strip() for cell in row):
                    continue
                if header is None:
                    header = row
                    if len(set(header)) != len(header):
                        raise ValueError(f"Duplicate columns in sensor data: {path}")
                else:
                    if len(row) != len(header):
                        raise ValueError(
                            f"Sensor row has {len(row)} columns; expected {len(header)}: {path}"
                        )
                    rows.append(row)
                    if len(rows) == 3:
                        break
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        raise ValueError(f"Could not read sensor data {path}: {error}") from error

    if header is None:
        raise ValueError(f"Sensor data has no header: {path}")
    if len(rows) < 3:
        raise ValueError(f"Sensor data needs at least three data rows: {path}")
    return header, rows


def infer_column_mapping(
    header: List[str], probe_rows: List[List[str]], settings: Dict[str, Any]
) -> Tuple[Dict[str, Optional[str]], List[int]]:
    """Map active channels, in source order, onto configured sensor names."""
    fields = settings["fields"]
    field_columns: Dict[int, Dict[str, int]] = {}
    for index, name in enumerate(header):
        match = _CHANNEL_HEADER.fullmatch(name)
        if match and match.group("field") in fields:
            channel = int(match.group("channel"))
            field = match.group("field")
            columns = field_columns.setdefault(channel, {})
            if field in columns:
                raise ValueError(f"Duplicate sensor field for channel {channel}: {field}")
            columns[field] = index

    if not field_columns:
        raise ValueError("Sensor table has no columns matching configured channel fields.")
    if len(probe_rows) != 3:
        raise ValueError("Exactly three sensor data rows are required for channel detection.")

    active_channels: List[int] = []
    populated_fields: Dict[int, List[str]] = {}
    for channel, columns in sorted(field_columns.items()):
        active_fields: List[str] = []
        for field in fields:
            index = columns.get(field)
            if index is None:
                continue
            is_populated = False
            for row_number, row in enumerate(probe_rows, start=1):
                value = row[index].strip()
                if not value:
                    continue
                try:
                    measurement = Decimal(value)
                except InvalidOperation as error:
                    raise ValueError(
                        f"Non-numeric sensor value in row {row_number}, "
                        f"column {header[index]}: {value!r}"
                    ) from error
                if not measurement.is_finite():
                    raise ValueError(
                        f"Non-finite sensor value in row {row_number}, "
                        f"column {header[index]}: {value!r}"
                    )
                if measurement != 0:
                    is_populated = True
            if is_populated:
                active_fields.append(field)
        if active_fields:
            active_channels.append(channel)
            populated_fields[channel] = active_fields

    sensor_order = settings["sensor_order"]
    if len(active_channels) != len(sensor_order):
        raise ValueError(
            f"Detected {len(active_channels)} populated channels "
            f"({', '.join(map(str, active_channels))}); configuration lists "
            f"{len(sensor_order)} sensor names. Refusing to guess a mapping."
        )

    mapping: Dict[str, Optional[str]] = {
        name: None for name in settings["annotation_columns"]
    }
    for channel, sensor in zip(active_channels, sensor_order):
        for field in populated_fields[channel]:
            suffix = fields[field]
            mapping[header[field_columns[channel][field]]] = f"{sensor}_{suffix}"
    return mapping, active_channels


def _sensor_data_path(speaker: Path, recording_id: str, folder: Path, metadata: dict) -> Path:
    architecture = architecture_files(speaker, recording_id, metadata)
    if architecture:
        return architecture["sensors"]

    files = get_section(metadata, "files")
    data_path = Path(files.get("data", "pos.txt"))
    if metadata.get("legacy"):
        manifest = load_config(speaker / "corpus.yaml")
        data_path = Path(get_section(manifest, "files").get("data", "input/pos.txt"))
        base = speaker
    else:
        base = folder
    return data_path if data_path.is_absolute() else base / data_path


def _update_template_reference(manifest: Path, relative_template: Path) -> None:
    content = manifest.read_text(encoding="utf-8")
    reference = f"column_template: {relative_template.as_posix()}"
    matches = list(re.finditer(r"(?m)^column_template\s*:[^\r\n]*", content))
    if len(matches) > 1:
        raise ValueError(f"Multiple top-level column_template entries in {manifest}")
    if matches:
        match = matches[0]
        content = content[:match.start()] + reference + content[match.end():]
    else:
        if content and not content.endswith(("\n", "\r")):
            content += "\n"
        content += reference + "\n"
    manifest.write_text(content, encoding="utf-8")


def map_columns_command(
    corpora: Optional[List[str]] = typer.Argument(
        None, help="Speaker/corpus IDs under --root, or full speaker paths."
    ),
    root: Optional[Path] = typer.Option(None, "--root", "-r", help="Parent folder containing speakers."),
    recording: str = typer.Option("rainbow", "--recording", help="Recording used to detect populated channels."),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Sensor order and naming YAML."),
) -> None:
    """Generate per-speaker column mappings from the first three sensor rows."""
    if not corpora:
        raise typer.BadParameter("Provide at least one speaker/corpus.")
    config_path = config or _DEFAULT_CONFIG
    settings = _mapping_settings(load_config(config_path))
    speakers = _corpora(corpora, root, {})
    failures = 0

    for speaker in speakers:
        try:
            manifest = speaker / "corpus.yaml"
            if not manifest.is_file():
                raise ValueError(f"Speaker manifest not found: {manifest}")
            load_config(manifest)
            selected = recordings_for(speaker, recording, include_reference=True)
            recording_id, folder, metadata = selected[0]
            sensor_data = _sensor_data_path(speaker, recording_id, folder, metadata)
            header, rows = _read_probe_rows(sensor_data, settings["delimiter"])
            mapping, active_channels = infer_column_mapping(header, rows, settings)

            relative_template = _MAPPING_PATH
            template_path = speaker / relative_template
            template_path.parent.mkdir(parents=True, exist_ok=True)
            template_path.write_text(
                yaml.safe_dump({"columns": mapping}, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            _update_template_reference(manifest, relative_template)
            typer.echo(
                f"{speaker}: mapped channels {', '.join(map(str, active_channels))} "
                f"to {template_path}"
            )
        except (OSError, ValueError, typer.BadParameter) as error:
            failures += 1
            typer.echo(f"{speaker}: FAILED - {error}", err=True)

    if failures:
        raise typer.Exit(1)
