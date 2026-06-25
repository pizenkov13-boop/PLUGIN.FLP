#!/usr/bin/env python3
"""Generate beta invite codes via the cloud admin API.

Examples:
    set PLG_ADMIN_SECRET=your-secret
    python scripts/beta_invites.py --count 50 --api https://api.pluginflp.app

    python scripts/beta_invites.py --count 10 --api http://127.0.0.1:8080 --out invites.txt
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate PLG beta invite codes")
    parser.add_argument("--count", type=int, default=50, help="Codes to create (max 500)")
    parser.add_argument("--api", default=os.environ.get("PLG_CLOUD_URL", "http://127.0.0.1:8080"))
    parser.add_argument("--admin-secret", default=os.environ.get("PLG_ADMIN_SECRET", ""))
    parser.add_argument("--ramp-tier", default="beta_50", help="Stored on invite_codes.ramp_tier")
    parser.add_argument("--max-uses", type=int, default=1, help="Uses per code (default 1)")
    parser.add_argument("--out", type=Path | None, default=None, help="Write codes to file")
    args = parser.parse_args(argv)

    secret = (args.admin_secret or "").strip()
    if not secret:
        print("Set PLG_ADMIN_SECRET or pass --admin-secret", file=sys.stderr)
        return 1

    api = str(args.api).rstrip("/")
    payload = {
        "count": max(1, min(500, int(args.count))),
        "ramp_tier": args.ramp_tier,
        "max_uses": int(args.max_uses),
    }
    try:
        resp = httpx.post(
            f"{api}/v1/admin/invite-codes",
            json=payload,
            headers={"X-PLG-Admin-Key": secret},
            timeout=30.0,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"Admin API failed: {exc}", file=sys.stderr)
        return 1

    data = resp.json()
    codes = data.get("codes") or []
    if not codes:
        print("No codes returned.", file=sys.stderr)
        return 1

    text = "\n".join(codes) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"Wrote {len(codes)} codes to {args.out}")
    else:
        print(text, end="")

    print(f"# {len(codes)} invite codes · tier={args.ramp_tier}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
