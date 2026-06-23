"""Generate a minimal FL Studio project (.flp) from a PLG pattern.

Why this exists
---------------
FL Studio has no CLI MIDI import, ``.mid`` argv is ignored, and menu/drag
automation proved unreliable (RU/EN UI, focus, OLE drag). The one thing FL
*does* do reliably is open a project file passed on the command line:

    FL64.exe C:\\PLUG.FLP\\PLG_Session.flp

So PLG writes a tiny, valid ``.flp`` containing six named Sampler channels
(Kick / Snare / Clap / Sub 808 / Hi-Hats / Melody) and one pattern holding the notes. When
``plg_sound_paths`` is present in the pattern JSON, each channel also gets a
``SamplePath`` event so FL loads starter or library wavs automatically.

FLP format (TLV event stream), grounded in the PyFLP project:
  - Header  "FLhd" + u32 size(=6) + i16 format(=0) + u16 channel_count + u16 ppq
  - Data    "FLdt" + u32 size + event stream
  - Events  id 0-63   -> 1 byte value
            id 64-127 -> 2 byte value (LE)
            id 128-191-> 4 byte value (LE)
            id 192-255-> variable: LEB128 length, then that many bytes
  - Note event (224) payload = N * 24-byte note structs.

Nothing here imports FL modules, so it runs as plain Python for tests.
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

from pattern_utils import (
    CHANNEL_NAMES,
    OPTIONAL_TRACK_KEYS,
    TRACK_KEYS,
    parse_note_name,
    step_to_beats,
    track_notes,
)

# Pulses per quarter note stored in the file header. 96 is a classic, always
# FL-supported value; note times below are computed in these units.
PPQ = 96

# FL version string FL reads first to decide text encoding. v21 -> UTF-16 text.
FL_VERSION = "21.0.0.0"

# --- event id bases (see PyFLP _events.py) ---
_BYTE = 0
_WORD = 64
_DWORD = 128
_TEXT = 192
_DATA = 208

# project
_VERSION = _TEXT + 7        # 199, ASCII version string
_TEMPO = _DWORD + 28        # 156, bpm * 1000
# channel
_CH_NEW = _WORD + 0         # 64, u16 channel index (starts a channel block)
_CH_TYPE = 21               # u8 channel kind, 0 = Sampler
_CH_NAME = _TEXT + 0        # 192, channel display name
_CH_SAMPLE_PATH = _TEXT + 4  # 196, absolute path to loaded sample (PyFLP SamplePath)
# pattern
_PAT_NEW = _WORD + 1        # 65, u16 pattern number (selects current pattern)
_PAT_NAME = _TEXT + 1       # 193, pattern name
_PAT_NOTES = _DATA + 16     # 224, array of 24-byte note structs

# neutral note byte values (PyFLP NotesEvent defaults)
_FINE_PITCH = 120   # 0 cents
_RELEASE = 64
_PAN = 64           # centred
_MOD_X = 128        # filter cutoff, neutral (no modulation)
_MOD_Y = 128        # resonance, neutral
_MIDI_CH = 0


def _leb128(value: int) -> bytes:
    """FL variable-length size: 7 bits/byte, little-endian, MSB = continue."""
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _byte_event(eid: int, value: int) -> bytes:
    return bytes([eid, value & 0xFF])


def _word_event(eid: int, value: int) -> bytes:
    return bytes([eid]) + struct.pack("<H", value & 0xFFFF)


def _dword_event(eid: int, value: int) -> bytes:
    return bytes([eid]) + struct.pack("<I", value & 0xFFFFFFFF)


def _text_event(eid: int, text: str, *, unicode: bool = True) -> bytes:
    if unicode:
        data = text.encode("utf-16-le") + b"\x00\x00"
    else:
        data = text.encode("ascii", "replace") + b"\x00"
    return bytes([eid]) + _leb128(len(data)) + data


def _data_event(eid: int, payload: bytes) -> bytes:
    return bytes([eid]) + _leb128(len(payload)) + payload


def _ticks(time_step: float) -> int:
    return int(round(step_to_beats(time_step) * PPQ))


def _note_struct(rack_channel: int, entry: dict[str, Any]) -> bytes:
    position = max(0, _ticks(entry["time_step"]))
    length = max(1, _ticks(entry["length"]))
    key = max(0, min(131, parse_note_name(entry["note"])))
    velocity = int(entry.get("velocity", 100))
    velocity = max(1, min(128, velocity))
    pan = int(entry.get("pan", _PAN))
    pan = max(0, min(127, pan))
    return struct.pack(
        "<IHHIHHBBBBBBBB",
        position,        # position (ticks)
        0,               # flags
        rack_channel,    # rack channel
        length,          # length (ticks)
        key,             # key (MIDI note, C5 = 60)
        0,               # group
        _FINE_PITCH,     # fine pitch
        0,               # _u1
        _RELEASE,        # release
        _MIDI_CH,        # midi channel
        pan,             # pan
        velocity,        # velocity
        _MOD_X,          # mod x (filter cutoff)
        _MOD_Y,          # mod y (resonance)
    )


def _channels_with_layout(data: dict[str, Any]) -> list[str]:
    """Lay out PLG channels; skip optional tracks with no notes."""
    channels: list[str] = []
    for key in TRACK_KEYS:
        if key in OPTIONAL_TRACK_KEYS and not track_notes(data, key):
            continue
        channels.append(key)
    return channels


def _sample_paths_from_data(data: dict[str, Any]) -> dict[str, Path]:
    raw = data.get("plg_sound_paths")
    if not isinstance(raw, dict):
        return {}
    paths: dict[str, Path] = {}
    for key, value in raw.items():
        if not value:
            continue
        path = Path(str(value))
        if path.is_file():
            paths[str(key)] = path.resolve()
    return paths


def build_flp(data: dict[str, Any]) -> bytes:
    """Serialise a PLG pattern dict into FLP bytes."""
    bpm = float(data.get("bpm", 140))
    channels = _channels_with_layout(data)
    sample_paths = _sample_paths_from_data(data)

    events = bytearray()
    events += _text_event(_VERSION, FL_VERSION, unicode=False)
    events += _dword_event(_TEMPO, int(round(bpm * 1000)))

    for index, key in enumerate(channels):
        events += _word_event(_CH_NEW, index)
        events += _byte_event(_CH_TYPE, 0)  # Sampler
        events += _text_event(_CH_NAME, CHANNEL_NAMES.get(key, key))
        sample_path = sample_paths.get(key)
        if sample_path is not None:
            events += _text_event(_CH_SAMPLE_PATH, str(sample_path))

    events += _word_event(_PAT_NEW, 1)
    events += _text_event(_PAT_NAME, "PLG Beat")

    notes = bytearray()
    note_count = 0
    for index, key in enumerate(channels):
        for entry in track_notes(data, key):
            try:
                notes += _note_struct(index, entry)
                note_count += 1
            except (KeyError, ValueError, TypeError):
                continue
    if note_count:
        events += _data_event(_PAT_NOTES, bytes(notes))

    header = b"FLhd" + struct.pack("<IhHH", 6, 0, len(channels), PPQ)
    body = b"FLdt" + struct.pack("<I", len(events)) + bytes(events)
    return header + body


def write_flp_session(data: dict[str, Any], output_path: Path) -> Path:
    """Write a ``.flp`` session next to the other PLG outputs."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(build_flp(data))
    return output_path


if __name__ == "__main__":
    import json
    import sys

    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output_pattern.json")
    pattern = json.loads(src.read_text(encoding="utf-8"))
    out = write_flp_session(pattern, Path("PLG_Session.flp"))
    print(f"Wrote {out} ({out.stat().st_size} bytes)")
