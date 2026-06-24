"""Build assets/logo.ico (multi-size Windows app icon) from the PLG mark.

Source of truth is assets/logo_icon.png — the browser's exact render of the
square PLG mark (web/public/favicon.svg → same paths as assets/logo.svg, drawn
with the SVG-default nonzero fill so the G's sharp spear-tail matches the logo
and the in-app <PlgLogo>). Regenerate that PNG with scripts/_recv_icon.py +
the dev server if the logo changes; this script just packs it into the .ico.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC_PNG = ROOT / "assets" / "logo_icon.png"
OUT_ICO = ROOT / "assets" / "logo.ico"

SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def main() -> None:
    if not SRC_PNG.is_file():
        raise SystemExit(
            f"{SRC_PNG} missing. Render it from the logo first:\n"
            "  1) python scripts/_recv_icon.py   (one-shot receiver)\n"
            "  2) load the dev server and POST the canvas render (see _recv_icon.py)."
        )
    img = Image.open(SRC_PNG).convert("RGBA")
    if img.size != (256, 256):
        img = img.resize((256, 256), Image.LANCZOS)
    img.save(OUT_ICO, format="ICO", sizes=SIZES)
    print(f"Wrote {OUT_ICO.name} from {SRC_PNG.name} ({OUT_ICO.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
