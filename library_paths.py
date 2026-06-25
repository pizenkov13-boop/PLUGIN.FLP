"""PLG library folders — maps FL Mafia-style categories to disk layout."""

from __future__ import annotations

from pathlib import Path

from plg_paths import app_dir

PROJECT_DIR = app_dir()
DEFAULT_LIBRARY_DIR = PROJECT_DIR / "PLG_Library"
LEGACY_LIBRARY_DIR = PROJECT_DIR / "PLG_Sounds"

# Audio — drum kits, samples, splice downloads
AUDIO_FOLDERS = ("808", "hats", "kits", "textures", "melodies", "fx", "vocal_presets", "splice", "references")

# Other Mafia categories
MIDI_FOLDER = "midi"
PRESETS_FOLDER = "presets"
PROJECTS_FOLDER = "projects"
BANKS_FOLDER = "banks"
PLUGINS_FOLDER = "plugins"

ALL_LIBRARY_FOLDERS = AUDIO_FOLDERS + (
    MIDI_FOLDER,
    PRESETS_FOLDER,
    PROJECTS_FOLDER,
    BANKS_FOLDER,
    PLUGINS_FOLDER,
)

AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".aif", ".aiff"}
MIDI_EXTENSIONS = {".mid", ".midi"}
PRESET_EXTENSIONS = {".fst", ".fxp", ".nmsv", ".vital", ".serumpreset", ".h2p"}
PROJECT_EXTENSIONS = {".flp"}
BANK_EXTENSIONS = {".sf2", ".sfz", ".zip"}
PLUGIN_EXTENSIONS = {".dll", ".vst3", ".exe"}

MAFIA_CATEGORY_HINTS = {
    "808": "drum kits / 808 bass",
    "hats": "drum kits / hi-hats",
    "kits": "drum kits / kicks snares claps",
    "textures": "samples / texture & noise",
    "melodies": "samples / loops & melodies",
    "fx": "samples / fx & transitions",
    "vocal_presets": "presets / vocal chains",
    "splice": "splice / one-shots & loops",
    "references": "references / drop snippets to reverse into MIDI",
    "midi": "midi / melody & drum MIDI",
    "presets": "presets / synth & mixer presets",
    "projects": "projects / reference FL templates",
    "banks": "banks / soundfonts & banks",
    "plugins": "plugins / install manually in FL",
}
