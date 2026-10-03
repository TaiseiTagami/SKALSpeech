# Commands

The command reference is maintained in [README.md](README.md) and
[textgrid-to-csv.md](textgrid-to-csv.md).

Detailed command pages are in the [`docs`](docs/README.md) folder.

After installing the project, inspect the live CLI reference with:

```powershell
skalspeech --help
skalspeech slice --help
skalspeech mfa --help
skalspeech align --help
skalspeech environment --help
skalspeech environment set --help
skalspeech environment open --help
skalspeech textgrid-to-csv --help
skalspeech csv --help
skalspeech csv from-txt --help
skalspeech csv insert --help
```

Configure the Conda environment used for alignment and open it in a new
PowerShell window:

```powershell
skalspeech environment set aligner
skalspeech environment open
```

The `open` command starts a new shell because a command-line program cannot
activate the PowerShell session that launched it. The current shell is not
changed.
