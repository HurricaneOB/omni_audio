#!/usr/bin/env bash
set -Eeuo pipefail

# 第一阶段统一入口：
#   offline-smoke = 离线“结构链路”测试（明确使用 test-tone，不用于试听判断语义）
#   smoke         = 本地 fixture + 真实 Edge-TTS，可直接试听金融问题
#   live-smoke    = 真实 Sujet streaming + 真实 Edge-TTS 少量样本
#   full          = 真实 Sujet + 真实 Edge-TTS 全量构建
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$ROOT/configs/build.yaml"
MODE=""
OUTPUT_ROOT=""
LIMIT=""
HF_CACHE_DIR=""

usage() {
  cat <<'USAGE'
用法：
  # 纯离线结构测试：生成测试音，不代表真实语音内容
  bash run_build.sh --mode offline-smoke [--output-root ./data_test/offline_structure]

  # 推荐的第一层真实语音测试：本地 12 条 fixture + 真实 Edge-TTS
  bash run_build.sh --mode smoke [--output-root ./data_test/smoke_edge]

  # 第二层真实测试：真实 Hugging Face Sujet + 真实 Edge-TTS，仅处理前 N 条 QA
  bash run_build.sh --mode live-smoke [--output-root ./data_test/live] [--limit 5] [--hf-cache-dir ...]

  # 全量：必须显式指定 NAS 输出目录
  bash run_build.sh --mode full --output-root /ky200t/datasets/$USER/finance_audio_qwen3_omni_sujet_v1 [--hf-cache-dir ...]
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="$2"; shift 2 ;;
    --output-root) OUTPUT_ROOT="$2"; shift 2 ;;
    --limit) LIMIT="$2"; shift 2 ;;
    --hf-cache-dir) HF_CACHE_DIR="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知参数: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$MODE" ]]; then
  echo "必须指定 --mode offline-smoke|smoke|live-smoke|full" >&2
  usage
  exit 2
fi

SOURCE_MODE="hf"
TTS_BACKEND="edge"
SOURCE_ARGS=()

case "$MODE" in
  offline-smoke)
    OUTPUT_ROOT="${OUTPUT_ROOT:-$ROOT/data_test/offline_structure}"
    SOURCE_MODE="local"
    TTS_BACKEND="test-tone"
    SOURCE_ARGS+=(--source-jsonl "$ROOT/tests/fixtures/sujet_mini.jsonl")
    ;;
  smoke)
    # 关键修复：smoke 必须使用真实 Edge-TTS。
    # 这样 smoke WAV 中真正包含 fixture 的金融问题，而不是 mock/test tone。
    OUTPUT_ROOT="${OUTPUT_ROOT:-$ROOT/data_test/smoke_edge}"
    SOURCE_MODE="local"
    TTS_BACKEND="edge"
    SOURCE_ARGS+=(--source-jsonl "$ROOT/tests/fixtures/sujet_mini.jsonl")
    ;;
  live-smoke)
    OUTPUT_ROOT="${OUTPUT_ROOT:-$ROOT/data_test/live}"
    TTS_BACKEND="edge"
    LIMIT="${LIMIT:-5}"
    SOURCE_ARGS+=(--limit "$LIMIT" --streaming-source)
    ;;
  full)
    if [[ -z "$OUTPUT_ROOT" ]]; then
      echo "full 模式必须显式指定 --output-root，避免把数万条音频误写到家目录。" >&2
      exit 2
    fi
    TTS_BACKEND="edge"
    ;;
  *) echo "非法 mode: $MODE" >&2; exit 2 ;;
esac

if [[ -n "$HF_CACHE_DIR" ]]; then
  SOURCE_ARGS+=(--hf-cache-dir "$HF_CACHE_DIR")
fi

mkdir -p "$OUTPUT_ROOT" "$ROOT/logs"
LOG="$ROOT/logs/${MODE}_$(date +%Y%m%d_%H%M%S).log"

# tee 同时把日志显示在终端并保存，便于 tmux 断线后追踪。
exec > >(tee -a "$LOG") 2>&1

echo "============================================================"
echo "Finance Audio Dataset Build"
echo "mode        : $MODE"
echo "output_root : $OUTPUT_ROOT"
echo "tts_backend : $TTS_BACKEND"
echo "log         : $LOG"
echo "============================================================"

if [[ "$TTS_BACKEND" == "test-tone" ]]; then
  echo "[WARNING] 当前是 offline-smoke/test-tone：只用于结构链路测试。"
  echo "[WARNING] 该模式的 WAV 不包含可理解金融问题，不能用于试听验收或训练。"
fi

python "$ROOT/scripts/00_env_check.py" --config "$CONFIG" --output-root "$OUTPUT_ROOT" --tts-backend "$TTS_BACKEND" --source-mode "$SOURCE_MODE"
python "$ROOT/scripts/01_prepare_source.py" --config "$CONFIG" --output-root "$OUTPUT_ROOT" "${SOURCE_ARGS[@]}"
python "$ROOT/scripts/02_prepare_tts_plan.py" --config "$CONFIG" --output-root "$OUTPUT_ROOT" --tts-backend "$TTS_BACKEND"
python "$ROOT/scripts/03_generate_audio.py" --config "$CONFIG" --output-root "$OUTPUT_ROOT" --tts-backend "$TTS_BACKEND"
python "$ROOT/scripts/04_audio_qc.py" --config "$CONFIG" --output-root "$OUTPUT_ROOT"
python "$ROOT/scripts/05_build_dataset.py" --config "$CONFIG" --output-root "$OUTPUT_ROOT"
python "$ROOT/scripts/06_validate_and_report.py" --config "$CONFIG" --output-root "$OUTPUT_ROOT"

# 对真实语音模式做 provenance gate：禁止误把 test-tone/mock 结果当成 Edge 结果。
if [[ "$TTS_BACKEND" == "edge" ]]; then
  python "$ROOT/scripts/07_verify_tts_backend.py" --output-root "$OUTPUT_ROOT" --expected-backend edge
fi

echo "[DONE] 第一阶段数据集构建完成。"
echo "Final JSONL: $OUTPUT_ROOT/final"
echo "Report     : $OUTPUT_ROOT/reports/FINAL_BUILD_REPORT.md"
