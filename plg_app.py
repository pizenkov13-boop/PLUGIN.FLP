"""PLG PLUGIN.FLP — branded desktop launcher."""

from __future__ import annotations

import logging
import os
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from backend_core import PROJECT_DIR, ensure_samples_library, resolve_samples_dir, run_pipeline
from fl_setup import install_plugin_script
from pattern_utils import format_build_guide
from logo_loader import load_logo_photo
from plg_theme import (
    ACCENT,
    BG,
    BG_CARD,
    BG_ELEVATED,
    BORDER,
    LOG_BG,
    LOG_FG,
    TEXT,
    TEXT_MUTED,
    apply_theme,
    make_card,
    mono_font,
)

PROMPT_PLACEHOLDER = "opium trap 145 bpm dark melody heavy distorted 808"


class PlgApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PLG — PLUGIN.FLP")
        self.geometry("860x760")
        self.minsize(760, 680)
        self._logo_image: tk.PhotoImage | None = None
        self._busy = False
        self._status = tk.StringVar(value="Ready")
        self._meta = tk.StringVar(value="BPM —  |  Style —")

        apply_theme(self)
        self._build_ui()
        self._boot_message()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=0)
        root.pack(fill="both", expand=True)

        self._build_header(root)
        self._build_prompt_card(root)
        self._build_actions(root)
        self._build_log(root)
        self._build_status(root)

    def _build_header(self, parent: ttk.Frame) -> None:
        header = tk.Frame(parent, bg=BG)
        header.pack(fill="x", padx=24, pady=(22, 8))

        self._logo_image = load_logo_photo(self)
        if self._logo_image is not None:
            logo_label = tk.Label(header, image=self._logo_image, bg=BG, borderwidth=0)
            logo_label.pack(side="left", padx=(0, 16))

        text_wrap = tk.Frame(header, bg=BG)
        text_wrap.pack(side="left", fill="x", expand=True)

        tk.Label(
            text_wrap,
            text="PLG",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 30, "bold"),
        ).pack(anchor="w")

        tk.Label(
            text_wrap,
            text="PLUGIN.FLP  ·  prompt → beat → your sound",
            bg=BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(2, 0))

        tk.Label(
            text_wrap,
            text="Opium to Dua Lipa to grind. Your voice. Your FL project.",
            bg=BG,
            fg="#666666",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(6, 0))

    def _build_prompt_card(self, parent: ttk.Frame) -> None:
        outer = tk.Frame(parent, bg=BG)
        outer.pack(fill="x", padx=24, pady=(8, 12))

        card = make_card(outer)
        card.pack(fill="x")

        inner = tk.Frame(card, bg=BG_CARD)
        inner.pack(fill="x", padx=18, pady=16)

        tk.Label(
            inner,
            text="DESCRIBE YOUR BEAT",
            bg=BG_CARD,
            fg=TEXT_MUTED,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")

        self.prompt_box = tk.Text(
            inner,
            height=4,
            bg="#0d0d0d",
            fg=TEXT,
            insertbackground=ACCENT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor="#555555",
            font=("Segoe UI", 12),
            wrap="word",
            padx=12,
            pady=10,
        )
        self.prompt_box.pack(fill="x", pady=(10, 14))
        self.prompt_box.insert("1.0", PROMPT_PLACEHOLDER)

        self.create_btn = ttk.Button(
            inner,
            text="CREATE BEAT",
            style="Primary.TButton",
            command=self.on_create,
        )
        self.create_btn.pack(anchor="w")

    def _build_actions(self, parent: ttk.Frame) -> None:
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill="x", padx=24, pady=(0, 8))

        tk.Label(
            wrap,
            text="OUTPUT",
            bg=BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        grid = tk.Frame(wrap, bg=BG)
        grid.pack(fill="x")

        actions = (
            ("Preview WAV", self.render_preview),
            ("Build Guide", self.open_guide),
            ("Sample Library", self.open_samples),
            ("MIDI Files", self.open_midi),
            ("Install FL Script", self.install_fl_script),
        )

        for index, (label, command) in enumerate(actions):
            row, col = divmod(index, 3)
            btn = ttk.Button(grid, text=label, style="Ghost.TButton", command=command)
            btn.grid(row=row, column=col, padx=(0, 10), pady=(0, 10), sticky="ew")
            grid.grid_columnconfigure(col, weight=1)

    def _build_log(self, parent: ttk.Frame) -> None:
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill="both", expand=True, padx=24, pady=(4, 8))

        tk.Label(
            wrap,
            text="SESSION LOG",
            bg=BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        self.log_box = scrolledtext.ScrolledText(
            wrap,
            height=14,
            bg=LOG_BG,
            fg=LOG_FG,
            insertbackground=LOG_FG,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            font=mono_font(),
            wrap="word",
            padx=12,
            pady=10,
        )
        self.log_box.pack(fill="both", expand=True)
        self.log_box.configure(state="disabled")

    def _build_status(self, parent: ttk.Frame) -> None:
        bar = tk.Frame(parent, bg=BG_ELEVATED, height=36)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        tk.Label(
            bar,
            textvariable=self._status,
            bg=BG_ELEVATED,
            fg=TEXT,
            font=("Segoe UI", 9),
            padx=16,
        ).pack(side="left", pady=8)

        tk.Label(
            bar,
            textvariable=self._meta,
            bg=BG_ELEVATED,
            fg=TEXT_MUTED,
            font=("Segoe UI", 9),
            padx=16,
        ).pack(side="right", pady=8)

    def _boot_message(self) -> None:
        samples_dir = resolve_samples_dir(None)
        ensure_samples_library(samples_dir)
        self.log(f"Sample library: {samples_dir}")
        self.log("Drop kits into 808/ hats/ textures/ then CREATE BEAT")

    def log(self, message: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def set_status(self, text: str) -> None:
        self._status.set(text)

    def set_meta(self, bpm: str | float = "—", style: str = "—") -> None:
        self._meta.set(f"BPM {bpm}  |  {style}")

    def on_create(self) -> None:
        if self._busy:
            return

        prompt = self.prompt_box.get("1.0", "end").strip()
        if not prompt:
            messagebox.showwarning("PLG", "Enter a prompt first.")
            return

        self._busy = True
        self.create_btn.configure(state="disabled", text="CREATING...")
        self.set_status("Generating with Gemini...")
        self.log("")
        self.log(f"> {prompt}")

        def worker() -> None:
            try:
                logging.basicConfig(level=logging.INFO)
                pattern = run_pipeline(prompt)
                guide = format_build_guide(pattern)
                self.after(0, lambda: self._on_success(pattern, guide))
            except Exception as exc:
                self.after(0, lambda: self._on_error(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_success(self, pattern: dict, guide: str) -> None:
        self._busy = False
        self.create_btn.configure(state="normal", text="CREATE BEAT")
        bpm = pattern.get("bpm", "—")
        style = pattern.get("style", "unknown")
        self.set_status("Beat ready")
        self.set_meta(bpm, style)
        self.log(f"OK | BPM {bpm} | {style}")
        self.log("output_pattern.json | output_midi/ | build_guide.txt | output_preview.wav")
        self.log("")
        self.log(guide)
        messagebox.showinfo(
            "PLG",
            "Beat created.\n\nListen: Preview WAV\nLater: FL Studio -> Scripts -> PLG PLUGIN.FLP",
        )

    def _on_error(self, exc: Exception) -> None:
        self._busy = False
        self.create_btn.configure(state="normal", text="CREATE BEAT")
        self.set_status("Error")
        self.log(f"ERROR: {exc}")
        messagebox.showerror("PLG", str(exc))

    def render_preview(self) -> None:
        try:
            from preview_wav import render_from_json

            self.set_status("Rendering preview...")
            path = render_from_json()
            self.log(f"Preview rendered: {path}")
            self.set_status("Preview ready")
            os.startfile(path)  # type: ignore[attr-defined]
        except Exception as exc:
            self.set_status("Preview failed")
            messagebox.showerror("PLG", f"Preview failed:\n{exc}")

    def open_guide(self) -> None:
        path = PROJECT_DIR / "build_guide.txt"
        if not path.exists():
            messagebox.showinfo("PLG", "Create a beat first.")
            return
        os.startfile(path)  # type: ignore[attr-defined]

    def open_samples(self) -> None:
        path = resolve_samples_dir(None)
        ensure_samples_library(path)
        os.startfile(path)  # type: ignore[attr-defined]

    def open_midi(self) -> None:
        path = PROJECT_DIR / "output_midi"
        path.mkdir(exist_ok=True)
        os.startfile(path)  # type: ignore[attr-defined]

    def install_fl_script(self) -> None:
        try:
            dest = install_plugin_script()
            self.log(f"FL script installed: {dest}")
            messagebox.showinfo("PLG", f"Installed:\n{dest}\n\nRestart FL -> Piano roll -> Scripts")
        except OSError as exc:
            messagebox.showerror("PLG", str(exc))


def main() -> None:
    app = PlgApp()
    app.mainloop()


if __name__ == "__main__":
    main()
