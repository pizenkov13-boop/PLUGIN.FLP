import json
from pathlib import Path

from midi_export import STEM_FILENAMES, export_stem_session


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
