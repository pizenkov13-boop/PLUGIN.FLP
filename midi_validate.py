"""Validate PLG pattern JSON and exported MIDI (pretty_midi)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pattern_utils import TRACK_KEYS, parse_note_name, track_notes

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_PATTERN = PROJECT_DIR / "output_pattern.json"
DEFAULT_MIDI_DIR = PROJECT_DIR / "output_midi"
COMBINED_MIDI = DEFAULT_MIDI_DIR / "PLG_Beat.mid"


def expected_note_counts(data: dict[str, Any]) -> dict[str, int]:
    return {key: len(track_notes(data, key)) for key in TRACK_KEYS}


def validate_pattern(data: dict[str, Any]) -> list[str]:
    """Return human-readable warnings for pattern JSON."""
    warnings: list[str] = []

    bpm = data.get("bpm")
    if bpm is None:
        warnings.append("missing bpm")
    elif not isinstance(bpm, (int, float)) or bpm <= 0:
        warnings.append(f"invalid bpm: {bpm!r}")

    tracks = data.get("tracks")
    if not isinstance(tracks, dict):
        warnings.append("tracks missing or not an object")
        return warnings

    total = sum(expected_note_counts(data).values())
    if total == 0:
        warnings.append("no notes in any PLG track")

    for key in TRACK_KEYS:
        for index, note in enumerate(track_notes(data, key)):
            if not isinstance(note, dict):
                warnings.append(f"{key}[{index}] is not an object")
                continue
            for field in ("note", "time_step", "length", "velocity"):
                if field not in note:
                    warnings.append(f"{key}[{index}] missing {field}")
            if "note" in note:
                try:
                    parse_note_name(str(note["note"]))
                except (ValueError, TypeError):
                    warnings.append(f"{key}[{index}] bad note: {note.get('note')!r}")
            if "velocity" in note:
                try:
                    velocity = int(note["velocity"])
                    if not 0 <= velocity <= 127:
                        warnings.append(f"{key}[{index}] velocity out of range: {velocity}")
                except (TypeError, ValueError):
                    warnings.append(f"{key}[{index}] bad velocity: {note.get('velocity')!r}")

    return warnings


def validate_midi_file(path: Path, *, min_notes: int = 1) -> dict[str, Any]:
    """Inspect a .mid file; requires pretty_midi."""
    import pretty_midi

    midi_path = Path(path)
    if not midi_path.is_file():
        return {"path": str(midi_path), "ok": False, "error": "file not found"}

    try:
        score = pretty_midi.PrettyMIDI(str(midi_path))
    except Exception as exc:
        return {"path": str(midi_path), "ok": False, "error": str(exc)}

    note_count = sum(len(inst.notes) for inst in score.instruments)
    duration = score.get_end_time()
    estimated_bpm: float | None = None
    try:
        estimated_bpm = float(score.estimate_tempo())
    except Exception:
        pass

    return {
        "path": str(midi_path.resolve()),
        "instruments": len(score.instruments),
        "notes": note_count,
        "duration_sec": round(duration, 2),
        "estimated_bpm": round(estimated_bpm, 1) if estimated_bpm else None,
        "ok": note_count >= min_notes,
    }


def validate_export(
    pattern: dict[str, Any],
    midi_dir: Path = DEFAULT_MIDI_DIR,
    combined: Path = COMBINED_MIDI,
) -> dict[str, Any]:
    """Cross-check JSON note counts vs exported MIDI on disk."""
    json_warnings = validate_pattern(pattern)
    expected = expected_note_counts(pattern)
    expected_total = sum(expected.values())

    track_reports: dict[str, Any] = {}
    for key in TRACK_KEYS:
        track_path = midi_dir / f"{key}.mid"
        if expected[key] > 0 and track_path.is_file():
            track_reports[key] = validate_midi_file(track_path, min_notes=1)

    combined_report: dict[str, Any] | None = None
    if combined.is_file():
        combined_report = validate_midi_file(combined, min_notes=max(1, expected_total))

    midi_ok = True
    if expected_total > 0:
        if combined_report is None or not combined_report.get("ok"):
            midi_ok = False
        for key, count in expected.items():
            if count > 0:
                report = track_reports.get(key)
                if report is None or not report.get("ok"):
                    midi_ok = False

    return {
        "json_warnings": json_warnings,
        "expected_notes": expected,
        "tracks": track_reports,
        "combined": combined_report,
        "ok": not json_warnings and midi_ok,
    }


def log_validation_report(report: dict[str, Any]) -> None:
    expected = report.get("expected_notes") or {}
    logging.info(
        "Pattern notes: hi_hats=%s sub_808=%s melody=%s",
        expected.get("hi_hats", 0),
        expected.get("sub_808", 0),
        expected.get("melody_lead", 0),
    )
    for warning in report.get("json_warnings") or []:
        logging.warning("Pattern validation: %s", warning)

    combined = report.get("combined")
    if combined:
        logging.info(
            "MIDI %s: instruments=%s notes=%s duration=%ss bpm~%s",
            Path(combined["path"]).name,
            combined.get("instruments"),
            combined.get("notes"),
            combined.get("duration_sec"),
            combined.get("estimated_bpm"),
        )
        if combined.get("error"):
            logging.warning("MIDI validation: %s", combined["error"])

    if report.get("ok"):
        logging.info("Beat validation OK")
    else:
        logging.warning("Beat validation reported issues (see log above)")


def validate_on_disk(
    pattern_path: Path = DEFAULT_PATTERN,
    midi_dir: Path = DEFAULT_MIDI_DIR,
    combined: Path = COMBINED_MIDI,
) -> dict[str, Any]:
    data = json.loads(pattern_path.read_text(encoding="utf-8"))
    return validate_export(data, midi_dir=midi_dir, combined=combined)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    if not DEFAULT_PATTERN.is_file():
        raise SystemExit(f"No pattern at {DEFAULT_PATTERN} — run CREATE BEAT first.")
    result = validate_on_disk()
    log_validation_report(result)
    raise SystemExit(0 if result.get("ok") else 1)
