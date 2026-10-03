# `mfa`

Pass any MFA command and its arguments through to the installed `mfa`
executable. SKALSpeech does not install or manage MFA.

## Usage

```powershell
skalspeech mfa <mfa_command> [arguments_and_options]
```

Examples:

```powershell
skalspeech mfa version
skalspeech mfa validate corpus dictionary.dict --verbose
skalspeech mfa align corpus dictionary.dict acoustic_model.zip output
```

If an environment was saved with `skalspeech environment set <name>` and Conda
is available on `PATH`, SKALSpeech automatically runs MFA in that environment.
Otherwise, MFA must be available on `PATH`. Its exit code is returned by
SKALSpeech.
