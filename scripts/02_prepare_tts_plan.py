#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
from _common import add_common_args, load_from_args
from fin_audio.planning import prepare_tts_plan

parser = argparse.ArgumentParser(description="生成金融发音文本与稳定 voice/rate 计划")
add_common_args(parser)
parser.add_argument("--tts-backend", choices=["edge", "mock"], default="edge")
args = parser.parse_args()
cfg = load_from_args(args)
summary = asyncio.run(prepare_tts_plan(cfg, args.config, args.output_root, args.tts_backend))
print("[OK] TTS plan prepared:", summary)
