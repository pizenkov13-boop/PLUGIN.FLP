from arranger import arrange_song


def _core() -> dict:
    return {
        "bpm": 144,
        "tracks": {
            "kick": [{"time_step": 0.0, "note": "C1", "length": 0.4, "velocity": 112}],
            "clap": [{"time_step": 2.0, "note": "E1", "length": 0.25, "velocity": 100}],
            "hi_hats": [{"time_step": i * 0.5, "note": "C5", "length": 0.2, "velocity": 94} for i in range(8)],
            "sub_808": [{"time_step": 0.0, "note": "C2", "length": 2.0, "velocity": 127}],
            "melody_lead": [{"time_step": 0.0, "note": "A4", "length": 4.0, "velocity": 100}],
        },
    }


def test_arrange_makes_full_48_bar_song():
    p = _core()
    arrange_song(p)
    assert p["plg_total_bars"] == 48
    assert [s["name"] for s in p["plg_arrangement"]] == ["intro", "verse", "chorus", "outro"]


def test_intro_is_melody_only():
    p = _core()
    arrange_song(p)
    # Intro = first 8 bars (32 beats): no kick, no clap; melody present.
    assert all(n["time_step"] >= 32 for n in p["tracks"].get("kick", []))
    assert all(n["time_step"] >= 32 for n in p["tracks"].get("clap", []))
    assert any(n["time_step"] < 32 for n in p["tracks"]["melody_lead"])


def test_song_runs_to_the_end():
    p = _core()
    arrange_song(p)
    mel = [n["time_step"] for n in p["tracks"]["melody_lead"]]
    assert max(mel) >= 40 * 4  # melody reaches the outro near bar 48


def test_one_bar_drum_loop_tiles_across_bars():
    p = _core()
    arrange_song(p)
    assert len(p["tracks"]["kick"]) >= 16  # kick (chorus) hits many bars, not once
