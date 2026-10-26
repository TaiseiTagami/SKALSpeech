# `collect`

Copy each subject's keyword wav and its position file into the project layout:

```
<output>\CMF21\info.txt
<output>\CMF21\input\speech.wav
<output>\CMF21\input\pos.txt
```

```powershell
skalspeech collect CMF17 CMF18 CMF19 -c collect.yaml
```

Folders, `--identifier` and `--output` can be given on the command line or in the
config (see `config.example.yaml`):

```yaml
collect:
  root: '\\server\share\EMA Vandy Controls'
  audio_subdir: EMA\pos   # "EMA" matches e.g. CMF17_07242024_EMA
  identifier: rainbow
  output: tests\local\control
  group: Control          # first word of info.txt
  wav_name: speech.wav
  pos_name: pos.txt
  frequency: 250
  folders: [CMF17, CMF18, CMF19]
```

- A subject prefix must match exactly one folder (`CMF17` -> `CMF17_07242024`).
- Exactly one wav must contain the identifier; the pos file is the same name
  with `.txt`.
- Otherwise that subject is reported and skipped, the others continue, and the
  exit code is 1. Existing output for a collected subject is overwritten.

## Per-subject metadata

Each successful collection also writes `<subject>/corpus.yaml`, alongside the
legacy `info.txt`. It records the subject ID, group, original WAV and position
file paths, collection identifier, sensor sample frequency, copied filenames,
and an initially empty `columns` mapping. Edit that mapping separately for
each subject to describe its actual sensor placements. `collect` regenerates
this YAML on recollection, so preserve manual mappings before recollecting.

```yaml
subject: CMF23
group: Control
corpus:
  frequency: 250
source:
  wav: 'C:\data\CMF23\rainbow.wav'
  position: 'C:\data\CMF23\rainbow.txt'
  subject_directory: 'C:\data\CMF23'
  identifier: rainbow
files:
  wav: input/speech.wav
  data: input/pos.txt
columns:
  Ch1_X: tongue_tip_x
  Ch1_Y: tongue_tip_y
```

The `pipeline process-csv` command reads this file automatically, using its
frequency and subject-specific column names. See [pipeline](pipeline.md).

## Metadata-only collection for existing subjects

```powershell
skalspeech collect CMF23 CMF24 -c collect_control.yaml --yaml-only
```

This mode only creates or updates each existing subject's `corpus.yaml`.
It never recopies audio/sensor files or rewrites `info.txt`. Existing sensor
column assignments and other metadata are preserved. It uses the original
source when available and falls back to the original WAV path in `info.txt`
when that source is inaccessible. The already collected input files must exist.

## Shared column template

Pass `--column-template path/to/template.yaml` with normal collection or
`--yaml-only` to save a reusable template reference in each corpus YAML.
The template contains a `columns:` mapping. Individual `corpus.yaml`
`columns` values override it during `pipeline process-csv`.
