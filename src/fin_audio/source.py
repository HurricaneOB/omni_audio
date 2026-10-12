from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Iterator

from .domain_gate import (
    DomainDecision,
    assert_supported_policy,
    decide_source,
    expected_full_scan,
    is_enabled as domain_filter_enabled,
    validate_boundary_sentinel,
)
from .ids import stable_sample_id, stable_split
from .io_utils import file_sha256, write_json, write_jsonl
from .paths import BuildPaths


def _iter_local_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """读取本地 fixture/source JSONL，供离线 smoke test 使用。"""
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"本地源第 {line_no} 行不是 JSON object")
            yield row


def _load_hf_rows(
    cfg: dict[str, Any],
    paths: BuildPaths,
    cache_dir: str | None,
    streaming: bool,
) -> tuple[Iterable[dict[str, Any]], dict[str, Any]]:
    """从 Hugging Face 获取 Sujet；full 模式落盘 raw parquet，smoke 可流式读取。"""
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError("缺少 datasets，请先 uv pip install -r requirements.txt") from exc

    source_cfg = cfg["source"]
    hf_id = source_cfg["hf_id"]
    split = source_cfg.get("split", "train")
    revision = source_cfg.get("revision")
    raw_parquet = paths.raw / "sujet_train.parquet"

    if not streaming and raw_parquet.exists():
        ds = load_dataset(
            "parquet",
            data_files=str(raw_parquet),
            split="train",
            cache_dir=cache_dir,
        )
        meta = {
            "mode": "frozen_parquet",
            "raw_parquet": str(raw_parquet.resolve()),
            "raw_parquet_sha256": file_sha256(raw_parquet),
            "fingerprint": getattr(ds, "_fingerprint", None),
            "requested_revision": revision,
        }
        return ds, meta

    ds = load_dataset(
        hf_id,
        split=split,
        revision=revision,
        cache_dir=cache_dir,
        streaming=streaming,
    )
    meta: dict[str, Any] = {
        "mode": "hf_streaming" if streaming else "hf_download",
        "hf_id": hf_id,
        "split": split,
        "requested_revision": revision,
        "fingerprint": getattr(ds, "_fingerprint", None),
    }

    if not streaming:
        raw_parquet.parent.mkdir(parents=True, exist_ok=True)
        tmp_parquet = raw_parquet.with_name(raw_parquet.stem + ".tmp.parquet")
        tmp_parquet.unlink(missing_ok=True)
        ds.to_parquet(str(tmp_parquet))
        tmp_parquet.replace(raw_parquet)
        meta["raw_parquet"] = str(raw_parquet.resolve())
        meta["raw_parquet_sha256"] = file_sha256(raw_parquet)

    try:
        from huggingface_hub import HfApi
        info = HfApi().dataset_info(hf_id, revision=revision)
        meta["resolved_revision"] = info.sha
    except Exception as exc:
        meta["resolved_revision"] = None
        meta["revision_lookup_warning"] = repr(exc)

    return ds, meta


def _assert_full_domain_counts(
    cfg: dict[str, Any], qa_seen: int, kept: int, rejected: int
) -> None:
    expected = expected_full_scan(cfg)
    if not expected:
        return
    got = {"raw_qa_rows": qa_seen, "kept_rows": kept, "rejected_rows": rejected}
    mismatch = {
        key: {"expected": expected[key], "got": got.get(key)}
        for key in expected
        if got.get(key) != expected[key]
    }
    if mismatch:
        raise RuntimeError(
            "DOMAIN_FULL_SCAN_COUNT_MISMATCH: audited Sujet counts changed. "
            f"mismatch={mismatch}. Stop before TTS and re-audit."
        )


