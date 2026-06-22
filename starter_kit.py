"""PLG starter sound pack — bundled with the app, optional CC0 upgrade."""

from __future__ import annotations

import json
import logging
import math
import shutil
import struct
import wave
import zipfile
from pathlib import Path
from typing import Any

from library_paths import AUDIO_EXTENSIONS, DEFAULT_LIBRARY_DIR
from plg_paths import starter_bundle_dir, starter_runtime_dir

BUNDLE_VERSION = 1

TRACK_STARTER_FILES = {
    "hi_hats": "PLG_starter_hat.wav",
    "sub_808": "PLG_starter_808.wav",
    "melody_lead": "PLG_starter_melody.wav",
}

TRACK_SEARCH_FOLDERS = {
    "hi_hats": ("hats", "kits", "splice"),
    "sub_808": ("808", "kits"),
    "melody_lead": ("melodies", "kits", "splice"),
}

CHANNEL_LABELS = {
    "hi_hats": "PLG Hi-Hats",
    "sub_808": "PLG Sub 808",
    "melody_lead": "PLG Melody / Lead",
}

CC0_SOURCES = {
    "trap_vault": "https://signaturesounds.org/store/p/trap-vault-drum-loops",
    "kick_drums": "https://signaturesounds.org/store/p/multi-genre-kick-drums",
    "grand_piano": "https://signaturesounds.org/store/p/grand-piano-loopsand-midi",
}


def _starter_dir() -> Path:
    return starter_runtime_dir()


def _incoming_dir() -> Path:
    path = _starter_dir() / "incoming"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_dir() -> Path:
    path = _starter_dir() / "_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _manifest_file() -> Path:
    return _starter_dir() / "starter_manifest.json"


def _license_file() -> Path:
    return _starter_dir() / "LICENSE_CC0.txt"


def _write_wav_mono(path: Path, samples: list[float], sample_rate: int = 44100) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        for value in samples:
            clamped = max(-1.0, min(1.0, value))
            handle.writeframes(struct.pack("<h", int(clamped * 32767)))


def _soft_clip(value: float, drive: float = 2.2) -> float:
    return math.tanh(value * drive) / math.tanh(drive)


def _synth_808(sample_rate: int = 44100, duration: float = 0.62) -> list[float]:
    total = int(sample_rate * duration)
    out: list[float] = []
    for i in range(total):
        t = i / sample_rate
        progress = min(1.0, t / duration)
        freq = 62 * (1.0 - 0.62 * progress) + 28
        body = math.sin(2 * math.pi * freq * t)
        click = math.sin(2 * math.pi * 180 * t) * math.exp(-90 * t) * 0.35
        env = math.exp(-2.4 * t) * (1.0 - progress * 0.12)
        out.append(_soft_clip((body * 0.95 + click) * env, drive=2.8))
    return out


def _synth_hat(sample_rate: int = 44100, duration: float = 0.055) -> list[float]:
    import random

    random.seed(808)
    total = int(sample_rate * duration)
    out: list[float] = []
    for i in range(total):
        t = i / sample_rate
        noise = random.uniform(-1, 1)
        tone = math.sin(2 * math.pi * 9200 * t) * 0.15
        env = math.exp(-70 * t)
        out.append(_soft_clip((noise * 0.75 + tone) * env * 0.55, drive=1.8))
    return out


def _synth_melody_pluck(sample_rate: int = 44100, duration: float = 0.45) -> list[float]:
    total = int(sample_rate * duration)
    freqs = (440.0, 660.0, 880.0)
    out: list[float] = []
    for i in range(total):
        t = i / sample_rate
        env = math.exp(-7.5 * t)
        value = sum(math.sin(2 * math.pi * freq * t) * weight for freq, weight in zip(freqs, (0.55, 0.3, 0.15)))
        out.append(_soft_clip(value * env * 0.42, drive=1.6))
    return out


def _write_manifest(source: str, paths: dict[str, Path]) -> None:
    _manifest_file().write_text(
        json.dumps(
            {"source": source, "bundle_version": BUNDLE_VERSION, "files": {k: str(v) for k, v in paths.items()}},
            indent=2,
        ),
        encoding="utf-8",
    )


def _existing_paths() -> dict[str, Path] | None:
    paths = {
        track: (_starter_dir() / filename).resolve()
        for track, filename in TRACK_STARTER_FILES.items()
        if (_starter_dir() / filename).is_file()
    }
    if len(paths) == len(TRACK_STARTER_FILES):
        return paths
    return None


