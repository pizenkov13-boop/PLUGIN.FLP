# PLUGIN.FLP — чеклист до релиза

Отмечай `[x]` по ходу. Фазы 1–7 в коде — см. `cloud/README.md`, `desktop/README.md`.

---

## Инфра и безопасность

- [x] Серверная квота **30/мес + 3/день** (`cloud/app/quota.py`, миграции)
- [x] API keys **только на сервере** (cloud generate; release `.env.release` без ключей в UI)
- [x] **Cloudflare** + rate limits (`cloud/infra/cloudflare.md`, `rate_limit.py`)
- [x] **Kill switch** на API spend (`kill_switch.py`, runbook)
- [x] **Оплата** ЮKassa + webhook + **grace period** (Phase 2)
- [x] **Автообновление** + min client version (`plg_updater.py`, `MIN_CLIENT_VERSION`)
- [x] **Оферта** + владение контентом + **удаление данных** (Phase 5 legal)
- [x] **Ramp** 200→2k→20k→100k, не шлюз в один день (`cloud/infra/ramp-100k.md`)
- [x] **Админка** + метрики cost/revenue (`/v1/admin/metrics`, `admin_ops.py`)
- [ ] **Бета 50 человек** до платной рекламы — см. [`docs/BETA.md`](docs/BETA.md), `landing/`, `scripts/beta_invites.py`
- [ ] Supabase миграции **002–006** применены на prod
- [ ] `dist\.env` заполнен (`SUPABASE_*`, `PLG_CLOUD_URL`)
- [ ] Resend + SPF/DKIM/DMARC (`cloud/ops/email-deliverability.md`)
- [ ] Code signing `PLG.exe` (`desktop/release-signing.md`)
- [ ] Чистая VM: `desktop/clean-windows-test.md`

---

## Экономика (напоминание)

| Масштаб | Выручка (899 ₽/мес) | API cost (оценка) |
|---------|---------------------|-------------------|
| **200** юзеров | ≈ **180k ₽/мес** | копейки |
| **100k** юзеров | ≈ **90M ₽/мес** | **~3–7%** при Flash + лимитах |

**Главный риск — не API, а абуз без серверной квоты.** Квота + device binding + CAPTCHA + баны — обязательны до рекламы.

---

## Мультиязычный поток (как работает в фоне)

```
Промпт на родном языке (ar/zh/fr/…)
        ↓
prompt_locale.py + assets/prompt_tags.json
  → системные теги OPIUM | RAGE | PHONK | …
  → обогащённый EN-промпт для LLM
        ↓
LLM (только на сервере) → output_pattern.json
        ↓
beat_humanize / drum_defaults / MIDI  ← язык не важен, одна математика
        ↓
READ_ME_IMBA.txt на языке UI (plg_locale в паттерне)
```

Подробнее: `docs/MULTILINGUAL_FLOW.md`

- [x] JSON-словарь ключевых слов → теги (`assets/prompt_tags.json`)
- [x] Нормализация промпта перед LLM (`prompt_locale.py`)
- [x] `READ_ME_IMBA` на 9 языках (`mix_blueprint` + `assets/mix_blueprint_i18n.json`)
- [x] Locale с десктопа → cloud generate → паттерн
- [ ] PostHog воронка по языкам (dashboard вручную)

---

## Phase 8 (до публичного лонча)

- [x] Landing + waitlist form (`landing/`, `POST /v1/waitlist/join`)
- [x] Beta invite generator (`scripts/beta_invites.py`, `PLG_INVITE_ONLY`)
- [x] Auth UI: invite code + waitlist link
- [ ] 60s demo video on landing
- [ ] Бета 50 с обратной связью (ops)
- [ ] Telegram/Discord community после беты

---

## Быстрый smoke перед каждым релизом

```bat
python -m pytest tests/ -q
cd web && npm run build
build_plg.bat release
```

Login → 1 beat → Regenerate (−1) → Open FL → Help FAQ → Settings feedback.
