# PLUGIN.FLP — Handoff для Claude Opus 4.8 (polish pass)

**Дата:** 2025-06-23  
**Репо:** `C:\PLUG.FLP`  
**Ветка:** `feat/fl-bridge-and-library-buildout` (много изменений **не закоммичено** — фазы 2–7 + i18n)  
**Тесты:** `78 passed` (`python -m pytest tests/ -q`)  
**Frontend:** `cd web && npm run build` — OK  

**Цель продукта:** Windows desktop → prompt → LLM → `output_pattern.json` → samples → `PLG_Session.flp` → FL Studio.  
**Cloud mode:** подписка 899 ₽/мес (СНГ) / $14.99 intl — AI на сервере, без API keys в клиенте.

---

## Архитектура (как сейчас)

```
PLG.pyw → plg_webview.py (pywebview + WebView2)
              ↓ window.pywebview.api.*
         plg_api.py (UI-agnostic, jobs, quota)
              ↓
    ┌─────────┴──────────┐
    │ cloud              │ local dev
    PLG_CLOUD_MODE=true  PLG_CLOUD_MODE=false
    plg_cloud.py         backend_core.run_pipeline + .env keys
    POST /v1/generate     Gemini/Anthropic local
              ↓
    run_pipeline_from_pattern (humanize, MIDI, stems, READ_ME)
              ↓
    FL: fl_launch.py → PLG_Session.flp + scripts
```

**React UI:** `web/src/` → `web/dist/` (бандлится в `PLG.exe` через PyInstaller).

---

## Фаза 1 — Cloud MVP ✅

| Что | Где |
|-----|-----|
| FastAPI cloud API | `cloud/app/main.py`, `cloud/run.py` |
| Supabase auth proxy | `cloud/app/auth.py`, desktop `plg_cloud.py` |
| JWT + refresh на десктопе | `plg_cloud.login/refresh_session` |
| `POST /v1/generate` — LLM только на сервере | `cloud/app/llm_proxy.py` |
| Квота trial 3 + 30/30д + 3/день | `cloud/app/quota.py` |
| Device binding max 3 | `cloud/app/devices.py`, `plg_device.py` |
| Desktop cloud mode gate | `web/src/App.tsx` → `AuthView` |
| Schema | `cloud/supabase/schema.sql` |

**Env desktop:** `PLG_CLOUD_MODE`, `PLG_CLOUD_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`

---

## Фаза 2 — Платежи ✅ (ЮKassa live, Stripe/Paddle stubs)

| Что | Где |
|-----|-----|
| ЮKassa checkout CIS 899 ₽ | `cloud/app/billing.py`, `providers/yookassa_provider.py` |
| Webhooks + idempotency | `payment_events` table, `migrations/002_payments.sql` |
| Grace 3 дня | `PLG_GRACE_DAYS`, billing snapshot |
| Trial beats | `PLG_TRIAL_BEATS` |
| Desktop Subscribe | `SettingsView.tsx`, `cloud_billing_checkout` |
| Stripe/Paddle | webhook routes есть, провайдеры — **заглушки** |

**Не сделано / polish:** dunning cron, customer portal, VAT receipts, promo codes.

---

## Фаза 3 — Security ✅

| Что | Где |
|-----|-----|
| Rate limits 1/15s, 20/hr user, 100/hr IP | `cloud/app/rate_limit.py` |
| CAPTCHA Turnstile/hCaptcha | `cloud/app/captcha.py`, `AuthView.tsx` |
| Honeypot signup | поле `website` |
| Trial anti-farming | `device_trial_claims`, `migrations/003_security.sql` |
| Bans + admin ban API | `security_bans`, `cloud/app/admin.py` |
| Abuse alerts | `cloud/app/abuse.py` |
| LLM queue slots | `cloud/app/queue.py`, `PLG_LLM_QUEUE_SLOTS` |
| Content moderation | `cloud/app/moderation.py` |
| Cloudflare docs | `cloud/infra/cloudflare.md` |
| Tests | `tests/test_cloud_security.py` |

---

## Фаза 4 — Infra ✅

| Что | Где |
|-----|-----|
| Dockerfile + fly.toml | `cloud/Dockerfile`, `cloud/fly.toml`, `render.yaml` |
| Redis (Upstash) rate limits + LLM slots | `cloud/app/redis_store.py` |
| Sentry server + desktop | `cloud/app/sentry_init.py`, `plg_sentry.py` |
| Feature flags | `feature_flags`, `GET /v1/flags` |
| Waitlist + invite codes | `cloud/app/waitlist.py`, `migrations/004_infra.sql` |
| k6 load tests | `cloud/loadtest/` |
| Staging env | `cloud/.env.staging.example`, `infra/staging.md` |
| Ramp 200→2k→20k→100k | `cloud/infra/ramp-100k.md` |
| Tests | `tests/test_cloud_infra.py` |

