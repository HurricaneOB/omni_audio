from pathlib import Path
import subprocess

from fin_audio.schema import build_training_record, validate_training_record


def test_qwen_ms_swift_schema(tmp_path: Path):
    wav = tmp_path / "q.wav"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
        "-i", "sine=frequency=440:sample_rate=16000:duration=1",
        "-ac", "1", "-c:a", "pcm_s16le", str(wav)
    ], check=True)
    record = build_training_record(
        "You are a professional financial assistant.",
        "<audio>Please answer the financial question in the audio.",
        "Original answer.",
        str(wav),
    )
    assert validate_training_record(record, "What is duration?") == []
    assert record["messages"][1]["content"].count("<audio>") == 1
    assert len(record["audios"]) == 1
