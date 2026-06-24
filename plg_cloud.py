"""Desktop client for PLG Cloud API + Supabase Auth."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx

from app_config import app_version
from plg_device import get_device_id, get_device_name
from plg_session_store import clear_session, load_session, save_session

logger = logging.getLogger("plg.cloud")

_SESSION_SKEW_S = 90
_device_registered = False


def is_cloud_mode() -> bool:
    raw = os.getenv("PLG_CLOUD_MODE", "").strip().lower()
    return raw in ("1", "true", "yes")


def cloud_api_url() -> str:
    return (os.getenv("PLG_CLOUD_URL") or "http://127.0.0.1:8787").rstrip("/")


def _format_cloud_http_error(exc: Exception, *, path: str = "") -> dict[str, Any]:
    """Turn httpx/network failures into actionable UI messages."""
    url = cloud_api_url()
    target = f"{url}{path}" if path else url
    text = str(exc).strip() or exc.__class__.__name__
    lower = text.lower()

    if "getaddrinfo failed" in lower or "name or service not known" in lower:
        hint = (
            f"Cannot reach PLG Cloud at {url} (DNS lookup failed).\n\n"
            "For local dev:\n"
            "1. Terminal: python cloud\\run.py\n"
            "2. In .env set PLG_CLOUD_URL=http://127.0.0.1:8787\n"
            "3. Restart PLG\n\n"
            "For release: deploy the cloud API first, then point PLG_CLOUD_URL "
            "to your live host (e.g. https://api.plugflp.tech)."
        )
        return {"ok": False, "error": hint, "error_type": "cloud"}

    if "connection refused" in lower or "actively refused" in lower:
        return {
            "ok": False,
            "error": (
                f"PLG Cloud is not running at {url}.\n\n"
                "Start it: python cloud\\run.py\n"
                "Then click Create beat again."
            ),
            "error_type": "cloud",
        }

    if "timed out" in lower or "timeout" in lower:
        return {
            "ok": False,
            "error": (
                "PLG Cloud did not respond in time.\n\n"
                f"Server: {target}\n\n"
                "Gemini can take 1–3 minutes when busy. Keep cloud\\run.py open "
                "and try again."
            ),
            "error_type": "cloud",
        }

    return {"ok": False, "error": f"Cloud request failed ({target}): {text}", "error_type": "cloud"}


def supabase_url() -> str:
    return (os.getenv("SUPABASE_URL") or "").rstrip("/")


def supabase_anon_key() -> str:
    return (
        os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_PUBLISHABLE_KEY") or ""
    ).strip()


def _auth_headers() -> dict[str, str]:
    session = load_session()
    token = str(session.get("access_token") or "").strip()
    if not token:
        raise RuntimeError("Not signed in.")
    return {
        "Authorization": f"Bearer {token}",
        "X-PLG-Version": app_version(),
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
    expires_in = data.get("expires_in")
    expires_at: float | None = None
    if expires_in is not None:
        try:
            expires_at = time.time() + float(expires_in)
        except (TypeError, ValueError):
            expires_at = None
    session = {
        "access_token": data.get("access_token"),
        "refresh_token": data.get("refresh_token"),
        "expires_in": data.get("expires_in"),
        "expires_at": expires_at,
        "user": data.get("user"),
        "email": (data.get("user") or {}).get("email"),
    }
    save_session(session)
    return session


def _needs_refresh(session: dict[str, Any]) -> bool:
    token = str(session.get("access_token") or "").strip()
    refresh = str(session.get("refresh_token") or "").strip()
    if not token:
        return bool(refresh)
    expires_at = session.get("expires_at")
    if expires_at is None:
        return False
    try:
        return time.time() >= float(expires_at) - _SESSION_SKEW_S
    except (TypeError, ValueError):
        return False


def ensure_session(*, validate: bool = False) -> dict[str, Any]:
    """Restore session from disk; refresh expired tokens; optionally validate with /v1/me."""
    global _device_registered

    session = load_session()
    if not session.get("access_token") and not session.get("refresh_token"):
        return {"ok": True, "signed_in": False}

    did_refresh = False
    if _needs_refresh(session):
        refreshed = refresh_session()
        did_refresh = bool(refreshed.get("ok"))
        if not did_refresh:
            return {"ok": True, "signed_in": False}
        session = load_session()

    token = str(session.get("access_token") or "").strip()
    if not token:
        return {"ok": True, "signed_in": False}

    if not validate:
        return {"ok": True, "signed_in": True}

    me = fetch_me()
    if me.get("ok"):
        if did_refresh or not _device_registered:
            reg = register_device()
            if reg.get("ok"):
                _device_registered = True
            else:
                logger.warning("device register on session restore: %s", reg.get("error"))
        return {"ok": True, "signed_in": True}

    if me.get("error_type") == "auth":
        clear_session()
        _device_registered = False
        return {"ok": True, "signed_in": False}

    return {"ok": True, "signed_in": True}


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
            headers={"X-PLG-Version": app_version(), "Content-Type": "application/json"},
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
        else:
            login_result = login(email, password)
            if not login_result.get("ok"):
                return {
                    "ok": True,
                    "message": data.get("message", "Account created."),
                    "session": session,
                    "needs_login": True,
                }
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
        global _device_registered
        _device_registered = False
        register_device()
        _device_registered = True
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
    global _device_registered
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
            _device_registered = False
            return {"ok": False, "error": "Session expired. Sign in again.", "error_type": "auth"}
        _store_auth_response(resp.json())
        return {"ok": True, "session": load_session()}


def logout() -> dict[str, Any]:
    global _device_registered
    try:
        with httpx.Client(timeout=15.0) as client:
            client.post(f"{cloud_api_url()}/v1/auth/logout", headers=_api_headers())
    except Exception:  # noqa: BLE001
        pass
    clear_session()
    _device_registered = False
    return {"ok": True}


def is_signed_in() -> bool:
    session = load_session()
    if not session.get("access_token"):
        return False
    if _needs_refresh(session):
        return bool(ensure_session().get("signed_in"))
    return True


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
        try:
            data = resp.json() if resp.content else {}
        except Exception:  # noqa: BLE001
            data = {}
        if resp.status_code >= 400:
            detail = data.get("detail") if isinstance(data.get("detail"), str) else resp.text
            return {"ok": False, "error": detail or f"HTTP {resp.status_code}", "error_type": "device"}
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

    try:
        with httpx.Client(timeout=180.0) as client:
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
    except httpx.HTTPError as exc:
        logger.exception("cloud_generate request failed")
        return _format_cloud_http_error(exc, path="/v1/generate")
    except OSError as exc:
        logger.exception("cloud_generate network failed")
        return _format_cloud_http_error(exc, path="/v1/generate")

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
    global _device_registered
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
    _device_registered = False
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
            resp = client.get(f"{base}/v1/status", headers={"X-PLG-Version": app_version()})
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
