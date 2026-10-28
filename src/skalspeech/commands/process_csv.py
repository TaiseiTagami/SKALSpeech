"""Batch TextGrid + sensor conversion using the same processing as pipeline run."""
from pathlib import Path
from typing import List, Optional

import typer

from ..config import get_section, load_config
from .corpus_pipelines import _corpora
from .recording_layout import recordings_for, recording_paths, recording_config
from .csv_commands import read_table_rows, select_and_rename_columns, write_rows


def process_csv_command(
    corpora: Optional[List[str]] = typer.Argument(
        None, help="Corpus names under --root, or full corpus paths."
    ),
    config: Path = typer.Option(..., "--config", "-c", help="YAML config."),
    root: Optional[Path] = typer.Option(None, "--root", "-r", help="Corpus parent folder."),
    recording: Optional[str] = typer.Option(None, "--recording", help="Only this recording ID."),
    sensor_only: bool = typer.Option(False, '--sensor-only', help='Process sensor data without TextGrid; include reference recordings.'),
    source: str = typer.Option(
        "mfa", "--source", "-s", help="TextGrid source: mfa (output/) or whisper (input/)."
    ),
) -> None:
    """Generate analysis-ready CSVs for each corpus without rerunning alignment.

    Reads the same corpus/textgrid/data/columns settings as pipeline run.
    By default uses MFA's output/speech.TextGrid, input/pos.txt and writes
    processed/merged.csv. --source whisper uses input/speech.TextGrid.
    """
    # Import lazily to avoid circular imports with pipeline.py.
    from .pipeline import run_pipeline

    settings = load_config(config)
    if source not in ("mfa", "whisper"):
        raise typer.BadParameter("--source must be 'mfa' or 'whisper'.")
    section = get_section(settings, "process_csv")
    align_settings = get_section(settings, "mfa" if source == "mfa" else "whisperx")
    corpus_settings = dict(align_settings)
    corpus_settings.update(section)
    input_dir = section.get("input_dir", align_settings.get("input_dir", "input"))
    output_dir = section.get("mfa_output_dir", get_section(settings, "mfa").get("output_dir", "output"))
    grid_dir = output_dir if source == "mfa" else input_dir
    grid_name = section.get("textgrid_name", Path(align_settings.get("wav_name", "speech.wav")).stem + ".TextGrid")
    data_name = section.get("data_name", "pos.txt")
    destination = section.get("output", "processed/merged.csv")
    for name, value in (("input_dir", input_dir), ("grid_dir", grid_dir),
                        ("textgrid_name", grid_name), ("data_name", data_name), ("output", destination)):
        if not isinstance(value, str) or not value:
            raise typer.BadParameter(f"process_csv {name} must be a nonempty string.")
    failures = 0
    for corpus in _corpora(corpora, root, corpus_settings):
        for rid, folder, meta in recordings_for(corpus, recording, include_reference=sensor_only):
            try:
                local_settings = recording_config(settings, corpus, folder, meta, config)
                input_directory, annotation_dir, processed_dir = recording_paths(folder, meta, source)
                speaker_meta = load_config(corpus / "corpus.yaml") if (corpus / "corpus.yaml").is_file() else {}
                recording_meta = load_config(folder / "recording.yaml") if (folder / "recording.yaml").is_file() else {}
                # Shared defaults < speaker files < recording files.
                # Explicit process_csv paths take precedence over metadata.
                file_settings = {**get_section(speaker_meta, "files"), **get_section(recording_meta, "files")}
                path_settings = {**get_section(speaker_meta, "process_csv"), **get_section(recording_meta, "process_csv")}
                path_settings = {**section, **path_settings}
                if meta.get("legacy"):
                    grid = corpus / grid_dir / grid_name
                    local_files = get_section(load_config(corpus / "corpus.yaml"), "files") if (corpus / "corpus.yaml").is_file() else {}
                    data = corpus / local_files.get("data", str(Path(input_dir) / data_name))
                    output = corpus / destination
                else:
                    # Relative paths resolve from the recording directory.
                    # Legacy speaker files entries such as input/pos.txt are
                    # intentionally not used as recording-level defaults.
                    wav_name = file_settings.get("wav", "speech.wav")
                    if Path(wav_name).parent != Path("."):
                        wav_name = Path(wav_name).name
                    default_grid = Path("annotations") / ("mfa" if source == "mfa" else "") / (Path(wav_name).stem + ".TextGrid")
                    sensor_name = get_section(recording_meta, "files").get("data", "sensors.txt")
                    grid = folder / path_settings.get("textgrid", str(default_grid))
                    data = folder / path_settings.get("data", sensor_name)
                    output = folder / path_settings.get("output", destination)
                if output.resolve() in (data.resolve(), grid.resolve()):
                    raise ValueError("Output path must not overwrite an input file.")
                if not data.is_file():
                    raise FileNotFoundError(f"Sensor data not found: {data}")
                if sensor_only:
                    if data.resolve() == output.resolve():
                        raise ValueError("Output cannot overwrite sensor input")
                    delimiter = get_section(local_settings, "data").get("delimiter", "\\t")
                    rows = read_table_rows(data, delimiter)
                    if not rows:
                        raise ValueError(f"Empty sensor table: {data}")
                    # Ignore linguistic annotation columns in sensor-only mode.
                    columns = get_section(local_settings, "columns")
                    selected = {key: value for key, value in columns.items() if key in rows[0]}
                    if selected:
                        rows = select_and_rename_columns(rows, selected)
                    write_rows(output, rows)
                else:
                    if not grid.is_file():
                        raise FileNotFoundError(f"TextGrid not found: {grid}")
                    run_pipeline(grid, data, output, local_settings)
                typer.echo(f"{corpus}/{rid}: wrote {output}")
            except (OSError, ValueError, typer.BadParameter) as error:
                failures += 1
                typer.echo(f"{corpus}/{rid}: SKIPPED - {error}", err=True)
    raise typer.Exit(1 if failures else 0)
