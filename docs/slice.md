# `slice`

Split a WAV recording into files using intervals from a Praat TextGrid tier.

## Usage

```powershell
skalspeech slice <wav_file> <textgrid_file> <tier_name>
```

Example:

```powershell
skalspeech slice recording.wav recording.TextGrid words
```

For each positive-duration interval, the command writes a numbered WAV file and
matching TXT label beside the source WAV, such as `recording_1.wav` and
`recording_1.txt`. Empty or zero-duration intervals are skipped.
