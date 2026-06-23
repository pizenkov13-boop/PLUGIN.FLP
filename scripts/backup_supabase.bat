@echo off
REM Weekly Supabase backup — set DATABASE_URL first (from Supabase dashboard)
if "%DATABASE_URL%"=="" (
  echo ERROR: Set DATABASE_URL to your Supabase Postgres connection string.
  exit /b 1
)
set OUT=backups\plg_%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%.sql
mkdir backups 2>nul
pg_dump "%DATABASE_URL%" -Fc -f "%OUT%"
echo Backup saved: %OUT%
