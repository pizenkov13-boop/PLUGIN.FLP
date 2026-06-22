"""Read and write PLG settings (.env) from the desktop app."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from library_paths import DEFAULT_LIBRARY_DIR, LEGACY_LIBRARY_DIR
from plg_paths import app_dir

PROJECT_DIR = app_dir()
ENV_FILE = PROJECT_DIR / ".env"
ENV_EXAMPLE = PROJECT_DIR / ".env.example"

MANAGED_KEYS = (
    "PLG_LLM_PROVIDER",
    "GEMINI_API_KEY",
    "ANTHROPIC_API_KEY",
    "PLG_SAMPLES_DIR",
    "GEMINI_MODEL",
    "PLG_CLAUDE_MODEL",
    "PLG_AUTO_OPEN_FL",
)


def load_environment() -> None:
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE, override=True)
    else:
        load_dotenv()


def read_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_FILE.exists():
        return values

    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def write_env_file(updates: dict[str, str]) -> None:
    current = read_env_file()
    current.update({key: value for key, value in updates.items() if value is not None})

    lines: list[str] = []
    written_keys: set[str] = set()

    if ENV_EXAMPLE.exists():
        for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                lines.append(line)
                continue
            if "=" not in stripped:
                lines.append(line)
                continue
            key = stripped.split("=", 1)[0].strip()
            if key in current:
                lines.append(f"{key}={current[key]}")
                written_keys.add(key)
            else:
                lines.append(line)

    for key, value in current.items():
        if key not in written_keys:
            lines.append(f"{key}={value}")

    ENV_FILE.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    load_dotenv(ENV_FILE, override=True)


def get_samples_dir() -> Path:
    load_environment()
    raw = os.environ.get("PLG_SAMPLES_DIR") or os.environ.get("PLG_LIBRARY_DIR")
    if raw:
        return Path(raw).expanduser().resolve()
    if DEFAULT_LIBRARY_DIR.is_dir():
        return DEFAULT_LIBRARY_DIR.resolve()
    if LEGACY_LIBRARY_DIR.is_dir():
        return LEGACY_LIBRARY_DIR.resolve()
    return DEFAULT_LIBRARY_DIR.resolve()


def has_api_key() -> bool:
    load_environment()
    provider = (os.environ.get("PLG_LLM_PROVIDER") or "gemini").strip().lower()
    if provider in ("anthropic", "claude"):
        return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
    return bool(
        os.environ.get("GEMINI_API_KEY", "").strip()
        or os.environ.get("GOOGLE_API_KEY", "").strip()
    )


def get_auto_open_fl() -> bool:
    load_environment()
    raw = (os.environ.get("PLG_AUTO_OPEN_FL") or "true").strip().lower()
    return raw not in ("0", "false", "no", "off")


def settings_snapshot() -> dict[str, str]:
    load_environment()
    return {
        "provider": os.environ.get("PLG_LLM_PROVIDER", "gemini"),
        "gemini_key": os.environ.get("GEMINI_API_KEY", ""),
        "anthropic_key": os.environ.get("ANTHROPIC_API_KEY", ""),
        "samples_dir": str(get_samples_dir()),
        "gemini_model": os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
        "claude_model": os.environ.get("PLG_CLAUDE_MODEL", "claude-sonnet-4-6"),
        "auto_open_fl": "true" if get_auto_open_fl() else "false",
    }
