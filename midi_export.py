"""Export PLG pattern JSON to per-track MIDI files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from midiutil import MIDIFile

from pattern_utils import TRACK_KEYS, parse_note_name, track_notes

PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output_midi"
DEFAULT_JSON = PROJECT_DIR / "output_pattern.json"


def _steps_to_beats(steps: float) -> float:
    return float(steps) / 4.0


def export_track(
    midi: MIDIFile,
    track_index: int,
    notes: list[dict[str, Any]],
    channel: int,
) -> None:
    for entry in notes:
        pitch = parse_note_name(entry["note"])
        start = _steps_to_beats(entry["time_step"])
        duration = max(0.05, _steps_to_beats(entry["length"]))
        velocity = int(entry.get("velocity", 100))
        midi.addNote(track_index, channel, pitch, start, duration, velocity)


def export_pattern_to_midi(
    data: dict[str, Any],
    output_dir: Path = OUTPUT_DIR,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    bpm = float(data.get("bpm", 120))
    written: list[Path] = []

    for track_key in TRACK_KEYS:
        notes = track_notes(data, track_key)
        if not notes:
            continue

        midi = MIDIFile(1)
        midi.addTempo(0, 0, bpm)
        export_track(midi, 0, notes, 0)

        out_path = output_dir / f"{track_key}.mid"
        with out_path.open("wb") as handle:
            midi.writeFile(handle)
        written.append(out_path)

    return written


def export_from_json(json_path: Path = DEFAULT_JSON, output_dir: Path = OUTPUT_DIR) -> list[Path]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return export_pattern_to_midi(data, output_dir)
