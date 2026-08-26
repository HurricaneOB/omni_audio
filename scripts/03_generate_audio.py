#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
from _common import add_common_args, load_from_args
from fin_audio.generation import generate_audio

parser = argparse.ArgumentParser(description="Edge-TTS/Test-tone 合成并转换为 16k PCM16 WAV")
add_common_args(parser)
parser.add_argument("--tts-backend", choices=["edge", "test-tone"], default="edge")
args = parser.parse_args()
cfg = load_from_args(args)
summary = asyncio.run(generate_audio(cfg, args.output_root, args.tts_backend))
print("[OK] Audio generated:", summary)
