#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fin_audio.config import load_config
from fin_audio.domain_gate import decide_provenance
from fin_audio.io_utils import iter_jsonl, write_json, write_jsonl


def sid_from_final_row(row: dict) -> str:
    audios = row.get("audios")
    if not isinstance(audios, list) or len(audios) != 1:
        raise ValueError(f"Invalid audios field: {audios!r}")
    return Path(audios[0]).stem


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Build a finance-only release from an already-built polluted full without regenerating WAV"
    )
    ap.add_argument("--input-root", required=True, help="Existing polluted full root")
    ap.add_argument(
        "--output-root",
        required=True,
        help="New candidate release root; never point this at input-root",
    )
    ap.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "configs" / "build.yaml"),
    )
    args = ap.parse_args()

    root = Path(args.input_root).expanduser().resolve()
    output = Path(args.output_root).expanduser().resolve()
    if output == root or root in output.parents:
        # A child candidate is safe; exact equality is not.
        if output == root:
            raise SystemExit("--output-root must not equal --input-root")

    final_out = output / "final"
    manifests_out = output / "manifests"
    reports_out = output / "reports"
    final_out.mkdir(parents=True, exist_ok=True)
    manifests_out.mkdir(parents=True, exist_ok=True)
    reports_out.mkdir(parents=True, exist_ok=True)

    cfg = load_config(args.config)
    provenance_path = root / "manifests" / "provenance.jsonl"
    provenance = list(iter_jsonl(provenance_path))
    by_id = {p["id"]: p for p in provenance}
    if len(by_id) != len(provenance):
        raise RuntimeError("Duplicate ids found in provenance.jsonl")

    decisions: dict[str, bool] = {}
    audit: list[dict] = []
    kept_provenance: list[dict] = []

    for p in provenance:
        decision = decide_provenance(p, cfg)
        decisions[p["id"]] = decision.keep
        audit.append(
            {
                "id": p["id"],
                "source_row_id": p.get("source_row_id"),
                "upstream_dataset": p.get("upstream_dataset"),
                "source_user_text": p.get("source_user_text"),
                "assistant_text": p.get("assistant_text"),
                "audio_wav": p.get("audio_wav"),
                "domain_policy": decision.policy,
                "domain_decision": "KEEP" if decision.keep else "DROP",
                "domain_reason": decision.reason,
            }
        )
        if decision.keep:
            q = dict(p)
            q["domain_status"] = decision.status
            q["domain_policy"] = decision.policy
            q["domain_reason"] = decision.reason
            kept_provenance.append(q)

    summary: dict[str, object] = {
        "input_root": str(root),
        "output_root": str(output),
        "policy": cfg["source"]["domain_filter"]["policy"],
    }

    for filename in ("all.jsonl", "train.jsonl", "valid.jsonl"):
        total = 0
        kept_rows: list[dict] = []
        for row in iter_jsonl(root / "final" / filename):
            total += 1
            sid = sid_from_final_row(row)
            if sid not in by_id:
                raise RuntimeError(f"No provenance for final row id={sid}")
            if decisions[sid]:
                kept_rows.append(row)
        write_jsonl(final_out / filename, kept_rows)
        summary[filename] = {
            "total": total,
            "kept": len(kept_rows),
            "dropped": total - len(kept_rows),
        }

    write_jsonl(manifests_out / "provenance.jsonl", kept_provenance)
    write_jsonl(manifests_out / "domain_audit_all.jsonl", audit)

    expected = {
        "all.jsonl": (38801, 6770, 32031),
        "train.jsonl": (38005, 6646, 31359),
        "valid.jsonl": (796, 124, 672),
    }
    for filename, (total, kept, dropped) in expected.items():
        got = summary[filename]
        triple = (got["total"], got["kept"], got["dropped"])
        if triple != (total, kept, dropped):
            raise RuntimeError(
                f"AUDITED_RELEASE_COUNT_MISMATCH {filename}: got={triple}, "
                f"expected={(total, kept, dropped)}"
            )

    if len(kept_provenance) != 6770:
        raise RuntimeError(
            f"Kept provenance mismatch: {len(kept_provenance)} != 6770"
        )

    source_snapshot = {}
    source_snapshot_path = root / "manifests" / "source_snapshot.json"
    if source_snapshot_path.exists():
        source_snapshot = json.loads(source_snapshot_path.read_text(encoding="utf-8"))

    build_summary = {
        "release_type": "finance_only_repair_without_tts_regeneration",
        "domain_policy": summary["policy"],
        "source_resolved_revision": source_snapshot.get("resolved_revision"),
        "source_raw_rows_seen": source_snapshot.get("raw_rows_seen"),
        "qa_rows_before_domain_filter": 38801,
        "domain_kept_rows": 6770,
        "domain_rejected_rows": 32031,
        "final_rows": 6770,
        "train_rows": 6646,
        "valid_rows": 124,
        "reuses_existing_audio_wav": True,
        "audio_root_remains": str((root / "audio_16k").resolve()),
    }
    write_json(manifests_out / "domain_repair_summary.json", summary)
    write_json(manifests_out / "build_summary.json", build_summary)

    report = f"""# FINAL BUILD REPORT — finance-only repaired release

- Release type: **finance-only repair; no TTS regeneration**
- Domain policy: `{summary['policy']}`
- Source resolved revision: `{source_snapshot.get('resolved_revision')}`
- QA before Domain Gate: **38,801**
- Domain KEEP: **6,770**
- Domain REJECT: **32,031**
- Final rows: **6,770**
- Train / Valid: **6,646 / 124**
- Audio WAV: **reused from existing `{(root / 'audio_16k').resolve()}`**

## Release contract

Only `final/train.jsonl` and `final/valid.jsonl` from this repaired release are training inputs.
The original polluted 38,801-row `final/` must not be used for training.
The existing WAV directory is intentionally reused; unreferenced WAV files do not enter training unless a JSONL record references them.
"""
    (reports_out / "FINAL_BUILD_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
