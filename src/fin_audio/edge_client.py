from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
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
    """把文本合成为 MP3；生产用 Edge，测试用 mock。"""
    target = Path(output_mp3)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.stem + ".part.mp3")
    tmp.unlink(missing_ok=True)

    if backend == "edge":
        # 延迟导入，避免离线单元测试必须安装/联网调用 Edge-TTS。
        from edge_tts import Communicate

        communicate = Communicate(text=text, voice=voice, rate=rate, pitch=pitch, volume="+0%")
        await communicate.save(str(tmp))
    elif backend == "mock":
        # mock 只用于工程验收：优先用本地 espeak 生成“真的可听问题”，再转成 24 kHz MP3。
        # 如果环境没有 espeak，则退回确定性正弦信号；两者都不会进入正式 full 数据。
        espeak = shutil.which("espeak") or shutil.which("espeak-ng")
        if espeak:
            espeak_wav = target.with_name(target.stem + ".espeak.wav")
            espeak_wav.unlink(missing_ok=True)
            try:
                await asyncio.to_thread(
                    subprocess.run,
                    [espeak, "-w", str(espeak_wav), "-s", "155", text],
                    check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                cmd = [
                    "ffmpeg", "-y", "-loglevel", "error", "-i", str(espeak_wav),
                    "-ar", "24000", "-ac", "1", "-b:a", "48k", str(tmp),
                ]
                await asyncio.to_thread(subprocess.run, cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            finally:
                espeak_wav.unlink(missing_ok=True)
        else:
            duration = min(4.0, max(0.8, 0.22 * max(1, len(text.split()))))
            digest = hashlib.sha256(f"{voice}:{text}".encode("utf-8")).hexdigest()
            frequency = 330 + (int(digest[:4], 16) % 330)
            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "lavfi",
                "-i", f"sine=frequency={frequency}:sample_rate=24000:duration={duration:.3f}",
                "-ac", "1", "-b:a", "48k", str(tmp),
            ]
            await asyncio.to_thread(subprocess.run, cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        raise ValueError(f"未知 TTS backend: {backend}")

    if not tmp.exists() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("TTS_NO_AUDIO: 合成结束但 MP3 为空")
    os.replace(tmp, target)
