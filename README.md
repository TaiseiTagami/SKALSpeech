# SKALSpeech

A small command-line tool for working with speech recordings and Praat
TextGrid annotations. It provides commands to split a WAV recording into
labeled segments and to convert a TextGrid into CSV.

## Setup

The project uses Python and a virtual environment.

Create and activate the virtual environment on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the project and its dependencies:

```powershell
python -m pip install -e ".[dev]"
```

The same activation and installation notes are also available in
[`help.md`](help.md).

## Running Commands

After installation, run the CLI from any directory:

```powershell
skalspeech --help
```

For a checkout without installing it, `python main.py` remains available:

```powershell
python main.py --help
```

Available commands:

| Command | Purpose |
| --- | --- |
| `version` | Print the application version. |
| `slice` | Create WAV and TXT files for intervals in a selected TextGrid tier. |
| `convert` | Alias for the TextGrid conversion command. |
| `textgrid-to-csv` | Sample a TextGrid into a time-based CSV or export interval rows. |
| `csv from-txt` | Convert a delimited text table into a CSV file. |
| `csv insert` | Insert columns from one CSV into another CSV. |

## Convert Text Tables to CSV

Use `csv from-txt` for tab-separated text tables such as exported sensor
data. The first row is used as the CSV header, and tab separation is the
default:

```powershell
python main.py csv from-txt input.txt output.csv
```

For another delimiter, pass `--delimiter`:

```powershell
python main.py csv from-txt input.txt output.csv --delimiter ";"
```

## Insert CSV Columns

The `csv insert` command matches data rows from a source CSV with rows in a
destination CSV and writes the combined result to a new CSV. All source
columns are inserted at the beginning by default:

```powershell
python main.py csv insert source.csv destination.csv combined.csv
```

Use repeatable `--column` options to select source columns. Use `--position 0`
for the beginning, `--position -1` for the end, or another zero-based
destination column number. Alternatively, insert before a destination header:

```powershell
python main.py csv insert source.csv destination.csv combined.csv `
	--column 1 --position -1
python main.py csv insert source.csv destination.csv combined.csv `
	--before-header words
```

The source and destination must have the same number of data rows. The header
row is preserved and expanded with the inserted source headers.

## Slice Audio from a TextGrid

The `slice` command uses one tier from a TextGrid to cut a WAV file into
segments. Each positive-duration interval produces:

- a WAV file containing the audio for the interval
- a TXT file containing the interval label

### Usage

```powershell
python main.py slice <wav_file> <textgrid_file> <tier_name>
```

### Example

```powershell
python main.py slice recording.wav recording.TextGrid words
```

If the input WAV is `recording.wav`, output files are written beside it using
the interval number:

```text
recording_1.wav
recording_1.txt
recording_2.wav
recording_2.txt
```

The command preserves the source sample as long as they have a positive duration.
The selected tier must exist in the TextGrid.

## Convert Intervals to a Time-Based CSV

The default `textgrid-to-csv` mode reads a TextGrid directly and samples the
labels at a specified frequency. The output has a `time` column followed by
one column for each selected tier. `convert` is an alias for this command.

### Usage

```powershell
python main.py textgrid-to-csv <frequency> <textgrid_file> <output_csv>
```

By default, all tiers are included in one output CSV. Select tiers with
repeatable `--tier` options or create one output file per tier with
`--separate`:

```powershell
python main.py textgrid-to-csv 100 `
	tests/data/rainbow/output/rainbow.TextGrid `
	tests/data/rainbow/output/rainbow_sampled.csv `
	--tier phones --separate
```

`frequency` is measured in samples per second (Hz). A frequency of `100`
creates a row every `0.01` seconds. Each sample receives the label of the
interval containing its timestamp, or an empty value when no interval covers
that timestamp.

The output header for a single selected tier is:

```powershell
time,phones
```

When multiple tiers are combined, each tier gets its own column:

```text
time,words,phones
```

The total time is the greatest interval end time in the TextGrid.

## Legacy TextGrid-to-Intervals Export

The old conversion behavior is available from `textgrid-to-csv` with
`--intervals` (or the alias `--legacy`). The frequency is ignored, so pass
`0`:

```powershell
python main.py textgrid-to-csv 0 `
	tests/data/rainbow/output/rainbow.TextGrid `
	tests/data/rainbow/output/rainbow_intervals.csv `
	--intervals --tier phones
```

This writes one row per TextGrid entry with the columns `tier,start,end,label`.
See [`textgrid-to-csv.md`](textgrid-to-csv.md) for details.

By default, all tiers are written to the requested CSV. Repeat `--tier` to
select specific tiers:

```powershell
python main.py textgrid-to-csv recording.TextGrid words.csv --tier words
```

Add `--separate` to create one file per selected tier. With an output path of
`rainbow.csv`, this creates `rainbow_words.csv` and `rainbow_phones.csv`:

```powershell
python main.py textgrid-to-csv recording.TextGrid rainbow.csv `
	--tier words --tier phones --separate
```

## Sample Data

The sample annotation files are under
[`tests/data/rainbow`](tests/data/rainbow). The output TextGrid contains:

- a `words` tier with 81 entries
- a `phones` tier with 236 entries
- 317 entries total

For example, sample the TextGrid directly at 100 Hz:

```powershell
python main.py textgrid-to-csv 100 `
	tests/data/rainbow/output/rainbow.TextGrid `
	tests/data/rainbow/output/rainbow_phones.csv `
	--tier phones
```

## Project Layout

```text
pyproject.toml                  Packaging, dependencies, and CLI entry point
src/skalspeech/
	cli.py                        Typer application and command registration
	commands/                      Slice and conversion implementations
tests/                          Automated tests and sample fixture data
.github/workflows/tests.yml     GitHub Actions test workflow
README.md                       Project documentation
textgrid-to-csv.md              Conversion-specific documentation
```

## Current Limitations

- `slice` requires the WAV path, TextGrid path, and tier name explicitly.
- `slice` writes output beside the source WAV; there is no output-directory
	option yet.
- `slice` creates TXT labels but does not create segmented TextGrid files.
- `convert` overwrites the requested CSV path when it already exists.
- Automated Python tests are not yet included; the sample rainbow data is the
	current manual validation fixture.
