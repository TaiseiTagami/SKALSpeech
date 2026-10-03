# `convert`

Convert a Praat TextGrid into sampled or interval-row CSV data.

`convert` is an alias for [`textgrid-to-csv`](textgrid-to-csv.md); both commands
accept the same arguments and options.

## Usage

```powershell
skalspeech convert <frequency> <textgrid_file> <output_csv> [options]
```

Use `--tier` repeatedly to select tiers, `--separate` to write one file per
tier, and `--instances` to add per-label occurrence columns. Use `--intervals`
(or `--legacy`) to write interval rows instead of sampled time rows.
