# `textgrid-to-csv`

Convert a Praat TextGrid into a time-based CSV, or export one row per TextGrid
entry.

## Sampled output

```powershell
skalspeech textgrid-to-csv 100 recording.TextGrid recording.csv
```

The first argument is the sampling frequency in Hz. The output contains a
`time` column followed by a label and zero-based source interval number for
each selected tier. Select tiers with repeatable `--tier` options:

```powershell
skalspeech textgrid-to-csv 100 recording.TextGrid phones.csv --tier phones
```

Use `--separate` to write one output file per selected tier.

For example, one selected tier produces columns like:

```text
time,phones,phones_int
```

Use `--instances` to add a `<tier>_instance` column. Each non-empty label is
numbered from zero independently within its tier, and the number stays the
same for every sampled row inside that interval. Empty labels have an empty
instance value.

```powershell
skalspeech textgrid-to-csv 100 recording.TextGrid recording.csv `
	--tier words --tier phones --instances
```

## Interval output

```powershell
skalspeech textgrid-to-csv 0 recording.TextGrid intervals.csv --intervals
```

The interval format contains `tier`, `start`, `end`, and `label` columns. The
frequency is ignored in this mode, so `0` is convenient. `--legacy` is an
alias for `--intervals`.
