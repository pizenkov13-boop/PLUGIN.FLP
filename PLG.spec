# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — bundles PLG starter sounds into PLG.exe."""

from pathlib import Path

block_cipher = None
root = Path(SPECPATH)

starter_files = [
    (str(root / "assets" / "starter" / name), "assets/starter")
    for name in (
        "PLG_starter_808.wav",
        "PLG_starter_hat.wav",
        "PLG_starter_melody.wav",
        "BUNDLED.json",
        "README.md",
    )
    if (root / "assets" / "starter" / name).is_file()
]

asset_files = [
    (str(root / "assets" / name), "assets")
    for name in ("logo.svg", "logo.png", "Frame 2.svg")
    if (root / "assets" / name).is_file()
]

root_data_files = [
    "plugin_script.py",
    "FL_WORKFLOWS.md",
    "FL_BRIDGE.md",
    "FL_SCRIPTS.md",
    "START_HERE.md",
    "user_profile.json",
    ".env.example",
]

datas = starter_files + asset_files + [
    (str(root / name), ".")
    for name in root_data_files
    if (root / name).is_file()
] + [
    (str(root / "fl_scripts"), "fl_scripts"),
    (str(root / "themes"), "themes"),
]

hiddenimports = [
    "pretty_midi",
    "mido",
    "dotenv",
]

a = Analysis(
    ["PLG.pyw"],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="PLG",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
