# Email deliverability (SPF / DKIM / DMARC)

Sender: `noreply@pluginflp.app` via [Resend](https://resend.com).

## DNS records (pluginflp.app)

Add in Cloudflare / registrar:

### SPF
```
TXT @ "v=spf1 include:amazonses.com include:resend.com ~all"
```
(Adjust if Resend docs specify different include — verify in Resend dashboard.)

### DKIM
Resend dashboard → Domains → copy CNAME records (usually `resend._domainkey`).

### DMARC
```
TXT _dmarc "v=DMARC1; p=quarantine; rua=mailto:dmarc@pluginflp.app; pct=100"
```
Start with `p=none` for 2 weeks monitoring, then `quarantine`.

## Templates (auto-email)
| Event | Template | Trigger |
|-------|----------|---------|
| Payment success | `payment_success` | ЮKassa webhook |
| Subscription expiring | `subscription_expiring` | Cron (TODO) |
| Daily quota | `quota_daily_limit` | 429 handler |
| Monthly quota | `quota_monthly_limit` | 429 handler |
| Welcome | `welcome` | Signup (optional) |
| Password reset | Supabase Auth | Built-in |

## Monitoring
- Resend dashboard: bounce rate < 2%
- `notification_log` table: `status=failed`
- Gmail Postmaster Tools

## Support replies
Use `support@pluginflp.app` (separate mailbox or Resend inbound) — not `noreply@`.
