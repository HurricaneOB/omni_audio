from fin_audio.ids import stable_sample_id, stable_split, stable_index


def test_stable_id_repeatable():
    a = stable_sample_id("ds", "1", "hello")
    b = stable_sample_id("ds", "1", "hello")
    assert a == b and len(a) == 64


def test_split_and_indices_repeatable():
    sid = stable_sample_id("ds", "2", "question")
    assert stable_split(sid, 0.98) == stable_split(sid, 0.98)
    assert stable_index(sid, 5, "voice") == stable_index(sid, 5, "voice")
