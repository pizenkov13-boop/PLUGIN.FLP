"""Genre router — per-genre humanize profiles.

One deterministic profile per genre drives the producer brain so the same
engine does justice to country, opium, rage, phonk, drill, hyperpop, jersey,
k-pop, R&B, pop and (only on request) grind / anti-music — instead of forcing
trap micro-timing onto everything. Each profile only flips knobs the humanize
layer actually controls; the LLM still writes the notes.

The "trap" default reproduces the engine's original behaviour exactly, so the
opium/rage path and its tests are unchanged.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, fields, replace
from pathlib import Path

logger = logging.getLogger("plg.genre")


@dataclass(frozen=True)
class GenreProfile:
    name: str
    melody_scale: str | None  # snap target; None = leave melody pitches alone
    eight08: bool = True  # process the 808 line at all
    eight08_slides: bool = True  # high-register slide stabs
    hat_rolls: bool = True  # trap 1/32–1/64 rolls + pitch creep
    hat_swing: float = 1.0  # multiplier on the swing shift (0 = grid-locked)
    drop_tension: bool = False  # wipe kick+808 before phrase drops
    humanize_drum_velocity: bool = True  # randomize snare/clap velocity
    counter_melody: bool = True  # off-beat answer line
    stereo_drop: bool = True  # narrow verse → wide drop
    soft_clip: bool = False  # master soft-clip hint
    filth: float = 0.5  # 0..1 distortion / aggression hint
    melody_lag_ms: float = 0.0  # lazy groove-lag: drag melody notes late off the grid
    voicing_spread: float = 0.0  # 0..1 chance to invert a chord tone an octave for width
    kick_syncopation: float = 0.0  # 0..1 probability of extra off-grid kick hits (never on clap)
    markov_hats: bool = False  # Markov velocity state-machine for non-monotonous hats
    snare_riser: bool = False  # accelerating 1/4→1/32 snare roll + pitch-up before each drop


DEFAULT = GenreProfile("trap", None)

PROFILES: dict[str, GenreProfile] = {
    "trap": DEFAULT,
    "opium": GenreProfile(
        "opium", "phrygian", drop_tension=True, humanize_drum_velocity=False,
        soft_clip=True, filth=0.9, melody_lag_ms=12.0, voicing_spread=0.15,
        kick_syncopation=0.35, markov_hats=True,
    ),
    "phonk": GenreProfile(
        "phonk", "natural_minor", hat_swing=1.1, drop_tension=True,
        humanize_drum_velocity=False, soft_clip=True, filth=0.85, melody_lag_ms=12.0,
        kick_syncopation=0.3, markov_hats=True,
    ),
    "drill": GenreProfile(
        "drill", "phrygian", hat_swing=0.9, drop_tension=True,
        humanize_drum_velocity=False, filth=0.7, melody_lag_ms=10.0,
        kick_syncopation=0.4, markov_hats=True,
    ),
    "hyperpop": GenreProfile(
        "hyperpop", "lydian", hat_swing=0.8, drop_tension=True, soft_clip=True, filth=0.95,
    ),
    "jersey": GenreProfile(
        "jersey", "natural_minor", eight08_slides=False, hat_rolls=False,
        hat_swing=0.5, filth=0.4,
    ),
    "kpop": GenreProfile(
        "kpop", "major", eight08_slides=False, hat_rolls=False, hat_swing=0.3, filth=0.2,
    ),
    "rnb": GenreProfile(
        "rnb", "dorian", eight08_slides=False, hat_rolls=False, hat_swing=0.5, filth=0.15,
        melody_lag_ms=10.0, voicing_spread=0.15,
    ),
    "pop": GenreProfile(
        "pop", "major", eight08_slides=False, hat_rolls=False, hat_swing=0.3, filth=0.25,
        voicing_spread=0.12,
    ),
    "grind": GenreProfile(
        "grind", "locrian", eight08=False, eight08_slides=False, hat_rolls=False,
        hat_swing=0.0, counter_melody=False, stereo_drop=False, soft_clip=True, filth=1.0,
    ),
    # The Weeknd — dark synth-pop: Minor 9th colour (wide voicings), smooth
    # behind-the-beat pocket, no trap rolls, gentle.
    "weeknd": GenreProfile(
        "weeknd", "dorian", eight08_slides=False, hat_rolls=False, hat_swing=0.4,
        humanize_drum_velocity=True, soft_clip=False, filth=0.2,
        melody_lag_ms=14.0, voicing_spread=0.22,
    ),
    # Dua Lipa — nu-disco/dance-pop: straight 120 grid, off-beat hats, funky
    # syncopated bass, wide bright chords, no rolls.
    "dualipa": GenreProfile(
        "dualipa", "dorian", eight08_slides=False, hat_rolls=False, hat_swing=0.2,
        humanize_drum_velocity=True, soft_clip=False, filth=0.2,
        kick_syncopation=0.45, voicing_spread=0.2,
    ),
    # Martin Garrix — festival/big-room EDM: minor, layered leads, and an
    # accelerating snare riser (1/4→1/32) with pitch-up before each drop.
    "garrix": GenreProfile(
        "garrix", "natural_minor", eight08=False, eight08_slides=False, hat_rolls=False,
        hat_swing=0.3, drop_tension=True, soft_clip=True, filth=0.5,
        voicing_spread=0.2, snare_riser=True, markov_hats=True,
    ),
}

# Detection keywords (EN + RU). Checked in PRIORITY order so e.g. "k-pop" and
# "hyperpop" win over a bare "pop" substring.
GENRE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "grind": ("grindcore", "grind core", "anti-music", "anti music", "антимузык", "гриндкор", "blastbeat", "blast beat"),
    "opium": ("opium", "rage", "f1lthy", "filthy", "ken carson", "carson", "destroy lonely", "playboi", "carti", "pluggnb", "plugg", "sexyy", "sigma", "jerk"),
    "phonk": ("phonk", "memphis", "cowbell", "фонк", "дрифт"),
    "drill": ("drill", "дрилл", "uk drill", "ny drill"),
    "hyperpop": ("hyperpop", "hyper pop", "гиперпоп", "glitchcore", "glitch core"),
    "jersey": ("jersey", "jersey club", "джерси", "bed squeak"),
    "kpop": ("kpop", "k-pop", "к-поп", "кпоп", "idol pop"),
    "rnb": ("rnb", "r&b", "rhythm and blues", "neo soul", "neo-soul", "neosoul", "эрэнби"),
    "garrix": ("garrix", "martin garrix", "edm", "big room", "bigroom", "festival", "future bounce", "progressive house"),
    "dualipa": ("dua lipa", "dua", "nu-disco", "nu disco", "disco pop", "dance pop"),
    "weeknd": ("weeknd", "the weeknd", "abel", "dark pop", "synthwave pop", "80s pop"),
    "pop": ("pop", "поп", "synthpop", "synth pop"),
}
PRIORITY = (
    "grind", "opium", "phonk", "drill", "hyperpop", "jersey", "kpop", "rnb",
    "garrix", "dualipa", "weeknd", "pop",
)


def detect_genre(style: str = "", prompt: str = "") -> str:
    text = f"{style} {prompt}".lower()
    for genre in PRIORITY:
        if any(keyword in text for keyword in GENRE_KEYWORDS[genre]):
            return genre
    return "trap"


_ASSET_JSON = Path(__file__).resolve().parent / "assets" / "genre_profiles.json"


def _apply_profile_overrides() -> None:
    """Overlay preset values from JSON so genres can be retuned (or served from
    the cloud) without code changes. Source: PLG_GENRE_PROFILES_JSON env path, or
    the bundled assets/genre_profiles.json. Built-in PROFILES stay the fallback;
    any error is swallowed so a bad file can never break generation."""
    try:
        path = os.getenv("PLG_GENRE_PROFILES_JSON") or (
            str(_ASSET_JSON) if _ASSET_JSON.is_file() else ""
        )
        if not path:
            return
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        data = raw.get("profiles") if isinstance(raw, dict) and "profiles" in raw else raw
        valid = {f.name for f in fields(GenreProfile)}
        for name, fields_dict in (data or {}).items():
            if not isinstance(fields_dict, dict):
                continue
            patch = {k: v for k, v in fields_dict.items() if k in valid and k != "name"}
            if name in PROFILES:
                PROFILES[name] = replace(PROFILES[name], **patch)
            else:
                PROFILES[name] = GenreProfile(name=name, **patch)
    except Exception as exc:  # noqa: BLE001 — never let presets break the engine
        logger.warning("genre profile overrides ignored: %s", exc)


_apply_profile_overrides()


def profile_for(style: str = "", prompt: str = "", *, filth_max: bool = False) -> GenreProfile:
    profile = PROFILES.get(detect_genre(style, prompt), DEFAULT)
    if filth_max:
        profile = replace(
            profile,
            filth=1.0,
            soft_clip=True,
            drop_tension=True,
            humanize_drum_velocity=False,
            hat_swing=max(profile.hat_swing, 1.5),
        )
    return profile
