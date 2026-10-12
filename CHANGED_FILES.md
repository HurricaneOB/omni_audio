# Minimal replacement manifest

Required production changes:

1. `configs/build.yaml` — pin audited Sujet revision and define finance Domain Gate.
2. `src/fin_audio/source.py` — insert Domain Gate after `task_type == qa` and before `qa_source.jsonl` / TTS.
3. `src/fin_audio/domain_gate.py` — new deterministic audited lineage policy.
4. `scripts/08_repair_polluted_full.py` — repair the already-generated polluted release without re-running 56h TTS.
5. `tests/test_domain_gate.py` — regression tests for keep/drop boundary and repair policy.
6. `docs/07_v1.2_金融域过滤最小修复说明.md` — engineering contract note.

Intentionally NOT changed:
- `planning.py`
- `generation.py`
- `qc.py`
- `dataset_builder.py`
- `schema.py`
- `reporting.py`
- audio format / voice / split logic

The uploaded source ZIP does not contain `run_build.sh` although its docs/tests reference it. This patch therefore does not overwrite the user's server runner. The filter lives inside `source.py`, so an existing runner that calls `scripts/01_prepare_source.py` before TTS automatically receives the fix.

The repair script also writes candidate `manifests/build_summary.json` and `reports/FINAL_BUILD_REPORT.md`, so the shared release metadata can be switched together with `final/` and `provenance.jsonl` without running TTS again.


## v1.2.1 最终发布门新增

- `scripts/09_release_gate.py`：只读发布前硬验收，不修改数据；强制检查 ms-swift schema、finance-domain provenance、6,770/6,646/124 计数、train/valid 无交叉、绝对 WAV 路径及正式服务器上的 WAV existence。
