from pathlib import Path

import mido

from midi_ingest import (
    ingest_library_midi,
    read_midi_notes,
    split_by_register,
)


def _write_midi(path: Path, notes, ticks_per_beat: int = 480) -> None:
    """notes: list of (midi_note, start_tick, dur_tick, velocity)."""
    mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    events = []
    for note, start, dur, vel in notes:
        events.append((start, "on", note, vel))
        events.append((start + dur, "off", note, 0))
    events.sort(key=lambda e: e[0])
    last = 0
    for tick, kind, note, vel in events:
        delta = tick - last
        last = tick
        msg_type = "note_on" if kind == "on" else "note_off"
        track.append(mido.Message(msg_type, note=note, velocity=vel, time=delta))
    mid.save(str(path))


def test_read_midi_notes_beats_and_names(tmp_path: Path):
    path = tmp_path / "loop.mid"
    # melody C5 (midi 60) 1 beat, bass C3 (midi 36) 2 beats, both at tick 0
    _write_midi(path, [(60, 0, 480, 100), (36, 0, 960, 110)])
    notes = read_midi_notes(path)
    assert len(notes) == 2
    by_name = {n["note"]: n for n in notes}
    assert by_name["C5"]["length"] == 1.0
    assert by_name["C5"]["velocity"] == 100
    assert by_name["C3"]["length"] == 2.0


def test_split_by_register():
    notes = [{"note": "C5", "time_step": 0, "length": 1.0, "velocity": 100},
             {"note": "C3", "time_step": 0, "length": 2.0, "velocity": 110}]
    melody, bass = split_by_register(notes)
    assert [n["note"] for n in melody] == ["C5"]
    assert [n["note"] for n in bass] == ["C3"]


def test_ingest_plays_matching_midi(tmp_path: Path):
    (tmp_path / "midi").mkdir()
    _write_midi(tmp_path / "midi" / "dark_melody_loop.mid", [(60, 0, 480, 100), (62, 480, 480, 96)])
    pattern = {
        "style": "opium",
        "tracks": {"melody_lead": [{"time_step": 0.0, "note": "A4", "length": 4.0, "velocity": 90}]},
    }
    ok = ingest_library_midi(pattern, library_root=tmp_path, prompt="dark melody", style="opium")
    assert ok is True
    assert pattern["plg_midi_ingest"]["name"] == "dark_melody_loop.mid"
    assert len(pattern["tracks"]["melody_lead"]) == 2  # LLM melody replaced by the MIDI


def test_ingest_skips_when_nothing_matches(tmp_path: Path):
    (tmp_path / "midi").mkdir()
    _write_midi(tmp_path / "midi" / "zzz_unrelated.mid", [(60, 0, 480, 100)])
    original = [{"time_step": 0.0, "note": "A4", "length": 4.0, "velocity": 90}]
    pattern = {"style": "trap", "tracks": {"melody_lead": list(original)}}
    ok = ingest_library_midi(pattern, library_root=tmp_path, prompt="trap beat", style="trap")
    assert ok is False
    assert pattern["tracks"]["melody_lead"] == original  # untouched


def test_ingest_no_midi_dir(tmp_path: Path):
    pattern = {"tracks": {}}
    assert ingest_library_midi(pattern, library_root=tmp_path / "missing") is False
