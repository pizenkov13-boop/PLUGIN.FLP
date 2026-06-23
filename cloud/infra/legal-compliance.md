# Legal & compliance (Phase 5)

## Retention cron

Daily purge of generation metadata (no prompt text stored):

```bash
curl -X POST https://api.pluginflp.app/v1/admin/retention/purge \
  -H "X-PLG-Admin-Key: $PLG_ADMIN_SECRET"
```

Or Fly scheduled machine / GitHub Action.

## Env

```env
PLG_PROMPT_LOG_RETENTION_DAYS=90
PLG_PAYMENT_LOG_RETENTION_DAYS=730
PLG_LEGAL_MIN_AGE=16
PLG_DATA_REGION=eu
PLG_SUPPORT_EMAIL=support@pluginflp.app
```

## GDPR delete flow

1. User: Settings → Delete account
2. API: `DELETE /v1/account`
3. Deletes: profile, devices, generation_logs, legal_acceptances, auth user
4. Anonymizes: payment_events (kept 2+ years)

## Before launch

- [ ] Fill placeholders in `legal/*.md`
- [ ] Run `005_legal.sql` on Supabase
- [ ] Publish Terms/Privacy on website
- [ ] Supabase project in **EU** for EU users
- [ ] Register ИП/ООО + ЮKassa
