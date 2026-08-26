#!/usr/bin/env python3
from __future__ import annotations

import argparse
from _common import add_common_args
from fin_audio.env_check import run_env_check

parser = argparse.ArgumentParser(description="检查第一阶段数据构建环境")
add_common_args(parser)
parser.add_argument("--tts-backend", choices=["edge", "test-tone"], default="edge")
parser.add_argument("--source-mode", choices=["hf", "local"], default="hf")
args = parser.parse_args()
report = run_env_check(args.output_root, args.tts_backend, args.source_mode)
print("[OK] 环境检查完成:", report["output_root"])
