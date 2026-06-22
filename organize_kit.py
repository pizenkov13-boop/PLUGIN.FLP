#!/usr/bin/env python3
"""Sort FL Mafia / Splice / kit downloads into PLG_Library layout."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

from library_catalog import save_catalog, scan_library
from library_paths import (
    ALL_LIBRARY_FOLDERS,
    AUDIO_EXTENSIONS,
    BANK_EXTENSIONS,
    DEFAULT_LIBRARY_DIR,
    MIDI_EXTENSIONS,
    PLUGIN_EXTENSIONS,
    PRESET_EXTENSIONS,
    PROJECT_EXTENSIONS,
)

PROJECT_DIR = Path(__file__).resolve().parent

AUDIO_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("808", ("808", "bass", "sub", "subbass", "sub_bass", "808s")),
    ("hats", ("hat", "hihat", "hi-hat", "hi_hat", "openhat", "open_hat", "cymbal", "ride")),
    ("melodies", ("melody", "loop", "keys", "piano", "bell", "pluck", "lead", "arp")),
    ("textures", ("texture", "foley", "noise", "buzz", "vinyl", "atmo", "ambient")),
    ("fx", ("fx", "impact", "riser", "sweep", "transition", "chant", "vox", "tag")),
    ("vocal_presets", ("vocal", "autotune", "voice")),
    ("splice", ("splice",)),
    ("kits", ("kick", "snare", "clap", "rim", "perc", "drum", "tom")),
)

SKIP_PARTS = {"macosx", "__macosx", ".git"}


def classify_audio(name: str) -> str:
    text = name.lower().replace("-", "_").replace(" ", "_")
    for category, keywords in AUDIO_RULES:
        if any(key in text for key in keywords):
            return category
    return "kits"


def unique_destination(folder: Path, filename: str) -> Path:
    target = folder / filename
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    index = 2
    while True:
        candidate = folder / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def target_folder(suffix: str, stem: str) -> str:
    lower = suffix.lower()
    if lower in MIDI_EXTENSIONS:
        return "midi"
    if lower in PRESET_EXTENSIONS:
        return "presets"
    if lower in PROJECT_EXTENSIONS:
        return "projects"
    if lower in BANK_EXTENSIONS:
        return "banks"
    if lower in PLUGIN_EXTENSIONS:
        return "plugins"
    if lower in AUDIO_EXTENSIONS:
        return classify_audio(stem)
    return "kits"


def organize_library(source: Path, output: Path, *, dry_run: bool = False) -> dict[str, int]:
    if not source.is_dir():
        raise FileNotFoundError(f"Source folder not found: {source}")

    output.mkdir(parents=True, exist_ok=True)
    for name in ALL_LIBRARY_FOLDERS:
        (output / name).mkdir(exist_ok=True)

    counts: dict[str, int] = {name: 0 for name in ALL_LIBRARY_FOLDERS}

    all_extensions = (
        AUDIO_EXTENSIONS
        | MIDI_EXTENSIONS
        | PRESET_EXTENSIONS
        | PROJECT_EXTENSIONS
        | BANK_EXTENSIONS
        | PLUGIN_EXTENSIONS
    )

    for file_path in sorted(source.rglob("*")):
        if not file_path.is_file():
            continue
        suffix = file_path.suffix.lower()
        if suffix not in all_extensions:
            continue
        if any(part.lower() in SKIP_PARTS for part in file_path.parts):
            continue

        category = target_folder(suffix, file_path.stem)
        dest = unique_destination(output / category, file_path.name)

        if dry_run:
            print(f"[dry] {file_path.name} -> {category}/")
        else:
            shutil.copy2(file_path, dest)
        counts[category] = counts.get(category, 0) + 1

    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Organize FL Mafia downloads into PLG_Library/")
    parser.add_argument("source", type=Path, help="Folder with extracted download")
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_LIBRARY_DIR)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    counts = organize_library(args.source.resolve(), args.output.resolve(), dry_run=args.dry_run)
    total = sum(counts.values())

    print("")
    print(f"PLG Library: {args.output.resolve()}")
    print(f"Files sorted: {total}")
    for key, value in counts.items():
        if value:
            print(f"  {key}: {value}")

    if args.dry_run:
        print("(dry run — no files copied)")
        return 0

    if total == 0:
        print("No supported files found (.wav .mid .flp .fst .fxp .dll ...)")
        return 1

    catalog = scan_library(args.output.resolve())
    save_catalog(catalog, PROJECT_DIR / "sample_catalog.json")
    print(f"Catalog: {catalog['total']} assets -> sample_catalog.json")
    print("")
    print("Next: run_plg.bat -> CREATE BEAT")
    return 0


# Backward-compatible alias
organize_kit = organize_library

if __name__ == "__main__":
    raise SystemExit(main())
