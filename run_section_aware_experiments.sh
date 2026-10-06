#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPERIMENT="$ROOT/experiments/high_temperature_hea_qwen35b"
TEMPORAL="$EXPERIMENT/temporal_v2"
RUN_ROOT="$EXPERIMENT/section_aware"
LOG_DIR="$RUN_ROOT/logs"
STATUS="$RUN_ROOT/status.json"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
LLAMA_SERVER="${LLAMA_SERVER:-/home/t-ydsonale/.copilot/session-state/ddc46855-f88c-4679-a06a-5714ced0b156/files/llama.cpp/build-cu12/bin/llama-server}"
MODEL_PATH="${MODEL_PATH:-/home/t-ydsonale/.copilot/session-state/ddc46855-f88c-4679-a06a-5714ced0b156/files/models/Qwen3.5-35B-A3B-Q4_K_M.gguf}"
SERVER_URL="${OPENAI_BASE_URL:-http://127.0.0.1:8000/v1}"
HEALTH_URL="${SERVER_URL%/v1}/health"
SERVER_PID=""
STARTED_SERVER=0

mkdir -p "$LOG_DIR" "$RUN_ROOT/paper_maps" "$RUN_ROOT/papers" \
  "$RUN_ROOT/checkpoints" "$RUN_ROOT/results"

write_status() {
  "$PYTHON" - "$STATUS" "$1" "$2" "$3" <<'PY'
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path
path = Path(sys.argv[1])
payload = {
    "state": sys.argv[2], "stage": sys.argv[3], "message": sys.argv[4],
    "updated_at": datetime.now(timezone.utc).isoformat(), "pid": os.getppid(),
}
temporary = path.with_suffix(".json.tmp")
temporary.write_text(json.dumps(payload, indent=2) + "\n")
temporary.replace(path)
PY
}

cleanup() {
  code=$?
  if [[ "$STARTED_SERVER" -eq 1 && -n "$SERVER_PID" ]]; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  if [[ "$code" -ne 0 ]]; then
    write_status failed "${CURRENT_STAGE:-unknown}" "Pipeline failed with exit code $code"
  fi
  exit "$code"
}
trap cleanup EXIT

run_stage() {
  CURRENT_STAGE="$1"; shift
  write_status running "$CURRENT_STAGE" "Stage started"
  echo "[$(date -Is)] START $CURRENT_STAGE" | tee -a "$LOG_DIR/pipeline.log"
  "$@" 2>&1 | tee -a "$LOG_DIR/$CURRENT_STAGE.log"
  echo "[$(date -Is)] DONE $CURRENT_STAGE" | tee -a "$LOG_DIR/pipeline.log"
}

cd "$ROOT"
write_status starting server "Preparing local Qwen inference server"
if ! curl --fail --silent "$HEALTH_URL" >/dev/null 2>&1; then
  CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0,1,2,3}" \
    "$LLAMA_SERVER" --model "$MODEL_PATH" --host 127.0.0.1 --port 8000 \
    --ctx-size 131072 --parallel 4 --n-gpu-layers 99 --split-mode layer \
    --tensor-split 1,1,1,1 --flash-attn off --jinja --metrics \
    >"$LOG_DIR/llama-server.log" 2>&1 &
  SERVER_PID=$!
  STARTED_SERVER=1
  echo "$SERVER_PID" >"$RUN_ROOT/llama-server.pid"
  for _ in $(seq 1 180); do
    if curl --fail --silent "$HEALTH_URL" >/dev/null 2>&1; then break; fi
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
      tail -n 80 "$LOG_DIR/llama-server.log" >&2
      exit 1
    fi
    sleep 2
  done
fi
curl --fail --silent "$HEALTH_URL" >"$RUN_ROOT/server-health.json"

export MATHG_PROVIDER=openai
export OPENAI_BASE_URL="$SERVER_URL"
export OPENAI_API_KEY=local
export OPENAI_MODEL=Qwen3.5-35B-A3B-Q4_K_M.gguf
export OPENAI_CHAT_TEMPLATE_KWARGS='{"enable_thinking":false}'
export MATHG_CONTEXT_WINDOW=32768
export MATHG_REQUEST_TIMEOUT=300

run_stage extract \
  "$PYTHON" section_aware_extraction.py extract \
  --text-dir "$EXPERIMENT/data/corpus/text" \
  --evidence-dir "$TEMPORAL/materials_evidence_v2" \
  --output-dir "$RUN_ROOT/papers" \
  --map-dir "$RUN_ROOT/paper_maps" \
  --checkpoint-dir "$RUN_ROOT/checkpoints" \
  --workers 4 --resume

run_stage evaluate \
  "$PYTHON" section_aware_extraction.py evaluate \
  --text-dir "$EXPERIMENT/data/corpus/text" \
  --evidence-dir "$TEMPORAL/materials_evidence_v2" \
  --output-dir "$RUN_ROOT/papers" \
  --output "$RUN_ROOT/results/evaluation.json"

CURRENT_STAGE=complete
write_status complete complete "All 50 section-aware paper extractions and validation completed"
touch "$RUN_ROOT/COMPLETE"
echo "[$(date -Is)] ALL STAGES COMPLETE" | tee -a "$LOG_DIR/pipeline.log"
