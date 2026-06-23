"""IP/fingerprint extraction, bans, honeypot, device binding."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, Request
from supabase import Client

from cloud.app.config import REQUIRE_DEVICE_BINDING

logger = logging.getLogger("plg.security")


def client_ip(request: Request) -> str:
    cf = request.headers.get("CF-Connecting-IP", "").strip()
    if cf:
        return cf
    forwarded = request.headers.get("X-Forwarded-For", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host or ""
    return ""


def fingerprint(device_id: str | None, ip: str) -> str:
    raw = f"{(device_id or '').strip()}|{ip.strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def check_honeypot(value: str | None) -> None:
    if value and str(value).strip():
        raise HTTPException(400, "Request rejected.")


def _ban_active(row: dict[str, Any] | None) -> bool:
    if not row:
        return False
    expires = row.get("expires_at")
    if expires:
        exp = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > exp:
            return False
    return True


def is_banned(
    client: Client,
    *,
    user_id: str | None = None,
    device_id: str | None = None,
    ip: str | None = None,
    fp: str | None = None,
) -> str | None:
    profile_ban = None
    if user_id:
        prof = client.table("profiles").select("banned,ban_reason").eq("id", user_id).maybe_single().execute()
        if prof.data and prof.data.get("banned"):
            return str(prof.data.get("ban_reason") or "Account banned.")

    checks: list[tuple[str, str]] = []
    if user_id:
        checks.append(("user", user_id))
    if device_id:
        checks.append(("device", device_id))
    if ip:
        checks.append(("ip", ip))
    if fp:
        checks.append(("fingerprint", fp))

    for ban_type, ban_value in checks:
        result = (
            client.table("security_bans")
            .select("*")
            .eq("ban_type", ban_type)
            .eq("ban_value", ban_value)
            .maybe_single()
            .execute()
        )
        if _ban_active(result.data):
            return str(result.data.get("reason") or f"Banned ({ban_type}).")
    return None


def enforce_not_banned(
    client: Client,
    *,
    user_id: str,
    device_id: str | None = None,
    ip: str | None = None,
) -> None:
    fp = fingerprint(device_id, ip or "")
    reason = is_banned(client, user_id=user_id, device_id=device_id, ip=ip, fp=fp)
    if reason:
        raise HTTPException(403, reason)


def require_registered_device(client: Client, user_id: str, device_id: str | None) -> str:
    device_id = (device_id or "").strip()
    if not device_id:
        if REQUIRE_DEVICE_BINDING:
            raise HTTPException(400, "Missing device_id. Update the desktop app.")
        return ""

    existing = (
        client.table("user_devices")
        .select("id")
        .eq("user_id", user_id)
        .eq("device_id", device_id)
        .maybe_single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(
            403,
            "Unknown device. Sign out and sign in again to bind this PC.",
        )
    return device_id


def claim_device_trial(client: Client, device_id: str, user_id: str) -> bool:
    """Return True if this device may use trial; False if trial already claimed elsewhere."""
    device_id = (device_id or "").strip()
    if not device_id:
        return True

    existing = (
        client.table("device_trial_claims")
        .select("*")
        .eq("device_id", device_id)
        .maybe_single()
        .execute()
    )
    if existing.data:
        return str(existing.data.get("first_user_id")) == user_id

    client.table("device_trial_claims").insert(
        {"device_id": device_id, "first_user_id": user_id}
    ).execute()
    return True


def block_trial_farming(client: Client, user_id: str, device_id: str | None) -> None:
    if not claim_device_trial(client, device_id or "", user_id):
        client.table("profiles").update(
            {
                "status": "expired",
                "ban_reason": "Trial already used on this device.",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", user_id).execute()
        logger.warning("trial farming blocked user=%s device=%s", user_id, device_id)
