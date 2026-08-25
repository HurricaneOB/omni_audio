from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    """读取 YAML 配置，并做最小结构校验。"""
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError(f"配置文件必须是 YAML mapping: {config_path}")
    for key in ("source", "split", "edge_tts", "audio", "training_format"):
        if key not in cfg:
            raise ValueError(f"配置缺少必需区块: {key}")
    return cfg


def with_output_override(cfg: dict[str, Any], output_root: str | Path) -> dict[str, Any]:
    """返回配置副本，并写入本次运行的输出根目录。"""
    out = deepcopy(cfg)
    out.setdefault("runtime", {})["output_root"] = str(Path(output_root).expanduser().resolve())
    return out


def project_root_from_config(config_path: str | Path) -> Path:
    """根据 configs/build.yaml 推导代码项目根目录。"""
    path = Path(config_path).resolve()
    return path.parent.parent
