"""Transactional email — Resend API + notification log."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from supabase import Client

from cloud.app.config import EMAIL_FROM, RESEND_API_KEY, SUPPORT_EMAIL

logger = logging.getLogger("plg.email")

TEMPLATES: dict[str, str] = {
    "payment_success": "PLUGIN.FLP — payment received. Your subscription is active for 30 days.",
    "subscription_expiring": "PLUGIN.FLP — subscription ends in {days} days. Renew in Settings to keep generating beats.",
    "quota_daily_limit": "PLUGIN.FLP — daily beat limit reached (3/day). Resets tomorrow.",
    "quota_monthly_limit": "PLUGIN.FLP — monthly beat limit reached. Resets in {days} days or upgrade.",
    "welcome": "Welcome to PLUGIN.FLP — 3 trial beats included. Describe a beat and open FL Studio.",
}


def _log_notification(
    client: Client,
    *,
    user_id: str | None,
    template: str,
    recipient: str,
    status: str,
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    try:
        client.table("notification_log").insert(
            {
                "user_id": user_id,
                "channel": "email",
                "template": template,
                "recipient": recipient,
                "status": status,
                "error": error,
                "metadata": metadata or {},
            }
        ).execute()
    except Exception:  # noqa: BLE001
        logger.warning("notification_log insert failed")


def send_email(
    client: Client,
    *,
    to: str,
    subject: str,
    body: str,
    template: str,
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    if not to or "@" not in to:
        return False

    if not RESEND_API_KEY:
        logger.info("email skipped (no RESEND_API_KEY) to=%s template=%s", to, template)
        _log_notification(
            client,
            user_id=user_id,
            template=template,
            recipient=to,
            status="queued",
            metadata=metadata,
        )
        return False

    try:
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={"from": EMAIL_FROM, "to": [to], "subject": subject, "text": body},
            timeout=20.0,
        )
        if resp.status_code >= 400:
            _log_notification(
                client,
                user_id=user_id,
                template=template,
                recipient=to,
                status="failed",
                error=resp.text,
                metadata=metadata,
            )
            return False
        _log_notification(
            client,
            user_id=user_id,
            template=template,
            recipient=to,
            status="sent",
            metadata=metadata,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        _log_notification(
            client,
            user_id=user_id,
            template=template,
            recipient=to,
            status="failed",
            error=str(exc),
            metadata=metadata,
        )
        return False


def notify_payment_success(client: Client, user_id: str, email: str) -> None:
    send_email(
        client,
        to=email,
        subject="PLUGIN.FLP — subscription active",
        body=TEMPLATES["payment_success"],
        template="payment_success",
        user_id=user_id,
    )


def notify_subscription_expiring(client: Client, user_id: str, email: str, *, days: int) -> bool:
    body = TEMPLATES["subscription_expiring"].format(days=days)
    return send_email(
        client,
        to=email,
        subject="PLUGIN.FLP — subscription ending soon",
        body=body,
        template="subscription_expiring",
        user_id=user_id,
        metadata={"days": days},
    )


def notify_quota_limit(client: Client, user_id: str, email: str, *, daily: bool, days: int = 0) -> bool:
    key = "quota_daily_limit" if daily else "quota_monthly_limit"
    body = TEMPLATES[key].format(days=days)
    return send_email(
        client,
        to=email,
        subject="PLUGIN.FLP — beat limit reached",
        body=body,
        template=key,
        user_id=user_id,
    )
