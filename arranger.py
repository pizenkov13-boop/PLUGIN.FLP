"""Arrange a short core loop into a full song — the length/structure fix.

LLMs reliably write only a few bars, so PLG generates a strong CORE and then
deterministically develops it across a real arrangement: Intro / Verse /
Chorus(drop) / Outro. Each section gates which tracks play, so the song breathes
(intro = melody only, verse adds drums+808, chorus = full wall, outro
winds down). Each track tiles by its own loop length, so a 1-bar drum loop
repeats every bar while a 4-bar melody repeats every 4 bars.

Runs before humanize, so swing / hat-rolls / drop-tension / register layout all
apply across the whole song. The result is one long pattern whose notes span the
full timeline — FL plays the entire song on open (no playlist surgery needed).
"""

from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

from pattern_utils import TRACK_KEYS, track_notes

BEATS_PER_BAR = 4.0

# (section name, bars, tracks that play). ~48 bars of real structure.
DEFAULT_SECTIONS: tuple[tuple[str, int, tuple[str, ...]], ...] = (
    ("intro", 8, ("melody_lead",)),
    # Verse stays sparse: clap + steady hats + 808, NO snare. Because hat rolls
    # and the layered accent snare key off snare hits, dropping snare here means
    # the verse automatically plays clean while the chorus gets the full wall.
    ("verse", 16, ("melody_lead", "hi_hats", "clap", "sub_808")),
    ("chorus", 16, TRACK_KEYS),  # full wall — kick + snare + rolls + layers drop in here
    ("outro", 8, ("melody_lead", "hi_hats")),
)


def _track_core_beats(notes: list[dict[str, Any]]) -> float:
    maxend = 0.0
    for entry in notes:
        maxend = max(maxend, float(entry.get("time_step", 0)) + float(entry.get("length", 0.25)))
    bars = max(1, math.ceil(maxend / BEATS_PER_BAR)) if maxend > 0 else 1
    return bars * BEATS_PER_BAR


def _tile(
    core_notes: list[dict[str, Any]],
    start_beat: float,
    length_beats: float,
    core_beats: float,
    section: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    offset = 0.0
    while offset < length_beats - 1e-6:
        for entry in core_notes:
            step = float(entry.get("time_step", 0))
            if step >= core_beats:
                continue
            placed = offset + step
            if placed >= length_beats - 1e-6:
                continue
            note = deepcopy(entry)
            note["time_step"] = round(start_beat + placed, 5)
            note["section"] = section  # downstream dynamics key off this
            out.append(note)
        offset += core_beats
    return out


def arrange_song(
    pattern: dict[str, Any],
    *,
    sections: tuple[tuple[str, int, tuple[str, ...]], ...] = DEFAULT_SECTIONS,
) -> dict[str, Any]:
    """Develop the core loop into a full multi-section song (in place)."""
    tracks = pattern.get("tracks")
    if not isinstance(tracks, dict):
        return pattern

    core = {key: [deepcopy(n) for n in track_notes(pattern, key)] for key in TRACK_KEYS}
    if not any(core.values()):
        return pattern

    core_beats = {key: _track_core_beats(notes) for key, notes in core.items() if notes}

    new_tracks: dict[str, list[dict[str, Any]]] = {key: [] for key in TRACK_KEYS}
    bar_cursor = 0
    arrangement: list[dict[str, Any]] = []

    for name, bars, gated in sections:
        start_beat = bar_cursor * BEATS_PER_BAR
        length_beats = bars * BEATS_PER_BAR
        for key in gated:
            if core.get(key):
                new_tracks[key].extend(_tile(core[key], start_beat, length_beats, core_beats[key], name))
        arrangement.append({"name": name, "start_bar": bar_cursor, "bars": bars})
        bar_cursor += bars

    pattern["tracks"] = {key: notes for key, notes in new_tracks.items() if notes}
    pattern["plg_arrangement"] = arrangement
    pattern["plg_total_bars"] = bar_cursor
    return pattern
