import csv

import pytest
import yaml
from typer.testing import CliRunner

from skalspeech.cli import app
from skalspeech.commands.corpus_architecture import template_snapshot
from skalspeech.commands.recording_layout import recording_config
from skalspeech.commands.sensor_mapping import infer_column_mapping


def _settings():
    return {
        "sensor_order": ["lr", "rr", "mr"],
        "fields": {"X": "x", "Y": "y"},
        "annotation_columns": ["time", "words"],
        "delimiter": "\t",
    }


def test_infer_column_mapping_uses_populated_channels_in_numeric_order():
    settings = _settings()
    header = [
        f"Ch{channel}_{field}"
        for channel in (1, 2, 4, 5, 6)
        for field in ("X", "Y", "Extra")
    ]
    rows = []
    active = {2, 4, 6}
    for value in (1, 2, 3):
        rows.append([
            str(value if channel in active and field in ("X", "Y") else 0)
            for channel in (1, 2, 4, 5, 6)
            for field in ("X", "Y", "Extra")
        ])

    mapping, channels = infer_column_mapping(header, rows, settings)

    assert channels == [2, 4, 6]
    assert list(mapping.items()) == [
        ("time", None),
        ("words", None),
        ("Ch2_X", "lr_x"),
        ("Ch2_Y", "lr_y"),
        ("Ch4_X", "rr_x"),
        ("Ch4_Y", "rr_y"),
        ("Ch6_X", "mr_x"),
        ("Ch6_Y", "mr_y"),
    ]


def test_infer_column_mapping_requires_three_rows_and_expected_channel_count():
    settings = _settings()
    header = [f"Ch{channel}_{field}" for channel in (1, 2, 3) for field in ("X", "Y")]
    rows = [["1", "1", "0", "0", "1", "1"] for _ in range(3)]
    with pytest.raises(ValueError, match="populated channels"):
        infer_column_mapping(header, rows, settings)
    with pytest.raises(ValueError, match="Exactly three"):
        infer_column_mapping(header, rows[:2], settings)


def test_infer_column_mapping_omits_fields_zero_in_all_probe_rows():
    settings = _settings()
    header = [f"Ch{channel}_{field}" for channel in (1, 2, 3) for field in ("X", "Y")]
    rows = [["1", "0", "1", "0", "1", "0"] for _ in range(3)]

    mapping, channels = infer_column_mapping(header, rows, settings)

    assert channels == [1, 2, 3]
    assert list(mapping.items()) == [
        ("time", None),
        ("words", None),
        ("Ch1_X", "lr_x"),
        ("Ch2_X", "rr_x"),
        ("Ch3_X", "mr_x"),
    ]


def test_map_columns_writes_template_and_updates_speaker_reference(tmp_path):
    speaker = tmp_path / "CMF21"
    recording = speaker / "recordings" / "rainbow"
    data = recording / "pos.txt"
    data.parent.mkdir(parents=True)
    channels = (2, 4, 6)
    fields = ("X", "Y")
    header = [f"Ch{channel}_{field}" for channel in (1, 2, 4, 5, 6) for field in fields]
    with data.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, delimiter="\t")
        writer.writerow(header)
        for value in (1, 2, 3):
            writer.writerow([
                str(value if channel in channels else 0)
                for channel in (1, 2, 4, 5, 6)
                for _ in range(len(fields))
            ])

    manifest = speaker / "corpus.yaml"
    manifest.write_text(yaml.safe_dump({
        "schema_version": 2,
        "architecture": template_snapshot({}),
        "recordings": [{"id": "rainbow", "type": "speech"}],
        "column_template": "old-template.yaml",
    }, sort_keys=False), encoding="utf-8")
    (recording / "recording.yaml").write_text(
        yaml.safe_dump({"id": "rainbow", "type": "speech"}), encoding="utf-8"
    )
    config = tmp_path / "sensor_mapping.yaml"
    config.write_text(yaml.safe_dump({"sensor_mapping": _settings()}), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        ["map-columns", "CMF21", "--root", str(tmp_path), "--config", str(config)],
    )

    assert result.exit_code == 0, result.output
    updated = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    assert updated["column_template"] == "column_templates/sensor_columns.yaml"
    template = yaml.safe_load(
        (speaker / updated["column_template"]).read_text(encoding="utf-8")
    )
    assert template["columns"]["Ch2_X"] == "lr_x"
    assert template["columns"]["Ch4_X"] == "rr_x"
    assert template["columns"]["Ch6_X"] == "mr_x"
    local_settings = recording_config(
        {},
        speaker,
        recording,
        yaml.safe_load((recording / "recording.yaml").read_text(encoding="utf-8")),
        config,
    )
    assert local_settings["columns"]["Ch2_X"] == "lr_x"


def test_map_columns_does_not_update_manifest_on_channel_count_mismatch(tmp_path):
    speaker = tmp_path / "CMF21"
    recording = speaker / "recordings" / "rainbow"
    data = recording / "pos.txt"
    data.parent.mkdir(parents=True)
    data.write_text(
        "Ch1_X\tCh1_Y\tCh2_X\tCh2_Y\tCh3_X\tCh3_Y\n"
        "1\t1\t0\t0\t0\t0\n"
        "2\t2\t0\t0\t0\t0\n"
        "3\t3\t0\t0\t0\t0\n",
        encoding="utf-8",
    )
    manifest = speaker / "corpus.yaml"
    manifest.write_text(yaml.safe_dump({
        "architecture": template_snapshot({}),
        "recordings": [{"id": "rainbow", "type": "speech"}],
        "column_template": "old-template.yaml",
    }), encoding="utf-8")
    (recording / "recording.yaml").write_text(
        yaml.safe_dump({"id": "rainbow", "type": "speech"}), encoding="utf-8"
    )
    config = tmp_path / "sensor_mapping.yaml"
    config.write_text(yaml.safe_dump({"sensor_mapping": _settings()}), encoding="utf-8")
    original = manifest.read_text(encoding="utf-8")

    result = CliRunner().invoke(
        app,
        ["map-columns", "CMF21", "--root", str(tmp_path), "--config", str(config)],
    )

    assert result.exit_code == 1
    assert "Refusing to guess a mapping" in result.output
    assert manifest.read_text(encoding="utf-8") == original
    assert not (speaker / "column_templates" / "sensor_columns.yaml").exists()
