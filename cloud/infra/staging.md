# Staging environment

**Rule:** staging never touches production keys, payments, or user data.

## Stack

| Component | Staging | Production |
|-----------|---------|------------|
| Supabase | `plg-staging` project | `plg-prod` project |
| API | `plg-api-staging.fly.dev` | `api.pluginflp.app` |
| Redis | separate Upstash DB | prod Upstash |
| Sentry | `environment=staging` | `environment=production` |
| ЮKassa / Stripe | **test mode** keys | live keys |

## Setup

1. Copy `cloud/.env.staging.example` → `cloud/.env.staging`
2. Run migrations on **staging** Supabase only
3. Deploy: `fly deploy --config cloud/fly.toml --app plg-api-staging`
4. Desktop `.env`:

```env
PLG_CLOUD_URL=https://plg-api-staging.fly.dev
PLG_ENV=staging
```

## Smoke test before prod promote

```bash
curl https://plg-api-staging.fly.dev/health
k6 run cloud/loadtest/k6-smoke.js -e BASE_URL=https://plg-api-staging.fly.dev
```

## Data

- Use fake emails (`+staging@`)
- `PLG_WAITLIST_MODE=false` in staging unless testing waitlist
- `PLG_CAPTCHA_PROVIDER=none` OK for internal QA
