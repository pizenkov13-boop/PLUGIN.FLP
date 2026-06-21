#!/usr/bin/env python3
"""
PLG PLUGIN.FLP — внешнее ИИ-ядро (File Bridge: prompt -> output_pattern.json).

Модуль 1: промпт + папка сэмплов -> JSON для FL Studio.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

from sample_catalog import format_catalog_for_prompt, save_catalog, scan_samples_directory

MODEL = "gemini-2.5-flash"
PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = PROJECT_DIR / "output_pattern.json"
CATALOG_FILE = PROJECT_DIR / "sample_catalog.json"
ENV_FILE = PROJECT_DIR / ".env"
USER_PROFILE_FILE = PROJECT_DIR / "user_profile.json"
DEFAULT_SAMPLES_DIR = PROJECT_DIR / "PLG_Sounds"
SAMPLE_SUBDIRS = ("808", "hats", "textures", "melodies", "fx", "vocal_presets", "kits")

NOTE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["time_step", "note", "length", "velocity"],
    "properties": {
        "time_step": {"type": "number"},
        "note": {"type": "string"},
        "length": {"type": "number"},
        "velocity": {"type": "integer", "minimum": 0, "maximum": 127},
        "sample": {"type": "string"},
    },
}

SAMPLE_LAYER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["file", "track", "time_step"],
    "properties": {
        "file": {"type": "string"},
        "track": {
            "type": "string",
            "enum": ["hi_hats", "sub_808", "melody_lead", "textures", "fx"],
        },
        "time_step": {"type": "number"},
        "note": {"type": "string"},
        "velocity": {"type": "integer", "minimum": 0, "maximum": 127},
    },
}

RESPONSE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["bpm", "tracks", "build_order"],
    "properties": {
        "bpm": {"type": "number"},
        "style": {"type": "string"},
        "build_order": {
            "type": "array",
            "items": {"type": "string"},
        },
        "tracks": {
            "type": "object",
            "required": ["melody_lead", "sub_808", "hi_hats"],
            "properties": {
                "melody_lead": {"type": "array", "items": NOTE_SCHEMA},
                "sub_808": {"type": "array", "items": NOTE_SCHEMA},
                "hi_hats": {"type": "array", "items": NOTE_SCHEMA},
            },
        },
        "samples": {
            "type": "array",
            "items": SAMPLE_LAYER_SCHEMA,
        },
        "fx_automation": {
            "type": "object",
            "properties": {
                "Fruity_Fast_Dist": {
                    "type": "object",
                    "properties": {
                        "drive": {"type": "number"},
                        "mix": {"type": "number"},
                    },
                },
                "Fruity_WaveShaper": {
                    "type": "object",
                    "properties": {
                        "boost": {"type": "number"},
                    },
                },
                "Channel_Precomputed": {
                    "type": "object",
                    "properties": {
                        "boost": {"type": "number"},
                    },
                },
            },
        },
        "vocal_fx": {
            "type": "object",
            "properties": {
                "reference": {"type": "string"},
                "pitch_correction": {"type": "string"},
                "autotune_retune": {"type": "number"},
                "reverb": {"type": "string"},
                "delay": {"type": "string"},
            },
        },
        "manual_steps": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
}

SYSTEM_INSTRUCTION_BASE = """\
Ты — главный ИИ-движок PLUGIN.FLP (PLG). Переводи любой промпт в JSON для FL Studio.

Порядок сборки (build_order) — всегда указывай массив шагов, например:
["hi_hats", "sub_808", "melody_lead", "samples", "fx_automation", "vocal_fx"]

tracks — три MIDI-дорожки:
1) hi_hats — ритм, rolls, time_step 0.25
2) sub_808 — бас по root notes, velocity 127
3) melody_lead — мелодия/аккорды под стиль промпта

Если передан sample catalog — выбирай РЕАЛЬНЫЕ файлы из списка:
- samples[]: file (relative path), track, time_step, optional note/velocity
- в notes можно добавить поле "sample" для привязки wav к ноте
- 808 из папки 808/, textures/noise/buzz из textures/, hats из hats/

FX — при dist/opium/ken carson:
Channel_Precomputed boost=0.30, Fruity_Fast_Dist drive=0.90 mix=1.0, Fruity_WaveShaper boost=0.40

vocal_fx — если промпт про вокал/autotune/weeknd/travis (НЕ AI-голос, только FX на голос юзера):
reference, pitch_correction (soft/hard), autotune_retune, reverb, delay

manual_steps — если что-то нельзя автоматизировать, дай 2-5 коротких шагов под версию FL из профиля.

