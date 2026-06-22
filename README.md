# PLUGIN.FLP (PLG)

**prompt → beat → your sound** — Windows desktop app for trap producers using FL Studio.

## What works without a sample library

You do **not** need FL Mafia or downloaded kits to start:

1. Add a Gemini API key in Settings (`.env`)
2. **CREATE BEAT** — AI writes MIDI notes to `output_pattern.json`
3. **OPEN IN FL** — generates `PLG_Session.flp` with starter 808 / hats / melody + notes
4. Swap samples on the named channels when you add your own kits

Empty library = **bundled starter sounds** load into FL automatically. Import kits anytime for your sound.

Build standalone `.exe` (starter inside):

```bat
build_plg.bat
```

Optional CC0 trap upgrade (not required):

```bat
install_starter_sounds.bat
```

## Quick start

```bat
run_plg.bat
```

**Where to click / ship:** see [START_HERE.md](START_HERE.md) (also **Help → Where is everything?** in the app).

| You want | Do this |
|----------|---------|
| Use PLG | `run_plg.bat` or `dist\PLG.exe` |
| Better trap sounds (optional) | **Tools → Upgrade Starter Sounds** or `install_starter_sounds.bat` |
| Build for Gumroad | `build_plg.bat` → upload `dist\PLG.exe` |

Or test FL bridge only (after CREATE BEAT):

```bat
test_open_fl.bat
```

## Tools (no kits required)

| Menu | What it does |
|------|----------------|
| **Install FL Scripts** | Piano roll script pack (hat roll, pan, quantize, …) |
| **Install FL Themes** | Color specs for FL theme editor (`themes/*.json`) |
| **Split Stems** | Optional — needs `pip install demucs` (~2 GB) |

## Docs

- [FL_BRIDGE.md](FL_BRIDGE.md) — how OPEN IN FL works (`.flp` session)
- [FL_SCRIPTS.md](FL_SCRIPTS.md) — piano roll scripts
- [THEMES.md](THEMES.md) — Opium / Chrome / Balenciaga color specs

## Beat quota (planned billing)

30 beats per 30-day period. Regenerate (↻) uses 1 beat — app warns first.  
Dev override: `PLG_SKIP_BEAT_LIMIT=true` in `.env`.

## Dev setup

```bat
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m pytest
python midi_validate.py
```

Optional (heavy): `pip install -r requirements-optional.txt` — demucs, music21, pyflp.

## PR / branch

Active work: `feat/fl-bridge-and-library-buildout` → [PR #1](https://github.com/pizenkov13-boop/PLUGIN.FLP/pull/1)
