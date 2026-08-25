#!/usr/bin/env python3
from __future__ import annotations

import argparse
from _common import add_common_args, load_from_args
from fin_audio.reporting import validate_and_report

parser = argparse.ArgumentParser(description="最终静态验收并生成 FINAL_BUILD_REPORT")
add_common_args(parser)
args = parser.parse_args()
cfg = load_from_args(args)
summary = validate_and_report(cfg, args.output_root)
print("[OK] Final validation errors:", summary["final_validation_error_count"])
if summary["final_validation_error_count"]:
    raise SystemExit(2)