def _seed_from_bundle() -> dict[str, Path] | None:
    """Copy shipped starter wavs into the runtime folder (first run / after install)."""
    bundled = starter_bundle_dir()
    runtime = _starter_dir()
    manifest = _manifest_file()
    if manifest.is_file():
        try:
            if json.loads(manifest.read_text(encoding="utf-8")).get("source") == "signature_sounds_cc0":
                return _existing_paths()
        except (OSError, json.JSONDecodeError):
            pass

    copied = False
    for filename in TRACK_STARTER_FILES.values():
        src = bundled / filename
        dest = runtime / filename
        if src.is_file() and not dest.is_file():
            shutil.copy2(src, dest)
            copied = True

    if bundled.joinpath("BUNDLED.json").is_file() and not (runtime / "BUNDLED.json").is_file():
        shutil.copy2(bundled / "BUNDLED.json", runtime / "BUNDLED.json")

    if copied:
        paths = _existing_paths()
        if paths:
            logging.info("Installed bundled PLG starter sounds to %s", runtime)
            _write_manifest("plg_bundled", paths)
            return paths
    return _existing_paths()


def _ensure_synthetic_starter() -> dict[str, Path]:
    runtime = _starter_dir()
    generators = {
        "hi_hats": lambda: _write_wav_mono(runtime / TRACK_STARTER_FILES["hi_hats"], _synth_hat()),
        "sub_808": lambda: _write_wav_mono(runtime / TRACK_STARTER_FILES["sub_808"], _synth_808()),
        "melody_lead": lambda: _write_wav_mono(runtime / TRACK_STARTER_FILES["melody_lead"], _synth_melody_pluck()),
    }
    paths: dict[str, Path] = {}
    for track, filename in TRACK_STARTER_FILES.items():
        path = runtime / filename
        if not path.is_file():
            logging.info("Creating PLG synth starter: %s", path.name)
            generators[track]()
        paths[track] = path.resolve()
    _write_manifest("plg_synth", paths)
    return paths


def _write_cc0_license() -> None:
    _license_file().write_text(
        "\n".join(
            [
                "PLG Starter Sound Pack — CC0 upgrade",
                "",
                f"  Trap Vault:  {CC0_SOURCES['trap_vault']}",
                f"  Kick Drums:  {CC0_SOURCES['kick_drums']}",
                f"  Grand Piano: {CC0_SOURCES['grand_piano']}",
                "",
                "Optional: run install_starter_sounds.bat and drop zips in incoming/",
            ]
        ),
        encoding="utf-8",
    )


def _score_name(name: str, keywords: tuple[str, ...]) -> tuple[int, int]:
    lower = name.lower()
    return sum(10 for keyword in keywords if keyword in lower), -len(lower)


def _pick_wav(root: Path, keywords: tuple[str, ...]) -> Path | None:
    files = list(root.rglob("*.wav"))
    if not files:
        return None
    return max(files, key=lambda path: _score_name(path.name, keywords))


def _extract_incoming_zips() -> dict[str, Path]:
    extracted: dict[str, Path] = {}
    for zip_path in sorted(_incoming_dir().glob("*.zip")):
        key = zip_path.stem.lower().replace(" ", "_")
        if "trap" in key or "vault" in key:
            bucket = "trap_vault"
        elif "kick" in key:
            bucket = "kick_drums"
        elif "piano" in key or "grand" in key:
            bucket = "grand_piano"
        else:
            continue
        out_dir = _cache_dir() / bucket
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(out_dir)
        extracted[bucket] = out_dir
        logging.info("Extracted %s -> %s", zip_path.name, out_dir)
    return extracted


