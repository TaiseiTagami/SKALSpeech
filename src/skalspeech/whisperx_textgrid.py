"""Convert WhisperX JSON output into a Praat TextGrid."""

import json
from pathlib import Path
from typing import Dict, List

from praatio import textgrid
from praatio.data_classes.interval_tier import IntervalTier


def _tier(name: str, entries: List[tuple], max_time: float) -> IntervalTier:
    """Build a non-overlapping interval tier from (start, end, label) tuples."""
    cleaned = []
    previous_end = 0.0
    for start, end, label in sorted(entries):
        start = max(start, previous_end)
        end = min(end, max_time)
        if end <= start:
            continue
        cleaned.append((start, end, label))
        previous_end = end
    return IntervalTier(name, cleaned, 0.0, max_time)


def whisperx_json_to_textgrid(
    data: Dict, output_path: Path, duration: float = 0.0
) -> None:
    segments = data.get("segments") or []
    words, sentences = [], []
    for segment in segments:
        if "start" in segment and "end" in segment:
            sentences.append(
                (segment["start"], segment["end"], segment.get("text", "").strip())
            )
        for word in segment.get("words", []):
            if "start" in word and "end" in word:
                words.append((word["start"], word["end"], word["word"]))
    if not words and data.get("word_segments"):
        words = [
            (w["start"], w["end"], w["word"])
            for w in data["word_segments"]
            if "start" in w and "end" in w
        ]

    all_times = [end for _, end, _ in words + sentences]
    max_time = max([duration, *all_times, 0.001])

    grid = textgrid.Textgrid()
    grid.addTier(_tier("words", words, max_time))
    if sentences:
        grid.addTier(_tier("sentences", sentences, max_time))
    grid.save(str(output_path), format="long_textgrid", includeBlankSpaces=True)


def json_file_to_textgrid(
    json_path: Path, output_path: Path, duration: float = 0.0
) -> None:
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        data = {"segments": [], "word_segments": data}
    whisperx_json_to_textgrid(data, output_path, duration)
