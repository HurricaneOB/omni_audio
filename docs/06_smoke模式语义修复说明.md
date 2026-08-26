# smoke 模式语义修复说明（v1.0.1）

旧版 `smoke` 的目的本应是验证少量数据全流程，但它使用 `mock` backend；当服务器没有 `espeak/espeak-ng` 时，代码自动用 FFmpeg 生成正弦波。正弦波能通过“非静音、格式合法”的 Audio QC，却没有任何金融问题语义。

v1.0.1 将运行模式重新定义为：

```text
offline-smoke = local fixture + test-tone        # 仅结构测试
smoke         = local fixture + Edge-TTS         # 可试听真实语音
live-smoke    = real Sujet streaming + Edge-TTS  # 真实数据小样本
full          = real Sujet + Edge-TTS             # 全量
```

生产和语义验收模式不再允许隐式测试音 fallback。


人类审计/追踪：
data_test/smoke_edge/manifests/provenance.jsonl

真正给 Qwen3-Omni 训练：
data_test/smoke_edge/final/all.jsonl

