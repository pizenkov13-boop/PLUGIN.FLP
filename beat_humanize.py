"""F1LTHY / Opium producer brain — deterministic MIDI humanization after the LLM."""

from __future__ import annotations

import hashlib
import logging
import math
import random
import re
from copy import deepcopy
from typing import Any

from pattern_utils import TRACK_KEYS, parse_note_name, track_notes

logger = logging.getLogger("plg.humanize")

BEATS_PER_BAR = 4.0
PPQ_SWING_MIN = 3 / 96.0
PPQ_SWING_MAX = 7 / 96.0
PHASE_DELAY_BEATS = 0.008
DROP_GAP_START = 3.5
PRE_SNARE_SHIFT_MS = (2.0, 5.0)
ATTACK_FLATTEN_MS = 12.0
HAT_DB_DOWN = 6.0  # Rule 25 — hats ~6 dB below clap/snare
VELOCITY_DB_FACTOR = 10 ** (-HAT_DB_DOWN / 20.0)
PITCH_BEND_PHRASE_BARS = 8


def _rng_for(pattern: dict[str, Any]) -> random.Random:
    seed_src = f"{pattern.get('user_prompt', '')}|{pattern.get('bpm', '')}|{pattern.get('style', '')}"
    digest = hashlib.sha256(seed_src.encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _note_step(entry: dict[str, Any]) -> float:
    return float(entry.get("time_step", 0))


def _note_end(entry: dict[str, Any]) -> float:
    return _note_step(entry) + float(entry.get("length", 0.25))


def _set_velocity(entry: dict[str, Any], value: int) -> None:
    entry["velocity"] = max(1, min(127, int(value)))


def ms_to_beats(ms: float, bpm: float) -> float:
    return ms / (60_000.0 / max(1.0, bpm))


def apply_pre_snare_shift(
    notes: list[dict[str, Any]],
    bpm: float,
    rng: random.Random,
) -> list[dict[str, Any]]:
    """Rule 22 — clap/snare 2–5 ms early for Atlanta push."""
    out: list[dict[str, Any]] = []
    for entry in notes:
        note = deepcopy(entry)
        ms = rng.uniform(*PRE_SNARE_SHIFT_MS)
        note["time_step"] = round(_note_step(note) - ms_to_beats(ms, bpm), 5)
        note["pre_snare_shift_ms"] = round(ms, 2)
        out.append(note)
    return sorted(out, key=_note_step)


def apply_velocity_sine_curve(
    notes: list[dict[str, Any]],
    *,
    base: int = 100,
    amplitude: int = 22,
) -> list[dict[str, Any]]:
    """Rule 24 — sinusoidal velocity wave for percussion."""
    ordered = sorted(notes, key=_note_step)
    out: list[dict[str, Any]] = []
    total = max(1, len(ordered) - 1)
    for index, entry in enumerate(ordered):
        note = deepcopy(entry)
        phase = (index / total) * 2.0 * math.pi
        wave = math.sin(phase)
        _set_velocity(note, int(base + amplitude * wave))
        out.append(note)
    return out


def apply_six_db_hat_rule(
    hats: list[dict[str, Any]],
    reference_notes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Rule 25 — hats ~6 dB below main clap/snare velocity."""
    if not hats or not reference_notes:
        return hats
    ref_vel = max(int(n.get("velocity", 100)) for n in reference_notes)
    target = max(1, min(127, int(ref_vel * VELOCITY_DB_FACTOR)))
    out: list[dict[str, Any]] = []
    for entry in hats:
        note = deepcopy(entry)
        current = int(note.get("velocity", 100))
        _set_velocity(note, min(current, target))
        note["hat_db_rule"] = True
        out.append(note)
    return out


def _is_open_hat(entry: dict[str, Any]) -> bool:
    if entry.get("hat_type") == "open":
        return True
    length = float(entry.get("length", 0.25))
    name = str(entry.get("note", "")).lower()
    return length >= 0.35 or "open" in name


def apply_open_hat_choke(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rule 26 — closed hat cuts open hat tail (choke group)."""
    ordered = sorted((deepcopy(n) for n in notes), key=_note_step)
    closed_hits = [_note_step(n) for n in ordered if not _is_open_hat(n)]

    for entry in ordered:
        entry["choke_group"] = "plg_hats"
        if not _is_open_hat(entry):
            entry["hat_type"] = "closed"
            continue
        entry["hat_type"] = "open"
        start = _note_step(entry)
        end = _note_end(entry)
        for hit in closed_hits:
            if start < hit < end:
                entry["length"] = max(0.05, round(hit - start, 5))
                entry["choked_by"] = hit
                break
    return ordered


def apply_808_attack_flatten(
    bass_notes: list[dict[str, Any]],
    bpm: float,
) -> list[dict[str, Any]]:
    """Rule 27 — soften 808 attack so kick wins the transient."""
    delay = ms_to_beats(ATTACK_FLATTEN_MS, bpm)
    out: list[dict[str, Any]] = []
    for entry in bass_notes:
        note = deepcopy(entry)
        note["time_step"] = round(_note_step(note) + delay, 5)
        note["attack_ms"] = ATTACK_FLATTEN_MS
        vel = int(note.get("velocity", 127))
        _set_velocity(note, min(127, vel + 4))
        out.append(note)
    return sorted(out, key=_note_step)


def apply_mono_stereo_drop(
    melody_notes: list[dict[str, Any]],
    *,
    phrase_bars: int = PITCH_BEND_PHRASE_BARS,
) -> list[dict[str, Any]]:
    """Rule 28 — verse melody narrow mono; drop bars wide stereo."""
    out: list[dict[str, Any]] = []
    phrase_len = phrase_bars * BEATS_PER_BAR
    drop_window = 0.5  # beats before phrase boundary

    for entry in melody_notes:
        note = deepcopy(entry)
        step = _note_step(note)
        pos_in_phrase = step % phrase_len
        near_drop = pos_in_phrase >= phrase_len - drop_window
        bar_in_phrase = int(pos_in_phrase // BEATS_PER_BAR)

        if near_drop or bar_in_phrase >= phrase_bars - 1:
            note["pan"] = 48 if int(step * 2) % 2 == 0 else 80
            note["stereo_width"] = 1.0
        else:
            note["pan"] = 64
            note["stereo_width"] = 0.15
        out.append(note)
    return out


def build_pitch_bend_automation(
    pattern: dict[str, Any],
    *,
    phrase_bars: int = PITCH_BEND_PHRASE_BARS,
) -> list[dict[str, Any]]:
    """Rule 23 — pitch bend dip (-2 st) before each 8-bar transition."""
    max_step = 0.0
    for key in ("melody_lead", "counter_melody"):
        for entry in track_notes(pattern, key):
            max_step = max(max_step, _note_end(entry))

    phrase_len = phrase_bars * BEATS_PER_BAR
    phrases = max(1, int(max_step // phrase_len))
    events: list[dict[str, Any]] = []

    for p in range(1, phrases + 1):
        boundary = p * phrase_len
        dip_start = boundary - 0.5
        events.extend([
            {"time_step": round(dip_start, 4), "track": "melody_lead", "value": 8192},
            {"time_step": round(boundary - 0.08, 4), "track": "melody_lead", "value": 0},
            {"time_step": round(boundary, 4), "track": "melody_lead", "value": 8192},
        ])
    return events


def add_counter_melody_offbeat(
    melody_notes: list[dict[str, Any]],
    kick_notes: list[dict[str, Any]],
    rng: random.Random,
) -> list[dict[str, Any]]:
    """Rule 29 — counter melody only on off-beats, never with kick."""
    if not melody_notes:
        return []

    kick_steps = {_note_step(k) for k in kick_notes}
    melody_steps = {_note_step(m) for m in melody_notes}
    counter: list[dict[str, Any]] = []

    for entry in melody_notes:
        step = _note_step(entry)
        bar_base = int(step // BEATS_PER_BAR) * BEATS_PER_BAR
        # Off-beats: eighth-note syncopation (0.5, 1.5, 2.5, 3.5 …)
        for offset in (0.5, 1.5, 2.5, 3.5):
            hit = round(bar_base + offset, 4)
            if hit <= step:
                continue
            if any(abs(hit - ks) < 0.06 for ks in kick_steps):
                continue
            if any(abs(hit - ms) < 0.06 for ms in melody_steps):
                continue
            if rng.random() > 0.45:
                continue
            try:
                midi = parse_note_name(str(entry.get("note", "A4")))
            except ValueError:
                midi = 69
            counter.append({
                "time_step": hit,
                "note": _midi_to_name(min(91, midi + rng.choice((7, 12, 19)))),
                "length": rng.choice((0.125, 0.2, 0.25)),
                "velocity": rng.randint(68, 92),
                "pan": rng.choice((44, 84)),
                "offbeat_sync": True,
            })
            break

    return sorted(counter, key=_note_step)[:16]


def humanize_velocities(
    notes: list[dict[str, Any]],
    *,
    lo: int,
    hi: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for entry in notes:
        note = deepcopy(entry)
        _set_velocity(note, rng.randint(lo, hi))
        out.append(note)
    return out


def apply_hi_hat_swing(notes: list[dict[str, Any]], rng: random.Random) -> list[dict[str, Any]]:
    """Micro-timing: offbeat hats nudged forward/back for bounce."""
    out: list[dict[str, Any]] = []
    for index, entry in enumerate(sorted(notes, key=_note_step)):
        note = deepcopy(entry)
        step = _note_step(note)
        beat_in_bar = step % BEATS_PER_BAR
        is_offbeat = abs(beat_in_bar % 0.5 - 0.25) < 0.06 or index % 2 == 1
        if is_offbeat:
            shift = rng.uniform(PPQ_SWING_MIN, PPQ_SWING_MAX)
            if index % 4 in (1, 3):
                shift *= -1
            note["time_step"] = round(step + shift, 5)
        out.append(note)
    return out


def apply_hat_roll_pitch(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pitch roller: fast 1/32–1/64 rolls creep up/down by semitone."""
    ordered = sorted(notes, key=_note_step)
    out: list[dict[str, Any]] = []
    group: list[dict[str, Any]] = []

    def flush(group_notes: list[dict[str, Any]]) -> None:
        if len(group_notes) < 3:
            out.extend(deepcopy(n) for n in group_notes)
            return
        direction = 1
        for i, entry in enumerate(group_notes):
            note = deepcopy(entry)
            try:
                midi = parse_note_name(str(note.get("note", "C5")))
                note["note"] = _midi_to_name(midi + direction * i)
            except ValueError:
                pass
            note["pan"] = _roll_pan(i, len(group_notes))
            out.append(note)

    prev_end = -1.0
    for entry in ordered:
        step = _note_step(entry)
        length = float(entry.get("length", 0.25))
        if group and step - prev_end > 0.07:
            flush(group)
            group = []
        group.append(entry)
        prev_end = step + length
    flush(group)
    return sorted(out, key=_note_step)


def _roll_pan(index: int, total: int) -> int:
    """Sinusoidal L-C-R across a roll."""
    if total <= 1:
        return 64
    phase = index / max(1, total - 1)
    return int(64 + 20 * (phase * 2 - 1))


def _midi_to_name(midi: int) -> str:
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = midi // 12
    return f"{names[midi % 12]}{octave}"


def apply_hat_panning(notes: list[dict[str, Any]], rng: random.Random) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for entry in notes:
        note = deepcopy(entry)
        name = str(note.get("note", "")).lower()
        if "pan" in note:
            out.append(note)
            continue
        if "open" in name:
            note["pan"] = 54
        elif rng.random() < 0.35:
            note["pan"] = rng.choice([50, 78])
        else:
            note["pan"] = 64
        out.append(note)
    return out


def mono_legato_bass(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cut Itself: 808 notes never overlap."""
    ordered = sorted((deepcopy(n) for n in notes), key=_note_step)
    for i in range(len(ordered) - 1):
        current = ordered[i]
        nxt = ordered[i + 1]
        end = _note_end(current)
        next_start = _note_step(nxt)
        if next_start < end:
            current["length"] = max(0.05, round(next_start - _note_step(current), 5))
    return ordered


def add_808_bar_slides(notes: list[dict[str, Any]], *, bars: int = 8) -> list[dict[str, Any]]:
    """High-register slide stabs at end of each 4-bar phrase."""
    out = sorted((deepcopy(n) for n in notes), key=_note_step)
    if not out:
        return out

    phrase_count = max(1, int(bars // 4))
    for phrase in range(1, phrase_count + 1):
        slide_at = phrase * 4 * BEATS_PER_BAR - 0.25
        root = out[-1]
        try:
            root_midi = parse_note_name(str(root.get("note", "C2")))
        except ValueError:
            root_midi = 36
        high_midi = min(84, root_midi + 24)
        out.append({
            "time_step": round(slide_at, 5),
            "note": _midi_to_name(high_midi),
            "length": 0.125,
            "velocity": 118,
            "slide": True,
        })
    return sorted(out, key=_note_step)


def phase_align_kick_808(
    kick_notes: list[dict[str, Any]],
    bass_notes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """808 starts slightly after kick transients."""
    kick_steps = {_note_step(n) for n in kick_notes}
    out: list[dict[str, Any]] = []
    for entry in bass_notes:
        note = deepcopy(entry)
        step = _note_step(note)
        if any(abs(step - ks) < 0.05 for ks in kick_steps):
            note["time_step"] = round(step + PHASE_DELAY_BEATS, 5)
        out.append(note)
    return sorted(out, key=_note_step)


def apply_drop_tension(
    pattern: dict[str, Any],
    *,
    phrase_bars: int = 4,
) -> None:
    """Mute kick + 808 for half a beat before each phrase drop."""
    tracks = pattern.get("tracks")
    if not isinstance(tracks, dict):
        return

    phrase_len = phrase_bars * BEATS_PER_BAR
    max_step = 0.0
    for key in TRACK_KEYS:
        for entry in track_notes(pattern, key):
            max_step = max(max_step, _note_end(entry))

    phrases = max(1, int(max_step // phrase_len) + 1)
    gaps: list[tuple[float, float]] = []
    for p in range(1, phrases + 1):
        start = p * phrase_len - (BEATS_PER_BAR - DROP_GAP_START)
        gaps.append((start, start + 0.5))

    for key in ("kick", "sub_808"):
        raw = tracks.get(key)
        if not isinstance(raw, list):
            continue
        kept: list[dict[str, Any]] = []
        for entry in raw:
            step = _note_step(entry)
            if any(start <= step < end for start, end in gaps):
                continue
            kept.append(entry)
        tracks[key] = kept


def duplicate_snare_layer(
    snare_notes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Rim layer: same hits, ~40% velocity."""
    layer: list[dict[str, Any]] = []
    for entry in snare_notes:
        hit = deepcopy(entry)
        _set_velocity(hit, int(int(hit.get("velocity", 100)) * 0.4))
        layer.append(hit)
    return layer


def darken_melody_intervals(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Nudge major thirds down to minor where obvious (simple heuristic)."""
    out: list[dict[str, Any]] = []
    for entry in notes:
        note = deepcopy(entry)
        try:
            midi = parse_note_name(str(note.get("note", "A4")))
            pitch_class = midi % 12
            if pitch_class in (4, 11):  # E/B in major-ish contexts → flatten
                note["note"] = _midi_to_name(midi - 1)
        except ValueError:
            pass
        out.append(note)
    return out


def add_counter_melody_hooks(
    melody_notes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Legacy sparse hooks — prefer add_counter_melody_offbeat in humanize."""
    if not melody_notes:
        return []
    counter: list[dict[str, Any]] = []
    for entry in melody_notes:
        step = _note_step(entry)
        bar = int(step // BEATS_PER_BAR)
        if bar % 2 == 1 and step % BEATS_PER_BAR >= 2.0:
            try:
                midi = parse_note_name(str(entry.get("note", "A4")))
            except ValueError:
                midi = 69
            counter.append({
                "time_step": round(step + 0.5, 5),
                "note": _midi_to_name(min(88, midi + 12)),
                "length": 0.2,
                "velocity": 78,
                "pan": 72,
            })
    return sorted(counter, key=_note_step)


def build_sidechain_hints(kick_notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Automation hints: duck 808 to ~40% on kick, recover in 2 steps."""
    hints: list[dict[str, Any]] = []
    for entry in kick_notes:
        step = _note_step(entry)
        hints.append({"time_step": step, "target": "sub_808", "gain": 0.4})
        hints.append({"time_step": round(step + 0.125, 5), "target": "sub_808", "gain": 0.7})
        hints.append({"time_step": round(step + 0.25, 5), "target": "sub_808", "gain": 1.0})
    return hints


def _style_flags(pattern: dict[str, Any]) -> dict[str, bool]:
    text = f"{pattern.get('style', '')} {pattern.get('user_prompt', '')}".lower()
    return {
        "opium": any(k in text for k in ("opium", "f1lthy", "ken", "carson", "rage", "destroy", "lonely")),
        "country": any(k in text for k in ("country", "кантри", "banjo", "банджо")),
        "phonk": any(k in text for k in ("phonk", "drift", "memphis", "cowbell")),
        "ambient": any(k in text for k in ("ambient", "chill", "sleep", "эмбиент")),
        "pop_dance": any(k in text for k in ("dua", "weeknd", "dance pop", "nu-disco")),
    }


def humanize_pattern(pattern: dict[str, Any]) -> dict[str, Any]:
    """Apply producer-brain post-processing to LLM output."""
    data = deepcopy(pattern)
    tracks = data.setdefault("tracks", {})
    if not isinstance(tracks, dict):
        return data

    flags = _style_flags(data)
    rng = _rng_for(data)
    bpm = float(data.get("bpm", 140))

    if flags["country"]:
        logger.info("Producer brain: country shuffle mode")
        if isinstance(tracks.get("hi_hats"), list):
            tracks["hi_hats"] = apply_hi_hat_swing(tracks["hi_hats"], rng)
        return data

    if flags["ambient"]:
        logger.info("Producer brain: ambient — light humanize only")
        return data

    # --- Hi-hats ---
    hats = track_notes(data, "hi_hats")
    snare = track_notes(data, "snare")
    clap = track_notes(data, "clap")
    kick = track_notes(data, "kick")

    if hats:
        from hat_roll_engine import apply_hat_rolling_engine

        data = apply_hat_rolling_engine(data, rng)
        hats = track_notes(data, "hi_hats")
        hats = apply_hi_hat_swing(hats, rng)
        hats = apply_velocity_sine_curve(hats, base=96, amplitude=18)
        hats = apply_hat_roll_pitch(hats)
        hats = apply_open_hat_choke(hats)
        hats = apply_hat_panning(hats, rng)
        ref = clap or snare
        if ref:
            hats = apply_six_db_hat_rule(hats, ref)
        tracks["hi_hats"] = hats

    # --- Snare / clap: pre-snare shift + sine velocity on layer ---
    for key, lo, hi in (("snare", 100, 127), ("clap", 95, 120)):
        raw = track_notes(data, key)
        if raw:
            shifted = apply_pre_snare_shift(raw, bpm, rng)
            if flags["opium"] or flags["phonk"]:
                tracks[key] = shifted
            else:
                tracks[key] = humanize_velocities(shifted, lo=lo, hi=hi, rng=rng)

    snare = track_notes(data, "snare")
    if snare:
        layer = duplicate_snare_layer(snare)
        tracks["snare_layer"] = apply_velocity_sine_curve(layer, base=55, amplitude=15)

    # --- 808 mono + slides + phase + attack flatten ---
    bass = track_notes(data, "sub_808")
    if bass:
        bass = mono_legato_bass(bass)
        if flags["opium"] or not flags["pop_dance"]:
            bass = add_808_bar_slides(bass)
        if kick:
            bass = phase_align_kick_808(kick, bass)
        bass = apply_808_attack_flatten(bass, bpm)
        tracks["sub_808"] = bass

    # --- Drop tension (opium / trap) ---
    if flags["opium"] or flags["phonk"]:
        apply_drop_tension(data)

    # --- Melody + pitch bend + mono/stereo ---
    melody = track_notes(data, "melody_lead")
    if melody:
        if flags["opium"] or flags["phonk"]:
            melody = darken_melody_intervals(melody)
        melody = apply_mono_stereo_drop(melody)
        counter = add_counter_melody_offbeat(melody, kick, rng)
        if counter:
            tracks["counter_melody"] = counter
        tracks["melody_lead"] = melody

    pitch_bends = build_pitch_bend_automation(data)
    if pitch_bends:
        data["pitch_bend_automation"] = pitch_bends

    # --- Producer metadata for FL / mixer ---
    meta = {
        "sidechain": build_sidechain_hints(kick),
        "low_cut_hz": 25,
        "master_soft_clip": flags["opium"] or flags["phonk"],
        "reverb_duck": {"melody_lead": 0.7},
        "bpm_drift": float(data.get("plg_vibe_drift", 0) or 0),
        "hat_choke_group": "plg_hats",
        "808_attack_ms": ATTACK_FLATTEN_MS,
        "mono_stereo_drop_bars": PITCH_BEND_PHRASE_BARS,
        "pre_snare_shift_ms": PRE_SNARE_SHIFT_MS,
        "hat_db_down": HAT_DB_DOWN,
    }
    data["plg_producer_meta"] = meta

    steps = list(data.get("manual_steps") or [])
    steps.append("Pre-snare shift: clap/snare 2–5 ms early (Atlanta push).")
    steps.append("6 dB rule: hats ducked under clap/snare velocity.")
    steps.append("Open-hat choke: closed hats cut open tails (choke_group plg_hats).")
    steps.append("808 attack +12 ms soften — kick wins transient.")
    steps.append("Pitch bend: -2 st dip every 8 bars on melody (see pitch_bend_automation).")
    steps.append("Mono→stereo drop: narrow verse melody, wide at phrase drop.")
    data["manual_steps"] = steps[:14]

    logger.info("Producer brain applied (opium=%s)", flags["opium"])
    return data
