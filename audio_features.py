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


def _features_from_array(x: np.ndarray, sr: int, duration_s: float) -> dict[str, float] | None:
    if x.size == 0:
        return None

    env = np.abs(x)
    peak_i = int(np.argmax(env))
    peak = float(env[peak_i])
    if peak <= 1e-6:
        return None

    attack_ms = peak_i / sr * 1000.0
    after = env[peak_i:]
    below = np.where(after < 0.1 * peak)[0]
    decay_ms = float((below[0] if below.size else len(after)) / sr * 1000.0)

    window = x[:sr] if x.size > sr else x
    spec = np.abs(np.fft.rfft(window * np.hanning(len(window))))
    freqs = np.fft.rfftfreq(len(window), 1.0 / sr)
    spec_sum = float(spec.sum()) + 1e-9
    centroid = float((freqs * spec).sum() / spec_sum)

    band = (freqs >= 40.0) & (freqs <= 500.0)
    pitch = float(freqs[band][int(np.argmax(spec[band]))]) if band.any() and spec[band].size else 0.0

    zcr = float(np.mean(np.abs(np.diff(np.sign(x))) > 0)) if x.size > 1 else 0.0

    return {
        "duration_s": round(duration_s, 3),
        "rms": round(float(np.sqrt(np.mean(x ** 2))), 5),
        "centroid": round(centroid, 1),
        "zcr": round(zcr, 4),
        "attack": round(attack_ms, 1),
        "decay": round(decay_ms, 1),
        "pitch": round(pitch, 1),
    }


def _load_wav_samples(path: Path, *, max_ms: int = ANALYZE_MS) -> tuple[np.ndarray, int, float] | None:
    """Read WAV via stdlib wave — no ffmpeg/ffprobe dependency."""
    import wave

    try:
        with wave.open(str(path), "rb") as wf:
            sr = wf.getframerate()
            channels = wf.getnchannels()
            width = wf.getsampwidth()
            if sr <= 0 or channels <= 0 or width not in (1, 2, 3, 4):
                return None
            max_frames = max(1, int(sr * max_ms / 1000))
            raw = wf.readframes(max_frames)
            total_frames = wf.getnframes()
    except (wave.Error, EOFError, OSError, ValueError):
        return None

    if not raw:
        return None

    if width == 1:
        samples = np.frombuffer(raw, dtype=np.uint8).astype(np.float64)
        samples = (samples - 128.0) / 128.0
    elif width == 2:
        samples = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    elif width == 3:
        # 24-bit little-endian packed samples
        arr = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        ints = (
            arr[:, 0].astype(np.int32)
            | (arr[:, 1].astype(np.int32) << 8)
            | (arr[:, 2].astype(np.int32) << 16)
        )
        ints = np.where(ints >= 2**23, ints - 2**24, ints)
        samples = ints.astype(np.float64) / float(2**23)
    else:
        samples = np.frombuffer(raw, dtype="<i4").astype(np.float64) / float(2**31)

    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)

    duration_s = total_frames / sr
    return samples, sr, duration_s


def _load_pydub_samples(path: Path, *, max_ms: int = ANALYZE_MS) -> tuple[np.ndarray, int, float] | None:
    try:
        from pydub import AudioSegment

        seg = AudioSegment.from_file(str(path))
    except Exception as exc:  # unreadable / no ffmpeg for mp3 — fall back to names
        logger.debug("audio analyze skip %s: %s", path, exc)
        return None
    if len(seg) == 0:
        return None

    seg = seg[:max_ms].set_channels(1)
    sr = seg.frame_rate or 44100
    samples = np.asarray(seg.get_array_of_samples(), dtype=np.float64)
    if samples.size == 0:
        return None
    maxv = float(2 ** (8 * seg.sample_width - 1)) or 1.0
    x = samples / maxv
    return x, sr, len(seg) / 1000.0


def analyze(path: Path | str) -> dict[str, float] | None:
    """Extract features from a file head. Returns None if unreadable/silent."""
    p = Path(path)
    loaded: tuple[np.ndarray, int, float] | None = None
    if p.suffix.lower() == ".wav":
        loaded = _load_wav_samples(p)
    else:
        loaded = _load_pydub_samples(p)
    if loaded is None:
        return None
    x, sr, duration_s = loaded
    return _features_from_array(x, sr, duration_s)


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
