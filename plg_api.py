"""PLG application API — UI-agnostic logic layer.

This module is the single seam between PLG's engine (backend_core, flp_writer,
fl_launch, starter_kit, beat_quota, …) and whatever front-end drives it. It does
NOT import tkinter, pywebview, or any UI toolkit, and it never touches the
engine modules' internals — it only *wraps* their existing public functions.

Design notes
------------
* Every public function returns a plain JSON-serializable ``dict`` (Path values
  are stringified). That lets a pywebview bridge expose these methods straight
  to JavaScript without translation.
* Errors are returned as ``{"ok": False, "error": <human text>, "error_type": …}``
  instead of raising, so the UI can render them. Truly unexpected exceptions are
  logged and also surface as ``ok: False``.
* Beat generation (``run_pipeline``) is a single 30–90 s blocking call inside the
  engine; we cannot see inside it without modifying backend_core, which is off
  limits. So generation reports *coarse phases* around the call, while the
  per-second "Generating · 42s" feedback is computed by the UI from the job's
  ``started_at`` (the same thing the old tk ticker did, moved client-side).
* Long-running work is exposed two ways:
    - a synchronous function (``create_beat``, ``split_stems_file``) — pure,
      testable, accepts an optional ``on_progress`` callback;
    - an async job (``start_beat`` → ``get_job`` polling) layered on top via a
      tiny thread-backed registry. pywebview UIs use the job/poll path so the
      window thread never blocks.

This file is the foundation for the React + pywebview front-end. plg_app.py
(tkinter) stays the shipping UI until the web UI is ready; nothing here changes
the engine, so both UIs can coexist.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import app_config
from app_config import (
    app_version,
    get_auto_open_fl,
    get_samples_dir,
    has_api_key,
    is_release_build,
    settings_snapshot,
    write_env_file,
)
from backend_core import count_track_notes, run_pipeline, run_pipeline_from_pattern
from beat_quota import (
    BeatQuotaExceeded,
    consume_beat,
    ensure_can_consume_beat,
    format_quota_label,
    get_quota_snapshot,
)
from fl_launch import find_fl_executable, fl_version_label, open_beat_in_fl
from fl_setup import install_all, is_fl_bridge_ready
from library_catalog import save_catalog, scan_library as _scan_library
from llm_client import format_llm_error, get_provider, provider_label
from plg_paths import app_dir

try:
    import plg_cloud
except ImportError:  # pragma: no cover
    plg_cloud = None  # type: ignore[assignment]

logger = logging.getLogger("plg.api")

PROJECT_DIR = app_dir()
PATTERN_JSON = PROJECT_DIR / "output_pattern.json"
CATALOG_FILE = PROJECT_DIR / "sample_catalog.json"

# Generation phases reported through on_progress (UI maps these to copy/spinner).
PHASE_GENERATING = "generating"
PHASE_FINALIZING = "finalizing"
PHASE_DONE = "done"

ProgressCb = Callable[[str, float, str], None]

# ---------------------------------------------------------------------------
# Module state (single desktop user; guarded by a lock).
# ---------------------------------------------------------------------------
_state_lock = threading.Lock()
_last_prompt: str = ""
_ui_locale: str = "en"


def set_ui_locale(locale: str) -> dict[str, Any]:
    global _ui_locale
    from prompt_locale import VALID_LOCALES

    _ui_locale = locale if locale in VALID_LOCALES else "en"
    return {"ok": True, "locale": _ui_locale}


def _set_last_prompt(prompt: str) -> None:
    global _last_prompt
    with _state_lock:
        _last_prompt = prompt


def _get_last_prompt() -> str:
    with _state_lock:
        return _last_prompt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _err(message: str, error_type: str = "unknown", **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"ok": False, "error": message, "error_type": error_type}
    payload.update(extra)
    return payload


def _emit(on_progress: ProgressCb | None, phase: str, fraction: float, message: str) -> None:
    """Call a progress callback without ever letting it break the worker."""
    if on_progress is None:
        return
    try:
        on_progress(phase, float(fraction), message)
    except Exception:  # noqa: BLE001 - progress is best-effort, never fatal
        logger.debug("progress callback raised", exc_info=True)


def _provider_label_safe() -> str:
    try:
        return provider_label()
    except Exception:  # noqa: BLE001 - unknown provider in .env shouldn't crash status
        return "—"


def _cached_audio_total() -> int:
    """Audio count from the last saved catalog — cheap (no filesystem walk).

    May be stale until ``scan_library()`` is called; used only for status hints.
    """
    try:
        data = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
        return int(data.get("audio_total", 0))
    except (OSError, ValueError, TypeError):
        return 0


def _cloud_enabled() -> bool:
    return bool(plg_cloud and plg_cloud.is_cloud_mode())


def _network_online() -> bool:
    if not _cloud_enabled():
        return True
    return plg_cloud.ping_cloud().get("ok", False)


def _format_cloud_quota_label(snap: dict[str, Any]) -> str:
    days = snap.get("days_until_reset", 0)
    daily = snap.get("daily_remaining", snap.get("daily_limit", 3))
    return (
        f"{snap.get('remaining', 0)}/{snap.get('limit', 30)} beats · "
        f"{daily}/day left · resets in {days}d"
    )


# ---------------------------------------------------------------------------
# Cloud auth (Phase 1)
# ---------------------------------------------------------------------------
def get_auth_status() -> dict[str, Any]:
    if not _cloud_enabled():
        return {"ok": True, "cloud_mode": False, "signed_in": True}
    snap = plg_cloud.session_snapshot()
    cfg = plg_cloud.fetch_auth_config()
    flags = plg_cloud.fetch_feature_flags()
    return {
        "ok": True,
        "cloud_mode": True,
        "signed_in": snap.get("signed_in", False),
        "email": snap.get("email"),
        "captcha_provider": cfg.get("captcha_provider"),
        "captcha_site_key": cfg.get("captcha_site_key"),
        "captcha_required": cfg.get("captcha_required", False),
        "invite_required": cfg.get("invite_required", False),
        "feature_flags": flags.get("flags") if flags.get("ok") else {},
    }


def cloud_signup(
    email: str,
    password: str,
    captcha_token: str | None = None,
    invite_code: str | None = None,
    accept_terms: bool = False,
    confirm_age: bool = False,
) -> dict[str, Any]:
    if not _cloud_enabled():
        return _err("Cloud mode is disabled.", "config")
    return plg_cloud.signup(
        email, password, captcha_token, invite_code, accept_terms, confirm_age
    )


def cloud_delete_account() -> dict[str, Any]:
    if not _cloud_enabled():
        return _err("Cloud mode is disabled.", "config")
    if not plg_cloud.is_signed_in():
        return _err("Sign in first.", "auth")
    return plg_cloud.delete_account()


def cloud_login(email: str, password: str) -> dict[str, Any]:
    if not _cloud_enabled():
        return _err("Cloud mode is disabled.", "config")
    result = plg_cloud.login(email, password)
    if result.get("ok"):
        plg_cloud.register_device()
        try:
            import plg_analytics

            session = plg_cloud.load_session()
            user = session.get("user") or {}
            uid = str(user.get("id") or user.get("sub") or email)
            plg_analytics.identify_user(uid, {"email": email})
            plg_analytics.track("login")
        except Exception:  # noqa: BLE001
            pass
    return result


def cloud_logout() -> dict[str, Any]:
    if not _cloud_enabled():
        return {"ok": True}
    return plg_cloud.logout()


def cloud_reset_password(email: str) -> dict[str, Any]:
    if not _cloud_enabled():
        return _err("Cloud mode is disabled.", "config")
    return plg_cloud.request_password_reset(email)


def cloud_billing_status() -> dict[str, Any]:
    if not _cloud_enabled():
        return _err("Cloud mode is disabled.", "config")
    if not plg_cloud.is_signed_in():
        return _err("Sign in first.", "auth")
    return plg_cloud.billing_status()


def cloud_billing_checkout(price_tier: str | None = None) -> dict[str, Any]:
    if not _cloud_enabled():
        return _err("Cloud mode is disabled.", "config")
    if not plg_cloud.is_signed_in():
        return _err("Sign in first.", "auth")
    result = plg_cloud.billing_checkout(price_tier)
    if not result.get("ok"):
        return result
    url = str(result.get("confirmation_url") or "").strip()
    if url:
        opened = open_external_url(url)
        if not opened.get("ok"):
            return {**result, "opened": False, "warning": opened.get("error")}
        return {**result, "opened": True}
    return result


def cloud_fetch_status() -> dict[str, Any]:
    if not _cloud_enabled():
        return {"ok": False, "error": "Cloud mode is disabled.", "error_type": "config"}
    return plg_cloud.fetch_status()


def cloud_submit_feedback(
    category: str,
    message: str,
    *,
    attach_log: bool = False,
) -> dict[str, Any]:
    if not _cloud_enabled():
        return _err("Cloud mode is disabled.", "config")
    if not plg_cloud.is_signed_in():
        return _err("Sign in first.", "auth")
    log_excerpt = None
    if attach_log:
        try:
            from plg_log import read_log_tail

            log_excerpt = read_log_tail()
        except Exception:  # noqa: BLE001
            log_excerpt = None
    return plg_cloud.submit_feedback(
        category=category,
        message=message,
        attach_log=attach_log,
        log_excerpt=log_excerpt,
    )


def open_external_url(url: str) -> dict[str, Any]:
    """Open HTTPS checkout or help link in the default browser."""
    target = (url or "").strip()
    if not target.startswith(("https://", "http://")):
        return _err("Invalid URL.", "validation")
    try:
        import webbrowser

        webbrowser.open(target, new=2)
        return {"ok": True, "url": target}
    except OSError as exc:
        return _err(str(exc), "os_error")


# ---------------------------------------------------------------------------
# Settings  (wraps app_config)
# ---------------------------------------------------------------------------
def get_settings() -> dict[str, Any]:
    """Current settings for the form. Keys are returned raw (local-only app).

    ``has_*_key`` booleans are provided so the UI can show "configured" state
    without echoing secrets if it prefers to mask them.
    """
    app_config.load_environment()
    snap = settings_snapshot()
    return {
        "ok": True,
        "provider": snap["provider"],
        "gemini_key": snap["gemini_key"],
        "anthropic_key": snap["anthropic_key"],
        "has_gemini_key": bool(snap["gemini_key"]),
        "has_anthropic_key": bool(snap["anthropic_key"]),
        "samples_dir": snap["samples_dir"],
        "gemini_model": snap["gemini_model"],
        "claude_model": snap["claude_model"],
        "auto_open_fl": snap["auto_open_fl"] == "true",
    }


def save_settings(updates: dict[str, Any]) -> dict[str, Any]:
    """Persist settings to .env. Accepts a partial dict; merges with current.

    Mirrors the validation in the old SettingsDialog: the *active* provider must
    have a matching API key after the merge.
    """
    current = get_settings()
    provider = str(updates.get("provider", current["provider"]) or "gemini").strip().lower()
    gemini_key = str(updates.get("gemini_key", current["gemini_key"])).strip()
    anthropic_key = str(updates.get("anthropic_key", current["anthropic_key"])).strip()
    samples_dir = str(updates.get("samples_dir", current["samples_dir"])).strip()

    auto_open = updates.get("auto_open_fl", current["auto_open_fl"])
    auto_open_str = "true" if (auto_open if isinstance(auto_open, bool) else str(auto_open).lower() == "true") else "false"

    if _cloud_enabled():
        write_env_file(
            {
                "PLG_SAMPLES_DIR": samples_dir,
                "PLG_AUTO_OPEN_FL": auto_open_str,
            }
        )
        return {"ok": True, "settings": get_settings()}

    if provider in ("anthropic", "claude") and not anthropic_key:
        return _err("Add an Anthropic API key or switch the provider to gemini.", "validation")
    if provider not in ("anthropic", "claude") and not gemini_key:
        return _err("Add a Gemini API key to continue.", "validation")

    env_updates: dict[str, str] = {
        "PLG_LLM_PROVIDER": provider,
        "GEMINI_API_KEY": gemini_key,
        "ANTHROPIC_API_KEY": anthropic_key,
        "PLG_SAMPLES_DIR": samples_dir,
        "PLG_AUTO_OPEN_FL": auto_open_str,
    }
    if "gemini_model" in updates:
        env_updates["GEMINI_MODEL"] = str(updates["gemini_model"]).strip()
    if "claude_model" in updates:
        env_updates["PLG_CLAUDE_MODEL"] = str(updates["claude_model"]).strip()

    write_env_file(env_updates)
    return {"ok": True, "settings": get_settings()}


# ---------------------------------------------------------------------------
# Status & quota
# ---------------------------------------------------------------------------
def get_quota() -> dict[str, Any]:
    """Beat quota snapshot plus the short label the status bar shows."""
    if _cloud_enabled() and plg_cloud.is_signed_in():
        me = plg_cloud.fetch_me()
        if me.get("ok") and isinstance(me.get("quota"), dict):
            snap = dict(me["quota"])
            snap["label"] = _format_cloud_quota_label(snap)
            snap["skipped"] = False
            return snap
    snap = get_quota_snapshot()
    snap["label"] = format_quota_label(snap)
    return snap


def _read_pattern_field(key: str, default: Any = None) -> Any:
    try:
        data = json.loads(PATTERN_JSON.read_text(encoding="utf-8"))
        return data.get(key, default)
    except (OSError, ValueError, TypeError):
        return default


def _read_sample_picks() -> dict[str, str]:
    picks = _read_pattern_field("plg_sample_picks")
    return picks if isinstance(picks, dict) else {}


def _read_export_meta() -> dict[str, Any]:
    blueprint = PROJECT_DIR / "READ_ME_IMBA.txt"
    stem_files = _read_pattern_field("plg_stem_files", [])
    if not isinstance(stem_files, list):
        stem_files = []
    chop = _read_pattern_field("plg_sample_chop")
    return {
        "bpm": _read_pattern_field("bpm"),
        "style": _read_pattern_field("style"),
        "stem_session": _read_pattern_field("plg_stem_session"),
        "stem_files": [Path(str(p)).name for p in stem_files],
        "mix_blueprint": str(blueprint) if blueprint.is_file() else None,
        "sample_chop": chop if isinstance(chop, dict) else None,
        "filth_mode": bool(_read_pattern_field("plg_filth_mode", False)),
    }


def get_status() -> dict[str, Any]:
    """Cheap app status for the header/status bar (no filesystem walk)."""
    app_config.load_environment()
    fl_exe = find_fl_executable()
    export_meta = _read_export_meta() if PATTERN_JSON.is_file() else {}
    cloud = _cloud_enabled()
    signed_in = plg_cloud.is_signed_in() if cloud else True
    auth = plg_cloud.session_snapshot() if cloud else {}
    return {
        "ok": True,
        "cloud_mode": cloud,
        "release_build": is_release_build(),
        "signed_in": signed_in,
        "auth_email": auth.get("email"),
        "app_version": app_version(),
        "network_online": _network_online(),
        "provider": _provider_label_safe() if not cloud else "PLG Cloud",
        "has_api_key": signed_in if cloud else has_api_key(),
        "fl_bridge_ready": is_fl_bridge_ready(PROJECT_DIR),
        "fl_installed": fl_exe is not None,
        "fl_version": fl_version_label(fl_exe),
        "fl_executable": str(fl_exe) if fl_exe else None,
        "beat_ready": PATTERN_JSON.is_file(),
        "auto_open_fl": get_auto_open_fl(),
        "library_audio_total": _cached_audio_total(),
        "last_prompt": _get_last_prompt(),
        "sample_picks": _read_sample_picks(),
        "quota": get_quota(),
        **export_meta,
    }


def reveal_path(path: str) -> dict[str, Any]:
    """Open a file or its parent folder in the OS shell (Windows Explorer)."""
    target = Path((path or "").strip())
    if not target.exists():
        return _err(f"Path not found: {path}", "not_found")
    try:
        import os
        import sys

        reveal = target if target.is_dir() else target.parent
        if sys.platform == "win32":
            os.startfile(reveal)  # noqa: S606 — intentional desktop shell open
        elif sys.platform == "darwin":
            import subprocess

            subprocess.run(["open", str(reveal)], check=False)
        else:
            import subprocess

            subprocess.run(["xdg-open", str(reveal)], check=False)
        return {"ok": True, "path": str(reveal)}
    except OSError as exc:
        return _err(str(exc), "os_error")


# ---------------------------------------------------------------------------
# Producer console (pattern_tools — no LLM, no quota)
# ---------------------------------------------------------------------------
def chaos_roll() -> dict[str, Any]:
    from pattern_tools import PatternError, chaos_roll as _chaos_roll

    try:
        return _chaos_roll()
    except PatternError as exc:
        return _err(str(exc), "no_beat")


def flip_beat() -> dict[str, Any]:
    from pattern_tools import PatternError, flip_beat as _flip_beat

    try:
        return _flip_beat()
    except PatternError as exc:
        return _err(str(exc), "no_beat")


def bake_session() -> dict[str, Any]:
    from pattern_tools import PatternError, bake_session as _bake_session

    try:
        return _bake_session()
    except PatternError as exc:
        return _err(str(exc), "no_beat")


def set_filth_mode(enabled: bool) -> dict[str, Any]:
    from pattern_tools import PatternError, set_filth_mode as _set_filth

    try:
        return _set_filth(bool(enabled))
    except PatternError as exc:
        return _err(str(exc), "no_beat")


def get_producer_blueprint() -> dict[str, Any]:
    from pattern_tools import PatternError, get_producer_blueprint as _blueprint

    try:
        return _blueprint()
    except PatternError as exc:
        return _err(str(exc), "no_beat")


# ---------------------------------------------------------------------------
# Library
# ---------------------------------------------------------------------------
def scan_library() -> dict[str, Any]:
    """Fresh scan of the sample library; persists sample_catalog.json.

    Heavier than get_status (walks the tree), so the UI calls it explicitly —
    on the library screen or after an import — not on every poll.
    """
    samples_dir = get_samples_dir()
    try:
        catalog = _scan_library(samples_dir)
    except FileNotFoundError:
        return _err(f"Library folder not found: {samples_dir}", "not_found", samples_dir=str(samples_dir))
    save_catalog(catalog, CATALOG_FILE)
    return {
        "ok": True,
        "root": catalog["root"],
        "total": catalog["total"],
        "audio_total": catalog.get("audio_total", 0),
        "audio": catalog.get("audio", {}),
        "midi": catalog.get("midi", []),
        "presets": catalog.get("presets", []),
        "projects": catalog.get("projects", []),
        "banks": catalog.get("banks", []),
        "plugins": catalog.get("plugins", []),
    }


def preview_kit(prompt: str) -> dict[str, Any]:
    """Match kick/snare/clap/808/hats/melody from the library without generating a beat."""
    prompt = (prompt or "").strip()
    if not prompt:
        return _err("Describe your beat first.", "validation")

    app_config.load_environment()
    samples_dir = get_samples_dir()
    try:
        catalog = _scan_library(samples_dir)
    except FileNotFoundError:
        return _err(f"Library folder not found: {samples_dir}", "not_found", samples_dir=str(samples_dir))

    from starter_kit import ensure_starter_kit, resolve_track_samples

    ensure_starter_kit()
    picks = resolve_track_samples(catalog, library_root=samples_dir, prompt=prompt)
    return {
        "ok": True,
        "audio_total": catalog.get("audio_total", 0),
        "picks": {track: {"name": path.name, "path": str(path)} for track, path in picks.items()},
    }


# ---------------------------------------------------------------------------
# Beat generation  (wraps backend_core.run_pipeline + beat_quota)
# ---------------------------------------------------------------------------
def create_beat(
    prompt: str,
    on_progress: ProgressCb | None = None,
    *,
    locale: str | None = None,
) -> dict[str, Any]:
    """Generate a beat from a prompt. Synchronous (blocks 30–90 s).

    Checks the quota first, runs the engine pipeline, consumes one beat on
    success — the same order the old tk UI used. Does NOT auto-open FL; the
    returned ``auto_open_fl`` flag lets the caller decide.
    """
    prompt = (prompt or "").strip()
    if not prompt:
        return _err("Describe your beat first.", "validation")

    app_config.load_environment()
    if _cloud_enabled():
        if not plg_cloud.is_signed_in():
            return _err("Sign in to generate beats.", "auth")
    elif not has_api_key():
        return _err("Add an API key in Settings to generate beats.", "no_api_key")

    if not _cloud_enabled():
        try:
            ensure_can_consume_beat()
        except BeatQuotaExceeded as exc:
            return _err(str(exc), "quota", quota=get_quota())

    loc = locale or _ui_locale
    _emit(on_progress, PHASE_GENERATING, 0.1, f"Generating · {_provider_label_safe()}")
    try:
        logger.info("create_beat start: %s locale=%s", prompt[:80], loc)
        if _cloud_enabled():
            samples_dir = Path(get_samples_dir())
            try:
                catalog = _scan_library(samples_dir)
            except FileNotFoundError:
                catalog = {"root": str(samples_dir), "total": 0, "audio_total": 0, "audio": {}}
            cloud_out = plg_cloud.cloud_generate(prompt, catalog=catalog, locale=loc)
            if not cloud_out.get("ok"):
                return _err(
                    str(cloud_out.get("error") or "Cloud generation failed."),
                    str(cloud_out.get("error_type") or "cloud"),
                    quota=cloud_out.get("quota"),
                )
            pattern = run_pipeline_from_pattern(cloud_out["pattern"], prompt, locale=loc)
            cloud_quota = cloud_out.get("quota")
        else:
            pattern = run_pipeline(prompt, locale=loc)
            cloud_quota = None
    except Exception as exc:  # noqa: BLE001 - surface any engine/LLM error to the UI
        logger.exception("create_beat: pipeline failed")
        return _err(format_llm_error(exc), "llm")

    _emit(on_progress, PHASE_FINALIZING, 0.9, "Baking session · FL")
    if not _cloud_enabled():
        try:
            consume_beat()
        except BeatQuotaExceeded:
            pass

    baked: dict[str, Any] = {}
    try:
        from pattern_tools import bake_session

        baked = bake_session()
    except Exception as exc:  # noqa: BLE001 - bake is best-effort after generation
        logger.warning("Auto-bake after create_beat failed: %s", exc)

    _set_last_prompt(prompt)
    logger.info("create_beat ok: bpm=%s style=%s", pattern.get("bpm"), pattern.get("style"))
    result = {
        "ok": True,
        "bpm": pattern.get("bpm"),
        "style": pattern.get("style", "unknown"),
        "note_count": count_track_notes(pattern),
        "sample_count": len(pattern.get("samples") or []),
        "provider": _provider_label_safe(),
        "auto_open_fl": get_auto_open_fl(),
        "sample_picks": pattern.get("plg_sample_picks") or {},
        "stem_session": baked.get("stem_session") or pattern.get("plg_stem_session"),
        "stem_files": baked.get("stem_files")
        or [Path(p).name for p in (pattern.get("plg_stem_files") or [])],
        "mix_blueprint": baked.get("mix_blueprint") or str(PROJECT_DIR / "READ_ME_IMBA.txt"),
        "flp": baked.get("flp"),
        "filth_mode": bool(baked.get("filth_mode") or pattern.get("plg_filth_mode")),
        "quota": cloud_quota if cloud_quota else get_quota(),
        "message": baked.get("message") or "Session baked — open in FL Studio",
    }
    _emit(on_progress, PHASE_DONE, 1.0, "Open in FL Studio")
    return result


def regenerate(prompt: str | None = None, on_progress: ProgressCb | None = None) -> dict[str, Any]:
    """Re-run generation. Uses the last prompt when none is given.

    Quota is enforced inside create_beat; any "this uses 1 beat" confirmation is
    a UI concern and should happen before calling this.
    """
    text = (prompt or "").strip() or _get_last_prompt()
    if not text:
        return _err("Describe your beat first.", "validation")
    return create_beat(text, on_progress=on_progress, locale=_ui_locale)


# ---------------------------------------------------------------------------
# Open in FL  (wraps fl_launch.open_beat_in_fl)
# ---------------------------------------------------------------------------
def open_in_fl() -> dict[str, Any]:
    """Write the .flp session, install scripts, and launch FL Studio."""
    try:
        result = open_beat_in_fl(PROJECT_DIR)
    except FileNotFoundError as exc:
        msg = str(exc)
        if "FL Studio not found" in msg:
            return _err(msg, "fl_not_found")
        return _err(msg, "not_found")
    except ValueError as exc:
        return _err(str(exc), "validation")
    except OSError as exc:
        return _err(str(exc), "io")

    method = str(result.get("import_method", ""))
    if result.get("imported") and method == "flp_session":
        message = "FL Studio · 3 channels ready — load your sounds"
    elif result.get("imported"):
        message = "FL Studio · 3 tracks imported"
    else:
        message = "FL Studio opened"

    return {
        "ok": True,
        "message": message,
        "imported": bool(result.get("imported")),
        "import_method": method,
        "flp": str(result.get("flp", "")),
        "midi": str(result.get("midi", "")),
        "fl_exe": str(result.get("fl_exe", "")),
    }


# ---------------------------------------------------------------------------
# FL setup  (wraps fl_setup.install_all)
# ---------------------------------------------------------------------------
def install_fl_scripts() -> dict[str, Any]:
    """Install the importer + V2 piano-roll script pack into FL's user folder."""
    try:
        installed = install_all(PROJECT_DIR)
    except OSError as exc:
        return _err(str(exc), "io")
    pack = installed.get("script_pack") or []
    return {
        "ok": True,
        "plugin_script": str(installed.get("plugin_script", "")),
        "script_pack_count": len(pack),
        "fl_bridge_ready": is_fl_bridge_ready(PROJECT_DIR),
    }


