# Finance Audio Qwen3-Omni Sujet v1.0.1

本工程把 `sujet-ai/Sujet-Finance-Instruct-177k` 中 `task_type == "qa"` 的 `user_prompt` 转为英文金融问题音频，原始 `answer` 原样作为文本监督，最终生成适配 Qwen3-Omni / ms-swift 的 `messages + audios` JSONL。

## 重要：四种运行模式

```bash
# 0. 可选：纯离线结构测试。
# 会明确生成 test-tone，只验证 MP3→WAV→QC→JSONL 链路；不能试听判断语义，也不能用于训练。
bash run_build.sh --mode offline-smoke

# 1. 推荐第一层测试：本地 12 条 fixture + 真实 Edge-TTS。
# 生成的 WAV 必须能听到真实金融问题；默认写 ./data_test/smoke_edge
bash run_build.sh --mode smoke

# 2. 第二层测试：真实 Hugging Face Sujet + 真实 Edge-TTS，仅处理前 5 条 QA。
bash run_build.sh --mode live-smoke \
  --output-root ./data_test/live \
  --limit 5 \
  --hf-cache-dir /ky200t/datasets/$USER/.cache/huggingface

# 3. 全量：必须显式指定 NAS 输出目录。
bash run_build.sh --mode full \
  --output-root /ky200t/datasets/$USER/finance_audio_qwen3_omni_sujet_v1 \
  --hf-cache-dir /ky200t/datasets/$USER/.cache/huggingface
```

## v1.0.1 smoke 语义修复

旧版 `smoke` 使用 mock backend；服务器没有 `espeak` 时会隐式退化成正弦测试音。该测试音可以通过技术 Audio QC，但不包含问题语义。

v1.0.1 已修复：

- `smoke` 固定使用真实 `Edge-TTS`；
- 新增 `offline-smoke`，仅用于纯离线结构测试；
- 离线测试 backend 明确命名为 `test-tone`；
- 删除“没有 espeak 就静默回退成正弦波”的隐式逻辑；
- 增加 `scripts/07_verify_tts_backend.py`，真实语音模式结束后强制确认 provenance 中 backend 为 `edge`；
- 文档明确：技术 QC 不能代替语义试听验收。

详细执行见 `docs/01_从0到全量_逐步执行手册.md`。
