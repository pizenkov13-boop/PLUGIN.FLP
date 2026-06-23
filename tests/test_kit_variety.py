from pathlib import Path

from kit_variety import last_kit_paths, pick_with_variety, save_kit_pick


def test_kit_variety_blocks_last_paths(tmp_path: Path):
    a = tmp_path / "kick.wav"
    b = tmp_path / "snare.wav"
    a.write_bytes(b"x")
    b.write_bytes(b"y")
    save_kit_pick({"kick": a, "snare": b})
    blocked = last_kit_paths()
    assert str(a.resolve()) in blocked
    assert str(b.resolve()) in blocked


def test_pick_with_variety_targets_described_timbre(tmp_path: Path):
    (tmp_path / "808").mkdir()
    files = ["808/dark_distorted_808.wav", "808/clean_bright_sub.wav"]
    for rel in files:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")
    catalog = {"audio_total": 2, "audio": {"808": files}}

    kit = pick_with_variety(catalog, tmp_path, prompt="тёмный жёсткий дисторшн бас", style="opium")
    assert kit["sub_808"][0].name == "dark_distorted_808.wav"
