from beat_humanize import mono_legato_bass, apply_hi_hat_swing, humanize_pattern
import random


def test_mono_legato_trims_overlap():
    notes = [
        {"time_step": 0.0, "note": "C2", "length": 2.0, "velocity": 127},
        {"time_step": 1.0, "note": "D2", "length": 2.0, "velocity": 127},
    ]
    out = mono_legato_bass(notes)
    assert out[0]["length"] == 1.0


def test_hat_swing_moves_offbeats():
    notes = [
        {"time_step": 0.0, "note": "C5", "length": 0.25, "velocity": 100},
        {"time_step": 0.5, "note": "C5", "length": 0.25, "velocity": 100},
    ]
    rng = random.Random(42)
    out = apply_hi_hat_swing(notes, rng)
    assert out[1]["time_step"] != 0.5


def test_humanize_adds_producer_meta():
    pattern = {
        "bpm": 145,
        "style": "opium rage ken carson",
        "user_prompt": "dark trap",
        "tracks": {
            "kick": [{"time_step": 0.0, "note": "C1", "length": 0.4, "velocity": 110}],
            "snare": [{"time_step": 1.0, "note": "D1", "length": 0.3, "velocity": 110}],
            "clap": [],
            "sub_808": [{"time_step": 0.0, "note": "C2", "length": 2.0, "velocity": 127}],
            "hi_hats": [{"time_step": 0.0, "note": "C5", "length": 0.25, "velocity": 100}],
            "melody_lead": [{"time_step": 0.0, "note": "A4", "length": 1.0, "velocity": 90}],
        },
    }
    out = humanize_pattern(pattern)
    assert "plg_producer_meta" in out
    assert out["tracks"]["snare_layer"]
