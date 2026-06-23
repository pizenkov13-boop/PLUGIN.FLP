"""Kit Variety Guard — never reuse the same sample kit twice in a row."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from plg_paths import user_data_dir

logger = logging.getLogger("plg.kit_variety")

HISTORY_FILE = user_data_dir() / "kit_history.json"
MAX_HISTORY = 6


def _load_history() -> list[dict[str, str]]:
    if not HISTORY_FILE.is_file():
        return []
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        entries = data.get("kits", [])
        return entries if isinstance(entries, list) else []
    except (OSError, json.JSONDecodeError, TypeError):
        return []


def last_kit_paths() -> set[str]:
    history = _load_history()
    if not history:
        return set()
    last = history[-1]
    if not isinstance(last, dict):
        return set()
    return {str(v) for v in last.values() if v}


def save_kit_pick(picks: dict[str, Path]) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {track: str(path.resolve()) for track, path in picks.items()}
    history = _load_history()
    history.append(entry)
    history = history[-MAX_HISTORY:]
    HISTORY_FILE.write_text(json.dumps({"kits": history}, indent=2), encoding="utf-8")
    logger.info("Kit variety: saved kit (%s tracks)", len(entry))


def apply_variety_penalty(
    score: int,
    path: Path,
    *,
    blocked: set[str],
    last_paths: set[str],
) -> int:
    resolved = str(path.resolve())
    if resolved in blocked:
        return -10_000
    if resolved in last_paths:
        return score - 120
    return score


def pick_with_variety(
    catalog: dict[str, Any],
    library_root: Path,
    *,
    prompt: str = "",
    style: str = "",
) -> dict[str, tuple[Any, int]]:
    """Wrapper around pick_full_kit that penalizes last generation's files."""
    from sample_match import KIT_TRACK_ORDER, partner_kick_keywords, pick_best_for_track
    from sound_descriptors import descriptor_hints

    last_paths = last_kit_paths()
    used: set[str] = set()
    kit: dict[str, tuple[Any, int]] = {}

    # Timbre targeting: pull samples whose names match the *character* asked for
    # (dark / hard / distorted / glassy / vintage…), EN or RU, any genre.
    desc = descriptor_hints(prompt, style)

    for track in KIT_TRACK_ORDER:
        bonus: tuple[str, ...] = desc
        # Rule 16 — Perfect Pair: bias the kick toward the chosen 808's partner.
        if track == "kick" and "sub_808" in kit:
            bonus = tuple(dict.fromkeys(partner_kick_keywords(Path(kit["sub_808"][0]).name) + desc))
        # First pass: strict block on last kit
        path, score = pick_best_for_track(
            catalog,
            track,
            library_root,
            prompt=prompt,
            style=style,
            exclude=used | last_paths,
            bonus_keywords=bonus,
        )
        # Second pass: allow last kit only if nothing else fits
        if path is None:
            path, score = pick_best_for_track(
                catalog,
                track,
                library_root,
                prompt=prompt,
                style=style,
                exclude=used,
                bonus_keywords=bonus,
            )
            if path is not None and str(path.resolve()) in last_paths:
                score -= 40

        if path is None:
            continue
        kit[track] = (path, score)
        used.add(str(path.resolve()))

    return kit
