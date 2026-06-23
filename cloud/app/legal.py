"""Legal constants, GDPR deletion, log retention."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from supabase import Client

from cloud.app.config import (
    LEGAL_AGE_MIN,
    LEGAL_PRIVACY_VERSION,
    LEGAL_TERMS_VERSION,
    PAYMENT_LOG_RETENTION_DAYS,
    PROMPT_LOG_RETENTION_DAYS,
    DATA_REGION,
    SUPPORT_EMAIL,
)

logger = logging.getLogger("plg.legal")

LEGAL_DOCS = {
    "terms_version": LEGAL_TERMS_VERSION,
    "privacy_version": LEGAL_PRIVACY_VERSION,
    "min_age": LEGAL_AGE_MIN,
    "data_region": DATA_REGION,
    "support_email": SUPPORT_EMAIL,
    "prompt_log_retention_days": PROMPT_LOG_RETENTION_DAYS,
    "payment_log_retention_days": PAYMENT_LOG_RETENTION_DAYS,
}


def legal_snapshot() -> dict[str, Any]:
    return {
        "ok": True,
        **LEGAL_DOCS,
        "documents": {
            "terms": "legal/TERMS_RU.md",
            "terms_en": "legal/TERMS_EN.md",
            "privacy": "legal/PRIVACY_RU.md",
            "privacy_en": "legal/PRIVACY_EN.md",
            "refund": "legal/REFUND.md",
        },
        "disclaimers": {
            "ai_generated": (
                "Beats are AI-assisted. You are responsible for how you use and release outputs. "
                "PLUGIN.FLP is a tool, not a co-author."
            ),
            "sample_licenses": (
                "Imported kits and samples remain your responsibility. "
                "Ensure you have rights to use sounds in your projects."
            ),
            "beat_ownership": (
                "You own the output session files generated for your account, "
                "subject to third-party sample licenses you import."
            ),
        },
        "subscription": {
            "cancel_anytime": True,
            "refund_via_support": True,
            "auto_refund": False,
        },
    }


def record_acceptance(
    client: Client,
    user_id: str,
    *,
    terms_version: str,
    privacy_version: str,
    ip: str | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    client.table("profiles").update(
        {
            "terms_version": terms_version,
            "terms_accepted_at": now,
            "privacy_version": privacy_version,
            "age_confirmed_at": now,
            "updated_at": now,
        }
    ).eq("id", user_id).execute()

    rows = [
        {"user_id": user_id, "doc_type": "terms", "doc_version": terms_version, "ip_address": ip},
        {"user_id": user_id, "doc_type": "privacy", "doc_version": privacy_version, "ip_address": ip},
        {"user_id": user_id, "doc_type": "age", "doc_version": str(LEGAL_AGE_MIN), "ip_address": ip},
    ]
    client.table("legal_acceptances").insert(rows).execute()


def require_terms_acceptance(accept_terms: bool, confirm_age: bool) -> None:
    if not accept_terms:
        raise HTTPException(400, "You must accept the Terms of Service and Privacy Policy.")
    if not confirm_age:
        raise HTTPException(400, f"You must confirm you are at least {LEGAL_AGE_MIN} years old.")


def delete_user_account(client: Client, user_id: str) -> dict[str, Any]:
    """GDPR erasure — delete PII; anonymize payment records (retain 2+ years)."""
    email = _user_email(client, user_id)
    now = datetime.now(timezone.utc).isoformat()
    client.table("profiles").update({"deletion_requested_at": now}).eq("id", user_id).execute()

    client.table("generation_logs").delete().eq("user_id", user_id).execute()
    client.table("user_devices").delete().eq("user_id", user_id).execute()
    client.table("legal_acceptances").delete().eq("user_id", user_id).execute()
    client.table("abuse_alerts").update({"user_id": None}).eq("user_id", user_id).execute()
    client.table("payment_events").update({"user_id": None}).eq("user_id", user_id).execute()

    if email:
        client.table("waitlist_entries").delete().eq("email", email.lower()).execute()

    client.table("profiles").delete().eq("id", user_id).execute()

    try:
        client.auth.admin.delete_user(user_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("auth delete failed user=%s", user_id)
        raise HTTPException(500, "Account deletion failed. Contact support.") from exc

    logger.info("account deleted user=%s", user_id)
    return {"ok": True, "message": "Account and personal data deleted."}


def _user_email(client: Client, user_id: str) -> str:
    try:
        resp = client.auth.admin.get_user_by_id(user_id)
        user = getattr(resp, "user", None) or (resp.get("user") if isinstance(resp, dict) else None)
        if user:
            return str(getattr(user, "email", None) or user.get("email") or "")
    except Exception:  # noqa: BLE001
        pass
    return ""


def purge_generation_logs(client: Client) -> dict[str, Any]:
    """Delete generation metadata older than retention window (no prompt text stored)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=PROMPT_LOG_RETENTION_DAYS)
    cutoff_iso = cutoff.isoformat()

    old = client.table("generation_logs").select("id").lt("created_at", cutoff_iso).execute()
    ids = [row["id"] for row in (old.data or [])]
    if not ids:
        return {"ok": True, "purged": 0}

    for batch_start in range(0, len(ids), 100):
        batch = ids[batch_start : batch_start + 100]
        client.table("generation_logs").delete().in_("id", batch).execute()

    logger.info("purged %s generation_logs older than %s days", len(ids), PROMPT_LOG_RETENTION_DAYS)
    return {"ok": True, "purged": len(ids), "retention_days": PROMPT_LOG_RETENTION_DAYS}