# ---------------------------------------------------------------------------
# Stem splitter  (wraps stem_split.split_stems) — real progress fractions
# ---------------------------------------------------------------------------
def split_stems_file(source: str, on_progress: ProgressCb | None = None) -> dict[str, Any]:
    """Split an audio file into 4 stems. Long-running; emits real progress."""
    from stem_split import StemSplitError, split_stems, stems_available

    src = Path(source)
    if not src.is_file():
        return _err("File not found.", "not_found")
    if not stems_available():
        return _err("Demucs is not installed (optional, ~2 GB):  pip install -U demucs", "missing_dep")

    out_dir = PROJECT_DIR / "output_stems" / src.stem
    try:
        result = split_stems(
            src,
            out_dir,
            progress_cb=lambda frac, msg: _emit(on_progress, "splitting", frac, msg),
        )
    except (StemSplitError, OSError) as exc:
        return _err(str(exc), "stems")
    return {
        "ok": True,
        "out_dir": str(out_dir),
        "stems": {name: str(path) for name, path in result.items()},
    }


# ---------------------------------------------------------------------------
# Async job registry — start_* + get_job polling for non-blocking UIs
# ---------------------------------------------------------------------------
@dataclass
class _Job:
    id: str
    kind: str
    status: str = "running"  # running | done | error
    phase: str = ""
    progress: float = 0.0
    message: str = ""
    result: dict[str, Any] | None = None
    error: str | None = None
    error_type: str | None = None
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None

    def snapshot(self) -> dict[str, Any]:
        now = self.finished_at if self.finished_at is not None else time.time()
        return {
            "ok": True,
            "job_id": self.id,
            "kind": self.kind,
            "status": self.status,
            "phase": self.phase,
            "progress": self.progress,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "error_type": self.error_type,
            "started_at": self.started_at,
            "elapsed": round(now - self.started_at, 1),
        }


