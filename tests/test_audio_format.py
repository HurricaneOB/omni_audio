from pathlib import Path
import subprocess

from fin_audio.audio_utils import inspect_wav


def test_pcm16_16k_mono(tmp_path: Path):
    wav = tmp_path / "x.wav"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
        "-i", "sine=frequency=440:sample_rate=16000:duration=1",
        "-ac", "1", "-c:a", "pcm_s16le", str(wav)
    ], check=True)
    info = inspect_wav(wav)
    assert info["ok"]
    assert info["sample_rate"] == 16000
    assert info["channels"] == 1
    assert info["subtype"] == "PCM_16"
    assert not info["is_silent"]
