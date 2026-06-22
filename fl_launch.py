"""Find and launch FL Studio with PLG beat files."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
PATTERN_JSON = PROJECT_DIR / "output_pattern.json"
COMBINED_MIDI = PROJECT_DIR / "output_midi" / "PLG_Beat.mid"

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

    image_line = Path(r"C:\Program Files\Image-Line")
    if image_line.is_dir():
        matches = sorted(image_line.glob("*/FL64.exe"), reverse=True)
        if matches:
            return matches[0]

    image_line_x86 = Path(r"C:\Program Files (x86)\Image-Line")
    if image_line_x86.is_dir():
        matches = sorted(image_line_x86.glob("*/FL64.exe"), reverse=True)
        if matches:
            return matches[0]
    return None


def open_beat_in_fl(project_dir: Path | None = None) -> dict[str, Path | str | bool]:
    """Export MIDI, install bridge script, launch FL, import tracks into channel rack."""
    from fl_import import launch_fl_and_import_midi
    from fl_setup import install_plugin_script
    from midi_export import export_combined_midi, export_pattern_to_midi

    root = (project_dir or PROJECT_DIR).resolve()
    pattern_path = root / "output_pattern.json"
    if not pattern_path.is_file():
        raise FileNotFoundError("Create a beat first (CREATE BEAT).")

    data = json.loads(pattern_path.read_text(encoding="utf-8"))
    midi_dir = root / "output_midi"
    export_pattern_to_midi(data, midi_dir)
    combined = export_combined_midi(data, midi_dir / "PLG_Beat.mid")

    script_path = install_plugin_script(root)
    fl_exe = find_fl_executable()
    if fl_exe is None:
        raise FileNotFoundError(
            "FL Studio not found. Install FL Studio or open PLG_Beat.mid manually from output_midi/."
        )

    import_result = launch_fl_and_import_midi(fl_exe, combined, project_dir=root)

    return {
        "fl_exe": fl_exe,
        "midi": combined,
        "script": Path(script_path),
        "pattern": pattern_path,
        "imported": bool(import_result.get("imported")),
        "import_method": str(import_result.get("method", "")),
        "import_configured": bool(import_result.get("import_configured")),
    }
