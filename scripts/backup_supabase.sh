#!/usr/bin/env bash
# Weekly Supabase backup — export DATABASE_URL first
set -euo pipefail
if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: Set DATABASE_URL" >&2
  exit 1
fi
mkdir -p backups
OUT="backups/plg_$(date +%Y%m%d_%H%M).dump"
pg_dump "$DATABASE_URL" -Fc -f "$OUT"
echo "Backup saved: $OUT"
