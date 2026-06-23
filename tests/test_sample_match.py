from sample_match import partner_kick_keywords, pick_full_kit, score_candidate


def test_partner_kick_long_808_wants_punchy():
    kws = partner_kick_keywords("Reese_long_distorted_808.wav")
    assert "click" in kws or "punch" in kws


def test_partner_kick_short_808_wants_fat():
    kws = partner_kick_keywords("short_punch_808_tight.wav")
    assert "fat" in kws or "boom" in kws


def test_bonus_keywords_boost_score():
    base = score_candidate(
        "kits/kick_clean.wav", "kick", prompt_tokens=set(), style_tokens=set(), prompt_raw=""
    )
    boosted = score_candidate(
        "kits/kick_clean.wav",
        "kick",
        prompt_tokens=set(),
        style_tokens=set(),
        prompt_raw="",
        bonus_keywords=("clean",),
    )
    assert boosted > base


def test_808_prefers_prompt_match_over_alphabetical(tmp_path):
    (tmp_path / "808").mkdir()
    (tmp_path / "kits").mkdir()
    files = {
        "808/AAA_generic.wav": b"",
        "808/KEN_CARSON_chaos_808.wav": b"",
        "808/ZZZ_dark_sub.wav": b"",
        "kits/random_snare.wav": b"",
    }
    for rel in files:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")

    catalog = {
        "audio_total": 4,
        "audio": {
            "808": [
                "808/AAA_generic.wav",
                "808/KEN_CARSON_chaos_808.wav",
                "808/ZZZ_dark_sub.wav",
            ],
            "kits": ["kits/random_snare.wav"],
        },
    }

    kit = pick_full_kit(catalog, tmp_path, prompt="ken carson chaos rage 808", style="opium trap")
    assert kit["sub_808"][0].name == "KEN_CARSON_chaos_808.wav"
    assert kit["sub_808"][1] > score_candidate(
        "808/AAA_generic.wav",
        "sub_808",
        prompt_tokens=set(),
        style_tokens=set(),
        prompt_raw="",
    )


def test_808_avoids_snare_in_kits_folder():
    rel_scores = {
        rel: score_candidate(rel, "sub_808", prompt_tokens={"chaos"}, style_tokens=set(), prompt_raw="chaos 808")
        for rel in ("kits/chaos_snare_hard.wav", "kits/chaos_808_sub.wav", "808/BLAKK_ROCKSTAR.wav")
    }
    assert rel_scores["kits/chaos_snare_hard.wav"] < rel_scores["808/BLAKK_ROCKSTAR.wav"]


def test_full_kit_no_duplicate_files(tmp_path):
  for folder in ("808", "kits", "hats", "melodies"):
      (tmp_path / folder).mkdir()
  samples = {
      "808/low_808.wav": b"",
      "kits/kick_hard.wav": b"",
      "kits/snare_crack.wav": b"",
      "kits/clap_snap.wav": b"",
      "hats/open_rage.wav": b"",
      "melodies/dark_bell.wav": b"",
  }
  for rel in samples:
      path = tmp_path / rel
      path.parent.mkdir(parents=True, exist_ok=True)
      path.write_bytes(b"")

  catalog = {
      "audio_total": 6,
      "audio": {
          "808": ["808/low_808.wav"],
          "kits": ["kits/kick_hard.wav", "kits/snare_crack.wav", "kits/clap_snap.wav"],
          "hats": ["hats/open_rage.wav"],
          "melodies": ["melodies/dark_bell.wav"],
      },
  }
  kit = pick_full_kit(catalog, tmp_path, prompt="rage kick snare clap 808 hat melody")
  paths = [str(path.resolve()) for path, _ in kit.values()]
  assert len(paths) == len(set(paths))
  assert kit["kick"][0].name == "kick_hard.wav"
  assert kit["snare"][0].name == "snare_crack.wav"
  assert kit["sub_808"][0].name == "low_808.wav"
