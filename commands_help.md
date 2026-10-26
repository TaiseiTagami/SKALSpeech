# Command Help

## `csv select`

Copies a CSV keeping only the columns named in a config file, optionally
renaming them.

```powershell
skalspeech csv select <input_csv> <output_csv> <config_file>
```

| Argument | Description |
| --- | --- |
| `input_csv` | Path to the original CSV. |
| `output_csv` | Path to write the new CSV. Parent folders are created if needed. |
| `config_file` | Path to a YAML config whose `columns` section lists the columns to keep and their new names. |

### Config file

A YAML file with a `columns` section. Each key is an original column name,
spelled exactly as in the CSV header (case-sensitive). Each value is the new
name for that column. Leave the value empty (or `null`) to keep the original
name.

```yaml
columns:
  Time: time_s
  Word: word_label
  Phone:
```

- Only the listed columns are written; all others are dropped.
- Output columns appear in the order they are listed, not the order in the
  original CSV.
- Other sections in the file (such as `corpus` or `mfa`) are ignored, so the
  same config can be shared with other commands. See
  [docs/pipeline.md](docs/pipeline.md) for the full layout.

### Example

Input `input.csv`:

```csv
Time,Word,Phone,Notes
0.00,hello,HH,a
0.25,world,W,b
```

Config `config.yaml`:

```yaml
columns:
  Word: word_label
  Time: time_s
```

Command:

```powershell
skalspeech csv select input.csv output.csv config.yaml
```

Output `output.csv`:

```csv
word_label,time_s
hello,0.00
world,0.25
```

### Errors

The command stops with an error if:

- the input CSV or config file does not exist,
- the config file is not valid YAML, or `columns` is not a mapping of names to
  text,
- the `columns` section names no columns,
- a listed column is not in the CSV header,
- a data row has fewer columns than the header.

## `collect`

Copies each subject's keyword wav and position file from a data share into the
project layout (`<output>\<ID>\input\...` plus `info.txt`), renaming them to the
configured names.

```powershell
skalspeech collect [folders...] --config <config_file> [--identifier <word>] [--output <dir>]
```

| Argument / option | Description |
| --- | --- |
| `folders` | Subject folder prefixes, e.g. `CMF17 CMF18`. Optional if `collect.folders` is in the config. |
| `--config`, `-c` | Path to the YAML config with a `collect` section (required). |
| `--identifier`, `-i` | Keyword that must appear in the wav name, e.g. `rainbow`. Overrides `collect.identifier`. |
| `--output`, `-o` | Output directory. Overrides `collect.output`. |

### Config file

```yaml
collect:
  root: '\\server\share\EMA Vandy Controls'   # required: folder holding the subject folders
  audio_subdir: EMA\pos     # path inside a subject folder; "EMA" matches e.g. CMF17_07242024_EMA
  identifier: rainbow       # keyword in the wav name
  output: tests\local\control
  group: Control            # first word of info.txt (default: Control)
  wav_name: speech.wav      # default
  pos_name: pos.txt         # default
  frequency: 250            # written to info.txt (default: 250)
  folders: [CMF17, CMF18, CMF19]
```

- The position file is the wav's name with `.txt`.
- Existing output for a collected subject is overwritten.

### Example

```powershell
skalspeech collect CMF18 CMF19 -c collect.yaml
```

Output:

```text
tests\local\control\CMF18\info.txt
tests\local\control\CMF18\input\speech.wav
tests\local\control\CMF18\input\pos.txt
```

### Errors

A subject is reported and skipped (the others continue, and the exit code is 1)
if:

- no folder, or more than one folder, starts with the subject prefix,
- the audio folder is missing or ambiguous,
- no wav, or more than one wav, contains the identifier,
- the matching `.txt` position file does not exist.

The command stops immediately if the config is missing or `root`, `identifier`,
`output` or the folder list is not set.

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

## `pipeline run`

Samples a TextGrid at the config's frequency, merges it with sensor data
(`.txt` or `.csv`), and applies the `columns` select/rename list, all in one
step.

```powershell
skalspeech pipeline run <textgrid_file> <data_file> <output_csv> <config_file>
```

