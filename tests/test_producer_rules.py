import random

from beat_humanize import (
    apply_open_hat_choke,
    apply_pre_snare_shift,
    apply_six_db_hat_rule,
    apply_velocity_sine_curve,
    build_pitch_bend_automation,
    humanize_pattern,
    ms_to_beats,
)


def test_ms_to_beats():
    assert ms_to_beats(5.0, 120.0) > 0


def test_pre_snare_shift_earlier():
    notes = [{"time_step": 1.0, "note": "D1", "length": 0.25, "velocity": 110}]
    rng = random.Random(1)
    out = apply_pre_snare_shift(notes, 140.0, rng)
    assert out[0]["time_step"] < 1.0
    assert "pre_snare_shift_ms" in out[0]


def test_six_db_rule_lowers_hats():
    hats = [{"time_step": 0.0, "note": "C5", "length": 0.25, "velocity": 120}]
    ref = [{"time_step": 0.0, "note": "D1", "length": 0.25, "velocity": 110}]
    out = apply_six_db_hat_rule(hats, ref)
    assert out[0]["velocity"] < 110


def test_open_hat_choke_shortens_tail():
    hats = [
        {"time_step": 0.0, "note": "C5", "length": 0.5, "velocity": 100, "hat_type": "open"},
        {"time_step": 0.25, "note": "C5", "length": 0.125, "velocity": 110},
    ]
    out = apply_open_hat_choke(hats)
    open_hat = next(n for n in out if n.get("hat_type") == "open")
    assert open_hat["length"] <= 0.26


def test_velocity_sine_curve_varies():
    notes = [{"time_step": float(i), "note": "C5", "length": 0.25, "velocity": 100} for i in range(4)]
    out = apply_velocity_sine_curve(notes)
    velocities = {n["velocity"] for n in out}
    assert len(velocities) > 1


def test_pitch_bend_automation_every_8_bars():
    pattern = {
        "bpm": 140,
        "tracks": {
            "melody_lead": [{"time_step": 0.0, "note": "A4", "length": 32.0, "velocity": 90}],
        },
    }
    events = build_pitch_bend_automation(pattern)
    assert events
    assert any(e["value"] == 0 for e in events)


def test_humanize_pitch_bend_meta():
    pattern = {
        "bpm": 145,
        "style": "opium rage ken carson",
        "user_prompt": "dark trap",
        "tracks": {
            "kick": [{"time_step": 0.0, "note": "C1", "length": 0.4, "velocity": 110}],
            "snare": [{"time_step": 1.0, "note": "D1", "length": 0.3, "velocity": 110}],
            "clap": [{"time_step": 1.0, "note": "D1", "length": 0.2, "velocity": 105}],
            "sub_808": [{"time_step": 0.0, "note": "C2", "length": 2.0, "velocity": 127}],
            "hi_hats": [{"time_step": 0.0, "note": "C5", "length": 0.25, "velocity": 100}],
            "melody_lead": [{"time_step": 0.0, "note": "A4", "length": 16.0, "velocity": 90}],
        },
    }
    out = humanize_pattern(pattern)
    assert out["tracks"]["snare_layer"]
    assert out.get("pitch_bend_automation")
    assert out["plg_producer_meta"].get("hat_db_down") == 6.0
