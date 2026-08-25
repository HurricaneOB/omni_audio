from __future__ import annotations

from typing import Any

from .ids import stable_index


MOCK_VOICES = [
    {"Name": "mock-en-US-A", "Locale": "en-US", "Gender": "Female"},
    {"Name": "mock-en-GB-B", "Locale": "en-GB", "Gender": "Male"},
    {"Name": "mock-en-AU-C", "Locale": "en-AU", "Gender": "Female"},
]


async def discover_english_voices(allowed_locales: list[str], backend: str) -> list[dict[str, Any]]:
    """动态发现英语 voice；mock 模式返回固定假 voice 供离线全链路测试。"""
    if backend == "mock":
        return [v for v in MOCK_VOICES if v["Locale"] in set(allowed_locales)]

    if backend != "edge":
        raise ValueError(f"未知 TTS backend: {backend}")

    # 延迟导入，保证没有 edge-tts 时仍能运行纯离线 mock 测试。
    from edge_tts import VoicesManager

    manager = await VoicesManager.create()
    voices = manager.find(Language="en")
    allowed = set(allowed_locales)
    cleaned = [v for v in voices if v.get("Locale") in allowed and v.get("Name")]
    cleaned.sort(key=lambda v: (v.get("Locale", ""), v.get("Name", "")))
    if not cleaned:
        raise RuntimeError("Edge-TTS 运行时未发现满足 locale 配置的英语 voice")
    return cleaned


def assign_voice_and_rate(sample_id: str, voices: list[dict[str, Any]], rates: list[str]) -> tuple[dict[str, Any], str]:
    """基于 sample_id 稳定选择一个 voice 和一个 rate。"""
    if not voices:
        raise ValueError("voice pool 不能为空")
    if not rates:
        raise ValueError("rates 不能为空")
    voice = voices[stable_index(sample_id, len(voices), "voice")]
    rate = rates[stable_index(sample_id, len(rates), "rate")]
    return voice, rate
