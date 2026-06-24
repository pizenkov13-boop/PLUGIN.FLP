"""FL Studio mixing blueprint — READ_ME_IMBA.txt for every generated beat."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from mix_blueprint_i18n import blueprint_text

PROJECT_DIR = Path(__file__).resolve().parent
BLUEPRINT_FILE = PROJECT_DIR / "READ_ME_IMBA.txt"


def _style_bucket(data: dict[str, Any]) -> str:
    tags = data.get("plg_style_tags")
    if isinstance(tags, list):
        joined = " ".join(str(t) for t in tags).lower()
        if "rage" in joined or "dark trap" in joined:
            return "rage"
        if "phonk" in joined:
            return "phonk"
        if "atmospheric" in joined:
            return "atmospheric"
    text = f"{data.get('style', '')} {data.get('user_prompt', '')}".lower()
    if any(k in text for k in ("rage", "dark trap", "underground", "plugg", "jerk")):
        return "rage"
    if any(k in text for k in ("phonk", "drift", "memphis", "cowbell")):
        return "phonk"
    if any(k in text for k in ("atmospheric", "ambient trap", "cinematic")):
        return "atmospheric"
    if any(k in text for k in ("country", "кантри")):
        return "country"
    return "trap"


def _bpm_line(bpm: float, bucket: str, locale: str) -> str:
    if bucket == "rage":
        return blueprint_text(locale, "bpm_opium", bpm=f"{bpm:.0f}")
    if bucket == "phonk":
        return blueprint_text(locale, "bpm_phonk", bpm=f"{bpm:.0f}")
    return blueprint_text(locale, "bpm_trap", bpm=f"{bpm:.0f}")


def _channel_block(data: dict[str, Any], bucket: str, locale: str) -> list[str]:
    meta = data.get("plg_producer_meta") if isinstance(data.get("plg_producer_meta"), dict) else {}
    picks = data.get("plg_sample_picks") if isinstance(data.get("plg_sample_picks"), dict) else {}
    lines: list[str] = []

    kick_name = picks.get("kick", "kick")
    lines.extend([
        f"KICK ({kick_name})",
        f"  • {blueprint_text(locale, 'kick_line')}",
        f"  • {blueprint_text(locale, 'kick_bus')}",
        "",
    ])

    snare_name = picks.get("snare", "snare")
    lines.extend([
        f"SNARE ({snare_name})",
        f"  • {blueprint_text(locale, 'snare_line')}",
        f"  • {blueprint_text(locale, 'snare_layer')}",
        "",
    ])

    hat_name = picks.get("hi_hats", "hats")
    rolls = data.get("plg_hat_rolls", 0)
    lines.extend([
        f"HI-HATS ({hat_name})",
        f"  • {blueprint_text(locale, 'hats_line', rolls=rolls or 'auto')}",
        f"  • {blueprint_text(locale, 'hats_pan')}",
        f"  • {blueprint_text(locale, 'hats_eq')}",
        "",
    ])

    bass_name = picks.get("sub_808", "808")
    if bucket == "rage":
        bass_fx = [
            f"808 / SUB ({bass_name})",
            f"  • {blueprint_text(locale, 'bass_opium')}",
        ]
    elif bucket == "phonk":
        bass_fx = [
            f"808 / SUB ({bass_name})",
            f"  • {blueprint_text(locale, 'bass_phonk')}",
        ]
    else:
        bass_fx = [
            f"808 / SUB ({bass_name})",
            f"  • {blueprint_text(locale, 'bass_trap')}",
        ]
    lines.extend(bass_fx)
    lines.append("")

    melody_name = picks.get("melody_lead", "lead")
    lines.extend([
        f"MELODY ({melody_name})",
        f"  • {blueprint_text(locale, 'melody_line')}",
        "",
    ])

    if meta.get("master_soft_clip") or bucket in ("rage", "phonk"):
        lines.extend([
            "MASTER",
            f"  • {blueprint_text(locale, 'master_opium')}",
            "",
        ])
    else:
        lines.extend([
            "MASTER",
            f"  • {blueprint_text(locale, 'master_trap')}",
            "",
        ])

    return lines


def _mastering_math_block(bpm: float, locale: str) -> list[str]:
    """Exact commercial mix/master targets, with reverb times derived from BPM
    (ms = 60000 / BPM). The numbers are the spec; FL is where they're applied."""
    beat_ms = 60_000.0 / max(1.0, bpm)
    predelay_ms = beat_ms / 4.0       # 1/16-note pre-delay
    bar_ms = beat_ms * 4.0            # one bar = reverb decay target
    header = (
        "МАТЕМАТИКА СВЕДЕНИЯ И МАСТЕРИНГА (применить в FL)"
        if locale == "ru"
        else "MIX & MASTER MATH (apply in FL)"
    )
    return [
        f"─── {header} ───",
        "  Peaks:  Kick -2 dB · 808 -5 dB · Clap/Snare -6 dB · Melody -12 dB · Hi-Hats -12..-15 dB",
        "  EQ:     Kick HPF <30 Hz · 808 LPF >250 Hz (vocal space) · Clap +1.5 kHz snap",
        "          Hats HPF <500 Hz · Melody HPF <150 Hz + dip 200-500 Hz & 2-4 kHz",
        "  Sidechain: 808 → Fruity Limiter (COMP) → input = Kick · Threshold ~1/2 down · Ratio up (~50 ms duck)",
        "  Mono:   everything <120 Hz strictly MONO (Fruity Stereo Shaper → 100% mono)",
        f"  Reverb @ {bpm:.0f} BPM:  beat = {beat_ms:.1f} ms · pre-delay 1/16 = {predelay_ms:.1f} ms · decay 1 bar = {bar_ms:.0f} ms",
        "  Master: Fruity Soft Clipper · Ceiling -1.0 dB (true-peak) · Dithering + noise-shaping ON",
        "          Target loudness: -7..-5 LUFS short-term (commercial trap density)",
        "",
    ]


