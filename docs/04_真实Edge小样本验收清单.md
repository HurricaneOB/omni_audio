# 真实 Sujet + Edge-TTS 小样本验收清单

执行：

```bash
bash run_build.sh --mode live-smoke --output-root ./data_test/live --limit 5
```

确认：

- [ ] `source_snapshot.json` 显示 HF streaming；
- [ ] `edge_voice_snapshot.json` 中不是 mock voice；
- [ ] `tts_status.jsonl` 至少一条 success；
- [ ] WAV 可试听，内容是金融问题；
- [ ] `ffprobe` 为 16000 Hz、1 channel、pcm_s16le；
- [ ] `final/all.jsonl` user content 不含原问题文本；
- [ ] assistant 与 provenance 中 `assistant_text` 完全一致；
- [ ] `FINAL_BUILD_REPORT.md` 中 final validation error 为 0。

只有这份清单通过后再启动 full。
