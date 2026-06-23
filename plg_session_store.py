"""Persist cloud auth session (access + refresh tokens) locally."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from plg_paths import app_dir

SESSION_FILE = app_dir() / "plg_cloud_session.json"


def load_session() -> dict[str, Any]:
    custom = os.getenv("PLG_CLOUD_SESSION_FILE", "").strip()
    path = Path(custom) if custom else SESSION_FILE
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_session(data: dict[str, Any]) -> None:
    custom = os.getenv("PLG_CLOUD_SESSION_FILE", "").strip()
    path = Path(custom) if custom else SESSION_FILE
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_session() -> None:
    custom = os.getenv("PLG_CLOUD_SESSION_FILE", "").strip()
    path = Path(custom) if custom else SESSION_FILE
    if path.is_file():
        path.unlink()
