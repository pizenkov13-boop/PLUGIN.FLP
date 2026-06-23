"""Prompt → timbre descriptor matching for sample selection.

Turns the *character* a user asks for — dark, hard, distorted, glassy, deep,
vintage, punchy… in English or Russian — into filename keyword hints, so the
picker grabs the 808 / kick / melody that actually sounds like the request
instead of a random file from the dump folder. Hints ride the existing
``bonus_keywords`` channel in sample_match, so they stack with Rule 16 pairing.
"""

from __future__ import annotations

# family -> (prompt triggers EN+RU substrings, filename hint keywords)
DESCRIPTOR_FAMILIES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "distorted": (
        ("distort", "dist", "overdrive", "grimy", "gritty", "fuzz", "saturat", "screw",
         "crunch", "dirty", "дист", "искаж", "грязн", "перегруз", "хрип"),
        ("dist", "distort", "drive", "od", "sat", "grime", "grimy", "fuzz", "crush",
         "dirty", "screw", "crunch"),
    ),
    "dark": (
        ("dark", "evil", "sinister", "gloom", "grim", "doom", "haunt", "creepy",
         "тёмн", "темн", "злой", "мрачн", "жутк"),
        ("dark", "evil", "night", "gloom", "shadow", "grim", "doom", "haunt",
         "creep", "blakk", "black"),
    ),
    "hard": (
        ("hard", "aggress", "heavy", "banger", "brutal", "violent",
         "жёстк", "жестк", "агресс", "тяжёл", "тяжел", "мощн"),
        ("hard", "heavy", "aggress", "bang", "war", "brutal", "slam"),
    ),
    "clean": (
        ("clean", "pure", "smooth", "polished", "чист", "гладк"),
        ("clean", "pure", "dry", "smooth"),
    ),
    "deep": (
        ("deep", "subby", "low end", "boom", "thick", "rumble", "fat",
         "глубок", "низк", "саб", "жирн", "бубн"),
        ("deep", "sub", "low", "boom", "thick", "rumble", "fat"),
    ),
    "punchy": (
        ("punch", "tight", "snappy", "knock", "click", "snap",
         "панч", "чётк", "четк", "хлёст", "хлест"),
        ("punch", "tight", "knock", "snap", "click", "tick", "pop"),
    ),
    "vintage": (
        ("vintage", "lofi", "lo-fi", "retro", "vinyl", "dusty", "tape", "analog",
         "винтаж", "ретро", "пыльн", "плёнк", "пленк", "старый"),
        ("vintage", "lofi", "lo_fi", "retro", "vinyl", "dust", "tape", "analog", "warm"),
    ),
    "bright": (
        ("bright", "glassy", "glass", "crystal", "shiny", "shine", "bell", "airy",
         "светл", "ярк", "стекл", "звонк", "колокол"),
        ("bright", "glass", "crystal", "shine", "bell", "air", "glassy"),
    ),
    "metallic": (
        ("metal", "metallic", "steel", "industrial", "металл", "сталь"),
        ("metal", "steel", "metallic", "industr"),
    ),
    "trap_opium": (
        ("opium", "rage", "carti", "ken", "carson", "destroy", "lonely", "f1lthy",
         "pluggnb", "plugg", "playboi"),
        ("opium", "rage", "carti", "ken", "plugg"),
    ),
    "phonk": (
        ("phonk", "drift", "memphis", "cowbell", "фонк", "дрифт"),
        ("phonk", "drift", "memphis", "cowbell"),
    ),
}


def descriptor_hints(prompt: str = "", style: str = "") -> tuple[str, ...]:
    """Filename keyword hints for every descriptor family the text triggers."""
    text = f"{prompt} {style}".lower()
    hints: list[str] = []
    seen: set[str] = set()
    for triggers, keywords in DESCRIPTOR_FAMILIES.values():
        if any(trig in text for trig in triggers):
            for keyword in keywords:
                if keyword not in seen:
                    seen.add(keyword)
                    hints.append(keyword)
    return tuple(hints)
