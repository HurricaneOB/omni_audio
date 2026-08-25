from fin_audio.finance_pronunciation import normalize_tts_text


def test_finance_units_are_conservative():
    out = normalize_tts_text("A yield rose 25 bps to 4.50%.")
    assert "25 basis points" in out
    assert "4.50 percent" in out
    assert "25 percent" not in out


def test_currency_scale_is_not_downgraded():
    out = normalize_tts_text("Revenue was $1.25bn.")
    assert "1.25 billion US dollars" in out
    assert "million" not in out


def test_source_semantic_numbers_preserved():
    src = "The spread is -12.5 bps."
    out = normalize_tts_text(src)
    assert "-12.5" in out
    assert "basis points" in out
