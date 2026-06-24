"""One-shot localhost receiver: accepts a POSTed PNG data-URL and writes it to
assets/logo_icon.png, then exits. Used to capture the browser's exact render of
the PLG mark (matching the in-app logo) without routing bytes through the agent.
"""

from __future__ import annotations

import base64
import http.server
import socketserver
import threading
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "assets" / "logo_icon.png"
PORT = 8799


class Handler(http.server.BaseHTTPRequestHandler):
    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n).decode("utf-8", "replace")
        b64 = body.split(",")[-1]
        OUT.write_bytes(base64.b64decode(b64))
        self.send_response(200)
        self._cors()
        self.end_headers()
        self.wfile.write(b"ok")
        print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, *_a) -> None:  # noqa: D401 - quiet
        pass


with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as srv:
    print(f"listening on 127.0.0.1:{PORT}")
    srv.serve_forever()