---

## Фаза 5 — Legal ✅

| Что | Где |
|-----|-----|
| Terms / Privacy / Refund RU+EN | `legal/*.md` |
| ИП checklist | `legal/BUSINESS_RU.md` (плейсхолдеры `[НАИМЕНОВАНИЕ]`, `[ИНН]`) |
| Signup terms + age 16+ | `AuthView.tsx`, `signup.py` |
| GDPR delete | `DELETE /v1/account`, Settings button |
| Retention 90d prompts | `cloud/app/purge_retention.py`, `migrations/005_legal.sql` |
| Tests | `tests/test_cloud_legal.py` |

**Polish:** заполнить legal placeholders, `START_HERE.md` всё ещё про API keys — устарел.

---

## Фаза 6 — Ops ✅

| Что | Где |
|-----|-----|
| Support SLA, Telegram, FAQ 9 языков | `HelpView.tsx`, `web/src/i18n/faq.ts` |
| Status JSON | `GET /v1/status`, `cloud/app/status_page.py` |
| Feedback + log attach | `POST /v1/feedback`, `plg_log.py`, `SettingsView` |
| Email Resend templates | `cloud/app/email.py` (payment success wired в ЮKassa webhook) |
| SPF/DKIM docs | `cloud/ops/email-deliverability.md` |
| Admin users/metrics/UTM | `admin_ops.py`, `/v1/admin/*` |
| Runbooks | `cloud/ops/runbooks/*.md` |
| PostHog desktop | `plg_analytics.py` |
| Server analytics_events | `analytics_ops.py`, UTM on signup |
| Migration | `migrations/006_ops.sql` |
| Tests | `tests/test_cloud_ops.py` |

**Не сделано:** cron для `subscription_expiring` / quota emails; хостинг status.pluginflp.app; PostHog dashboards вручную.

---

## Фаза 7 — Desktop release ✅

| Что | Где |
|-----|-----|
| Release без API keys | `.env.release`, `build_plg.bat release`, `PLG_RELEASE_BUILD` |
| Regenerate ↻ + «−1 бит» confirm | `SessionView`, `HomeView`, `App.tsx`, `startRegenerate` |
| Auto-update | `plg_updater.py`, `GET /v1/release/manifest`, Settings Updates |
| Code signing hooks | `build_plg.bat` + `desktop/release-signing.md` |
| Offline banner | `OfflineBanner.tsx`, `network_online` в `get_status()` |
| Sentry crashes | `sentry-sdk` в requirements, excepthook в `plg_sentry.py` |
| FL onboarding (нет FL / нет scripts) | `FlOnboardingBanner.tsx` |
| FL versions doc | `FL_VERSIONS.md` (12, 20–25, 2025) |
| Clean VM checklist | `desktop/clean-windows-test.md` |
| PyInstaller | `PLG.spec`, `build_plg.bat` |

---

## Мультиязычность (cross-cutting) ✅

```
Промпт (ar/zh/fr/…) 
  → prompt_locale.py + assets/prompt_tags.json 
  → теги OPIUM|RAGE|PHONK|… 
  → LLM (server)
  → beat_humanize (язык не важен)
  → READ_ME_IMBA на plg_locale (9 языков)
```

| Файл | Роль |
|------|------|
| `assets/prompt_tags.json` | Ключевые слова → системные теги |
| `prompt_locale.py` | `prepare_prompt_for_llm()` |
| `assets/mix_blueprint_i18n.json` | READ_ME строки |
| `mix_blueprint_i18n.py` | Loader |
| `mix_blueprint.py` | Локализованный blueprint |
| `docs/MULTILINGUAL_FLOW.md` | Архитектура |
| UI locale → API | `set_ui_locale`, `startBeat(prompt, locale)`, `GenerateBody.locale` |

**Polish для Opus:**
- Расширить `prompt_tags.json` (больше жанров/сленга)
- `list_blueprint_steps()` в UI checklist — **всё ещё на русском/английском в коде**, не из i18n
- BlueprintChecklist steps не локализованы

---

## Фаза 8 — НЕ НАЧАТА ⏳

- [ ] Landing page + 60s demo video
- [ ] Closed beta 50 users (invite-only gate перед рекламой)
- [ ] Telegram/Discord community launch
- [ ] Обновить маркетинговый copy

