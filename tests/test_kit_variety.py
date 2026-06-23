from pathlib import Path

from kit_variety import last_kit_paths, save_kit_pick


def test_kit_variety_blocks_last_paths(tmp_path: Path):
    a = tmp_path / "kick.wav"
    b = tmp_path / "snare.wav"
    a.write_bytes(b"x")
    b.write_bytes(b"y")
    save_kit_pick({"kick": a, "snare": b})
    blocked = last_kit_paths()
    assert str(a.resolve()) in blocked
    assert str(b.resolve()) in blocked
