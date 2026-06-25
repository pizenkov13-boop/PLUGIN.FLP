from copy import deepcopy

from beat_humanize import humanize_pattern
from genre_profiles import PROFILES
from pattern_score import score_humanized_pattern
from plg_tune import base_profile, evaluate_profile, load_fixtures, profile_to_json_entry, suggest_profile


def test_score_humanized_rage_fixture():
    from genre_profiles import profile_for

    fixtures = load_fixtures(
        __import__("pathlib").Path(__file__).resolve().parents[1] / "assets" / "tune_fixtures.json",
        "rage",
    )
    profile = profile_for(style="rage", prompt="rage")
    pattern = deepcopy(fixtures[0])
    out = humanize_pattern(pattern, profile=profile)
    score = score_humanized_pattern(out, profile)
    assert score > 30.0


def test_evaluate_profile_baseline():
    fixtures = load_fixtures(
        __import__("pathlib").Path(__file__).resolve().parents[1] / "assets" / "tune_fixtures.json",
        "rage",
    )
    score = evaluate_profile(PROFILES["rage"], fixtures)
    assert score > 0


def test_profile_to_json_roundtrip_keys():
    entry = profile_to_json_entry(PROFILES["rage"])
    valid = {f.name for f in __import__("dataclasses").fields(PROFILES["rage"])}
    assert set(entry.keys()) <= valid | {"name"}


def test_filth_not_in_float_search():
    from plg_tune import FLOAT_SEARCH

    assert "filth" not in FLOAT_SEARCH


def test_locked_identity_bools_not_flipped_off():
    from plg_tune import LOCKED_BOOLS, suggest_profile

    class _Trial:
        def __init__(self) -> None:
            self._i = 0

        def suggest_float(self, name: str, lo: float, hi: float) -> float:
            return (lo + hi) / 2

        def suggest_categorical(self, name: str, choices: list[bool]) -> bool:
            self._i += 1
            return False

    seed = base_profile("rage")
    assert seed.soft_clip is True
    profile = suggest_profile(_Trial(), "rage", seed)
    assert profile.soft_clip is True
    assert "soft_clip" in LOCKED_BOOLS["rage"]
