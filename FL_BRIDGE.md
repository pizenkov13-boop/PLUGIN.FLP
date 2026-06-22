# FL Bridge — how OPEN IN FL works

**Goal:** CREATE BEAT → OPEN IN FL → FL Studio opens with **3 channel-rack
channels already containing the pattern notes**:

1. **PLG Hi-Hats** (`hi_hats`)
2. **PLG Sub 808** (`sub_808`)
3. **PLG Melody / Lead** (`melody_lead`)

No manual drag. No File → Import dialog. No "run a script per layer".

---

## The approach: PLG writes a `.flp` and FL opens it

FL Studio reliably opens a project file passed on the command line:

```
FL64.exe C:\PLUG.FLP\PLG_Session.flp
```

So PLG generates a tiny, valid `.flp` from `output_pattern.json` and hands it to
FL. That is the whole bridge.

```
output_pattern.json  ──▶  flp_writer.build_flp()  ──▶  PLG_Session.flp  ──▶  FL64.exe <file>
```

The three channels are **Sampler channels with notes**. When your kit folder is
empty, PLG embeds **starter wav paths** (`assets/starter/`) so FL loads audible
808 / hat / melody out of the box. When you add your own library, those paths
are used instead — swap anytime for *your sound*.

### Why not the other approaches?

Everything below was tried and abandoned (see git history / the spec):

| Approach | Why it failed |
|---|---|
| `File → Import → MIDI` keystroke automation | Fragile: RU/EN menus, focus loss, custom dialogs. This is what produced `imported=False method=explorer_fallback`. |
| `WM_DROPFILES` / simulated drag onto FL | FL uses OLE drag-and-drop; the messages are ignored. |
| `FL64.exe PLG_Beat.mid` (MIDI on argv) | FL opens but ignores the MIDI. |
| `.mid` file association | Points at Media Player, not FL. |
| PyFLP parsing the user's `.flp` | `EventEnum` parse error on FL 2025 files (confirmed: PyFLP 2.2.1 crashes on the first event under Python 3.12). |
| Piano-roll script alone | Can only write the **current** channel — cannot create 3 channels. |
| MIDI controller (device) script | The `channels` API has no documented "create channel + write pattern notes" path, and it needs a one-time MIDI-port assignment (loopMIDI) — friction we explicitly wanted to avoid. |

Writing a project file sidesteps all of it.

---

## File format (for maintainers)

`flp_writer.py` emits the FLP TLV event stream directly (no third-party dep):

* **Header** `FLhd` + `u32 size(=6)` + `i16 format(=0)` + `u16 channel_count` + `u16 ppq(=96)`
* **Data** `FLdt` + `u32 size` + event stream
* **Events** — id `0-63`→1 byte, `64-127`→2 bytes (LE), `128-191`→4 bytes (LE),
  `192-255`→variable (LEB128 length, then bytes)

Events written, in order:

| Event | ID | Value |
|---|---|---|
| Version | 199 (TEXT+7) | `"21.0.0.0"` (ASCII) |
| Tempo | 156 (DWORD+28) | `bpm * 1000` |
| New channel ×3 | 64 (WORD) | channel index 0/1/2 |
| Channel type ×3 | 21 | `0` (Sampler) |
| Channel name ×3 | 192 (TEXT) | UTF-16-LE name |
| New pattern | 65 (WORD+1) | `1` |
| Pattern name | 193 (TEXT+1) | `"PLG Beat"` |
| Notes | 224 (DATA+16) | N × 24-byte note struct |

