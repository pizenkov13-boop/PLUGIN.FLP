from music_theory import detect_root_pc, key_label, name_for_midi, snap_pc_to_scale


def test_detect_root_prefers_weighted_pitch():
    notes = [
        {"note": "A3", "length": 4.0, "velocity": 120},
        {"note": "C4", "length": 0.25, "velocity": 80},
    ]
    assert detect_root_pc(notes) == 9  # A


def test_detect_root_default_when_empty():
    assert detect_root_pc([]) == 9


def test_snap_major_third_to_minor_in_a():
    # A natural minor has C natural, so C#5 (major 3rd) collapses down to C.
    cs5 = 5 * 12 + 1
    snapped = snap_pc_to_scale(cs5, 9, "natural_minor")
    assert snapped % 12 == 0  # C


def test_snap_keeps_in_scale_note():
    a5 = 5 * 12 + 9
    assert snap_pc_to_scale(a5, 9, "natural_minor") == a5


def test_phrygian_allows_flat_second():
    # Phrygian on A includes the flat-2 (A#); it must survive untouched.
    as5 = 5 * 12 + 10
    assert snap_pc_to_scale(as5, 9, "phrygian") == as5


def test_name_for_midi_roundtrip():
    assert name_for_midi(57) == "A4"


def test_key_label():
    assert key_label(9, "natural_minor") == "A minor"
    assert key_label(9, "phrygian") == "A phrygian"
