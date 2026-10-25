# `mfa`

Pass any MFA command and its arguments through to the installed `mfa`
executable. SKALSpeech does not install or manage MFA.

## Usage

```powershell
skalspeech mfa <mfa_command> [arguments_and_options]
```

Examples:

```powershell
skalspeech align-config corpus output --config config.yaml
skalspeech mfa version
skalspeech mfa validate corpus dictionary.dict --verbose
skalspeech mfa align corpus dictionary.dict acoustic_model.zip output
```

`align-config` takes only the corpus and output folders; the dictionary,
acoustic model, and MFA options come from the `mfa` section of the YAML config
(`true` gives a bare flag, `false`/empty is skipped, lists repeat the flag):

```yaml
mfa:
  dictionary: models/dictionary/english_us_arpa.dict
  acoustic_model: models/acoustic/english_us_arpa.zip
  options:
    clean: true
    num_jobs: 4
```

If an environment was saved with `skalspeech environment set <name>` and Conda
is available on `PATH`, SKALSpeech automatically runs MFA in that environment.
Otherwise, MFA must be available on `PATH`. Its exit code is returned by
SKALSpeech.
