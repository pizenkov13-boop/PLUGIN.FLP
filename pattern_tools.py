"""Fast pattern mutations — no LLM, no beat quota (Chaos Roll, Flip, Bake, Filth)."""

from __future__ import annotations

import json
import logging
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

from pattern_utils import TRACK_KEYS, track_notes
from plg_paths import app_dir

logger = logging.getLogger("plg.pattern_tools")

PROJECT_DIR = app_dir()
PATTERN_JSON = PROJECT_DIR / "output_pattern.json"


class PatternError(Exception):
    """Raised when no pattern exists or mutation is invalid."""


def load_pattern(path: Path = PATTERN_JSON) -> dict[str, Any]:
    if not path.is_file():
        raise PatternError("Create a beat first.")
    return json.loads(path.read_text(encoding="utf-8"))


def save_pattern(pattern: dict[str, Any], path: Path = PATTERN_JSON) -> None:
    path.write_text(json.dumps(pattern, ensure_ascii=False, indent=2), encoding="utf-8")


def finalize_pattern_exports(pattern: dict[str, Any], project_dir: Path | None = None) -> dict[str, Any]:
    """Stem session + guides; does not launch FL."""
    root = (project_dir or PROJECT_DIR).resolve()
    from guide_export import export_build_guide
    from midi_export import export_stem_session
    from midi_validate import log_validation_report, validate_export
    from mix_blueprint import export_mix_blueprint

    midi_dir = root / "output_midi"
    session = export_stem_session(pattern, midi_dir)
    stem_dir = session["session_dir"]
    combined = session["combined_path"]
    log_validation_report(validate_export(pattern, midi_dir=stem_dir, combined=combined))

    pattern["plg_stem_session"] = str(stem_dir)
    pattern["plg_stem_files"] = [str(p) for p in session["stem_paths"]]

    export_build_guide(pattern, output_path=root / "build_guide.txt")
    export_mix_blueprint(
        pattern,
        output_path=root / "READ_ME_IMBA.txt",
        stem_folder=str(stem_dir),
    )
    save_pattern(pattern, root / "output_pattern.json")
    return {
        "stem_session": str(stem_dir),
        "stem_files": [p.name for p in session["stem_paths"]],
        "combined_midi": str(combined),
        "mix_blueprint": str(root / "READ_ME_IMBA.txt"),
    }


def result_payload(pattern: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "ok": True,
        "bpm": pattern.get("bpm"),
        "style": pattern.get("style", "unknown"),
        "note_count": sum(len(track_notes(pattern, k)) for k in TRACK_KEYS),
        "sample_picks": pattern.get("plg_sample_picks") or {},
        "stem_session": pattern.get("plg_stem_session"),
        "stem_files": [Path(p).name for p in (pattern.get("plg_stem_files") or [])],
        "mix_blueprint": str(PROJECT_DIR / "READ_ME_IMBA.txt"),
        "filth_mode": bool(pattern.get("plg_filth_mode")),
        "sample_chop": pattern.get("plg_sample_chop"),
        **extra,
    }


def chaos_roll(pattern: dict[str, Any] | None = None) -> dict[str, Any]:
    """Re-roll hi-hat machine-gun patterns with a new seed."""
    from beat_humanize import reprocess_hi_hats

    data = deepcopy(pattern or load_pattern())
    seed = int(time.time() * 1000) % 1_000_000_007
    data = reprocess_hi_hats(data, chaos_seed=seed)
    exports = finalize_pattern_exports(data)
    logger.info("Chaos roll applied (seed=%s)", seed)
    return result_payload(data, chaos_seed=seed, chaos_rolls=data.get("plg_chaos_rolls", 0), **exports)


