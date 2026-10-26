# Multi-recording layout (schema version 2)

A speaker owns a `corpus.yaml` with subject/group/frequency, column templates,
sensor mappings and a `recordings` registry. Every recording has its own
`recording.yaml`, `speech.wav`, `sensors.txt`, `annotations/` and
`processed/`. Reference recordings use `type: reference` and are skipped by
speech processing by default. IDs should be unique within each speaker, e.g.
`rainbow_001`, `rainbow_002`, `silent_reference`.

```text
tests/local/control/CMF21/
  corpus.yaml
  recordings/
    rainbow/
      recording.yaml
      speech.wav
      sensors.txt
      annotations/
        speech.TextGrid
        mfa/speech.TextGrid
      processed/merged.csv
    silent_reference/
      recording.yaml
      speech.wav
      sensors.txt
```

`collect` accepts `--recording-id` and `--recording-type speech|reference`.
For example, `skalspeech collect CMF21 -c collect_control.yaml
--recording-id rainbow`. Existing speaker YAML and recording YAML are retained
when collecting additional recordings. `--yaml-only` requires the already
collected recording files to exist and never copies them.

`pipeline whisper`, `pipeline mfa`, and `pipeline process-csv` accept
`--recording ID`; otherwise they iterate all speech recordings registered
for the speaker. Existing legacy speaker input/output/processed folders remain
readable until migration. `process-csv` applies shared settings, speaker
metadata and recording-specific overrides, with recording columns highest
priority. Whisper writes to `annotations/speech.TextGrid`, MFA writes to
`annotations/mfa/speech.TextGrid`, and processed CSV goes to
`processed/merged.csv`.

## Migrating existing collected data

Run the one-off script from the repository root:

```powershell
python scripts/migrate_recordings.py tests/local/control tests/local/als
python scripts/migrate_recordings.py tests/local/control tests/local/als --apply
```

The first invocation previews changes. `--apply` **copies**, never moves or
deletes the original `input/`, `output/`, or `processed/` folders. It
refuses to overwrite an existing target recording. Inspect the result before
manually retiring the legacy folders. Use `--recording-id` if the old
single recording is not the Rainbow Passage. The migration does not infer
silent reference recordings from numbered filenames.
