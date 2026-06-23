# PLG Cloud — Fly.io deploy

## Prerequisites

- [Fly CLI](https://fly.io/docs/hands-on/install-flyctl/)
- Supabase project (prod)
- Upstash Redis (optional, recommended at 2k+ users)
- Cloudflare DNS → orange cloud → Fly app

## First deploy

```bash
cd C:\PLUG.FLP
fly auth login
fly launch --config cloud/fly.toml --no-deploy
fly secrets set \
  SUPABASE_URL=... \
  SUPABASE_SERVICE_KEY=... \
  SUPABASE_JWT_SECRET=... \
  GEMINI_API_KEY=... \
  REDIS_URL=... \
  SENTRY_DSN=... \
  PLG_ADMIN_SECRET=...
fly deploy --config cloud/fly.toml
```

## Scale (ramp)

| Wave | Users | Fly machines | Redis |
|------|-------|--------------|-------|
| Beta | 200 | 1 × 1GB | optional |
| Growth | 2k | 2 × 1GB | Upstash |
| Scale | 20k | 4 × 2GB | Upstash Pro |
| Target | 100k | 8+ + queue | required |

```bash
fly scale count 2
fly scale vm shared-cpu-2x --memory 2048
```

## Cloudflare

Point `api.pluginflp.app` CNAME → `<app>.fly.dev`. See `cloudflare.md`.

## Staging

Separate Fly app `plg-api-staging` + Supabase staging project. Never reuse prod keys.
