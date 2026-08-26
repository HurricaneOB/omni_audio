#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"{path}:{line_no} JSON 解析失败: {exc}") from exc


parser = argparse.ArgumentParser(description="确认 smoke/live/full 使用的真实 TTS backend 与计划一致")
parser.add_argument("--output-root", required=True)
parser.add_argument("--expected-backend", default="edge")
args = parser.parse_args()

root = Path(args.output_root).expanduser().resolve()
expected = args.expected_backend

snapshot_path = root / "manifests" / "edge_voice_snapshot.json"
plan_path = root / "prepared" / "tts_plan.jsonl"
status_path = root / "manifests" / "tts_status.jsonl"

if not snapshot_path.exists():
    raise SystemExit(f"[BACKEND-GUARD][FAIL] 缺少 {snapshot_path}")
if not plan_path.exists():
    raise SystemExit(f"[BACKEND-GUARD][FAIL] 缺少 {plan_path}")
if not status_path.exists():
    raise SystemExit(f"[BACKEND-GUARD][FAIL] 缺少 {status_path}")

snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
if snapshot.get("backend") != expected:
    raise SystemExit(
        f"[BACKEND-GUARD][FAIL] voice snapshot backend={snapshot.get('backend')!r}, expected={expected!r}"
    )

plan_rows = list(iter_jsonl(plan_path))
if not plan_rows:
    raise SystemExit("[BACKEND-GUARD][FAIL] tts_plan.jsonl 为空")

wrong = [r.get("id") for r in plan_rows if r.get("tts_backend") != expected]
if wrong:
    raise SystemExit(
        f"[BACKEND-GUARD][FAIL] 有 {len(wrong)} 条计划不是 backend={expected}; examples={wrong[:3]}"
    )

status_rows = list(iter_jsonl(status_path))
success = sum(1 for r in status_rows if r.get("tts_status") == "success")
if success == 0:
    raise SystemExit("[BACKEND-GUARD][FAIL] 没有任何 TTS success")

print(
    f"[BACKEND-GUARD][PASS] backend={expected} | plan_rows={len(plan_rows)} | tts_success={success}"
)
