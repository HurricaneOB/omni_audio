from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from .audio_utils import inspect_wav
from .io_utils import dir_size_bytes, iter_jsonl, read_json, write_json
from .paths import BuildPaths
from .schema import validate_training_record


def _count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(r.get(key)) for r in rows).items()))


def validate_and_report(cfg: dict[str, Any], output_root: str | Path) -> dict[str, Any]:
    """重新读取最终产物做静态验收，并生成机器可读 summary 与 Markdown 报告。"""
    paths = BuildPaths.from_root(output_root)
    source_snapshot = read_json(paths.manifests / "source_snapshot.json")
    plan_rows = list(iter_jsonl(paths.prepared / "tts_plan.jsonl")) if (paths.prepared / "tts_plan.jsonl").exists() else []
    active_ids = {r["id"] for r in plan_rows}
    tts_rows = [r for r in iter_jsonl(paths.manifests / "tts_status.jsonl") if r.get("id") in active_ids] if (paths.manifests / "tts_status.jsonl").exists() else []
    qc_rows = [r for r in iter_jsonl(paths.manifests / "audio_qc.jsonl") if r.get("id") in active_ids] if (paths.manifests / "audio_qc.jsonl").exists() else []
    provenance = list(iter_jsonl(paths.manifests / "provenance.jsonl")) if (paths.manifests / "provenance.jsonl").exists() else []
    final_rows = list(iter_jsonl(paths.final / "all.jsonl")) if (paths.final / "all.jsonl").exists() else []
    train_rows = list(iter_jsonl(paths.final / "train.jsonl")) if (paths.final / "train.jsonl").exists() else []
    valid_rows = list(iter_jsonl(paths.final / "valid.jsonl")) if (paths.final / "valid.jsonl").exists() else []

    source_by_audio = {p["audio_wav"]: p for p in provenance}
    validation_errors: list[dict[str, Any]] = []
    for i, row in enumerate(final_rows):
        audio = row.get("audios", [None])[0] if isinstance(row.get("audios"), list) and row.get("audios") else None
        p = source_by_audio.get(str(Path(audio).resolve())) if audio else None
        errors = validate_training_record(row, source_question=(p or {}).get("source_user_text"))
        if p and row["messages"][-1].get("content") != p.get("assistant_text"):
            errors.append("assistant_not_original_answer")
        if audio:
            info = inspect_wav(audio, float(cfg["audio"]["silence_rms_threshold"]))
            if not info.get("ok") or info.get("sample_rate") != int(cfg["audio"]["sample_rate"]) or info.get("channels") != int(cfg["audio"]["channels"]) or info.get("subtype") != "PCM_16":
                errors.append("audio_recheck_failed")
        if errors:
            validation_errors.append({"row_index": i, "errors": sorted(set(errors)), "audio": audio})

    durations = np.array([float(p["duration_sec"]) for p in provenance if p.get("duration_sec") is not None], dtype=float)
    if len(durations):
        duration_stats = {
            "duration_min": float(np.min(durations)),
            "duration_p50": float(np.percentile(durations, 50)),
            "duration_p90": float(np.percentile(durations, 90)),
            "duration_p95": float(np.percentile(durations, 95)),
            "duration_p99": float(np.percentile(durations, 99)),
            "duration_max": float(np.max(durations)),
            "total_audio_duration_hours": float(np.sum(durations) / 3600.0),
        }
    else:
        duration_stats = {k: 0.0 for k in ("duration_min", "duration_p50", "duration_p90", "duration_p95", "duration_p99", "duration_max", "total_audio_duration_hours")}

    summary = {
        "source_total_rows_seen": source_snapshot.get("raw_rows_seen"),
        "qa_rows": source_snapshot.get("qa_rows_written"),
        "tts_planned_rows": source_snapshot.get("qa_rows_written"),
        "tts_success_rows": sum(r.get("tts_status") == "success" for r in tts_rows),
        "tts_failed_rows": sum(r.get("tts_status") != "success" for r in tts_rows),
        "audio_qc_pass_rows": sum(r.get("audio_qc") == "pass" for r in qc_rows),
        "audio_qc_failed_rows": sum(r.get("audio_qc") == "fail" for r in qc_rows),
        "long_audio_rows": sum(r.get("audio_qc") == "long" for r in qc_rows),
        "final_rows": len(final_rows),
        "train_rows": len(train_rows),
        "valid_rows": len(valid_rows),
        **duration_stats,
        "voice_distribution": _count_by(provenance, "voice"),
        "locale_distribution": _count_by(provenance, "voice_locale"),
        "rate_distribution": _count_by(provenance, "rate"),
        "upstream_dataset_distribution": _count_by(provenance, "upstream_dataset"),
        "wav_disk_usage_bytes": dir_size_bytes(paths.audio_16k),
        "final_validation_error_count": len(validation_errors),
        "final_validation_errors": validation_errors[:100],
    }
    write_json(paths.manifests / "build_summary.json", summary)

    md = [
        "# FINAL BUILD REPORT",
        "",
        f"- Output root: `{paths.root}`",
        f"- QA rows: **{summary['qa_rows']}**",
        f"- TTS success / failed: **{summary['tts_success_rows']} / {summary['tts_failed_rows']}**",
        f"- Audio QC pass / fail / long: **{summary['audio_qc_pass_rows']} / {summary['audio_qc_failed_rows']} / {summary['long_audio_rows']}**",
        f"- Final rows: **{summary['final_rows']}**",
        f"- Train / Valid: **{summary['train_rows']} / {summary['valid_rows']}**",
        f"- Total audio hours: **{summary['total_audio_duration_hours']:.4f}**",
        f"- Duration p50 / p95 / max: **{summary['duration_p50']:.3f}s / {summary['duration_p95']:.3f}s / {summary['duration_max']:.3f}s**",
        f"- Final static validation errors: **{summary['final_validation_error_count']}**",
        "",
        "## Voice distribution",
        "",
        "```json",
        __import__('json').dumps(summary['voice_distribution'], ensure_ascii=False, indent=2),
        "```",
        "",
        "## Locale distribution",
        "",
        "```json",
        __import__('json').dumps(summary['locale_distribution'], ensure_ascii=False, indent=2),
        "```",
        "",
        "## Rate distribution",
        "",
        "```json",
        __import__('json').dumps(summary['rate_distribution'], ensure_ascii=False, indent=2),
        "```",
        "",
        "## 判定",
        "",
        "- `final_validation_error_count == 0` 时，静态数据结构、音频技术格式和 answer 映射验收通过。",
        "- 本报告不评价 Sujet 原始 answer 的语义正确性；这是本阶段明确不执行的任务。",
        "",
    ]
    paths.reports.mkdir(parents=True, exist_ok=True)
    (paths.reports / "FINAL_BUILD_REPORT.md").write_text("\n".join(md), encoding="utf-8")
    return summary