| Argument | Description |
| --- | --- |
| `textgrid_file` | Path to the TextGrid output by MFA. |
| `data_file` | Path to the raw sensor data. `.csv` is read as CSV; anything else is read as a delimited text table (tab by default). |
| `output_csv` | Path to write the merged CSV. Parent folders are created if needed. |
| `config_file` | Path to the YAML config (see below). |

### Example

```powershell
skalspeech pipeline run output\rainbow.TextGrid data.txt processed\merged.csv config.yaml
```

With only `corpus.frequency` set, this produces the same file as running
`textgrid-to-csv --instances`, `csv from-txt` and `csv insert` by hand.

## `pipeline from-config`

Runs the same pipeline using only a YAML file. The input and output paths come
from the config's `files` section; relative paths are resolved from the YAML
file's folder, not the current directory.

```powershell
skalspeech pipeline from-config <config_file>
```

### Example

```powershell
skalspeech pipeline from-config tests\local\rainbow_control_2\config.yaml
```

## Pipeline config file

Sections are independent, and unknown sections or keys are ignored, so one
file can hold corpus info, instrument settings and settings for other commands.

```yaml
corpus:
  frequency: 250            # required: sensor samples per second (Hz)

files:                      # required only for `pipeline from-config`
  textgrid: output/rainbow.TextGrid
  data: data.txt
  output: output/processed/merged.csv

data:
  delimiter: "\t"           # optional; for non-.csv data files (default: tab)

textgrid:
  tiers: [words, phones]    # optional; default is every tier
  instances: true           # optional; per-label occurrence numbers (default: true)

columns:                    # optional; original name -> new name
  time: time_s
  words: word
  phones:                   # empty keeps the original name
  Ch1_X: tongue_x

mfa: {}                     # reserved for MFA flags; currently unused
```

- `columns` is applied to the merged table, so TextGrid columns (`time`,
  `<tier>`, `<tier>_int`, `<tier>_instance`) must be listed to be kept. Without
  `columns`, every column is kept.
- Output columns follow the order in `columns`.

### Errors

The commands stop with an error, writing nothing, if:

- the TextGrid, data file or config file does not exist,
- `corpus.frequency` is missing, non-numeric or not greater than zero,
- `from-config` is missing `files.textgrid`, `files.data` or `files.output`,
- a requested tier is not in the TextGrid,
- the TextGrid and data have different numbers of rows,
- a column listed in `columns` is not in the merged table.

## `pipeline process-csv`

Batch-process existing MFA or WhisperX TextGrids with sensor position data, without
running alignment again. This uses the same sampling, merge and column selection
as `pipeline run`.

```powershell
skalspeech pipeline process-csv CMF23 CMF24 -c config.yaml --root tests/local/control
skalspeech pipeline process-csv CMF23 -c config.yaml --source whisper
```

| Argument / option | Description |
| --- | --- |
| `corpora` | Optional subject IDs or absolute paths; defaults to the config corpus list. |
| `--config`, `-c` | Required YAML configuration. |
| `--root`, `-r` | Overrides the parent folder for subject IDs. |
| `--source`, `-s` | `mfa` (default) or `whisper`; selects which TextGrid to use. |

By default, MFA reads `output/speech.TextGrid`, Whisper reads
`input/speech.TextGrid`, sensor data comes from `input/pos.txt`, and
`processed/merged.csv` is written within each subject folder.

The `process_csv` section can configure `root`, `corpora`, `input_dir`,
`mfa_output_dir`, `textgrid_name`, `data_name`, and `output`. Otherwise,
source-specific `mfa` or `whisperx` settings provide the root, corpora and
input directory. `corpus.frequency` is required; `textgrid.tiers`,
`textgrid.instances`, `data.delimiter`, and `columns` work exactly as in
`pipeline run`. The `files` section is not used.

Each corpus is processed independently. Missing files, row-count mismatches,
invalid tiers and missing columns are reported as skipped corpora. The command
returns exit code 1 if any corpus fails; it does not interpolate or resample
sensor data. See [the full pipeline guide](docs/pipeline.md).
