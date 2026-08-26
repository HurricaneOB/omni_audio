import re
from pathlib import Path


def _case_block(name: str) -> str:
    script = (Path(__file__).resolve().parents[1] / "run_build.sh").read_text(encoding="utf-8")
    pattern = rf"(?ms)^  {re.escape(name)}\)\n(.*?)(?=^  [a-zA-Z-]+\)|^esac$)"
    m = re.search(pattern, script)
    assert m, f"没有找到 case block: {name}"
    return m.group(1)


def test_smoke_mode_uses_real_edge_backend():
    """回归测试：smoke 不能再绑定 mock/test-tone。"""
    block = _case_block("smoke")
    assert 'TTS_BACKEND="edge"' in block
    assert 'TTS_BACKEND="test-tone"' not in block


def test_offline_smoke_is_explicit_test_tone():
    """纯离线模式必须显式命名为 test-tone，避免误当真实语音。"""
    block = _case_block("offline-smoke")
    assert 'TTS_BACKEND="test-tone"' in block
    assert 'TTS_BACKEND="edge"' not in block
