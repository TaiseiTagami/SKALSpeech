from pathlib import Path
from typing import cast

import soundfile as sf
import typer
from praatio import textgrid


def slice_command(wav_file: str, textgrid_file: str, tier_name: str) -> None:
    """Split a WAV file using intervals from a TextGrid tier."""
    wav_path = Path(wav_file)
    textgrid_path = Path(textgrid_file)
    if not wav_path.exists():
        raise typer.BadParameter(f"WAV file does not exist: {wav_path}")
    if not textgrid_path.exists():
        raise typer.BadParameter(
            f"TextGrid file does not exist: {textgrid_path}"
        )

    audio, sample_rate = sf.read(wav_path)
    grid = textgrid.openTextgrid(
        str(textgrid_path),
        includeEmptyIntervals=True,
    )
    if tier_name not in grid.tierNames:
        raise typer.BadParameter(
            f"Tier '{tier_name}' not found. Available tiers: "
            f"{', '.join(grid.tierNames)}"
        )

    tier = grid.getTier(tier_name)
    print(f"Read WAV: {wav_path}")
    print(f"Read TextGrid: {textgrid_path}")
    print(f"Tier: {tier_name}")
    print(f"Sample rate: {sample_rate}")

    created = 0
    for interval_number, entry in enumerate(tier.entries, start=1):
        if len(entry) != 3:
            continue
        start, end, label = cast(tuple[float, float, str], entry)
        if end <= start:
            continue

        start_sample = int(start * sample_rate)
        end_sample = int(end * sample_rate)
        base_name = wav_path.stem
        wav_output = wav_path.parent / f"{base_name}_{interval_number}.wav"
        txt_output = wav_path.parent / f"{base_name}_{interval_number}.txt"
        sf.write(wav_output, audio[start_sample:end_sample], sample_rate)
        txt_output.write_text(label, encoding="utf-8")
        print(f"Created: {wav_output}")
        print(f"Created: {txt_output}")
        created += 1

    print(f"Created {created} segments")
