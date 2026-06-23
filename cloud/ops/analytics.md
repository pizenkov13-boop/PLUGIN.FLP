# Analytics — PostHog + server events

## Funnel
```
signup → payment_completed → first_beat → beat_generated (retention D7/D30)
```

## Desktop (PostHog)
Env in root `.env`:
```env
PLG_POSTHOG_KEY=phc_xxx
PLG_POSTHOG_HOST=https://eu.i.posthog.com
```

Events via `plg_analytics.track()`:
- `beat_created` (after successful generation)
- `$identify` on cloud login

## Server (`analytics_events` table)
| Event | When |
|-------|------|
| `signup` | Account created |
| `payment_completed` | ЮKassa webhook |
| `first_beat` | First `/v1/generate` success |
| `beat_generated` | Every generation |

## Admin dashboard
`GET /v1/admin/metrics?days=30` (requires `PLG_ADMIN_SECRET`):
- `revenue_rub_estimate` vs `api_spend_usd`
- `signups`, `first_beats`
- `attribution_top` — UTM sources from `profiles`

## PostHog dashboards (manual setup)
1. **Revenue vs cost** — correlate `payment_completed` with generation count × $0.03 est.
2. **Cohort retention** — users with `first_beat` → weekly `beat_generated`
3. **UTM** — property `utm_source` on signup

## UTM capture
Signup body: `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `referrer`
Stored on `profiles` — query paying users by source in admin metrics.

## Privacy
- No prompt text in PostHog
- GDPR: delete account purges `analytics_events` (add to retention job if needed)
