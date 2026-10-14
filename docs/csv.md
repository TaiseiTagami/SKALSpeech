# `csv`

Group of commands for working with CSV files.

## Subcommands

- `csv from-txt` converts a delimited text table to CSV:

	```powershell
	skalspeech csv from-txt <input_txt> <output_csv> [--delimiter DELIMITER]
	```

- `csv insert` inserts columns from one CSV into another:

	```powershell
	skalspeech csv insert <source_csv> <destination_csv> <output_csv> [options]
	```

- `csv select` copies a CSV keeping only the columns named in the `columns`
	section of a YAML config, optionally renaming them:

	```powershell
	skalspeech csv select <input_csv> <output_csv> <config_file>
	```

	The `columns` section maps original column names (exactly as in the CSV) to
	new names. An empty new name keeps the original name. Output columns
	follow the order in the file. Other config sections are ignored (see
	[pipeline](pipeline.md) for the full config layout).

	```yaml
	columns:
	  start: begin
	  label:
	```

Use `skalspeech csv --help` to list the available CSV subcommands.
