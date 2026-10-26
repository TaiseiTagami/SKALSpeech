# `pipeline`

Processes raw MFA output and sensor data into one CSV in a single step. This
replaces running `textgrid-to-csv`, `csv from-txt`, `csv insert` and
`csv select` by hand.

## Subcommands

- `pipeline run` takes every path explicitly; settings come from the YAML:

	```powershell
	skalspeech pipeline run <textgrid_file> <data_file> <output_csv> <config_file>
	```

- `pipeline from-config` takes only the YAML; the paths come from its `files`
	section:

	```powershell
	skalspeech pipeline from-config <config_file>
	```

- `pipeline process-csv` batch-processes aligned corpora into one CSV per subject:

  ```powershell
  skalspeech pipeline process-csv CMF23 CMF24 -c config.yaml
  skalspeech pipeline process-csv CMF23 -c config.yaml --source whisper
  ```

## What it does

1. Samples the TextGrid at `corpus.frequency` (same output as
	`textgrid-to-csv`, with `--instances` on by default).
2. Reads the sensor data. `.csv` files are read as CSV; anything else is read
	as a delimited text table (tab-separated by default).
3. Inserts the TextGrid columns before the sensor columns. The row counts must
	match, otherwise the command stops with an error and writes nothing.
4. If a `columns` section is present, keeps only those columns of the merged
	table, renamed as given. Without it, every column is kept.

## Config file

The config is split into sections so one file can hold general corpus
information, repeated instrument settings, and settings for other commands.
Unknown sections (and keys) are ignored.

```yaml
corpus:            # general info about the sample / measuring instrument
  frequency: 250   # required: sensor samples per second (Hz)

files:             # only used by `pipeline from-config`
  textgrid: output/rainbow.TextGrid   # relative paths are resolved from
  data: data.txt                      # the YAML file's folder
  output: processed/merged.csv

data:
  delimiter: "\t"  # optional; for non-.csv data files (default: tab)

textgrid:
  tiers: [words, phones]  # optional; default is every tier
  instances: true         # optional; per-label occurrence numbers (default: true)

columns:           # optional; original column name -> new name
  time: time_s     # names must match the merged table exactly
  words: word
  phones:          # empty keeps the original name
  Ch1_X: tongue_x

mfa: {}            # alignment settings (used by pipeline mfa)
```

`columns` is applied to the merged table, so TextGrid columns (`time`,
`<tier>`, `<tier>_int`, `<tier>_instance`) must be listed too if you want to
keep them. Output columns follow the order in `columns`.

`csv select` reads the same `columns` section, so one config can drive both.

## `pipeline whisper` and `pipeline mfa`

Run WhisperX or MFA over a list of corpus folders (the `collect` layout, e.g.
`tests\local\control\CMF23`). Corpora are given on the command line or as
`corpora:` in the config; a corpus that fails is reported and skipped, and the
exit code is 1 if any did. Names are resolved under `root:` in the config (or
`--root`), so only the subject IDs are needed; absolute paths are used as given.

```powershell
skalspeech pipeline whisper CMF23 CMF24 -c config.yaml
skalspeech pipeline mfa CMF23 -c config.yaml --root tests\local\control
```

- `whisper` reads `<corpus>\input\speech.wav` and writes
  `<corpus>\input\speech.TextGrid` (`words` and `sentences` tiers), using the
  [`transcribe`](transcribe.md) settings from the `whisperx` section, plus
  optional `corpora`, `input_dir` (default `input`) and `wav_name` (default
  `speech.wav`).
- `mfa` runs `mfa align <corpus>\input <dictionary> <acoustic_model>
  <corpus>\output` using the `mfa` section (`dictionary`, `acoustic_model`,
  `options`, plus optional `corpora`, `input_dir`, `output_dir`, and
  `transcript_tiers`). Only the TextGrid tiers in `transcript_tiers` (default
  `[words]`) are given to MFA, because MFA treats every tier as a separate
  speaker. The input is staged in a temporary folder (`pos.txt` is left out), so
  your input folder is not changed.


## Batch CSV processing: `pipeline process-csv`

