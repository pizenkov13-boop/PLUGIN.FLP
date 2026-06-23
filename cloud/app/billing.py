"""Subscription billing — activation, grace, idempotency, geo prices."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from supabase import Client

from cloud.app.config import (
    GRACE_DAYS,
    PERIOD_DAYS,
    PRICE_CIS_RUB,
    PRICE_INTL_USD_CENTS,
    TRIAL_BEATS,
)

logger = logging.getLogger("plg.billing")

ACTIVE_STATUSES = frozenset({"trial", "active", "grace"})


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def price_label(tier: str) -> str:
    if tier == "intl":
        dollars = PRICE_INTL_USD_CENTS / 100
        return f"${dollars:.2f}/mo"
    return f"{PRICE_CIS_RUB} ₽/mo"


def resolve_price_tier(explicit: str | None, locale_header: str | None) -> str:
    if explicit in ("cis", "intl"):
        return explicit
    lang = (locale_header or "").lower()
    cis_prefixes = ("ru", "uk", "be", "kk", "uz", "hy", "ka", "az", "ky", "tg")
    if any(lang.startswith(p) for p in cis_prefixes):
        return "cis"
    return "intl"


def trial_remaining(row: dict[str, Any]) -> int:
    used = int(row.get("trial_beats_used") or 0)
    return max(0, TRIAL_BEATS - used)


def apply_grace_expiry(row: dict[str, Any]) -> dict[str, Any]:
    status = str(row.get("status") or "expired")
    if status != "grace":
        return row
    grace_until = _parse_ts(row.get("grace_until"))
    if grace_until and _utc_now() > grace_until:
        row["status"] = "expired"
        row["grace_until"] = None
    return row


def billing_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    row = apply_grace_expiry(dict(row))
    status = str(row.get("status") or "expired")
    tier = str(row.get("price_tier") or "cis")
    ends_at = _parse_ts(row.get("subscription_ends_at"))
    grace_until = _parse_ts(row.get("grace_until"))

    grace_days_left = 0
    if status == "grace" and grace_until:
        grace_days_left = max(0, (grace_until.date() - _utc_now().date()).days)

    days_until_renewal = 0
    if ends_at and status in ("active", "grace"):
        days_until_renewal = max(0, (ends_at.date() - _utc_now().date()).days)

    return {
        "status": status,
        "price_tier": tier,
        "price_label": price_label(tier),
        "trial_beats": TRIAL_BEATS,
        "trial_remaining": trial_remaining(row) if status == "trial" else 0,
        "grace_days_left": grace_days_left,
        "subscription_ends_at": ends_at.isoformat() if ends_at else None,
        "days_until_renewal": days_until_renewal,
        "billing_provider": row.get("billing_provider"),
        "can_subscribe": status in ("trial", "expired", "cancelled", "grace"),
        "needs_payment": status in ("expired", "cancelled") or (
            status == "trial" and trial_remaining(row) <= 0
        ),
    }


def claim_idempotency(
    client: Client,
    *,
    provider: str,
    idempotency_key: str,
    event_type: str,
    user_id: str | None = None,
    amount_cents: int | None = None,
    currency: str | None = None,
    external_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> bool:
    """Return True if this event was already processed (duplicate webhook)."""
    existing = (
        client.table("payment_events")
        .select("id")
        .eq("provider", provider)
        .eq("idempotency_key", idempotency_key)
        .maybe_single()
        .execute()
    )
    if existing.data:
        logger.info("duplicate payment event provider=%s key=%s", provider, idempotency_key)
        return True

    client.table("payment_events").insert(
        {
            "provider": provider,
            "idempotency_key": idempotency_key,
            "event_type": event_type,
            "user_id": user_id,
            "amount_cents": amount_cents,
            "currency": currency,
            "external_id": external_id,
            "payload": payload or {},
        }
    ).execute()
    return False


def activate_subscription(
    client: Client,
    user_id: str,
    *,
    provider: str,
    external_id: str,
    price_tier: str,
    period_days: int = PERIOD_DAYS,
) -> dict[str, Any]:
    now = _utc_now()
    ends = now + timedelta(days=period_days)
    patch = {
        "status": "active",
        "billing_provider": provider,
        "price_tier": price_tier,
        "external_subscription_id": external_id,
        "subscription_ends_at": ends.isoformat(),
        "grace_until": None,
        "period_start": now.isoformat(),
        "beats_used": 0,
        "beats_today": 0,
        "updated_at": now.isoformat(),
    }
    client.table("profiles").update(patch).eq("id", user_id).execute()
    logger.info("subscription activated user=%s provider=%s tier=%s", user_id, provider, price_tier)
    result = client.table("profiles").select("*").eq("id", user_id).single().execute()
    return result.data or patch


def enter_grace_period(client: Client, user_id: str) -> None:
    now = _utc_now()
    grace_until = now + timedelta(days=GRACE_DAYS)
    client.table("profiles").update(
        {
            "status": "grace",
            "grace_until": grace_until.isoformat(),
            "updated_at": now.isoformat(),
        }
    ).eq("id", user_id).execute()
    logger.info("grace period user=%s until=%s", user_id, grace_until.isoformat())


def expire_subscription(client: Client, user_id: str) -> None:
    now = _utc_now()
    client.table("profiles").update(
        {
            "status": "expired",
            "grace_until": None,
            "updated_at": now.isoformat(),
        }
    ).eq("id", user_id).execute()
    logger.info("subscription expired user=%s", user_id)


def cancel_subscription(client: Client, user_id: str) -> None:
    now = _utc_now()
    client.table("profiles").update(
        {
            "status": "cancelled",
            "updated_at": now.isoformat(),
        }
    ).eq("id", user_id).execute()
    logger.info("subscription cancelled user=%s", user_id)


def pick_checkout_provider(price_tier: str) -> str:
    from cloud.app.config import PADDLE_API_KEY, STRIPE_SECRET_KEY, YOOKASSA_SECRET_KEY, YOOKASSA_SHOP_ID

    if price_tier == "cis":
        if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY:
            return "yookassa"
        raise HTTPException(503, "ЮKassa not configured for CIS checkout.")
    if STRIPE_SECRET_KEY and STRIPE_PRICE_ID_INTL:
        return "stripe"
    if PADDLE_API_KEY:
        return "paddle"
    raise HTTPException(503, "International billing not configured yet (Stripe/Paddle).")
