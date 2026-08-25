from fin_audio.schema import build_training_record


def test_answer_is_preserved_exactly(tmp_path):
    wav = tmp_path / "x.wav"
    wav.write_bytes(b"placeholder")
    answer = "  Yes.\nSecond line remains exactly.  "
    record = build_training_record("system", "<audio>task", answer, str(wav))
    assert record["messages"][-1]["content"] == answer
