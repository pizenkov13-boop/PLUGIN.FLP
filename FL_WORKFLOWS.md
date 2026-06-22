# FL Workflows — Don Toliver / Opium (PLG producer brain)

PLG generates MIDI + this guide. **Your wav = your sound.** Don-level mix = follow steps below in FL 2025.

---

## Open beat (PLG → FL)

1. CREATE BEAT → OPEN IN FL → `PLG_Session.flp`
2. Channel Rack shows: **PLG Hi-Hats**, **PLG Sub 808**, **PLG Melody**
3. Drag samples from `PLG_Library` or disk onto each Sampler channel

---

## 808 (Don pocket)

| Step | FL action |
|------|-----------|
| Sample | Long 808 one-shot, mono, C root |
| Sampler | Sustain max, release ~200ms, **Portamento / glide** on |
| Notes | Roots on 1 and 3, slides on pitch changes (use PLG 808 Glide script) |
| FX | Precomputed boost 30% → **Fruity Fast Dist** drive 90% → **WaveShaper** boost 40% |
| Mixer | EQ: high-pass 25 Hz, boost 60–80 Hz gentle |

Don: sub is felt, not constant mud — space between 808 hits.

---

## Hi-hats (bounce, not only rage)

| Step | FL action |
|------|-----------|
| Sample | Short tight hat or opium roll wav |
| Pattern | Offbeats + 1/16 bursts every 2 bars |
| Script | Piano roll → Scripts → PLG → **Hat Roll** / **Pan Spread** |
| Mixer | Pan hats L/R slightly, -3 dB vs 808 |

Ken Carson = denser rolls. Don = **pocket + bounce**.

---

## Melody (vocal-ready)

| Step | FL action |
|------|-----------|
| Sound | Dark bell, pluck, or simple lead |
| Range | C4–C6, leave room for vocals |
| FX | Light reverb, cut 300–500 Hz on melody bus |
| Arrangement | Repeat hook 4 bars, variation bar 5–8 |

---

## Mixer (last 10 minutes)

1. **F9** Channel rack levels: 808 loudest, hats -6 dB, melody -4 dB
2. Drums bus optional — glue with Fruity Limiter soft
3. Sidechain: 808 triggers hat duck (light) if mix fights
4. Master: no clip — headroom for vocal later

---

## Hotkeys (Don speed)

| Key | Action |
|-----|--------|
| F5 | Piano roll |
| F6 | Channel rack |
| F9 | Mixer |
| Alt+F8 | Plugin picker |
| Ctrl+L | Toggle playlist |

---

## PLG scripts (Piano roll → Scripts → PLG)

- **Hat Roll** — opium rolls on selected hats
- **808 Glide** — slides on 808 notes
- **Pan Spread** — stereo hats
- **Quantize Opium** — loose trap swing
- **Import ALL** — re-import JSON layers

---

## Style map

| Prompt vibe | BPM | Hats | 808 | Melody |
|-------------|-----|------|-----|--------|
| Don Toliver | 145–155 | Bounce, space | Smooth slides, dist medium | Catchy minor hook |
| Ken Carson | 150–160 | Dense rolls | Heavy distorted | Sparse eerie |
| Opium dark | 140–150 | Triplet bursts | Long sub | Bell / pad |

PLG AI uses this table when you prompt artist names.
