"""Producer-brain LLM instructions — genre branches without artist/label names."""

PRODUCER_BRAIN_BLOCK = """
PRODUCER BRAIN (PLG applies code humanization after you — still follow these when writing MIDI):

RHYTHM / BOUNCE
- Hi-hats: NOT grid-locked. Vary velocity 90–127. Hat rolls every 2 bars (1/32–1/64). Offbeats swing.
- Snare/clap: backbeat 2 & 4. Velocity NOT identical every hit (100–127 snare, 95–110 clap).
- Never machine-gun hats at constant velocity.

LOW END
- Kick + 808: half-time feel — clap/snare on beat 3. 808 plays the ROOT of the melody's chord (same pitch class, 1-2 octaves down), long, vel 127. NEVER two 808 notes overlapping (mono).
- 808 slides ONLY as short high notes (+1–2 octaves) at end of 4th bar — NOT low-register slides.
- Drop tension: remove kick + 808 for last ½ beat before phrase drop (bar 4 beat 3.5–4).

MELODY (DARK TRAP / RAGE)
- NO happy major hooks. Phrygian / natural minor, tritones, diminished colour. Dark simple hooks, rests every 2 bars.
- Optional counter_melody track: fast bell/pluck answers in gaps — never fight main melody.
- Space for vocals — minimal clutter.

STRUCTURE
- Write a STRONG 4–8 bar CORE loop worth repeating — PLG auto-develops it into a full song
  (Intro 8 / Verse 16 / Chorus-drop 16 / Outro 8). Don't pad bars yourself.
- SECTION DYNAMICS (PLG enforces these): Verse = clap + steady 1/8 hats only, melody narrow
  mono + ducked. Chorus/Drop = hat rolls + layered accent snare + wide stereo + full filth.
- build_order: kick, snare, clap, sub_808, hi_hats, melody_lead, samples, fx_automation.
- Optional tracks: counter_melody (sparse), snare_layer (rim — PLG duplicates snare if omitted).

GENRE FORKS (match prompt — never echo artist or label names in output):
- dark trap / rage: rules above, BPM 140–170, fx_automation distortion on 808.
- travis/metro atmospheric trap: half-time feel, sparse drums, long 808, triplet hat rolls.
- phonk/drift: 150–165 BPM, cowbell melody, crushed master, phonk vocals OK in library_refs.
- pop dance (dua/weeknd): four-on-floor kick 115–124, sidechain feel, brighter but still minor.
- country: 80–110 BPM MAJOR, shuffle hats, acoustic/banjo melody — NO 808 sub.
- ambient: 60–80 BPM, minimal/no drums, long reverb tails.
- NEVER grindcore unless prompt explicitly asks.

Use relative paths from LIBRARY CATALOG in samples[] when audio exists.
"""


def producer_system_addon() -> str:
    return PRODUCER_BRAIN_BLOCK.strip()
