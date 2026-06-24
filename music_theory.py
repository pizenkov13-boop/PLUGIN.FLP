"""Key detection + dark-scale quantization (Rule 11 / Rule 18).

Pure, dependency-light music theory the producer brain uses to lock melodies
and 808s to an underground minor palette — instead of blindly flattening every
E and B regardless of key (the old heuristic broke any non-C-ish song).
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from pattern_utils import NOTE_NAMES, parse_note_name

# Semitone offsets from the root. Dark / rage palette = natural minor + phrygian.
SCALES: dict[str, tuple[int, ...]] = {
    "natural_minor": (0, 2, 3, 5, 7, 8, 10),
    "phrygian": (0, 1, 3, 5, 7, 8, 10),
    "major": (0, 2, 4, 5, 7, 9, 11),
    "dorian": (0, 2, 3, 5, 7, 9, 10),
    "lydian": (0, 2, 4, 6, 7, 9, 11),
    "locrian": (0, 1, 3, 5, 6, 8, 10),
}
_SCALE_QUALITY = {
    "natural_minor": "minor",
    "phrygian": "phrygian",
    "major": "major",
    "dorian": "dorian",
    "lydian": "lydian",
    "locrian": "locrian",
}
DEFAULT_ROOT_PC = 9  # A — PLG's home key when nothing can be detected


def _safe_midi(note: str) -> int | None:
    try:
        return parse_note_name(note)
    except ValueError:
        return None


def detect_root_pc(notes: list[dict[str, Any]], *, default: int = DEFAULT_ROOT_PC) -> int:
    """Most prominent pitch class, weighted by note length × velocity."""
    weights: Counter[int] = Counter()
    for entry in notes:
        midi = _safe_midi(str(entry.get("note", "")))
        if midi is None:
            continue
        weight = max(1.0, float(entry.get("length", 0.25))) * max(1, int(entry.get("velocity", 100)))
        weights[midi % 12] += weight
    if not weights:
        return default % 12
    # Highest weight wins; ties resolve to the lower pitch class (darker root).
    return max(weights.items(), key=lambda kv: (kv[1], -kv[0]))[0]


def snap_pc_to_scale(midi: int, root_pc: int, scale: str = "natural_minor") -> int:
    """Snap a MIDI note into the scale; ties resolve downward (darker)."""
    intervals = SCALES.get(scale, SCALES["natural_minor"])
    scale_pcs = {(root_pc + i) % 12 for i in intervals}
    pc = midi % 12
    if pc in scale_pcs:
        return midi
    for dist in range(1, 7):
        if (pc - dist) % 12 in scale_pcs:
            return midi - dist
        if (pc + dist) % 12 in scale_pcs:
            return midi + dist
    return midi


def name_for_midi(midi: int) -> str:
    return f"{NOTE_NAMES[midi % 12]}{midi // 12}"


def key_label(root_pc: int, scale: str = "natural_minor") -> str:
    quality = _SCALE_QUALITY.get(scale, "minor")
    return f"{NOTE_NAMES[root_pc % 12]} {quality}"
