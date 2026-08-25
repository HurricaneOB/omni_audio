from __future__ import annotations

import hashlib


def stable_sample_id(source_dataset: str, source_row_id: str, user_prompt: str) -> str:
    """用源数据集、源行号和原始问题生成稳定 SHA256 ID。"""
    payload = "\n".join([source_dataset, str(source_row_id), user_prompt]).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def hash_fraction(hex_digest: str, offset: int = 0) -> float:
    """把 SHA256 的 8 个十六进制字符稳定映射到 [0, 1)。"""
    token = hex_digest[offset : offset + 8]
    if len(token) < 8:
        token = hashlib.sha256(hex_digest.encode("utf-8")).hexdigest()[:8]
    return int(token, 16) / float(16**8)


def stable_split(sample_id: str, train_ratio: float) -> str:
    """根据 stable ID 做确定性 train/valid 划分。"""
    if not 0.0 < train_ratio < 1.0:
        raise ValueError("train_ratio 必须位于 (0,1)")
    return "train" if hash_fraction(sample_id) < train_ratio else "valid"


def stable_index(sample_id: str, modulo: int, salt: str) -> int:
    """稳定选择 voice/rate 的索引；salt 用来让不同用途互不耦合。"""
    if modulo <= 0:
        raise ValueError("modulo 必须 > 0")
    digest = hashlib.sha256(f"{salt}:{sample_id}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16) % modulo
