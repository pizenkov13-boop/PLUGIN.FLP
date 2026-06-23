"""Ingest user .mid files from the library so their notes actually play.

Moves MIDI from a build-guide reference (Tier 2) to a real, played part
(Tier 1): the best-matching .mid in the library is parsed and merged into the
pattern (high notes → melody, low notes → 808), then humanize_pattern key-locks
it like everything else.

Beat-relative and tempo-agnostic: reads ticks / ticks_per_beat, so the loop
lines up at any BPM. Only fires when a .mid name matches the prompt or the user
explicitly asks for MIDI — otherwise the LLM melody is left untouched.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import mido

from music_theory import name_for_midi
from pattern_utils import parse_note_name, track_notes

logger = logging.getLogger("plg.midi_ingest")

REGISTER_SPLIT = 48  # MIDI C3 — below = 808/bass, at/above = melody
MAX_BEATS = 64.0
MIDI_EXTS = (".mid", ".midi")
_EXPLICIT = ("midi", "миди", "мелодию из", "из миди", "loop", "луп")


def read_midi_notes(path: Path, *, max_beats: float = MAX_BEATS) -> list[dict[str, Any]]:
    """Parse a .mid into PLG notes (time_step + length in beats)."""
    try:
        mid = mido.MidiFile(str(path))
    except Exception as exc:  # malformed MIDI — skip, never crash a generation
        logger.warning("MIDI read failed %s: %s", path.name, exc)
        return []

    tpb = mid.ticks_per_beat or 480
    notes: list[dict[str, Any]] = []
    for track in mid.tracks:
        abs_tick = 0
        active: dict[tuple[int, int], tuple[int, int]] = {}
        for msg in track:
            abs_tick += msg.time
            if msg.type == "note_on" and msg.velocity > 0:
                active[(msg.channel, msg.note)] = (abs_tick, msg.velocity)
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                start = active.pop((msg.channel, msg.note), None)
                if start is None:
                    continue
                start_tick, vel = start
                start_beat = start_tick / tpb
                if start_beat >= max_beats:
                    continue
                length_beat = max(0.0625, (abs_tick - start_tick) / tpb)
                notes.append({
                    "time_step": round(start_beat, 5),
                    "note": name_for_midi(msg.note),
                    "length": round(length_beat, 5),
                    "velocity": max(1, min(127, int(vel))),
                    "midi": True,
                })
    notes.sort(key=lambda n: (n["time_step"], n["note"]))
    return notes


def split_by_register(
    notes: list[dict[str, Any]],
    split: int = REGISTER_SPLIT,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split notes into (melody, bass) by pitch."""
    melody: list[dict[str, Any]] = []
    bass: list[dict[str, Any]] = []
    for note in notes:
        try:
            midi = parse_note_name(str(note["note"]))
        except (ValueError, KeyError):
            melody.append(note)
            continue
        (bass if midi < split else melody).append(note)
    return melody, bass


def find_library_midi(library_root: Path) -> list[Path]:
    found: set[Path] = set()
    for ext in MIDI_EXTS:
        found.update(p for p in library_root.rglob(f"*{ext}") if p.is_file())
    return sorted(found)


def _score_name(path: Path, tokens: set[str]) -> int:
    name = path.stem.lower()
    return sum(1 for token in tokens if token and token in name)


def pick_library_midi(library_root: Path, prompt: str = "", style: str = "") -> Path | None:
    """Best .mid for the prompt, or None when nothing matches (LLM melody kept)."""
    candidates = find_library_midi(library_root)
    if not candidates:
        return None
    from sound_descriptors import descriptor_hints

    text = f"{prompt} {style}".lower()
    tokens = set(re.findall(r"[a-z0-9]{3,}", text))
    tokens |= set(descriptor_hints(prompt, style, track="melody_lead"))
    best = max(candidates, key=lambda p: _score_name(p, tokens))
    if _score_name(best, tokens) > 0 or any(k in text for k in _EXPLICIT):
        return best
    return None


def ingest_library_midi(
    pattern: dict[str, Any],
    *,
    library_root: Path | str,
    prompt: str = "",
    style: str = "",
) -> bool:
    """Play the best-matching library .mid as the melody (and 808 if low notes)."""
    root = Path(library_root)
    if not root.is_dir():
        return False
    midi_path = pick_library_midi(root, prompt, style)
    if midi_path is None:
        return False
    notes = read_midi_notes(midi_path)
    if not notes:
        return False

    melody, bass = split_by_register(notes)
    tracks = pattern.setdefault("tracks", {})
    if not isinstance(tracks, dict):
        return False

    if melody:
        tracks["melody_lead"] = melody
    elif bass:
        tracks["melody_lead"] = bass  # bass-only midi → use it as the lead
        bass = []
    if bass and not track_notes(pattern, "sub_808"):
        tracks["sub_808"] = bass

    pattern["plg_midi_ingest"] = {
        "source": str(midi_path),
        "name": midi_path.name,
        "notes": len(notes),
        "melody_notes": len(melody),
        "bass_notes": len(bass),
    }
    steps = list(pattern.get("manual_steps") or [])
    steps.insert(0, f"MIDI ingest: played {midi_path.name} ({len(notes)} notes) from your library.")
    pattern["manual_steps"] = steps[:16]
    logger.info("MIDI ingest: %s (%s notes)", midi_path.name, len(notes))
    return True
