from mix_blueprint import build_mix_blueprint, session_slug


def test_session_slug_sanitizes_style():
    data = {"bpm": 145, "style": "opium rage!!! ken"}
    slug = session_slug(data)
    assert slug.startswith("PLG_Stems_145bpm_")
    assert "!!!" not in slug


def test_blueprint_mentions_808_and_stems():
    data = {
        "bpm": 150,
        "style": "opium rage ken carson",
        "user_prompt": "dark trap",
        "plg_hat_rolls": 8,
        "plg_producer_meta": {"master_soft_clip": True},
        "plg_sample_picks": {"sub_808": "808_opium_heavy.wav"},
        "manual_steps": ["mono legato applied"],
    }
    text = build_mix_blueprint(data, stem_folder="C:/out/PLG_Stems_150bpm_opium")
    assert "808" in text
    assert "Blood Overdrive" in text
    assert "Kick.mid" in text
    assert "FL Studio Blueprint" in text


def test_blueprint_has_fx_recipe_without_brands():
    data = {"bpm": 150, "style": "dark rage trap", "plg_producer_meta": {"master_soft_clip": True}}
    text = build_mix_blueprint(data)
    assert "Pre-Amp 40%" in text
    assert "+4 dB" in text
    assert "Fruity Soft Clipper" in text
    assert "F1LTHY" not in text.upper()
    assert "OPIUM" not in text.upper()
