from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .audio_utils import inspect_wav
from .io_utils import iter_jsonl
from .manifest import JsonlKeyedStore
from .paths import BuildPaths


def run_audio_qc(cfg: dict[str, Any], output_root: str | Path) -> dict[str, Any]:
    """对成功生成的 WAV 做逐文件技术 QC，并清理已通过样本的临时 MP3。"""
    paths = BuildPaths.from_root(output_root)
    paths.ensure()
    status_store = JsonlKeyedStore(paths.manifests / "tts_status.jsonl")
    status = status_store.rows
    plan = {r["id"]: r for r in iter_jsonl(paths.prepared / "tts_plan.jsonl")}
    qc_store = JsonlKeyedStore(paths.manifests / "audio_qc.jsonl")

    min_duration = float(cfg["audio"]["min_duration_sec"])
    max_duration = float(cfg["audio"]["max_duration_sec"])
    target_sr = int(cfg["audio"]["sample_rate"])
    target_channels = int(cfg["audio"]["channels"])
    silence_threshold = float(cfg["audio"]["silence_rms_threshold"])
    keep_mp3 = bool(cfg["edge_tts"]["keep_raw_mp3"])

    pass_count = fail_count = long_count = 0
    for index, (sid, row) in enumerate(plan.items(), start=1):
        tts = status.get(sid)
        if not tts or tts.get("tts_status") != "success":
            qc_store.upsert({"id": sid, "audio_qc": "fail", "failure_reason": "TTS_FAILED"})
            fail_count += 1
            continue

        info = inspect_wav(tts["audio_wav"], silence_threshold)
        reason = None
        qc_state = "pass"
        if not info.get("ok"):
            reason = info.get("failure_reason") or "AUDIO_DECODE_FAILED"
        elif info["sample_rate"] != target_sr:
            reason = "WRONG_SAMPLE_RATE"
        elif info["channels"] != target_channels:
            reason = "WRONG_CHANNELS"
        elif info["subtype"] != "PCM_16":
            reason = "WRONG_CODEC"
        elif info["is_silent"]:
            reason = "AUDIO_SILENT"
        elif info["duration_sec"] < min_duration:
            reason = "AUDIO_TOO_SHORT"
        elif info["duration_sec"] > max_duration:
            reason = "AUDIO_TOO_LONG"
            qc_state = "long"

        if reason and qc_state != "long":
            qc_state = "fail"

        # 超长音频真正移动到 long_audio；同步更新 tts_status，保证重跑时不会重复生成。
        if qc_state == "long":
            src_wav = Path(tts["audio_wav"])
            if paths.long_audio not in src_wav.parents:
                dst_wav = paths.long_audio / sid[:2] / src_wav.name
                dst_wav.parent.mkdir(parents=True, exist_ok=True)
                os.replace(src_wav, dst_wav)
                tts["audio_wav"] = str(dst_wav.resolve())
                status_store.upsert(tts)
                info["audio_wav"] = str(dst_wav.resolve())

        record = {"id": sid, "audio_qc": qc_state, "failure_reason": reason, **info}
        qc_store.upsert(record)

        if qc_state == "pass":
            pass_count += 1
            if not keep_mp3:
                Path(tts.get("edge_mp3", "")).unlink(missing_ok=True)
        elif qc_state == "long":
            long_count += 1
            if not keep_mp3:
                Path(tts.get("edge_mp3", "")).unlink(missing_ok=True)
        else:
            fail_count += 1

        if index % 1000 == 0:
            print(f"[Audio QC] {index}/{len(plan)} | pass={pass_count} fail={fail_count} long={long_count}", flush=True)

    qc_store.flush()
    status_store.flush()
    return {"audio_qc_pass_rows": pass_count, "audio_qc_failed_rows": fail_count, "long_audio_rows": long_count}
