from fin_audio.domain_gate import decide_provenance, decide_source, validate_boundary_sentinel


def _cfg():
    return {
        "source": {
            "question_field": "user_prompt",
            "provenance_field": "dataset",
            "domain_filter": {
                "enabled": True,
                "policy": "sujet_audited_finance_qa_v1",
                "finance_alpaca_max_source_row_id": 62179,
                "allowed_full_qa_datasets": ["adityamavle/FinRiskAnalysis"],
                "boundary_sentinel": {
                    "source_row_id": 62180,
                    "upstream_dataset": "gbharti/finance-alpaca",
                    "user_prompt": "Question:\nGive three tips for staying healthy.",
                },
            },
        }
    }


def test_last_audited_finance_alpaca_row_is_kept():
    d = decide_source(62179, {"dataset": "gbharti/finance-alpaca"}, _cfg())
    assert d.keep is True


def test_first_canonical_stanford_alpaca_row_is_rejected():
    d = decide_source(62180, {"dataset": "gbharti/finance-alpaca"}, _cfg())
    assert d.keep is False


def test_finrisk_qa_is_kept():
    d = decide_source(138300, {"dataset": "adityamavle/FinRiskAnalysis"}, _cfg())
    assert d.keep is True


def test_unknown_upstream_fails_closed():
    d = decide_source(10, {"dataset": "unknown/source"}, _cfg())
    assert d.keep is False


def test_boundary_sentinel_exact_match_passes():
    validate_boundary_sentinel(
        62180,
        {
            "dataset": "gbharti/finance-alpaca",
            "user_prompt": "Question:\nGive three tips for staying healthy.",
        },
        _cfg(),
    )


def test_repair_provenance_uses_same_policy():
    d = decide_provenance(
        {"source_row_id": "62179", "upstream_dataset": "gbharti/finance-alpaca"},
        _cfg(),
    )
    assert d.keep is True
