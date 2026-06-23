# Runbook: Payments not working

## Symptoms
- Checkout URL missing or 502 on `/v1/billing/checkout`
- Webhooks not activating subscriptions
- Users stuck in grace / expired after paying

## Triage
1. ЮKassa merchant cabinet — webhook URL `https://api.pluginflp.app/v1/billing/webhook/yookassa`
2. Check `payment_events` for duplicate `external_id` (idempotency OK) vs zero rows
3. Verify `YOOKASSA_SHOP_ID` + `YOOKASSA_SECRET_KEY` in prod env
4. Test webhook signature with ЮKassa test payment

## Fix paths
| Issue | Action |
|-------|--------|
| Webhook 401/403 | Cloudflare WAF allow ЮKassa IPs |
| Signature fail | Rotate secret, update env, redeploy |
| DB insert fail | Check Supabase logs, RLS on `payment_events` |
| User paid, no activate | Manual: `activate_subscription()` + email user |

## Comms
- Status component `payments` → degraded
- Support macro: ask for payment ID + email, SLA 24h for billing
