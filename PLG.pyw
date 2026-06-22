"""PLG desktop entry point (no console window on Windows)."""

from __future__ import annotations

import os
from pathlib import Path

os.chdir(Path(__file__).resolve().parent)

from plg_app import main

if __name__ == "__main__":
    main()
