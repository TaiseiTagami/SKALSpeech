import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import typer

from ..config import get_section, load_config
from ..whisperx_textgrid import json_file_to_textgrid
from .align_config import _option_arguments

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _whisperx_executable(configured: Optional[str]) -> str:
    if configured:
        return str(configured)
    local = PROJECT_ROOT / ".venv-whisperx" / "Scripts" / "whisperx.exe"
    if local.exists():
        return str(local)
    found = shutil.which("whisperx")
    if found:
        return found
    raise typer.BadParameter(
        "WhisperX was not found. Create .venv-whisperx, set 'whisperx.executable' "
        "in the config, or put 'whisperx' on PATH."
    )


def _whisperx_environment(executable: str) -> dict:
    """Put the WhisperX environment's Scripts folder (with ffmpeg) on PATH."""
    environment = os.environ.copy()
    scripts = str(Path(executable).resolve().parent)
    environment["PATH"] = scripts + os.pathsep + environment.get("PATH", "")
    return environment



DEFAULT_ALIGN_MODEL = "WAV2VEC2_ASR_LARGE_LV60K_960H"


def _soundfile_duration(audio_path: Path) -> float:
    import soundfile

    try:
        return float(soundfile.info(str(audio_path)).duration)
    except RuntimeError:
        return 0.0


def transcribe_audio(
    audio_path: Path, output_directory: Path, settings: Dict[str, Any]
) -> Path:
    """Run WhisperX on one file and return the path of the TextGrid it wrote."""
    options = settings.get("options") or {}
    if not isinstance(options, dict):
        raise typer.BadParameter("Config 'whisperx.options' must be a mapping.")

    defaults = {
        "model": str(PROJECT_ROOT / "models" / "whisper" / "small"),
        "language": "en",
        "device": "cpu",
        "compute_type": "int8",
    }
    for key in defaults:
        defaults[key] = settings.get(key, defaults[key])
    output_directory.mkdir(parents=True, exist_ok=True)
    merged = {
        **defaults,
        "align_model": settings.get("align_model", DEFAULT_ALIGN_MODEL),
        **options,
        "output_format": "json",
        "output_dir": str(output_directory),
    }

    executable = _whisperx_executable(settings.get("executable"))
    command = [executable, str(audio_path), *_option_arguments(merged)]
    result = subprocess.run(
        command, check=False, env=_whisperx_environment(executable)
    )
    if result.returncode:
        raise RuntimeError(f"WhisperX exited with code {result.returncode}")

    json_path = output_directory / f"{audio_path.stem}.json"
    textgrid_path = output_directory / f"{audio_path.stem}.TextGrid"
    json_file_to_textgrid(json_path, textgrid_path, _soundfile_duration(audio_path))
    if not settings.get("keep_json", False):
        json_path.unlink()
    return textgrid_path


def transcribe_command(
    audio_path: Path,
    output_directory: Path,
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="YAML config with a `whisperx` section."
    ),
) -> None:
    """Transcribe audio with WhisperX and write a force-aligned TextGrid.

    The TextGrid has `words` and `sentences` tiers. Settings (`executable`,
    `model`, `align_model`, `language`, `device`, `compute_type`, `keep_json`,
    `options`) come from the `whisperx` section of the config.
    """
    settings = get_section(load_config(config), "whisperx") if config else {}
    try:
        textgrid_path = transcribe_audio(audio_path, output_directory, settings)
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1)
    typer.echo(f"Wrote {textgrid_path}")

def forced_align_command(
    audio_path: Path,
    transcript_path: Path,
    output_textgrid: Path,
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="YAML config with a `whisperx` section."
    ),
) -> None:
    """Force-align a known transcript to audio and write a TextGrid.

    No Whisper model is needed, only the wav2vec2 alignment model.
    """
    settings = get_section(load_config(config), "whisperx") if config else {}
    executable = _whisperx_executable(settings.get("executable"))
    python = Path(executable).resolve().parent / "python.exe"
    if not python.exists():
        raise typer.BadParameter(f"No python.exe next to {executable}.")

    with tempfile.TemporaryDirectory() as temporary:
        json_path = Path(temporary) / "aligned.json"
        command = [
            str(python),
            str(Path(__file__).resolve().parent.parent / "whisperx_align.py"),
            str(audio_path),
            str(transcript_path),
            str(json_path),
            str(settings.get("language", "en")),
            str(settings.get("device", "cpu")),
            str(settings.get("align_model", DEFAULT_ALIGN_MODEL)),
        ]
        result = subprocess.run(
            command, check=False, env=_whisperx_environment(executable)
        )
        if result.returncode:
            raise typer.Exit(result.returncode)
        output_textgrid.parent.mkdir(parents=True, exist_ok=True)
        json_file_to_textgrid(
            json_path, output_textgrid, _soundfile_duration(audio_path)
        )
    typer.echo(f"Wrote {output_textgrid}")
