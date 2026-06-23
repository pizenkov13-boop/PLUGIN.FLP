"""Tests for multilingual prompt bridge."""

from __future__ import annotations

from prompt_locale import detect_tags, prepare_prompt_for_llm


def test_detect_russian_opium_tags():
    tags = detect_tags("мрачный опиум бит с жёстким 808", "ru")
    assert "OPIUM" in tags
    assert any("MOOD" in t for t in tags)


def test_prepare_enriches_llm_prompt():
    prep = prepare_prompt_for_llm("dark rage beat hard 808", "en")
    assert "OPIUM" in prep["plg_style_tags"] or "RAGE" in prep["plg_style_tags"]
    assert prep["user_prompt"] == "dark rage beat hard 808"
    assert "PLG tags" in prep["llm_prompt"]


def test_arabic_locale_preserved():
    prep = prepare_prompt_for_llm("رايج مظلم", "ar")
    assert prep["plg_locale"] == "ar"
