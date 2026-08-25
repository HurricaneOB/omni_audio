from __future__ import annotations

from pathlib import Path
from typing import Any


def build_training_record(system_prompt: str, user_prompt: str, assistant_text: str, audio_wav: str) -> dict[str, Any]:
    """构造 ms-swift/Qwen3-Omni 标准 messages + audios 记录。"""
    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": assistant_text},
        ],
        "audios": [str(Path(audio_wav).resolve())],
    }


def validate_training_record(record: dict[str, Any], source_question: str | None = None) -> list[str]:
    """静态检查最终训练结构；不加载 Qwen3-Omni 模型。"""
    errors: list[str] = []
    messages = record.get("messages")
    audios = record.get("audios")
    if not isinstance(messages, list):
        return ["messages_not_list"]
    if not isinstance(audios, list) or len(audios) != 1:
        errors.append("audios_must_have_one_item")
    roles = [m.get("role") for m in messages if isinstance(m, dict)]
    for role in ("system", "user", "assistant"):
        if role not in roles:
            errors.append(f"missing_role:{role}")

    user_contents = [m.get("content", "") for m in messages if isinstance(m, dict) and m.get("role") == "user"]
    user_text = "\n".join(str(x) for x in user_contents)
    if user_text.count("<audio>") != 1:
        errors.append("audio_token_count_not_one")
    if source_question and source_question.strip() and source_question.strip() in user_text:
        errors.append("question_transcript_leakage")

    if isinstance(audios, list) and len(audios) == 1 and not Path(audios[0]).exists():
        errors.append("audio_path_missing")
    return errors
