from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import project_root_from_config
from .finance_pronunciation import load_exact_replacements, normalize_tts_text
from .io_utils import iter_jsonl, write_json, write_jsonl
from .paths import BuildPaths
from .voice_manager import assign_voice_and_rate, discover_english_voices


async def prepare_tts_plan(cfg: dict[str, Any], config_path: str | Path, output_root: str | Path, backend: str) -> dict[str, Any]:
    """生成确定性的 tts_text、voice、rate、目标音频路径计划。"""
    paths = BuildPaths.from_root(output_root)
    paths.ensure()

    pron_path = Path(cfg["tts_normalization"]["pronunciation_file"])
    if not pron_path.is_absolute():
        pron_path = project_root_from_config(config_path) / pron_path
    replacements = load_exact_replacements(pron_path)

    locales = list(cfg["edge_tts"]["locales"])
    voices = await discover_english_voices(locales, backend)
    rates = list(cfg["edge_tts"]["rates"])
    pitch = str(cfg["edge_tts"]["pitch"])

    voice_snapshot = {
        "backend": backend,
        "allowed_locales": locales,
        "voice_count": len(voices),
        "voices": voices,
    }
    write_json(paths.manifests / "edge_voice_snapshot.json", voice_snapshot)

    rows_out: list[dict[str, Any]] = []
    for row in iter_jsonl(paths.prepared / "qa_source.jsonl"):
        sid = row["id"]
        tts_text = normalize_tts_text(row["source_user_text"], replacements)
        voice, rate = assign_voice_and_rate(sid, voices, rates)
        shard = sid[:2]
        mp3 = paths.tmp_mp3 / shard / f"{sid}.mp3"
        wav = paths.audio_16k / shard / f"{sid}.wav"
        rows_out.append({
            **row,
            "tts_text": tts_text,
            "voice": voice["Name"],
            "voice_locale": voice.get("Locale"),
            "rate": rate,
            "pitch": pitch,
            "edge_mp3": str(mp3.resolve()),
            "audio_wav": str(wav.resolve()),
            "tts_backend": backend,
            "normalizer_version": cfg["tts_normalization"]["version"],
            "build_version": cfg["project"]["build_version"],
        })

    target = paths.prepared / "tts_plan.jsonl"
    write_jsonl(target, rows_out)
    return {"tts_planned_rows": len(rows_out), "tts_plan_path": str(target.resolve()), "voice_count": len(voices), "backend": backend}
