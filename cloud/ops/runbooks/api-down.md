# Runbook: Cloud API down

## Symptoms
- Desktop: "Generation failed" / network errors
- `GET /health` not 200
- Fly/Render alerts, Sentry spike

## Triage (5 min)
1. `curl https://api.pluginflp.app/health`
2. Check [status page](https://status.pluginflp.app) — post incident if not already
3. Fly: `fly status` / Render dashboard — last deploy?
4. Supabase status page — DB/auth outage?

## Fix paths
| Cause | Action |
|-------|--------|
| Bad deploy | `fly releases` → rollback previous image |
| OOM / crash loop | Scale memory, check Sentry stack traces |
| Supabase down | Enable maintenance message; wait for provider |
| Kill switch off | `UPDATE kill_switch SET enabled=true WHERE id=1` |
| Redis down | Rate limits fall back to in-memory; restore `REDIS_URL` |

## Comms
- Update `status_incidents` table + Telegram updates channel
- Template: "Investigating API errors — generation may fail. ETA updating."

## Post-incident
- Root cause in Notion/incident doc
- Add k6 smoke to CI if regression
