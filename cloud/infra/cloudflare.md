# Cloudflare — Phase 3 DDoS / WAF (put in front of Railway/Fly API)

## DNS

1. Add domain `api.pluginflp.app` → CNAME to your host (Railway/Fly).
2. **Proxy enabled** (orange cloud) — never expose origin IP.

## SSL/TLS

- Mode: **Full (strict)**
- Minimum TLS: 1.2

## WAF (free tier basics)

Security → WAF → Custom rules:

| Rule | Expression | Action |
|------|------------|--------|
| Block bad bots | `(cf.client.bot) and not (cf.verified_bot_category in {"Search Engine Crawler"})` | Block |
| Rate limit API | `(http.request.uri.path contains "/v1/generate")` | Rate limit 30/min per IP |
| Geo block (emergency) | `(ip.geoip.country in {"XX"})` | Block — fill during attack |

## DDoS

- **Under Attack Mode** — enable manually during spike (Caching → Configuration).
- Origin: only accept traffic from [Cloudflare IP ranges](https://www.cloudflare.com/ips/) if your host supports it.

## Headers (API reads these)

Cloudflare sends `CF-Connecting-IP` — used by `cloud/app/security.py` for rate limits and abuse alerts.

Set transform rule to pass through:

- `CF-Connecting-IP`
- `X-PLG-Version`
- `Authorization`

## Bot Fight Mode

Security → Bots → **Bot Fight Mode: On** for `/v1/auth/signup` path via WAF rule.

## Turnstile (CAPTCHA)

1. Dashboard → Turnstile → create widget for `pluginflp.app`.
2. Set `TURNSTILE_SITE_KEY` + `TURNSTILE_SECRET_KEY` in API `.env`.
3. Desktop signup uses server-side verify (`/v1/auth/signup`).

## Queue at peak

API-side `PLG_LLM_QUEUE_SLOTS=8` caps concurrent LLM calls. Cloudflare rate limit is the first line; queue prevents OOM on origin.

## JWT TTL (Supabase)

Dashboard → Auth → Settings:

- **JWT expiry: 3600** (1 hour) — short TTL, refresh token on desktop
- Rotate `JWT Secret` quarterly; update `SUPABASE_JWT_SECRET` on API server same day

## Checklist

- [ ] Orange cloud on API subdomain
- [ ] Turnstile on signup
- [ ] WAF bot block rule
- [ ] Rate limit on `/v1/generate`
- [ ] Under Attack Mode playbook documented for team
- [ ] Origin firewall: Cloudflare IPs only
