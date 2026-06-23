#!/usr/bin/env python3
"""Purge old generation logs — run daily via cron / Fly scheduler."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "cloud" / ".env")

from cloud.app.auth import service_client
from cloud.app.legal import purge_generation_logs


def main() -> None:
    result = purge_generation_logs(service_client())
    print(result)


if __name__ == "__main__":
    main()
