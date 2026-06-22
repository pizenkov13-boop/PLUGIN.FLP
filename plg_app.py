"""PLG PLUGIN.FLP — desktop application."""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from pathlib import Path

from app_config import (
    get_auto_open_fl,
    get_samples_dir,
    has_api_key,
    load_environment,
    settings_snapshot,
    write_env_file,
)
from backend_core import PROJECT_DIR, ensure_samples_library, resolve_samples_dir, run_pipeline
from beat_quota import BeatQuotaExceeded, consume_beat, ensure_can_consume_beat, format_quota_label, get_quota_snapshot
from fl_launch import open_beat_in_fl
from fl_setup import install_all, is_fl_bridge_ready
from library_catalog import save_catalog, scan_library
from llm_client import format_llm_error, provider_label
from logo_loader import load_logo_photo
from stem_split import StemSplitError, split_stems, stems_available
from starter_kit import ensure_starter_kit
from theme_install import install_themes
from plg_theme import (
    ACCENT,
    BG,
    BG_CARD,
    BG_ELEVATED,
    BG_INPUT,
    BORDER,
    BORDER_FOCUS,
    DANGER,
    SUCCESS,
    TEXT,
    TEXT_DIM,
    TEXT_MUTED,
    WARN,
    accent_bar,
    apply_theme,
    bind_entry_shortcuts,
    bind_text_shortcuts,
    make_card,
    section_label,
    workflow_step,
)

PROMPT_PLACEHOLDER = "opium trap 145 bpm dark melody heavy distorted 808"
PATTERN_JSON = PROJECT_DIR / "output_pattern.json"
SESSION_LOG = PROJECT_DIR / "plg_session.log"


