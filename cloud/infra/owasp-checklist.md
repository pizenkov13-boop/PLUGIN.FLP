# OWASP-oriented checklist (PLG Cloud + Desktop)

Use before each major wave. Not a substitute for professional pen-test.

## A01 Broken Access Control

- [x] JWT required on all `/v1/*` except documented public routes
- [x] Service role key server-only
- [x] RLS on Supabase tables
- [x] Admin routes need `X-PLG-Admin-Key`
- [ ] Quarterly review of public route list

## A02 Cryptographic Failures

- [x] TLS everywhere (Cloudflare + Fly)
- [x] No card data stored (PCI via ЮKassa/Stripe)
- [x] Secrets in env / Fly secrets, not git
- [ ] JWT secret rotation schedule (Supabase dashboard)

## A03 Injection

- [x] Prompt sanitization + moderation
- [x] Pydantic validation on bodies
- [x] Parameterized Supabase client (no raw SQL from user input)

## A04 Insecure Design

- [x] Server-side quota + rate limits
- [x] Device binding + trial anti-farming
- [x] Kill switch for LLM spend
- [x] Waitlist / invite ramp

## A05 Security Misconfiguration

- [ ] `PLG_CLOUD_DEV_BYPASS` disabled in prod
- [ ] Staging uses separate keys (`staging.md`)
- [ ] CORS tightened to app origins before 20k wave
- [x] Default CAPTCHA on signup in prod

## A07 Identification and Authentication

- [x] Supabase Auth
- [x] Short JWT TTL (configure 1h in Supabase)
- [x] Refresh token on desktop
- [x] CAPTCHA on signup

## A09 Security Logging

- [x] Sentry server + desktop optional
- [x] `generation_logs`, `payment_events`, `abuse_alerts`
- [ ] Log retention policy (90 days)

## API-specific

- [x] Rate limit per user + IP
- [x] Webhook idempotency
- [x] Payment verify server-side (ЮKassa)

## Desktop (.exe)

- [x] API keys in local `.env` only (non-cloud mode)
- [ ] Code signing certificate before wide release
- [x] Sentry optional via `PLG_SENTRY_DSN`

## Pen-test

Before **wave_20k**: budget for light pen-test or use OWASP ZAP against staging API.
