"""PLG pywebview entry point — owns the OS window, exposes plg_api to JS.

This is a *thin* shell. It does two things and nothing else:
  1. opens a native window (WebView2 on Windows) sized like the old app;
  2. exposes an ``Api`` object whose methods are 1-line passthroughs to plg_api,
     reachable from the React side as ``window.pywebview.api.<name>(...)``.

No app logic lives here — that's all in plg_api, which stays importable and
testable without a window.

Modes
-----
dev  (``--dev`` or ``PLG_DEV=1``): load the Vite dev server (hot reload) at
     ``PLG_DEV_URL`` (default http://localhost:5173). pywebview still injects
     ``window.pywebview`` into that page, so the bridge works the same.
prod (default / frozen exe): serve the built ``web/dist`` over a tiny localhost
     static server and load that. We use http:// (not file://) on purpose —
     Chromium blocks ES-module loading over file://, and Vite's prod build is
     ES modules. The dist folder is located via plg_paths so it works both from
     the repo and from inside a PyInstaller bundle (_MEIPASS).

plg_app.py (tkinter) remains as a legacy fallback; PLG.pyw launches this pywebview UI.
"""

from __future__ import annotations

import argparse
import logging
import os
import threading
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import webview

import plg_api
from app_config import load_environment
from plg_paths import resource_path
from starter_kit import ensure_starter_kit

logger = logging.getLogger("plg.webview")

WINDOW_TITLE = "PLG — PLUGIN.FLP"
WIN_W, WIN_H = 1100, 720
WIN_MIN_W, WIN_MIN_H = 900, 600
DEV_URL = os.environ.get("PLG_DEV_URL", "http://localhost:5173")
BG_COLOR = "#0A0A0A"


class Api:
    """Every public method here becomes ``window.pywebview.api.<name>`` in JS.

    Keep them as pure passthroughs. Args and return values are JSON only
    (plg_api already returns plain dicts), so pywebview marshals them as-is.
    """

    # --- status / settings / quota / library (cheap reads) -----------------
    def get_status(self) -> dict:
        return plg_api.get_status()

    def get_settings(self) -> dict:
        return plg_api.get_settings()

    def save_settings(self, updates: dict | None = None) -> dict:
        return plg_api.save_settings(updates or {})

    def get_quota(self) -> dict:
        return plg_api.get_quota()

    def scan_library(self) -> dict:
        return plg_api.scan_library()

    def preview_kit(self, prompt: str) -> dict:
        return plg_api.preview_kit(prompt)

    # --- long actions: start a job, then poll get_job(job_id) --------------
    def start_beat(self, prompt: str) -> dict:
        return plg_api.start_beat(prompt)

    def start_regenerate(self, prompt: str | None = None) -> dict:
        return plg_api.start_regenerate(prompt)

    def start_open_in_fl(self) -> dict:
        return plg_api.start_open_in_fl()

    def start_stem_split(self, source: str) -> dict:
        return plg_api.start_stem_split(source)

    def get_job(self, job_id: str) -> dict:
        return plg_api.get_job(job_id)

    def clear_finished_jobs(self) -> dict:
        return plg_api.clear_finished_jobs()

    # --- small/fast sync actions (no job needed) ---------------------------
    def open_in_fl(self) -> dict:
        return plg_api.open_in_fl()

    def install_fl_scripts(self) -> dict:
        return plg_api.install_fl_scripts()

    def reveal_path(self, path: str) -> dict:
        return plg_api.reveal_path(path)


class _QuietHandler(SimpleHTTPRequestHandler):
    """Static handler that doesn't spam the log with every asset request."""

    def log_message(self, *_args) -> None:  # noqa: D401 - silence access log
        pass


def _serve_dist(dist_dir: Path) -> str:
    """Serve ``dist_dir`` on a background localhost server; return its URL."""
    handler = partial(_QuietHandler, directory=str(dist_dir))
    httpd = HTTPServer(("127.0.0.1", 0), handler)  # port 0 → OS picks a free port
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True, name="plg-static").start()
    logger.info("Serving built UI from %s on 127.0.0.1:%s", dist_dir, port)
    return f"http://127.0.0.1:{port}/index.html"


def _resolve_url(dev: bool) -> str:
    if dev:
        logger.info("DEV mode → %s", DEV_URL)
        return DEV_URL
    dist_dir = resource_path("web", "dist")
    index = dist_dir / "index.html"
    if not index.is_file():
        raise FileNotFoundError(
            f"Built UI not found at {index}.\n"
            "Build it first:  cd web && npm install && npm run build\n"
            "Or run dev mode:  python plg_webview.py --dev"
        )
    return _serve_dist(dist_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="PLG pywebview UI")
    parser.add_argument("--dev", action="store_true", help="Load the Vite dev server (hot reload)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | PLG webview | %(levelname)s | %(message)s")
    load_environment()
    ensure_starter_kit()

    dev = args.dev or os.environ.get("PLG_DEV") == "1"
    url = _resolve_url(dev)

    webview.create_window(
        WINDOW_TITLE,
        url=url,
        js_api=Api(),
        width=WIN_W,
        height=WIN_H,
        min_size=(WIN_MIN_W, WIN_MIN_H),
        background_color=BG_COLOR,
    )
    # debug=True opens devtools and is handy while building the UI.
    webview.start(debug=dev)


if __name__ == "__main__":
    main()