---

## Ключевые файлы (карта)

### Desktop
- `PLG.pyw` — entry
- `plg_webview.py` — pywebview bridge
- `plg_api.py` — вся логика для UI (~1100 строк)
- `plg_cloud.py` — HTTP client cloud
- `backend_core.py` — pipeline LLM→pattern→MIDI
- `beat_humanize.py`, `producer_brain.py` — Opium/Rage математика
- `fl_launch.py`, `flp_writer.py`, `fl_setup.py` — FL bridge

### Web UI
- `web/src/App.tsx` — shell, jobs, offline, regenerate
- `web/src/components/*` — views
- `web/src/i18n/` — 9 locales

### Cloud
- `cloud/app/main.py` — все routes
- `cloud/app/*.py` — модули по фазам
- `cloud/supabase/migrations/002-006.sql`

### Docs / Ops
- `RELEASE_CHECKLIST.md` — чеклист до релиза
- `cloud/README.md` — setup phases 1–6
- `desktop/README.md` — phase 7
- `cloud/ops/` — runbooks

---

## Экономика (не забыть)

| Масштаб | MRR (899 ₽) | API cost est. |
|---------|-------------|---------------|
| 200 users | ~180k ₽ | копейки |
| 100k users | ~90M ₽ | ~3–7% при Flash + лимитах |

**Главный риск — абуз без серверной квоты**, не стоимость API.

---

## Что Opus должен довести до «конфетки» (приоритет)

### P0 — блокеры релиза
1. **Применить миграции 002–006 на prod Supabase**
2. **Заполнить** `legal/*.md` placeholders, `dist/.env` / `.env.release` с реальными Supabase keys
3. **Deploy cloud** на Fly + Cloudflare (см. `cloud/fly.toml`, `cloud/infra/cloudflare.md`)
4. **ЮKassa webhook** на prod URL — smoke test оплаты end-to-end
5. **`build_plg.bat release`** → тест на чистой VM (`desktop/clean-windows-test.md`)
6. **Code signing** или осознанный waiver + SmartScreen copy для юзеров

### P1 — качество кода
1. **Синхронизировать `APP_VERSION`** — сейчас `PLG_APP_VERSION` env vs hardcoded местами
2. **Stripe/Paddle** — довести stubs до рабочего intl checkout или явно скрыть за feature flag
3. **Email cron** — subscription_expiring, quota_limit (`cloud/app/email.py` templates есть)
4. **Error UX** — ветвление по `error_type` в React (auth/network/quota/subscription) везде, не только generate
5. **`START_HERE.md`** — переписать под cloud subscription, не Gumroad/API keys
6. **BlueprintChecklist + `list_blueprint_steps`** — полная i18n
7. **PostHog** — funnel dashboard + `first_beat` retention

### P2 — polish
1. UI/visual pass (см. ui-ux skill если нужно)
2. Расширить `prompt_tags.json` + тесты на zh/ar/ja edge cases
3. Admin UI (сейчас только API) — опционально простая web admin
4. `status.pluginflp.app` — статическая страница на `/v1/status` JSON
5. Phase 8 landing + beta 50 flow (`PLG_INVITE_ONLY`)

### P3 — tech debt
1. `plg_app.py` (tkinter) — legacy fallback, можно deprecate
2. Дубли import в `fl_launch.py`
3. CI pipeline (GitHub Actions): pytest + `npm run build` + optional k6
4. Consolidate `.env.example` root vs `cloud/.env.example`

---

## Команды для проверки

```bat
pip install -r requirements.txt -r cloud/requirements.txt
python -m pytest tests/ -q
cd web && npm run build
python cloud/run.py
PLG_CLOUD_MODE=true run_plg.bat
build_plg.bat release
```

---

## Публичные endpoints (без JWT)

`/health`, `/v1/status`, `/v1/release/manifest`, `/v1/auth/signup`, `/v1/auth/config`, `/v1/flags`, `/v1/waitlist/*`, `/v1/legal`, billing webhooks.

---

## Контекст для Opus

Вся bulk-реализация фаз 2–7 делалась **быстро** («завтра клод проверит»). Архитектура цельная, тесты зелёные, но:
- много **доков-заглушек** с плейсхолдерами
- **Stripe/intl** не production-ready
- **cron/email** не wired
- UI **функционален**, не pixel-perfect
- **не всё закоммичено** — проверь `git status` перед PR

**Задача Opus:** P0 релиз → P1 качество → P2 polish. Не переписывать с нуля — минимальные точечные diff'ы в стиле кодовой базы.
