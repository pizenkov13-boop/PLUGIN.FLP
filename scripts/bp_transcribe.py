#!/usr/bin/env python3
"""Transcribe one audio file to MIDI via basic-pitch (run inside .venv-bp).

Usage:
    python scripts/bp_transcribe.py input.wav output_dir [--bpm 140]

Prints the absolute path of the written .mid on the last line (for PLG subprocess).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="basic-pitch audio → MIDI for PLG")
    parser.add_argument("audio", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--bpm", type=float, default=120.0)
    args = parser.parse_args()

    audio = args.audio.resolve()
    out = args.output_dir.resolve()
    if not audio.is_file():
        print(f"audio not found: {audio}", file=sys.stderr)
        return 1

    out.mkdir(parents=True, exist_ok=True)

    from basic_pitch.inference import ICASSP_2022_MODEL_PATH, predict_and_save

    predict_and_save(
        [str(audio)],
        str(out),
        save_midi=True,
        sonify_midi=False,
        save_model_outputs=False,
        save_notes=False,
        model_or_model_path=ICASSP_2022_MODEL_PATH,
        midi_tempo=float(args.bpm),
    )

    midi_path = out / f"{audio.stem}.mid"
    if not midi_path.is_file():
        mids = sorted(out.glob("*.mid"))
        if not mids:
            print("basic-pitch produced no .mid file", file=sys.stderr)
            return 1
        midi_path = mids[0]

    print(midi_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
