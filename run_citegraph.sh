#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_ROOT="$ROOT/experiments/high_temperature_hea_qwen35b/citegraph"
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
CURRENT_STAGE="setup"
FINAL_STATE_WRITTEN=0

mkdir -p "$LOG_DIR"

write_status() {
  "$PYTHON" - "$STATUS" "$1" "$2" "$3" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
temporary = path.with_suffix(".json.tmp")
temporary.write_text(json.dumps({"state": sys.argv[2], "stage": sys.argv[3], "message": sys.argv[4],
                                 "updated_at": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n")
temporary.replace(path)
PY
}

stop_server() {
  if [[ "$STARTED_SERVER" -eq 1 && -n "$SERVER_PID" ]]; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
    STARTED_SERVER=0
  fi
}

cleanup() {
  local exit_code=$?
  stop_server
  if [[ "$exit_code" -ne 0 && "$FINAL_STATE_WRITTEN" -eq 0 ]]; then
    write_status "failed" "$CURRENT_STAGE" "Stopped with exit code $exit_code; rerun this script to resume"
  fi
  exit "$exit_code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP

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
  # Same server settings as run_eval_v3.sh, run_eval_kg.sh and run_eval_critique.sh.
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
    --temp 0.2 \
    --metrics \
    >"$LOG_DIR/llama-server.log" 2>&1 &
  SERVER_PID=$!
  STARTED_SERVER=1
  for _ in $(seq 1 180); do
    curl --fail --silent "$HEALTH_URL" >/dev/null 2>&1 && break
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
      echo "llama-server exited during startup" >&2
      tail -n 80 "$LOG_DIR/llama-server.log" >&2
      exit 1
    fi
    sleep 2
  done
fi
curl --fail --silent "$HEALTH_URL" | tee "$LOG_DIR/server-health.json"

export MATHG_PROVIDER=openai
export OPENAI_BASE_URL="$SERVER_URL"
export OPENAI_API_KEY=local
export OPENAI_MODEL=Qwen3.5-35B-A3B-Q4_K_M.gguf
export OPENAI_CHAT_TEMPLATE_KWARGS='{"enable_thinking":false}'
export MATHG_CONTEXT_WINDOW=32768
export JUDGE_PROVIDER=trapi
export JUDGE_TRAPI_DEPLOYMENT="${JUDGE_TRAPI_DEPLOYMENT:-gpt-5.6-sol_2026-07-09}"

# Acquisition is network-bound (Europe PMC, OpenAlex); extraction and generation use the local server.
MATHG_REQUEST_TIMEOUT=600 run_stage acquire "$PYTHON" citegraph.py acquire
MATHG_REQUEST_TIMEOUT=900 run_stage extract "$PYTHON" citegraph.py extract --workers 4
MATHG_REQUEST_TIMEOUT=900 run_stage extract_retry "$PYTHON" citegraph.py extract --workers 4
run_stage graph "$PYTHON" citegraph.py graph
# A failed generation gets exactly one retry; the failed run is copied to failed_attempts/ first.
MATHG_REQUEST_TIMEOUT=600 run_stage generate "$PYTHON" citegraph.py generate --workers 4
MATHG_REQUEST_TIMEOUT=600 run_stage generate_retry "$PYTHON" citegraph.py generate --workers 4
stop_server

CURRENT_STAGE="trapi"
write_status "running" "trapi" "Judging, cross-judging and auditing in parallel"
echo "[$(date -Is)] START trapi stages" | tee -a "$LOG_DIR/pipeline.log"
"$PYTHON" citegraph.py judge --workers 8 >"$LOG_DIR/judge.log" 2>&1 &
"$PYTHON" citegraph.py cross_judge --workers 6 >"$LOG_DIR/cross_judge.log" 2>&1 &
"$PYTHON" citegraph.py audit --workers 10 >"$LOG_DIR/audit.log" 2>&1 &
wait
for stage in judge cross_judge audit; do
  "$PYTHON" citegraph.py "$stage" --workers 4 >>"$LOG_DIR/${stage}.log" 2>&1
done
echo "[$(date -Is)] DONE trapi stages" | tee -a "$LOG_DIR/pipeline.log"

run_stage report "$PYTHON" citegraph.py report

CURRENT_STAGE=integrity
if ! "$PYTHON" -c 'import json, sys; sys.exit(0 if json.load(open(sys.argv[1]))["integrity"]["verified"] else 1)' \
  "$RUN_ROOT/results/analysis.json"; then
  write_status "needs_attention" "integrity" "Integrity not verified; see results/analysis.json. Rerun to resume."
  FINAL_STATE_WRITTEN=1
  echo "[$(date -Is)] INTEGRITY NOT VERIFIED" | tee -a "$LOG_DIR/pipeline.log"
  exit 2
fi
CURRENT_STAGE=complete
write_status "complete" "complete" "Citation-graph variants generated, judged and analysed with verified integrity"
FINAL_STATE_WRITTEN=1
touch "$RUN_ROOT/COMPLETE"
echo "[$(date -Is)] ALL STAGES COMPLETE" | tee -a "$LOG_DIR/pipeline.log"
