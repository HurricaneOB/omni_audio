from __future__ import annotations

import math
import os
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf


def ffmpeg_to_pcm16_wav(src_mp3: str | Path, dst_wav: str | Path, sample_rate: int = 16000) -> None:
    """使用 FFmpeg 把 Edge MP3 原子转换成 16 kHz mono PCM16 WAV。"""
    src = Path(src_mp3)
    dst = Path(dst_wav)
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.stem + ".tmp.wav")
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(src),
        "-ac", "1",
        "-ar", str(sample_rate),
        "-c:a", "pcm_s16le",
        str(tmp),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if not tmp.exists() or tmp.stat().st_size == 0:
            raise RuntimeError("FFmpeg 未生成有效 WAV")
        os.replace(tmp, dst)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def inspect_wav(path: str | Path, silence_rms_threshold: float = 1e-5) -> dict[str, Any]:
    """读取 WAV 技术属性并计算 duration、peak、RMS、静音判断。"""
    p = Path(path)
    if not p.exists():
        return {"ok": False, "failure_reason": "AUDIO_MISSING", "audio_wav": str(p)}
    if p.stat().st_size == 0:
        return {"ok": False, "failure_reason": "AUDIO_EMPTY", "audio_wav": str(p)}

    try:
        info = sf.info(str(p))
        audio, sr = sf.read(str(p), always_2d=True, dtype="float32")
    except Exception as exc:
        return {"ok": False, "failure_reason": "AUDIO_DECODE_FAILED", "error": repr(exc), "audio_wav": str(p)}

    if audio.size == 0:
        return {"ok": False, "failure_reason": "AUDIO_EMPTY", "audio_wav": str(p)}

    finite = bool(np.isfinite(audio).all())
    peak = float(np.max(np.abs(audio))) if finite else math.nan
    rms = float(np.sqrt(np.mean(np.square(audio)))) if finite else math.nan
    duration = float(len(audio) / sr) if sr else 0.0

    return {
        "ok": finite,
        "failure_reason": None if finite else "AUDIO_NONFINITE",
        "audio_wav": str(p.resolve()),
        "sample_rate": int(sr),
        "channels": int(audio.shape[1]),
        "subtype": info.subtype,
        "format": info.format,
        "frames": int(info.frames),
        "duration_sec": duration,
        "peak": peak,
        "rms": rms,
        "is_silent": bool(finite and rms <= silence_rms_threshold),
        "file_size_bytes": p.stat().st_size,
    }
