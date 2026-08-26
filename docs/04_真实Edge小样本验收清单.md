# 真实 Edge-TTS 小样本验收清单（v1.0.1）

## A. 本地 fixture + 真实 Edge-TTS smoke

执行：

```bash
bash run_build.sh --mode smoke
```

默认输出：

```text
./data_test/smoke_edge
```

确认：

- [ ] `edge_voice_snapshot.json` 中 `backend == "edge"`；
- [ ] voice 名称不是 `test-tone-*`；
- [ ] `tts_plan.jsonl` 每条 `tts_backend == "edge"`；
- [ ] `tts_status.jsonl` 至少一条 success；
- [ ] WAV 可试听，内容确实是 fixture 中的金融问题；
- [ ] WAV 为 16000 Hz、1 channel、PCM16；
- [ ] `final/all.jsonl` user content 不含原问题文本；
- [ ] assistant 与 provenance 中 `assistant_text` 完全一致；
- [ ] `FINAL_BUILD_REPORT.md` 中 final validation error 为 0；
- [ ] 终端出现 `[BACKEND-GUARD][PASS] backend=edge`。

## B. 真实 Sujet + Edge-TTS live-smoke

执行：

```bash
bash run_build.sh \
  --mode live-smoke \
  --output-root ./data_test/live \
  --limit 5 \
  --hf-cache-dir /ky200t/datasets/$USER/.cache/huggingface
```

除 A 的验收项外，还确认：

- [ ] `source_snapshot.json` 显示 HF streaming；
- [ ] 样本来自真实 Sujet `task_type == qa`；
- [ ] 随机试听 2～3 条真实 Sujet 问题。

只有 A+B 都通过后再启动 full。

> `offline-smoke` 只生成 `test-tone`，不能代替 A 或 B。
