"""Tests for pattern / MIDI validation."""

from pathlib import Path

from midi_validate import validate_export, validate_pattern


def test_validate_pattern_ok() -> None:
    pattern = {
        "bpm": 140,
        "tracks": {
            "hi_hats": [{"note": "C5", "time_step": 0.0, "length": 0.25, "velocity": 90}],
            "sub_808": [{"note": "C2", "time_step": 0.0, "length": 1.0, "velocity": 127}],
            "melody_lead": [],
        },
    }
    assert validate_pattern(pattern) == []


def test_validate_pattern_empty() -> None:
    warnings = validate_pattern({"bpm": 120, "tracks": {}})
    assert any("no notes" in item for item in warnings)


def test_validate_export_without_files() -> None:
    pattern = {
        "bpm": 140,
        "tracks": {
            "hi_hats": [{"note": "C5", "time_step": 0.0, "length": 0.25, "velocity": 90}],
            "sub_808": [],
            "melody_lead": [],
        },
    }
    report = validate_export(pattern, midi_dir=Path("_missing_midi"))
    assert report["ok"] is False