def build_mix_blueprint(data: dict[str, Any], *, stem_folder: str | None = None) -> str:
    """Producer-style mixing cheat sheet for the generated beat."""
    bpm = float(data.get("bpm", 140))
    style = str(data.get("style", "unknown"))
    bucket = _style_bucket(data)
    prompt = str(data.get("user_prompt", ""))[:120]
    locale = str(data.get("plg_locale") or "en")

    lines = [
        "═══════════════════════════════════════════════════════════",
        f"  {blueprint_text(locale, 'title')}",
        "═══════════════════════════════════════════════════════════",
        "",
        f"{blueprint_text(locale, 'track')}: {style}",
        _bpm_line(bpm, bucket, locale),
        f"{blueprint_text(locale, 'prompt')}: {prompt}" if prompt else "",
        "",
        f"─── {blueprint_text(locale, 'stems_header')} ───",
    ]

    if stem_folder:
        lines.extend([
            f"{blueprint_text(locale, 'stems_folder')}: {stem_folder}",
            blueprint_text(locale, "stems_drag"),
            blueprint_text(locale, "stems_map"),
            blueprint_text(locale, "stems_or_one"),
            "",
        ])
    else:
        lines.extend([
            blueprint_text(locale, "stems_fallback"),
            "",
        ])

    lines.append(f"─── {blueprint_text(locale, 'channels_header')} ───")
    lines.append("")
    lines.extend(_channel_block(data, bucket, locale))

    meta = data.get("plg_producer_meta") if isinstance(data.get("plg_producer_meta"), dict) else {}
    if bucket in ("rage", "phonk") or meta.get("master_soft_clip"):
        lines.extend([
            f"─── {blueprint_text(locale, 'fx_recipe_header')} ───",
            f"  {blueprint_text(locale, 'fx_recipe_808')}",
            f"  {blueprint_text(locale, 'fx_recipe_808_alt')}",
            f"  {blueprint_text(locale, 'fx_recipe_master')}",
            f"  {blueprint_text(locale, 'fx_recipe_kick')}",
            "",
        ])

    lines.extend(_mastering_math_block(bpm, locale))

    manual = data.get("manual_steps") or []
    if manual:
        lines.extend([f"─── {blueprint_text(locale, 'plg_done')} ───", ""])
        lines.extend(f"  • {step}" for step in manual[:8])
        lines.append("")

    fx = data.get("fx_automation")
    if fx:
        lines.extend([f"─── {blueprint_text(locale, 'fx_header')} ───", json.dumps(fx, ensure_ascii=False, indent=2), ""])

    lines.extend([
        f"─── {blueprint_text(locale, 'scripts_header')} ───",
        f"  {blueprint_text(locale, 'scripts_hint')}",
        "",
        blueprint_text(locale, "footer"),
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


def list_blueprint_steps(data: dict[str, Any], locale: str | None = None) -> list[dict[str, str]]:
    """Interactive producer checklist for the web UI."""
    loc = locale or "en"
    steps: list[dict[str, str]] = []
    meta = data.get("plg_producer_meta") if isinstance(data.get("plg_producer_meta"), dict) else {}

    if data.get("plg_filth_mode") or meta.get("master_soft_clip"):
        steps.append({
            "id": "filth-master",
            "text": blueprint_text(loc, "step_filth_master"),
        })
        steps.append({
            "id": "filth-808",
            "text": blueprint_text(loc, "step_filth_808"),
        })

    steps.append({
        "id": "pre-snare",
        "text": blueprint_text(loc, "step_pre_snare"),
    })
    steps.append({
        "id": "hat-6db",
        "text": blueprint_text(loc, "step_hat_6db"),
    })
    steps.append({
        "id": "hat-choke",
        "text": blueprint_text(loc, "step_hat_choke"),
    })
    steps.append({
        "id": "808-attack",
        "text": blueprint_text(loc, "step_808_attack"),
    })
    steps.append({
        "id": "sidechain",
        "text": blueprint_text(loc, "step_sidechain"),
    })
    steps.append({
        "id": "stems",
        "text": blueprint_text(loc, "step_stems"),
    })

    for index, line in enumerate(data.get("manual_steps") or []):
        steps.append({"id": f"manual-{index}", "text": str(line)})

    if data.get("pitch_bend_automation"):
        steps.append({
            "id": "pitch-bend",
            "text": blueprint_text(loc, "step_pitch_bend"),
        })

    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for step in steps:
        key = step["text"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(step)
    return unique[:24]
