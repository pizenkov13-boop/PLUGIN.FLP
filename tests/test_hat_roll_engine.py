import random

from hat_roll_engine import inject_snare_hat_rolls, snare_hit_steps


def test_snare_fallback_beats_two_and_four():
    pattern = {"tracks": {"hi_hats": [], "snare": []}}
    steps = snare_hit_steps(pattern, bars=2)
    assert 1.0 in steps
    assert 3.0 in steps
    assert 5.0 in steps
    assert 7.0 in steps


def test_hat_roll_injects_before_snare():
    hats = [
        {"time_step": 0.5, "note": "C5", "length": 0.25, "velocity": 100},
        {"time_step": 0.75, "note": "C5", "length": 0.25, "velocity": 100},
    ]
    snare_steps = [1.0]
    rng = random.Random(7)
    out = inject_snare_hat_rolls(hats, snare_steps, rng, roll_depth=0.25)
    assert len(out) > len(hats)
    assert any(n.get("hat_roll") for n in out)
    assert max(n["time_step"] for n in out) < 1.0


def test_hat_roll_keeps_notes_outside_window():
    hats = [
        {"time_step": 0.0, "note": "C5", "length": 0.25, "velocity": 100},
        {"time_step": 2.0, "note": "C5", "length": 0.25, "velocity": 100},
    ]
    rng = random.Random(1)
    out = inject_snare_hat_rolls(hats, [1.0], rng)
    assert any(abs(n["time_step"] - 0.0) < 1e-4 for n in out)
    assert any(abs(n["time_step"] - 2.0) < 1e-4 for n in out)
