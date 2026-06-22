"""PLG install paths — dev folder, PyInstaller bundle, and per-user data."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """Writable app root (repo folder or folder containing PLG.exe)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundle_dir() -> Path:
    """Read-only shipped assets (PyInstaller _MEIPASS or repo root)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", app_dir()))
    return Path(__file__).resolve().parent


def user_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    root = Path(base) if base else Path.home() / "AppData" / "Local"
    return root / "PLG"


def starter_runtime_dir() -> Path:
    """Where PLG reads/writes active starter wavs (stable paths for FL)."""
    if is_frozen():
        path = user_data_dir() / "starter"
    else:
        path = app_dir() / "assets" / "starter"
    path.mkdir(parents=True, exist_ok=True)
    return path


def starter_bundle_dir() -> Path:
    """Shipped starter wavs inside the installer / repo."""
    return bundle_dir() / "assets" / "starter"


def resource_path(*parts: str) -> Path:
    """Find a shipped file in the PyInstaller bundle or dev repo."""
    bundled = bundle_dir().joinpath(*parts)
    if bundled.is_file() or bundled.is_dir():
        return bundled
    return app_dir().joinpath(*parts)
