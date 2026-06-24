#!/usr/bin/env bash
# Deploy the PLG Cloud API on a fresh Ubuntu/Debian VPS (RU-friendly hosts:
# Timeweb / Selectel / Beget / Yandex Cloud — paid in rubles).
#
# Prereqs on the box: this repo present (git clone or scp) and cloud/.env filled.
# Run from the repo root:
#   PLG_API_DOMAIN=api.pluginflp.app bash scripts/deploy_vps.sh
#
# The domain's A record must already point at this server's IP, and ports
# 80 + 443 must be open in the provider firewall.
set -euo pipefail

: "${PLG_API_DOMAIN:?Set PLG_API_DOMAIN=your.domain (its A-record must point at this VPS)}"

if [ ! -f cloud/.env ]; then
  echo "ERROR: cloud/.env missing. Copy cloud/.env.example -> cloud/.env and fill Supabase + Gemini keys." >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo ">> Installing Docker..."
  curl -fsSL https://get.docker.com | sh
fi

echo ">> Building and starting api + caddy (auto-HTTPS for ${PLG_API_DOMAIN})..."
PLG_API_DOMAIN="${PLG_API_DOMAIN}" docker compose up -d --build

echo ""
echo ">> Up. Give Caddy ~30s for the TLS cert, then check:"
echo "     curl https://${PLG_API_DOMAIN}/health"
echo "   Logs:    docker compose logs -f api"
echo "   Update:  git pull && PLG_API_DOMAIN=${PLG_API_DOMAIN} docker compose up -d --build"
