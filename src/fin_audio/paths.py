from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BuildPaths:
    """统一管理数据构建输出目录，避免脚本之间各自拼路径。"""

    root: Path

    @classmethod
    def from_root(cls, root: str | Path) -> "BuildPaths":
        return cls(Path(root).expanduser().resolve())

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def prepared(self) -> Path:
        return self.root / "prepared"

    @property
    def tmp_mp3(self) -> Path:
        return self.root / "tmp_mp3"

    @property
    def audio_16k(self) -> Path:
        return self.root / "audio_16k"

    @property
    def long_audio(self) -> Path:
        return self.root / "long_audio"

    @property
    def failed(self) -> Path:
        return self.root / "failed"

    @property
    def final(self) -> Path:
        return self.root / "final"

    @property
    def manifests(self) -> Path:
        return self.root / "manifests"

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    def ensure(self) -> None:
        """创建所有标准目录；重复调用不会报错。"""
        for p in (
            self.raw,
            self.prepared,
            self.tmp_mp3,
            self.audio_16k,
            self.long_audio,
            self.failed,
            self.final,
            self.manifests,
            self.reports,
        ):
            p.mkdir(parents=True, exist_ok=True)
