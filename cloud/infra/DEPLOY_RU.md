# Деплой PLG — по шагам

## Что уже есть (не надо деплоить)

| Что | Статус |
|-----|--------|
| Supabase (база + auth) | ✅ `huqawbucybjatmvdghtt.supabase.co` |
| SQL-таблицы | ✅ `setup_all.sql` |
| Cloud API (код) | ✅ папка `cloud/` |
| Десктоп PLG | ✅ локально через `run_plg.bat` |

## Что ещё НЕ в интернете

| Что | Куда |
|-----|------|
| Cloud API | Fly.io → `api.pluginflp.app` |
| DNS | Cloudflare (твой домен) |
| Сайт pluginflp.app | отдельно (позже) |
| ЮKassa оплата | кабинет ЮKassa |

---

## Шаг 1 — Деплой API на Fly.io (один раз)

```bat
cd c:\PLUG.FLP
scripts\deploy_cloud.bat
```

Первый раз откроется браузер — войди в Fly.io (бесплатный аккаунт).

Скрипт сам:
- возьмёт ключи из `cloud\.env`
- создаст приложение `plg-api`
- задеплоит Docker-образ

Проверка: https://plg-api.fly.dev/health

---

## Шаг 2 — Домен (Cloudflare)

Если домен `pluginflp.app` у тебя в Cloudflare:

| Тип | Имя | Значение |
|-----|-----|----------|
| CNAME | `api` | `plg-api.fly.dev` |

Прокси (оранжевое облако) — включено.

Проверка: https://api.pluginflp.app/health

---

## Шаг 3 — Десктоп для пользователей

В `.env.release` (уже есть URL) допиши Supabase **publishable** ключ:

```env
SUPABASE_URL=https://huqawbucybjatmvdghtt.supabase.co
SUPABASE_ANON_KEY=sb_publishable_...
PLG_CLOUD_URL=https://api.pluginflp.app
```

Сборка:

```bat
build_plg.bat release
```

`dist\PLG.exe` — отдавать пользователям.

---

## Шаг 4 — Оплата (когда будешь готов)

1. Зарегистрируй магазин в [ЮKassa](https://yookassa.ru)
2. В `cloud\.env` на сервере: `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`
3. Webhook в ЮKassa:
   ```
   https://api.pluginflp.app/v1/billing/webhooks/yookassa
   ```
4. `fly secrets set YOOKASSA_SHOP_ID=... YOOKASSA_SECRET_KEY=... --app plg-api`
5. `fly deploy --config cloud/fly.toml`

---

## Ежедневная работа (dev)

```bat
python cloud\run.py          rem терминал 1
c:\PLUG.FLP\run_plg.bat      rem терминал 2
```

Продакшен API крутится на Fly 24/7 — локально `cloud\run.py` не нужен.
