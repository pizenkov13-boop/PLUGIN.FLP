"""PLG Cloud API — auth proxy, quota, billing, beat generation, security."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from supabase import Client

from cloud.app.abuse import record_generation_ip, list_alerts
from cloud.app.admin import ack_alert, admin_dashboard, ban_entity, require_admin, unban_entity
from cloud.app.auth import current_user, profile_row, service_client
from cloud.app.billing import billing_snapshot, pick_checkout_provider, resolve_price_tier
from cloud.app.config import (
    APP_VERSION,
    CAPTCHA_PROVIDER,
    HCAPTCHA_SITE_KEY,
    MIN_CLIENT_VERSION,
    TURNSTILE_SITE_KEY,
)
from cloud.app.captcha import captcha_required
from cloud.app.devices import register_device, touch_device
from cloud.app.kill_switch import check_kill_switch, record_spend
from cloud.app.llm_proxy import generate_beat_pattern
from cloud.app.prompt_guard import sanitize_prompt
from cloud.app.providers import paddle_provider, stripe_provider, yookassa_provider
from cloud.app.queue import llm_slot
from cloud.app.quota import consume_beat, ensure_can_generate, quota_snapshot, roll_profile, save_profile
from cloud.app.rate_limit import check_generate_limits, check_ip_limit, record_ip_hit
from cloud.app.security import (
    client_ip,
    enforce_not_banned,
    require_registered_device,
)
from cloud.app.signup import signup_user
from cloud.app.sentry_init import init_sentry
from cloud.app.observability import health_payload
from cloud.app.feature_flags import flags_snapshot, flag_enabled, invalidate_cache
from cloud.app.waitlist import join_waitlist, generate_invite_codes, invite_required
from cloud.app.legal import delete_user_account, legal_snapshot, purge_generation_logs
from cloud.app.status_page import status_payload
from cloud.app.feedback import submit_feedback
from cloud.app.admin_ops import list_users, get_user_detail, patch_user_quota, ops_dashboard
from cloud.app.analytics_ops import admin_metrics, mark_first_beat, track_event

init_sentry()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("plg.cloud")

app = FastAPI(title="PLG Cloud API", version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_PUBLIC_PREFIXES = (
    "/health",
    "/v1/health",
    "/v1/billing/webhooks/",
    "/v1/auth/signup",
    "/v1/auth/config",
    "/v1/flags",
    "/v1/waitlist/",
    "/v1/legal",
    "/v1/status",
    "/v1/release/",
)


@app.middleware("http")
async def ip_rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if path.startswith("/v1/") and not any(path.startswith(p) for p in _PUBLIC_PREFIXES):
        ip = client_ip(request)
        try:
            check_ip_limit(ip)
            record_ip_hit(ip)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return await call_next(request)


class DeviceBody(BaseModel):
    device_id: str
    device_name: str | None = None


class GenerateBody(BaseModel):
    prompt: str
    catalog: dict[str, Any] | None = None
    user_profile: dict[str, Any] | None = None
    device_id: str | None = None
    locale: str | None = None


class CheckoutBody(BaseModel):
    price_tier: str | None = None


class SignupBody(BaseModel):
    email: str
    password: str
    device_id: str | None = None
    captcha_token: str | None = None
    invite_code: str | None = None
    website: str | None = None  # honeypot — must stay empty
    accept_terms: bool = False
    confirm_age: bool = False
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_content: str | None = None
    referrer: str | None = None


class FeedbackBody(BaseModel):
    category: str = "general"
    message: str
    email: str | None = None
    attach_log: bool = False
    log_excerpt: str | None = None
    platform: str | None = None


class QuotaPatchBody(BaseModel):
    beats_used: int | None = None
    status: str | None = None


class WaitlistBody(BaseModel):
    email: str
    ramp_tier: str | None = "wave_200"


class InviteGenBody(BaseModel):
    count: int = 10
    ramp_tier: str = "wave_200"
    max_uses: int | None = 1


class FlagPatchBody(BaseModel):
    key: str
    enabled: bool
    rollout_pct: int | None = None


class BanBody(BaseModel):
    ban_type: str
    ban_value: str
    reason: str | None = None
    expires_at: str | None = None


@app.get("/health")
def health() -> dict[str, Any]:
    return health_payload()


@app.get("/v1/health")
def health_v1() -> dict[str, Any]:
    return health_payload()


@app.get("/v1/auth/config")
def auth_config() -> dict[str, Any]:
    site_key = ""
    if CAPTCHA_PROVIDER == "turnstile":
        site_key = TURNSTILE_SITE_KEY
    elif CAPTCHA_PROVIDER == "hcaptcha":
        site_key = HCAPTCHA_SITE_KEY
    client = service_client()
    need_invite = invite_required(client)
    return {
        "ok": True,
        "captcha_provider": CAPTCHA_PROVIDER,
        "captcha_site_key": site_key,
        "captcha_required": captcha_required(),
        "invite_required": need_invite,
        "waitlist_mode": need_invite,
    }


@app.get("/v1/flags")
def get_flags() -> dict[str, Any]:
    return {"ok": True, "flags": flags_snapshot(service_client(), user_id=None)}


@app.get("/v1/flags/me")
def get_flags_me(user_id: str = Depends(current_user)) -> dict[str, Any]:
    client = service_client()
    return {"ok": True, "flags": flags_snapshot(client, user_id=user_id)}


@app.post("/v1/waitlist/join")
def waitlist_join(body: WaitlistBody) -> dict[str, Any]:
    return join_waitlist(service_client(), body.email, body.ramp_tier or "wave_200")


@app.post("/v1/auth/signup")
async def auth_signup(body: SignupBody, request: Request) -> dict[str, Any]:
    client = service_client()
    ip = client_ip(request)
    return await signup_user(
        client,
        email=body.email,
        password=body.password,
        device_id=body.device_id,
        captcha_token=body.captcha_token,
        honeypot=body.website,
        remote_ip=ip,
        invite_code=body.invite_code,
        accept_terms=body.accept_terms,
        confirm_age=body.confirm_age,
        utm_source=body.utm_source,
        utm_medium=body.utm_medium,
        utm_campaign=body.utm_campaign,
        utm_content=body.utm_content,
        referrer=body.referrer,
    )


@app.get("/v1/status")
def public_status() -> dict[str, Any]:
    return status_payload(service_client())


@app.get("/v1/release/manifest")
def release_manifest() -> dict[str, Any]:
    import os

    return {
        "ok": True,
        "version": APP_VERSION,
        "url": os.getenv("PLG_RELEASE_DOWNLOAD_URL", ""),
        "notes": os.getenv("PLG_RELEASE_NOTES", "Bug fixes and improvements."),
        "sha256": os.getenv("PLG_RELEASE_SHA256", ""),
        "mandatory": os.getenv("PLG_RELEASE_MANDATORY", "").lower() in ("1", "true", "yes"),
    }


@app.get("/v1/legal")
def legal_info() -> dict[str, Any]:
    return legal_snapshot()


@app.delete("/v1/account")
def account_delete(user_id: str = Depends(current_user)) -> dict[str, Any]:
    return delete_user_account(service_client(), user_id)


@app.get("/v1/me")
def me(
    request: Request,
    user_id: str = Depends(current_user),
    x_plg_device: str | None = Header(default=None, alias="X-PLG-Device"),
) -> dict[str, Any]:
    client = service_client()
    ip = client_ip(request)
    enforce_not_banned(client, user_id=user_id, device_id=x_plg_device, ip=ip)
    row = roll_profile(profile_row(client, user_id))
    save_profile(client, user_id, row)
    if x_plg_device:
        touch_device(client, user_id, x_plg_device)
    return {
        "ok": True,
        "user_id": user_id,
        "quota": quota_snapshot(row),
        "billing": billing_snapshot(row),
    }


@app.post("/v1/devices/register")
def devices_register(
    body: DeviceBody,
    request: Request,
    user_id: str = Depends(current_user),
) -> dict[str, Any]:
    client = service_client()
    ip = client_ip(request)
    enforce_not_banned(client, user_id=user_id, device_id=body.device_id, ip=ip)
    return register_device(client, user_id, body.device_id, body.device_name)


@app.post("/v1/generate")
def generate(
    body: GenerateBody,
    request: Request,
    user_id: str = Depends(current_user),
    x_plg_device: str | None = Header(default=None, alias="X-PLG-Device"),
) -> dict[str, Any]:
    client = service_client()
    ip = client_ip(request)
    device_id = body.device_id or x_plg_device

    if flag_enabled(client, "maintenance_mode", user_id=user_id):
        raise HTTPException(503, "Maintenance in progress. Try again shortly.")

    enforce_not_banned(client, user_id=user_id, device_id=device_id, ip=ip)
    check_generate_limits(user_id)
    device_id = require_registered_device(client, user_id, device_id)

    row = roll_profile(profile_row(client, user_id))
    row = ensure_can_generate(row)

    plan = str(row.get("plan") or "base")
    check_kill_switch(client, plan)

    prompt = sanitize_prompt(body.prompt)

    with llm_slot():
        pattern, meta = generate_beat_pattern(
            prompt,
            plan=plan,
            catalog=body.catalog,
            user_profile=body.user_profile,
            locale=body.locale,
        )

    quota = consume_beat(client, user_id, row)
    record_spend(client, plan, meta.get("cost_usd"))

    client.table("generation_logs").insert(
        {
            "user_id": user_id,
            "model": meta.get("model", "unknown"),
            "prompt_chars": meta.get("prompt_chars", len(prompt)),
            "cost_usd": meta.get("cost_usd"),
            "ip_address": ip,
            "device_id": device_id,
        }
    ).execute()

    record_generation_ip(client, ip, user_id, device_id)
    mark_first_beat(client, user_id)
    track_event(client, "beat_generated", user_id=user_id, properties={"model": meta.get("model")})

    if device_id:
        touch_device(client, user_id, device_id)

    return {
        "ok": True,
        "pattern": pattern,
        "quota": quota,
        "model": meta.get("model"),
    }


@app.post("/v1/feedback")
def feedback_submit(
    body: FeedbackBody,
    request: Request,
    user_id: str = Depends(current_user),
) -> dict[str, Any]:
    client = service_client()
    email = body.email
    if not email:
        try:
            from cloud.app.legal import _user_email
            email = _user_email(client, user_id)
        except Exception:  # noqa: BLE001
            email = None
    log_excerpt = body.log_excerpt if body.attach_log else None
    return submit_feedback(
        client,
        user_id=user_id,
        email=email,
        category=body.category,
        message=body.message,
        platform=body.platform or request.headers.get("User-Agent"),
        log_excerpt=log_excerpt,
    )


@app.post("/v1/auth/logout")
def logout(user_id: str = Depends(current_user)) -> dict[str, bool]:
    logger.info("logout user=%s", user_id)
    return {"ok": True}


@app.get("/v1/billing/status")
def billing_status(
    request: Request,
    user_id: str = Depends(current_user),
) -> dict[str, Any]:
    client = service_client()
    enforce_not_banned(client, user_id=user_id, ip=client_ip(request))
    row = roll_profile(profile_row(client, user_id))
    save_profile(client, user_id, row)
    return {"ok": True, "billing": billing_snapshot(row)}


@app.post("/v1/billing/checkout")
def billing_checkout(
    body: CheckoutBody,
    request: Request,
    user_id: str = Depends(current_user),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> dict[str, Any]:
    client = service_client()
    enforce_not_banned(client, user_id=user_id, ip=client_ip(request))
    tier = resolve_price_tier(body.price_tier, accept_language)
    provider = pick_checkout_provider(tier, client=client)
    if provider == "yookassa":
        out = yookassa_provider.create_checkout(user_id, tier)
    elif provider == "stripe":
        out = stripe_provider.create_checkout(user_id, tier)
    else:
        raise HTTPException(503, f"Checkout provider {provider} not implemented.")
    return {"ok": True, **out}


@app.post("/v1/billing/webhooks/yookassa")
async def webhook_yookassa(request: Request) -> dict[str, str]:
    client = service_client()
    body = await request.json()
    return yookassa_provider.handle_webhook(client, body)


@app.post("/v1/billing/webhooks/stripe")
async def webhook_stripe(request: Request) -> dict[str, str]:
    client = service_client()
    return await stripe_provider.handle_webhook(client, request)


@app.post("/v1/billing/webhooks/paddle")
async def webhook_paddle(request: Request) -> dict[str, str]:
    client = service_client()
    return await paddle_provider.handle_webhook(client, request)


# --- Admin (manual ban / alerts) -------------------------------------------

@app.get("/v1/admin/dashboard", dependencies=[Depends(require_admin)])
def admin_dash() -> dict[str, Any]:
    client = service_client()
    base = admin_dashboard(client)
    ops = ops_dashboard(client)
    return {**base, **ops}


@app.get("/v1/admin/users", dependencies=[Depends(require_admin)])
def admin_users(limit: int = 50, offset: int = 0) -> dict[str, Any]:
    return list_users(service_client(), limit=limit, offset=offset)


@app.get("/v1/admin/users/{user_id}", dependencies=[Depends(require_admin)])
def admin_user_detail(user_id: str) -> dict[str, Any]:
    return get_user_detail(service_client(), user_id)


@app.patch("/v1/admin/users/{user_id}/quota", dependencies=[Depends(require_admin)])
def admin_user_quota(user_id: str, body: QuotaPatchBody) -> dict[str, Any]:
    return patch_user_quota(
        service_client(),
        user_id,
        beats_used=body.beats_used,
        status=body.status,
    )


@app.get("/v1/admin/metrics", dependencies=[Depends(require_admin)])
def admin_metrics_route(days: int = 30) -> dict[str, Any]:
    return admin_metrics(service_client(), days=days)


@app.get("/v1/admin/alerts", dependencies=[Depends(require_admin)])
def admin_alerts(limit: int = 50) -> dict[str, Any]:
    return {"ok": True, "alerts": list_alerts(service_client(), limit=limit)}


@app.post("/v1/admin/ban", dependencies=[Depends(require_admin)])
def admin_ban(body: BanBody) -> dict[str, Any]:
    return ban_entity(
        service_client(),
        ban_type=body.ban_type,
        ban_value=body.ban_value,
        reason=body.reason,
        expires_at=body.expires_at,
    )


@app.post("/v1/admin/unban", dependencies=[Depends(require_admin)])
def admin_unban(body: BanBody) -> dict[str, Any]:
    return unban_entity(service_client(), ban_type=body.ban_type, ban_value=body.ban_value)


@app.post("/v1/admin/alerts/{alert_id}/ack", dependencies=[Depends(require_admin)])
def admin_ack_alert(alert_id: str) -> dict[str, Any]:
    return ack_alert(service_client(), alert_id)


@app.post("/v1/admin/invite-codes", dependencies=[Depends(require_admin)])
def admin_generate_invites(body: InviteGenBody) -> dict[str, Any]:
    codes = generate_invite_codes(
        service_client(),
        count=body.count,
        ramp_tier=body.ramp_tier,
        max_uses=body.max_uses,
    )
    return {"ok": True, "codes": codes, "count": len(codes)}


@app.patch("/v1/admin/flags", dependencies=[Depends(require_admin)])
def admin_patch_flag(body: FlagPatchBody) -> dict[str, Any]:
    from datetime import datetime, timezone

    patch: dict[str, Any] = {
        "enabled": body.enabled,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if body.rollout_pct is not None:
        patch["rollout_pct"] = body.rollout_pct
    service_client().table("feature_flags").update(patch).eq("key", body.key).execute()
    invalidate_cache()
    return {"ok": True, "key": body.key}


@app.post("/v1/admin/retention/purge", dependencies=[Depends(require_admin)])
def admin_purge_logs() -> dict[str, Any]:
    return purge_generation_logs(service_client())
