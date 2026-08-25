#!/usr/bin/env bash
set -Eeuo pipefail

# 第一阶段统一入口：smoke=离线全链路，live-smoke=真实 HF+Edge 少量，full=真实全量。
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$ROOT/configs/build.yaml"
MODE=""
OUTPUT_ROOT=""
LIMIT=""
HF_CACHE_DIR=""

usage() {
  cat <<'EOF'
用法：
  bash run_build.sh --mode smoke [--output-root ./data_test/mock]
  bash run_build.sh --mode live-smoke [--output-root ./data_test/live] [--limit 5]
  bash run_build.sh --mode full --output-root /ky200t/datasets/$USER/finance_audio_qwen3_omni_sujet_v1 [--hf-cache-dir ...]
EOF
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
  echo "必须指定 --mode smoke|live-smoke|full" >&2
  usage
  exit 2
fi

SOURCE_MODE="hf"
TTS_BACKEND="edge"
SOURCE_ARGS=()

case "$MODE" in
  smoke)
    OUTPUT_ROOT="${OUTPUT_ROOT:-$ROOT/data_test/mock}"
    SOURCE_MODE="local"
    TTS_BACKEND="mock"
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

python "$ROOT/scripts/00_env_check.py" --config "$CONFIG" --output-root "$OUTPUT_ROOT" --tts-backend "$TTS_BACKEND" --source-mode "$SOURCE_MODE"
python "$ROOT/scripts/01_prepare_source.py" --config "$CONFIG" --output-root "$OUTPUT_ROOT" "${SOURCE_ARGS[@]}"
python "$ROOT/scripts/02_prepare_tts_plan.py" --config "$CONFIG" --output-root "$OUTPUT_ROOT" --tts-backend "$TTS_BACKEND"
python "$ROOT/scripts/03_generate_audio.py" --config "$CONFIG" --output-root "$OUTPUT_ROOT" --tts-backend "$TTS_BACKEND"
python "$ROOT/scripts/04_audio_qc.py" --config "$CONFIG" --output-root "$OUTPUT_ROOT"
python "$ROOT/scripts/05_build_dataset.py" --config "$CONFIG" --output-root "$OUTPUT_ROOT"
python "$ROOT/scripts/06_validate_and_report.py" --config "$CONFIG" --output-root "$OUTPUT_ROOT"

echo "[DONE] 第一阶段数据集构建完成。"
echo "Final JSONL: $OUTPUT_ROOT/final"
echo "Report     : $OUTPUT_ROOT/reports/FINAL_BUILD_REPORT.md"
