# PLG Cloud API (Phase 1 + 2)



Server-side auth proxy, quota, billing, and beat generation. API keys never ship to clients.



## Setup



1. Create a [Supabase](https://supabase.com) project.

2. Run `cloud/supabase/schema.sql` in SQL Editor (new projects).

3. Existing projects: also run `cloud/supabase/migrations/002_payments.sql`.

4. Copy `cloud/.env.example` → `cloud/.env` (or root `.env`).

5. Fill in Supabase + LLM keys (see `.env.example`).

6. **Phase 2 billing (start):** register [ЮKassa](https://yookassa.ru), set `YOOKASSA_SHOP_ID` + `YOOKASSA_SECRET_KEY`.

7. Install deps:



```bat

pip install -r cloud/requirements.txt

pip install -r requirements.txt

```



8. Run API:



```bat

python cloud/run.py

```



Health: http://127.0.0.1:8787/health



## Desktop app (cloud mode)



In root `.env`:



```env

PLG_CLOUD_MODE=true

PLG_CLOUD_URL=http://127.0.0.1:8787

SUPABASE_URL=https://YOUR_PROJECT.supabase.co

SUPABASE_ANON_KEY=your-anon-key

```



Restart `run_plg.bat` — login screen appears; Settings → Subscribe opens ЮKassa checkout in browser.



## Endpoints



| Method | Path | Auth | Description |

|--------|------|------|-------------|

| GET | `/health` | — | Liveness |

| GET | `/v1/me` | JWT | Profile + quota + billing |

| GET | `/v1/billing/status` | JWT | Subscription snapshot |

| POST | `/v1/billing/checkout` | JWT | Create payment URL (ЮKassa CIS / Stripe intl) |

| POST | `/v1/billing/webhooks/yookassa` | — | ЮKassa notifications |

| POST | `/v1/billing/webhooks/stripe` | — | Stripe webhooks |

| POST | `/v1/billing/webhooks/paddle` | — | Paddle webhooks |

| POST | `/v1/devices/register` | JWT | Bind device (max 3) |

| POST | `/v1/generate` | JWT | Prompt → pattern JSON |

| POST | `/v1/auth/logout` | JWT | Ack logout |



Headers: `Authorization: Bearer <access_token>`, `X-PLG-Version: 1.0.0`, `X-PLG-Device: <uuid>`



## Pricing (geo)



| Region | Price | Provider (start → scale) |

|--------|-------|--------------------------|

| СНГ | **899 ₽/mo** | ЮKassa |

| EU / US | **$14.99/mo** | Stripe / Paddle (after ~200 users) |



`Accept-Language` or `price_tier` in checkout body selects tier.



## Quota & access



- **Trial:** 3 free beats (config: `PLG_TRIAL_BEATS`)

- **Paid:** 30 beats / 30 days + 3 / day

- **Grace:** 3 days after failed payment (`PLG_GRACE_DAYS`)

- Enforced on server only



## Billing checklist (Phase 2)



| Item | Status |

|------|--------|

| Webhook → activate subscription | ✅ |

| Idempotency (`payment_events`) | ✅ |

| Grace period | ✅ |

| Trial beats | ✅ |

| PCI (cards via provider only) | ✅ |

| ЮKassa CIS checkout | ✅ |

| Stripe / Paddle webhooks | ✅ stubs |

| Dunning (retry charges) | ⏳ provider-side / manual renew for MVP |

| Chargeback evidence | ✅ `generation_logs` + `payment_events` |

| Promo / referral | ⏳ after 200 users |

| Customer portal / cancel | ⏳ provider dashboard for now |

| VAT / receipts | ⏳ ЮKassa receipts + Paddle tax later |



## Webhook URLs (production)



Point provider dashboards to:



- `https://api.pluginflp.app/v1/billing/webhooks/yookassa`

- `https://api.pluginflp.app/v1/billing/webhooks/stripe`

- `https://api.pluginflp.app/v1/billing/webhooks/paddle`



ЮKassa: verify payments server-side via API (implemented). Never trust webhook body alone.



## Dev bypass



`PLG_CLOUD_DEV_BYPASS=true` on server skips JWT (local testing only).



## Deploy



Deploy `cloud/` to Railway, Fly.io, or Render. Put Cloudflare in front. Never expose `SUPABASE_SERVICE_KEY` or payment secrets to clients.

## Phase 3 — Security

Run `cloud/supabase/migrations/003_security.sql`.

| Feature | Implementation |
|---------|----------------|
| Rate limit gen | 1 / 15s + 20 / hour per user |
| Rate limit IP | 100 req / hour |
| CAPTCHA signup | Turnstile / hCaptcha via `POST /v1/auth/signup` |
| Honeypot | `website` field on signup form |
| Device binding | Required on `/v1/generate` |
| Trial anti-farming | `device_trial_claims` — 1 trial per device |
| Bans | `security_bans` + `profiles.banned` |
| Abuse alerts | >50 gen/day/IP → `abuse_alerts` |
| Admin API | `X-PLG-Admin-Key` → `/v1/admin/*` |
| LLM queue | `PLG_LLM_QUEUE_SLOTS` semaphore |
| Content mod | illegal/NSFW block in `moderation.py` |
| Cloudflare | See `cloud/infra/cloudflare.md` |

Public without JWT: `/health`, `/v1/auth/signup`, `/v1/auth/config`, payment webhooks only.

JWT TTL: set 1h in Supabase Auth settings; desktop uses refresh token.

## Phase 4 — Infra (100k/mo)

Run `cloud/supabase/migrations/004_infra.sql`.

| Component | Solution |
|-----------|----------|
| API deploy | `cloud/Dockerfile` + `cloud/fly.toml` (Fly primary) |
| Redis queue | Upstash `REDIS_URL` — rate limits + LLM slots |
| Sentry | `SENTRY_DSN` server, `PLG_SENTRY_DSN` desktop |
| Feature flags | `feature_flags` table + `GET /v1/flags` |
| Waitlist / ramp | `waitlist_entries` + invite codes |
| Staging | `cloud/.env.staging.example`, `infra/staging.md` |
| Backups | Supabase daily + `scripts/backup_supabase.*` |
| Load test | `k6 run cloud/loadtest/k6-smoke.js` |
| OWASP | `cloud/infra/owasp-checklist.md` |
| Ramp plan | `cloud/infra/ramp-100k.md` |

**Do not open 100k in one day** — waves: 200 → 2k → 20k → 100k.

## Phase 5 — Legal

Run `cloud/supabase/migrations/005_legal.sql`.

| Item | Implementation |
|------|----------------|
| Terms / Privacy / Refund | `legal/*.md` — open in Help & Settings |
| Beat ownership | Terms + API disclaimers |
| Sample license on user | Terms + UI disclaimer |
| Age 16+ | Signup checkboxes + `PLG_LEGAL_MIN_AGE` |
| GDPR delete | `DELETE /v1/account` + Settings button |
| Prompt retention | 90 days metadata purge (`purge_retention.py`) |
| Payment logs | 730+ days, anonymized on delete |
| ИП/ООО checklist | `legal/BUSINESS_RU.md` |

Fill `[НАИМЕНОВАНИЕ]`, `[ИНН]`, `[EMAIL]` in legal docs before launch.

## Phase 6 — Ops

Run `cloud/supabase/migrations/006_ops.sql`.

| Item | Implementation |
|------|----------------|
| Support SLA 24–48h | `PLG_SUPPORT_EMAIL`, Telegram, FAQ i18n (9 langs) |
| Status page | `GET /v1/status` → status.pluginflp.app JSON |
| Auto-email | Resend: payment, quota, welcome (`cloud/app/email.py`) |
| SPF/DKIM/DMARC | `cloud/ops/email-deliverability.md` |
| Admin users/metrics | `/v1/admin/users`, `/v1/admin/metrics` |
| Runbooks | `cloud/ops/runbooks/` |
| Support at 100k | `cloud/ops/support-scale.md` |
| Discord/TG mods | `cloud/ops/community-moderation.md` |
| In-app feedback | `POST /v1/feedback` + `plg_session.log` attach |
| Analytics | PostHog desktop + `analytics_events` + UTM on signup |

Public without JWT: add `/v1/status` to public prefixes.

Desktop: Settings → feedback; Help → FAQ + support links.