def prepare_source(
    cfg: dict[str, Any],
    output_root: str | Path,
    source_jsonl: str | Path | None = None,
    limit: int | None = None,
    cache_dir: str | None = None,
    streaming: bool = False,
) -> dict[str, Any]:
    """提取 Sujet direct-QA，在进入 TTS 前执行可审计金融域过滤。"""
    paths = BuildPaths.from_root(output_root)
    paths.ensure()
    assert_supported_policy(cfg)

    if source_jsonl:
        source_path = Path(source_jsonl).resolve()
        rows: Iterable[dict[str, Any]] = _iter_local_jsonl(source_path)
        source_meta: dict[str, Any] = {
            "mode": "local_jsonl",
            "source_path": str(source_path),
        }
    else:
        rows, source_meta = _load_hf_rows(cfg, paths, cache_dir, streaming)

    source_cfg = cfg["source"]
    task_type_target = source_cfg["task_type"]
    question_field = source_cfg["question_field"]
    answer_field = source_cfg["answer_field"]
    provenance_field = source_cfg["provenance_field"]
    train_ratio = float(cfg["split"]["train"])
    source_dataset = source_cfg["hf_id"]

    qa_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    domain_rejections: list[dict[str, Any]] = []
    raw_seen = 0
    qa_seen = 0
    domain_rejected = 0
    upstream_qa: Counter[str] = Counter()
    upstream_kept: Counter[str] = Counter()
    upstream_rejected: Counter[str] = Counter()

    sentinel_cfg = (source_cfg.get("domain_filter") or {}).get("boundary_sentinel") or {}
    sentinel_index = int(sentinel_cfg.get("source_row_id", -1))
    sentinel_seen = False

    for idx, row in enumerate(rows):
        raw_seen += 1

        if domain_filter_enabled(cfg) and idx == sentinel_index:
            validate_boundary_sentinel(idx, row, cfg)
            sentinel_seen = True

        # 任务形态过滤：QA != 金融。金融域过滤在下面单独执行。
        if row.get("task_type") != task_type_target:
            continue
        qa_seen += 1

        upstream = row.get(provenance_field)
        upstream_qa[str(upstream)] += 1

        question = row.get(question_field)
        answer = row.get(answer_field)
        if not isinstance(question, str) or not question.strip():
            failures.append(
                {"source_row_id": str(idx), "failure_reason": "EMPTY_USER_PROMPT"}
            )
            continue
        if not isinstance(answer, str):
            failures.append(
                {
                    "source_row_id": str(idx),
                    "failure_reason": "SOURCE_SCHEMA_FAILURE",
                    "detail": f"{answer_field} is not string",
                }
            )
            continue

        # 本地 fixture 是工程 smoke 接口，不扩张生产 allowlist。
        if source_jsonl is not None:
            decision = DomainDecision(
                True, "FINANCE_KEEP", "explicit_local_test_fixture"
            )
        else:
            decision = decide_source(idx, row, cfg)

        if not decision.keep:
            domain_rejected += 1
            upstream_rejected[str(upstream)] += 1
            domain_rejections.append(
                {
                    "source_row_id": str(idx),
                    "upstream_dataset": upstream,
                    "task_type": task_type_target,
                    "source_user_text": question,
                    "assistant_text": answer,
                    "domain_status": decision.status,
                    "domain_reason": decision.reason,
                    "domain_policy": decision.policy,
                }
            )
            continue

        upstream_kept[str(upstream)] += 1
        sid = stable_sample_id(source_dataset, str(idx), question)
        qa_rows.append(
            {
                "id": sid,
                "source_dataset": source_dataset,
                "source_row_id": str(idx),
                "upstream_dataset": upstream,
                "task_type": task_type_target,
                "source_user_text": question,
                "assistant_text": answer,  # 原始 answer 原样保留。
                "split": stable_split(sid, train_ratio),
                "domain_status": decision.status,
                "domain_reason": decision.reason,
                "domain_policy": decision.policy,
            }
        )

        # limit 只用于 smoke；它不是全量金融纯度审计。
        if limit is not None and len(qa_rows) >= limit:
            break

    full_domain_scan = source_jsonl is None and not streaming and limit is None
    if domain_filter_enabled(cfg) and full_domain_scan:
        if sentinel_index >= 0 and not sentinel_seen:
            raise RuntimeError("DOMAIN_BOUNDARY_SENTINEL_NOT_SEEN")
        _assert_full_domain_counts(cfg, qa_seen, len(qa_rows), domain_rejected)

    out_path = paths.prepared / "qa_source.jsonl"
    write_jsonl(out_path, qa_rows)
    write_jsonl(paths.failed / "source_failures.jsonl", failures)
    write_jsonl(paths.failed / "domain_rejections.jsonl", domain_rejections)

    snapshot = {
        **source_meta,
        "source_dataset": source_dataset,
        "raw_rows_seen": raw_seen,
        "qa_rows_seen": qa_seen,
        "qa_rows_written": len(qa_rows),
        "source_failures": len(failures),
        "limit": limit,
        "streaming": streaming,
        "qa_source_path": str(out_path.resolve()),
        "domain_filter_enabled": domain_filter_enabled(cfg),
        "domain_policy": (source_cfg.get("domain_filter") or {}).get("policy"),
        "domain_full_scan": full_domain_scan,
        "domain_rejected_rows": domain_rejected,
        "upstream_qa_distribution": dict(sorted(upstream_qa.items())),
        "upstream_kept_distribution": dict(sorted(upstream_kept.items())),
        "upstream_rejected_distribution": dict(sorted(upstream_rejected.items())),
        "boundary_sentinel_seen": sentinel_seen,
    }
    write_json(paths.manifests / "source_snapshot.json", snapshot)
    return snapshot
