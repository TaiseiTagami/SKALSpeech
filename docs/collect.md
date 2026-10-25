# `collect`

Copy each subject's keyword wav and its position file into the project layout:

```
<output>\CMF21\info.txt
<output>\CMF21\input\speech.wav
<output>\CMF21\input\pos.txt
```

```powershell
skalspeech collect CMF17 CMF18 CMF19 -c collect.yaml
```

Folders, `--identifier` and `--output` can be given on the command line or in the
config (see `config.example.yaml`):

```yaml
collect:
  root: '\\server\share\EMA Vandy Controls'
  audio_subdir: EMA\pos   # "EMA" matches e.g. CMF17_07242024_EMA
  identifier: rainbow
  output: tests\local\control
  group: Control          # first word of info.txt
  wav_name: speech.wav
  pos_name: pos.txt
  frequency: 250
  folders: [CMF17, CMF18, CMF19]
```

- A subject prefix must match exactly one folder (`CMF17` -> `CMF17_07242024`).
- Exactly one wav must contain the identifier; the pos file is the same name
  with `.txt`.
- Otherwise that subject is reported and skipped, the others continue, and the
  exit code is 1. Existing output for a collected subject is overwritten.
