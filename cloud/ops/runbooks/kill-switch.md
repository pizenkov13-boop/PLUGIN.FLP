# Runbook: Kill switch

## When to use
- Runaway API spend (>$ cap in hours)
- Provider account compromised
- Critical security incident
- Legal takedown

## Disable generation (immediate)
```sql
UPDATE public.kill_switch SET enabled = false WHERE id = 1;
```
Or admin env `PLG_KILL_SWITCH=false` if wired.

## Re-enable
1. Confirm root cause fixed
2. Reset `today_spend_usd` if false alarm
3. `UPDATE kill_switch SET enabled = true WHERE id = 1`
4. Post on status page + Telegram

## Desktop impact
- Users see quota/billing errors or "generation unavailable"
- Billing/checkout can stay up — do not block payments unless fraud
