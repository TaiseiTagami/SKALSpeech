## Local setup

Create and activate the virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the project in editable mode with development tools:

```powershell
python -m pip install -e ".[dev]"
```

Run the CLI:

```powershell
skalspeech --help
```