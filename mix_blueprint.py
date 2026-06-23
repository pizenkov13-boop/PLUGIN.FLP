"""FL Studio mixing blueprint — READ_ME_IMBA.txt for every generated beat."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pattern_utils import TRACK_KEYS, TRACK_LABELS, track_notes

PROJECT_DIR = Path(__file__).resolve().parent
BLUEPRINT_FILE = PROJECT_DIR / "READ_ME_IMBA.txt"


def _style_bucket(data: dict[str, Any]) -> str:
    text = f"{data.get('style', '')} {data.get('user_prompt', '')}".lower()
    if any(k in text for k in ("opium", "f1lthy", "ken", "carson", "rage", "destroy", "lonely")):
        return "opium"
    if any(k in text for k in ("phonk", "drift", "memphis", "cowbell")):
        return "phonk"
    if any(k in text for k in ("travis", "metro", "atmospheric")):
        return "metro"
    if any(k in text for k in ("country", "кантри")):
        return "country"
    return "trap"


def _bpm_line(bpm: float, bucket: str) -> str:
    if bucket == "opium":
        return f"BPM {bpm:.0f} — rage pocket. Не трогай темп, Carti/Ken сидят на 145–165."
    if bucket == "phonk":
        return f"BPM {bpm:.0f} — phonk drift. Держи swing на хэтах, бас моно."
    return f"BPM {bpm:.0f} — trap / melodic. Сведи так, чтобы под вокал осталось место."


def _channel_block(data: dict[str, Any], bucket: str) -> list[str]:
    meta = data.get("plg_producer_meta") if isinstance(data.get("plg_producer_meta"), dict) else {}
    picks = data.get("plg_sample_picks") if isinstance(data.get("plg_sample_picks"), dict) else {}
    lines: list[str] = []

    kick_name = picks.get("kick", "kick")
    lines.extend([
        f"KICK ({kick_name})",
        "  • Channel rack → Fruity Limiter (ceiling) или лёгкий EQ: cut ниже 30 Hz.",
        "  • Mixer: route на Drum bus, -3 dB headroom до клипа.",
        "",
    ])

    snare_name = picks.get("snare", "snare")
    lines.extend([
        f"SNARE ({snare_name})",
        "  • Fruity Reverb 2 — 8% wet, pre-delay 12 ms (только хвост, не мыло).",
        "  • Если есть Snare Layer — панорама +15% R, velocity ~40% от основного.",
        "",
    ])

    hat_name = picks.get("hi_hats", "hats")
    rolls = data.get("plg_hat_rolls", 0)
    lines.extend([
        f"HI-HATS ({hat_name})",
        f"  • PLG вставил {rolls or 'auto'} hat roll(s) перед снэром — не квантуй обратно в сетку.",
        "  • Pan: closed L50 / open R78, или Scripts → PLG Pan Spread.",
        "  • EQ: high-pass 6 kHz+ на открытых, чтобы не резало ухо.",
        "",
    ])

    bass_name = picks.get("sub_808", "808")
    if bucket == "opium":
        bass_fx = [
            f"808 / SUB ({bass_name}) — ГЛАВНЫЙ КАНАЛ",
            "  • Бро, на этот 808 накинь Blood Overdrive ~15% (или Fruity Fast Dist drive 88%).",
            "  • WaveShaper boost ~38%, потом Fruity Parametric EQ 2: low shelf +2 dB @ 60 Hz.",
            "  • Cut Itself / mono legato уже в MIDI — не overlap в Piano Roll.",
            "  • Sidechain: duck 808 до ~40% на каждый kick (см. plg_producer_meta.sidechain).",
        ]
    elif bucket == "phonk":
        bass_fx = [
            f"808 / SUB ({bass_name})",
            "  • Fruity Blood Overdrive + Soft Clipper на канале 808.",
            "  • Cowbell / layer если есть — отдельный канал, -6 dB.",
        ]
    else:
        bass_fx = [
            f"808 / SUB ({bass_name})",
            "  • Fruity Fast Dist лёгкий drive, low-cut 25 Hz на канале.",
            "  • Glide между корнями: Piano roll → Scripts → PLG 808 Glide.",
        ]
    lines.extend(bass_fx)
    lines.append("")

    melody_name = picks.get("melody_lead", "lead")
    lines.extend([
        f"MELODY ({melody_name})",
        "  • Fruity Reeverb 2 — plate, decay 1.8 s, mix 12–18%.",
        "  • EQ cut 300–450 Hz (mud), boost 8 kHz +1.5 dB для air.",
        "  • Оставь дыры каждые 2 такта — вокал сядет сюда.",
        "",
    ])

    if meta.get("master_soft_clip") or bucket in ("opium", "phonk"):
        lines.extend([
            "MASTER",
            "  • Fruity Soft Clipper на Master — Post-Gain +2…+3 dB до лёгкого касания.",
            "  • Fruity Limiter ceiling -0.3 dB, low-cut 25 Hz на мастере (см. plg_producer_meta).",
            "  • Не пережимай снэр — Opium = бас громче, верх воздушный.",
            "",
        ])
    else:
        lines.extend([
            "MASTER",
            "  • Soft clip лёгкий, LUFS разумный — оставь динамику под вокал.",
            "",
        ])

    return lines


def build_mix_blueprint(data: dict[str, Any], *, stem_folder: str | None = None) -> str:
    """Producer-style mixing cheat sheet for the generated beat."""
    bpm = float(data.get("bpm", 140))
    style = str(data.get("style", "unknown"))
    bucket = _style_bucket(data)
    prompt = str(data.get("user_prompt", ""))[:120]

    lines = [
        "═══════════════════════════════════════════════════════════",
        "  PLG — READ_ME_IMBA.txt  |  FL Studio Blueprint",
        "═══════════════════════════════════════════════════════════",
        "",
        f"Track: {style}",
        _bpm_line(bpm, bucket),
        f"Prompt: {prompt}" if prompt else "",
        "",
        "─── DRAG & DROP STEMS ───",
    ]

    if stem_folder:
        lines.extend([
            f"Папка: {stem_folder}",
            "Перетащи каждый .mid на свой канал микшера:",
            "  Kick.mid → Kick  |  Snare.mid → Snare  |  808_Bass.mid → 808",
            "  HiHats.mid → Hats  |  Melody.mid → Lead",
            "Или один PLG_Beat.mid если лень — но stems = чистый микс.",
            "",
        ])
    else:
        lines.extend([
            "Смотри output_midi/ — отдельные дорожки Kick, Snare, 808_Bass, HiHats, Melody.",
            "",
        ])

    lines.append("─── КАНАЛЫ (как у F1LTHY / Star Boy) ───")
    lines.append("")
    lines.extend(_channel_block(data, bucket))

    manual = data.get("manual_steps") or []
    if manual:
        lines.extend(["─── PLG УЖЕ СДЕЛАЛ ───", ""])
        lines.extend(f"  • {step}" for step in manual[:8])
        lines.append("")

    fx = data.get("fx_automation")
    if fx:
        lines.extend(["─── FX AUTOMATION (из паттерна) ───", json.dumps(fx, ensure_ascii=False, indent=2), ""])

    lines.extend([
        "─── FL SCRIPTS ───",
        "  Piano roll → Scripts → PLG: Hat Roll, 808 Glide, Pan Spread",
        "",
        "Удачи. Звучи как будто платишь F1LTHY $5k за сведение.",
        "═══════════════════════════════════════════════════════════",
    ])
    return "\n".join(line for line in lines if line is not None)


def export_mix_blueprint(
    data: dict[str, Any],
    output_path: Path = BLUEPRINT_FILE,
    *,
    stem_folder: str | None = None,
) -> Path:
    text = build_mix_blueprint(data, stem_folder=stem_folder)
    output_path.write_text(text + "\n", encoding="utf-8")
    return output_path


def session_slug(data: dict[str, Any]) -> str:
    bpm = int(float(data.get("bpm", 140)))
    raw = re.sub(r"[^\w\s-]", "", str(data.get("style", "beat")).lower())
    slug = re.sub(r"\s+", "_", raw.strip())[:28] or "beat"
    return f"PLG_Stems_{bpm}bpm_{slug}"
