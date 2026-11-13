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
| Whisper | architecture audio path | architecture transcription path (`annotations/transcription.TextGrid` by default) |
| MFA | architecture audio and transcription paths | architecture alignment path (`annotations/alignment.TextGrid` by default) |
| process-csv (MFA default) | architecture alignment path + `pos.txt` | architecture processed path |
| process-csv (`--source whisper`) | architecture transcription path + `pos.txt` | architecture processed path |
| process-csv (`--sensor-only`) | architecture sensor path, no TextGrid | architecture processed path |

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
Null-mapped optional columns absent from the current input are ignored;
non-null mappings to absent columns remain errors.
Template paths are relative to the YAML that specifies them.

## Generating per-speaker sensor mappings

`map-columns` inspects the first three nonblank data rows of a recording's
sensor table. A channel is populated when any configured sensor field has a
nonzero value in those rows; individual fields that remain zero (or blank)
in all three rows are omitted. Populated source channels are sorted numerically
and paired with the sensor names in
`config/default/sensor_mapping.yaml`. The command writes
`column_templates/sensor_columns.yaml` under each speaker and updates its
`corpus.yaml` to reference that file. It refuses to generate a mapping if the
populated channel count does not match the configured sensor-name count.

For example, to generate mappings for all local ALS and control Rainbow
recordings:

```powershell
skalspeech map-columns AF19 AF20 AF21 AF22 AF23 AF24 AF25 AF26 AF27 AF28 AF29 AF30 --root tests/local/als --recording rainbow
skalspeech map-columns CMF18 CMF19 CMF20 CMF21 CMF22 CMF23 CMF24 CMF25 CMF26 CMF27 CMF28 CMF29 --root tests/local/control --recording rainbow
```

The configured sensor order and field suffixes are intentionally editable.
Review the generated YAML before re-running `pipeline process-csv`.

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

## Configurable CSV input/output paths

For version 2 recordings, the default output is the architecture's processed
path (`processed.csv`). An explicit `process_csv.output` overrides it and is
relative to each recording folder. `process_csv.data` and
`process_csv.textgrid` can override the recording input paths. The recording
`recording.yaml` `files.data` is used when no explicit data path is set;
otherwise the architecture's sensor path is used (`pos.txt` at the recording
root by default). TextGrid inputs always come from the architecture's
alignment/transcription path for saved recording layouts.

```yaml
process_csv:
  output: processed/rainbow_processed.csv
  # data: pos.txt
  # textgrid: annotations/alignment.TextGrid
```

You may also place a `process_csv` section in a speaker's `corpus.yaml` or
a recording's `recording.yaml` for individual overrides. This does not
change the `pipeline run` or `pipeline from-config` path rules.
