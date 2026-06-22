# PLG FL Script Pack (V2)

Five piano-roll Python scripts tuned for trap / opium workflows. They are
installed automatically by OPEN IN FL (or `fl_setup.install_script_pack()`), and
also via the app's **Tools → Install FL Scripts**.

## Install location

```
Documents/Image-Line/FL Studio/Settings/Piano roll scripts/PLG/
```

(plus the single-layer importer `PLG PLUGIN.FLP.pyscript` one level up.)

`fl_setup.py` copies every `fl_scripts/*.pyscript` there and patches
`BRIDGE_PATH` to your absolute `output_pattern.json`, so the scripts work no
matter where PLG lives.

## Using them

In FL: open the **Piano roll**, click the **script menu** (the small
tools/script icon, top-left of the piano roll) → **PLG** → pick a script. A
dialog appears; set the knobs and click **Accept**.

Most scripts act on **selected notes**; if nothing is selected they fall back to
all notes (where it makes sense). Select notes first for surgical edits.

---

## The scripts

### 1. PLG Hat Roll (v2)
Chops each note into evenly spaced rolls — the bread-and-butter trap hat roll.
- **Division** — 1/4, 1/8, 1/16, 1/32, 1/8 triplet, 1/16 triplet, **1/24 triplet**.
- **Velocity ramp** — negative fades the roll out, positive builds it up, 0 = flat.
- **Velocity humanize** — random per-hit velocity variation so the roll breathes.
- **Timing humanize** — micro-shifts each hit off the grid (first hit stays put) for a loose, not-robotic feel.
- **Only selected notes** — on by default.

### 2. PLG Pan Spread
Spreads notes across the stereo field (built for hats/perc to widen a beat).
- **Mode** — Alternate L/R, Ramp L→R, Ramp R→L, Random.
- **Width** — 0 = centred, 1 = hard L/R.
- **Keep accents centred** — loud hits (the main hat) stay up the middle while
  quiet ghost hats fan out — how pro hats sit wide without the groove drifting.
- **Accent threshold** — velocity above which a note counts as an accent.
- **Only selected notes**.

### 3. PLG Quantize Opium
Quantize that keeps a human/trap feel instead of a robotic grid.
- **Grid** — 1/8, 1/16, 1/16 triplet, 1/4.
- **Strength** — how hard notes are pulled to the grid (1 = exact).
- **Swing** — drags the off-beat 1/16s (referenced to a fixed 1/16 feel, so it
  swings musically regardless of the quantize grid).
- **Looseness** — small random offset so it never sounds machine-perfect.

### 4. PLG Import ALL
Reads `output_pattern.json` and drops **all three layers** into the current
piano roll, colour-coded (hats / 808 / melody).
- Per-layer checkboxes + **Clear piano roll first**.
- **Note:** a piano-roll script can only write the channel it was opened from,
  so this stacks every layer on one channel. For three **separate** channels use
  **OPEN IN FL** in the PLG app (the `.flp` bridge — see FL_BRIDGE.md). This
  script is the in-piano-roll companion / fallback.

### 5. PLG 808 Glide
Adds slide + portamento glide to 808 notes, and manages note length so the glide
actually has somewhere to slide to.
- **Slide**, **Portamento** — toggle each (FL's API can only turn these *on*,
  which is what we want).
- **Stretch to next note** — butts each note against the next.
- **Overlap (beats)** — extend each note *past* the next note's start for a
  smooth, continuous slide.
- **Min length (beats)** — force short 808s up to a minimum so they're audible.
- **Only selected notes**.

---

## Notes for maintainers

- Scripts are plain Python using `import flpianoroll as flp` — no pip deps inside
  FL. They are validated for syntax in CI-style checks but the `flpianoroll`
  module only exists inside FL, so behaviour is verified in FL.
- API used: `flp.score.noteCount / getNote / addNote / deleteNote / clearNotes /
  PPQ`, `flp.Note` (number, time, length, velocity 0–1, pan 0–1 centred at 0.5,
  color 0–15, slide/porta bools, selected), `flp.ScriptDialog` (addInputCombo,
  addInputKnob, addInputCheckbox, getInputValue), `flp.Utils.ShowMessage/log`.
- Timing convention matches the rest of PLG: `time_step` 1.0 = 1 beat, ticks =
  `time_step * flp.score.PPQ`.
- Only the **PLG Import ALL** script contains `BRIDGE_PATH`; the others need no
  patching.
