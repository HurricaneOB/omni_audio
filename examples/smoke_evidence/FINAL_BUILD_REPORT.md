# FINAL BUILD REPORT

- Output root: `/mnt/data/finance_audio_qwen3_omni_sujet_v1/data_test/mock`
- QA rows: **12**
- TTS success / failed: **12 / 0**
- Audio QC pass / fail / long: **12 / 0 / 0**
- Final rows: **12**
- Train / Valid: **11 / 1**
- Total audio hours: **0.0097**
- Duration p50 / p95 / max: **2.681s / 5.184s / 5.858s**
- Final static validation errors: **0**

## Voice distribution

```json
{
  "mock-en-AU-C": 4,
  "mock-en-GB-B": 5,
  "mock-en-US-A": 3
}
```

## Locale distribution

```json
{
  "en-AU": 4,
  "en-GB": 5,
  "en-US": 3
}
```

## Rate distribution

```json
{
  "+0%": 4,
  "+4%": 5,
  "-4%": 3
}
```

## 判定

- `final_validation_error_count == 0` 时，静态数据结构、音频技术格式和 answer 映射验收通过。
- 本报告不评价 Sujet 原始 answer 的语义正确性；这是本阶段明确不执行的任务。
