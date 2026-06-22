"""Find and launch FL Studio with a ready-made PLG beat.

OPEN IN FL writes a real ``.flp`` session (3 named channels + the pattern notes)
and hands it to FL on the command line. Opening a project file is the one FL
import path that is actually reliable — no menu automation, no drag, no MIDI
import dialog. See FL_BRIDGE.md for the full rationale.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from plg_paths import app_dir

PROJECT_DIR = app_dir()
PATTERN_JSON = PROJECT_DIR / "output_pattern.json"
COMBINED_MIDI = PROJECT_DIR / "output_midi" / "PLG_Beat.mid"
SESSION_FLP = PROJECT_DIR / "PLG_Session.flp"

FL_CANDIDATES = (
    Path(r"C:\Program Files\Image-Line\FL Studio 2025\FL64.exe"),
    Path(r"C:\Program Files\Image-Line\FL Studio 24\FL64.exe"),
    Path(r"C:\Program Files\Image-Line\FL Studio 21\FL64.exe"),
    Path(r"C:\Program Files (x86)\Image-Line\FL Studio 20\FL64.exe"),
)


def find_fl_executable() -> Path | None:
    for candidate in FL_CANDIDATES:
        if candidate.is_file():
            return candidate

    for base in (Path(r"C:\Program Files\Image-Line"), Path(r"C:\Program Files (x86)\Image-Line")):
        if base.is_dir():
            matches = sorted(base.glob("*/FL64.exe"), reverse=True)
            if matches:
                return matches[0]
    return None


def _has_notes(data: dict) -> bool:
    tracks = data.get("tracks")
    if not isinstance(tracks, dict):
        return False
    return any(tracks.get(key) for key in ("hi_hats", "sub_808", "melody_lead"))


def launch_fl_with_session(fl_exe: Path, flp_path: Path) -> None:
    """Open FL with a project file. FL is single-instance: if it is already
    running it will prompt to save the current project, then load this one."""
    subprocess.Popen([str(fl_exe), str(flp_path)], cwd=str(fl_exe.parent), close_fds=True)


def open_beat_in_fl(project_dir: Path | None = None) -> dict[str, Path | str | bool]:
    """Write a .flp session, install the scripts, and open it in FL Studio."""
    from fl_setup import install_all
    from flp_writer import write_flp_session
    from midi_export import export_combined_midi, export_pattern_to_midi

    root = (project_dir or PROJECT_DIR).resolve()
    pattern_path = root / "output_pattern.json"
    if not pattern_path.is_file():
        raise FileNotFoundError("Create a beat first (CREATE BEAT).")

    data = json.loads(pattern_path.read_text(encoding="utf-8"))
    if not _has_notes(data):
        raise ValueError("This beat has no MIDI notes to load into FL.")

    from library_catalog import scan_library
    from starter_kit import attach_sounds_to_pattern

    library_root = Path(data.get("sample_library") or root / "PLG_Library")
    catalog = scan_library(library_root) if library_root.is_dir() else None
    attach_sounds_to_pattern(data, catalog, library_root=library_root)
    pattern_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # MIDI export is kept for manual import / other DAWs; the .flp is primary.
    midi_dir = root / "output_midi"
    export_pattern_to_midi(data, midi_dir)
    combined = export_combined_midi(data, midi_dir / "PLG_Beat.mid")

    flp_path = write_flp_session(data, root / "PLG_Session.flp")
    scripts = install_all(root)

    fl_exe = find_fl_executable()
    if fl_exe is None:
        raise FileNotFoundError(
            "FL Studio not found. Install FL Studio, or open PLG_Session.flp "
            "from the PLG folder manually."
        )

    launch_fl_with_session(fl_exe, flp_path)

    return {
        "fl_exe": fl_exe,
        "midi": combined,
        "flp": flp_path,
        "script": Path(scripts["plugin_script"]),  # type: ignore[index]
        "pattern": pattern_path,
        "imported": True,
        "import_method": "flp_session",
        "import_configured": True,
    }


if __name__ == "__main__":
    result = open_beat_in_fl(PROJECT_DIR)
    for key, value in result.items():
        print(f"{key}: {value}")
