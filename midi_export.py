"""Export PLG pattern JSON to per-track MIDI files (Stem Export Mixer)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from midiutil import MIDIFile

from mix_blueprint import session_slug
from pattern_utils import CHANNEL_NAMES, TRACK_KEYS, parse_note_name, step_to_beats, track_notes

# 960 pulses-per-quarter — atomic timing so humanize micro-shifts (swing, melody
# groove-lag, 808 attack) survive export instead of snapping to a coarse grid.
PPQ = 960

PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output_midi"
DEFAULT_JSON = PROJECT_DIR / "output_pattern.json"
COMBINED_MIDI = OUTPUT_DIR / "PLG_Beat.mid"

TRACK_EXPORT_NAMES = {key: CHANNEL_NAMES.get(key, key) for key in TRACK_KEYS}

# Friendly drag-and-drop names for FL mixer channels
STEM_FILENAMES = {
    "kick": "Kick.mid",
    "snare": "Snare.mid",
    "snare_layer": "Snare_Layer.mid",
    "clap": "Clap.mid",
    "sub_808": "808_Bass.mid",
    "hi_hats": "HiHats.mid",
    "melody_lead": "Melody.mid",
    "counter_melody": "Counter_Melody.mid",
}


def _steps_to_beats(steps: float) -> float:
    return step_to_beats(steps)


def export_track(
    midi: MIDIFile,
    track_index: int,
    notes: list[dict[str, Any]],
    channel: int,
    *,
    bpm: float = 120.0,
) -> None:
    for entry in notes:
        pitch = parse_note_name(entry["note"])
        start = _steps_to_beats(entry["time_step"])
        duration = max(0.05, _steps_to_beats(entry["length"]))
        velocity = int(entry.get("velocity", 100))
        midi.addNote(track_index, channel, pitch, start, duration, velocity)
        if "pan" in entry:
            pan = max(0, min(127, int(entry["pan"])))
            midi.addControllerEvent(track_index, channel, start, 10, pan)


def _export_pitch_bends(
    midi: MIDIFile,
    track_index: int,
    channel: int,
    events: list[dict[str, Any]],
    *,
    track_key: str,
) -> None:
    for event in events:
        if event.get("track") not in (track_key, None):
            continue
        when = _steps_to_beats(float(event.get("time_step", 0)))
        value = int(event.get("value", 8192))
        # MIDIUtil signature is (track, channel, time, value) — channel before time.
        midi.addPitchWheelEvent(track_index, channel, when, max(0, min(16383, value)))


def export_pattern_to_midi(
    data: dict[str, Any],
    output_dir: Path = OUTPUT_DIR,
    *,
    friendly_names: bool = False,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    bpm = float(data.get("bpm", 120))
    written: list[Path] = []

    for track_key in TRACK_KEYS:
        notes = track_notes(data, track_key)
        if not notes:
            continue

        midi = MIDIFile(1, ticks_per_quarternote=PPQ)
        midi.addTempo(0, 0, bpm)
        export_track(midi, 0, notes, 0, bpm=bpm)
        bends = data.get("pitch_bend_automation") or []
        if bends and track_key == "melody_lead":
            _export_pitch_bends(midi, 0, 0, bends, track_key=track_key)

        filename = STEM_FILENAMES.get(track_key, f"{track_key}.mid") if friendly_names else f"{track_key}.mid"
        out_path = output_dir / filename
        with out_path.open("wb") as handle:
            midi.writeFile(handle)
        written.append(out_path)

    return written


def _stems_readme(session_dir: Path, files: list[Path]) -> None:
    lines = [
        "PLG Stem Export Mixer",
        "=====================",
        "",
        "Drag each .mid onto its own FL mixer channel:",
        "",
    ]
    for path in sorted(files):
        if path.name == "PLG_Beat.mid":
            continue
        lines.append(f"  {path.name}")
    lines.extend([
        "",
        "Combined: PLG_Beat.mid (all tracks in one file)",
        "Mixing guide: READ_ME_IMBA.txt (project root)",
        "",
    ])
    (session_dir / "_DRAG_TO_MIXER.txt").write_text("\n".join(lines), encoding="utf-8")


def export_stem_session(
    data: dict[str, Any],
    base_dir: Path = OUTPUT_DIR,
) -> dict[str, Any]:
    """Export a session folder with separated stems + combined MIDI."""
    session_name = session_slug(data)
    session_dir = base_dir / session_name
    session_dir.mkdir(parents=True, exist_ok=True)

    stems = export_pattern_to_midi(data, session_dir, friendly_names=True)
    combined = export_combined_midi(data, session_dir / "PLG_Beat.mid")
    manifest = {
        "session": session_name,
        "bpm": data.get("bpm"),
        "style": data.get("style"),
        "stems": [p.name for p in stems],
        "combined": combined.name,
    }
    (session_dir / "stems_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _stems_readme(session_dir, stems + [combined])

    return {
        "session_dir": session_dir,
        "session_name": session_name,
        "stem_paths": stems,
        "combined_path": combined,
        "manifest_path": session_dir / "stems_manifest.json",
    }


def export_combined_midi(
    data: dict[str, Any],
    output_path: Path = COMBINED_MIDI,
) -> Path:
    """Single multi-track MIDI for FL Studio import."""
    tracks = [(key, track_notes(data, key)) for key in TRACK_KEYS if track_notes(data, key)]
    if not tracks:
        raise ValueError("No MIDI notes to export.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpm = float(data.get("bpm", 120))
    midi = MIDIFile(len(tracks), ticks_per_quarternote=PPQ)

    for track_index, (track_key, notes) in enumerate(tracks):
        midi.addTrackName(track_index, 0, TRACK_EXPORT_NAMES.get(track_key, track_key))
        midi.addTempo(track_index, 0, bpm)
        export_track(midi, track_index, notes, track_index, bpm=bpm)
        bends = data.get("pitch_bend_automation") or []
        if bends and track_key == "melody_lead":
            _export_pitch_bends(midi, track_index, track_index, bends, track_key=track_key)

    with output_path.open("wb") as handle:
        midi.writeFile(handle)
    return output_path


def export_from_json(json_path: Path = DEFAULT_JSON, output_dir: Path = OUTPUT_DIR) -> dict[str, Any]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    session = export_stem_session(data, output_dir)
    # Legacy flat export (latest stems also at output_midi root)
    export_pattern_to_midi(data, output_dir, friendly_names=True)
    export_combined_midi(data, output_dir / "PLG_Beat.mid")
    return session
