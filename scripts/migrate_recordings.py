"""One-off, non-destructive legacy layout migration. Run with --apply to copy."""
import argparse
import shutil
from pathlib import Path
import yaml


def migrate(speaker: Path, recording_id: str = "rainbow", apply: bool = False):
    source = speaker / "input"
    if not source.is_dir():
        raise ValueError(f"Legacy input not found: {source}")
    target = speaker / "recordings" / recording_id
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite {target}")
    operations = []
    for name, destination in (
        ("speech.wav", "speech.wav"), ("pos.txt", "sensors.txt"),
        ("speech.TextGrid", "annotations/speech.TextGrid"),
    ):
        if (source / name).is_file():
            operations.append((source / name, target / destination))
    old_mfa = speaker / "output"
    if old_mfa.is_dir():
        for path in old_mfa.glob("*.TextGrid"):
            operations.append((path, target / "annotations" / "mfa" / path.name))
    old_processed = speaker / "processed"
    if old_processed.is_dir():
        for path in old_processed.glob("*.csv"):
            operations.append((path, target / "processed" / path.name))
    if not operations:
        raise ValueError(f"No recognized recording files in {speaker}")
    print(f"{speaker} -> {target}")
    for src, dst in operations:
        print(f"  COPY {src} -> {dst}")
    if not apply:
        return
    for src, dst in operations:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    manifest = speaker / "corpus.yaml"
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
    data = data or {}
    data["schema_version"] = 2
    data.setdefault("subject", speaker.name)
    entries = data.setdefault("recordings", [])
    if not any(e.get("id") == recording_id for e in entries):
        entries.append({"id": recording_id, "type": "speech"})
    manifest.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    recording_yaml = target / "recording.yaml"
    recording_yaml.write_text(yaml.safe_dump({"id": recording_id, "type": "speech", "task": recording_id}, sort_keys=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roots", nargs="+", type=Path, help="e.g. tests/local/control tests/local/als")
    parser.add_argument("--recording-id", default="rainbow")
    parser.add_argument("--apply", action="store_true", help="Copy files; default is dry-run")
    args = parser.parse_args()
    for root in args.roots:
        for speaker in sorted(root.iterdir()):
            if speaker.is_dir() and (speaker / "input").is_dir():
                migrate(speaker, args.recording_id, args.apply)


if __name__ == "__main__":
    main()