_jobs: dict[str, _Job] = {}
_jobs_lock = threading.Lock()

JobTarget = Callable[[ProgressCb], dict[str, Any]]


def _update_job(job: _Job, phase: str, fraction: float, message: str) -> None:
    with _jobs_lock:
        job.phase = phase
        job.progress = float(fraction)
        job.message = message


def _finish_job(job: _Job, result: dict[str, Any]) -> None:
    with _jobs_lock:
        job.finished_at = time.time()
        if result.get("ok"):
            job.status = "done"
            job.result = result
            job.progress = 1.0
            if job.kind == "beat":
                try:
                    import plg_analytics

                    plg_analytics.track("beat_created")
                except Exception:  # noqa: BLE001
                    pass
        else:
            job.status = "error"
            job.error = result.get("error")
            job.error_type = result.get("error_type")
            job.result = result


def _run_job(kind: str, target: JobTarget) -> dict[str, Any]:
    """Run ``target(on_progress)`` in a daemon thread; return a job handle."""
    job = _Job(id=uuid4().hex, kind=kind)
    with _jobs_lock:
        _jobs[job.id] = job

    def worker() -> None:
        try:
            result = target(lambda phase, frac, msg: _update_job(job, phase, frac, msg))
        except Exception as exc:  # noqa: BLE001 - never let a job thread die silently
            logger.exception("job %s crashed", kind)
            try:
                from plg_sentry import capture_exception

                capture_exception(exc)
            except Exception:  # noqa: BLE001
                pass
            result = _err(str(exc), "unknown")
        _finish_job(job, result)

    threading.Thread(target=worker, daemon=True, name=f"plg-{kind}").start()
    return {"ok": True, "job_id": job.id, "kind": kind, "status": "running"}


