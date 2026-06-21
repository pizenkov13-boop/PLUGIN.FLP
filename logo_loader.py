"""Load PLG logo for tkinter (JPEG/PNG/SVG-with-embedded-image)."""

from __future__ import annotations

import base64
import re
import tkinter as tk
from io import BytesIO
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
LOGO_CANDIDATES = (
    PROJECT_DIR / "assets" / "logo.jpg",
    PROJECT_DIR / "assets" / "logo.png",
    PROJECT_DIR / "assets" / "logo.svg",
    PROJECT_DIR / "plug.jpg",
)


def _load_image_file(path: Path):
    from PIL import Image

    if path.suffix.lower() == ".svg":
        text = path.read_text(encoding="utf-8")
        match = re.search(r"data:image/(?:jpeg|jpg|png);base64,([^\"']+)", text, re.I)
        if not match:
            return None
        raw = base64.b64decode(match.group(1))
        return Image.open(BytesIO(raw))

    return Image.open(path)


def load_logo_photo(master: tk.Misc, max_height: int = 72) -> tk.PhotoImage | None:
    path = next((candidate for candidate in LOGO_CANDIDATES if candidate.is_file()), None)
    if path is None:
        return None

    try:
        from PIL import Image, ImageTk

        image = _load_image_file(path)
        if image is None:
            return None

        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA")

        width, height = image.size
        if height > max_height:
            scale = max_height / height
            image = image.resize((int(width * scale), max_height), Image.Resampling.LANCZOS)

        return ImageTk.PhotoImage(image, master=master)
    except ImportError:
        return None
    except OSError:
        return None
