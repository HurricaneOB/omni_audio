from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

# 货币符号到自然发音单位的映射；仅在明确数字金额时展开。
_CURRENCY = {
    "$": "US dollars",
    "€": "euros",
    "£": "British pounds",
    "¥": "Japanese yen",
}

# 常见数量级缩写；只在货币金额中使用，避免把普通字母误改写。
_SCALE = {
    "k": "thousand",
    "m": "million",
    "mn": "million",
    "b": "billion",
    "bn": "billion",
    "t": "trillion",
    "tn": "trillion",
}


def load_exact_replacements(path: str | Path) -> dict[str, str]:
    """读取版本化金融发音词典。"""
    p = Path(path)
    if not p.exists():
        return {}
    data: dict[str, Any] = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    mapping = data.get("exact_replacements", {})
    if not isinstance(mapping, dict):
        raise ValueError("tts_pronunciation.yaml 的 exact_replacements 必须是 mapping")
    return {str(k): str(v) for k, v in mapping.items()}


def _replace_currency_amounts(text: str) -> str:
    """把 $1.25bn 这类金额展开为可读形式，同时保留原始数值。"""
    pattern = re.compile(r"([\$€£¥])\s*([+-]?[0-9][0-9,]*(?:\.\d+)?)\s*(k|mn|m|bn|b|tn|t)?\b", re.I)

    def repl(match: re.Match[str]) -> str:
        symbol, number, scale = match.group(1), match.group(2), match.group(3)
        scale_text = f" {_SCALE[scale.lower()]}" if scale else ""
        return f"{number}{scale_text} {_CURRENCY[symbol]}"

    return pattern.sub(repl, text)


def _replace_currency_pairs(text: str) -> str:
    """把 EUR/USD 这类外汇对改为明确的字母读法。"""
    pattern = re.compile(r"\b(USD|EUR|GBP|JPY|CNY|AUD|CAD|CHF)/(USD|EUR|GBP|JPY|CNY|AUD|CAD|CHF)\b")

    def spell(code: str) -> str:
        return " ".join(code)

    return pattern.sub(lambda m: f"{spell(m.group(1))} to {spell(m.group(2))}", text)


def normalize_tts_text(source_text: str, exact_replacements: dict[str, str] | None = None) -> str:
    """对用户问题做保守、确定性的金融发音规范化，不使用 LLM 重写。"""
    if not isinstance(source_text, str):
        raise TypeError("source_text 必须是字符串")

    # 仅清理首尾空白和连续空白；原始 source_user_text 在上游仍完整保留。
    text = re.sub(r"\s+", " ", source_text.strip())

    # 先处理更具体的结构，避免后面的通用 token 替换破坏它们。
    text = _replace_currency_pairs(text)
    text = _replace_currency_amounts(text)

    # bps 和百分号采用明确金融单位读法；数字本身不改写，降低数量级风险。
    text = re.sub(r"\bbps\b", "basis points", text, flags=re.I)
    text = re.sub(r"(?<=\d)%", " percent", text)

    # 精确发音词典按 key 长度降序替换，避免较短 token 抢先匹配。
    for src, dst in sorted((exact_replacements or {}).items(), key=lambda kv: len(kv[0]), reverse=True):
        text = re.sub(re.escape(src), dst, text, flags=re.I)

    # 再压缩一次空白，确保 TTS 输入稳定。
    return re.sub(r"\s+", " ", text).strip()