def get_job(job_id: str) -> dict[str, Any]:
    """Poll a job's state. Returns status=unknown for stale/unknown ids."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        return {"ok": False, "status": "unknown", "error": "Unknown job id.", "job_id": job_id}
    return job.snapshot()


def start_beat(prompt: str, locale: str | None = None) -> dict[str, Any]:
    """Async create_beat. UI polls get_job(job_id) for phase/elapsed/result."""
    prompt = (prompt or "").strip()
    if locale:
        set_ui_locale(locale)
    loc = locale or _ui_locale
    return _run_job("beat", lambda prog: create_beat(prompt, on_progress=prog, locale=loc))


def start_regenerate(prompt: str | None = None) -> dict[str, Any]:
    return _run_job("beat", lambda prog: regenerate(prompt, on_progress=prog))


def start_open_in_fl() -> dict[str, Any]:
    """Async open_in_fl — keeps the UI thread free while scanning/launching."""
    return _run_job("open_fl", lambda _prog: open_in_fl())


def start_stem_split(source: str) -> dict[str, Any]:
    return _run_job("stems", lambda prog: split_stems_file(source, on_progress=prog))


def clear_finished_jobs() -> dict[str, Any]:
    """Drop done/error jobs from the registry (housekeeping)."""
    with _jobs_lock:
        stale = [jid for jid, job in _jobs.items() if job.status in ("done", "error")]
        for jid in stale:
            del _jobs[jid]
    return {"ok": True, "cleared": len(stale)}


APP_VERSION = app_version()


def check_for_updates() -> dict[str, Any]:
    try:
        from plg_updater import check_for_updates as _check

        return _check()
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), "unknown")


def download_update() -> dict[str, Any]:
    try:
        from plg_updater import download_update as _download

        return _download()
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), "unknown")


def apply_downloaded_update() -> dict[str, Any]:
    try:
        from plg_updater import apply_downloaded_update as _apply

        return _apply()
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), "unknown")


DOC_FILES = {
    "start_here": "START_HERE.md",
    "fl_bridge": "FL_BRIDGE.md",
    "fl_scripts": "FL_SCRIPTS.md",
    "fl_workflows": "FL_WORKFLOWS.md",
    "fl_versions": "FL_VERSIONS.md",
    "terms": "legal/TERMS_RU.md",
    "terms_en": "legal/TERMS_EN.md",
    "privacy": "legal/PRIVACY_RU.md",
    "privacy_en": "legal/PRIVACY_EN.md",
    "refund": "legal/REFUND.md",
    "business": "legal/BUSINESS_RU.md",
}


def import_kit_folder(source: str) -> dict[str, Any]:
    """Copy kit download into PLG_Library layout and rescan."""
    from organize_kit import organize_library

    src = Path((source or "").strip())
    if not src.is_dir():
        return _err(f"Folder not found: {source}", "not_found")

    samples_dir = Path(get_samples_dir())
    try:
        counts = organize_library(src.resolve(), samples_dir.resolve())
        catalog = _scan_library(samples_dir)
        save_catalog(catalog, CATALOG_FILE)
    except OSError as exc:
        return _err(str(exc), "io")

    imported = sum(counts.values())
    return {
        "ok": True,
        "imported": imported,
        "counts": counts,
        "root": catalog["root"],
        "total": catalog["total"],
        "audio_total": catalog.get("audio_total", 0),
        "message": f"Imported {imported} files into library.",
    }


def get_app_info() -> dict[str, Any]:
    """Version, paths, starter pack, FL — for Settings / Help."""
    from starter_kit import starter_kit_info

    fl_exe = find_fl_executable()
    starter = starter_kit_info()
    try:
        from stem_split import stems_available
        demucs = stems_available()
    except Exception:  # noqa: BLE001
        demucs = False

    docs = {
        key: str(PROJECT_DIR / name)
        for key, name in DOC_FILES.items()
        if (PROJECT_DIR / name).is_file()
    }
    return {
        "ok": True,
        "version": APP_VERSION,
        "project_dir": str(PROJECT_DIR),
        "fl_executable": str(fl_exe) if fl_exe else None,
        "fl_bridge_ready": is_fl_bridge_ready(PROJECT_DIR),
        "demucs_available": demucs,
        "starter": starter,
        "docs": docs,
        "quota": get_quota(),
    }


def open_document(doc_id: str) -> dict[str, Any]:
    """Reveal a shipped markdown doc in Explorer."""
    name = DOC_FILES.get(doc_id)
    if not name:
        return _err(f"Unknown document: {doc_id}", "validation")
    path = PROJECT_DIR / name
    if not path.is_file():
        return _err(f"Document missing: {name}", "not_found")
    return reveal_path(str(path))


def stems_status() -> dict[str, Any]:
    try:
        from stem_split import stems_available

        ok = stems_available()
    except Exception:  # noqa: BLE001
        ok = False
    return {
        "ok": True,
        "available": ok,
        "hint": "pip install -r requirements-optional.txt" if not ok else "Demucs ready",
    }


__all__ = [
    # settings
    "get_settings",
    "save_settings",
    # status / quota / library
    "get_status",
    "get_quota",
    "scan_library",
    # actions (sync)
    "create_beat",
    "regenerate",
    "open_in_fl",
    "install_fl_scripts",
    "reveal_path",
    "chaos_roll",
    "flip_beat",
    "bake_session",
    "set_filth_mode",
    "get_producer_blueprint",
    "import_kit_folder",
    "get_app_info",
    "open_document",
    "stems_status",
    "get_auth_status",
    "cloud_signup",
    "cloud_delete_account",
    "cloud_login",
    "cloud_logout",
    "cloud_reset_password",
    "cloud_billing_status",
    "cloud_billing_checkout",
    "cloud_fetch_status",
    "cloud_submit_feedback",
    "set_ui_locale",
    "check_for_updates",
    "download_update",
    "apply_downloaded_update",
    "open_external_url",
    "split_stems_file",
    # actions (async job)
    "start_beat",
    "start_regenerate",
    "start_open_in_fl",
    "start_stem_split",
    "get_job",
    "clear_finished_jobs",
]


if __name__ == "__main__":
    # Quick smoke check without any UI: prints status as JSON.
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(get_status(), ensure_ascii=False, indent=2))
