"""PLG brand tokens and tkinter widget helpers."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

# Opium / chrome studio
BG = "#030303"
BG_ELEVATED = "#0c0c0c"
BG_CARD = "#111111"
BG_INPUT = "#080808"
BORDER = "#2a2a2a"
BORDER_FOCUS = "#4a4a4a"
TEXT = "#f2f2f2"
TEXT_MUTED = "#7a7a7a"
TEXT_DIM = "#505050"
ACCENT = "#ffffff"
ACCENT_CHROME = "#d4d4d4"
ACCENT_DIM = "#a8a8a8"
DANGER = "#ff3b3b"
SUCCESS = "#3ddc84"
WARN = "#e8c547"
LOG_BG = "#060606"
LOG_FG = "#b8b8b8"

FONT_DISPLAY = ("Segoe UI", 28, "bold")
FONT_TITLE = ("Segoe UI", 11, "bold")
FONT_BODY = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_CAPTION = ("Segoe UI", 8, "bold")
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
        "Primary.TButton",
        background=ACCENT,
        foreground="#000000",
        font=("Segoe UI", 11, "bold"),
        padding=(22, 11),
        borderwidth=0,
    )
    style.map(
        "Primary.TButton",
        background=[("active", ACCENT_CHROME), ("disabled", "#333333")],
        foreground=[("disabled", "#666666")],
    )

    style.configure(
        "Accent.TButton",
        background=BG_CARD,
        foreground=ACCENT,
        font=("Segoe UI", 10, "bold"),
        padding=(16, 10),
        borderwidth=1,
        relief="solid",
    )
    style.map(
        "Accent.TButton",
        background=[("active", BORDER)],
        foreground=[("active", ACCENT_CHROME)],
    )

    style.configure(
        "Ghost.TButton",
        background=BG_ELEVATED,
        foreground=TEXT_MUTED,
        font=FONT_BODY,
        padding=(12, 8),
        borderwidth=1,
        relief="solid",
    )
    style.map(
        "Ghost.TButton",
        background=[("active", BG_CARD)],
        foreground=[("active", TEXT)],
    )

    style.configure(
        "TCombobox",
        fieldbackground=BG_INPUT,
        background=BG_CARD,
        foreground=TEXT,
        bordercolor=BORDER,
        arrowcolor=TEXT_MUTED,
    )
    style.configure(
        "TProgressbar",
        background=ACCENT,
        troughcolor=BG_INPUT,
        bordercolor=BORDER,
        lightcolor=ACCENT,
        darkcolor=ACCENT,
    )
    return style


def make_card(parent: tk.Misc, **kwargs) -> tk.Frame:
    return tk.Frame(
        parent,
        bg=BG_CARD,
        highlightbackground=BORDER,
        highlightthickness=1,
        **kwargs,
    )


def accent_bar(parent: tk.Misc) -> tk.Frame:
    bar = tk.Frame(parent, bg=ACCENT, height=2)
    bar.pack(fill="x")
    return bar


def section_label(parent: tk.Misc, text: str, *, bg: str = BG) -> tk.Label:
    return tk.Label(
        parent,
        text=text,
        bg=bg,
        fg=TEXT_DIM,
        font=FONT_CAPTION,
    )


def workflow_step(parent: tk.Misc, number: str, label: str, *, active: bool = False) -> tk.Frame:
    bg = BG_CARD if active else BG_ELEVATED
    wrap = tk.Frame(parent, bg=bg, padx=10, pady=6)
    tk.Label(
        wrap,
        text=number,
        bg=bg,
        fg=ACCENT if active else TEXT_DIM,
        font=("Segoe UI", 9, "bold"),
    ).pack(side="left")
    tk.Label(
        wrap,
        text=label,
        bg=bg,
        fg=TEXT if active else TEXT_MUTED,
        font=("Segoe UI", 9),
    ).pack(side="left", padx=(6, 0))
    return wrap


def bind_text_shortcuts(
    widget: tk.Text,
    *,
    before_edit: Callable[[], None] | None = None,
) -> None:
    def copy(_event: tk.Event | None = None) -> str:
        try:
            if widget.tag_ranges("sel"):
                widget.clipboard_clear()
                widget.clipboard_append(widget.get("sel.first", "sel.last"))
        except tk.TclError:
            pass
        return "break"

    def cut(_event: tk.Event | None = None) -> str:
        if before_edit:
            before_edit()
        copy()
        try:
            if widget.tag_ranges("sel"):
                widget.delete("sel.first", "sel.last")
        except tk.TclError:
            pass
        return "break"

    def paste(_event: tk.Event | None = None) -> str:
        if before_edit:
            before_edit()
        try:
            text = widget.clipboard_get()
        except tk.TclError:
            return "break"
        try:
            if widget.tag_ranges("sel"):
                widget.delete("sel.first", "sel.last")
        except tk.TclError:
            pass
        widget.insert("insert", text)
        return "break"

    def select_all(_event: tk.Event | None = None) -> str:
        widget.tag_add("sel", "1.0", "end-1c")
        return "break"

    for sequence in ("<Control-c>", "<Control-C>"):
        widget.bind(sequence, copy)
    for sequence in ("<Control-x>", "<Control-X>"):
        widget.bind(sequence, cut)
    for sequence in ("<Control-v>", "<Control-V>", "<Shift-Insert>"):
        widget.bind(sequence, paste)
    for sequence in ("<Control-a>", "<Control-A>"):
        widget.bind(sequence, select_all)

    menu = tk.Menu(widget, tearoff=0, bg=BG_CARD, fg=TEXT, activebackground=BORDER, activeforeground=TEXT)

    def show_menu(event: tk.Event) -> None:
        menu.tk_popup(event.x_root, event.y_root)

    menu.add_command(label="Cut", command=lambda: cut())
    menu.add_command(label="Copy", command=lambda: copy())
    menu.add_command(label="Paste", command=lambda: paste())
    menu.add_command(label="Select All", command=lambda: select_all())
    widget.bind("<Button-3>", show_menu)


def bind_entry_shortcuts(widget: tk.Entry | ttk.Entry) -> None:
    def paste(_event: tk.Event | None = None) -> str:
        try:
            text = widget.clipboard_get()
        except tk.TclError:
            return "break"
        try:
            widget.delete("sel.first", "sel.last")
        except tk.TclError:
            pass
        widget.insert("insert", text)
        return "break"

    def copy(_event: tk.Event | None = None) -> str:
        try:
            widget.clipboard_clear()
            widget.clipboard_append(widget.selection_get())
        except tk.TclError:
            pass
        return "break"

    def cut(_event: tk.Event | None = None) -> str:
        copy()
        try:
            widget.delete("sel.first", "sel.last")
        except tk.TclError:
            pass
        return "break"

    def select_all(_event: tk.Event | None = None) -> str:
        widget.selection_range(0, "end")
        widget.icursor("end")
        return "break"

    for sequence in ("<Control-v>", "<Control-V>", "<Shift-Insert>"):
        widget.bind(sequence, paste)
    for sequence in ("<Control-c>", "<Control-C>"):
        widget.bind(sequence, copy)
    for sequence in ("<Control-x>", "<Control-X>"):
        widget.bind(sequence, cut)
    for sequence in ("<Control-a>", "<Control-A>"):
        widget.bind(sequence, select_all)
