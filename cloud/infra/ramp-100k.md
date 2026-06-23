# Ramp to 100k users/month

## Load math

- 100k users × ~12 beats/mo ≈ **1.2M generations/month**
- ≈ **40k generations/day** ≈ **~28/min** average (peaks 5–10× higher)
- Flash API cost ≈ **3–7% of revenue** at 899 ₽ with 30 beat cap — OK

## Do NOT open 100k in one day

Use controlled waves:

| Wave | Users | Invite tier | Duration |
|------|-------|-------------|----------|
| 1 | 200 | `wave_200` | Beta, friends |
| 2 | 2,000 | `wave_2k` | Soft launch |
| 3 | 20,000 | `wave_20k` | Ads / creators |
| 4 | 100,000 | `wave_100k` | Full scale |

## Controls (implemented)

- `PLG_INVITE_ONLY=true` — signup needs invite code
- `POST /v1/waitlist/join` — collect emails
- `POST /v1/admin/invite-codes` — batch generate codes per wave
- Feature flags — toggle UI without new `.exe`
- Kill switch — `kill_switch` table daily spend cap
- LLM queue — `PLG_LLM_QUEUE_SLOTS` + Redis at scale

## Before each wave

1. Run `k6 run cloud/loadtest/k6-smoke.js`
2. Check Sentry error rate < 1%
3. Verify Redis connected (`/health` → `"redis": true`)
4. Supabase Pro if connections spike

## Generate invite codes (wave 2 example)

```bash
curl -X POST https://api.pluginflp.app/v1/admin/invite-codes \
  -H "X-PLG-Admin-Key: $PLG_ADMIN_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"count": 2000, "ramp_tier": "wave_2k", "max_uses": 1}'
```
