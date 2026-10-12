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
from fin_audio.io_utils import iter_jsonl


EXPECTED_SYSTEM = "You are a professional, accurate, and careful financial assistant."
EXPECTED_USER = "<audio>Please answer the financial question in the audio."


def _sid_from_audio(row: dict) -> str:
    audios = row.get("audios")
    if not isinstance(audios, list) or len(audios) != 1:
        raise RuntimeError(f"MS_SWIFT_SCHEMA_FAIL: audios must contain exactly one item: {audios!r}")
    audio = audios[0]
    if not isinstance(audio, str):
        raise RuntimeError("MS_SWIFT_SCHEMA_FAIL: audio path must be a string")
    return Path(audio).stem


def _validate_record(row: dict, prov: dict, check_audio_exists: bool) -> list[str]:
    errors: list[str] = []

    if set(row.keys()) != {"messages", "audios"}:
        errors.append(f"top_level_keys={sorted(row.keys())}")

    messages = row.get("messages")
    audios = row.get("audios")

    if not isinstance(messages, list) or len(messages) != 3:
        errors.append("messages_must_have_exactly_3_items")
    else:
        expected_roles = ["system", "user", "assistant"]
        roles = [m.get("role") if isinstance(m, dict) else None for m in messages]
        if roles != expected_roles:
            errors.append(f"roles={roles!r}")

        if isinstance(messages[0], dict) and messages[0].get("content") != EXPECTED_SYSTEM:
            errors.append("system_prompt_changed")
        if isinstance(messages[1], dict):
            user_text = messages[1].get("content")
            if user_text != EXPECTED_USER:
                errors.append("user_prompt_changed")
            if not isinstance(user_text, str) or user_text.count("<audio>") != 1:
                errors.append("audio_token_count_must_equal_1")
            source_question = str(prov.get("source_user_text") or "").strip()
            if source_question and isinstance(user_text, str) and source_question in user_text:
                errors.append("question_transcript_leakage")
        if isinstance(messages[2], dict) and messages[2].get("content") != prov.get("assistant_text"):
            errors.append("assistant_text_not_original_passthrough")

    if not isinstance(audios, list) or len(audios) != 1 or not isinstance(audios[0], str):
        errors.append("audios_must_have_one_string_path")
    else:
        p = Path(audios[0])
        if not p.is_absolute():
            errors.append("audio_path_not_absolute")
        if check_audio_exists and not p.exists():
            errors.append(f"audio_path_missing:{p}")

    decision = decide_provenance(prov, CFG)
    if not decision.keep:
        errors.append(f"finance_domain_reject:{decision.reason}")

    return errors


def _load_rows(path: Path) -> list[dict]:
    if not path.exists():
        raise RuntimeError(f"RELEASE_FILE_MISSING: {path}")
    return list(iter_jsonl(path))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only final release gate: ms-swift schema + audited finance-domain purity."
    )
    parser.add_argument("--release-root", required=True)
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "configs" / "build.yaml"),
    )
    parser.add_argument(
        "--skip-audio-exists",
        action="store_true",
        help="Only for off-server inspection. Formal server release must NOT use this flag.",
    )
    args = parser.parse_args()

    global CFG
    CFG = load_config(args.config)

    root = Path(args.release_root).expanduser().resolve()
    all_rows = _load_rows(root / "final" / "all.jsonl")
    train_rows = _load_rows(root / "final" / "train.jsonl")
    valid_rows = _load_rows(root / "final" / "valid.jsonl")
    prov_rows = _load_rows(root / "manifests" / "provenance.jsonl")

    expected = {"all": 6770, "train": 6646, "valid": 124, "provenance": 6770}
    got = {
        "all": len(all_rows),
        "train": len(train_rows),
        "valid": len(valid_rows),
        "provenance": len(prov_rows),
    }
    if got != expected:
        raise RuntimeError(f"RELEASE_COUNT_FAIL: got={got}, expected={expected}")

    by_id = {str(p["id"]): p for p in prov_rows}
    if len(by_id) != len(prov_rows):
        raise RuntimeError("PROVENANCE_DUPLICATE_ID_FAIL")

    all_ids: list[str] = []
    failures: list[dict] = []

    for i, row in enumerate(all_rows):
        try:
            sid = _sid_from_audio(row)
        except Exception as exc:
            failures.append({"row": i, "id": None, "errors": [str(exc)]})
            continue

        all_ids.append(sid)
        prov = by_id.get(sid)
        if prov is None:
            failures.append({"row": i, "id": sid, "errors": ["missing_provenance"]})
            continue

        errors = _validate_record(
            row, prov, check_audio_exists=not args.skip_audio_exists
        )
        if errors:
            failures.append({"row": i, "id": sid, "errors": errors})

    if len(set(all_ids)) != len(all_ids):
        failures.append({"row": None, "id": None, "errors": ["duplicate_final_ids"]})

    train_ids = {_sid_from_audio(r) for r in train_rows}
    valid_ids = {_sid_from_audio(r) for r in valid_rows}
    if train_ids & valid_ids:
        failures.append(
            {"row": None, "id": None, "errors": [f"train_valid_overlap:{len(train_ids & valid_ids)}"]}
        )
    if train_ids | valid_ids != set(all_ids):
        failures.append(
            {"row": None, "id": None, "errors": ["train_valid_union_not_equal_all"]}
        )

    # Provenance must itself be 100% accepted by the finance-domain policy.
    provenance_rejects = []
    for p in prov_rows:
        d = decide_provenance(p, CFG)
        if not d.keep:
            provenance_rejects.append(
                {"id": p.get("id"), "source_row_id": p.get("source_row_id"),
                 "upstream_dataset": p.get("upstream_dataset"), "reason": d.reason}
            )
    if provenance_rejects:
        failures.append(
            {"row": None, "id": None, "errors": [f"non_finance_provenance:{len(provenance_rejects)}"]}
        )

    print(json.dumps({
        "release_root": str(root),
        "counts": got,
        "schema_checked": len(all_rows),
        "finance_provenance_checked": len(prov_rows),
        "audio_exists_checked": not args.skip_audio_exists,
        "failures": len(failures),
    }, ensure_ascii=False, indent=2))

    if failures:
        print(json.dumps(failures[:30], ensure_ascii=False, indent=2))
        raise SystemExit(1)

    print("PASS: ms-swift schema + audited finance-domain release contract.")


if __name__ == "__main__":
    CFG = {}
    main()
