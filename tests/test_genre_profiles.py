from genre_profiles import builtin_profile, detect_genre, profile_for


def test_default_is_trap():
    assert detect_genre("", "just make a beat") == "trap"
    assert profile_for("", "just make a beat").name == "trap"


def test_kpop_detected_over_bare_pop():
    assert detect_genre("k-pop", "bright idol song") == "kpop"
    prof = profile_for("k-pop", "")
    assert prof.melody_scale == "major"
    assert prof.drop_tension is False
    assert prof.hat_rolls is False


def test_rage_profile_dark_and_clipped():
    prof = profile_for("rage", "dark trap")
    assert prof.name == "rage"
    assert prof.melody_scale == "phrygian"
    assert prof.drop_tension is True
    shipped = builtin_profile("rage")
    assert shipped.soft_clip is True
    assert shipped.filth == 0.9


def test_rnb_is_dorian_and_soft():
    prof = profile_for("rnb neo soul", "smooth")
    assert prof.melody_scale == "dorian"
    assert prof.hat_rolls is False


def test_grind_strips_808_and_is_request_only():
    assert detect_genre("", "grindcore anti-music") == "grind"
    assert detect_genre("", "trap beat") != "grind"
    prof = profile_for("", "grindcore")
    assert prof.eight08 is False
    assert prof.counter_melody is False


def test_filth_max_escalates_any_profile():
    maxed = profile_for("kpop", "", filth_max=True)
    assert maxed.filth == 1.0
    assert maxed.drop_tension is True
    assert maxed.soft_clip is True
    assert maxed.hat_swing >= 1.3
