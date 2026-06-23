"""Desktop client for PLG Cloud API + Supabase Auth."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from plg_device import get_device_id, get_device_name
from plg_session_store import clear_session, load_session, save_session

logger = logging.getLogger("plg.cloud")

APP_VERSION = os.getenv("PLG_APP_VERSION", "1.0.0")


def is_cloud_mode() -> bool:
    raw = os.getenv("PLG_CLOUD_MODE", "").strip().lower()
    return raw in ("1", "true", "yes")


def cloud_api_url() -> str:
    return (os.getenv("PLG_CLOUD_URL") or "http://127.0.0.1:8787").rstrip("/")


def supabase_url() -> str:
    return (os.getenv("SUPABASE_URL") or "").rstrip("/")


def supabase_anon_key() -> str:
    return (os.getenv("SUPABASE_ANON_KEY") or "").strip()


def _auth_headers() -> dict[str, str]:
    session = load_session()
    token = str(session.get("access_token") or "").strip()
    if not token:
        raise RuntimeError("Not signed in.")
    return {
        "Authorization": f"Bearer {token}",
        "X-PLG-Version": APP_VERSION,
        "X-PLG-Device": get_device_id(),
    }


def _api_headers() -> dict[str, str]:
    return {**_auth_headers(), "Content-Type": "application/json"}


def _supabase_headers() -> dict[str, str]:
    key = supabase_anon_key()
    if not key:
        raise RuntimeError("SUPABASE_ANON_KEY not configured.")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _store_auth_response(data: dict[str, Any]) -> dict[str, Any]:
    session = {
        "access_token": data.get("access_token"),
        "refresh_token": data.get("refresh_token"),
        "expires_in": data.get("expires_in"),
        "user": data.get("user"),
        "email": (data.get("user") or {}).get("email"),
    }
    save_session(session)
    return session


def signup(
    email: str,
    password: str,
    captcha_token: str | None = None,
    invite_code: str | None = None,
    accept_terms: bool = False,
    confirm_age: bool = False,
) -> dict[str, Any]:
    base = cloud_api_url()
    if not base:
        return {"ok": False, "error": "PLG_CLOUD_URL not configured.", "error_type": "config"}

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"{base}/v1/auth/signup",
            headers={"X-PLG-Version": APP_VERSION, "Content-Type": "application/json"},
            json={
                "email": email.strip(),
                "password": password,
                "device_id": get_device_id(),
                "captcha_token": captcha_token,
                "invite_code": invite_code,
                "website": "",
                "accept_terms": accept_terms,
                "confirm_age": confirm_age,
            },
        )
        data = resp.json()
        if resp.status_code >= 400:
            detail = data.get("detail") if isinstance(data.get("detail"), str) else resp.text
            return {"ok": False, "error": detail, "error_type": "auth"}

        session = data.get("session") or {}
        if session.get("access_token"):
            _store_auth_response(
                {
                    "access_token": session["access_token"],
                    "refresh_token": session.get("refresh_token"),
                    "expires_in": session.get("expires_in"),
                    "user": session.get("user"),
                }
            )
            register_device()
        return {"ok": True, "message": data.get("message", "Account created."), "session": load_session()}


def login(email: str, password: str) -> dict[str, Any]:
    base = supabase_url()
    if not base:
        return {"ok": False, "error": "SUPABASE_URL not configured.", "error_type": "config"}

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"{base}/auth/v1/token?grant_type=password",
            headers=_supabase_headers(),
            json={"email": email.strip(), "password": password},
        )
        if resp.status_code >= 400:
            return {"ok": False, "error": _parse_error(resp), "error_type": "auth"}
        _store_auth_response(resp.json())
        register_device()
        return {"ok": True, "session": load_session()}


def request_password_reset(email: str) -> dict[str, Any]:
    base = supabase_url()
    if not base:
        return {"ok": False, "error": "SUPABASE_URL not configured.", "error_type": "config"}

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"{base}/auth/v1/recover",
            headers=_supabase_headers(),
            json={"email": email.strip()},
        )
        if resp.status_code >= 400:
            return {"ok": False, "error": _parse_error(resp), "error_type": "auth"}
        return {"ok": True, "message": "Password reset email sent."}


def refresh_session() -> dict[str, Any]:
    session = load_session()
    refresh = str(session.get("refresh_token") or "").strip()
    base = supabase_url()
    if not refresh or not base:
        return {"ok": False, "error": "No refresh token.", "error_type": "auth"}

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"{base}/auth/v1/token?grant_type=refresh_token",
            headers=_supabase_headers(),
            json={"refresh_token": refresh},
        )
        if resp.status_code >= 400:
            clear_session()
            return {"ok": False, "error": "Session expired. Sign in again.", "error_type": "auth"}
        _store_auth_response(resp.json())
        return {"ok": True, "session": load_session()}


def logout() -> dict[str, Any]:
    try:
        with httpx.Client(timeout=15.0) as client:
            client.post(f"{cloud_api_url()}/v1/auth/logout", headers=_api_headers())
    except Exception:  # noqa: BLE001
        pass
    clear_session()
    return {"ok": True}


def is_signed_in() -> bool:
    return bool(load_session().get("access_token"))


def session_snapshot() -> dict[str, Any]:
    session = load_session()
    user = session.get("user") or {}
    email = session.get("email") or user.get("email")
    return {
        "signed_in": bool(session.get("access_token")),
        "email": email,
    }


def register_device() -> dict[str, Any]:
    with httpx.Client(timeout=20.0) as client:
        resp = client.post(
            f"{cloud_api_url()}/v1/devices/register",
            headers=_api_headers(),
            json={"device_id": get_device_id(), "device_name": get_device_name()},
        )
        if resp.status_code == 401:
            refreshed = refresh_session()
            if not refreshed.get("ok"):
                return refreshed
            resp = client.post(
                f"{cloud_api_url()}/v1/devices/register",
                headers=_api_headers(),
                json={"device_id": get_device_id(), "device_name": get_device_name()},
            )
        data = resp.json()
        if resp.status_code >= 400:
            return {"ok": False, "error": data.get("detail") or resp.text, "error_type": "device"}
        return {"ok": True, **data}


def fetch_me() -> dict[str, Any]:
    with httpx.Client(timeout=20.0) as client:
        resp = client.get(f"{cloud_api_url()}/v1/me", headers=_api_headers())
        if resp.status_code == 401:
            refreshed = refresh_session()
            if not refreshed.get("ok"):
                return refreshed
            resp = client.get(f"{cloud_api_url()}/v1/me", headers=_api_headers())
        data = resp.json()
        if resp.status_code >= 400:
            return {"ok": False, "error": data.get("detail") or resp.text, "error_type": "cloud"}
        return {"ok": True, **data}


def billing_status() -> dict[str, Any]:
    return _cloud_get("/v1/billing/status")


def billing_checkout(price_tier: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if price_tier:
        payload["price_tier"] = price_tier
    return _cloud_post("/v1/billing/checkout", payload)


def _cloud_get(path: str) -> dict[str, Any]:
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(f"{cloud_api_url()}{path}", headers=_api_headers())
        if resp.status_code == 401:
            refreshed = refresh_session()
            if not refreshed.get("ok"):
                return refreshed
            resp = client.get(f"{cloud_api_url()}{path}", headers=_api_headers())
        data = resp.json()
        if resp.status_code >= 400:
            detail = data.get("detail") if isinstance(data.get("detail"), str) else resp.text
            return {"ok": False, "error": detail, "error_type": "billing"}
        return {"ok": True, **data}


def _cloud_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(f"{cloud_api_url()}{path}", headers=_api_headers(), json=payload)
        if resp.status_code == 401:
            refreshed = refresh_session()
            if not refreshed.get("ok"):
                return refreshed
            resp = client.post(f"{cloud_api_url()}{path}", headers=_api_headers(), json=payload)
        data = resp.json()
        if resp.status_code >= 400:
            detail = data.get("detail") if isinstance(data.get("detail"), str) else resp.text
            return {"ok": False, "error": detail, "error_type": "billing"}
        return {"ok": True, **data}


def cloud_generate(
    prompt: str,
    *,
    catalog: dict[str, Any] | None = None,
    user_profile: dict[str, Any] | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "prompt": prompt,
        "device_id": get_device_id(),
    }
    if catalog is not None:
        payload["catalog"] = catalog
    if user_profile is not None:
        payload["user_profile"] = user_profile
    if locale:
        payload["locale"] = locale

    with httpx.Client(timeout=120.0) as client:
        resp = client.post(
            f"{cloud_api_url()}/v1/generate",
            headers=_api_headers(),
            json=payload,
        )
        if resp.status_code == 401:
            refreshed = refresh_session()
            if not refreshed.get("ok"):
                return refreshed
            resp = client.post(
                f"{cloud_api_url()}/v1/generate",
                headers=_api_headers(),
                json=payload,
            )
        data = resp.json()
        if resp.status_code >= 400:
            detail = data.get("detail") if isinstance(data.get("detail"), str) else data.get("detail")
            if isinstance(detail, list):
                detail = detail[0].get("msg") if detail else resp.text
            err_type = "quota" if resp.status_code == 429 else "cloud"
            if resp.status_code == 402:
                err_type = "subscription"
            return {"ok": False, "error": detail or resp.text, "error_type": err_type, "quota": data.get("quota")}
        return {"ok": True, **data}


def fetch_feature_flags() -> dict[str, Any]:
    try:
        with httpx.Client(timeout=15.0) as client:
            if is_signed_in():
                resp = client.get(f"{cloud_api_url()}/v1/flags/me", headers=_auth_headers())
            else:
                resp = client.get(f"{cloud_api_url()}/v1/flags")
            if resp.status_code >= 400:
                return {"ok": False}
            return {"ok": True, **resp.json()}
    except Exception as exc:  # noqa: BLE001
        logger.warning("flags fetch failed: %s", exc)
        return {"ok": False}


def fetch_auth_config() -> dict[str, Any]:
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{cloud_api_url()}/v1/auth/config")
            if resp.status_code >= 400:
                return {"ok": False}
            return {"ok": True, **resp.json()}
    except Exception as exc:  # noqa: BLE001
        logger.warning("auth config fetch failed: %s", exc)
        return {"ok": False}


def delete_account() -> dict[str, Any]:
    with httpx.Client(timeout=30.0) as client:
        resp = client.delete(f"{cloud_api_url()}/v1/account", headers=_api_headers())
        if resp.status_code == 401:
            refreshed = refresh_session()
            if not refreshed.get("ok"):
                return refreshed
            resp = client.delete(f"{cloud_api_url()}/v1/account", headers=_api_headers())
        data = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            detail = data.get("detail") if isinstance(data.get("detail"), str) else resp.text
            return {"ok": False, "error": detail, "error_type": "account"}
    clear_session()
    return {"ok": True, "message": data.get("message", "Account deleted.")}


def ping_cloud() -> dict[str, Any]:
    """Quick connectivity check for offline UI."""
    return fetch_status()


def fetch_status() -> dict[str, Any]:
    base = cloud_api_url()
    if not base:
        return {"ok": False, "error": "PLG_CLOUD_URL not configured.", "error_type": "config"}
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{base}/v1/status", headers={"X-PLG-Version": APP_VERSION})
            if resp.status_code >= 400:
                return {"ok": False, "error": resp.text, "error_type": "cloud"}
            return {"ok": True, **resp.json()}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "error_type": "network"}


def submit_feedback(
    *,
    category: str,
    message: str,
    attach_log: bool = False,
    log_excerpt: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "category": category,
        "message": message,
        "attach_log": attach_log,
    }
    if log_excerpt:
        payload["log_excerpt"] = log_excerpt
    return _cloud_post("/v1/feedback", payload)


def _parse_error(resp: httpx.Response) -> str:
    try:
        data = resp.json()
        return str(data.get("msg") or data.get("error_description") or data.get("message") or resp.text)
    except Exception:  # noqa: BLE001
        return resp.text or f"HTTP {resp.status_code}"
