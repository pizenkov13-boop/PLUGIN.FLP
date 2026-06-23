# Database backups

## Supabase Pro (recommended at 2k+ users)

Dashboard → **Database → Backups**:

- Enable **daily automatic backups** (7-day retention on Pro)
- Enable **Point-in-Time Recovery (PITR)** on Team plan for prod

## Manual pg_dump (weekly archive)

Requires `DATABASE_URL` from Supabase → Settings → Database → Connection string (URI).

### Windows

```bat
scripts\backup_supabase.bat
```

### Linux / CI

```bash
./scripts/backup_supabase.sh
```

Store dumps encrypted (S3 / Backblaze / local vault). **Never commit dumps to git.**

## Restore drill (quarterly)

1. Restore to staging Supabase branch
2. Run `pytest tests/test_cloud_*.py` against staging API
3. Document time-to-restore in ops log

## What to backup

| Asset | Method |
|-------|--------|
| Postgres | Supabase daily + pg_dump |
| Auth users | included in Postgres |
| Payment events | Postgres |
| Redis rate limits | ephemeral — no backup |
| LLM keys | secrets manager / Fly secrets |
