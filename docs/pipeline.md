# pipeline — multi-recording workflow

Batch commands operate on `<speaker>/recordings/<id>` using speaker
`corpus.yaml` and recording `recording.yaml`.
By default, Whisper, MFA and TextGrid-based CSV processing skip recordings
marked `type: reference`. Use `--recording ID` to select one.

```powershell
skalspeech pipeline whisper CMF21 -c whisper.yaml --root tests/local/control --recording rainbow
skalspeech pipeline mfa CMF21 -c mfa.yaml --root tests/local/control --recording rainbow
skalspeech pipeline process-csv CMF21 -c config.yaml --root tests/local/control --recording rainbow
skalspeech pipeline process-csv CMF21 -c config.yaml --root tests/local/control --recording silent_reference --sensor-only
```

| Stage | Input relative to recording | Output relative to recording |
| --- | --- | --- |
| Whisper | `speech.wav` | `annotations/speech.TextGrid` |
| MFA | WAV and Whisper TextGrid | `annotations/mfa/speech.TextGrid` |
| process-csv (MFA default) | MFA TextGrid + `sensors.txt` | `processed/merged.csv` |
| process-csv (`--source whisper`) | Whisper TextGrid + `sensors.txt` | `processed/merged.csv` |
| process-csv (`--sensor-only`) | `sensors.txt`, no TextGrid | `processed/merged.csv` |

`--sensor-only` includes reference recordings. Without `--recording`,
it processes both speech and reference recordings. It filters configured
annotation columns absent from the sensor table and does not add a time
column. MFA stages only configured transcript tiers (`mfa.transcript_tiers`,
default `[words]`).

## Configuration and column mappings

Batch corpora may be supplied on the CLI or under `corpora` in the
relevant `whisperx`, `mfa` or `process_csv` section.
`--root` overrides its `root`.

Normal CSV processing samples TextGrid annotations at `corpus.frequency`,
merges sensor rows and selects/renames columns. Row counts must match exactly:
no interpolation or sensor resampling is performed.

Column mapping precedence, lowest to highest:

1. Shared processing YAML `columns`.
2. Shared column template.
3. Speaker `corpus.yaml` `columns`.
4. Recording `recording.yaml` `columns`.

Higher-priority values override matching original headers without moving
their column order. With mappings, only selected columns are kept; without
them, all columns are kept. A null rename keeps the original name.
Template paths are relative to the YAML that specifies them.

```yaml
# Shared config.yaml
textgrid:
  tiers: [words]
  instances: true
process_csv:
  root: tests/local/control
  column_template: templates/ema.yaml
```

```yaml
# CMF21/corpus.yaml
schema_version: 2
subject: CMF21
group: Control
corpus:
  frequency: 250
recordings:
  - id: rainbow
    type: speech
  - id: silent_reference
    type: reference
columns:
  Ch1_X: tongue_tip_x
```

```yaml
# recordings/silent_reference/recording.yaml
id: silent_reference
type: reference
columns:
  Ch1_X: jaw_x
```

## Explicit paths and legacy layout

`pipeline run <textgrid_file> <data_file> <output_csv> <config_file>`
uses explicit files. `pipeline from-config <config_file>` resolves
`files.textgrid`, `files.data` and `files.output` relative to its YAML.
These commands are layout-independent.

Batch commands retain legacy speaker-level `input/speech.wav`,
`input/pos.txt`, `output/speech.TextGrid`, `processed/merged.csv`
compatibility. New collection uses v2 instead. See
[recordings](recordings.md) for the copy-only migration script.
