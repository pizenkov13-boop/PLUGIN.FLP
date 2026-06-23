"""Audio analysis for "hearing" sample selection (V2).

Listens to the actual waveform — spectral brightness (centroid), attack/decay
transient, grit (zero-crossing rate) and low fundamental (808 tone) — so the
picker matches the vibe a user asked for even when files are named garbage
(01.wav, final_v3.wav). Pure numpy + pydub; no librosa, so it stays light and
PyInstaller-friendly. pydub reads WAV without ffmpeg; anything unreadable
(e.g. mp3 with no ffmpeg) returns None and the name-based scorer takes over.

Features are cached by path+mtime+size so big libraries are analyzed once.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

from plg_paths import user_data_dir

logger = logging.getLogger("plg.audio")

CACHE_FILE = user_data_dir() / "audio_features.json"
ANALYZE_MS = 2000  # only the head of a file is needed for one-shots/loops

# (high_threshold, low_threshold) per feature, tuned for 44.1k one-shots.
THRESHOLDS = {
    "centroid": (3500.0, 1800.0),
    "zcr": (0.08, 0.03),
    "attack": (60.0, 15.0),   # ms — "low" = punchy
    "decay": (600.0, 150.0),  # ms — "low" = tight
    "pitch": (200.0, 120.0),  # Hz — "low" = deep sub
}

# descriptor family -> desired feature directions
FAMILY_TARGET: dict[str, dict[str, str]] = {
    "dark": {"centroid": "low"},
    "bright": {"centroid": "high"},
    "deep": {"centroid": "low", "pitch": "low"},
    "punchy": {"attack": "low", "decay": "low"},
    "hard": {"zcr": "high", "decay": "low"},
    "distorted": {"zcr": "high"},
    "clean": {"zcr": "low"},
    "vintage": {"centroid": "low"},
    "metallic": {"centroid": "high", "zcr": "high"},
}


def analyze(path: Path | str) -> dict[str, float] | None:
    """Extract features from a file head. Returns None if unreadable/silent."""
    try:
        from pydub import AudioSegment

        seg = AudioSegment.from_file(str(path))
    except Exception as exc:  # unreadable / no ffmpeg for mp3 — fall back to names
        logger.debug("audio analyze skip %s: %s", path, exc)
        return None
    if len(seg) == 0:
        return None

    seg = seg[:ANALYZE_MS].set_channels(1)
    sr = seg.frame_rate or 44100
    samples = np.asarray(seg.get_array_of_samples(), dtype=np.float64)
    if samples.size == 0:
        return None
    maxv = float(2 ** (8 * seg.sample_width - 1)) or 1.0
    x = samples / maxv

    env = np.abs(x)
    peak_i = int(np.argmax(env))
    peak = float(env[peak_i])
    if peak <= 1e-6:
        return None

    attack_ms = peak_i / sr * 1000.0
    after = env[peak_i:]
    below = np.where(after < 0.1 * peak)[0]
    decay_ms = float((below[0] if below.size else len(after)) / sr * 1000.0)

    window = x[: sr] if x.size > sr else x
    spec = np.abs(np.fft.rfft(window * np.hanning(len(window))))
    freqs = np.fft.rfftfreq(len(window), 1.0 / sr)
    spec_sum = float(spec.sum()) + 1e-9
    centroid = float((freqs * spec).sum() / spec_sum)

    band = (freqs >= 40.0) & (freqs <= 500.0)
    pitch = float(freqs[band][int(np.argmax(spec[band]))]) if band.any() and spec[band].size else 0.0

    zcr = float(np.mean(np.abs(np.diff(np.sign(x))) > 0)) if x.size > 1 else 0.0

    return {
        "duration_s": round(len(seg) / 1000.0, 3),
        "rms": round(float(np.sqrt(np.mean(x ** 2))), 5),
        "centroid": round(centroid, 1),
        "zcr": round(zcr, 4),
        "attack": round(attack_ms, 1),
        "decay": round(decay_ms, 1),
        "pitch": round(pitch, 1),
    }


_cache: dict[str, Any] | None = None


def _load_cache() -> dict[str, Any]:
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            _cache = {}
    return _cache


def _save_cache() -> None:
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(_load_cache()), encoding="utf-8")
    except OSError:
        pass


def analyze_cached(path: Path | str) -> dict[str, float] | None:
    """analyze() with a path+mtime+size cache so libraries are scanned once."""
    p = Path(path)
    try:
        st = p.stat()
    except OSError:
        return None
    key = f"{p}:{int(st.st_mtime)}:{st.st_size}"
    cache = _load_cache()
    if key in cache:
        return cache[key]
    feats = analyze(p)
    cache[key] = feats
    _save_cache()
    return feats


def target_from_prompt(prompt: str = "", style: str = "", track: str | None = None) -> dict[str, str]:
    """Desired feature directions from the prompt's descriptor families."""
    from sound_descriptors import DESCRIPTOR_FAMILIES

    text = f"{prompt} {style}".lower()
    target: dict[str, str] = {}
    for family, (triggers, _hints, tracks) in DESCRIPTOR_FAMILIES.items():
        if family not in FAMILY_TARGET:
            continue
        if track is not None and tracks and track not in tracks:
            continue
        if any(trig in text for trig in triggers):
            target.update(FAMILY_TARGET[family])
    return target


def feature_match_score(features: dict[str, float] | None, target: dict[str, str]) -> int:
    """+12 per feature matching the wanted direction, -6 for the opposite."""
    if not features or not target:
        return 0
    score = 0
    for feature, want in target.items():
        value = features.get(feature)
        if value is None or feature not in THRESHOLDS:
            continue
        high, low = THRESHOLDS[feature]
        if want == "high":
            score += 12 if value >= high else (-6 if value <= low else 0)
        else:  # "low"
            score += 12 if value <= low else (-6 if value >= high else 0)
    return score
