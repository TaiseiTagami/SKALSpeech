"""Run inside the WhisperX environment: force-align a transcript to audio."""

import json
import sys
from pathlib import Path

import whisperx


def main(audio_path, transcript_path, output_path, language, device, align_model):
    audio = whisperx.load_audio(audio_path)
    text = " ".join(Path(transcript_path).read_text(encoding="utf-8").split())
    segments = [{"text": text, "start": 0.0, "end": len(audio) / 16000}]
    model, metadata = whisperx.load_align_model(
        language_code=language, device=device, model_name=align_model
    )
    result = whisperx.align(
        segments, model, metadata, audio, device
    )
    Path(output_path).write_text(
        json.dumps({"segments": result["segments"]}, default=float), encoding="utf-8"
    )


if __name__ == "__main__":
    main(*sys.argv[1:7])
