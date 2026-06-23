from pathlib import Path

from library_catalog import scan_library


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")


def test_deep_custom_kit_sorted_by_keywords(tmp_path: Path):
    # A nested kit with NO top-level 808/hats folders (the real-world case).
    _touch(tmp_path / "MORE CHAOS" / "808s" / "dark_distorted.wav")
    _touch(tmp_path / "MORE CHAOS" / "Claps" / "hard_clap.wav")
    _touch(tmp_path / "ORGANIZED" / "Hi Hats" / "open_hat.wav")
    _touch(tmp_path / "ORGANIZED" / "Melody Loops" / "sad_piano.wav")

    audio = scan_library(tmp_path)["audio"]
    assert any("dark_distorted" in r for r in audio.get("808", []))
    assert any("hard_clap" in r for r in audio.get("kits", []))
    assert any("open_hat" in r for r in audio.get("hats", []))
    assert any("sad_piano" in r for r in audio.get("melodies", []))


def test_distortion_path_is_bass(tmp_path: Path):
    _touch(tmp_path / "Distortion Bass" / "x.wav")
    cat = scan_library(tmp_path)
    assert any(r.endswith("x.wav") for r in cat["audio"].get("808", []))
    assert cat["audio_total"] == 1


def test_nfo_and_images_ignored(tmp_path: Path):
    _touch(tmp_path / "kit" / "808" / "boom.wav")
    _touch(tmp_path / "kit" / "readme.nfo")
    _touch(tmp_path / "kit" / "art.jpg")
    cat = scan_library(tmp_path)
    assert cat["audio_total"] == 1
