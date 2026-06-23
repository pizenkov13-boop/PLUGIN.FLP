"""Localized strings for READ_ME_IMBA.txt."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from plg_paths import bundle_dir

_I18N_FILE = bundle_dir() / "assets" / "mix_blueprint_i18n.json"


@lru_cache(maxsize=1)
def _packs() -> dict[str, dict[str, str]]:
    if not _I18N_FILE.is_file():
        return {}
    raw = json.loads(_I18N_FILE.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if isinstance(v, dict)}


def blueprint_text(locale: str | None, key: str, **params: Any) -> str:
    loc = (locale or "en").lower()
    pack = _packs().get(loc) or _packs().get("en") or {}
    template = pack.get(key) or (_packs().get("en") or {}).get(key, key)
    try:
        return str(template).format(**params)
    except (KeyError, ValueError):
        return str(template)
