"""Install PLG piano roll script into FL Studio user folder."""

from __future__ import annotations

import shutil
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
SOURCE_SCRIPT = PROJECT_DIR / "plugin_script.py"
SCRIPT_NAME = "PLG PLUGIN.FLP.pyscript"


def fl_piano_roll_scripts_dir() -> Path:
    home = Path.home()
    candidates = [
        home / "Documents" / "Image-Line" / "FL Studio" / "Settings" / "Piano roll scripts",
        home / "OneDrive" / "Documents" / "Image-Line" / "FL Studio" / "Settings" / "Piano roll scripts",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def install_plugin_script() -> Path:
    target_dir = fl_piano_roll_scripts_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / SCRIPT_NAME
    shutil.copy2(SOURCE_SCRIPT, destination)
    return destination
