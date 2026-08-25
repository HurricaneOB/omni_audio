#!/usr/bin/env python3
from __future__ import annotations

import argparse
from _common import add_common_args, load_from_args
from fin_audio.source import prepare_source

parser = argparse.ArgumentParser(description="下载/读取 Sujet 并提取 task_type=qa")
add_common_args(parser)
parser.add_argument("--source-jsonl", default=None, help="仅测试时使用的本地 Sujet 结构 JSONL")
parser.add_argument("--limit", type=int, default=None, help="只处理前 N 条 QA；full 模式不要设置")
parser.add_argument("--hf-cache-dir", default=None, help="Hugging Face datasets cache，可指向 /ky200t")
parser.add_argument("--streaming-source", action="store_true", help="真实小样本测试时流式读取 HF，不冻结全量 parquet")
args = parser.parse_args()
cfg = load_from_args(args)
summary = prepare_source(cfg, args.output_root, args.source_jsonl, args.limit, args.hf_cache_dir, args.streaming_source)
print("[OK] Source prepared:", summary)
