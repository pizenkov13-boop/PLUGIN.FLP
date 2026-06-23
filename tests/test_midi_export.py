import json
from pathlib import Path

from midi_export import (
    STEM_FILENAMES,
    export_combined_midi,
    export_pattern_to_midi,
    export_stem_session,
)


def test_stem_export_friendly_names(tmp_path: Path):
    data = {
        "bpm": 140,
        "style": "trap",
        "tracks": {
            "kick": [{"time_step": 0.0, "note": "C1", "length": 0.25, "velocity": 110}],
            "snare": [{"time_step": 1.0, "note": "D1", "length": 0.25, "velocity": 110}],
            "hi_hats": [{"time_step": 0.0, "note": "C5", "length": 0.25, "velocity": 100}],
            "sub_808": [{"time_step": 0.0, "note": "C2", "length": 1.0, "velocity": 127}],
            "melody_lead": [{"time_step": 0.0, "note": "A4", "length": 1.0, "velocity": 90}],
        },
    }
    session = export_stem_session(data, tmp_path)
    names = {p.name for p in session["stem_paths"]}
    assert "Kick.mid" in names
    assert "808_Bass.mid" in names
    assert "HiHats.mid" in names
    assert "Melody.mid" in names
    assert (session["session_dir"] / "PLG_Beat.mid").is_file()
    manifest = json.loads((session["session_dir"] / "stems_manifest.json").read_text())
    assert manifest["bpm"] == 140


def test_stem_filenames_cover_drum_tracks():
    assert STEM_FILENAMES["sub_808"] == "808_Bass.mid"
    assert STEM_FILENAMES["hi_hats"] == "HiHats.mid"


def test_export_with_pitch_bends_writes(tmp_path: Path):
    # Regression: pitch_bend_automation must serialize (addPitchWheelEvent arg
    # order was track/channel/time — a float time landed in the channel slot and
    # crashed writeFile with "unsupported operand type(s) for |: 'int' and 'float'").
    data = {
        "bpm": 144,
        "tracks": {"melody_lead": [{"time_step": 0.0, "note": "A4", "length": 32.0, "velocity": 90}]},
        "pitch_bend_automation": [
            {"time_step": 31.5, "track": "melody_lead", "value": 8192},
            {"time_step": 31.92, "track": "melody_lead", "value": 0},
            {"time_step": 32.0, "track": "melody_lead", "value": 8192},
        ],
    }
    stems = export_pattern_to_midi(data, tmp_path, friendly_names=True)
    assert any(p.name == "Melody.mid" and p.stat().st_size > 0 for p in stems)
    combined = export_combined_midi(data, tmp_path / "PLG_Beat.mid")
    assert combined.is_file() and combined.stat().st_size > 0
