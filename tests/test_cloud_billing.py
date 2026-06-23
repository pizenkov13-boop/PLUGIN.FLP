"""Tests for billing logic (trial, grace, geo prices)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from unittest.mock import MagicMock

import pytest

from cloud.app.billing import (
    apply_grace_expiry,
    billing_snapshot,
    pick_checkout_provider,
    price_label,
    resolve_price_tier,
    trial_remaining,
)
from cloud.app.quota import ensure_can_generate, quota_snapshot, roll_profile
from fastapi import HTTPException


def _row(**kwargs) -> dict:
    now = datetime.now(timezone.utc)
    base = {
        "plan": "base",
        "status": "active",
        "period_start": now.isoformat(),
        "beats_used": 0,
        "beats_today": 0,
        "daily_reset": now.date().isoformat(),
        "trial_beats_used": 0,
        "price_tier": "cis",
    }
    base.update(kwargs)
    return base


def test_price_label_cis():
    assert "₽" in price_label("cis")


def test_price_label_intl():
    assert "$" in price_label("intl")


def test_resolve_price_tier_ru():
    assert resolve_price_tier(None, "ru-RU") == "cis"


def test_resolve_price_tier_en():
    assert resolve_price_tier(None, "en-US") == "intl"


def test_trial_remaining():
    assert trial_remaining(_row(status="trial", trial_beats_used=1)) == 2


def test_grace_expires():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    row = _row(status="grace", grace_until=past.isoformat())
    out = apply_grace_expiry(row)
    assert out["status"] == "expired"


def test_trial_blocks_when_exhausted():
    row = _row(status="trial", trial_beats_used=3)
    with pytest.raises(HTTPException) as exc:
        ensure_can_generate(row)
    assert exc.value.status_code == 402


def test_billing_snapshot_trial():
    snap = billing_snapshot(_row(status="trial", trial_beats_used=1))
    assert snap["trial_remaining"] == 2
    assert snap["can_subscribe"] is True


def test_quota_trial_uses_trial_limit():
    snap = quota_snapshot(_row(status="trial", trial_beats_used=0))
    assert snap["limit"] == 3
    assert snap["remaining"] == 3


def test_intl_checkout_blocked_without_flag():
    client = MagicMock()
    with pytest.raises(HTTPException) as exc:
        pick_checkout_provider("intl", client=client)
    assert exc.value.status_code == 503
