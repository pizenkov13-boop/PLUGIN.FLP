"""Test defaults — keep CLAP off unless a test opts in (model load is ~30–60s)."""

from __future__ import annotations

import os
import warnings


def pytest_configure() -> None:
    os.environ.setdefault("PLG_USE_CLAP", "0")
    os.environ.setdefault("PLG_USE_BEAT_SCORER", "0")
    os.environ.setdefault("PLG_USE_BEAT_REWARD", "0")
    warnings.filterwarnings(
        "ignore",
        message=".*audioop.*",
        category=DeprecationWarning,
    )
    warnings.filterwarnings(
        "ignore",
        message=".*ffmpeg or avconv.*",
        category=RuntimeWarning,
    )
    warnings.filterwarnings(
        "ignore",
        message=".*ffprobe or avprobe.*",
        category=RuntimeWarning,
    )
