#!/usr/bin/env python3
from __future__ import annotations

import argparse
from _common import add_common_args, load_from_args
from fin_audio.qc import run_audio_qc

parser = argparse.ArgumentParser(description="逐文件执行 16k/mono/PCM16/duration/silence Audio QC")
add_common_args(parser)
args = parser.parse_args()
cfg = load_from_args(args)
summary = run_audio_qc(cfg, args.output_root)
print("[OK] Audio QC:", summary)
