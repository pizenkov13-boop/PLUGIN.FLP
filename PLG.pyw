"""PLG desktop entry point (no console window on Windows)."""

from __future__ import annotations

import os

from plg_paths import app_dir

os.chdir(app_dir())

from plg_webview import main

if __name__ == "__main__":
    main()
