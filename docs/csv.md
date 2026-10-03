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

Use `skalspeech csv --help` to list the available CSV subcommands.
