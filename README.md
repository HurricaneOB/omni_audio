# Finance Audio Qwen3-Omni Sujet v1

本工程把 `sujet-ai/Sujet-Finance-Instruct-177k` 中 `task_type == "qa"` 的 `user_prompt` 转为英文金融问题音频，原始 `answer` 原样作为文本监督，最终生成适配 Qwen3-Omni / ms-swift 的 `messages + audios` JSONL。

## 三种运行模式

```bash
# 1. 离线工程全链路测试：不联网，不调用真实 Edge；默认写当前项目 ./data_test/mock
bash run_build.sh --mode smoke

# 2. 真实少量测试：真实 Hugging Face + Edge-TTS，仅处理前 5 条 QA
bash run_build.sh --mode live-smoke --output-root ./data_test/live --limit 5

# 3. 全量：必须显式指定 NAS 输出目录
bash run_build.sh --mode full \
  --output-root /ky200t/datasets/$USER/finance_audio_qwen3_omni_sujet_v1 \
  --hf-cache-dir /ky200t/datasets/$USER/.cache/huggingface
```

详细步骤见 `docs/01_从0到全量_逐步执行手册.md`。

## 交付内已完成的实际测试

- `python -m compileall`：通过；
- `pytest`：10 passed；
- `bash run_build.sh --mode smoke`：12/12 音频 QC 通过，11 train + 1 valid，final schema error = 0；
- 二次 smoke 重跑：WAV 与 final JSONL SHA256 一致（idempotency PASS）；
- 自定义 `--output-root`：通过；
- full 未指定 output root：程序主动拒绝启动。

详见 `reports/本地全流程Smoke测试与工程审计报告.md`。
