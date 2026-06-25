"""Underground / rage producer brain — deterministic MIDI humanization after the LLM."""

from __future__ import annotations

import hashlib
import logging
import math
import random
from copy import deepcopy
from typing import Any

from genre_profiles import GenreProfile, profile_for
from music_theory import detect_root_pc, key_label, snap_pc_to_scale
from pattern_utils import TRACK_KEYS, parse_note_name, track_notes

logger = logging.getLogger("plg.humanize")

BEATS_PER_BAR = 4.0
PPQ_SWING_MIN = 6 / 96.0   # dirtier swing — +6..+9 ticks @ PPQ 96
PPQ_SWING_MAX = 9 / 96.0
PHASE_DELAY_BEATS = 0.008
DROP_GAP_START = 3.5
PRE_SNARE_SHIFT_MS = (2.0, 5.0)
ATTACK_FLATTEN_MS = 15.0   # 808 attack pushed so the click-kick punches first
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
        section = note.get("section")
        if section in ("chorus", "drop"):
            wide = True
        elif section in ("intro", "verse", "outro"):
            wide = False
        else:
            # No section tag (raw humanize call): fall back to phrase position.
            pos_in_phrase = step % phrase_len
            near_drop = pos_in_phrase >= phrase_len - drop_window
            bar_in_phrase = int(pos_in_phrase // BEATS_PER_BAR)
            wide = near_drop or bar_in_phrase >= phrase_bars - 1

        if wide:
            note["pan"] = 48 if int(step * 2) % 2 == 0 else 80
            note["stereo_width"] = 1.0
        else:
            note["pan"] = 64
            note["stereo_width"] = 0.15
            # Rule 28 — duck the verse melody so the drop hits harder.
            note["velocity"] = max(1, int(int(note.get("velocity", 100)) * 0.8))
        out.append(note)
    return out


def dedupe_heavy_overlaps(
    pattern: dict[str, Any],
    *,
    keys: tuple[str, ...] = ("kick", "sub_808"),
    eps: float = 0.03,
) -> None:
    """Censor: two heavy hits never share a tick — keep the loudest, drop the rest."""
    tracks = pattern.get("tracks")
    if not isinstance(tracks, dict):
        return
    for key in keys:
        notes = tracks.get(key)
        if not isinstance(notes, list) or len(notes) < 2:
            continue
        ordered = sorted(notes, key=lambda n: (float(n.get("time_step", 0)), -int(n.get("velocity", 0))))
        kept: list[dict[str, Any]] = []
        last: float | None = None
        for note in ordered:
            step = float(note.get("time_step", 0))
            if last is not None and abs(step - last) < eps:
                continue  # a louder hit already owns this tick
            kept.append(note)
            last = step
        tracks[key] = kept


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


def apply_hi_hat_swing(
    notes: list[dict[str, Any]],
    rng: random.Random,
    *,
    intensity: float = 1.0,
) -> list[dict[str, Any]]:
    """Micro-timing: offbeat hats nudged forward/back for bounce.

    ``intensity`` scales the swing depth per genre (0 = grid-locked, 1 = trap).
    """
    out: list[dict[str, Any]] = []
    if intensity <= 0:
        return [deepcopy(n) for n in sorted(notes, key=_note_step)]
    for index, entry in enumerate(sorted(notes, key=_note_step)):
        note = deepcopy(entry)
        step = _note_step(note)
        beat_in_bar = step % BEATS_PER_BAR
        is_offbeat = abs(beat_in_bar % 0.5 - 0.25) < 0.06 or index % 2 == 1
        if is_offbeat:
            shift = rng.uniform(PPQ_SWING_MIN, PPQ_SWING_MAX) * intensity
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


def align_808_to_key(
    bass_notes: list[dict[str, Any]],
    melody_notes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Rule 18 — lock the 808 to the melody's key.

    Transposes the whole 808 line by the nearest interval (-6..+5 semitones)
    mapping its detected root onto the melody root, so the sub never clashes
    with the chords. No-op when the keys already agree or melody is empty.
    """
    if not bass_notes or not melody_notes:
        return bass_notes
    mel_root = detect_root_pc(melody_notes)
    bass_root = detect_root_pc(bass_notes)
    delta = (mel_root - bass_root) % 12
    if delta > 6:
        delta -= 12
    if delta == 0:
        return bass_notes
    out: list[dict[str, Any]] = []
    for entry in bass_notes:
        note = deepcopy(entry)
        try:
            midi = parse_note_name(str(note.get("note", "C2")))
            note["note"] = _midi_to_name(midi + delta)
            note["key_matched"] = True
        except ValueError:
            pass
        out.append(note)
    return out


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


def darken_melody_intervals(
    notes: list[dict[str, Any]],
    *,
    scale: str = "natural_minor",
) -> list[dict[str, Any]]:
    """Rule 11 — snap melody into a dark, key-aware scale (minor / phrygian).

    Detects the melody's own root, then quantizes every note to the nearest
    in-scale tone (ties resolve downward for darkness). Replaces the old blind
    'flatten every E and B' rule, which corrupted any key that wasn't C-ish.
    """
    if not notes:
        return []
    root = detect_root_pc(notes)
    out: list[dict[str, Any]] = []
    for entry in notes:
        note = deepcopy(entry)
        try:
            midi = parse_note_name(str(note.get("note", "A4")))
            snapped = snap_pc_to_scale(midi, root, scale)
            if snapped != midi:
                note["note"] = _midi_to_name(snapped)
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
        "rage": any(k in text for k in ("rage", "dark trap", "underground", "plugg", "jerk")),
        "country": any(k in text for k in ("country", "кантри", "banjo", "банджо")),
        "phonk": any(k in text for k in ("phonk", "drift", "memphis", "cowbell")),
        "ambient": any(k in text for k in ("ambient", "chill", "sleep", "эмбиент")),
        "pop_dance": any(k in text for k in ("dance pop", "nu-disco", "disco", "dark pop")),
    }


def reprocess_hi_hats(pattern: dict[str, Any], *, chaos_seed: int | None = None) -> dict[str, Any]:
    """Re-run hat roll + humanize on hi-hats (Chaos Roll button)."""
    data = deepcopy(pattern)
    tracks = data.setdefault("tracks", {})
    if not isinstance(tracks, dict):
        return data

    hats = track_notes(data, "hi_hats")
    if not hats:
        return data

    base = [deepcopy(n) for n in hats if not n.get("hat_roll")]
    if len(base) < 3:
        base = [deepcopy(n) for n in hats]

    tracks["hi_hats"] = base
    rng = random.Random(chaos_seed) if chaos_seed is not None else _rng_for(data)

    from hat_roll_engine import apply_hat_rolling_engine

    data = apply_hat_rolling_engine(data, rng)
    hats = track_notes(data, "hi_hats")
    hats = apply_hi_hat_swing(hats, rng)
    hats = apply_velocity_sine_curve(hats, base=96, amplitude=18)
    hats = apply_hat_roll_pitch(hats)
    hats = apply_open_hat_choke(hats)
    hats = apply_hat_panning(hats, rng)

    snare = track_notes(data, "snare")
    clap = track_notes(data, "clap")
    ref = clap or snare
    if ref:
        hats = apply_six_db_hat_rule(hats, ref)

    tracks["hi_hats"] = hats
    data["plg_chaos_rolls"] = int(data.get("plg_chaos_rolls", 0)) + 1
    data["plg_hat_rolls"] = data.get("plg_hat_rolls", 0)
    return data


# Register layout — stop the "everything mushed in C5-C6" problem.
DRUM_NATIVE_MIDI = 60        # C5 — one-shot drums play at native pitch here
SUB_REGISTER = (24, 47)      # C1..B2 — fat sub for the 808
MELODY_REGISTER = (60, 83)   # C5..B6 — keep the lead clear of the bass
# Hi-hats are intentionally left alone: apply_hat_roll_pitch tunes rolls (Rule 3).
DRUM_LAYOUT_KEYS = ("kick", "snare", "snare_layer", "clap")


def _clamp_octave(notes: list[dict[str, Any]], lo: int, hi: int) -> None:
    for entry in notes:
        try:
            midi = parse_note_name(str(entry.get("note", "C5")))
        except ValueError:
            continue
        while midi < lo:
            midi += 12
        while midi > hi:
            midi -= 12
        entry["note"] = _midi_to_name(midi)


def normalize_registers(pattern: dict[str, Any]) -> None:
    """Lay tracks into clean registers so notes don't collide into mush.

    Drums snap to a native key (one-shots play un-pitched); the 808 drops into a
    fat sub octave; melody/counter sit in the mid register — all preserving
    pitch class, so the key the humanizer locked stays intact.
    """
    tracks = pattern.get("tracks")
    if not isinstance(tracks, dict):
        return
    native = _midi_to_name(DRUM_NATIVE_MIDI)
    for key in DRUM_LAYOUT_KEYS:
        for entry in tracks.get(key) or []:
            entry["note"] = native
    _clamp_octave(tracks.get("sub_808") or [], *SUB_REGISTER)
    _clamp_octave(tracks.get("melody_lead") or [], *MELODY_REGISTER)
    _clamp_octave(tracks.get("counter_melody") or [], *MELODY_REGISTER)


def apply_melody_groove_lag(
    notes: list[dict[str, Any]],
    bpm: float,
    ms: float,
    rng: random.Random,
) -> list[dict[str, Any]]:
    """Lazy groove-lag — drag melody notes a few ms late off the grid for a
    behind-the-beat feel (Groove-опоздание). Drums stay locked; only the melody
    leans back, which is what makes the pocket feel human instead of robotic."""
    if ms <= 0:
        return [deepcopy(n) for n in notes]
    out: list[dict[str, Any]] = []
    for entry in notes:
        note = deepcopy(entry)
        lag = max(0.0, ms + rng.uniform(-2.0, 2.0))
        note["time_step"] = round(_note_step(note) + ms_to_beats(lag, bpm), 5)
        note["groove_lag_ms"] = round(lag, 2)
        out.append(note)
    return sorted(out, key=_note_step)


def apply_chord_voicing_spread(
    notes: list[dict[str, Any]],
    rng: random.Random,
    *,
    chance: float,
    register: tuple[int, int] = MELODY_REGISTER,
) -> list[dict[str, Any]]:
    """Open clustered chords — with ``chance`` probability per note, invert a tone
    by an octave (kept inside the melody register) so triads breathe and leave
    mid-range space for a vocal, instead of a tight cramped block chord."""
    if chance <= 0:
        return [deepcopy(n) for n in notes]
    lo, hi = register
    out: list[dict[str, Any]] = []
    for entry in notes:
        note = deepcopy(entry)
        if rng.random() < chance:
            try:
                midi = parse_note_name(str(note.get("note", "C5")))
                cand = midi + (12 if rng.random() < 0.5 else -12)
                if lo <= cand <= hi:
                    note["note"] = _midi_to_name(cand)
                    note["voicing_inverted"] = True
            except ValueError:
                pass
        out.append(note)
    return out


_HAT_STATES = ("ghost", "normal", "accent")
_HAT_VEL_FACTOR = {"ghost": 0.52, "normal": 0.80, "accent": 1.0}
# Markov transition weights (current → next), tuned to avoid monotonous runs.
_HAT_TRANSITIONS = {
    "ghost": (0.15, 0.55, 0.30),
    "normal": (0.42, 0.23, 0.35),
    "accent": (0.48, 0.40, 0.12),
}


def apply_markov_hat_dynamics(
    notes: list[dict[str, Any]],
    rng: random.Random,
    *,
    peak: int = 118,
) -> list[dict[str, Any]]:
    """Markov velocity state-machine for hats — walk ghost/normal/accent through a
    transition matrix so dynamics breathe (waves of ~100% / ~50%) instead of a
    monotone machine-gun. Roll notes keep their ramp into the snare."""
    ordered = sorted((deepcopy(n) for n in notes), key=_note_step)
    state = "normal"
    for note in ordered:
        if note.get("hat_roll"):
            continue
        state = rng.choices(_HAT_STATES, weights=_HAT_TRANSITIONS[state])[0]
        _set_velocity(note, int(peak * _HAT_VEL_FACTOR[state]) + rng.randint(-4, 4))
        note["hat_state"] = state
    return ordered


_KICK_SYNC_OFFSETS = (1.0, 2.5, 2.75, 3.25)  # weak 16ths; beat 2.0 (clap) excluded


def add_kick_syncopation(
    kick_notes: list[dict[str, Any]],
    bars: int,
    rng: random.Random,
    *,
    prob: float,
    clap_offsets: tuple[float, ...] = (2.0,),
) -> list[dict[str, Any]]:
    """Weighted syncopation matrix — sprinkle off-grid kicks on weak steps (never
    on the clap, never doubling an existing kick). The downbeat stays the anchor."""
    if prob <= 0:
        return [deepcopy(n) for n in kick_notes]
    out = [deepcopy(n) for n in kick_notes]
    existing = {round(_note_step(n), 3) for n in kick_notes}
    for bar in range(max(1, bars)):
        base = bar * BEATS_PER_BAR
        for off in _KICK_SYNC_OFFSETS:
            if rng.random() > prob:
                continue
            t = round(base + off, 5)
            if any(abs(t - e) < 0.2 for e in existing):
                continue
            if any(abs((t % BEATS_PER_BAR) - c) < 0.15 for c in clap_offsets):
                continue
            out.append({
                "time_step": t, "note": "C1", "length": 0.4,
                "velocity": rng.randint(86, 104), "kick_sync": True,
            })
            existing.add(t)
    return sorted(out, key=_note_step)


def build_snare_riser(
    end_beats: float,
    *,
    phrase_bars: int = 8,
) -> list[dict[str, Any]]:
    """Festival build — accelerating snare roll (1/4→1/8→1/16→1/32) with rising
    velocity and a pitch-up hint, in the bar before each phrase drop."""
    risers: list[dict[str, Any]] = []
    phrase_len = phrase_bars * BEATS_PER_BAR
    phrases = max(1, int(end_beats // phrase_len))
    # (segment start, end, step) — 1/4 → 1/8 → 1/16 → 1/32 across the last bar.
    segments = ((0.0, 1.0, 1.0), (1.0, 2.0, 0.5), (2.0, 3.0, 0.25), (3.0, 4.0, 0.125))
    for p in range(1, phrases + 1):
        bar_start = p * phrase_len - BEATS_PER_BAR
        for seg_start, seg_end, step in segments:
            t = bar_start + seg_start
            while t < bar_start + seg_end - 1e-6:
                prog = (t - bar_start) / BEATS_PER_BAR
                risers.append({
                    "time_step": round(t, 5), "note": "D1",
                    "length": round(step * 0.9, 5),
                    "velocity": min(127, int(78 + prog * 49)),
                    "riser": True, "pitch_up": int(round(prog * 12)),
                })
                t += step
    return sorted(risers, key=_note_step)


def humanize_pattern(pattern: dict[str, Any], *, profile: GenreProfile | None = None) -> dict[str, Any]:
    """Apply producer-brain post-processing to LLM output.

    Pass ``profile`` to override genre detection (used by ``plg_tune`` offline).
    """
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

    style = str(data.get("style", ""))
    prompt = str(data.get("user_prompt", ""))
    filth = bool(data.get("plg_filth_mode")) or any(
        k in f"{style} {prompt}".lower()
        for k in ("filth", "filthy", "мясо", "max filth", "брутал")
    )
    profile = profile if profile is not None else profile_for(style, prompt, filth_max=filth)
    logger.info("Producer brain: genre=%s filth=%s", profile.name, filth)

    # --- Hi-hats ---
    hats = track_notes(data, "hi_hats")
    snare = track_notes(data, "snare")
    clap = track_notes(data, "clap")
    kick = track_notes(data, "kick")

    if hats:
        if profile.hat_rolls:
            from hat_roll_engine import apply_hat_rolling_engine

            data = apply_hat_rolling_engine(data, rng)
            hats = track_notes(data, "hi_hats")
        hats = apply_hi_hat_swing(hats, rng, intensity=profile.hat_swing)
        if profile.markov_hats:
            hats = apply_markov_hat_dynamics(hats, rng)
        else:
            hats = apply_velocity_sine_curve(hats, base=96, amplitude=18)
        if profile.hat_rolls:
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
            if profile.humanize_drum_velocity:
                tracks[key] = humanize_velocities(shifted, lo=lo, hi=hi, rng=rng)
            else:
                tracks[key] = shifted

    snare = track_notes(data, "snare")
    if snare:
        layer = duplicate_snare_layer(snare)
        tracks["snare_layer"] = apply_velocity_sine_curve(layer, base=55, amplitude=15)

    # --- 808 mono + slides + phase + attack flatten ---
    bass = track_notes(data, "sub_808")
    if bass and profile.eight08:
        bass = align_808_to_key(bass, track_notes(data, "melody_lead"))
        bass = mono_legato_bass(bass)
        if profile.eight08_slides:
            bass = add_808_bar_slides(bass)
        if kick:
            bass = phase_align_kick_808(kick, bass)
        bass = apply_808_attack_flatten(bass, bpm)
        tracks["sub_808"] = bass

    # --- Drop tension ---
    if profile.drop_tension:
        apply_drop_tension(data)

    # --- Melody + pitch bend + mono/stereo ---
    melody = track_notes(data, "melody_lead")
    if melody:
        if profile.melody_scale:
            melody = darken_melody_intervals(melody, scale=profile.melody_scale)
            data["plg_key"] = key_label(detect_root_pc(melody), profile.melody_scale)
        if profile.voicing_spread > 0:
            melody = apply_chord_voicing_spread(melody, rng, chance=profile.voicing_spread)
        if profile.melody_lag_ms > 0:
            melody = apply_melody_groove_lag(melody, bpm, profile.melody_lag_ms, rng)
        if profile.stereo_drop:
            melody = apply_mono_stereo_drop(melody)
        if profile.counter_melody:
            counter = add_counter_melody_offbeat(melody, kick, rng)
            if counter:
                tracks["counter_melody"] = counter
        tracks["melody_lead"] = melody

    # --- Kick syncopation: weighted off-grid hits (never on the clap) ---
    if profile.kick_syncopation > 0 and kick:
        bars = max(1, int(max(_note_end(n) for n in kick) // BEATS_PER_BAR) + 1)
        kick = add_kick_syncopation(kick, bars, rng, prob=profile.kick_syncopation)
        tracks["kick"] = kick

    # --- Snare riser: accelerating build before each drop (festival/EDM) ---
    if profile.snare_riser:
        end_beats = 0.0
        for key in TRACK_KEYS:
            for entry in track_notes(data, key):
                end_beats = max(end_beats, _note_end(entry))
        risers = build_snare_riser(end_beats)
        if risers:
            tracks["snare"] = sorted(track_notes(data, "snare") + risers, key=_note_step)

    # Lay everything into clean registers (808 sub, melody mid, drums native).
    normalize_registers(data)
    # Censor: no two kick or two 808 hits on the same tick (no phase mush).
    dedupe_heavy_overlaps(data)

    pitch_bends = build_pitch_bend_automation(data)
    if pitch_bends:
        data["pitch_bend_automation"] = pitch_bends

    # --- Producer metadata for FL / mixer ---
    meta = {
        "sidechain": build_sidechain_hints(kick),
        "low_cut_hz": 25,
        "master_soft_clip": profile.soft_clip,
        "reverb_duck": {"melody_lead": 0.7},
        "bpm_drift": float(data.get("plg_vibe_drift", 0) or 0),
        "hat_choke_group": "plg_hats",
        "808_attack_ms": ATTACK_FLATTEN_MS,
        "mono_stereo_drop_bars": PITCH_BEND_PHRASE_BARS,
        "pre_snare_shift_ms": PRE_SNARE_SHIFT_MS,
        "hat_db_down": HAT_DB_DOWN,
        "key": data.get("plg_key"),
        "key_matched_808": bool(profile.eight08),
        "melody_lag_ms": profile.melody_lag_ms,
        "voicing_spread": profile.voicing_spread,
        "kick_syncopation": profile.kick_syncopation,
        "markov_hats": profile.markov_hats,
        "snare_riser": profile.snare_riser,
        "genre": profile.name,
        "filth": round(profile.filth, 2),
        "filth_max": filth,
    }
    data["plg_producer_meta"] = meta
    data["plg_genre"] = profile.name

    steps = list(data.get("manual_steps") or [])
    steps.append("Pre-snare shift: clap/snare 2–5 ms early (Atlanta push).")
    steps.append("6 dB rule: hats ducked under clap/snare velocity.")
    steps.append("Open-hat choke: closed hats cut open tails (choke_group plg_hats).")
    steps.append("808 attack +15 ms soften — click-kick punches first, no phase mush.")
    steps.append("Pitch bend: -2 st dip every 8 bars on melody (see pitch_bend_automation).")
    steps.append("Mono→stereo drop: narrow verse melody, wide at phrase drop.")
    if profile.melody_lag_ms > 0:
        steps.append(f"Groove lag: melody dragged ~{profile.melody_lag_ms:.0f} ms late (lazy pocket).")
    if profile.voicing_spread > 0:
        steps.append("Chord voicing: ~octave inversions open the harmony for vocal space.")
    if profile.markov_hats:
        steps.append("Markov hats: ghost/normal/accent velocity walk — no monotone machine-gun.")
    if profile.kick_syncopation > 0:
        steps.append("Kick syncopation: weighted off-grid hits on weak steps, clear of the clap.")
    if profile.snare_riser:
        steps.append("Snare riser: 1/4→1/32 accelerating build + pitch-up into each drop.")
    if data.get("plg_key"):
        steps.append(f"Key lock: melody + 808 snapped to {data['plg_key']}.")
    steps.append(f"Genre profile: {profile.name}" + (" · FILTH MAX" if filth else "") + ".")
    data["manual_steps"] = steps[:15]

    logger.info("Producer brain applied (rage=%s)", flags["rage"])
    return data