Convert completed WhisperX or MFA corpora into analysis-ready, sample-aligned CSVs
without rerunning transcription or alignment. It invokes the exact same merge,
TextGrid sampling, row-count validation, and column selection as `pipeline run`.

```powershell
skalspeech pipeline process-csv CMF23 CMF24 -c config.yaml --root tests/local/control
skalspeech pipeline process-csv CMF23 -c config.yaml --source whisper
```

Default `--source mfa` reads `<corpus>/output/speech.TextGrid`;
`--source whisper` reads `<corpus>/input/speech.TextGrid`.
Both read `<corpus>/input/pos.txt` and write
`<corpus>/processed/merged.csv`. Use `corpus.frequency`, `textgrid`,
`data` and `columns` to control the output, just like `pipeline run`.
Each failed corpus is skipped and reported; any failure causes exit code 1.

Optional config:

```yaml
process_csv:
  root: tests/local/control
  corpora: [CMF23, CMF24]
  input_dir: input
  mfa_output_dir: output
  textgrid_name: speech.TextGrid
  data_name: pos.txt
  output: processed/merged.csv
```

CLI corpus names and `--root` override configured corpora and root. When
`process_csv` does not set them, source-specific `mfa` or `whisperx`
settings are reused. The `files` section is used by `from-config`, not by `process-csv`.
For `process-csv`, `corpus.frequency` is required and `columns` must match
actual sensor headers and selected TextGrid tiers. The source-specific
`mfa` or `whisperx` config supplies the default corpus list/root; `process_csv`
overrides those settings. When `--source whisper` is used, the TextGrid name
defaults to the configured `whisperx.wav_name` stem plus `.TextGrid`.

A CSV is only written when input data and sampled
TextGrid rows match exactly; no interpolation or sensor resampling is done.

## Subject-specific corpus metadata

`collect` creates `<corpus>/corpus.yaml` with subject, group, source paths,
`corpus.frequency`, copied file names and an empty `columns` mapping. Edit
`columns` to label the actual sensor placements for each subject. When
`pipeline process-csv` runs, it automatically loads this file, overriding
shared `corpus`, `textgrid`, and `data` settings for that subject. Nonempty
per-subject `columns` entries override or extend shared column mappings;
shared column selection remains active. An empty mapping keeps the global
mapping. `files.data` points to the collected sensor file relative to the
subject directory. A missing `corpus.yaml` retains the old shared-config
behavior.

```yaml
subject: CMF23
group: Control
corpus:
  frequency: 250
source:
  wav: 'C:\data\CMF23\rainbow.wav'
  position: 'C:\data\CMF23\rainbow.txt'
files:
  wav: input/speech.wav
  data: input/pos.txt
columns:
  Ch1_X: tongue_tip_x
  Ch1_Y: tongue_tip_y
```

Sensor mappings are **per corpus**, so the same channel can have a different
anatomical meaning for another subject. Keep all shared column keys valid
for every subject, or omit the shared `columns` section and specify all
required columns in each subject's metadata.

## Shared sensor column templates

A reusable YAML template can supply a common sensor mapping to several corpora:

```yaml
# templates/standard-sensors.yaml
columns:
  time: time_s
  words: word
  Ch1_X: tongue_tip_x
  Ch1_Y: tongue_tip_y
```

Each corpus can reference it, with local overrides:

```yaml
# CMF23/corpus.yaml
column_template: ../templates/standard-sensors.yaml
columns:
  Ch1_X: jaw_x
```

`process-csv` combines the shared config's `columns`, then the template's
`columns`, then the corpus's `columns` (highest priority). The final
mapping controls both selection and renaming; omitted keys retain inherited
mappings. Template paths in `corpus.yaml` are relative to the corpus folder.
Alternatively set `process_csv.column_template` in the shared config (relative
to that config's folder) for all subjects, and override it per subject.

To assign a template during metadata generation:

```powershell
skalspeech collect CMF23 CMF24 -c collect_control.yaml --yaml-only --column-template templates/standard-sensors.yaml
```

The template is referenced, not copied, so later edits to the template apply
to all corpora referencing it. Existing explicit corpus mappings retain priority.