Note struct (24 bytes, little-endian): `position u32, flags u16, rack_channel
u16, length u32, key u16, group u16, fine_pitch u8, _u1 u8, release u8,
midi_channel u8, pan u8, velocity u8, mod_x u8, mod_y u8`. Neutral values:
pan 64, velocity 100 (or the note's own), mod_x/mod_y 128, fine_pitch 120,
release 64.

**Timing:** `time_step` 1.0 = 1 beat. In the `.flp`, ticks = `time_step * 96`
(PPQ). 0.25 → 24 ticks, 4.0 → 384 ticks.

The event IDs and note layout are taken from the PyFLP project (the most current
open FLP reference). The writer was structurally verified with an independent
decoder: for the sample project it produced 3 named channels and 117 notes
(42 hats / 5 × 808 / 70 melody), matching the JSON exactly.

---

## Python entry points

* `fl_launch.open_beat_in_fl(project_dir)` — exports MIDI (kept for manual/other
  DAWs), writes `PLG_Session.flp`, installs the FL scripts, finds `FL64.exe`,
  launches it with the `.flp`. Returns:

  ```python
  {
    "fl_exe": Path, "midi": Path, "flp": Path, "script": Path,
    "pattern": Path, "imported": True,
    "import_method": "flp_session", "import_configured": True,
  }
  ```

* `fl_setup.install_all(project_dir)` — installs the single-layer importer
  (`PLG PLUGIN.FLP.pyscript`) **and** the V2 script pack (see FL_SCRIPTS.md).
* `fl_setup.is_fl_bridge_ready(project_dir)` — for the GUI setup strip.
* `flp_writer.write_flp_session(data, path)` — JSON → `.flp`.

---

## One-time setup

**None.** The `.flp` carries everything. The first OPEN IN FL also installs the
piano-roll scripts automatically.

---

## Re-running OPEN IN FL (second beat)

Each CREATE BEAT rewrites `output_pattern.json`; each OPEN IN FL regenerates
`PLG_Session.flp` and launches FL with it.

* **FL not running** → opens fresh with the new beat.
* **FL already running** → FL is single-instance, so it prompts to save the
  current project, then loads the new `PLG_Session.flp`. No duplicate/ghost
  channels — it is a clean project load, not a merge.

---

## Verify it yourself (FL 2025)

1. In PLG, type a prompt and hit **CREATE BEAT**.
2. Hit **OPEN IN FL**.
3. FL Studio 2025 launches and loads `PLG_Session.flp`.
4. **Expected:** the Channel Rack shows **PLG Hi-Hats**, **PLG Sub 808**,
   **PLG Melody / Lead**, each with the pattern's notes (open any in the piano
   roll to see them).
5. Drag your own samples onto the three channels, then press play.

Quick check without the app:

```powershell
python flp_writer.py output_pattern.json      # writes PLG_Session.flp
& "C:\Program Files\Image-Line\FL Studio 2025\FL64.exe" "C:\PLUG.FLP\PLG_Session.flp"
```

> **Status:** the writer is structurally verified, but "opens cleanly in FL
> 2025" should be confirmed on your machine with the steps above — that is the
> one thing this repo cannot self-test. If FL reports a problem loading the
> file, grab `plg_session.log` and the FL error text.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| "FL Studio not found" | Install FL, or check the path in `fl_launch.FL_CANDIDATES`. The finder also scans `C:\Program Files\Image-Line\*\FL64.exe`. |
| FL opens empty | Confirm `PLG_Session.flp` exists in `C:\PLUG.FLP` and is non-zero. Re-run CREATE BEAT first. |
| Channels there but silent | Expected — load your own sounds onto them (that's the product). For a quick test, drop any sample or add 3xOsc. |
| Notes look off-grid | Check `time_step` in the JSON (1.0 = 1 beat). |
| Want all layers on one channel | Use the **PLG Import ALL** piano-roll script (FL_SCRIPTS.md). |

---

## Fallback

If `.flp` generation ever fails, `open_beat_in_fl` raises rather than launching
an empty FL. The single-layer piano-roll importer (`PLG PLUGIN.FLP`) and the
**PLG Import ALL** script remain available as manual paths, and `output_midi/`
still contains `PLG_Beat.mid` for manual `File → Import → MIDI`.

*Cursor note:* the `explorer_fallback` branch + drag messagebox in
`plg_app._on_fl_opened` is now dead under normal use and can be simplified.
