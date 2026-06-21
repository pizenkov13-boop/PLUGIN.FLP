"""Render a rough WAV preview from pattern JSON (no FL Studio required)."""

from __future__ import annotations

import json
from pathlib import Path

from typing import Any

from pydub import AudioSegment
from pydub.generators import Sine

from pattern_utils import TRACK_KEYS, parse_note_name, track_notes

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_JSON = PROJECT_DIR / "output_pattern.json"
PREVIEW_FILE = PROJECT_DIR / "output_preview.wav"

TRACK_SAMPLE_DIRS = {
    "hi_hats": ("hats", "808", "kits"),
    "sub_808": ("808", "kits"),
    "melody_lead": ("melodies", "kits"),
    "textures": ("textures", "fx"),
    "fx": ("fx", "textures"),
}

AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".aif", ".aiff"}


def step_to_ms(time_step: float, bpm: float) -> int:
    beats = float(time_step) / 4.0
    return int(beats * (60_000.0 / bpm))


def note_length_ms(length_step: float, bpm: float) -> int:
    return max(80, step_to_ms(length_step, bpm))


def find_first_sample(samples_root: Path, folders: tuple[str, ...]) -> Path | None:
    for folder in folders:
        base = samples_root / folder
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix.lower() in AUDIO_EXTENSIONS:
                return path
    return None


def load_clip(path: Path) -> AudioSegment:
    suffix = path.suffix.lower()
    if suffix == ".wav":
        return AudioSegment.from_wav(path)
    if suffix == ".mp3":
        return AudioSegment.from_mp3(path)
    if suffix == ".ogg":
        return AudioSegment.from_ogg(path)
    return AudioSegment.from_file(path)


def synth_from_note(note: dict, bpm: float) -> AudioSegment:
    pitch = parse_note_name(note["note"])
    freq = 440.0 * (2 ** ((pitch - 69) / 12.0))
    duration = note_length_ms(note["length"], bpm)
    velocity = int(note.get("velocity", 100))
    volume_down = max(0, 127 - velocity)
    tone = Sine(freq).to_audio_segment(duration=duration) - volume_down
    return tone - 6


def estimate_duration_ms(data: dict[str, Any]) -> int:
    bpm = float(data.get("bpm", 120))
    max_step = 0.0

    for track_key in TRACK_KEYS:
        for note in track_notes(data, track_key):
            max_step = max(max_step, float(note["time_step"]) + float(note["length"]))

    for item in data.get("samples") or []:
        max_step = max(max_step, float(item.get("time_step", 0)) + 1.0)

    max_step = max(max_step, 16.0)
    return step_to_ms(max_step, bpm) + 500


def render_preview(
    data: dict,
    samples_root: Path,
    output_path: Path = PREVIEW_FILE,
) -> Path:
    bpm = float(data.get("bpm", 120))
    mix = AudioSegment.silent(duration=estimate_duration_ms(data))

    for track_key in TRACK_KEYS:
        default_sample = find_first_sample(samples_root, TRACK_SAMPLE_DIRS.get(track_key, ()))
        for note in track_notes(data, track_key):
            start_ms = step_to_ms(note["time_step"], bpm)
            clip: AudioSegment | None = None

            sample_ref = note.get("sample")
            sample_path = samples_root / sample_ref if sample_ref else None
            if sample_path and sample_path.is_file():
                clip = load_clip(sample_path)
            elif default_sample:
                clip = load_clip(default_sample)
            else:
                clip = synth_from_note(note, bpm)

            clip = clip[: note_length_ms(note["length"], bpm)]
            mix = mix.overlay(clip, position=start_ms)

    for item in data.get("samples") or []:
        rel = item.get("file")
        if not rel:
            continue
        path = samples_root / rel
        if not path.is_file():
            continue
        start_ms = step_to_ms(item["time_step"], bpm)
        clip = load_clip(path)
        mix = mix.overlay(clip, position=start_ms)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    mix.export(output_path, format="wav")
    return output_path


def render_from_json(
    json_path: Path = DEFAULT_JSON,
    samples_root: Path | None = None,
    output_path: Path = PREVIEW_FILE,
) -> Path:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    root = Path(samples_root or data.get("sample_library") or PROJECT_DIR / "PLG_Sounds")
    return render_preview(data, root.resolve(), output_path)
