from __future__ import annotations

import asyncio
import hashlib
import os
import subprocess
from pathlib import Path


async def synthesize_mp3(
    text: str,
    voice: str,
    rate: str,
    pitch: str,
    output_mp3: str | Path,
    backend: str = "edge",
) -> None:
    """把文本合成为 MP3。

    backend="edge":
        正式/可试听模式。调用 Edge-TTS，输出真正包含输入文本语义的语音。

    backend="test-tone":
        纯离线结构测试模式。生成确定性测试音，只验证 MP3→WAV→QC→JSONL 链路，
        明确不代表真实 TTS，也不能用于训练或试听语义验收。

    重要修复：不再存在“找不到 espeak 时静默回退到正弦波”的隐式行为。
    因此只要模式声称使用 Edge，就一定真正调用 Edge；测试音必须显式选择 test-tone。
    """
    target = Path(output_mp3)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.stem + ".part.mp3")
    tmp.unlink(missing_ok=True)

    if backend == "edge":
        # 延迟导入，避免纯离线 test-tone 单元测试必须实际连接 Edge 服务。
        from edge_tts import Communicate

        communicate = Communicate(
            text=text,
            voice=voice,
            rate=rate,
            pitch=pitch,
            volume="+0%",
        )
        await communicate.save(str(tmp))

    elif backend == "test-tone":
        # 该测试音只服务于离线结构回归测试；不能被误认为“语音合成成功”。
        # 使用 sample text + voice 的 hash 生成稳定频率，使重跑结果可复现。
        duration = min(4.0, max(0.8, 0.22 * max(1, len(text.split()))))
        digest = hashlib.sha256(f"{voice}:{text}".encode("utf-8")).hexdigest()
        frequency = 330 + (int(digest[:4], 16) % 330)
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi",
            "-i", f"sine=frequency={frequency}:sample_rate=24000:duration={duration:.3f}",
            "-ac", "1", "-b:a", "48k", str(tmp),
        ]
        await asyncio.to_thread(
            subprocess.run,
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    else:
        raise ValueError(f"未知 TTS backend: {backend}")

    if not tmp.exists() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("TTS_NO_AUDIO: 合成结束但 MP3 为空")

    os.replace(tmp, target)
