# `environment`

Configure and open a Conda environment in a new PowerShell window.

A command-line program cannot activate the PowerShell session that launched it,
so `environment open` starts a separate window. The current shell is unchanged.

## Usage

Save the environment name with `set`:

```powershell
skalspeech environment set <environment_name>
```

Open a new activated shell with `open`:

```powershell
skalspeech environment open
```

For an MFA environment named `aligner`:

```powershell
skalspeech environment set aligner
skalspeech environment open
```

Conda must be installed and available on `PATH`.
