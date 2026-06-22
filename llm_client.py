"""PLG LLM providers — Gemini for dev, Anthropic for release."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

DEFAULT_PROVIDER = "gemini"
GEMINI_MODEL = "gemini-2.5-flash"
CLAUDE_MODEL = "claude-sonnet-4-6"
LLM_TIMEOUT_MS = int(os.environ.get("PLG_LLM_TIMEOUT_MS", "90000"))
LLM_RETRY_ATTEMPTS = int(os.environ.get("PLG_LLM_RETRY_ATTEMPTS", "2"))


def get_provider() -> str:
    raw = (os.environ.get("PLG_LLM_PROVIDER") or DEFAULT_PROVIDER).strip().lower()
    if raw in ("gemini", "google"):
        return "gemini"
    if raw in ("anthropic", "claude"):
        return "anthropic"
    raise EnvironmentError(
        f"Unknown PLG_LLM_PROVIDER={raw!r}. Use gemini (dev) or anthropic (release)."
    )


def provider_label() -> str:
    if get_provider() == "gemini":
        model = _gemini_model()
        return f"Gemini ({model})"
    return f"Claude ({_claude_model()})"


def _gemini_model() -> str:
    return os.environ.get("GEMINI_MODEL") or os.environ.get("PLG_GEMINI_MODEL") or GEMINI_MODEL


def _claude_model() -> str:
    return os.environ.get("PLG_CLAUDE_MODEL") or os.environ.get("ANTHROPIC_MODEL") or CLAUDE_MODEL


def _gemini_api_key() -> str:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY required when PLG_LLM_PROVIDER=gemini")
    return api_key


def _anthropic_api_key() -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY required when PLG_LLM_PROVIDER=anthropic")
    return api_key


def format_llm_error(exc: Exception) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    upper = text.upper()

    if "429" in text or "RESOURCE_EXHAUSTED" in upper or "QUOTA" in upper:
        model = _gemini_model()
        return (
            "Gemini quota exceeded (429).\n\n"
            f"Model: {model}\n\n"
            "What to do:\n"
            "1. Wait 1–2 minutes and try again\n"
            "2. Settings → new key from aistudio.google.com/apikey (starts with AIza)\n"
            "3. Or set GEMINI_MODEL=gemini-2.5-flash in .env\n"
            "4. Check usage: aistudio.google.com → API keys → Quota"
        )

    if "timeout" in text.lower() or "timed out" in text.lower():
        return (
            "Gemini did not answer in time.\n\n"
            "Check internet connection and API key in Settings."
        )

    if "API_KEY" in upper or "401" in text or "403" in text or "INVALID" in upper:
        return (
            "Invalid Gemini API key.\n\n"
            "Get a free key: aistudio.google.com/apikey\n"
            "Paste in Settings — should start with AIza"
        )

    if len(text) > 420:
        return text[:420] + "\n\n...(see plg_session.log for full error)"
    return text


def generate_pattern(
    prompt: str,
    system_instruction: str,
    json_schema: dict[str, Any],
) -> dict[str, Any]:
    if get_provider() == "gemini":
        return _generate_gemini(prompt, system_instruction, json_schema)
    return _generate_anthropic(prompt, system_instruction, json_schema)


def _generate_gemini(
    prompt: str,
    system_instruction: str,
    json_schema: dict[str, Any],
) -> dict[str, Any]:
    from google import genai
    from google.genai import types

    model = _gemini_model()
    logging.info("Gemini (%s)...", model)

    client = genai.Client(
        api_key=_gemini_api_key(),
        http_options=types.HttpOptions(
            timeout=LLM_TIMEOUT_MS,
            retry_options=types.HttpRetryOptions(attempts=LLM_RETRY_ATTEMPTS),
        ),
    )
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_json_schema=json_schema,
            temperature=0.85,
        ),
    )

    raw_text = response.text
    if not raw_text or not raw_text.strip():
        raise RuntimeError("Gemini returned an empty response.")

    data = json.loads(raw_text)
    if not isinstance(data, dict) or "tracks" not in data:
        raise RuntimeError("Expected JSON with bpm, tracks, build_order.")
    return data


def _generate_anthropic(
    prompt: str,
    system_instruction: str,
    json_schema: dict[str, Any],
) -> dict[str, Any]:
    import anthropic

    model = _claude_model()
    logging.info("Claude (%s)...", model)

    client = anthropic.Anthropic(
        api_key=_anthropic_api_key(),
        timeout=LLM_TIMEOUT_MS / 1000.0,
        max_retries=LLM_RETRY_ATTEMPTS,
    )
    tool = {
        "name": "beat_pattern",
        "description": "Beat pattern JSON for FL Studio File Bridge",
        "input_schema": json_schema,
    }

    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=system_instruction,
        messages=[{"role": "user", "content": prompt}],
        tools=[tool],
        tool_choice={"type": "tool", "name": "beat_pattern"},
        temperature=0.85,
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "beat_pattern":
            data = block.input
            if isinstance(data, dict) and "tracks" in data:
                return data
            raise RuntimeError("Claude tool output missing tracks.")

    raise RuntimeError("Claude did not return beat_pattern tool output.")
