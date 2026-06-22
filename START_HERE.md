# PLG — куда нажимать и что где лежит

## Обычный юзер (бит в FL)

1. Запуск: **`run_plg.bat`** или **`dist\PLG.exe`** (после сборки)
2. В приложении: **CREATE BEAT** → **OPEN IN FL** → Play в FL Studio  
3. Звуки уже внутри — **ничего качать не надо**

| Вопрос | Где |
|--------|-----|
| Быстрая инструкция | Меню **Help → Quick Start** |
| Свои киты | **File → Import Kit Folder** или **File → Library** |
| Лучший trap-звук (опционально) | **Tools → Upgrade Starter Sounds (optional)...** |
| Настройки API | **Tools → Settings** |

### Upgrade Starter Sounds (Signature Sounds) — опционально

1. **Tools → Upgrade Starter Sounds (optional)...**  
   или двойной клик **`install_starter_sounds.bat`** в папке PLG  
2. Скачай 3 пака за £0 на Signature Sounds  
3. Положи zip сюда: **`assets\starter\incoming\`**  
4. Запусти bat ещё раз  

Пока не сделал — работает **встроенный** starter (норм для демо).

---

## Ты (продажа / Gumroad)

| Задача | Где |
|--------|-----|
| Собрать `.exe` для продажи | **`build_plg.bat`** в корне `C:\PLUG.FLP` |
| Готовый файл для загрузки | **`dist\PLG.exe`** |
| Проверить FL без GUI | **`test_open_fl.bat`** |
| Доки по FL-мосту | **`FL_BRIDGE.md`** |

### Сборка для Gumroad

```bat
cd C:\PLUG.FLP
build_plg.bat
```

На выходе: **`dist\PLG.exe`** — один файл, starter sounds внутри.  
Юзер: скачал → запустил → API key → CREATE BEAT → OPEN IN FL.

### Что положить на Gumroad

- `PLG.exe` из `dist\`
- Кратко: «Нужен FL Studio + Gemini API key (бесплатный tier ок)»
- Starter sounds included — без FL Mafia

---

## Папки

| Путь | Зачем |
|------|--------|
| `assets\starter\` | Встроенные wav (808, hat, melody) |
| `assets\starter\incoming\` | Сюда zip для CC0-апгрейда |
| `PLG_Library\` | Свои сэмплы юзера |
| `dist\PLG.exe` | Сборка для продажи |
