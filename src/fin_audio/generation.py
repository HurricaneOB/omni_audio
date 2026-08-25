from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from .audio_utils import ffmpeg_to_pcm16_wav
from .edge_client import synthesize_mp3
from .io_utils import iter_jsonl
from .manifest import JsonlKeyedStore
from .paths import BuildPaths


async def _process_one(row: dict[str, Any], cfg: dict[str, Any], backend: str, sem: asyncio.Semaphore) -> dict[str, Any]:
    """合成单条 MP3 并标准化为 WAV；失败时返回结构化错误，不抛出到全局。"""
    sid = row["id"]
    mp3 = Path(row["edge_mp3"])
    wav = Path(row["audio_wav"])
    max_retries = int(cfg["edge_tts"]["max_retries"])
    base_wait = float(cfg["edge_tts"].get("base_retry_seconds", 2))

    # 如果上次已经生成 WAV，本阶段直接复用，真正的技术合法性由后续 Audio QC 再判断。
    if wav.exists() and wav.stat().st_size > 0:
        return {"id": sid, "tts_status": "success", "audio_wav": str(wav.resolve()), "edge_mp3": str(mp3.resolve()), "attempts": 0, "resume_hit": True}

    last_error: str | None = None
    async with sem:
        for attempt in range(1, max_retries + 1):
            try:
                mp3.parent.mkdir(parents=True, exist_ok=True)
                wav.parent.mkdir(parents=True, exist_ok=True)
                await synthesize_mp3(row["tts_text"], row["voice"], row["rate"], row["pitch"], mp3, backend=backend)
                await asyncio.to_thread(ffmpeg_to_pcm16_wav, mp3, wav, int(cfg["audio"]["sample_rate"]))
                return {"id": sid, "tts_status": "success", "audio_wav": str(wav.resolve()), "edge_mp3": str(mp3.resolve()), "attempts": attempt, "resume_hit": False}
            except Exception as exc:
                last_error = repr(exc)
                if attempt < max_retries:
                    await asyncio.sleep(min(30.0, base_wait * (2 ** (attempt - 1))))

    return {"id": sid, "tts_status": "failed", "failure_reason": "TTS_FAILED", "error": last_error, "audio_wav": str(wav.resolve()), "edge_mp3": str(mp3.resolve()), "attempts": max_retries}


async def generate_audio(cfg: dict[str, Any], output_root: str | Path, backend: str) -> dict[str, Any]:
    """使用 bounded worker queue 全量生成音频，并持续刷新唯一键 manifest。"""
    paths = BuildPaths.from_root(output_root)
    paths.ensure()
    rows = list(iter_jsonl(paths.prepared / "tts_plan.jsonl"))
    store = JsonlKeyedStore(paths.manifests / "tts_status.jsonl")
    concurrency = int(cfg["edge_tts"]["concurrency"])
    sem = asyncio.Semaphore(concurrency)
    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue(maxsize=max(8, concurrency * 4))
    completed = 0
    success_count = 0
    fail_count = 0
    store_lock = asyncio.Lock()

    async def worker() -> None:
        nonlocal completed, success_count, fail_count
        while True:
            row = await queue.get()
            if row is None:
                queue.task_done()
                return
            try:
                old = store.get(row["id"])
                if old and old.get("tts_status") == "success" and Path(old.get("audio_wav", "")).exists():
                    result = old
                else:
                    result = await _process_one(row, cfg, backend, sem)
                async with store_lock:
                    store.upsert(result)
                    completed += 1
                    if result.get("tts_status") == "success":
                        success_count += 1
                    else:
                        fail_count += 1
                    # 每 100 条做一次 checkpoint 并打印进度，便于 tmux/log 观察长任务。
                    if completed % 100 == 0:
                        store.flush()
                        print(f"[TTS] {completed}/{len(rows)} | success={success_count} failed={fail_count}", flush=True)
            finally:
                queue.task_done()

    workers = [asyncio.create_task(worker()) for _ in range(concurrency)]
    for row in rows:
        await queue.put(row)
    for _ in workers:
        await queue.put(None)
    await queue.join()
    await asyncio.gather(*workers)
    store.flush()

    active_ids = {x["id"] for x in rows}
    successes = sum(1 for r in store.rows.values() if r.get("tts_status") == "success" and r.get("id") in active_ids)
    failures = len(rows) - successes
    return {"tts_planned_rows": len(rows), "tts_success_rows": successes, "tts_failed_rows": failures, "backend": backend}
