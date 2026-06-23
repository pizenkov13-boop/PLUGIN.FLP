# Support at 100k users — staffing plan

**SLA:** 24–48h first response (business days). Not 24/7 until revenue supports it.

## Tiers

| Scale | Team | Channels |
|-------|------|----------|
| 0–2k | Founder + 1 part-time | Email, Telegram |
| 2k–20k | 2 FTE support + founder escalation | + status page, FAQ i18n |
| 20k–100k | 4–6 FTE (2 shifts EU/CIS) + 1 billing specialist | + Discord mod volunteers |

## Roles
1. **L1** — FAQ, password reset, quota questions, refund requests (macro replies)
2. **L2** — billing disputes, account bans, log review (`feedback_submissions.log_excerpt`)
3. **On-call engineer** — API/payments runbooks (rotation weekly)

## Tools
- Shared inbox: `support@pluginflp.app` (Help Scout / Front / Gmail shared)
- Telegram: `@pluginflp_support` bot → ticket queue
- Macros in RU + EN (expand with i18n FAQ)
- Admin: `/v1/admin/users`, `/v1/admin/metrics`

## Metrics
- First response time (target < 24h)
- CSAT after ticket close (optional PostHog survey)
- % deflected by FAQ (in-app Help views)

## Hiring trigger
Add L1 when > 30 tickets/day sustained or SLA breach > 10%.
