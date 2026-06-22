"""FL import fallback helpers.

The previous version of this module tried to drive FL Studio's
``File -> Import -> MIDI`` dialog with simulated Alt+F keystrokes and Win32
window automation. That proved unreliable (RU/EN menus, focus loss, custom
dialogs) and is the reason OPEN IN FL reported ``imported=False``.

The reliable path now lives in :mod:`flp_writer` / :mod:`fl_launch`: PLG writes
a real ``.flp`` session and hands it to FL on the command line. This module is
reduced to the small bits the GUI still calls plus an Explorer-reveal fallback
used only when ``.flp`` generation is unavailable.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_MARKER_NAME = ".plg_fl_import_ready"


def import_marker_path(project_dir: Path) -> Path:
    return Path(project_dir) / _MARKER_NAME


def is_fl_import_configured(project_dir: Path) -> bool:
    """Kept for the GUI setup strip. The .flp bridge needs no manual setup."""
    return import_marker_path(project_dir).is_file()


def mark_fl_import_configured(project_dir: Path) -> None:
    import_marker_path(project_dir).write_text("ok\n", encoding="utf-8")


def reveal_in_explorer(path: Path) -> None:
    """Open Explorer with ``path`` selected (last-resort fallback)."""
    subprocess.Popen(["explorer", "/select,", str(Path(path).resolve())], close_fds=True)


# Backwards-compatible alias for older callers.
reveal_midi_in_explorer = reveal_in_explorer
