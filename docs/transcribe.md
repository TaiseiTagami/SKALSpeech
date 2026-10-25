# `transcribe` and `forced-align`

Transcribe audio with WhisperX and write a force-aligned Praat TextGrid.

## Setup

WhisperX needs Python 3.10-3.13, so it lives in its own environment:

```powershell
py -3.12 -m venv .venv-whisperx
.\.venv-whisperx\Scripts\python -m pip install whisperx imageio-ffmpeg
```

SKALSpeech uses `.venv-whisperx` automatically, then falls back to `whisperx`
on `PATH`, or `whisperx.executable` from the config. `ffmpeg` must be in that
environment's `Scripts` folder (copy it from `imageio_ffmpeg.get_ffmpeg_exe()`).

## `transcribe`

```powershell
skalspeech transcribe speech.wav output --config config.yaml
```

Writes `output\speech.TextGrid` with two tiers: `words` and `sentences`. The Whisper model is read from
`models\whisper\small`, so no Hugging Face access is needed.

Settings come from the `whisperx` config section; all are optional:

```yaml
whisperx:
  model: models/whisper/small                 # default
  align_model: WAV2VEC2_ASR_LARGE_LV60K_960H  # default (more precise than base)
  language: en          # default
  device: cpu           # default
  compute_type: int8    # default
  keep_json: false      # keep the raw WhisperX JSON next to the TextGrid
  options:              # any other whisperx flag (true = bare flag)
    beam_size: 5
```

The large alignment model is the default for tighter timing. Remaining
imprecision is inherent to wav2vec2 (about 20 ms frames); word boundaries are
least reliable on short function words and dysarthric speech. Use
`skalspeech align` (MFA) for phone-level boundaries.

## `forced-align`

Align a transcript you already have, with no Whisper model:

```powershell
skalspeech forced-align speech.wav transcript.txt speech.TextGrid
```

Uses the same alignment model and words/sentences tiers. Models download from
pytorch.org on first use.
