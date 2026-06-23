"""Server-proxied signup with CAPTCHA + honeypot + device trial claim."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException
from supabase import Client

from cloud.app.captcha import verify_captcha
from cloud.app.security import block_trial_farming, check_honeypot, enforce_not_banned
from cloud.app.waitlist import consume_invite_code, validate_invite_code

logger = logging.getLogger("plg.signup")


async def signup_user(
    client: Client,
    *,
    email: str,
    password: str,
    device_id: str | None,
    captcha_token: str | None,
    honeypot: str | None,
    remote_ip: str | None,
    invite_code: str | None = None,
    accept_terms: bool = False,
    confirm_age: bool = False,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
    utm_content: str | None = None,
    referrer: str | None = None,
) -> dict[str, Any]:
    check_honeypot(honeypot)
    await verify_captcha(captcha_token, remote_ip)

    from cloud.app.legal import require_terms_acceptance

    require_terms_acceptance(accept_terms, confirm_age)
    invite = validate_invite_code(client, invite_code)

    email = email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(400, "Invalid email.")
    if len(password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters.")

    if device_id:
        enforce_not_banned(client, user_id="", device_id=device_id, ip=remote_ip)

    try:
        result = client.auth.admin.create_user(
            {
                "email": email,
                "password": password,
                "email_confirm": True,
            }
        )
    except Exception as exc:
        msg = str(exc)
        if "already" in msg.lower():
            raise HTTPException(409, "Email already registered.") from exc
        logger.exception("signup failed email=%s", email)
        raise HTTPException(500, "Signup failed.") from exc

    user = result.user
    if not user or not user.id:
        raise HTTPException(500, "Signup failed — no user returned.")

    user_id = str(user.id)
    if invite.get("code"):
        consume_invite_code(client, str(invite["code"]), user_id)
    block_trial_farming(client, user_id, device_id)

    from cloud.app.legal import record_acceptance
    from cloud.app.config import LEGAL_PRIVACY_VERSION, LEGAL_TERMS_VERSION

    record_acceptance(
        client,
        user_id,
        terms_version=LEGAL_TERMS_VERSION,
        privacy_version=LEGAL_PRIVACY_VERSION,
        ip=remote_ip,
    )

    from cloud.app.analytics_ops import save_attribution, track_event

    save_attribution(
        client,
        user_id,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        utm_content=utm_content,
        referrer=referrer,
    )
    track_event(
        client,
        "signup",
        user_id=user_id,
        properties={
            "utm_source": utm_source,
            "utm_campaign": utm_campaign,
        },
    )

    session_data: dict[str, Any] = {"user_id": user_id, "email": email}
    try:
        sign_in = client.auth.sign_in_with_password({"email": email, "password": password})
        if sign_in.session:
            session_data = {
                "access_token": sign_in.session.access_token,
                "refresh_token": sign_in.session.refresh_token,
                "expires_in": sign_in.session.expires_in,
                "user": {"id": user_id, "email": email},
            }
    except Exception:  # noqa: BLE001
        logger.warning("auto sign-in after signup failed for %s", email)

    return {"ok": True, "message": "Account created.", "session": session_data}
