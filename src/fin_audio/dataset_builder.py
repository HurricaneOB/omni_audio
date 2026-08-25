from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import iter_jsonl, write_jsonl
from .paths import BuildPaths
from .schema import build_training_record, validate_training_record


def build_final_dataset(cfg: dict[str, Any], output_root: str | Path) -> dict[str, Any]:
    """把 Audio-QA 映射成 Qwen3-Omni/ms-swift JSONL，并保留完整 provenance。"""
    paths = BuildPaths.from_root(output_root)
    paths.ensure()
    source = {r["id"]: r for r in iter_jsonl(paths.prepared / "qa_source.jsonl")}
    plan = {r["id"]: r for r in iter_jsonl(paths.prepared / "tts_plan.jsonl")}
    tts = {r["id"]: r for r in iter_jsonl(paths.manifests / "tts_status.jsonl")}
    qc = {r["id"]: r for r in iter_jsonl(paths.manifests / "audio_qc.jsonl")}

    system_prompt = cfg["training_format"]["system_prompt"]
    user_prompt = cfg["training_format"]["user_prompt"]
    all_rows: list[dict[str, Any]] = []
    train_rows: list[dict[str, Any]] = []
    valid_rows: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for sid in sorted(source):
        src = source[sid]
        qcr = qc.get(sid)
        ttsr = tts.get(sid)
        pl = plan.get(sid)
        if not qcr or qcr.get("audio_qc") != "pass" or not ttsr or ttsr.get("tts_status") != "success" or not pl:
            continue

        record = build_training_record(system_prompt, user_prompt, src["assistant_text"], ttsr["audio_wav"])
        errors = validate_training_record(record, source_question=src["source_user_text"])
        if errors:
            failures.append({"id": sid, "failure_reason": "FINAL_SCHEMA_INVALID", "errors": errors})
            continue

        all_rows.append(record)
        if src["split"] == "train":
            train_rows.append(record)
        else:
            valid_rows.append(record)

        provenance.append({
            "id": sid,
            "source_dataset": src["source_dataset"],
            "source_row_id": src["source_row_id"],
            "upstream_dataset": src.get("upstream_dataset"),
            "task_type": src["task_type"],
            "source_user_text": src["source_user_text"],
            "tts_text": pl["tts_text"],
            "assistant_text": src["assistant_text"],
            "split": src["split"],
            "voice": pl["voice"],
            "voice_locale": pl.get("voice_locale"),
            "rate": pl["rate"],
            "pitch": pl["pitch"],
            "audio_wav": str(Path(ttsr["audio_wav"]).resolve()),
            "duration_sec": qcr.get("duration_sec"),
            "sample_rate": qcr.get("sample_rate"),
            "channels": qcr.get("channels"),
            "audio_subtype": qcr.get("subtype"),
            "tts_status": ttsr["tts_status"],
            "audio_qc": qcr["audio_qc"],
            "normalizer_version": pl["normalizer_version"],
            "build_version": pl["build_version"],
        })

    write_jsonl(paths.final / "all.jsonl", all_rows)
    write_jsonl(paths.final / "train.jsonl", train_rows)
    write_jsonl(paths.final / "valid.jsonl", valid_rows)
    write_jsonl(paths.manifests / "provenance.jsonl", provenance)
    write_jsonl(paths.failed / "final_schema_failures.jsonl", failures)
    return {"final_rows": len(all_rows), "train_rows": len(train_rows), "valid_rows": len(valid_rows), "final_schema_failures": len(failures)}
