# `align`

Convenience alias for `mfa align`. It accepts the four standard MFA alignment
positional arguments and forwards additional MFA options unchanged.

## Usage

```powershell
skalspeech align <corpus_directory> <dictionary_path> `
  <acoustic_model_path> <output_directory> [MFA options]
```

Example:

```powershell
skalspeech align corpus dictionary.dict english.zip output `
  --clean --single_speaker
```

MFA must be installed separately. If a Conda environment was saved with
`skalspeech environment set <name>`, SKALSpeech looks for MFA there
automatically; otherwise MFA must be available on `PATH`. Use
[`mfa`](mfa.md) for other MFA commands.
