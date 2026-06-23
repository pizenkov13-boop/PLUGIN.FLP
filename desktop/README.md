# Phase 7 — Desktop release

## Release build (cloud-only, no API keys)

```bat
build_plg.bat release
```

- Bundles `web/dist`, starter sounds, docs
- Copies `.env.release` → `dist\.env` (add `SUPABASE_URL` + `SUPABASE_ANON_KEY`)
- First launch seeds `.env` from bundle if missing

Users see **login only** — Gemini/Anthropic fields hidden when `PLG_CLOUD_MODE=true`.

## Regenerate UI

Session + Home: **↻ Regenerate** with confirm dialog and **−1 beat** label.

## Auto-update

- Manifest: `GET /v1/release/manifest` (public)
- Desktop: Settings → Updates → Check / Download / Restart
- Env: `PLG_UPDATE_MANIFEST_URL`, `PLG_RELEASE_DOWNLOAD_URL` on server

## Code signing

See `desktop/release-signing.md`. Optional:

```bat
set PLG_SIGN_CERT=CN=Your Company
build_plg.bat release
```

## Offline mode

Red banner when cloud unreachable; generation blocked with clear message.

## Sentry crashes

```env
PLG_SENTRY_DSN=https://...
```

`sentry-sdk` in `requirements.txt`; unhandled exceptions reported from job threads.

## Clean Windows test

`desktop/clean-windows-test.md` — VM checklist after `build_plg.bat release`.

## FL Studio

- Onboarding banner when FL missing or scripts not installed
- `FL_VERSIONS.md` — compatibility matrix (12, 20–25, 2025)
- Open in FL → guided error if FL not found
