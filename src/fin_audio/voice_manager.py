from __future__ import annotations

from typing import Any

from .ids import stable_index


# 只供 test-tone 离线结构测试使用，不代表真实 Edge voice。
TEST_TONE_VOICES = [
    {"Name": "test-tone-en-US-A", "Locale": "en-US", "Gender": "Test"},
    {"Name": "test-tone-en-GB-B", "Locale": "en-GB", "Gender": "Test"},
    {"Name": "test-tone-en-AU-C", "Locale": "en-AU", "Gender": "Test"},
]

# 保留旧符号别名，仅避免已有第三方测试代码 import 失败；新代码不再使用 mock backend。
MOCK_VOICES = TEST_TONE_VOICES


async def discover_english_voices(allowed_locales: list[str], backend: str) -> list[dict[str, Any]]:
    """动态发现英语 voice；test-tone 仅返回固定测试 voice。"""
    if backend == "test-tone":
        allowed = set(allowed_locales)
        return [v for v in TEST_TONE_VOICES if v["Locale"] in allowed]

    if backend != "edge":
        raise ValueError(f"未知 TTS backend: {backend}")

    # 真实 smoke/live-smoke/full 均进入这里，动态获取当前 Edge 英语 voices。
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
