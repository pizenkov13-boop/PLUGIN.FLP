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

from dataclasses import dataclass, replace


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


DEFAULT = GenreProfile("trap", None)

PROFILES: dict[str, GenreProfile] = {
    "trap": DEFAULT,
    "opium": GenreProfile(
        "opium", "phrygian", drop_tension=True, humanize_drum_velocity=False,
        soft_clip=True, filth=0.9,
    ),
    "phonk": GenreProfile(
        "phonk", "natural_minor", hat_swing=1.1, drop_tension=True,
        humanize_drum_velocity=False, soft_clip=True, filth=0.85,
    ),
    "drill": GenreProfile(
        "drill", "phrygian", hat_swing=0.9, drop_tension=True,
        humanize_drum_velocity=False, filth=0.7,
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
    ),
    "pop": GenreProfile(
        "pop", "major", eight08_slides=False, hat_rolls=False, hat_swing=0.3, filth=0.25,
    ),
    "grind": GenreProfile(
        "grind", "locrian", eight08=False, eight08_slides=False, hat_rolls=False,
        hat_swing=0.0, counter_melody=False, stereo_drop=False, soft_clip=True, filth=1.0,
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
    "pop": ("pop", "поп", "dua", "weeknd", "dance pop", "nu-disco", "nu disco", "synthpop", "synth pop"),
}
PRIORITY = ("grind", "opium", "phonk", "drill", "hyperpop", "jersey", "kpop", "rnb", "pop")


def detect_genre(style: str = "", prompt: str = "") -> str:
    text = f"{style} {prompt}".lower()
    for genre in PRIORITY:
        if any(keyword in text for keyword in GENRE_KEYWORDS[genre]):
            return genre
    return "trap"


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
