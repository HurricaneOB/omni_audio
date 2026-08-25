from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 允许在尚未 pip install -e . 时直接运行脚本。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fin_audio.config import load_config


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """给每个阶段脚本添加一致的 config/output 参数。"""
    parser.add_argument("--config", default=str(PROJECT_ROOT / "configs" / "build.yaml"), help="构建 YAML 配置")
    parser.add_argument("--output-root", required=True, help="本次测试/全量数据集输出根目录")


def load_from_args(args: argparse.Namespace):
    return load_config(args.config)