def install_from_incoming_zips() -> dict[str, Path] | None:
    extracted = _extract_incoming_zips()
    if not extracted:
        return None

    hat_src = _pick_wav(extracted.get("trap_vault", _starter_dir()), ("hat", "hihat", "hi-hat", "hh", "loop"))
    kick_src = _pick_wav(extracted.get("kick_drums", _starter_dir()), ("808", "trap", "sub", "kick"))
    if kick_src is None and "trap_vault" in extracted:
        kick_src = _pick_wav(extracted["trap_vault"], ("808", "kick", "bass", "loop"))
    melody_src = _pick_wav(extracted["grand_piano"], ("piano", "key", "loop", "pluck")) if "grand_piano" in extracted else None

    mapping = {"hi_hats": hat_src, "sub_808": kick_src, "melody_lead": melody_src}
    if any(value is None for value in mapping.values()):
        logging.warning("Incoming zips incomplete — need trap + kick + piano packs")
        return None

    runtime = _starter_dir()
    installed: dict[str, Path] = {}
    for track, src in mapping.items():
        assert src is not None
        dest = runtime / TRACK_STARTER_FILES[track]
        shutil.copy2(src, dest)
        installed[track] = dest.resolve()
        logging.info("Installed CC0 starter %s <- %s", dest.name, src.name)

    _write_manifest("signature_sounds_cc0", installed)
    _write_cc0_license()
    return installed


def ensure_starter_kit() -> dict[str, Path]:
    """Bundled starter (default) → optional CC0 zips → synth fallback."""
    cc0 = install_from_incoming_zips()
    if cc0:
        return cc0

    manifest = _manifest_file()
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            if data.get("source") == "signature_sounds_cc0":
                paths = _existing_paths()
                if paths:
                    return paths
        except (OSError, json.JSONDecodeError, ValueError):
            pass

    bundled = _seed_from_bundle()
    if bundled:
        return bundled

    return _ensure_synthetic_starter()


def _first_audio_in_folders(library_root: Path, folders: tuple[str, ...]) -> Path | None:
    for folder in folders:
        base = library_root / folder
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix.lower() in AUDIO_EXTENSIONS:
                return path.resolve()
    return None


def resolve_track_samples(
    catalog: dict[str, Any] | None,
    *,
    library_root: Path | None = None,
) -> dict[str, Path]:
    starter = ensure_starter_kit()
    root = Path(library_root or (catalog or {}).get("root") or DEFAULT_LIBRARY_DIR)
    if isinstance(root, str):
        root = Path(root)

    chosen: dict[str, Path] = {}
    for track, folders in TRACK_SEARCH_FOLDERS.items():
        user_path = _first_audio_in_folders(root, folders)
        chosen[track] = user_path if user_path else starter[track]
    return chosen


def build_samples_layer(sound_map: dict[str, Path]) -> list[dict[str, Any]]:
    return [
        {
            "file": str(path),
            "track": track,
            "time_step": 0.0,
            "note": "C4",
            "velocity": 127 if track == "sub_808" else 100,
        }
        for track, path in sound_map.items()
    ]


def build_manual_steps(sound_map: dict[str, Path], *, used_starter: bool) -> list[str]:
    steps = []
    for track, path in sound_map.items():
        label = CHANNEL_LABELS[track]
        if used_starter:
            steps.append(f"FL loaded starter sound on {label}: {path.name} (replace with your wav anytime)")
        else:
            steps.append(f"Drag {path.name} onto channel {label} if FL did not auto-load it")
    if used_starter:
        steps.append("Press Play — starter pack is ready. Swap samples in Channel rack for your sound.")
    return steps


def attach_sounds_to_pattern(
    pattern: dict[str, Any],
    catalog: dict[str, Any] | None,
    *,
    library_root: Path | None = None,
) -> dict[str, Path]:
    sound_map = resolve_track_samples(catalog, library_root=library_root)
    user_audio = int((catalog or {}).get("audio_total", 0) or 0) > 0
    pattern["plg_sound_paths"] = {track: str(path) for track, path in sound_map.items()}
    pattern["samples"] = build_samples_layer(sound_map)
    pattern["starter_mode"] = not user_audio
    pattern["manual_steps"] = build_manual_steps(sound_map, used_starter=not user_audio)
    pattern["sample_library"] = str(library_root or DEFAULT_LIBRARY_DIR)
    return sound_map


def starter_kit_info() -> dict[str, Any]:
    paths = ensure_starter_kit()
    source = "unknown"
    manifest = _manifest_file()
    if manifest.is_file():
        try:
            source = json.loads(manifest.read_text(encoding="utf-8")).get("source", source)
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "dir": str(_starter_dir().resolve()),
        "bundle_dir": str(starter_bundle_dir().resolve()),
        "source": source,
        "bundled": source in {"plg_bundled", "plg_synth", "signature_sounds_cc0"},
        "incoming_dir": str(_incoming_dir().resolve()),
        "cc0_sources": CC0_SOURCES,
        "files": {track: str(path) for track, path in paths.items()},
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(starter_kit_info(), indent=2))
