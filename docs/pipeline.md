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

mfa: {}            # reserved for MFA flags; currently unused
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
  [`transcribe`](docs/transcribe.md) settings from the `whisperx` section, plus
  optional `corpora`, `input_dir` (default `input`) and `wav_name` (default
  `speech.wav`).
- `mfa` runs `mfa align <corpus>\input <dictionary> <acoustic_model>
  <corpus>\output` using the `mfa` section (`dictionary`, `acoustic_model`,
  `options`, plus optional `corpora`, `input_dir`, `output_dir`, and
  `transcript_tiers`). Only the TextGrid tiers in `transcript_tiers` (default
  `[words]`) are given to MFA, because MFA treats every tier as a separate
  speaker. The input is staged in a temporary folder (`pos.txt` is left out), so
  your input folder is not changed.

