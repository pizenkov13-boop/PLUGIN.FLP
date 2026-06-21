"""Scan local sample folders and build a catalog for PLG / Gemini."""

from __future__ import annotations

import json
from pathlib import Path

AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".aif", ".aiff", ".flac"}
DEFAULT_CATEGORIES = ("808", "hats", "textures", "melodies", "fx", "vocal_presets", "other")
MAX_FILES_IN_PROMPT = 120


def _category_for(path: Path, root: Path) -> str:
    rel_parts = path.relative_to(root).parts
    if len(rel_parts) > 1:
        folder = rel_parts[0].lower()
        if folder in DEFAULT_CATEGORIES or folder != "other":
            return folder
    return "other"


def scan_samples_directory(root: Path) -> dict:
    if not root.is_dir():
        raise FileNotFoundError(f"Sample folder not found: {root}")

    categories: dict[str, list[str]] = {name: [] for name in DEFAULT_CATEGORIES}

    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        rel = file_path.relative_to(root).as_posix()
        category = _category_for(file_path, root)
        if category not in categories:
            categories[category] = []
        categories[category].append(rel)

    categories = {key: values for key, values in categories.items() if values}
    total = sum(len(values) for values in categories.values())

    return {
        "root": str(root.resolve()),
        "total": total,
        "categories": categories,
    }


def save_catalog(catalog: dict, output_path: Path) -> None:
    output_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")


def format_catalog_for_prompt(catalog: dict, limit: int = MAX_FILES_IN_PROMPT) -> str:
    if catalog.get("total", 0) == 0:
        return "Sample catalog is empty."

    lines = [
        f"Sample library root: {catalog['root']}",
        f"Total files: {catalog['total']}",
        "Pick ONLY files from this catalog. Use relative paths exactly as listed.",
        "",
    ]

    used = 0
    for category, files in catalog.get("categories", {}).items():
        lines.append(f"[{category}] ({len(files)} files)")
        for rel in files:
            if used >= limit:
                lines.append(f"... and {catalog['total'] - limit} more files omitted")
                return "\n".join(lines)
            lines.append(f"  - {rel}")
            used += 1
        lines.append("")

    return "\n".join(lines).strip()
