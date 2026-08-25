import json
from pathlib import Path

from fin_audio.source import prepare_source


def test_prepare_source_keeps_answer_exactly(tmp_path: Path):
    """验证 source 阶段不会 strip、重写或分类 answer。"""
    src = tmp_path / "source.jsonl"
    original_answer = "  Yes.\nLine two.  "
    row = {
        "task_type": "qa",
        "user_prompt": "What is equity?",
        "answer": original_answer,
        "dataset": "fixture",
    }
    src.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    cfg = {
        "source": {
            "hf_id": "sujet-ai/Sujet-Finance-Instruct-177k",
            "task_type": "qa",
            "question_field": "user_prompt",
            "answer_field": "answer",
            "provenance_field": "dataset",
        },
        "split": {"train": 0.98},
    }
    prepare_source(cfg, tmp_path / "out", source_jsonl=src)
    out_row = json.loads((tmp_path / "out/prepared/qa_source.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert out_row["assistant_text"] == original_answer
