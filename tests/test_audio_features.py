import wave
from pathlib import Path

import numpy as np

from audio_features import (
    analyze,
    feature_match_score,
    target_from_prompt,
)
from sample_match import pick_best_for_track


def _sine_wav(path: Path, freq: float, ms: int = 500, sr: int = 44100, amp: float = 0.5) -> None:
    t = np.arange(int(sr * ms / 1000)) / sr
    x = (amp * np.sin(2 * np.pi * freq * t) * 32767).astype("<i2")
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(x.tobytes())


def test_analyze_brightness_orders_correctly(tmp_path: Path):
    bright = tmp_path / "bright.wav"
    dark = tmp_path / "dark.wav"
    _sine_wav(bright, 6000)
    _sine_wav(dark, 150)
    fb = analyze(bright)
    fd = analyze(dark)
    assert fb and fd
    assert fb["centroid"] > fd["centroid"]


def test_analyze_unreadable_returns_none(tmp_path: Path):
    bad = tmp_path / "bad.wav"
    bad.write_bytes(b"not a wav")
    assert analyze(bad) is None


def test_target_from_prompt_directions():
    assert target_from_prompt("dark deep 808", "", "sub_808").get("centroid") == "low"
    assert target_from_prompt("glassy bright bell", "", "melody_lead").get("centroid") == "high"


def test_feature_match_rewards_and_penalizes():
    bright = {"centroid": 6000.0}
    dark = {"centroid": 200.0}
    assert feature_match_score(bright, {"centroid": "high"}) > 0
    assert feature_match_score(dark, {"centroid": "high"}) < 0


def test_pick_hears_vibe_on_neutral_names(tmp_path: Path):
    (tmp_path / "melodies").mkdir()
    # aaa = dark (first in order), bbb = bright. Names carry zero vibe info.
    _sine_wav(tmp_path / "melodies" / "aaa.wav", 150)
    _sine_wav(tmp_path / "melodies" / "bbb.wav", 6000)
    catalog = {"audio": {"melodies": ["melodies/aaa.wav", "melodies/bbb.wav"]}}

    target = target_from_prompt("glassy bright bell", "", "melody_lead")
    path, _score = pick_best_for_track(
        catalog, "melody_lead", tmp_path, prompt="glassy bright bell", audio_target=target
    )
    # Name scores are equal and aaa comes first; only "hearing" flips it to bbb.
    assert path is not None and path.name == "bbb.wav"
