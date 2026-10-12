#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from datetime import datetime

DROP_SOURCE_ROWS = {
    58075: "MBA/career advice",
    58598: "consumer-service dispute: dry cleaner",
    58631: "charity effectiveness/social-impact advice",
    58903: "computer repair/warranty dispute",
    58960: "career/employability advice",
    58977: "generic time-tracking software",
    59613: "student housing search/service recommendation",
    59777: "social-service referral",
}

EXPECTED_BEFORE = {"all": 6770, "train": 6646, "valid": 124, "provenance": 6770}
EXPECTED_AFTER  = {"all": 6762, "train": 6638, "valid": 124, "provenance": 6762}

def read_jsonl(path: Path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]

def write_jsonl_atomic(path: Path, rows):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(path)

def final_id(row: dict) -> str:
    audios = row["audios"]
    if not isinstance(audios, list) or len(audios) != 1:
        raise RuntimeError(f"bad audios field: {audios!r}")
    return Path(audios[0]).stem

def main():
    ap = argparse.ArgumentParser(
        description="Final strict semantic cleanup for the 6770-row finance-audio release."
    )
    ap.add_argument("--root", required=True, help="Current shared dataset root")
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Actually rewrite final/provenance and delete the 8 WAV files. "
             "Without --apply this is a read-only dry-run.",
    )
    args = ap.parse_args()

    root = Path(args.root).resolve()
    final_dir = root / "final"
    manifest_dir = root / "manifests"

    paths = {
        "all": final_dir / "all.jsonl",
        "train": final_dir / "train.jsonl",
        "valid": final_dir / "valid.jsonl",
        "provenance": manifest_dir / "provenance.jsonl",
    }
    for p in paths.values():
        if not p.exists():
            raise SystemExit(f"FAIL: missing {p}")

    rows = {k: read_jsonl(v) for k, v in paths.items()}
    before = {k: len(v) for k, v in rows.items()}
    print("before:", before)
    if before != EXPECTED_BEFORE:
        raise SystemExit(f"FAIL: unexpected pre-clean counts: {before}")

    drop_ids = {
        x["id"]
        for x in rows["provenance"]
        if int(x["source_row_id"]) in DROP_SOURCE_ROWS
    }
    if len(drop_ids) != 8:
        raise SystemExit(f"FAIL: expected 8 strict semantic drop IDs, got {len(drop_ids)}")

    valid_ids_before = {final_id(x) for x in rows["valid"]}
    if drop_ids & valid_ids_before:
        raise SystemExit("FAIL: a strict-drop sample appears in valid")

    # Check current WAV existence before any mutation.
    for row in rows["all"]:
        p = Path(row["audios"][0])
        if not p.exists():
            raise SystemExit(f"FAIL: missing current WAV: {p}")

    wavs_to_delete = [
        Path(row["audios"][0]).resolve()
        for row in rows["all"]
        if final_id(row) in drop_ids
    ]
    if len(wavs_to_delete) != 8:
        raise SystemExit(f"FAIL: expected 8 WAVs to delete, got {len(wavs_to_delete)}")

    new_all = [x for x in rows["all"] if final_id(x) not in drop_ids]
    new_train = [x for x in rows["train"] if final_id(x) not in drop_ids]
    new_valid = rows["valid"]
    new_prov = [x for x in rows["provenance"] if x["id"] not in drop_ids]

    after = {
        "all": len(new_all),
        "train": len(new_train),
        "valid": len(new_valid),
        "provenance": len(new_prov),
    }
    print("after:", after)
    if after != EXPECTED_AFTER:
        raise SystemExit(f"FAIL: unexpected post-clean counts: {after}")

    all_ids = {final_id(x) for x in new_all}
    train_ids = {final_id(x) for x in new_train}
    valid_ids = {final_id(x) for x in new_valid}
    prov_ids = {x["id"] for x in new_prov}

    if train_ids & valid_ids:
        raise SystemExit("FAIL: train/valid overlap")
    if train_ids | valid_ids != all_ids:
        raise SystemExit("FAIL: train ∪ valid != all")
    if all_ids != prov_ids:
        raise SystemExit("FAIL: final/provenance ID mismatch")

    print("\nStrict semantic DROP rows:")
    for x in rows["provenance"]:
        if x["id"] in drop_ids:
            print(
                f"- source_row_id={x['source_row_id']} "
                f"id={x['id']} "
                f"Q={x['source_user_text'].replace(chr(10), ' ')[:180]}"
            )

    if not args.apply:
        print("\nDRY-RUN PASS: nothing changed.")
        print("Re-run with --apply only after reviewing the 8 rows above.")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = root / f"_strict_semantic_cleanup_backup_{ts}"
    (backup / "final").mkdir(parents=True)
    (backup / "manifests").mkdir(parents=True)

    for key in ("all", "train", "valid"):
        shutil.copy2(paths[key], backup / "final" / paths[key].name)
    shutil.copy2(paths["provenance"], backup / "manifests" / "provenance.jsonl")
    print("backup:", backup)

    # All files are validated before mutation. Rewrite JSONs atomically.
    write_jsonl_atomic(paths["all"], new_all)
    write_jsonl_atomic(paths["train"], new_train)
    write_jsonl_atomic(paths["valid"], new_valid)
    write_jsonl_atomic(paths["provenance"], new_prov)

    # Delete only the exact 8 WAVs that were removed from final.
    audio_root = (root / "audio_16k").resolve()
    for p in wavs_to_delete:
        try:
            p.relative_to(audio_root)
        except ValueError:
            raise SystemExit(f"FAIL: WAV outside audio_16k: {p}")
        if not p.exists():
            raise SystemExit(f"FAIL: strict-drop WAV missing before delete: {p}")

    for p in wavs_to_delete:
        p.unlink()

    # Post-mutation verification.
    missing = []
    for row in new_all:
        p = Path(row["audios"][0])
        if not p.exists():
            missing.append(str(p))
    if missing:
        raise SystemExit(f"FAIL: {len(missing)} retained WAV files missing after cleanup")

    print("deleted strict semantic WAV:", len(wavs_to_delete))
    print("PASS: strict semantic cleanup complete")
    print("final all/train/valid/provenance = 6762 / 6638 / 124 / 6762")
    print("backup retained at:", backup)

if __name__ == "__main__":
    main()
