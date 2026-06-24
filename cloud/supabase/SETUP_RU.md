# Supabase — настройка PLG (с нуля)

## 1. Создай проект

1. [supabase.com/dashboard](https://supabase.com/dashboard) → **New project**
2. Имя: `plg-dev` (или любое)
3. Регион: **EU (Frankfurt)** — для GDPR
4. Пароль БД — сохрани (для бэкапов)

## 2. Прогони SQL

1. **SQL Editor** → **New query**
2. Скопируй весь файл [`setup_all.sql`](./setup_all.sql)
3. **Run** — без ошибок внизу

Это создаёт таблицы: `profiles`, `user_devices`, `payment_events`, `feature_flags`, `feedback_submissions` и т.д.

## 3. Auth (для локальной разработки)

**Authentication → Providers → Email** — включён

**Authentication → Settings:**

- **Confirm email** — выключи для dev (иначе регистрация не пустит без письма)
- JWT expiry — 3600 сек (1 час), как в README

## 4. Ключи API

**Project Settings → API:**

| Поле в `.env` | Откуда |
|---------------|--------|
| `SUPABASE_URL` | Project URL |
| `SUPABASE_ANON_KEY` | `anon` `public` |
| `SUPABASE_SERVICE_KEY` | `service_role` `secret` (только сервер!) |
| `SUPABASE_JWT_SECRET` | JWT Settings → JWT Secret |

## 5. Автоматическая настройка `.env`

Из корня репозитория:

```bat
scripts\setup_supabase.bat
```

Скрипт спросит ключи, запишет `cloud/.env` и обновит корневой `.env`, затем проверит подключение.

Или вручную:

**Корневой `.env`** (десктоп):

```env
PLG_CLOUD_MODE=true
PLG_CLOUD_URL=http://127.0.0.1:8787
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
PLG_ENV=development
```

**`cloud/.env`** (API-сервер) — скопируй из `cloud/.env.example` и заполни `SUPABASE_*` + `GEMINI_API_KEY`.

## 6. Запуск

```bat
pip install -r cloud\requirements.txt
python cloud\run.py
```

Проверка: http://127.0.0.1:8787/health

Перезапусти `run_plg.bat` → экран входа → **Аккаунт** с полным профилем.

## 7. Проверка

```bat
python scripts\verify_supabase.py
```

## Безопасность

- `service_role` и `JWT Secret` — **никогда** в клиент / GitHub
- `anon` key — только в десктопе (корневой `.env`)
- Для продакшена: включи Confirm email, CAPTCHA (`PLG_CAPTCHA_PROVIDER=turnstile`)
