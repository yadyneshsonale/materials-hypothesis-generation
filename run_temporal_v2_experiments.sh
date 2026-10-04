#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPERIMENT="$ROOT/experiments/high_temperature_hea_qwen35b"
RUN_ROOT="$EXPERIMENT/temporal_v2"
LOG_DIR="$RUN_ROOT/logs"
STATUS="$RUN_ROOT/status.json"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python
fi

LLAMA_SERVER="${LLAMA_SERVER:-/home/t-ydsonale/.copilot/session-state/ddc46855-f88c-4679-a06a-5714ced0b156/files/llama.cpp/build-cu12/bin/llama-server}"
MODEL_PATH="${MODEL_PATH:-/home/t-ydsonale/.copilot/session-state/ddc46855-f88c-4679-a06a-5714ced0b156/files/models/Qwen3.5-35B-A3B-Q4_K_M.gguf}"
SERVER_URL="${OPENAI_BASE_URL:-http://127.0.0.1:8000/v1}"
HEALTH_URL="${SERVER_URL%/v1}/health"
SERVER_PID=""
STARTED_SERVER=0

mkdir -p "$LOG_DIR" "$RUN_ROOT/checkpoints/v2" "$RUN_ROOT/materials_evidence_v2" \
  "$RUN_ROOT/benchmark_cases" "$RUN_ROOT/experiment_runs" "$RUN_ROOT/results"

write_status() {
  local state="$1"
  local stage="$2"
  local message="$3"
  "$PYTHON" - "$STATUS" "$state" "$stage" "$message" <<'PY'
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
payload = {
    "state": sys.argv[2],
    "stage": sys.argv[3],
    "message": sys.argv[4],
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "pid": os.getppid(),
}
temporary = path.with_suffix(".json.tmp")
temporary.write_text(json.dumps(payload, indent=2) + "\n")
temporary.replace(path)
PY
}

cleanup() {
  local exit_code=$?
  if [[ "$STARTED_SERVER" -eq 1 && -n "$SERVER_PID" ]]; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  if [[ "$exit_code" -ne 0 ]]; then
    write_status "failed" "${CURRENT_STAGE:-unknown}" "Pipeline failed with exit code $exit_code"
  fi
  exit "$exit_code"
}
trap cleanup EXIT

run_stage() {
  CURRENT_STAGE="$1"
  shift
  write_status "running" "$CURRENT_STAGE" "Stage started"
  echo "[$(date -Is)] START $CURRENT_STAGE" | tee -a "$LOG_DIR/pipeline.log"
  "$@" 2>&1 | tee -a "$LOG_DIR/$CURRENT_STAGE.log"
  echo "[$(date -Is)] DONE $CURRENT_STAGE" | tee -a "$LOG_DIR/pipeline.log"
}

cd "$ROOT"
write_status "starting" "server" "Preparing local Qwen inference server"

if ! curl --fail --silent "$HEALTH_URL" >/dev/null 2>&1; then
  if [[ ! -x "$LLAMA_SERVER" ]]; then
    echo "llama-server not executable: $LLAMA_SERVER" >&2
    exit 1
  fi
  if [[ ! -f "$MODEL_PATH" ]]; then
    echo "model not found: $MODEL_PATH" >&2
    exit 1
  fi
  CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0,1,2,3}" \
    "$LLAMA_SERVER" \
    --model "$MODEL_PATH" \
    --host 127.0.0.1 \
    --port 8000 \
    --ctx-size 131072 \
    --parallel 4 \
    --n-gpu-layers 99 \
    --split-mode layer \
    --tensor-split 1,1,1,1 \
    --flash-attn off \
    --jinja \
    --metrics \
    >"$LOG_DIR/llama-server.log" 2>&1 &
  SERVER_PID=$!
  STARTED_SERVER=1
  echo "$SERVER_PID" >"$RUN_ROOT/llama-server.pid"
  for _ in $(seq 1 180); do
    if curl --fail --silent "$HEALTH_URL" >/dev/null 2>&1; then
      break
    fi
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
      echo "llama-server exited during startup" >&2
      tail -n 80 "$LOG_DIR/llama-server.log" >&2
      exit 1
    fi
    sleep 2
  done
fi
curl --fail --silent "$HEALTH_URL" | tee "$RUN_ROOT/server-health.json"

export MATHG_PROVIDER=openai
export OPENAI_BASE_URL="$SERVER_URL"
export OPENAI_API_KEY=local
export OPENAI_MODEL=Qwen3.5-35B-A3B-Q4_K_M.gguf
export OPENAI_CHAT_TEMPLATE_KWARGS='{"enable_thinking":false}'
export MATHG_CONTEXT_WINDOW=32768
export MATHG_REQUEST_TIMEOUT=300

run_stage temporal_metadata \
  "$PYTHON" temporal_metadata.py \
  --manifest "$EXPERIMENT/data/corpus/manifest.json" \
  --papers-dir "$EXPERIMENT/outputs/papers" \
  --output "$RUN_ROOT/temporal_metadata.json"

run_stage question_triage \
  "$PYTHON" temporal_hypothesis_benchmark.py triage-questions \
  --papers-dir "$EXPERIMENT/outputs/papers" \
  --metadata "$RUN_ROOT/temporal_metadata.json" \
  --output "$RUN_ROOT/question_triage.json"

run_stage v2_extraction \
  "$PYTHON" materials_extract_v2.py \
  --input-dir "$EXPERIMENT/data/corpus/text" \
  --out-dir "$RUN_ROOT/materials_evidence_v2" \
  --checkpoint-dir "$RUN_ROOT/checkpoints/v2" \
  --workers 4 --resume

run_stage v2_evaluation \
  "$PYTHON" evaluate_hypothesis_evidence_v2.py \
  --evidence-dir "$RUN_ROOT/materials_evidence_v2" \
  --source-dir "$EXPERIMENT/data/corpus/text" \
  --output "$RUN_ROOT/results/v2_evidence_evaluation.json"

run_stage benchmark_cases \
  "$PYTHON" temporal_hypothesis_benchmark.py build-cases \
  --metadata "$RUN_ROOT/temporal_metadata.json" \
  --papers-dir "$EXPERIMENT/outputs/papers" \
  --v2-dir "$RUN_ROOT/materials_evidence_v2" \
  --output-dir "$RUN_ROOT/benchmark_cases" \
  --train-through 2023 \
  --validation-year 2024 \
  --include-validation \
  --resume

run_stage benchmark_experiments \
  "$PYTHON" temporal_hypothesis_benchmark.py run \
  --metadata "$RUN_ROOT/temporal_metadata.json" \
  --papers-dir "$EXPERIMENT/outputs/papers" \
  --v1-dir "$EXPERIMENT/materials_evidence" \
  --v2-dir "$RUN_ROOT/materials_evidence_v2" \
  --triage "$RUN_ROOT/question_triage.json" \
  --cases-dir "$RUN_ROOT/benchmark_cases" \
  --output-dir "$RUN_ROOT/experiment_runs" \
  --resume

CURRENT_STAGE=complete
write_status "complete" "complete" "All temporal v2 extraction and benchmark experiments completed"
touch "$RUN_ROOT/COMPLETE"
echo "[$(date -Is)] ALL STAGES COMPLETE" | tee -a "$LOG_DIR/pipeline.log"
