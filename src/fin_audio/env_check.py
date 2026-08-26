from __future__ import annotations

import importlib.metadata
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .io_utils import write_json
from .paths import BuildPaths


def _version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def run_env_check(output_root: str | Path, backend: str, source_mode: str) -> dict[str, Any]:
    """检查第一阶段数据工程环境。

    edge 模式要求 edge-tts；test-tone 模式仅用于纯离线结构测试。
    两种模式都要求 FFmpeg，因为最终音频都必须经过统一标准化链路。
    """
    paths = BuildPaths.from_root(output_root)
    paths.ensure()

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError(
            "未找到 ffmpeg。请先按项目文档把 FFmpeg 安装/链接到当前 uv 虚拟环境 PATH。"
        )
    ffmpeg_version = subprocess.check_output([ffmpeg, "-version"], text=True).splitlines()[0]

    packages = {
        name: _version(name)
        for name in (
            "PyYAML", "numpy", "soundfile", "datasets", "pyarrow",
            "edge-tts", "huggingface-hub", "tqdm"
        )
    }
    missing: list[str] = []
    if backend == "edge" and not packages["edge-tts"]:
        missing.append("edge-tts")
    if source_mode == "hf" and not packages["datasets"]:
        missing.append("datasets")
    if not packages["soundfile"]:
        missing.append("soundfile")
    if missing:
        raise RuntimeError(
            "缺少依赖: " + ", ".join(missing) + "。请执行 uv pip install -r requirements.txt"
        )

    report = {
        "python": sys.version,
        "python_executable": sys.executable,
        "ffmpeg": ffmpeg,
        "ffmpeg_version": ffmpeg_version,
        "packages": packages,
        "backend": backend,
        "source_mode": source_mode,
        "output_root": str(paths.root),
        "semantic_audio_expected": backend == "edge",
    }
    write_json(paths.manifests / "environment.json", report)
    return report
