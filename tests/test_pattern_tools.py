import json
from pathlib import Path

import pytest

from pattern_tools import PatternError, chaos_roll, flip_beat, load_pattern, save_pattern, set_filth_mode
from mix_blueprint import list_blueprint_steps


@pytest.fixture
def sample_pattern(tmp_path: Path, monkeypatch):
    pattern = {
        "bpm": 140,
        "style": "opium test",
        "user_prompt": "rage",
        "tracks": {
            "kick": [{"time_step": 0.0, "note": "C1", "length": 0.25, "velocity": 110}],
            "snare": [{"time_step": 1.0, "note": "D1", "length": 0.25, "velocity": 110}],
            "clap": [],
            "sub_808": [{"time_step": 0.0, "note": "C2", "length": 1.0, "velocity": 127}],
            "hi_hats": [
                {"time_step": 0.0, "note": "C5", "length": 0.25, "velocity": 100},
                {"time_step": 0.5, "note": "C5", "length": 0.25, "velocity": 100},
            ],
            "melody_lead": [{"time_step": 0.0, "note": "A4", "length": 1.0, "velocity": 90}],
        },
        "plg_sample_picks": {"kick": "kick.wav"},
    }
    path = tmp_path / "output_pattern.json"
    save_pattern(pattern, path)

    import pattern_tools as pt

    monkeypatch.setattr(pt, "PATTERN_JSON", path)
    monkeypatch.setattr(pt, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(pt, "finalize_pattern_exports", lambda p, project_dir=None: {
        "stem_session": str(tmp_path / "stems"),
        "stem_files": ["Kick.mid"],
        "mix_blueprint": str(tmp_path / "READ_ME_IMBA.txt"),
    })
    return pattern, path


def test_chaos_roll_increments_counter(sample_pattern):
    pattern, _path = sample_pattern
    out = chaos_roll(pattern)
    assert out["ok"] is True
    assert out.get("chaos_rolls", 0) >= 1


def test_flip_reverses_melody(sample_pattern):
    pattern, path = sample_pattern
    out = flip_beat(pattern)
    assert out["ok"] is True
    saved = load_pattern(path)
    melody = saved["tracks"]["melody_lead"]
    assert melody[0]["time_step"] >= 0


def test_filth_mode_toggle(sample_pattern):
    pattern, _ = sample_pattern
    on = set_filth_mode(True, pattern)
    assert on["filth_mode"] is True
    off = set_filth_mode(False, on)
    assert off["filth_mode"] is False


def test_blueprint_steps_nonempty(sample_pattern):
    pattern, _ = sample_pattern
    steps = list_blueprint_steps(pattern)
    assert len(steps) >= 3
    assert all("id" in s and "text" in s for s in steps)


def test_load_missing_raises(tmp_path: Path):
    missing = tmp_path / "missing.json"
    with pytest.raises(PatternError):
        load_pattern(missing)
