"""Optional CC0 upgrade — bundled starter is already inside PLG."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from plg_paths import app_dir
from starter_kit import CC0_SOURCES, ensure_starter_kit, install_from_incoming_zips, starter_kit_info


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    info = starter_kit_info()
    logging.info("Current starter: %s (%s)", info["source"], info["dir"])

    upgraded = install_from_incoming_zips()
    if upgraded:
        logging.info("CC0 starter upgrade installed.")
        for track, path in upgraded.items():
            logging.info("  %s -> %s", track, Path(path).name)
        return 0

    incoming = Path(info["incoming_dir"])
    if list(incoming.glob("*.zip")):
        logging.error("Zips found but install failed — need Trap Vault + Kick Drums + Grand Piano.")
        return 1

    logging.info("")
    logging.info("Bundled starter is already active — nothing required.")
    logging.info("Optional CC0 upgrade (better trap sound):")
    for name, url in CC0_SOURCES.items():
        logging.info("  %s", url)
    logging.info("")
    logging.info("Download 3 zips (Purchase -> GBP 0), then drop into:")
    logging.info("  %s", incoming)
    logging.info("Run this script again.")

    if sys.platform == "win32":
        bat = app_dir() / "install_starter_sounds.bat"
        if bat.is_file():
            subprocess.Popen(["cmd", "/c", "start", "", str(bat)], cwd=str(app_dir()))
    ensure_starter_kit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
