"""Default MIDI for kick / snare / clap when the LLM omits drum lanes."""

from __future__ import annotations

from typing import Any


def _bar_count(pattern: dict[str, Any], *, default: int = 4) -> int:
    tracks = pattern.get("tracks")
    if not isinstance(tracks, dict):
        return default

    max_step = 0.0
    for notes in tracks.values():
        if not isinstance(notes, list):
            continue
        for entry in notes:
            if isinstance(entry, dict):
                max_step = max(max_step, float(entry.get("time_step", 0)))
    if max_step <= 0:
        return default
    return max(default, int(max_step // 4) + 1)


def _kick_pattern(bars: int) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    for bar in range(bars):
        base = bar * 4.0
        notes.append({"time_step": base + 0.0, "note": "C1", "length": 0.45, "velocity": 112})
        notes.append({"time_step": base + 2.0, "note": "C1", "length": 0.45, "velocity": 108})
    return notes


def _snare_pattern(bars: int) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    for bar in range(bars):
        base = bar * 4.0
        notes.append({"time_step": base + 1.0, "note": "D1", "length": 0.35, "velocity": 108})
        notes.append({"time_step": base + 3.0, "note": "D1", "length": 0.35, "velocity": 104})
    return notes


def _clap_pattern(bars: int) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    for bar in range(bars):
        base = bar * 4.0
        notes.append({"time_step": base + 1.0, "note": "E1", "length": 0.25, "velocity": 92})
        notes.append({"time_step": base + 3.0, "note": "E1", "length": 0.25, "velocity": 88})
    return notes


def ensure_drum_tracks(pattern: dict[str, Any]) -> None:
    """Fill kick/snare/clap MIDI if the model returned only hats/808/melody."""
    tracks = pattern.setdefault("tracks", {})
    if not isinstance(tracks, dict):
        pattern["tracks"] = tracks = {}

    bars = _bar_count(pattern)
    if not tracks.get("kick"):
        tracks["kick"] = _kick_pattern(bars)
    if not tracks.get("snare"):
        tracks["snare"] = _snare_pattern(bars)
    if not tracks.get("clap"):
        tracks["clap"] = _clap_pattern(bars)

    order = pattern.get("build_order")
    if not isinstance(order, list) or not order:
        from pattern_utils import DEFAULT_BUILD_ORDER

        pattern["build_order"] = list(DEFAULT_BUILD_ORDER)
