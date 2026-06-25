"""Pick the best library audio per track from prompt + style (not first file).

Name/folder scoring is the fast first pass. Top candidates are re-ranked by:
  1) numpy spectral features (audio_features) when the prompt implies timbre
  2) CLAP text↔audio similarity when laion-clap is installed (PLG_USE_CLAP=1 or auto)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from library_paths import AUDIO_EXTENSIONS

KIT_TRACK_ORDER = ("sub_808", "kick", "snare", "clap", "hi_hats", "melody_lead")

TRACK_PROFILES: dict[str, dict[str, Any]] = {
    "kick": {
        "folders": ("kits", "808"),
        "strong": ("kick", "bd", "bassdrum", "bass_drum", "kik"),
        "avoid": ("snare", "clap", "hat", "hihat", "melody", "bell", "rim", "perc", "vocal", "tag", "808", "sub"),
    },
    "snare": {
        "folders": ("kits", "splice"),
        "strong": ("snare", "snr", "sd", "rim", "shot"),
        "avoid": ("kick", "808", "hat", "clap", "melody", "bass", "sub", "vocal", "tag"),
    },
    "snare_layer": {
        "folders": ("kits", "splice"),
        "strong": ("rim", "rimshot", "click", "snap", "perc", "tick"),
        "avoid": ("kick", "808", "hat", "melody", "vocal", "sub", "bass"),
    },
    "clap": {
        "folders": ("kits", "splice"),
        "strong": ("clap", "snap", "slap", "perc"),
        "avoid": ("kick", "snare", "808", "hat", "melody", "bass", "sub", "vocal"),
    },
    "sub_808": {
        "folders": ("808", "kits"),
        "strong": ("808", "sub", "subbass", "sub_bass", "bass", "donk", "low", "distort", "reese"),
        "avoid": (
            "kick",
            "snare",
            "clap",
            "hat",
            "hihat",
            "hi_hat",
            "openhat",
            "cymbal",
            "rim",
            "perc",
            "tom",
            "crash",
            "shaker",
            "vocal",
            "tag",
            "chant",
        ),
    },
    "hi_hats": {
        "folders": ("hats", "kits", "splice"),
        "strong": ("hat", "hihat", "hi_hat", "hi-hat", "hh", "open", "closed", "cymbal", "ride"),
        "avoid": ("808", "kick", "snare", "clap", "bass", "sub", "melody", "bell", "lead", "piano", "pluck"),
    },
    "melody_lead": {
        "folders": ("melodies", "kits", "splice", "textures"),
        "strong": (
            "melody",
            "lead",
            "bell",
            "pluck",
            "key",
            "piano",
            "arp",
            "synth",
            "loop",
            "stab",
            "choir",
            "pad",
            "flute",
            "guitar",
        ),
        "avoid": ("808", "kick", "snare", "clap", "hat", "hihat", "rim", "perc", "tom", "crash"),
    },
}


def _normalize(text: str) -> str:
    return text.lower().replace("-", "_").replace(" ", "_")


def _tokens(*texts: str) -> set[str]:
    found: set[str] = set()
    for text in texts:
        if not text:
            continue
        norm = _normalize(text)
        for part in re.split(r"[_/\\.\s]+", norm):
            if len(part) >= 2:
                found.add(part)
        for word in re.findall(r"[a-z0-9]{3,}", text.lower()):
            found.add(word)
    return found


# Rule 16 — Perfect Pair: kick character follows the chosen 808.
_LONG_808_HINTS = ("long", "distort", "dist", "reese", "growl", "sub", "deep", "boom", "sustain")
_SHORT_808_HINTS = ("short", "punch", "tight", "click", "clean", "stab", "pluck")
_PUNCHY_KICK = ("click", "punch", "tight", "hard", "clean", "short", "knock")
_FAT_KICK = ("fat", "boom", "deep", "sub", "round", "long", "808", "thump")


def partner_kick_keywords(eight08_name: str) -> tuple[str, ...]:
    """A long/distorted sub wants a short punchy click kick, and vice versa."""
    name = _normalize(eight08_name)
    if any(h in name for h in _SHORT_808_HINTS):
        return _FAT_KICK
    if any(h in name for h in _LONG_808_HINTS):
        return _PUNCHY_KICK
    return _PUNCHY_KICK  # dark default: long distorted 808 → tight click kick


def score_candidate(
    rel_path: str,
    track: str,
    *,
    prompt_tokens: set[str],
    style_tokens: set[str],
    prompt_raw: str,
    bonus_keywords: tuple[str, ...] = (),
) -> int:
    profile = TRACK_PROFILES[track]
    norm_name = _normalize(Path(rel_path).name)
    norm_path = _normalize(rel_path)
    score = 0

    parts = rel_path.replace("\\", "/").split("/")
    folder = parts[0].lower() if len(parts) > 1 else ""
    primary = profile["folders"][0]
    if folder == primary:
        score += 16
    elif folder in profile["folders"]:
        score += 8

    for keyword in profile["strong"]:
        if keyword in norm_name:
            score += 15
        elif keyword in norm_path:
            score += 8

    for keyword in profile.get("avoid", ()):
        if keyword in norm_name:
            score -= 45

    for token in prompt_tokens | style_tokens:
        if len(token) < 3:
            continue
        if token in norm_name:
            score += 24
        elif token in norm_path:
            score += 14

    lower_prompt = prompt_raw.lower()
    for word in re.findall(r"[a-z0-9]{4,}", lower_prompt):
        if word in norm_name:
            score += 20

    for keyword in bonus_keywords:
        if keyword in norm_name:
            score += 22
        elif keyword in norm_path:
            score += 10

    return score


def iter_track_candidates(catalog: dict[str, Any], track: str) -> list[str]:
    audio = catalog.get("audio") or {}
    profile = TRACK_PROFILES[track]
    seen: set[str] = set()
    ordered: list[str] = []

    for folder in profile["folders"]:
        for rel in audio.get(folder, []):
            if rel not in seen:
                seen.add(rel)
                ordered.append(rel)

    for folder, files in audio.items():
        if folder in profile["folders"]:
            continue
        for rel in files:
            if rel not in seen:
                seen.add(rel)
                ordered.append(rel)

    return ordered


def pick_best_for_track(
    catalog: dict[str, Any],
    track: str,
    library_root: Path,
    *,
    prompt: str = "",
    style: str = "",
    exclude: set[str] | None = None,
    bonus_keywords: tuple[str, ...] = (),
    audio_target: dict[str, str] | None = None,
    audio_top_k: int = 6,
    use_clap: bool | None = None,
    clap_top_k: int = 8,
) -> tuple[Path | None, int]:
    prompt_tokens = _tokens(prompt)
    style_tokens = _tokens(style)
    blocked = exclude or set()
    profile = TRACK_PROFILES[track]

    scored: list[tuple[int, Path]] = []
    for rel in iter_track_candidates(catalog, track):
        path = (library_root / rel).resolve()
        if not path.is_file():
            continue
        if str(path) in blocked:
            continue

        score = score_candidate(
            rel,
            track,
            prompt_tokens=prompt_tokens,
            style_tokens=style_tokens,
            prompt_raw=prompt,
            bonus_keywords=bonus_keywords,
        )
        folder = rel.split("/")[0].lower() if "/" in rel else ""
        if folder not in profile["folders"] and score < 18:
            continue
        scored.append((score, path))

    if not scored:
        return None, -10_000

    # Stable sort keeps the original candidate order on ties (legacy behaviour).
    order = sorted(range(len(scored)), key=lambda i: scored[i][0], reverse=True)

    rerank_k = max(audio_top_k, clap_top_k) if use_clap is not False else audio_top_k
    shortlist = [scored[i] for i in order[:rerank_k]]

    clap_on = use_clap
    if clap_on is None:
        try:
            import clap_match

            clap_on = clap_match.use_clap() and bool((prompt or style).strip())
        except ImportError:
            clap_on = False

    clap_bonuses: dict[str, int] = {}
    if clap_on and shortlist:
        import clap_match

        text_emb = clap_match.get_text_embedding(prompt, style, track)
        if text_emb is not None:
            clap_bonuses = clap_match.score_paths([p for _, p in shortlist], text_emb)

    if audio_target or clap_bonuses:
        import audio_features

        best_score = -10_000
        best_path: Path | None = None
        for name_score, path in shortlist:
            total = name_score
            if audio_target:
                total += audio_features.feature_match_score(
                    audio_features.analyze_cached(path),
                    audio_target,
                )
            total += clap_bonuses.get(str(path.resolve()), 0)
            if total > best_score:
                best_score = total
                best_path = path
    else:
        best_score, best_path = scored[order[0]]

    if best_path is None or best_score < 5:
        return None, best_score
    return best_path, best_score


def pick_full_kit(
    catalog: dict[str, Any],
    library_root: Path,
    *,
    prompt: str = "",
    style: str = "",
) -> dict[str, tuple[Path, int]]:
    """Pick one unique wav per drum/melody role — no file reused across channels."""
    used: set[str] = set()
    kit: dict[str, tuple[Path, int]] = {}

    for track in KIT_TRACK_ORDER:
        path, score = pick_best_for_track(
            catalog,
            track,
            library_root,
            prompt=prompt,
            style=style,
            exclude=used,
        )
        if path is None:
            continue
        kit[track] = (path, score)
        used.add(str(path.resolve()))

    return kit


def resolve_path_from_library(file_ref: str, library_root: Path) -> Path | None:
    raw = file_ref.strip()
    if not raw:
        return None

    direct = Path(raw)
    if direct.is_file():
        return direct.resolve()

    relative = library_root / raw
    if relative.is_file():
        return relative.resolve()

    target = Path(raw).name.lower()
    if not target:
        return None

    for path in library_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS and path.name.lower() == target:
            return path.resolve()
    return None


def merge_llm_sample_picks(
    sound_map: dict[str, Path],
    samples_layer: list[dict[str, Any]],
    library_root: Path,
) -> dict[str, Path]:
    merged = dict(sound_map)
    for entry in samples_layer:
        if not isinstance(entry, dict):
            continue
        track = entry.get("track")
        file_ref = entry.get("file")
        if track not in merged or not file_ref:
            continue
        resolved = resolve_path_from_library(str(file_ref), library_root)
        if resolved is not None:
            merged[str(track)] = resolved
    return merged
