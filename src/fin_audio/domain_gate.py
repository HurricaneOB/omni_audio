from __future__ import annotations

from dataclasses import dataclass
from typing import Any

POLICY_NAME = "sujet_audited_finance_qa_v1"


@dataclass(frozen=True)
class DomainDecision:
    keep: bool
    status: str
    reason: str
    policy: str = POLICY_NAME


def _domain_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    return dict(cfg.get("source", {}).get("domain_filter") or {})


def is_enabled(cfg: dict[str, Any]) -> bool:
    return bool(_domain_cfg(cfg).get("enabled", False))


def assert_supported_policy(cfg: dict[str, Any]) -> None:
    dc = _domain_cfg(cfg)
    if not dc.get("enabled", False):
        return
    got = str(dc.get("policy", ""))
    if got != POLICY_NAME:
        raise ValueError(
            f"Unsupported domain filter policy: {got!r}; expected {POLICY_NAME!r}"
        )


def _decide_from_lineage(upstream: Any, source_row_id: int, cfg: dict[str, Any]) -> DomainDecision:
    """Apply the audited, deterministic finance-only policy.

    This is intentionally lineage-based rather than a keyword classifier.
    For the pinned Sujet revision, all direct-QA rows in finance-alpaca before
    the audited Stanford-Alpaca boundary are retained, as are audited direct-QA
    rows from explicitly allowed finance-native upstream datasets.
    """
    dc = _domain_cfg(cfg)
    if not dc.get("enabled", False):
        return DomainDecision(True, "KEEP_UNFILTERED", "domain_filter_disabled")

    assert_supported_policy(cfg)
    allowed = set(dc.get("allowed_full_qa_datasets") or [])
    if upstream in allowed:
        return DomainDecision(True, "FINANCE_KEEP", f"audited_upstream:{upstream}")

    if upstream == "gbharti/finance-alpaca":
        max_finance_row = int(dc["finance_alpaca_max_source_row_id"])
        if source_row_id <= max_finance_row:
            return DomainDecision(
                True,
                "FINANCE_KEEP",
                "finance_alpaca_audited_finance_prefix",
            )
        return DomainDecision(
            False,
            "DOMAIN_REJECT",
            "canonical_stanford_alpaca_or_unverifiable_tail",
        )

    return DomainDecision(False, "DOMAIN_REJECT", f"unreviewed_upstream:{upstream}")


def decide_source(row_index: int, row: dict[str, Any], cfg: dict[str, Any]) -> DomainDecision:
    provenance_field = cfg["source"]["provenance_field"]
    return _decide_from_lineage(row.get(provenance_field), int(row_index), cfg)


def decide_provenance(row: dict[str, Any], cfg: dict[str, Any]) -> DomainDecision:
    try:
        source_row_id = int(row["source_row_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid provenance source_row_id: {row.get('source_row_id')!r}") from exc
    return _decide_from_lineage(row.get("upstream_dataset"), source_row_id, cfg)


def validate_boundary_sentinel(row_index: int, row: dict[str, Any], cfg: dict[str, Any]) -> None:
    """Abort if the pinned source layout no longer matches the audited boundary."""
    dc = _domain_cfg(cfg)
    if not dc.get("enabled", False):
        return
    sentinel = dc.get("boundary_sentinel") or {}
    expected_idx = int(sentinel.get("source_row_id", -1))
    if row_index != expected_idx:
        return

    provenance_field = cfg["source"]["provenance_field"]
    question_field = cfg["source"]["question_field"]
    got_upstream = row.get(provenance_field)
    got_prompt = row.get(question_field)
    if (
        got_upstream != sentinel.get("upstream_dataset")
        or got_prompt != sentinel.get("user_prompt")
    ):
        raise RuntimeError(
            "DOMAIN_BOUNDARY_SENTINEL_MISMATCH: pinned Sujet layout changed. "
            f"row={row_index}, upstream={got_upstream!r}, prompt={got_prompt!r}. "
            "Stop before TTS and re-audit the source."
        )


def expected_full_scan(cfg: dict[str, Any]) -> dict[str, int]:
    dc = _domain_cfg(cfg)
    return {str(k): int(v) for k, v in (dc.get("expected_full_scan") or {}).items()}
