from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import iter_jsonl, write_jsonl


class JsonlKeyedStore:
    """以 id 为主键维护 JSONL 状态，解决重复运行时的去重与覆盖问题。"""

    def __init__(self, path: str | Path, key: str = "id") -> None:
        self.path = Path(path)
        self.key = key
        self.rows: dict[str, dict[str, Any]] = {}
        if self.path.exists():
            for row in iter_jsonl(self.path):
                if key in row:
                    self.rows[str(row[key])] = row

    def get(self, key_value: str) -> dict[str, Any] | None:
        return self.rows.get(str(key_value))

    def upsert(self, row: dict[str, Any]) -> None:
        if self.key not in row:
            raise KeyError(f"manifest row 缺少主键 {self.key}")
        self.rows[str(row[self.key])] = row

    def flush(self) -> int:
        ordered = [self.rows[k] for k in sorted(self.rows)]
        return write_jsonl(self.path, ordered)
