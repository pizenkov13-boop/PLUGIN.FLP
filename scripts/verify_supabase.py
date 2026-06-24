#!/usr/bin/env python3
"""Verify Supabase credentials and schema after setup."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "cloud" / ".env")


def main() -> int:
    url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    anon = (os.getenv("SUPABASE_ANON_KEY") or "").strip()
    service = (
        os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SECRET_KEY") or ""
    ).strip()
    jwt = (os.getenv("SUPABASE_JWT_SECRET") or "").strip()
    jwks = (os.getenv("SUPABASE_JWKS_URL") or "").strip()
    if not jwks and url and "YOUR_PROJECT" not in url:
        jwks = f"{url}/auth/v1/.well-known/jwks.json"

    errors: list[str] = []
    if not url or "YOUR_PROJECT" in url:
        errors.append("SUPABASE_URL is missing or still a placeholder.")
    if not anon or anon == "your-anon-key":
        errors.append("SUPABASE_ANON_KEY is missing or still a placeholder.")
    if not service or service == "your-service-role-key":
        errors.append("SUPABASE_SERVICE_KEY is missing (needed for cloud API).")
    if not jwt and not jwks:
        errors.append("SUPABASE_JWT_SECRET or SUPABASE_JWKS_URL is missing.")
    elif jwt and jwt == "your-jwt-secret":
        errors.append("SUPABASE_JWT_SECRET is still a placeholder.")

    if errors:
        print("Configuration errors:")
        for e in errors:
            print(f"  - {e}")
        return 1

    try:
        import httpx

        resp = httpx.get(f"{url}/auth/v1/health", timeout=15.0)
        if resp.status_code >= 500:
            errors.append(f"Supabase health check failed: HTTP {resp.status_code}")
    except Exception as exc:
        errors.append(f"Cannot reach Supabase: {exc}")

    try:
        from supabase import create_client

        client = create_client(url, service)
        client.table("kill_switch").select("id").limit(1).execute()
        client.table("profiles").select("id").limit(1).execute()
        client.table("feature_flags").select("key").limit(1).execute()
        print("OK: service role can read kill_switch, profiles, feature_flags.")
    except Exception as exc:
        msg = str(exc)
        if "feature_flags" in msg or "PGRST205" in msg or "does not exist" in msg.lower():
            errors.append(
                "Tables missing — run cloud/supabase/setup_all.sql in Supabase SQL Editor."
            )
        else:
            errors.append(f"Supabase query failed: {exc}")

    if errors:
        print("\nVerification failed:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("\nSupabase is configured correctly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