def setup_gui_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | PLG GUI | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.FileHandler(SESSION_LOG, encoding="utf-8"),
        ],
        force=True,
    )


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent: PlgApp, *, first_run: bool = False) -> None:
        super().__init__(parent)
        self.parent = parent
        self.first_run = first_run
        self.title("PLG Setup" if first_run else "PLG Settings")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        snapshot = settings_snapshot()
        self._provider = tk.StringVar(value=snapshot["provider"])
        self._gemini_key = tk.StringVar(value=snapshot["gemini_key"])
        self._anthropic_key = tk.StringVar(value=snapshot["anthropic_key"])
        self._samples_dir = tk.StringVar(value=snapshot["samples_dir"])
        self._auto_open_fl = tk.BooleanVar(value=snapshot["auto_open_fl"] == "true")

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if first_run:
            self.wait_window()
        else:
            self.geometry("520x420")

    def _build(self) -> None:
        wrap = tk.Frame(self, bg=BG, padx=24, pady=20)
        wrap.pack(fill="both", expand=True)

        title = "Welcome to PLG" if self.first_run else "Settings"
        tk.Label(wrap, text=title, bg=BG, fg=TEXT, font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(
            wrap,
            text="API keys stay on your PC in .env — not in the cloud.",
            bg=BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(4, 16))

        self._field(wrap, "AI provider", ttk.Combobox(
            wrap,
            textvariable=self._provider,
            values=("gemini", "anthropic"),
            state="readonly",
            width=42,
        ))
        gemini_entry = ttk.Entry(wrap, textvariable=self._gemini_key, show="*", width=44)
        self._field(wrap, "Gemini API key", gemini_entry)
        bind_entry_shortcuts(gemini_entry)

        anthropic_entry = ttk.Entry(wrap, textvariable=self._anthropic_key, show="*", width=44)
        self._field(wrap, "Anthropic API key (release)", anthropic_entry)
        bind_entry_shortcuts(anthropic_entry)

        samples_row = tk.Frame(wrap, bg=BG)
        samples_row.pack(fill="x", pady=(0, 10))
        tk.Label(samples_row, text="Sample library folder", bg=BG, fg=TEXT_MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        entry_row = tk.Frame(samples_row, bg=BG)
        entry_row.pack(fill="x", pady=(4, 0))
        samples_entry = ttk.Entry(entry_row, textvariable=self._samples_dir, width=34)
        samples_entry.pack(side="left", fill="x", expand=True)
        bind_entry_shortcuts(samples_entry)
        ttk.Button(entry_row, text="Browse", command=self._browse_samples).pack(side="left", padx=(8, 0))

        auto_row = tk.Frame(wrap, bg=BG)
        auto_row.pack(fill="x", pady=(4, 0))
        ttk.Checkbutton(
            auto_row,
            text="Open FL Studio automatically after CREATE BEAT",
            variable=self._auto_open_fl,
        ).pack(anchor="w")

        btn_row = tk.Frame(wrap, bg=BG)
        btn_row.pack(fill="x", pady=(16, 0))
        ttk.Button(btn_row, text="Save", style="Primary.TButton", command=self._save).pack(side="left")
        if not self.first_run:
            ttk.Button(btn_row, text="Cancel", style="Ghost.TButton", command=self.destroy).pack(side="left", padx=(8, 0))

    def _field(self, parent: tk.Frame, label: str, widget: tk.Widget) -> None:
        tk.Label(parent, text=label, bg=BG, fg=TEXT_MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        widget.pack(anchor="w", pady=(4, 10))

    def _browse_samples(self) -> None:
        path = filedialog.askdirectory(initialdir=self._samples_dir.get() or str(PROJECT_DIR))
        if path:
            self._samples_dir.set(path)

    def _save(self) -> None:
        provider = self._provider.get().strip().lower() or "gemini"
        gemini_key = self._gemini_key.get().strip()
        anthropic_key = self._anthropic_key.get().strip()

        if provider in ("anthropic", "claude") and not anthropic_key:
            messagebox.showwarning("PLG", "Add Anthropic API key or switch provider to gemini.", parent=self)
            return
        if provider not in ("anthropic", "claude") and not gemini_key:
            messagebox.showwarning("PLG", "Add Gemini API key to continue.", parent=self)
            return

        write_env_file(
            {
                "PLG_LLM_PROVIDER": provider,
                "GEMINI_API_KEY": gemini_key,
                "ANTHROPIC_API_KEY": anthropic_key,
                "PLG_SAMPLES_DIR": self._samples_dir.get().strip(),
                "PLG_AUTO_OPEN_FL": "true" if self._auto_open_fl.get() else "false",
            }
        )
        self.parent._refresh_after_settings()
        if self.first_run:
            self.grab_release()
            self.destroy()
        else:
            messagebox.showinfo("PLG", "Settings saved.", parent=self)
            self.destroy()

    def _on_close(self) -> None:
        if self.first_run and not has_api_key():
            if messagebox.askyesno(
                "PLG",
                "API key is required to generate beats.\nQuit PLG?",
                parent=self,
            ):
                self.parent.destroy()
            return
        self.destroy()


class PlgApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        load_environment()
        setup_gui_logging()
        ensure_starter_kit()
        self.title("PLG — PLUGIN.FLP")
        self.geometry("720x420")
        self.minsize(640, 380)
        self._logo_image: tk.PhotoImage | None = None
        self._busy = False
        self._gen_started_at: float | None = None
        self._gen_tick_id: str | None = None
        self._ui_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._beat_ready = False
        self._last_prompt = ""
        self._placeholder_active = True
        self._status = tk.StringVar(value="Ready")
        self._meta = tk.StringVar(value="BPM —  |  Style —")
        self._quota = tk.StringVar(value="")
        self._provider_badge = tk.StringVar(value=provider_label())
        self._status_tone = "idle"
        self._empty_lib_warned = False

        apply_theme(self)
        self._build_menu()
        self._build_ui()
        self._boot_message()
        self.after(100, self._process_ui_queue)

    def _process_ui_queue(self) -> None:
        try:
            while True:
                kind, payload = self._ui_queue.get_nowait()
                if kind == "success":
                    self._on_success(payload)  # type: ignore[arg-type]
                elif kind == "error":
                    self._on_error(payload)  # type: ignore[arg-type]
                elif kind == "fl_done":
                    self._on_fl_opened(payload)  # type: ignore[arg-type]
                elif kind == "fl_error":
                    self._stop_busy()
                    exc = payload
                    if isinstance(exc, FileNotFoundError):
                        self.set_status("Create a beat first", tone="error")
                    else:
                        self.set_status("FL error", tone="error")
                    messagebox.showwarning("PLG", str(exc))
                elif kind == "stem_done":
                    self._on_stems_done(payload)  # type: ignore[arg-type]
                elif kind == "stem_error":
                    self._on_stems_error(payload)  # type: ignore[arg-type]
                elif kind == "stem_progress":
                    frac, msg = payload  # type: ignore[misc]
                    pct = int(float(frac) * 100)
                    self.set_status(f"Stems · {pct}% · {msg}", tone="busy")
        except queue.Empty:
            pass
        self.after(100, self._process_ui_queue)

    def _build_menu(self) -> None:
        menu = tk.Menu(self, tearoff=0, bg=BG_CARD, fg=TEXT, activebackground=BORDER, activeforeground=TEXT)
        self.config(menu=menu)

        file_menu = tk.Menu(menu, tearoff=0, bg=BG_CARD, fg=TEXT, activebackground=BORDER, activeforeground=TEXT)
        file_menu.add_command(label="Library", command=self.open_samples)
        file_menu.add_command(label="Import Kit Folder...", command=self.import_kit)
        file_menu.add_separator()
        file_menu.add_command(label="Build Guide", command=self.open_guide)
        file_menu.add_command(label="MIDI Folder", command=self.open_midi)
        file_menu.add_command(label="Output Folder", command=self.open_output_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menu.add_cascade(label="File", menu=file_menu)

        tools_menu = tk.Menu(menu, tearoff=0, bg=BG_CARD, fg=TEXT, activebackground=BORDER, activeforeground=TEXT)
        tools_menu.add_command(label="Settings...", command=self.open_settings)
        tools_menu.add_command(label="Upgrade Starter Sounds (optional)...", command=self.upgrade_starter_sounds)
        tools_menu.add_command(label="Install FL Scripts", command=self.install_fl_scripts)
        tools_menu.add_command(label="Install FL Themes", command=self.install_fl_themes)
        tools_menu.add_separator()
        tools_menu.add_command(label="Split Stems from File...", command=self.split_stems_from_file)
        menu.add_cascade(label="Tools", menu=tools_menu)

        help_menu = tk.Menu(menu, tearoff=0, bg=BG_CARD, fg=TEXT, activebackground=BORDER, activeforeground=TEXT)
        help_menu.add_command(label="Quick Start", command=self.show_quick_start)
        help_menu.add_command(label="Where is everything? (START_HERE)", command=self.open_start_here)
        help_menu.add_command(label="FL Bridge Guide", command=self.open_fl_bridge_doc)
        help_menu.add_command(label="Don FL Workflow", command=self.open_fl_workflows_doc)
        menu.add_cascade(label="Help", menu=help_menu)

    def _build_ui(self) -> None:
        accent_bar(self)
        root = ttk.Frame(self, padding=0)
        root.pack(fill="both", expand=True)

        self._build_header(root)
        self._build_empty_library_banner(root)
        self._build_setup_strip(root)
        self._build_workflow(root)
        self._build_prompt_card(root)
        self._build_status(root)

        self.bind("<Control-Return>", lambda _e: self.on_create())
        self.bind("<Control-KP_Enter>", lambda _e: self.on_create())

    def _build_workflow(self, parent: ttk.Frame) -> None:
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", padx=24, pady=(0, 10))
        for index, (num, label) in enumerate((("01", "PROMPT"), ("02", "GENERATE"), ("03", "FL STUDIO")), start=0):
            step = workflow_step(row, num, label, active=index == 0)
            step.pack(side="left", padx=(0, 8))

    def _build_header(self, parent: ttk.Frame) -> None:
        header = tk.Frame(parent, bg=BG)
        self._header_frame = header
        header.pack(fill="x", padx=24, pady=(20, 6))

        left = tk.Frame(header, bg=BG)
        left.pack(side="left", fill="x", expand=True)

        brand = tk.Frame(left, bg=BG)
        brand.pack(anchor="w")

        self._logo_image = load_logo_photo(self)
        if self._logo_image is not None:
            tk.Label(brand, image=self._logo_image, bg=BG, borderwidth=0).pack(side="left", padx=(0, 14))

        titles = tk.Frame(brand, bg=BG)
        titles.pack(side="left")
        tk.Label(titles, text="PLG", bg=BG, fg=TEXT, font=("Segoe UI", 26, "bold")).pack(anchor="w")
        tk.Label(
            titles,
            text="prompt → beat → your sound",
            bg=BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(0, 0))

        right = tk.Frame(header, bg=BG)
        right.pack(side="right", anchor="ne")

        badge = tk.Label(
            right,
            textvariable=self._provider_badge,
            bg=BG_ELEVATED,
            fg=TEXT_MUTED,
            font=("Segoe UI", 8),
            padx=10,
            pady=4,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        badge.pack(anchor="e", pady=(0, 8))
        ttk.Button(right, text="Settings", style="Ghost.TButton", command=self.open_settings).pack(anchor="e")

    def _build_empty_library_banner(self, parent: ttk.Frame) -> None:
        self._library_banner = tk.Frame(parent, bg="#1a1408", highlightbackground="#4a3a10", highlightthickness=1)
        inner = tk.Frame(self._library_banner, bg="#1a1408")
        inner.pack(fill="x", padx=24, pady=10)

        text = tk.Frame(inner, bg="#1a1408")
        text.pack(side="left", fill="x", expand=True)

        tk.Label(
            text,
            text="Starter sounds active — PLG loads built-in 808, hats, and melody into FL.",
            bg="#1a1408",
            fg=SUCCESS,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")
        tk.Label(
            text,
            text="Import your own kits anytime for a custom sound. Until then you can CREATE BEAT and OPEN IN FL right away.",
            bg="#1a1408",
            fg=TEXT_MUTED,
            font=("Segoe UI", 9),
            wraplength=520,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        actions = tk.Frame(inner, bg="#1a1408")
        actions.pack(side="right", padx=(12, 0))
        ttk.Button(actions, text="Import Kit", style="Ghost.TButton", command=self.import_kit).pack(side="left")
        ttk.Button(actions, text="Open Library", style="Ghost.TButton", command=self.open_samples).pack(
            side="left", padx=(8, 0)
        )

    def _refresh_library_banner(self) -> None:
        if self._library_has_audio():
            self._library_banner.pack_forget()
        else:
            self._library_banner.pack(fill="x", after=self._header_frame)

    def _strip_anchor(self) -> tk.Widget:
        if self._library_banner.winfo_ismapped():
            return self._library_banner
        return self._header_frame

    def _confirm_empty_library_create(self) -> bool:
        if self._library_has_audio():
            return True
        if self._empty_lib_warned:
            return True
        self._empty_lib_warned = True
        messagebox.showinfo(
            "PLG starter sounds",
            "Your kit folder is empty — that's OK.\n\n"
            "PLG loads built-in starter 808, hats, and melody into FL automatically.\n"
            "Add your own kits anytime via Import Kit or Open Library.",
        )
        return True

    def _build_setup_strip(self, parent: ttk.Frame) -> None:
        self._setup_strip = tk.Frame(parent, bg=BG_ELEVATED)
        self._setup_inner = tk.Frame(self._setup_strip, bg=BG_ELEVATED)
        self._setup_inner.pack(fill="x", padx=24, pady=(0, 8))

    def _refresh_setup_strip(self) -> None:
        self._refresh_library_banner()
        for child in self._setup_inner.winfo_children():
            child.destroy()

        hints: list[tuple[str, str]] = []
        if not has_api_key():
            hints.append(("Add API key for AI generation", self.open_settings))
        if not self._library_has_audio():
            hints.append(("Add your kits for custom sound (starter included)", self.import_kit))
        if not is_fl_bridge_ready(PROJECT_DIR):
            hints.append(("Install FL scripts", self.install_fl_scripts))

        if not hints:
            self._setup_strip.pack_forget()
            return

        self._setup_strip.pack(fill="x", after=self._strip_anchor())
        for index, (text, command) in enumerate(hints):
            if index:
                tk.Label(self._setup_inner, text="·", bg=BG_ELEVATED, fg=TEXT_DIM, font=("Segoe UI", 9)).pack(
                    side="left", padx=6
                )
            link = tk.Label(
                self._setup_inner,
                text=text,
                bg=BG_ELEVATED,
                fg=WARN,
                font=("Segoe UI", 9, "underline"),
                cursor="hand2",
            )
            link.pack(side="left")
            link.bind("<Button-1>", lambda _e, cmd=command: cmd())

    def _library_has_audio(self) -> bool:
        try:
            catalog = scan_library(get_samples_dir())
            return catalog.get("audio_total", 0) > 0
        except OSError:
            return False

    def _sync_beat_state(self) -> None:
        self._beat_ready = PATTERN_JSON.is_file()
        self._update_action_buttons()

    def _update_action_buttons(self) -> None:
        if self._busy:
            return
        if self._beat_ready:
            self.create_btn.configure(style="Accent.TButton")
            self.fl_btn.configure(state="normal", style="Primary.TButton")
            self.regen_btn.configure(state="normal")
        else:
            self.create_btn.configure(style="Primary.TButton")
            self.fl_btn.configure(state="disabled", style="Accent.TButton")
            self.regen_btn.configure(state="disabled")

    def _build_prompt_card(self, parent: ttk.Frame) -> None:
        outer = tk.Frame(parent, bg=BG)
        outer.pack(fill="x", padx=24, pady=(8, 12))

        card = make_card(outer)
        card.pack(fill="x")
        inner = tk.Frame(card, bg=BG_CARD)
        inner.pack(fill="x", padx=20, pady=18)

        section_label(inner, "DESCRIBE YOUR BEAT", bg=BG_CARD).pack(anchor="w")

        self.prompt_box = tk.Text(
            inner,
            height=5,
            bg=BG_INPUT,
            fg=TEXT_MUTED,
            insertbackground=ACCENT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=BORDER_FOCUS,
            font=("Segoe UI", 12),
            wrap="word",
            padx=14,
            pady=12,
        )
        self.prompt_box.pack(fill="x", pady=(10, 14))
        self.prompt_box.insert("1.0", PROMPT_PLACEHOLDER)
        self.prompt_box.bind("<FocusIn>", self._clear_placeholder)
        self.prompt_box.bind("<FocusOut>", self._restore_placeholder)
        bind_text_shortcuts(self.prompt_box, before_edit=self._clear_placeholder)

        action_row = tk.Frame(inner, bg=BG_CARD)
        action_row.pack(fill="x")

        self.create_btn = ttk.Button(
            action_row,
            text="CREATE BEAT",
            style="Primary.TButton",
            command=self.on_create,
        )
        self.create_btn.pack(side="left")

        self.fl_btn = ttk.Button(
            action_row,
            text="OPEN IN FL",
            style="Accent.TButton",
            command=self.open_in_fl_studio,
        )
        self.fl_btn.pack(side="left", padx=(10, 0))

        self.regen_btn = ttk.Button(
            action_row,
            text="↻",
            style="Ghost.TButton",
            width=3,
            command=self.on_regenerate,
        )
        self.regen_btn.pack(side="left", padx=(8, 0))
        self.regen_btn.configure(state="disabled")

        self.progress = ttk.Progressbar(action_row, mode="indeterminate", length=160)
        self.progress.pack(side="left", padx=(16, 0))
        self.progress.pack_forget()

    def _build_status(self, parent: ttk.Frame) -> None:
        bar = tk.Frame(parent, bg=BG_ELEVATED, height=40)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        left = tk.Frame(bar, bg=BG_ELEVATED)
        left.pack(side="left", padx=16, pady=10)

        self._status_dot = tk.Canvas(left, width=8, height=8, bg=BG_ELEVATED, highlightthickness=0, bd=0)
        self._status_dot.pack(side="left", padx=(0, 8))
        self._draw_status_dot("idle")

        tk.Label(left, textvariable=self._status, bg=BG_ELEVATED, fg=TEXT, font=("Segoe UI", 9)).pack(side="left")

        tk.Label(bar, textvariable=self._quota, bg=BG_ELEVATED, fg=TEXT_MUTED, font=("Segoe UI", 9)).pack(
            side="right", padx=(0, 4), pady=10
        )
        tk.Label(bar, textvariable=self._meta, bg=BG_ELEVATED, fg=TEXT_MUTED, font=("Segoe UI", 9), padx=16).pack(
            side="right", pady=10
        )

    def _draw_status_dot(self, tone: str) -> None:
        colors = {"idle": TEXT_DIM, "busy": WARN, "ok": SUCCESS, "error": DANGER}
        fill = colors.get(tone, TEXT_DIM)
        self._status_dot.delete("all")
        self._status_dot.create_oval(1, 1, 7, 7, fill=fill, outline=fill)
        self._status_tone = tone

    def _clear_placeholder(self, _event: tk.Event | None = None) -> None:
        if not self._placeholder_active:
            return
        self.prompt_box.delete("1.0", "end")
        self.prompt_box.configure(fg=TEXT)
        self._placeholder_active = False

    def _restore_placeholder(self, _event: tk.Event | None = None) -> None:
        if self.prompt_box.get("1.0", "end").strip():
            return
        self._placeholder_active = True
        self.prompt_box.insert("1.0", PROMPT_PLACEHOLDER)
        self.prompt_box.configure(fg=TEXT_MUTED)

    def _prompt_text(self) -> str:
        if self._placeholder_active:
            return ""
        return self.prompt_box.get("1.0", "end").strip()

    def _refresh_beat_quota(self) -> None:
        if not has_api_key():
            self._quota.set("")
            return
        self._quota.set(format_quota_label())

    def _boot_message(self) -> None:
        ensure_samples_library(get_samples_dir(), quiet=True)
        self._provider_badge.set(provider_label())
        self._sync_beat_state()
        self._refresh_setup_strip()
        self._refresh_beat_quota()
        if self._beat_ready:
            self._load_beat_meta()
            if self._library_has_audio():
                self.set_status("Beat ready — open in FL Studio", tone="ok")
            else:
                self.set_status("Beat ready — starter sounds load in FL", tone="ok")
        elif has_api_key():
            if self._library_has_audio():
                self.set_status("Ready — describe your beat", tone="idle")
            else:
                self.set_status("Ready — starter pack included, describe your beat", tone="idle")
        else:
            self.set_status("Add API key to generate beats", tone="idle")

    def _load_beat_meta(self) -> None:
        try:
            data = json.loads(PATTERN_JSON.read_text(encoding="utf-8"))
            bpm = data.get("bpm", "—")
            style = data.get("style", "—")
            self.set_meta(bpm, style, ready=True)
        except (OSError, json.JSONDecodeError, ValueError):
            self.set_meta()

    def _refresh_after_settings(self) -> None:
        ensure_samples_library(get_samples_dir(), quiet=True)
        self._provider_badge.set(provider_label())
        self._refresh_setup_strip()
        self._refresh_beat_quota()
        self.set_status("Settings saved", tone="idle")

    def set_status(self, text: str, *, tone: str | None = None) -> None:
        self._status.set(text)
        if tone:
            self._draw_status_dot(tone)

    def set_meta(self, bpm: str | float = "—", style: str = "—", *, ready: bool = False) -> None:
        suffix = " · ready for FL" if ready else ""
        self._meta.set(f"{bpm} BPM · {style}{suffix}")

    def open_settings(self) -> None:
        SettingsDialog(self, first_run=False)

    def show_quick_start(self) -> None:
        messagebox.showinfo(
            "PLG Quick Start",
            "1. Describe your beat → CREATE BEAT (Ctrl+Enter)\n"
            "2. OPEN IN FL — 3 channels + starter sounds + notes\n"
            "3. Play in FL Studio\n\n"
            "Starter sounds are BUNDLED — no download needed.\n\n"
            "Optional better trap sound:\n"
            "  Tools → Upgrade Starter Sounds (optional)\n"
            "  or install_starter_sounds.bat → zips to assets/starter/incoming/\n\n"
            "Sell / Gumroad .exe: run build_plg.bat → dist\\PLG.exe\n"
            "Full map: Help → Where is everything? (START_HERE)",
        )

    def open_start_here(self) -> None:
        path = PROJECT_DIR / "START_HERE.md"
        if path.is_file():
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            messagebox.showinfo("PLG", "START_HERE.md not found in the PLG folder.")

    def open_fl_workflows_doc(self) -> None:
        path = PROJECT_DIR / "FL_WORKFLOWS.md"
        if path.is_file():
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            messagebox.showinfo("PLG", "FL_WORKFLOWS.md not found.")

    def open_fl_bridge_doc(self) -> None:
        path = PROJECT_DIR / "FL_BRIDGE.md"
        if path.is_file():
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            messagebox.showinfo("PLG", "FL_BRIDGE.md not found in the project folder.")

    def install_fl_themes(self) -> None:
        try:
            result = install_themes()
            themes = result.get("themes") or []
            specs = result.get("specs") or []
            self.set_status("FL theme specs installed", tone="ok")
            messagebox.showinfo(
                "PLG Themes",
                f"Installed {len(specs)} color spec(s) to FL Themes/PLG/\n"
                f"Installed {len(themes)} .flstheme file(s).\n\n"
                "Open FL → theme editor → apply hex values from THEMES.md\n"
                "or the JSON files in your FL Themes/PLG folder.",
            )
        except OSError as exc:
            messagebox.showerror("PLG", str(exc))

    def split_stems_from_file(self) -> None:
        if self._busy:
            messagebox.showinfo("PLG", "Wait for the current task to finish.")
            return
        if not stems_available():
            if not messagebox.askyesno(
                "Stem splitter",
                "Demucs is not installed (optional, ~2 GB download).\n\n"
                "    pip install -U demucs\n\n"
                "Open stem splitter docs anyway?",
            ):
                return
            path = PROJECT_DIR / "stem_split.py"
            if path.is_file():
                os.startfile(path)  # type: ignore[attr-defined]
            return

        source = filedialog.askopenfilename(
            title="Select track to split (MP3 or WAV)",
            filetypes=[("Audio", "*.wav *.mp3 *.flac *.ogg"), ("All files", "*.*")],
        )
        if not source:
            return

        self._busy = True
        self.create_btn.configure(state="disabled")
        self.fl_btn.configure(state="disabled")
        self.regen_btn.configure(state="disabled")
        self.set_status("Splitting stems…", tone="busy")

        def worker() -> None:
            try:
                out_dir = PROJECT_DIR / "output_stems" / Path(source).stem
                result = split_stems(
                    Path(source),
                    out_dir,
                    progress_cb=lambda frac, msg: self._ui_queue.put(
                        ("stem_progress", (frac, msg))
                    ),
                )
                self._ui_queue.put(("stem_done", result))
            except (StemSplitError, OSError) as exc:
                self._ui_queue.put(("stem_error", exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_stems_done(self, result: dict) -> None:
        self._busy = False
        self._update_action_buttons()
        self.set_status("Stems ready", tone="ok")
        folder = next(iter(result.values())).parent
        messagebox.showinfo(
            "PLG Stems",
            f"Wrote {len(result)} stem(s):\n"
            + "\n".join(f"  {name}: {path.name}" for name, path in result.items())
            + f"\n\nFolder:\n{folder}",
        )
        os.startfile(folder)  # type: ignore[attr-defined]

    def _on_stems_error(self, exc: Exception) -> None:
        self._busy = False
        self._update_action_buttons()
        self.set_status("Stem split failed", tone="error")
        messagebox.showerror("PLG Stems", str(exc))

    def on_regenerate(self) -> None:
        if not self._last_prompt and not self._prompt_text():
            messagebox.showwarning("PLG", "Describe your beat first.")
            return
        snap = get_quota_snapshot()
        if not snap.get("skipped"):
            days = snap["days_until_reset"]
            day_word = "day" if days == 1 else "days"
            if not messagebox.askyesno(
                "Regenerate beat",
                "Regenerating uses 1 beat from your plan.\n\n"
                f"{snap['remaining']} of {snap['limit']} beats left · resets in {days} {day_word}.\n\n"
                "Continue?",
            ):
                return
        if self._last_prompt and not self._prompt_text():
            self.prompt_box.delete("1.0", "end")
            self.prompt_box.insert("1.0", self._last_prompt)
            self.prompt_box.configure(fg=TEXT)
            self._placeholder_active = False
        self.on_create()

    def on_create(self) -> None:
        if self._busy:
            return

        if not has_api_key():
            self.open_settings()
            return

        try:
            ensure_can_consume_beat()
        except BeatQuotaExceeded as exc:
            messagebox.showwarning("PLG", str(exc))
            self._refresh_beat_quota()
            return

        if not self._confirm_empty_library_create():
            return

        prompt = self._prompt_text()
        if not prompt:
            messagebox.showwarning("PLG", "Describe your beat first.")
            return

        self._last_prompt = prompt
        self._busy = True
        self._gen_started_at = time.time()
        self.create_btn.configure(state="disabled", text="CREATING...")
        self.fl_btn.configure(state="disabled")
        self.regen_btn.configure(state="disabled")
        self.progress.pack(side="left", padx=(16, 0))
        self.progress.start(12)
        self.set_status(f"Starting · {provider_label()}", tone="busy")
        self._start_gen_tick()

        def worker() -> None:
            try:
                logging.info("CREATE BEAT start: %s", prompt[:80])
                pattern = run_pipeline(prompt)
                logging.info("CREATE BEAT ok: bpm=%s style=%s", pattern.get("bpm"), pattern.get("style"))
                self._ui_queue.put(("success", pattern))
            except Exception as exc:
                logging.exception("CREATE BEAT failed")
                self._ui_queue.put(("error", exc))

        threading.Thread(target=worker, daemon=True).start()

    def _start_gen_tick(self) -> None:
        self._stop_gen_tick()

        def tick() -> None:
            if not self._busy or self._gen_started_at is None:
                return
            elapsed = int(time.time() - self._gen_started_at)
            self.set_status(f"Generating · {elapsed}s · {provider_label()}", tone="busy")
            if elapsed >= 75:
                self.set_status(
                    f"Still working · {elapsed}s — check internet / API key",
                    tone="busy",
                )
            self._gen_tick_id = self.after(1000, tick)

        self._gen_tick_id = self.after(1000, tick)

    def _stop_gen_tick(self) -> None:
        if self._gen_tick_id is not None:
            try:
                self.after_cancel(self._gen_tick_id)
            except tk.TclError:
                pass
            self._gen_tick_id = None
        self._gen_started_at = None

    def _stop_busy(self) -> None:
        self._stop_gen_tick()
        self._busy = False
        self.create_btn.configure(state="normal", text="CREATE BEAT")
        self.progress.stop()
        self.progress.pack_forget()
        self._sync_beat_state()

    def _on_success(self, pattern: dict) -> None:
        self._stop_busy()
        try:
            consume_beat()
        except BeatQuotaExceeded:
            pass
        self._refresh_beat_quota()
        self._beat_ready = True
        bpm = pattern.get("bpm", "—")
        style = pattern.get("style", "unknown")
        self.set_status("Beat ready", tone="ok")
        self.set_meta(bpm, style, ready=True)
        self._update_action_buttons()
        self._refresh_setup_strip()

        if get_auto_open_fl():
            threading.Thread(target=self._open_fl_worker, daemon=True).start()

    def _open_fl_worker(self) -> None:
        try:
            logging.info("OPEN IN FL start")
            result = open_beat_in_fl(PROJECT_DIR)
            logging.info("OPEN IN FL ok: imported=%s method=%s", result.get("imported"), result.get("import_method"))
            self._ui_queue.put(("fl_done", result))
        except (FileNotFoundError, ValueError, OSError) as exc:
            logging.exception("OPEN IN FL failed")
            self._ui_queue.put(("fl_error", exc))

    def _on_fl_opened(self, result: dict) -> None:
        method = str(result.get("import_method", ""))
        if result.get("imported") and method == "flp_session":
            self.set_status("FL Studio · 3 channels ready — load your sounds", tone="ok")
        elif result.get("imported"):
            self.set_status("FL Studio · 3 tracks imported", tone="ok")
        else:
            self.set_status("FL Studio opened", tone="ok")
        self._refresh_setup_strip()

    def _on_error(self, exc: Exception) -> None:
        self._stop_busy()
        self.set_status("Error", tone="error")
        messagebox.showerror("PLG", format_llm_error(exc))

    def open_guide(self) -> None:
        path = PROJECT_DIR / "build_guide.txt"
        if not path.exists():
            messagebox.showinfo("PLG", "Create a beat first.")
            return
        os.startfile(path)  # type: ignore[attr-defined]

    def open_samples(self) -> None:
        path = get_samples_dir()
        ensure_samples_library(path, quiet=True)
        os.startfile(path)  # type: ignore[attr-defined]
        self._refresh_setup_strip()

    def import_kit(self) -> None:
        source = filedialog.askdirectory(title="Select FL Mafia / kit download folder")
        if not source:
            return
        try:
            library = get_samples_dir()
            counts = organize_library(Path(source), library)
            total = sum(counts.values())
            if total == 0:
                messagebox.showwarning(
                    "PLG",
                    "No supported files found (.wav .mid .flp .fst .fxp ...).",
                )
                return
            catalog = scan_library(library)
            save_catalog(catalog, PROJECT_DIR / "sample_catalog.json")
            self._empty_lib_warned = False
            self._refresh_setup_strip()
            messagebox.showinfo("PLG", f"Imported {total} files into library.")
        except (OSError, FileNotFoundError) as exc:
            messagebox.showerror("PLG", str(exc))

    def upgrade_starter_sounds(self) -> None:
        import subprocess
        import sys

        bat = PROJECT_DIR / "install_starter_sounds.bat"
        if sys.platform == "win32" and bat.is_file():
            subprocess.Popen(["cmd", "/c", "start", "", str(bat)], cwd=str(PROJECT_DIR))
            messagebox.showinfo(
                "PLG Starter",
                "Bundled starter sounds are already active.\n\n"
                "Optional: download 3 free CC0 packs from Signature Sounds, "
                "drop zips into assets/starter/incoming/, run the installer again.",
            )
        else:
            messagebox.showinfo(
                "PLG Starter",
                "Bundled starter is already included.\n\n"
                "Optional CC0 upgrade: see assets/starter/README.md",
            )

    def install_fl_scripts(self) -> None:
        try:
            installed = install_all(PROJECT_DIR)
            pack = installed.get("script_pack") or []
            self._refresh_setup_strip()
            messagebox.showinfo(
                "PLG",
                f"FL scripts installed.\n\n"
                f"Importer: {installed['plugin_script']}\n"
                f"Script pack: {len(pack)} tools in Piano roll → Scripts → PLG\n\n"
                "OPEN IN FL loads PLG_Session.flp automatically.",
            )
        except OSError as exc:
            messagebox.showerror("PLG", str(exc))

    def open_midi(self) -> None:
        path = PROJECT_DIR / "output_midi"
        path.mkdir(exist_ok=True)
        os.startfile(path)  # type: ignore[attr-defined]

    def open_output_folder(self) -> None:
        os.startfile(PROJECT_DIR)  # type: ignore[attr-defined]

    def open_in_fl_studio(self, *, silent: bool = False) -> None:
        try:
            self.set_status("Opening FL Studio…", tone="busy")
            threading.Thread(target=self._open_fl_worker, daemon=True).start()
        except OSError as exc:
            messagebox.showerror("PLG", str(exc))


def main() -> None:
    app = PlgApp()
    app.mainloop()


if __name__ == "__main__":
    main()
