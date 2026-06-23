"""Cloud API configuration."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

APP_VERSION = os.getenv("PLG_APP_VERSION", "1.0.0")
MIN_CLIENT_VERSION = os.getenv("PLG_MIN_CLIENT_VERSION", "1.0.0")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

MAX_PROMPT_CHARS = int(os.getenv("PLG_MAX_PROMPT_CHARS", "4000"))
MAX_DEVICES = int(os.getenv("PLG_MAX_DEVICES", "3"))
BEAT_LIMIT = int(os.getenv("PLG_BEAT_LIMIT", "30"))
PERIOD_DAYS = int(os.getenv("PLG_BEAT_PERIOD_DAYS", "30"))
DAILY_BEAT_LIMIT = int(os.getenv("PLG_DAILY_BEAT_LIMIT", "3"))

# Rough cost estimate per generation for kill-switch (USD)
EST_COST_BASE = float(os.getenv("PLG_EST_COST_BASE_USD", "0.03"))
EST_COST_PREMIUM = float(os.getenv("PLG_EST_COST_PREMIUM_USD", "0.10"))

DEV_BYPASS_AUTH = os.getenv("PLG_CLOUD_DEV_BYPASS", "").lower() in ("1", "true", "yes")
DEV_USER_ID = os.getenv("PLG_CLOUD_DEV_USER_ID", "00000000-0000-0000-0000-000000000001")

# Billing (Phase 2)
GRACE_DAYS = int(os.getenv("PLG_GRACE_DAYS", "3"))
TRIAL_BEATS = int(os.getenv("PLG_TRIAL_BEATS", "3"))
PRICE_CIS_RUB = int(os.getenv("PLG_PRICE_CIS_RUB", "899"))
PRICE_INTL_USD_CENTS = int(os.getenv("PLG_PRICE_INTL_USD_CENTS", "1499"))
BILLING_RETURN_URL = os.getenv("PLG_BILLING_RETURN_URL", "https://pluginflp.app/billing/return")

YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID_INTL = os.getenv("STRIPE_PRICE_ID_INTL", "")

PADDLE_WEBHOOK_SECRET = os.getenv("PADDLE_WEBHOOK_SECRET", "")
PADDLE_API_KEY = os.getenv("PADDLE_API_KEY", "")

# Security (Phase 3)
GEN_COOLDOWN_SEC = int(os.getenv("PLG_GEN_COOLDOWN_SEC", "15"))
GEN_HOURLY_LIMIT = int(os.getenv("PLG_GEN_HOURLY_LIMIT", "20"))
IP_HOURLY_LIMIT = int(os.getenv("PLG_IP_HOURLY_LIMIT", "100"))
IP_DAILY_GEN_ALERT = int(os.getenv("PLG_IP_DAILY_GEN_ALERT", "50"))
LLM_QUEUE_SLOTS = int(os.getenv("PLG_LLM_QUEUE_SLOTS", "8"))
LLM_QUEUE_TIMEOUT_SEC = int(os.getenv("PLG_LLM_QUEUE_TIMEOUT_SEC", "120"))
REQUIRE_DEVICE_BINDING = os.getenv("PLG_REQUIRE_DEVICE_BINDING", "true").lower() in (
    "1",
    "true",
    "yes",
)

CAPTCHA_PROVIDER = os.getenv("PLG_CAPTCHA_PROVIDER", "turnstile").lower()
TURNSTILE_SITE_KEY = os.getenv("TURNSTILE_SITE_KEY", "")
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "")
HCAPTCHA_SITE_KEY = os.getenv("HCAPTCHA_SITE_KEY", "")
HCAPTCHA_SECRET_KEY = os.getenv("HCAPTCHA_SECRET_KEY", "")

ADMIN_SECRET = os.getenv("PLG_ADMIN_SECRET", "")
TRUSTED_PROXY = os.getenv("PLG_TRUSTED_PROXY", "cloudflare").lower()

# Infra (Phase 4)
PLG_ENV = os.getenv("PLG_ENV", os.getenv("ENVIRONMENT", "development"))
REDIS_URL = os.getenv("REDIS_URL", "") or os.getenv("UPSTASH_REDIS_URL", "")

SENTRY_DSN = os.getenv("SENTRY_DSN", "")
SENTRY_TRACES_SAMPLE_RATE = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))

WAITLIST_MODE = os.getenv("PLG_WAITLIST_MODE", "").lower() in ("1", "true", "yes")
INVITE_ONLY = os.getenv("PLG_INVITE_ONLY", "").lower() in ("1", "true", "yes")

LLM_REDIS_SLOT_KEY = os.getenv("PLG_LLM_REDIS_SLOT_KEY", "plg:llm:active")

# Legal (Phase 5)
LEGAL_TERMS_VERSION = os.getenv("PLG_LEGAL_TERMS_VERSION", "1.0")
LEGAL_PRIVACY_VERSION = os.getenv("PLG_LEGAL_PRIVACY_VERSION", "1.0")
LEGAL_AGE_MIN = int(os.getenv("PLG_LEGAL_MIN_AGE", "16"))
PROMPT_LOG_RETENTION_DAYS = int(os.getenv("PLG_PROMPT_LOG_RETENTION_DAYS", "90"))
PAYMENT_LOG_RETENTION_DAYS = int(os.getenv("PLG_PAYMENT_LOG_RETENTION_DAYS", "730"))
DATA_REGION = os.getenv("PLG_DATA_REGION", "eu")
SUPPORT_EMAIL = os.getenv("PLG_SUPPORT_EMAIL", "support@pluginflp.app")

# Ops (Phase 6)
SUPPORT_TELEGRAM = os.getenv("PLG_SUPPORT_TELEGRAM", "https://t.me/pluginflp_support")
SUPPORT_SLA_HOURS = os.getenv("PLG_SUPPORT_SLA_HOURS", "24-48")
SUPPORT_UPDATES_URL = os.getenv("PLG_SUPPORT_UPDATES_URL", "https://t.me/pluginflp_updates")
STATUS_PAGE_URL = os.getenv("PLG_STATUS_PAGE_URL", "https://status.pluginflp.app")

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM = os.getenv("PLG_EMAIL_FROM", "PLUGIN.FLP <noreply@pluginflp.app>")

POSTHOG_API_KEY = os.getenv("POSTHOG_API_KEY", "")
POSTHOG_HOST = os.getenv("POSTHOG_HOST", "https://eu.i.posthog.com").rstrip("/")
