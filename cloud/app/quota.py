"""Server-side beat quota — 30 / 30 days + 3 / day + trial + grace."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from supabase import Client

from cloud.app.billing import apply_grace_expiry, billing_snapshot, trial_remaining
from cloud.app.config import BEAT_LIMIT, DAILY_BEAT_LIMIT, PERIOD_DAYS, TRIAL_BEATS


logger = logging.getLogger("plg.quota")


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def roll_profile(row: dict[str, Any]) -> dict[str, Any]:
    row = apply_grace_expiry(dict(row))
    today = _utc_today()
    period_start = _parse_ts(str(row["period_start"]))
    daily_reset = date.fromisoformat(str(row["daily_reset"])[:10])

    beats_used = int(row.get("beats_used") or 0)
    beats_today = int(row.get("beats_today") or 0)

    if today > daily_reset:
        beats_today = 0
        daily_reset = today

    status = str(row.get("status") or "expired")
    if status in ("active", "grace"):
        while datetime.now(timezone.utc) >= period_start + timedelta(days=PERIOD_DAYS):
            period_start = period_start + timedelta(days=PERIOD_DAYS)
            beats_used = 0

    row["period_start"] = period_start.isoformat()
    row["beats_used"] = beats_used
    row["beats_today"] = beats_today
    row["daily_reset"] = daily_reset.isoformat()
    return row


def quota_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    row = roll_profile(dict(row))
    status = str(row.get("status") or "expired")
    period_start = _parse_ts(str(row["period_start"]))
    period_end = period_start + timedelta(days=PERIOD_DAYS)
    days_until = max(0, (period_end.date() - _utc_today()).days)
    used = int(row["beats_used"])
    today_used = int(row["beats_today"])

    if status == "trial":
        remaining = trial_remaining(row)
        limit = TRIAL_BEATS
    else:
        remaining = max(0, BEAT_LIMIT - used)
        limit = BEAT_LIMIT

    daily_remaining = max(0, DAILY_BEAT_LIMIT - today_used)
    snap = {
        "used": used if status != "trial" else int(row.get("trial_beats_used") or 0),
        "limit": limit,
        "remaining": remaining,
        "beats_today": today_used,
        "daily_limit": DAILY_BEAT_LIMIT,
        "daily_remaining": daily_remaining,
        "days_until_reset": days_until,
        "period_days": PERIOD_DAYS,
        "plan": row.get("plan", "base"),
        "status": status,
        "billing": billing_snapshot(row),
    }
    return snap


def ensure_can_generate(row: dict[str, Any]) -> dict[str, Any]:
    row = roll_profile(dict(row))
    status = str(row.get("status") or "expired")
    snap = quota_snapshot(row)

    if status == "trial":
        if snap["remaining"] <= 0:
            raise HTTPException(
                402,
                f"Trial ended ({TRIAL_BEATS} free beats). Subscribe to continue.",
            )
        if snap["daily_remaining"] <= 0:
            raise HTTPException(
                429,
                f"Daily limit reached ({DAILY_BEAT_LIMIT} beats / day). Try again tomorrow.",
            )
        return row

    if status not in ("active", "grace"):
        raise HTTPException(402, "Subscription inactive. Renew to generate beats.")

    if snap["remaining"] <= 0:
        raise HTTPException(
            429,
            f"Monthly limit reached ({BEAT_LIMIT} beats / {PERIOD_DAYS} days). "
            f"Resets in {snap['days_until_reset']} days.",
        )
    if snap["daily_remaining"] <= 0:
        raise HTTPException(
            429,
            f"Daily limit reached ({DAILY_BEAT_LIMIT} beats / day). Try again tomorrow.",
        )
    return row


def consume_beat(client: Client, user_id: str, row: dict[str, Any]) -> dict[str, Any]:
    before = quota_snapshot(row)
    row = ensure_can_generate(row)
    status = str(row.get("status") or "expired")
    now = datetime.now(timezone.utc).isoformat()

    if status == "trial":
        row["trial_beats_used"] = int(row.get("trial_beats_used") or 0) + 1
        row["beats_today"] = int(row.get("beats_today") or 0) + 1
        if int(row["trial_beats_used"]) >= TRIAL_BEATS:
            row["status"] = "expired"
    else:
        row["beats_used"] = int(row["beats_used"]) + 1
        row["beats_today"] = int(row["beats_today"]) + 1

    row["updated_at"] = now
    update = {
        "period_start": row["period_start"],
        "beats_used": row["beats_used"],
        "beats_today": row["beats_today"],
        "daily_reset": row["daily_reset"],
        "trial_beats_used": row.get("trial_beats_used", 0),
        "status": row.get("status"),
        "updated_at": now,
    }
    client.table("profiles").update(update).eq("id", user_id).execute()
    snap = quota_snapshot(row)
    _maybe_notify_quota_limit(client, user_id, before, snap)
    return snap


def _maybe_notify_quota_limit(
    client: Client,
    user_id: str,
    before: dict[str, Any],
    after: dict[str, Any],
) -> None:
    try:
        from cloud.app.email import notify_quota_limit
        from cloud.app.legal import _user_email

        email = _user_email(client, user_id)
        if not email:
            return
        if int(before.get("daily_remaining") or 0) > 0 and int(after.get("daily_remaining") or 0) == 0:
            notify_quota_limit(client, user_id, email, daily=True)
        status = str(after.get("status") or "")
        if (
            status in ("active", "grace")
            and int(before.get("remaining") or 0) > 0
            and int(after.get("remaining") or 0) == 0
        ):
            notify_quota_limit(
                client,
                user_id,
                email,
                daily=False,
                days=int(after.get("days_until_reset") or 0),
            )
    except Exception:  # noqa: BLE001
        logger.exception("quota limit email failed user=%s", user_id)


def save_profile(client: Client, user_id: str, row: dict[str, Any]) -> None:
    client.table("profiles").update(
        {
            "period_start": row["period_start"],
            "beats_used": row["beats_used"],
            "beats_today": row["beats_today"],
            "daily_reset": row["daily_reset"],
            "status": row.get("status"),
            "trial_beats_used": row.get("trial_beats_used", 0),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", user_id).execute()
