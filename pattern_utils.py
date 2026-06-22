"""Shared helpers for notes, build guides, and pattern stats."""

from __future__ import annotations

from typing import Any

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTE_ALIASES = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}
NOTE_INDEX = {name: idx for idx, name in enumerate(NOTE_NAMES)}
NOTE_INDEX.update({alias: NOTE_INDEX[mapped] for alias, mapped in NOTE_ALIASES.items()})

TRACK_KEYS = ("hi_hats", "sub_808", "melody_lead")
TRACK_LABELS = {
    "hi_hats": "1. Hi-Hats",
    "sub_808": "2. Sub 808",
    "melody_lead": "3. Melody / Lead",
}


def step_to_beats(time_step: float) -> float:
    """PLG grid: 1.0 time_step = one beat (0.25 = sixteenth)."""
    return float(time_step)


def step_to_ms(time_step: float, bpm: float) -> int:
    return int(step_to_beats(time_step) * (60_000.0 / bpm))


def parse_note_name(note_str: str) -> int:
    text = note_str.strip()
    if len(text) >= 3 and text[1] in "#b":
        pitch = text[:2]
        if pitch[1] == "b":
            pitch = NOTE_ALIASES.get(pitch[0] + "b", pitch)
        octave = int(text[2:])
    elif len(text) >= 2:
        pitch = text[0]
        octave = int(text[1:])
    else:
        raise ValueError(f"Invalid note: {note_str}")

    if pitch in NOTE_ALIASES:
        pitch = NOTE_ALIASES[pitch]
    if pitch not in NOTE_INDEX:
        raise ValueError(f"Unknown pitch: {pitch}")
    return octave * 12 + NOTE_INDEX[pitch]


def track_notes(data: dict[str, Any], track_key: str) -> list[dict[str, Any]]:
    tracks = data.get("tracks")
    if isinstance(tracks, dict) and track_key in tracks:
        return tracks[track_key]
    return []


def format_build_guide(data: dict[str, Any]) -> str:
    order = data.get("build_order") or list(TRACK_KEYS) + ["samples", "fx_automation", "vocal_fx"]
    lines = [
        f"PLG | BPM {data.get('bpm', '?')} | {data.get('style', 'unknown')}",
        f"Producer mode: Don Toliver / Opium FL workflow",
        "",
        "Build order:",
    ]

    step = 1
    for layer in order:
        if layer in TRACK_KEYS:
            count = len(track_notes(data, layer))
            lines.append(f"{step}. {TRACK_LABELS[layer]} -> {count} notes")
            step += 1
        elif layer == "samples" and data.get("samples"):
            lines.append(f"{step}. Load {len(data['samples'])} samples from library")
            step += 1
        elif layer == "fx_automation" and data.get("fx_automation"):
            lines.append(f"{step}. Apply FX on 808 channel")
            step += 1
        elif layer == "vocal_fx" and data.get("vocal_fx"):
            lines.append(f"{step}. Record vocals + apply vocal FX")
            step += 1

    refs = data.get("library_refs") or []
    if refs:
        lines.extend(["", "Library assets:"])
        for item in refs:
            lines.append(f"- [{item.get('type')}] {item.get('file')} — {item.get('note', '')}".rstrip(" —"))

    manual = data.get("manual_steps") or []
    if manual:
        lines.extend(["", "Manual:"])
        lines.extend(f"- {item}" for item in manual)

    if data.get("starter_mode"):
        workflow = (
            "Starter sounds are loaded in FL — press Play. "
            "Swap samples on PLG channels anytime for your sound."
        )
    else:
        workflow = "Don workflow: drag YOUR 808/hats/lead onto PLG channels → FX on 808 → Mixer F9"
    lines.extend([
        "",
        workflow,
        "FL: Piano roll -> Scripts -> PLG (Hat Roll, 808 Glide, Pan Spread)",
        "Full guide: FL_WORKFLOWS.md",
    ])
    return "\n".join(lines)
