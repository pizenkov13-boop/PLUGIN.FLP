"""Server-side LLM generation — keys never leave the server."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend_core import build_system_instruction, generate_pattern, load_user_profile  # noqa: E402
from cloud.app.config import EST_COST_BASE, EST_COST_PREMIUM  # noqa: E402
from cloud.app.pattern_validate import validate_pattern  # noqa: E402
from sample_catalog import format_catalog_for_prompt  # noqa: E402

logger = logging.getLogger("plg.cloud.llm")


def _empty_catalog() -> dict[str, Any]:
    return {
        "root": "",
        "total": 0,
        "audio_total": 0,
        "audio": {},
        "midi": [],
        "presets": [],
        "projects": [],
        "banks": [],
        "plugins": [],
    }


def _resolve_provider(plan: str) -> None:
    if plan == "premium":
        os.environ["PLG_LLM_PROVIDER"] = "anthropic"
    else:
        os.environ["PLG_LLM_PROVIDER"] = "gemini"


def generate_beat_pattern(
    prompt: str,
    *,
    plan: str = "base",
    catalog: dict[str, Any] | None = None,
    user_profile: dict[str, Any] | None = None,
    locale: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Returns (pattern, meta) where meta has model + estimated cost."""
    _resolve_provider(plan)

    cat = catalog if isinstance(catalog, dict) and catalog.get("root") is not None else _empty_catalog()
    if cat.get("total", 0) == 0 and not cat.get("audio_total"):
        cat = _empty_catalog()

    profile = user_profile if isinstance(user_profile, dict) else load_user_profile()
    system_instruction = build_system_instruction(profile, cat)

    from prompt_locale import apply_prompt_metadata, prepare_prompt_for_llm

    prepared = prepare_prompt_for_llm(prompt, locale)

    try:
        raw = generate_pattern(prepared["llm_prompt"], system_instruction)
    except Exception as exc:
        logger.exception("LLM generation failed")
        # Fallback: retry once on base model if premium failed
        if plan == "premium":
            try:
                os.environ["PLG_LLM_PROVIDER"] = "gemini"
                raw = generate_pattern(prepared["llm_prompt"], system_instruction)
                plan = "base"
            except Exception:
                raise HTTPException(503, "AI provider busy. Try again in a minute.") from exc
        else:
            raise HTTPException(503, "AI provider busy. Try again in a minute.") from exc

    pattern = validate_pattern(raw)
    pattern = apply_prompt_metadata(pattern, prepared)
    from llm_client import provider_label

    cost = EST_COST_PREMIUM if plan == "premium" else EST_COST_BASE
    meta = {
        "model": provider_label(),
        "plan": plan,
        "cost_usd": cost,
        "prompt_chars": len(prompt),
    }
    return pattern, meta
