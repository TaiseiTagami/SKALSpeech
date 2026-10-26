"""Batch TextGrid + sensor conversion using the same processing as pipeline run."""
from copy import deepcopy
from pathlib import Path
from typing import List, Optional

import typer

from ..config import get_section, load_config, get_columns
from .corpus_pipelines import _corpora
from .recording_layout import recordings_for, recording_paths, recording_config


def process_csv_command(
    corpora: Optional[List[str]] = typer.Argument(
        None, help="Corpus names under --root, or full corpus paths."
    ),
    config: Path = typer.Option(..., "--config", "-c", help="YAML config."),
    root: Optional[Path] = typer.Option(None, "--root", "-r", help="Corpus parent folder."),
    recording: Optional[str] = typer.Option(None, "--recording", help="Only this recording ID."),
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
        for rid, folder, meta in recordings_for(corpus, recording):
            try:
                local_settings = recording_config(settings, corpus, folder, meta, config)
                input_directory, annotation_dir, processed_dir = recording_paths(folder, meta, source)
                if meta.get("legacy"):
                    grid = corpus / grid_dir / grid_name
                    local_files = get_section(load_config(corpus / "corpus.yaml"), "files") if (corpus / "corpus.yaml").is_file() else {}
                    data = corpus / local_files.get("data", str(Path(input_dir) / data_name))
                    output = corpus / destination
                else:
                    grid = annotation_dir / ("mfa" if source == "mfa" else "") / grid_name
                    data = input_directory / "sensors.txt"
                    output = processed_dir / "merged.csv"
                if not grid.is_file():
                    raise FileNotFoundError(f"TextGrid not found: {grid}")
                if not data.is_file():
                    raise FileNotFoundError(f"Sensor data not found: {data}")
                run_pipeline(grid, data, output, local_settings)
                typer.echo(f"{corpus}/{rid}: wrote {output}")
            except (OSError, ValueError, typer.BadParameter) as error:
                failures += 1
                typer.echo(f"{corpus}/{rid}: SKIPPED - {error}", err=True)
    raise typer.Exit(1 if failures else 0)
