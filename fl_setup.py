"""Install PLG piano roll script into FL Studio user folder."""

from __future__ import annotations

import re
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


def _script_with_bridge_path(project_dir: Path) -> str:
    bridge = str((project_dir / "output_pattern.json").resolve())
    content = SOURCE_SCRIPT.read_text(encoding="utf-8")
    escaped = bridge.replace("\\", "\\\\")
    return re.sub(r'BRIDGE_PATH = r"[^"]*"', f'BRIDGE_PATH = r"{escaped}"', content, count=1)


def install_plugin_script(project_dir: Path | None = None) -> Path:
    root = (project_dir or PROJECT_DIR).resolve()
    target_dir = fl_piano_roll_scripts_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / SCRIPT_NAME
    destination.write_text(_script_with_bridge_path(root), encoding="utf-8")
    return destination


def is_plugin_script_installed(project_dir: Path | None = None) -> bool:
    root = (project_dir or PROJECT_DIR).resolve()
    destination = fl_piano_roll_scripts_dir() / SCRIPT_NAME
    if not destination.is_file():
        return False
    bridge = str((root / "output_pattern.json").resolve())
    return bridge in destination.read_text(encoding="utf-8")
