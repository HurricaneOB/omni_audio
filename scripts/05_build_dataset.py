#!/usr/bin/env python3
from __future__ import annotations

import argparse
from _common import add_common_args, load_from_args
from fin_audio.dataset_builder import build_final_dataset

parser = argparse.ArgumentParser(description="生成 Qwen3-Omni/ms-swift messages+audios JSONL")
add_common_args(parser)
args = parser.parse_args()
cfg = load_from_args(args)
summary = build_final_dataset(cfg, args.output_root)
print("[OK] Dataset built:", summary)
