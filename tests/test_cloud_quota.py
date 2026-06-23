"""Tests for server-side quota logic."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from fastapi import HTTPException

from cloud.app.quota import ensure_can_generate, quota_snapshot, roll_profile


def _row(
    *,
    beats_used: int = 0,
    beats_today: int = 0,
    period_start: datetime | None = None,
    daily_reset: date | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "plan": "base",
        "status": "active",
        "period_start": (period_start or now).isoformat(),
        "beats_used": beats_used,
        "beats_today": beats_today,
        "daily_reset": (daily_reset or now.date()).isoformat(),
        "trial_beats_used": 0,
    }


def test_quota_snapshot_remaining():
    snap = quota_snapshot(_row(beats_used=5))
    assert snap["remaining"] == 25
    assert snap["limit"] == 30


def test_daily_limit_blocks():
    row = _row(beats_used=0, beats_today=3)
    with pytest.raises(HTTPException) as exc:
        ensure_can_generate(row)
    assert exc.value.status_code == 429


def test_monthly_limit_blocks():
    row = _row(beats_used=30, beats_today=0)
    with pytest.raises(HTTPException) as exc:
        ensure_can_generate(row)
    assert exc.value.status_code == 429


def test_roll_period_resets_monthly():
    old_start = datetime.now(timezone.utc) - timedelta(days=31)
    row = _row(beats_used=30, beats_today=2, period_start=old_start)
    rolled = roll_profile(row)
    assert rolled["beats_used"] == 0


def test_roll_daily_resets_today():
    yesterday = date.today() - timedelta(days=1)
    row = _row(beats_today=3, daily_reset=yesterday)
    rolled = roll_profile(row)
    assert rolled["beats_today"] == 0


def test_expired_blocks():
    row = _row(beats_used=0, beats_today=0)
    row["status"] = "expired"
    with pytest.raises(HTTPException) as exc:
        ensure_can_generate(row)
    assert exc.value.status_code == 402
