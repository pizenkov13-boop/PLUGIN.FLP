from pathlib import Path

from sample_chop_engine import build_chop_arrangement, should_chop_source


def test_should_chop_on_keyword():
    assert should_chop_source(Path("x.wav"), prompt="vintage japanese pop sample flip")


def test_chop_arrangement_scatters(tmp_path: Path):
    paths = [tmp_path / f"c{i}.wav" for i in range(4)]
    for p in paths:
        p.write_bytes(b"RIFF")
    arr = build_chop_arrangement(paths, bpm=140, bars=4)
    assert len(arr) >= 2
    assert all(a.get("chop") for a in arr)
