#!/usr/bin/env python3
"""Offline Optuna tuner for assets/genre_profiles.json.

Runs humanize-only trials on bundled MIDI fixtures (no LLM, no audio render).
Writes the best knob set for one genre into the JSON overlay PLG already loads.

Examples:
    python plg_tune.py --genre rage --trials 40
    python plg_tune.py --genre edm --trials 30 --write assets/genre_profiles.json
    python plg_tune.py --genre trap --trials 10 --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from copy import deepcopy
from dataclasses import asdict, fields, replace
from pathlib import Path
from typing import Any

from beat_humanize import humanize_pattern
from genre_profiles import PROFILES, GenreProfile, _ASSET_JSON, builtin_profile
from pattern_score import score_humanized_pattern
from plg_paths import app_dir

logger = logging.getLogger("plg.tune")

FIXTURES_FILE = app_dir() / "assets" / "tune_fixtures.json"
DEFAULT_OUTPUT = _ASSET_JSON

# Float knobs searched on every tunable genre.
FLOAT_SEARCH: dict[str, tuple[float, float]] = {
    "hat_swing": (0.2, 1.35),
    "melody_lag_ms": (0.0, 18.0),
    "voicing_spread": (0.0, 0.35),
    "kick_syncopation": (0.0, 0.55),
}

# Bool knobs — only suggested when the base profile already enables them OR
# the genre typically uses them (rage-like).
BOOL_WHEN_ON = (
    "markov_hats",
    "drop_tension",
    "hat_rolls",
    "eight08_slides",
    "soft_clip",
    "counter_melody",
    "stereo_drop",
    "snare_riser",
    "humanize_drum_velocity",
)

# Genre identity knobs — never tuned off when enabled in shipped defaults.
LOCKED_BOOLS: dict[str, frozenset[str]] = {
    "rage": frozenset({"soft_clip"}),
    "phonk": frozenset({"soft_clip"}),
    "hyperpop": frozenset({"soft_clip"}),
    "edm": frozenset({"snare_riser"}),
    "grind": frozenset({"soft_clip"}),
}

RAGE_LIKE = frozenset({"rage", "phonk", "drill", "trap", "hyperpop"})


def load_fixtures(path: Path, genre: str) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = raw.get("fixtures") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        raise ValueError(f"Invalid fixtures file: {path}")

    out: list[dict[str, Any]] = []
    for entry in items:
        if not isinstance(entry, dict):
            continue
        genres = entry.get("genres") or []
        if genres and genre not in genres and "trap" not in genres:
            continue
        pattern = entry.get("pattern")
        if isinstance(pattern, dict):
            out.append(deepcopy(pattern))
    if not out:
        raise ValueError(f"No fixtures for genre {genre!r} in {path}")
    return out


def base_profile(genre: str) -> GenreProfile:
    if genre not in PROFILES:
        raise KeyError(f"Unknown genre {genre!r}. Known: {', '.join(sorted(PROFILES))}")
    return builtin_profile(genre)


def suggest_profile(trial: Any, genre: str, seed: GenreProfile) -> GenreProfile:
    """Build a trial profile from Optuna suggestions."""
    patch: dict[str, Any] = {"name": genre}

    for key, (lo, hi) in FLOAT_SEARCH.items():
        if not hasattr(seed, key):
            continue
        patch[key] = trial.suggest_float(key, lo, hi)

    for key in BOOL_WHEN_ON:
        if not hasattr(seed, key):
            continue
        locked = LOCKED_BOOLS.get(genre, frozenset())
        if key in locked and getattr(seed, key):
            patch[key] = True
            continue
        current = getattr(seed, key)
        explorables = {"markov_hats", "humanize_drum_velocity", "drop_tension", "hat_rolls"}
        if current or (key in explorables and genre in RAGE_LIKE):
            patch[key] = trial.suggest_categorical(key, [True, False])
        else:
            patch[key] = current

    if seed.melody_scale is not None:
        patch["melody_scale"] = seed.melody_scale

    return replace(seed, **patch)


def evaluate_profile(profile: GenreProfile, fixtures: list[dict[str, Any]]) -> float:
    total = 0.0
    for fixture in fixtures:
        pattern = deepcopy(fixture)
        pattern["style"] = pattern.get("style") or profile.name
        pattern["user_prompt"] = pattern.get("user_prompt") or f"{profile.name} tune"
        out = humanize_pattern(pattern, profile=profile)
        total += score_humanized_pattern(out, profile)
    return total / max(1, len(fixtures))


def profile_to_json_entry(profile: GenreProfile) -> dict[str, Any]:
    data = asdict(profile)
    data["name"] = profile.name
    return data


def merge_into_genre_json(path: Path, genre: str, profile: GenreProfile) -> None:
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            raw = {}
    else:
        raw = {}

    if isinstance(raw, dict) and "profiles" in raw:
        profiles = raw["profiles"]
    elif isinstance(raw, dict):
        profiles = raw
        raw = {"profiles": profiles}
    else:
        profiles = {}
        raw = {"profiles": profiles}

    if not isinstance(profiles, dict):
        profiles = {}
        raw["profiles"] = profiles

    profiles[genre] = profile_to_json_entry(profile)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_study(
    genre: str,
    *,
    trials: int,
    fixtures_path: Path,
    seed: int,
) -> tuple[GenreProfile, float]:
    try:
        import optuna
    except ImportError as exc:
        raise SystemExit("optuna is required: pip install optuna") from exc

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    fixtures = load_fixtures(fixtures_path, genre)
    start = base_profile(genre)
    baseline = evaluate_profile(start, fixtures)
    logger.info("Baseline score for %s: %.2f (%s fixtures)", genre, baseline, len(fixtures))

    def objective(trial: optuna.Trial) -> float:
        profile = suggest_profile(trial, genre, start)
        return evaluate_profile(profile, fixtures)

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(objective, n_trials=trials, show_progress_bar=False)

    best_params = study.best_params
    best_profile = replace(start, name=genre, **best_params)
    best_score = study.best_value
    logger.info("Best score: %.2f (Δ %+.2f)", best_score, best_score - baseline)
    return best_profile, best_score


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tune genre_profiles.json with Optuna (offline)")
    parser.add_argument("--genre", default="rage", help="Genre key in PROFILES (default: rage)")
    parser.add_argument("--trials", type=int, default=40, help="Optuna trials (default: 40)")
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=FIXTURES_FILE,
        help=f"Fixture JSON (default: {FIXTURES_FILE})",
    )
    parser.add_argument(
        "--write",
        type=Path,
        default=None,
        help=f"Merge best profile into this JSON (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print best params, do not write JSON")
    parser.add_argument("--seed", type=int, default=42, help="Optuna sampler seed")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if not args.fixtures.is_file():
        logger.error("Fixtures not found: %s", args.fixtures)
        return 1

    try:
        best_profile, best_score = run_study(
            args.genre,
            trials=max(1, args.trials),
            fixtures_path=args.fixtures,
            seed=args.seed,
        )
    except (KeyError, ValueError) as exc:
        logger.error("%s", exc)
        return 1

    print(json.dumps(profile_to_json_entry(best_profile), indent=2, ensure_ascii=False))
    print(f"\n# best_score={best_score:.3f}", file=sys.stderr)

    if args.dry_run:
        print("Dry run — JSON not written.", file=sys.stderr)
        return 0

    out_path = args.write or DEFAULT_OUTPUT
    merge_into_genre_json(out_path, args.genre, best_profile)
    logger.info("Wrote %s profile to %s", args.genre, out_path)
    print(
        "Reload PLG or set PLG_GENRE_PROFILES_JSON to pick up changes.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
