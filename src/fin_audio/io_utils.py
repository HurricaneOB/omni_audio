from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Iterator


def atomic_write_text(path: str | Path, text: str) -> None:
    """先写临时文件再原子替换，避免中断时留下半个文件。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json(path: str | Path, obj: Any) -> None:
    """原子写入 UTF-8 JSON。"""
    atomic_write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def read_json(path: str | Path) -> Any:
    """读取 JSON 文件。"""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> int:
    """原子写入 JSONL，并返回写入行数。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    count = 0
    with tmp.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    os.replace(tmp, path)
    return count


def iter_jsonl(path: str | Path) -> Iterator[dict[str, Any]]:
    """逐行读取 JSONL，适合数万条数据，避免一次性占满内存。"""
    with Path(path).open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSONL 解析失败: {path}:{line_no}: {exc}") from exc
            if not isinstance(obj, dict):
                raise ValueError(f"JSONL 每行必须是 object: {path}:{line_no}")
            yield obj


def file_sha256(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    """计算文件 SHA256，用于数据快照和构建审计。"""
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def dir_size_bytes(path: str | Path) -> int:
    """统计目录中常规文件占用字节数。"""
    total = 0
    root = Path(path)
    if not root.exists():
        return 0
    for p in root.rglob("*"):
        if p.is_file() and not p.is_symlink():
            try:
                total += p.stat().st_size
            except FileNotFoundError:
                pass
    return total
