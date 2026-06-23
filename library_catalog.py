"""Scan full PLG library: audio, MIDI, presets, projects, banks, plugins."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from library_paths import (
    ALL_LIBRARY_FOLDERS,
    AUDIO_EXTENSIONS,
    AUDIO_FOLDERS,
    BANK_EXTENSIONS,
    MIDI_EXTENSIONS,
    PLUGIN_EXTENSIONS,
    PRESET_EXTENSIONS,
    PROJECT_EXTENSIONS,
)

MAX_AUDIO_IN_PROMPT = 100
MAX_OTHER_IN_PROMPT = 20
CATALOG_FILE_NAME = "sample_catalog.json"


# Keyword → audio bucket, matched anywhere in the relative path (folder names +
# filename), so a deeply nested custom kit gets sorted by what the files ARE,
# not by a fixed top-level folder. First match wins; order matters.
_CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("808", ("808", "sub bass", "subbass", "sub_bass", "sub-bass", "distort", "reese", "bassloop")),
    ("hats", ("hat", "hi-hat", "hihat", "hi_hat", "cymbal", "ride", "shaker")),
    ("melodies", ("melod", "bell", "pluck", "piano", "guitar", "synth", "lead", "arp", "chord", "flute", "choir", "keys")),
    ("fx", ("fx", "riser", "downer", "sweep", "transition", "impact", "whoosh", "reverse")),
    ("textures", ("texture", "ambient", "drone", "vinyl", "atmos", "noise")),
    ("kits", ("kick", "snare", "clap", "rim", "perc", "tom", "crash", "snap", "drum")),
)


def _folder_category(path: Path, root: Path) -> str:
    rel = path.relative_to(root)
    parts = rel.parts
    # Fast path: an explicitly organized library (top folder is a known bucket).
    if len(parts) > 1 and parts[0].lower() in ALL_LIBRARY_FOLDERS:
        return parts[0].lower()
    # Otherwise classify by keywords across the whole path (any depth).
    hay = rel.as_posix().lower()
    for bucket, keywords in _CATEGORY_KEYWORDS:
        if any(keyword in hay for keyword in keywords):
            return bucket
    return "kits" if path.suffix.lower() in AUDIO_EXTENSIONS else "other"


def scan_library(root: Path) -> dict[str, Any]:
    if not root.is_dir():
        raise FileNotFoundError(f"Library folder not found: {root}")

    audio: dict[str, list[str]] = {name: [] for name in AUDIO_FOLDERS}
    midi: list[str] = []
    presets: list[str] = []
    projects: list[str] = []
    banks: list[str] = []
    plugins: list[str] = []

    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        suffix = file_path.suffix.lower()
        rel = file_path.relative_to(root).as_posix()

        if suffix in AUDIO_EXTENSIONS:
            category = _folder_category(file_path, root)
            if category not in audio:
                category = "kits"
            audio[category].append(rel)
        elif suffix in MIDI_EXTENSIONS:
            midi.append(rel)
        elif suffix in PRESET_EXTENSIONS:
            presets.append(rel)
        elif suffix in PROJECT_EXTENSIONS:
            projects.append(rel)
        elif suffix in BANK_EXTENSIONS:
            banks.append(rel)
        elif suffix in PLUGIN_EXTENSIONS:
            plugins.append(rel)

    audio = {key: values for key, values in audio.items() if values}
    audio_total = sum(len(values) for values in audio.values())
    total = audio_total + len(midi) + len(presets) + len(projects) + len(banks) + len(plugins)

    return {
        "root": str(root.resolve()),
        "total": total,
        "audio_total": audio_total,
        "audio": audio,
        "midi": midi,
        "presets": presets,
        "projects": projects,
        "banks": banks,
        "plugins": plugins,
    }


def save_catalog(catalog: dict[str, Any], output_path: Path) -> None:
    output_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")


def _limited_list(items: list[str], limit: int) -> tuple[list[str], int]:
    if len(items) <= limit:
        return items, 0
    return items[:limit], len(items) - limit


def format_library_for_prompt(catalog: dict[str, Any]) -> str:
    if catalog.get("total", 0) == 0:
        return "Library is empty."

    lines = [
        f"Library root: {catalog['root']}",
        f"Total assets: {catalog['total']} (audio: {catalog.get('audio_total', 0)})",
        "",
        "AUDIO — use in samples[] and note.sample (relative paths only):",
    ]

    audio_used = 0
    for category, files in catalog.get("audio", {}).items():
        lines.append(f"  [{category}] ({len(files)} files)")
        for rel in files:
            if audio_used >= MAX_AUDIO_IN_PROMPT:
                rest = catalog.get("audio_total", 0) - MAX_AUDIO_IN_PROMPT
                if rest > 0:
                    lines.append(f"  ... +{rest} more audio omitted")
                break
            lines.append(f"    - {rel}")
            audio_used += 1
        if audio_used >= MAX_AUDIO_IN_PROMPT:
            break

    for label, key in (
        ("MIDI — reference in library_refs[], optional manual_steps to drag into FL", "midi"),
        ("PRESETS — library_refs type=preset, tell user which channel to load", "presets"),
        ("PROJECTS — library_refs type=project, open as reference template", "projects"),
        ("BANKS — library_refs type=bank, load in sampler/FL browser", "banks"),
        ("PLUGINS — library_refs type=plugin, manual install only, never auto-load", "plugins"),
    ):
        items = catalog.get(key) or []
        if not items:
            continue
        shown, omitted = _limited_list(items, MAX_OTHER_IN_PROMPT)
        lines.extend(["", f"{label}:"])
        lines.extend(f"  - {item}" for item in shown)
        if omitted:
            lines.append(f"  ... +{omitted} more")

    return "\n".join(lines).strip()


# Backward-compatible aliases used across the project
def scan_samples_directory(root: Path) -> dict[str, Any]:
    catalog = scan_library(root)
    legacy_audio = catalog.get("audio") or {}
    return {
        "root": catalog["root"],
        "total": catalog.get("audio_total", 0),
        "categories": legacy_audio,
    }


def format_catalog_for_prompt(catalog: dict[str, Any]) -> str:
    if "audio" in catalog:
        return format_library_for_prompt(catalog)
    return format_library_for_prompt(
        {
            "root": catalog.get("root", ""),
            "total": catalog.get("total", 0),
            "audio_total": catalog.get("total", 0),
            "audio": catalog.get("categories", {}),
            "midi": [],
            "presets": [],
            "projects": [],
            "banks": [],
            "plugins": [],
        }
    )
