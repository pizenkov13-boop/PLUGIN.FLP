"""PLG brand tokens and tkinter widget helpers."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# Opium / vampire studio palette
BG = "#050505"
BG_ELEVATED = "#0f0f0f"
BG_CARD = "#141414"
BORDER = "#262626"
TEXT = "#f5f5f5"
TEXT_MUTED = "#8a8a8a"
ACCENT = "#ffffff"
ACCENT_DIM = "#bdbdbd"
DANGER = "#ff3b3b"
SUCCESS = "#35d07f"
LOG_BG = "#0a0a0a"
LOG_FG = "#c8c8c8"

FONT_DISPLAY = ("Segoe UI", 22, "bold")
FONT_TITLE = ("Segoe UI", 11, "bold")
FONT_BODY = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_MONO = ("Cascadia Mono", 10)
FONT_MONO_FALLBACK = ("Consolas", 10)


def mono_font() -> tuple[str, int]:
    return FONT_MONO_FALLBACK


def apply_theme(root: tk.Tk) -> ttk.Style:
    root.configure(bg=BG)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=BG, foreground=TEXT, font=FONT_BODY)
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=BG_CARD)
    style.configure("Elevated.TFrame", background=BG_ELEVATED)
    style.configure(
        "Muted.TLabel",
        background=BG,
        foreground=TEXT_MUTED,
        font=FONT_SMALL,
    )
    style.configure(
        "Title.TLabel",
        background=BG,
        foreground=TEXT,
        font=FONT_DISPLAY,
    )
    style.configure(
        "Primary.TButton",
        background=ACCENT,
        foreground="#000000",
        font=FONT_TITLE,
        padding=(18, 10),
        borderwidth=0,
    )
    style.map(
        "Primary.TButton",
        background=[("active", ACCENT_DIM), ("disabled", "#444444")],
        foreground=[("disabled", "#888888")],
    )
    style.configure(
        "Ghost.TButton",
        background=BG_CARD,
        foreground=TEXT,
        font=FONT_BODY,
        padding=(12, 8),
        borderwidth=1,
        relief="solid",
    )
    style.map(
        "Ghost.TButton",
        background=[("active", BORDER)],
    )
    return style


def make_card(parent: tk.Misc, **kwargs) -> tk.Frame:
    frame = tk.Frame(
        parent,
        bg=BG_CARD,
        highlightbackground=BORDER,
        highlightthickness=1,
        **kwargs,
    )
    return frame