Любой стиль: opium, pop, drill, grind, anti-music, dua lipa — адаптируй всё под промпт.
4-8 тактов. Только чистый JSON.\
"""


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | PLG.PLUGIN.FLP | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def load_environment() -> None:
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)
        logging.info("Загружен .env: %s", ENV_FILE)
    else:
        load_dotenv()


def get_api_key() -> str:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError(f"Создайте {ENV_FILE} с GEMINI_API_KEY=...")
    return api_key


def resolve_samples_dir(cli_path: str | None) -> Path:
    raw = cli_path or os.environ.get("PLG_SAMPLES_DIR") or str(DEFAULT_SAMPLES_DIR)
    return Path(raw).expanduser().resolve()


def ensure_samples_library(samples_dir: Path) -> None:
    """Create user sample folder layout on first run."""
    samples_dir.mkdir(parents=True, exist_ok=True)
    for name in SAMPLE_SUBDIRS:
        (samples_dir / name).mkdir(exist_ok=True)

    print("")
    print("PLG Sample Library")
    print(f"  Folder: {samples_dir}")
    print("  Drop kits here:")
    print("    808/  hats/  textures/  melodies/  kits/  fx/  vocal_presets/")
    print("  FL Mafia, Splice, own packs — any .wav/.mp3 works.")
    print("  Set another path in .env -> PLG_SAMPLES_DIR=...")
    print("")


def load_user_profile() -> dict[str, str]:
    if USER_PROFILE_FILE.exists():
        data = json.loads(USER_PROFILE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {
                "fl_version": str(data.get("fl_version", "24")),
                "fl_edition": str(data.get("fl_edition", "producer")),
                "os": str(data.get("os", "windows")),
            }
    return {"fl_version": "24", "fl_edition": "producer", "os": "windows"}


def build_system_instruction(profile: dict[str, str], catalog: dict | None) -> str:
    parts = [SYSTEM_INSTRUCTION_BASE, "", "FL user profile:"]
    parts.append(json.dumps(profile, ensure_ascii=False))
    if catalog and catalog.get("total", 0) > 0:
        parts.extend(["", "SAMPLE CATALOG:", format_catalog_for_prompt(catalog)])
    else:
        parts.append("\nSample catalog empty — use MIDI notes only, samples[] can be omitted.")
    return "\n".join(parts)


def read_prompt(cli_prompt: str | None) -> str:
    if cli_prompt and cli_prompt.strip():
        return cli_prompt.strip()
    logging.info("Ожидание промпта...")
    prompt = input("PLUGIN.FLP > ").strip()
    if not prompt:
        raise ValueError("Промпт не может быть пустым.")
    return prompt


def count_track_notes(data: dict[str, Any]) -> int:
    tracks = data.get("tracks", {})
    if isinstance(tracks, dict):
        return sum(len(tracks.get(name, [])) for name in ("melody_lead", "sub_808", "hi_hats"))
    return 0


def generate_pattern(
    client: genai.Client,
    prompt: str,
    system_instruction: str,
) -> dict[str, Any]:
    logging.info("Gemini (%s)...", MODEL)

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_json_schema=RESPONSE_JSON_SCHEMA,
            temperature=0.85,
        ),
    )

    raw_text = response.text
    if not raw_text or not raw_text.strip():
        raise RuntimeError("Gemini вернул пустой ответ.")

    data = json.loads(raw_text)
    if not isinstance(data, dict) or "tracks" not in data:
        raise RuntimeError("Ожидался JSON с bpm, tracks, build_order.")

    logging.info(
        "BPM=%s | style=%s | notes=%s | samples=%s | fx=%s | vocal=%s",
        data.get("bpm"),
        data.get("style", "n/a"),
        count_track_notes(data),
        len(data.get("samples") or []),
        "yes" if data.get("fx_automation") else "no",
        "yes" if data.get("vocal_fx") else "no",
    )
    return data


def save_pattern(data: dict[str, Any], output_path: Path = OUTPUT_FILE) -> None:
    logging.info("File Bridge -> %s", output_path)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_pipeline(
    prompt: str,
    samples_dir: Path | None = None,
    *,
    export_midi: bool = True,
) -> dict[str, Any]:
    """Main generation pipeline for CLI and GUI."""
    load_environment()
    resolved_samples = resolve_samples_dir(str(samples_dir) if samples_dir else None)
    ensure_samples_library(resolved_samples)

    catalog = scan_samples_directory(resolved_samples)
    save_catalog(catalog, CATALOG_FILE)
    logging.info("Catalog: %s files", catalog["total"])

    if catalog["total"] == 0:
        logging.warning("Sample folder empty — MIDI-only mode until kits are added")

    profile = load_user_profile()
    system_instruction = build_system_instruction(profile, catalog)
    client = genai.Client(api_key=get_api_key())
    pattern = generate_pattern(client, prompt, system_instruction)
    pattern["sample_library"] = catalog["root"]
    save_pattern(pattern)

    if export_midi:
        from midi_export import export_pattern_to_midi

        paths = export_pattern_to_midi(pattern)
        logging.info("MIDI exported: %s files -> output_midi/", len(paths))

    from guide_export import export_build_guide

    export_build_guide(pattern)
    logging.info("Build guide -> build_guide.txt")

    try:
        from preview_wav import render_preview

        preview = render_preview(pattern, resolved_samples)
        logging.info("Preview WAV -> %s", preview)
    except Exception as exc:
        logging.warning("Preview WAV skipped: %s", exc)

    return pattern


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PLG PLUGIN.FLP backend core")
    parser.add_argument("-p", "--prompt", type=str, help="Music prompt")
    parser.add_argument(
        "-s",
        "--samples-dir",
        type=str,
        help="Folder with 808/hats/textures (FL Mafia downloads, etc.)",
    )
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help="Only scan sample folder and write sample_catalog.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    setup_logging()
    logging.info("PLUGIN.FLP backend core")

    try:
        load_environment()
        samples_dir = resolve_samples_dir(args.samples_dir)
        ensure_samples_library(samples_dir)

        catalog = scan_samples_directory(samples_dir)
        save_catalog(catalog, CATALOG_FILE)
        logging.info("Catalog: %s files -> %s", catalog["total"], CATALOG_FILE)

        if args.scan_only:
            return 0

        prompt = read_prompt(args.prompt)
        run_pipeline(prompt, samples_dir)
        logging.info("Done: %s", OUTPUT_FILE)
        logging.info("FL: Piano roll -> Scripts -> PLG PLUGIN.FLP")
        return 0

    except EnvironmentError as exc:
        logging.error("Config: %s", exc)
        return 1
    except ValueError as exc:
        logging.error("Input: %s", exc)
        return 1
    except RuntimeError as exc:
        logging.error("API: %s", exc)
        return 1
    except Exception as exc:
        logging.exception("Error: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
