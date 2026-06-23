import random

from beat_humanize import (
    align_808_to_key,
    apply_open_hat_choke,
    apply_pre_snare_shift,
    apply_six_db_hat_rule,
    apply_velocity_sine_curve,
    build_pitch_bend_automation,
    darken_melody_intervals,
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


def test_darken_snaps_major_third_to_minor():
    # Melody clearly rooted on A; the C# major third must darken to C.
    notes = [
        {"time_step": 0.0, "note": "A4", "length": 4.0, "velocity": 120},
        {"time_step": 1.0, "note": "C#5", "length": 0.5, "velocity": 100},
    ]
    out = darken_melody_intervals(notes, scale="natural_minor")
    names = [n["note"] for n in out]
    assert names[0] == "A4"
    assert "C#5" not in names


def test_align_808_matches_melody_key():
    bass = [{"time_step": 0.0, "note": "C2", "length": 2.0, "velocity": 127}]
    melody = [{"time_step": 0.0, "note": "A4", "length": 4.0, "velocity": 120}]
    out = align_808_to_key(bass, melody)
    assert out[0]["note"] == "A1"  # C2 -> nearest A is down 3 semitones
    assert out[0]["key_matched"] is True


def test_align_808_noop_without_melody():
    bass = [{"time_step": 0.0, "note": "C2", "length": 2.0, "velocity": 127}]
    assert align_808_to_key(bass, []) == bass


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
