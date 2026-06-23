# FL Studio — supported versions

PLUGIN.FLP opens beats via **`.flp` project files** and optional **FL Scripts** (Piano roll import). This doc lists every FL lineage users still run in the wild.

## Compatibility matrix

| FL product name | Internal / marketing | Year | Arch | PLG support |
|-----------------|---------------------|------|------|-------------|
| FL Studio 12 | 12.x | 2014–2018 | 32+64 | **Legacy** — `.flp` opens; scripts may differ |
| FL Studio 20 | 20.x | 2018–2021 | 32+64 | **Supported** — common on older PCs |
| FL Studio 21 | 21.x | 2022 | 64-bit | **Supported** — `.flp` writer targets 21 header |
| FL Studio 22 | 22.x | 2023 | 64-bit | **Supported** |
| FL Studio 23 | 23.x | 2023 | 64-bit | **Supported** |
| FL Studio 24 | 24.x | 2024 | 64-bit | **Supported** |
| FL Studio 2025 | 25.x (2025) | 2025 | 64-bit | **Supported** — primary test target |

**Not supported:** FL Studio Mobile, FL Studio Fruity Edition without full project export, beta/nightly builds.

## How PLG finds FL (Windows)

`fl_launch.py` checks, in order:

1. `C:\Program Files\Image-Line\FL Studio 2025\FL64.exe`
2. `FL Studio 24`, `21`, `20` (x86)
3. Newest `Image-Line\*\FL64.exe` glob (covers 22, 23, odd installs)

If multiple versions exist, the **newest folder name** wins.

## What works per version

| Feature | FL 20–21 | FL 22–24 | FL 2025 |
|---------|----------|----------|---------|
| Open `PLG_Session.flp` | Yes | Yes | Yes |
| 3-channel pattern (kick/snare/melody) | Yes | Yes | Yes |
| PLG Scripts (Tools → Scripts) | Yes | Yes | Yes |
| PyFLP round-trip | Partial | Partial | Not for 2025-native saves |

## User-facing minimum

- **Recommended:** FL Studio 21 or newer (64-bit)
- **Minimum:** FL Studio 20 with 64-bit `FL64.exe`
- **Without FL:** You can still generate beats; use **Open project folder** and import MIDI/stems manually

## Install paths (typical)

```
C:\Program Files\Image-Line\FL Studio 2025\FL64.exe
C:\Program Files\Image-Line\FL Studio 24\FL64.exe
C:\Program Files\Image-Line\FL Studio 23\FL64.exe
C:\Program Files\Image-Line\FL Studio 22\FL64.exe
C:\Program Files\Image-Line\FL Studio 21\FL64.exe
C:\Program Files (x86)\Image-Line\FL Studio 20\FL64.exe
C:\Program Files (x86)\Image-Line\FL Studio 12\FL64.exe
```

Custom drive installs: detected via glob under `Image-Line`.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| “FL Studio not found” | Install FL or open `PLG_Session.flp` manually from project folder |
| FL opens empty | Run **Install FL Scripts** in Settings, then Open in FL again |
| Wrong FL version opens | Uninstall old FL or rename older `Image-Line` folder |
| 2025 project warnings | Expected — PLG writes FL21-compatible `.flp`; see `FL_BRIDGE.md` |

## Release QA checklist

Test on a clean VM with at least: **FL 21**, **FL 24**, **FL 2025** — Create beat → Open in FL → verify 3 channels + pattern.
