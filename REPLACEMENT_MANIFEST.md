# v1.0.1 smoke 修复替换清单

将本 ZIP 解压后，保持目录结构覆盖到原项目根目录。

## 核心代码

- `run_build.sh`
- `src/fin_audio/edge_client.py`
- `src/fin_audio/voice_manager.py`
- `src/fin_audio/env_check.py`
- `scripts/00_env_check.py`
- `scripts/02_prepare_tts_plan.py`
- `scripts/03_generate_audio.py`
- `scripts/07_verify_tts_backend.py`（新增）
- `tests/test_voice_plan.py`
- `tests/test_smoke_mode_contract.py`（新增）
- `pyproject.toml`
- `CHECKSUMS.sha256`

## 文档

- `README.md`
- `docs/00_环境配置_VSCode_SSH_uv_tmux.md`
- `docs/01_从0到全量_逐步执行手册.md`
- `docs/02_逐行代码拆解手册.md`
- `docs/03_音频QC与结果验收.md`
- `docs/04_真实Edge小样本验收清单.md`
- `docs/05_工程可靠性复核与外部接口依据.md`
- `docs/06_smoke模式语义修复说明.md`
- 对应历史/别名文档已加入 v1.0.1 修订提示。

## 建议删除的旧结果/旧证据

覆盖代码后执行：

```bash
rm -rf ./data_test/mock
rm -rf ./examples/smoke_evidence
```

旧 `data_test/mock` 可能是无语义 test tone；旧 `examples/smoke_evidence` 属于 v1.0.0 mock 历史证据，不应继续作为当前真实 TTS 验收依据。
