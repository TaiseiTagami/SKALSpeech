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