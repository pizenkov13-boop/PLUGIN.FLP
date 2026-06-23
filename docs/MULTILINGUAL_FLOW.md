# Мультиязычный pipeline PLUGIN.FLP

## Идея

Школьник из ОАЭ или Японии пишет промпт **на родном языке**. Музыкальному ядру всё равно — тики, clap −3 ms, 6 dB rule и фаза 808 одинаковы для всех. Язык влияет только на **вход** (теги для LLM) и **выход** (READ_ME_IMBA для человека).

## 1. Универсальный JSON-переводчик

`assets/prompt_tags.json` — компактный словарь:

- **Системные теги:** `OPIUM`, `RAGE`, `PHONK`, `METRO`, `PLUGGNB`, `MELODIC`, `DETROIT`
- **Настроения:** `dark`, `hard`, `fast`, `distorted`, `airy`, …
- Ключевые слова на **en, ru, es, pt, zh, ja, fr, de, ar**

`prompt_locale.prepare_prompt_for_llm()`:

1. Сканирует промпт по всем языкам словаря
2. Собирает `plg_style_tags: ["OPIUM", "RAGE", …]`
3. Строит `llm_prompt` — английское обогащение + оригинал в скобках
4. Сохраняет `user_prompt` (оригинал) в паттерне

Сервер (cloud) и локальный dev вызывают одну функцию **до** `generate_pattern()`.

## 2. Жёсткая математика

`beat_humanize.py`, `hat_roll_engine.py`, `drum_defaults.py` — без i18n.  
LLM отдаёт JSON; humanize правит velocity, clap pre-delay, sidechain, hat rolls.

## 3. READ_ME_IMBA на языке UI

`plg_locale` в паттерне (`en` | `ru` | …) — с десктопа при Create beat.  
`mix_blueprint.build_mix_blueprint()` читает `assets/mix_blueprint_i18n.json` и пишет гайд на выбранном языке.

## Передача locale

```
React (localStorage plg_locale)
  → start_beat(prompt) + set_ui_locale в plg_api
  → cloud POST /v1/generate { prompt, locale }
  → pattern.plg_locale + normalized prompt metadata
  → export_mix_blueprint() на клиенте после bake
```

## Расширение словаря

Добавь строку в `prompt_tags.json` → деплой без смены кода.  
Для редких языков без совпадений промпт уходит в LLM как есть (оригинал + EN hint).
