from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Iterator

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


def _load_hf_rows(cfg: dict[str, Any], paths: BuildPaths, cache_dir: str | None, streaming: bool) -> tuple[Iterable[dict[str, Any]], dict[str, Any]]:
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
        ds = load_dataset("parquet", data_files=str(raw_parquet), split="train", cache_dir=cache_dir)
        meta = {"mode": "frozen_parquet", "raw_parquet": str(raw_parquet.resolve()), "fingerprint": getattr(ds, "_fingerprint", None)}
        return ds, meta

    ds = load_dataset(hf_id, split=split, revision=revision, cache_dir=cache_dir, streaming=streaming)
    meta: dict[str, Any] = {
        "mode": "hf_streaming" if streaming else "hf_download",
        "hf_id": hf_id,
        "split": split,
        "requested_revision": revision,
        "fingerprint": getattr(ds, "_fingerprint", None),
    }

    # full 模式把源数据冻结为 parquet，后续重跑优先读本地快照。
    if not streaming:
        raw_parquet.parent.mkdir(parents=True, exist_ok=True)
        tmp_parquet = raw_parquet.with_name(raw_parquet.stem + ".tmp.parquet")
        tmp_parquet.unlink(missing_ok=True)
        ds.to_parquet(str(tmp_parquet))
        tmp_parquet.replace(raw_parquet)
        meta["raw_parquet"] = str(raw_parquet.resolve())
        meta["raw_parquet_sha256"] = file_sha256(raw_parquet)

    # 尽力记录 Hugging Face commit SHA；失败不影响数据构建本身。
    try:
        from huggingface_hub import HfApi
        info = HfApi().dataset_info(hf_id, revision=revision)
        meta["resolved_revision"] = info.sha
    except Exception as exc:
        meta["resolved_revision"] = None
        meta["revision_lookup_warning"] = repr(exc)

    return ds, meta


def prepare_source(
    cfg: dict[str, Any],
    output_root: str | Path,
    source_jsonl: str | Path | None = None,
    limit: int | None = None,
    cache_dir: str | None = None,
    streaming: bool = False,
) -> dict[str, Any]:
    """提取 Sujet direct-QA，原样保留 answer，并建立稳定 ID/split。"""
    paths = BuildPaths.from_root(output_root)
    paths.ensure()

    if source_jsonl:
        source_path = Path(source_jsonl).resolve()
        rows: Iterable[dict[str, Any]] = _iter_local_jsonl(source_path)
        source_meta: dict[str, Any] = {"mode": "local_jsonl", "source_path": str(source_path)}
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
    raw_seen = 0
    qa_seen = 0

    for idx, row in enumerate(rows):
        raw_seen += 1
        if row.get("task_type") != task_type_target:
            continue
        qa_seen += 1

        # 这里只做程序可运行所需的机械字段检查，不检查 answer 的语义/质量。
        question = row.get(question_field)
        answer = row.get(answer_field)
        if not isinstance(question, str) or not question.strip():
            failures.append({"source_row_id": str(idx), "failure_reason": "EMPTY_USER_PROMPT"})
            continue
        if not isinstance(answer, str):
            failures.append({"source_row_id": str(idx), "failure_reason": "SOURCE_SCHEMA_FAILURE", "detail": f"{answer_field} is not string"})
            continue

        sid = stable_sample_id(source_dataset, str(idx), question)
        qa_rows.append({
            "id": sid,
            "source_dataset": source_dataset,
            "source_row_id": str(idx),
            "upstream_dataset": row.get(provenance_field),
            "task_type": task_type_target,
            "source_user_text": question,
            "assistant_text": answer,  # 原始 answer 原样写入，不 strip、不改写。
            "split": stable_split(sid, train_ratio),
        })
        if limit is not None and len(qa_rows) >= limit:
            break

    out_path = paths.prepared / "qa_source.jsonl"
    write_jsonl(out_path, qa_rows)
    write_jsonl(paths.failed / "source_failures.jsonl", failures)

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
    }
    write_json(paths.manifests / "source_snapshot.json", snapshot)
    return snapshot
