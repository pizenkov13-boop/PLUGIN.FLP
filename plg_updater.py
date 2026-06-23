"""Desktop auto-update — check manifest, download new PLG.exe."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx

from app_config import app_version
from plg_paths import app_dir, is_frozen

logger = logging.getLogger("plg.updater")

_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


def _parse_version(text: str) -> tuple[int, int, int]:
    match = _VERSION_RE.match((text or "").strip())
    if not match:
        return (0, 0, 0)
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def manifest_url() -> str:
    return (
        os.getenv("PLG_UPDATE_MANIFEST_URL", "").strip()
        or "https://api.pluginflp.app/v1/release/manifest"
    )


def fetch_manifest() -> dict[str, Any]:
    url = manifest_url()
    try:
        resp = httpx.get(url, timeout=12.0, headers={"X-PLG-Version": app_version()})
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            return {"ok": False, "error": "Invalid manifest.", "error_type": "network"}
        return {"ok": True, **data}
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc), "error_type": "network"}
    except json.JSONDecodeError:
        return {"ok": False, "error": "Manifest is not JSON.", "error_type": "network"}


def check_for_updates() -> dict[str, Any]:
    current = app_version()
    manifest = fetch_manifest()
    if not manifest.get("ok"):
        return manifest

    latest = str(manifest.get("version") or "").strip()
    if not latest:
        return {"ok": True, "update_available": False, "current": current}

    newer = _parse_version(latest) > _parse_version(current)
    return {
        "ok": True,
        "update_available": newer,
        "current": current,
        "latest": latest,
        "url": manifest.get("url"),
        "notes": manifest.get("notes"),
        "sha256": manifest.get("sha256"),
        "mandatory": bool(manifest.get("mandatory")),
    }


def download_update(dest: Path | None = None) -> dict[str, Any]:
    info = check_for_updates()
    if not info.get("ok"):
        return info
    if not info.get("update_available"):
        return {"ok": True, "message": "Already on latest version.", "current": info.get("current")}

    url = str(info.get("url") or "").strip()
    if not url.startswith("https://"):
        return {"ok": False, "error": "Update URL missing.", "error_type": "config"}

    target = dest or (app_dir() / "PLG_update.exe")
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as resp:
            resp.raise_for_status()
            digest = hashlib.sha256()
            with target.open("wb") as handle:
                for chunk in resp.iter_bytes():
                    handle.write(chunk)
                    digest.update(chunk)
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc), "error_type": "network"}

    expected = str(info.get("sha256") or "").strip().lower()
    if expected and digest.hexdigest().lower() != expected:
        target.unlink(missing_ok=True)
        return {"ok": False, "error": "Checksum mismatch.", "error_type": "validation"}

    return {
        "ok": True,
        "path": str(target),
        "version": info.get("latest"),
        "message": f"Downloaded v{info.get('latest')} — restart to apply.",
    }


def apply_downloaded_update(download_path: str | None = None) -> dict[str, Any]:
    """Stage a swap script — user restarts PLG.exe to finish."""
    if not is_frozen():
        return {"ok": False, "error": "Updates apply only to PLG.exe builds.", "error_type": "config"}

    src = Path(download_path or app_dir() / "PLG_update.exe")
    if not src.is_file():
        return {"ok": False, "error": "Download PLG_update.exe first.", "error_type": "not_found"}

    exe = Path(sys.executable).resolve()
    bat = app_dir() / "apply_plg_update.bat"
    bat.write_text(
        "\n".join(
            [
                "@echo off",
                "echo Applying PLUGIN.FLP update...",
                f'timeout /t 2 /nobreak >nul',
                f'copy /Y "{src}" "{exe}"',
                f'del "{src}"',
                f'start "" "{exe}"',
                "del \"%~f0\"",
            ]
        ),
        encoding="utf-8",
    )
    subprocess.Popen(["cmd", "/c", str(bat)], cwd=str(app_dir()), close_fds=True)
    return {"ok": True, "message": "Restarting with new version…"}


def open_download_folder() -> dict[str, Any]:
    path = app_dir()
    try:
        os.startfile(path)  # noqa: S606
        return {"ok": True, "path": str(path)}
    except OSError as exc:
        return {"ok": False, "error": str(exc), "error_type": "os_error"}
