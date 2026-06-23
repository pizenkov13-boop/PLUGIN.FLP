# Clean Windows test — `build_plg.bat`

Run on a **fresh Windows 10/11 VM** (no Python, no Node) before wide release.

## Build machine (dev)

```bat
install_deps.bat
build_plg.bat release
```

Output: `dist\PLG.exe` + `dist\.env` (from `.env.release` — edit Supabase keys).

## VM checklist

1. Copy `dist\PLG.exe` and `dist\.env` to `C:\PLG\`
2. Double-click `PLG.exe` — app opens, **login screen** (no API key fields)
3. Sign up / log in with test account
4. Create beat — completes without local API keys
5. **Regenerate (↻)** — confirm dialog “−1 beat”, new pattern
6. Disconnect network — **offline banner** appears; generation shows clear error
7. Reconnect — banner clears
8. **No FL installed** — onboarding card visible; Open in FL shows guided error (not silent)
9. Install FL Studio 21+ → Settings → Install FL Scripts → Open in FL works
10. Settings → Check for updates — manifest response (or “up to date”)
11. Force crash (optional) — verify event in Sentry if `PLG_SENTRY_DSN` set

## Optional FL matrix

Repeat step 9 with FL **20**, **24**, **2025** — see `FL_VERSIONS.md`.

## Pass criteria

- No Python/Node required on VM
- No API key UI in release build
- SmartScreen: signed build shows publisher name; unsigned shows warning only (expected)

## Fail artifacts

Collect `%LOCALAPPDATA%\PLG\` and `plg_session.log` next to exe for support.
