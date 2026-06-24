"""Markov hats, kick syncopation, snare riser, new presets, mastering math, JSON."""

from __future__ import annotations

import random
from pathlib import Path

from beat_humanize import add_kick_syncopation, apply_markov_hat_dynamics, build_snare_riser
from genre_profiles import PROFILES, detect_genre, profile_for
from mix_blueprint import build_mix_blueprint


# --- Markov hat dynamics ----------------------------------------------------

def test_markov_hats_vary_and_tag():
    rng = random.Random(11)
    hats = [{"time_step": i * 0.5, "note": "C5", "velocity": 100} for i in range(16)]
    out = apply_markov_hat_dynamics(hats, rng)
    states = {n["hat_state"] for n in out}
    assert states <= {"ghost", "normal", "accent"}
    assert len({n["velocity"] for n in out}) >= 2  # not a monotone machine-gun


def test_markov_hats_preserve_rolls():
    rng = random.Random(1)
    hats = [{"time_step": 0.0, "note": "C5", "velocity": 120, "hat_roll": True}]
    out = apply_markov_hat_dynamics(hats, rng)
    assert out[0]["velocity"] == 120  # roll ramp untouched
    assert "hat_state" not in out[0]


# --- Kick syncopation -------------------------------------------------------

def test_kick_syncopation_avoids_clap_and_adds():
    rng = random.Random(5)
    kicks = [{"time_step": float(bar * 4), "note": "C1", "velocity": 115} for bar in range(2)]
    out = add_kick_syncopation(kicks, bars=2, rng=rng, prob=1.0)
    assert len(out) > len(kicks)
    for n in out:
        # never on the clap (beat 3 = offset 2.0 in the bar)
        assert abs((n["time_step"] % 4.0) - 2.0) > 0.15
    assert any(n.get("kick_sync") for n in out)


def test_kick_syncopation_zero_is_noop():
    out = add_kick_syncopation([{"time_step": 0.0, "note": "C1"}], bars=4, rng=random.Random(0), prob=0.0)
    assert len(out) == 1


# --- Snare riser ------------------------------------------------------------

def test_snare_riser_accelerates_before_drop():
    risers = build_snare_riser(32.0)  # one 8-bar phrase (32 beats)
    assert len(risers) == 1 + 2 + 4 + 8  # 1/4 → 1/8 → 1/16 → 1/32 across the last bar
    assert all(28.0 <= n["time_step"] < 32.0 for n in risers)  # last bar only
    assert risers[0]["velocity"] < risers[-1]["velocity"]      # rising build
    assert risers[-1]["pitch_up"] >= risers[0]["pitch_up"]     # pitch-up hint climbs


# --- New presets ------------------------------------------------------------

def test_new_presets_detected():
    assert detect_genre(prompt="martin garrix festival edm") == "garrix"
    assert detect_genre(prompt="dua lipa nu-disco") == "dualipa"
    assert detect_genre(prompt="the weeknd dark pop") == "weeknd"


def test_new_preset_knobs():
    assert profile_for(prompt="garrix big room").snare_riser is True
    assert profile_for(prompt="weeknd").melody_scale == "dorian"
    assert profile_for(prompt="weeknd").voicing_spread > 0
    assert profile_for(prompt="dua lipa").kick_syncopation > 0


# --- Mastering math in the guide -------------------------------------------

def test_mix_blueprint_has_mastering_numbers():
    text = build_mix_blueprint({"bpm": 160, "style": "opium rage"})
    assert "Ceiling -1.0" in text
    assert "LUFS" in text
    assert "Sidechain" in text
    # reverb math from BPM: beat = 60000/160 = 375.0 ms, pre-delay 1/16 = 93.8 ms
    assert "375.0 ms" in text and "93.8 ms" in text


# --- Cloud JSON externalization --------------------------------------------

def test_genre_profiles_json_present_and_loaded():
    path = Path(__file__).resolve().parents[1] / "assets" / "genre_profiles.json"
    assert path.is_file()
    assert "opium" in PROFILES and PROFILES["opium"].markov_hats is True
