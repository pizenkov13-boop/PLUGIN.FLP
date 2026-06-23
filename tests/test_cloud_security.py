"""Tests for Phase 3 security modules."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from cloud.app.moderation import moderate_prompt
from cloud.app.rate_limit import SlidingWindow, check_generate_limits
from cloud.app.security import check_honeypot, fingerprint


def test_honeypot_blocks():
    with pytest.raises(HTTPException) as exc:
        check_honeypot("spam@bot.com")
    assert exc.value.status_code == 400


def test_honeypot_allows_empty():
    check_honeypot("")
    check_honeypot(None)


def test_fingerprint_stable():
    a = fingerprint("device-1", "1.2.3.4")
    b = fingerprint("device-1", "1.2.3.4")
    assert a == b
    assert fingerprint("device-2", "1.2.3.4") != a


def test_moderation_blocks_illegal():
    with pytest.raises(HTTPException):
        moderate_prompt("make child porn beat")


def test_moderation_allows_trap():
    assert moderate_prompt("dark trap beat 140 bpm") == "dark trap beat 140 bpm"


def test_sliding_window():
    w = SlidingWindow()
    assert w.allow("k", 2, 60.0)
    assert w.allow("k", 2, 60.0)
    assert not w.allow("k", 2, 60.0)


def test_generate_cooldown():
    user = "test-user-cooldown-xyz"
    check_generate_limits(user)
    with pytest.raises(HTTPException) as exc:
        check_generate_limits(user)
    assert exc.value.status_code == 429
