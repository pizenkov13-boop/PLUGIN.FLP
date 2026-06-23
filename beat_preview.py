"""Instant in-app beat preview — render the pattern to audio before FL.

Takes the generated pattern + the chosen one-shot samples (plg_sound_paths) and
bakes a short stereo .wav so the user can hit Play and *hear* the beat in the
app, no DAW needed. Drums are scheduled on the grid; 808/melody one-shots are
pitch-shifted per note; notes are panned using the producer brain's pan data;
the master gets a gentle soft-clip. Pure numpy + pydub (reads WAV without
ffmpeg) + stdlib wave for output — light and PyInstaller-friendly.

Anything missing or unreadable is skipped or replaced by a synth tone, so a
preview always renders — even on an empty library (bundled starter sounds).
"""

from __future__ import annotations

import base64
import io
import logging
import wave
from pathlib import Path
from typing import Any

import numpy as np

from pattern_utils import parse_note_name, track_notes

logger = logging.getLogger("plg.preview")

SR = 32000
MAX_SECONDS = 20.0
BASE_MIDI = 60  # C5 in PLG naming — reference pitch for pitched one-shots
FADE_MS = 4

DRUM_TRACKS = ("kick", "snare", "snare_layer", "clap", "hi_hats")
PITCHED_TRACKS = ("sub_808", "melody_lead", "counter_melody")
TRACK_GAIN = {
    "kick": 1.0, "snare": 0.9, "snare_layer": 0.4, "clap": 0.8, "hi_hats": 0.5,
    "sub_808": 1.0, "melody_lead": 0.7, "counter_melody": 0.5,
}
_sample_cache: dict[str, np.ndarray] = {}


def _load_sample(path: str) -> np.ndarray | None:
    if path in _sample_cache:
        return _sample_cache[path]
    try:
        from pydub import AudioSegment

        seg = AudioSegment.from_file(path).set_channels(1).set_frame_rate(SR)
    except Exception as exc:
        logger.debug("preview load skip %s: %s", path, exc)
        return None
    data = np.asarray(seg.get_array_of_samples(), dtype=np.float64)
    if data.size == 0:
        return None
    data /= float(2 ** (8 * seg.sample_width - 1)) or 1.0
    _sample_cache[path] = data
    return data


def _pitch_shift(samples: np.ndarray, semitones: int) -> np.ndarray:
    if semitones == 0 or samples.size == 0:
        return samples
    factor = 2.0 ** (semitones / 12.0)
    new_len = max(1, int(samples.size / factor))
    idx = np.linspace(0, samples.size - 1, new_len)
    return np.interp(idx, np.arange(samples.size), samples)


def _synth_tone(midi: int, length_samples: int) -> np.ndarray:
    """Fallback saw tone with a quick ADSR when a track has no sample."""
    if length_samples <= 0:
        return np.zeros(0)
    freq = 440.0 * 2.0 ** ((midi - 69) / 12.0)
    t = np.arange(length_samples) / SR
    phase = (freq * t) % 1.0
    wave_out = 2.0 * phase - 1.0  # saw
    env = np.ones(length_samples)
    a = min(length_samples, int(0.005 * SR))
    r = min(length_samples, int(0.08 * SR))
    if a:
        env[:a] = np.linspace(0, 1, a)
    if r:
        env[-r:] *= np.linspace(1, 0, r)
    return wave_out * env * 0.5


def _fade(buf: np.ndarray) -> np.ndarray:
    n = min(len(buf), int(FADE_MS / 1000.0 * SR))
    if n > 1:
        buf = buf.copy()
        buf[:n] *= np.linspace(0, 1, n)
        buf[-n:] *= np.linspace(1, 0, n)
    return buf


def _pan_gains(pan: float) -> tuple[float, float]:
    theta = max(0.0, min(127.0, pan)) / 127.0 * (np.pi / 2.0)
    return float(np.cos(theta)), float(np.sin(theta))


def render_pattern(pattern: dict[str, Any]) -> np.ndarray:
    """Render the pattern to a stereo float buffer in [-1, 1]."""
    bpm = float(pattern.get("bpm", 140) or 140)
    spb = 60.0 / max(1.0, bpm)
    sound_paths = pattern.get("plg_sound_paths") or {}

    total_beats = 0.0
    for key in DRUM_TRACKS + PITCHED_TRACKS:
        for note in track_notes(pattern, key):
            total_beats = max(total_beats, float(note.get("time_step", 0)) + float(note.get("length", 0.25)))
    total_sec = min(MAX_SECONDS, total_beats * spb + 0.6)
    n = max(1, int(total_sec * SR))
    left = np.zeros(n)
    right = np.zeros(n)

    for key in DRUM_TRACKS + PITCHED_TRACKS:
        notes = track_notes(pattern, key)
        if not notes:
            continue
        base = _load_sample(str(sound_paths.get(key, ""))) if sound_paths.get(key) else None
        pitched = key in PITCHED_TRACKS
        track_gain = TRACK_GAIN.get(key, 0.7)

        for note in notes:
            start = int(float(note.get("time_step", 0)) * spb * SR)
            if start >= n:
                continue
            try:
                midi = parse_note_name(str(note.get("note", "C5")))
            except ValueError:
                midi = BASE_MIDI

            if base is not None:
                clip = _pitch_shift(base, midi - BASE_MIDI) if pitched else base
            elif pitched:
                length_samples = int(max(0.1, float(note.get("length", 0.5))) * spb * SR)
                clip = _synth_tone(midi, length_samples)
            else:
                continue

            clip = _fade(clip)
            gain = track_gain * (int(note.get("velocity", 100)) / 127.0)
            lg, rg = _pan_gains(float(note.get("pan", 64)))
            end = min(n, start + clip.size)
            seg = clip[: end - start]
            left[start:end] += seg * gain * lg
            right[start:end] += seg * gain * rg

    stereo = np.stack([left, right], axis=1)
    stereo = np.tanh(stereo * 1.1)  # gentle master soft-clip / glue
    peak = float(np.max(np.abs(stereo)))
    if peak > 1.0:
        stereo /= peak
    return stereo


def _to_wav_bytes(stereo: np.ndarray) -> bytes:
    pcm = (np.clip(stereo, -1.0, 1.0) * 32767.0).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "w") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def render_preview(pattern: dict[str, Any], out_path: Path | None = None) -> dict[str, Any]:
    """Render the pattern and return {ok, audio (data URI), seconds, path}."""
    stereo = render_pattern(pattern)
    seconds = round(stereo.shape[0] / SR, 2)
    wav_bytes = _to_wav_bytes(stereo)

    path_str = ""
    if out_path is not None:
        try:
            out_path.write_bytes(wav_bytes)
            path_str = str(out_path)
        except OSError as exc:
            logger.warning("preview write failed: %s", exc)

    b64 = base64.b64encode(wav_bytes).decode("ascii")
    return {
        "ok": True,
        "audio": f"data:audio/wav;base64,{b64}",
        "seconds": seconds,
        "path": path_str,
    }
