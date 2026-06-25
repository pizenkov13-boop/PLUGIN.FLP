# PLUGIN.FLP — Beta 50 runbook

Private beta before paid ads. Backend pieces already exist; this doc wires ops.

## 1. Cloud env (production)

```env
PLG_INVITE_ONLY=true
PLG_WAITLIST_MODE=true
PLG_ADMIN_SECRET=<strong-secret>
PLG_ALLOWED_ORIGINS=https://pluginflp.app,https://www.pluginflp.app
```

Apply Supabase migrations `002`–`006` on prod (`cloud/supabase/SETUP_RU.md`).

## 2. Landing + waitlist

Static site: [`landing/index.html`](../landing/index.html)

1. Set `<meta name="plg-api" content="https://api.pluginflp.app" />`
2. Deploy folder to `pluginflp.app` (Cloudflare Pages, Vercel, or S3+CF)
3. Form posts to `POST /v1/waitlist/join` with `ramp_tier: beta_50`

## 3. Generate 50 invite codes

```bat
set PLG_ADMIN_SECRET=your-secret
set PLG_CLOUD_URL=https://api.pluginflp.app
python scripts/beta_invites.py --count 50 --out beta_invites.txt
```

Distribute codes manually (email / Telegram DM). Each code is single-use by default.

## 4. Desktop client

Release build with cloud mode (`PLG_CLOUD_MODE=true` in `dist\.env`). Signup shows invite field when `invite_required` from `/v1/auth/config`.

## 5. Smoke checklist

- [ ] Waitlist join from landing (200 OK)
- [ ] Signup with valid invite code
- [ ] Signup without code → 403
- [ ] Login → generate beat → Open FL
- [ ] 👍/👎 rating saves locally
- [ ] Settings → feedback

## 6. After beta

- Collect feedback (`feedback_submissions`, 👍/👎 patterns)
- Tune `genre_profiles.json` if needed
- Ramp: `cloud/infra/ramp-100k.md`
- Telegram community: `PLG_SUPPORT_TELEGRAM`
