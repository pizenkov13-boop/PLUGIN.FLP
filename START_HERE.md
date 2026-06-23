# PLG — куда нажимать и что где лежит

## Обычный юзер (подписка + бит в FL)

1. Скачай **`PLG.exe`** с сайта / Gumroad → запусти
2. **Войди** (email + пароль) — API-ключи не нужны, AI на сервере
3. **CREATE BEAT** → опиши бит → **OPEN IN FL** → Play в FL Studio
4. Звуки уже внутри — **ничего качать не надо**

| Вопрос | Где |
|--------|-----|
| Быстрая инструкция | Меню **Help → Quick Start** |
| Подписка / оплата | **Settings → Subscribe** (899 ₽/мес СНГ) |
| Trial | 3 бесплатных бита, потом подписка |
| Свои киты | **Library** или **Tools → Import Kit** |
| Лучший trap-звук (опционально) | **Tools → Upgrade Starter Sounds** |
| Помощь / FAQ | **Help** |

### Подписка

- **СНГ:** 899 ₽/мес через ЮKassa (открывается в браузере)
- **Международная цена** ($14.99) — когда включим Stripe/Paddle
- Лимиты: **30 битов / 30 дней**, **3 бита / день**
- **↻ Regenerate** в Session — минус 1 бит с квоты (с подтверждением)

### Upgrade Starter Sounds (опционально)

1. **Tools → Upgrade Starter Sounds** или **`install_starter_sounds.bat`**
2. Скачай 3 пака за £0 на Signature Sounds
3. Положи zip в **`assets\starter\incoming\`**
4. Запусти bat ещё раз

Пока не сделал — работает **встроенный** starter (норм для демо).

---

## Ты (релиз / продакшен)

| Задача | Где |
|--------|-----|
| Release-сборка (cloud-only) | **`build_plg.bat release`** |
| Готовый файл | **`dist\PLG.exe`** + **`dist\.env`** (Supabase URL + anon key) |
| Cloud API | `cloud/README.md`, деплой Fly + Cloudflare |
| Миграции Supabase | `cloud/supabase/migrations/` |
| Чеклист релиза | **`RELEASE_CHECKLIST.md`** |
| Подпись .exe | `desktop/release-signing.md` |
| Чистая Windows VM | `desktop/clean-windows-test.md` |
| Handoff / polish | **`HANDOFF_OPUS.md`** |

### Сборка release

```bat
cd C:\PLUG.FLP
build_plg.bat release
```

На выходе: **`dist\PLG.exe`** — один файл, starter sounds внутри, **без полей API key в UI**.  
В `dist\.env` пропиши `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `PLG_CLOUD_URL`.

### Локальная разработка (свои ключи)

```bat
copy .env.example .env
run_plg.bat
```

`PLG_CLOUD_MODE=false` — Gemini/Anthropic ключи в **Settings**.

---

## Папки

| Путь | Зачем |
|------|--------|
| `assets\starter\` | Встроенные wav (kick, snare, clap) |
| `assets\starter\incoming\` | Сюда zip для CC0-апгрейда |
| `PLG_Library\` | Свои сэмплы юзера |
| `dist\PLG.exe` | Release-сборка |
| `cloud\` | FastAPI, billing, quota, LLM proxy |
| `web\src\` | React UI |
| `legal\` | Terms, Privacy, Refund (RU+EN) |
