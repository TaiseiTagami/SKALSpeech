# TextGrid and Interval CSV Conversion

The default `textgrid-to-csv` command reads a TextGrid directly and samples
interval labels into a time-based CSV. `convert` is an alias. The legacy
TextGrid-to-intervals export remains available with `--intervals` or
`--legacy`.

## Requirements

- The project virtual environment must be activated.
- The input must be a readable Praat TextGrid file.
- The project dependencies, including `praatio`, must be installed.

## Default: Intervals to Time-Based CSV

The converter reads the TextGrid and creates one row at each timestamp spaced
by `1 / frequency` seconds.

```powershell
python main.py textgrid-to-csv <frequency> <textgrid_file> <output_csv>
```

Example:

```powershell
python main.py textgrid-to-csv 100 `
  tests/data/rainbow/output/rainbow.TextGrid `
  tests/data/rainbow/output/rainbow_sampled.csv `
  --tier phones
```

The output for one selected tier is:

```csv
time,phones
0.0,
0.01,DH
0.02,DH
```

Repeat `--tier` to select tiers. Without it, every tier in the intervals CSV
is included. Add `--separate` to write one file per tier, using names such as
`rainbow_sampled_phones.csv`. With combined output, each selected tier gets a
column, such as `time,words,phones`.

`frequency` is required for this mode and must be greater than zero. The time
range ends at the greatest interval end time in the TextGrid.

## Legacy TextGrid to Intervals CSV

The legacy converter writes one row per TextGrid entry with the columns
`tier,start,end,label`:

```powershell
python main.py textgrid-to-csv 0 <textgrid_file> <csv_file> --intervals
```

The frequency is ignored in legacy mode, so `0` can be used. Tier selection
and `--separate` remain available. `--legacy` is an alias for `--intervals`.

The `convert` alias is also available:

```powershell
python main.py convert <frequency> <textgrid_file> <output_csv>
```

Optional filters and output modes:

```powershell
python main.py textgrid-to-csv <textgrid_file> <csv_file> `
  --tier words --tier phones --separate
```

### Arguments

`textgrid_file`

Path to the input TextGrid file.

`csv_file`

Path where the converted CSV file should be written. If the file already
exists, it is overwritten. When `--separate` is used, this path supplies the
base name for the per-tier files.

`--tier`

Optional tier filter. Repeat the option to select multiple tiers. If omitted,
all tiers are converted.

`--separate`

Optional flag that writes each selected tier to its own CSV file. For example,
`rainbow.csv` becomes `rainbow_words.csv` and `rainbow_phones.csv`.

## Example

Convert the sample rainbow TextGrid:

```powershell
python main.py textgrid-to-csv `
  tests/data/rainbow/output/rainbow.TextGrid `
  tests/data/rainbow/output/rainbow.csv
```

The command prints the path of the created CSV file:

```text
Created: tests\data\rainbow\output\rainbow.csv
```

## CSV Format

The output contains one row per TextGrid entry with these columns:

| Column | Description |
| --- | --- |
| `tier` | Name of the TextGrid tier containing the entry. |
| `start` | Start time in seconds. |
| `end` | End time in seconds. |
| `label` | Entry text or label. |

For interval tiers, `start` and `end` are the interval boundaries. For point
tiers, both columns contain the point time.

Empty labels are preserved as empty CSV fields. By default, all tiers are
included in one CSV. Use `--tier` to select tiers and `--separate` to create a
CSV for each selected tier.

Example output:

```csv
tier,start,end,label
words,0.0,0.7567,
words,0.7567,0.9467,the
words,0.9467,1.5767,rainbow
```

## Rainbow Fixture

The sample file at
`tests/data/rainbow/output/rainbow.TextGrid` contains:

- 81 entries in the `words` tier
- 236 entries in the `phones` tier
- 317 data rows total, plus the CSV header

To export only the words tier:

```powershell
python main.py textgrid-to-csv `
  tests/data/rainbow/output/rainbow.TextGrid `
  tests/data/rainbow/output/words.csv `
  --tier words
```

To export the words and phones tiers into separate files:

```powershell
python main.py textgrid-to-csv `
  tests/data/rainbow/output/rainbow.TextGrid `
  tests/data/rainbow/output/rainbow.csv `
  --tier words --tier phones --separate
```

This creates `rainbow_words.csv` and `rainbow_phones.csv`.

## Errors

If the input TextGrid does not exist, the command prints an error and does not
create the CSV file. Errors raised while reading the TextGrid or writing the
CSV are printed and re-raised so they can be diagnosed from the command line.
