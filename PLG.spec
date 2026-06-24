# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — PLG.exe with starter sounds, bundled kit, and web UI."""

from pathlib import Path

block_cipher = None
root = Path(SPECPATH)

starter_names = (
    "PLG_starter_808.wav",
    "PLG_starter_hat.wav",
    "PLG_starter_melody.wav",
    "PLG_starter_kick.wav",
    "PLG_starter_snare.wav",
    "PLG_starter_clap.wav",
    "BUNDLED.json",
    "README.md",
    "starter_manifest.json",
)

starter_files = [
    (str(root / "assets" / "starter" / name), "assets/starter")
    for name in starter_names
    if (root / "assets" / "starter" / name).is_file()
]

bundled_dir = root / "assets" / "starter" / "bundled_sounds"
if bundled_dir.is_dir():
    for path in sorted(bundled_dir.iterdir()):
        if path.is_file():
            starter_files.append((str(path), "assets/starter/bundled_sounds"))

asset_files = [
    (str(root / "assets" / name), "assets")
    for name in (
        "logo.svg",
        "logo.png",
        "logo.ico",
        "logo_icon.png",
        "Frame 2.svg",
        "prompt_tags.json",
        "mix_blueprint_i18n.json",
    )
    if (root / "assets" / name).is_file()
]

icon_path = root / "assets" / "logo.ico"
exe_icon = str(icon_path) if icon_path.is_file() else None

font_files = [
    (str(path), "assets/fonts")
    for path in (root / "assets" / "fonts").glob("*.ttf")
]

web_dist = root / "web" / "dist"
# PyInstaller's datas dest is the target *directory*, not the file path — so use
# the file's parent dir. (Using the full path nested index.html under a folder
# literally named "index.html", which broke the built UI at runtime.)
web_files = [
    (str(path), str(Path("web/dist") / path.relative_to(web_dist).parent))
    for path in web_dist.rglob("*")
    if path.is_file()
] if web_dist.is_dir() else []

root_data_files = [
    "plugin_script.py",
    "FL_WORKFLOWS.md",
    "FL_BRIDGE.md",
    "FL_SCRIPTS.md",
    "FL_VERSIONS.md",
    "START_HERE.md",
    "user_profile.example.json",
    ".env.example",
    ".env.release",
]

datas = starter_files + asset_files + font_files + web_files + [
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
    "webview",
    "httpx",
    "sentry_sdk",
    "beat_humanize",
    "hat_roll_engine",
    "sample_chop_engine",
    "kit_variety",
    "mix_blueprint",
    "producer_brain",
    "drum_defaults",
    "sample_match",
    "build_bundled_sounds",
    "pattern_tools",
    "arranger",
    "audio_features",
    "beat_preview",
    "midi_ingest",
    "music_theory",
    "genre_profiles",
    "sound_descriptors",
    "plg_webview",
    "plg_api",
    "plg_cloud",
    "plg_device",
    "plg_sentry",
    "plg_updater",
    "plg_log",
    "plg_analytics",
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
    # Demucs/torch stem-splitting is an optional, separately-installed feature
    # (stem_split.py imports it lazily and degrades gracefully). Keep the ~200 MB
    # torch stack out of the shipped exe so it stays lean (~50 MB).
    excludes=[
        "torch",
        "torchaudio",
        "torchvision",
        "demucs",
        "tensorflow",
    ],
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
    icon=exe_icon,
)
