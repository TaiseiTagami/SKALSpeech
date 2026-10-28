"""Run WhisperX or MFA over a list of corpus folders (e.g. tests\\local\\control\\CMF23).

Each corpus follows the `collect` layout:

    <corpus>/input/speech.wav      -> WhisperX writes <corpus>/input/speech.TextGrid
    <corpus>/input                 -> MFA writes <corpus>/output

MFA treats each TextGrid tier as a speaker, so only the configured tiers are
staged (default: words) rather than aligning the raw input folder.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from praatio import textgrid

from ..config import get_section, load_config, load_command_config
from .recording_layout import recordings_for, recording_paths, recording_file_names, architecture_files
from .align_config import _option_arguments
from .mfa import run_mfa_process
from .transcribe import transcribe_audio


def _corpora(
    cli_value: Optional[List[str]], root: Optional[Path], settings: Dict[str, Any]
) -> List[Path]:
    """Resolve corpus names against `root` (CLI --root or config 'root').

    Absolute paths are used as given; without a root, names are used as paths.
    """
    names = cli_value or [str(item) for item in settings.get("corpora") or []]
    if not names:
        raise typer.BadParameter("No corpora given (CLI or config 'corpora').")
    base = root or (Path(settings["root"]) if settings.get("root") else None)
    return [base / name if base and not Path(name).is_absolute() else Path(name) for name in names]


def whisper_pipeline_command(
    corpora: Optional[List[str]] = typer.Argument(
        None, help="Corpus names (e.g. CMF23) under the root, or full folder paths."
    ),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Optional YAML overrides."),
    root: Optional[Path] = typer.Option(
        None, "--root", "-r", help="Folder containing the corpora (e.g. tests\\local\\control)."
    ),
    recording: Optional[str] = typer.Option(None, "--recording", help="Only this recording ID."),
) -> None:
    """Run WhisperX on each corpus and write a words/sentences TextGrid.

    Reads `<corpus>/<input_dir>/<wav_name>` and writes the TextGrid next to it.
    Settings come from the `whisperx` config section, which also accepts
    `corpora`, `input_dir` (default input) and `wav_name` (default speech.wav).
    Corpora that fail are reported and skipped; the exit code is 1 if any did.
    """
    settings = get_section(load_command_config("whisper", config), "whisperx")
    failures = 0
    for corpus in _corpora(corpora, root, settings):
        for rid, folder, meta in recordings_for(corpus, recording):
            input_directory, annotation_dir, _ = recording_paths(folder, meta, "whisper")
            if meta.get("legacy"):
                annotation_dir = input_directory
            paths = architecture_files(corpus, rid, meta)
            wav = paths["audio"] if paths else input_directory / recording_file_names(folder, meta, settings)[0]
            if paths:
                annotation_dir = paths["transcription"].parent
            try:
                if not wav.is_file():
                    raise FileNotFoundError(f"Wav file not found: {wav}")
                annotation_dir.mkdir(parents=True, exist_ok=True)
                textgrid_path = transcribe_audio(wav, annotation_dir, settings)
                if paths and textgrid_path != paths["transcription"]:
                    paths["transcription"].parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(textgrid_path), str(paths["transcription"]))
                    textgrid_path = paths["transcription"]
                typer.echo(f"{corpus}/{rid}: wrote {textgrid_path}")
            except (OSError, RuntimeError, ValueError) as error:
                failures += 1
                typer.echo(f"{corpus}/{rid}: SKIPPED - {error}", err=True)
    raise typer.Exit(1 if failures else 0)


def _stage_corpus(input_directory: Path, staging: Path, tiers: List[str]) -> None:
    """Copy the input into `staging`, keeping only `tiers` in each TextGrid."""
    for source in input_directory.iterdir():
        if not source.is_file() or source.name.lower() == "pos.txt":
            continue
        target = staging / source.name
        if source.suffix.lower() == ".textgrid":
            grid = textgrid.openTextgrid(str(source), includeEmptyIntervals=True)
            missing = [name for name in tiers if name not in grid.tierNames]
            if missing:
                raise ValueError(f"{source.name} has no tier(s): {', '.join(missing)}")
            for name in list(grid.tierNames):
                if name not in tiers:
                    grid.removeTier(name)
            grid.save(str(target), format="long_textgrid", includeBlankSpaces=True)
        else:
            shutil.copyfile(source, target)


def mfa_pipeline_command(
    corpora: Optional[List[str]] = typer.Argument(
        None, help="Corpus names (e.g. CMF23) under the root, or full folder paths."
    ),
    config: Path = typer.Option(..., "--config", "-c", help="YAML config."),
    root: Optional[Path] = typer.Option(
        None, "--root", "-r", help="Folder containing the corpora (e.g. tests\\local\\control)."
    ),
    recording: Optional[str] = typer.Option(None, "--recording", help="Only this recording ID."),
) -> None:
    """Run `mfa align` on each corpus using settings from the config.

    Aligns `<corpus>/<input_dir>` into `<corpus>/<output_dir>`. Only the
    TextGrid tiers in `transcript_tiers` (default: words) are given to MFA,
    since MFA would otherwise treat every tier as a separate speaker. The `mfa`
    config section needs `dictionary` and `acoustic_model`, and accepts
    `corpora`, `input_dir` (default input), `output_dir` (default output),
    `transcript_tiers` and `options`. Corpora that fail are reported and
    skipped; the exit code is 1 if any did.
    """
    settings = get_section(load_command_config("mfa", config), "mfa")
    for key in ("dictionary", "acoustic_model"):
        if not settings.get(key):
            raise typer.BadParameter(f"Config section 'mfa' needs '{key}'.")
    options = settings.get("options") or {}
    if not isinstance(options, dict):
        raise typer.BadParameter("Config 'mfa.options' must be a mapping.")
    tiers = settings.get("transcript_tiers", ["words"])
    if isinstance(tiers, str):
        tiers = [tiers]
    if not tiers or not all(isinstance(name, str) for name in tiers):
        raise typer.BadParameter("Config 'mfa.transcript_tiers' must list tier names.")

    failures = 0
    for corpus in _corpora(corpora, root, settings):
        for rid, folder, meta in recordings_for(corpus, recording):
            input_directory, annotation_dir, _ = recording_paths(folder, meta, "mfa")
            paths = architecture_files(corpus, rid, meta)
            output_directory = folder / settings.get("output_dir", "output") if meta.get("legacy") else (paths["alignment"].parent if paths else annotation_dir / "mfa")
            try:
                if not input_directory.is_dir():
                    raise FileNotFoundError(f"{input_directory} not found")
                with tempfile.TemporaryDirectory() as staging:
                    if meta.get("legacy"):
                        _stage_corpus(input_directory, Path(staging), tiers)
                    else:
                        # Stage only the paired audio and Whisper transcript.
                        wav = input_directory / settings.get("wav_name", "speech.wav")
                        grid = annotation_dir / (wav.stem + ".TextGrid")
                        if not wav.is_file() or not grid.is_file():
                            raise FileNotFoundError(f"Missing WAV or Whisper TextGrid for {rid}")
                        shutil.copyfile(wav, Path(staging) / wav.name)
                        # Stage only the selected transcript, never unrelated grids.
                        if paths:
                            _stage_corpus_file(grid, Path(staging) / (wav.stem + ".TextGrid"), tiers)
                        else:
                            _stage_corpus(annotation_dir, Path(staging), tiers)
                    code = run_mfa_process("align", [staging, str(settings["dictionary"]),
                        str(settings["acoustic_model"]), str(output_directory), *_option_arguments(options)])
                if code:
                    raise RuntimeError(f"MFA exited with code {code}")
                if paths:
                    produced = output_directory / (wav.stem + ".TextGrid")
                    if produced.is_file() and produced != paths["alignment"]:
                        paths["alignment"].parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(produced), str(paths["alignment"]))
                typer.echo(f"{corpus}/{rid}: wrote {output_directory}")
            except (OSError, ValueError, RuntimeError) as error:
                failures += 1
                typer.echo(f"{corpus}/{rid}: SKIPPED - {error}", err=True)
    raise typer.Exit(1 if failures else 0)


def _stage_corpus_file(source: Path, target: Path, tiers: List[str]) -> None:
    grid = textgrid.openTextgrid(str(source), includeEmptyIntervals=True)
    missing = [name for name in tiers if name not in grid.tierNames]
    if missing:
        raise ValueError(f"{source.name} has no tier(s): {', '.join(missing)}")
    for name in list(grid.tierNames):
        if name not in tiers:
            grid.removeTier(name)
    grid.save(str(target), format="long_textgrid", includeBlankSpaces=True)
