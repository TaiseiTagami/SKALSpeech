# Command Help

This page summarizes collection and batch processing. Other CLI commands
remain available via `skalspeech --help` and their subcommand `--help`.

## collect

```powershell
skalspeech collect CMF21 -c collect_control.yaml --recording-id rainbow
skalspeech collect CMF21 -c collect_control.yaml --identifier 0001 --recording-id silent_reference --recording-type reference
skalspeech collect CMF21 -c collect_control.yaml --yaml-only --recording-id rainbow
```

Collect one matching WAV and sensor TXT per speaker into
`<speaker>/recordings/<id>/speech.wav` and `sensors.txt`, plus speaker
`corpus.yaml` and recording `recording.yaml`. Options:
`--config/-c`, `--identifier/-i`, `--output/-o`,
`--recording-id`, `--recording-type`, `--yaml-only`,
`--column-template`. See [collect](docs/collect.md).

## pipeline whisper / mfa

```powershell
skalspeech pipeline whisper CMF21 -c whisper.yaml --root tests/local/control --recording rainbow
skalspeech pipeline mfa CMF21 -c mfa.yaml --root tests/local/control --recording rainbow
```

Whisper writes `annotations/speech.TextGrid`, MFA writes
`annotations/mfa/speech.TextGrid` under each recording. Reference recordings
are skipped. See [pipeline](docs/pipeline.md).

## pipeline process-csv

```powershell
skalspeech pipeline process-csv CMF21 -c config.yaml --root tests/local/control --recording rainbow
skalspeech pipeline process-csv CMF21 -c config.yaml --root tests/local/control --recording silent_reference --sensor-only
```

TextGrid mode merges annotations with `sensors.txt`; sensor-only mode
does not require a TextGrid and includes references. Both write
`recordings/<id>/processed/merged.csv`. Column renames inherit from
shared YAML, templates, speaker and recording metadata.
See [pipeline](docs/pipeline.md).

## Other commands

`pipeline run` processes explicitly supplied files;
`pipeline from-config` uses paths in its YAML `files` section.
`csv from-txt`, `csv select`, `csv insert`, and the standalone
alignment/transcription commands are documented in [docs](docs/README.md)
and available through CLI `--help`.