def _reverse_notes(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not notes:
        return []
    span = max(_note_end(n) for n in notes)
    out: list[dict[str, Any]] = []
    for entry in notes:
        note = deepcopy(entry)
        start = float(note.get("time_step", 0))
        length = float(note.get("length", 0.25))
        end = start + length
        note["time_step"] = round(max(0.0, span - end), 5)
        out.append(note)
    return sorted(out, key=lambda n: float(n["time_step"]))


def _note_end(entry: dict[str, Any]) -> float:
    return float(entry.get("time_step", 0)) + float(entry.get("length", 0.25))


def flip_beat(pattern: dict[str, Any] | None = None) -> dict[str, Any]:
    """Mirror melody + re-chop samples for a new variant without LLM."""
    data = deepcopy(pattern or load_pattern())
    tracks = data.setdefault("tracks", {})
    if not isinstance(tracks, dict):
        raise PatternError("Invalid pattern tracks.")

    melody = track_notes(data, "melody_lead")
    if melody:
        tracks["melody_lead"] = _reverse_notes(melody)
    counter = track_notes(data, "counter_melody")
    if counter:
        tracks["counter_melody"] = _reverse_notes(counter)

    flip_count = int(data.get("plg_flip_count", 0)) + 1
    data["plg_flip_count"] = flip_count

    paths = data.get("plg_sound_paths") or {}
    melody_path = paths.get("melody_lead")
    if melody_path:
        from sample_chop_engine import apply_sample_chop_to_pattern

        apply_sample_chop_to_pattern(
            data,
            Path(melody_path),
            prompt=str(data.get("user_prompt", "")),
        )

    exports = finalize_pattern_exports(data)
    logger.info("Flip beat #%s", flip_count)
    return result_payload(data, flip_count=flip_count, **exports)


def bake_session(pattern: dict[str, Any] | None = None) -> dict[str, Any]:
    """Export stems, write .flp, install FL scripts — one-click session bake."""
    from fl_setup import install_all
    from flp_writer import write_flp_session

    data = deepcopy(pattern or load_pattern())
    if not any(track_notes(data, k) for k in TRACK_KEYS):
        raise PatternError("Beat has no MIDI notes to bake.")

    exports = finalize_pattern_exports(data)
    root = PROJECT_DIR.resolve()
    flp_path = write_flp_session(data, root / "PLG_Session.flp")
    scripts = install_all(root)

    return result_payload(
        data,
        flp=str(flp_path),
        script_pack_count=len(scripts.get("script_pack") or []),
        message="Session baked — stems, .flp, and mix guide ready.",
        **exports,
    )


def set_filth_mode(enabled: bool, pattern: dict[str, Any] | None = None) -> dict[str, Any]:
    """Toggle the heavy distortion mix preset (metadata + blueprint — configure plugins in FL)."""
    data = deepcopy(pattern or load_pattern())
    meta = data.setdefault("plg_producer_meta", {})
    if not isinstance(meta, dict):
        meta = {}
        data["plg_producer_meta"] = meta

    data["plg_filth_mode"] = bool(enabled)
    meta["master_soft_clip"] = bool(enabled)
    meta["filth_mode"] = bool(enabled)
    if enabled:
        meta["mix_hints"] = {
            "master": "Fruity Soft Clipper · Post-Gain +4 dB · Threshold ~ -3 dB",
            "sub_808": "Fruity Blood Overdrive · Pre-Amp 40% · Color center",
        }
    else:
        meta.pop("mix_hints", None)

    steps = [s for s in (data.get("manual_steps") or []) if "Filth mode" not in s]
    if enabled:
        steps.insert(
            0,
            "Filth mode ON — Master Soft Clipper Post-Gain +4 dB, 808 Blood Overdrive Pre-Amp 40% / Color center (see READ_ME_IMBA).",
        )
    data["manual_steps"] = steps[:16]

    exports = finalize_pattern_exports(data)
    return result_payload(data, filth_mode=bool(enabled), **exports)


def get_producer_blueprint(*, locale: str | None = None) -> dict[str, Any]:
    """Structured checklist steps for the interactive blueprint UI."""
    from mix_blueprint import list_blueprint_steps

    pattern = load_pattern()
    steps = list_blueprint_steps(pattern, locale)
    return {
        "ok": True,
        "steps": steps,
        "filth_mode": bool(pattern.get("plg_filth_mode")),
        "mix_blueprint": str(PROJECT_DIR / "READ_ME_IMBA.txt"),
    }
