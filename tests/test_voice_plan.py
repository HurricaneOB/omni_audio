from fin_audio.voice_manager import TEST_TONE_VOICES, assign_voice_and_rate


def test_voice_plan_is_deterministic():
    sid = "a" * 64
    first = assign_voice_and_rate(sid, TEST_TONE_VOICES, ["-4%", "+0%", "+4%"])
    second = assign_voice_and_rate(sid, TEST_TONE_VOICES, ["-4%", "+0%", "+4%"])
    assert first == second
