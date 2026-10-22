#!/usr/bin/env bash
# Runs the LLM stages of stage_metrics.py in parallel, then retries failures once and builds the report.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
LOG_DIR="$ROOT/experiments/high_temperature_hea_qwen35b/stage_metrics/logs"
mkdir -p "$LOG_DIR"
export JUDGE_PROVIDER=trapi
export JUDGE_TRAPI_DEPLOYMENT="${JUDGE_TRAPI_DEPLOYMENT:-gpt-5.6-sol_2026-07-09}"

echo "[$(date -Is)] start LLM stages" | tee -a "$LOG_DIR/pipeline.log"
"$PYTHON" stage_metrics.py audit --workers 6 --resume >"$LOG_DIR/audit.log" 2>&1 &
"$PYTHON" stage_metrics.py inferability --workers 4 --resume >"$LOG_DIR/inferability.log" 2>&1 &
"$PYTHON" stage_metrics.py revision-review --workers 4 --resume >"$LOG_DIR/revision_review.log" 2>&1 &
"$PYTHON" stage_metrics.py retest --workers 8 --resume >"$LOG_DIR/retest.log" 2>&1 &
"$PYTHON" stage_metrics.py cross-judge --workers 6 --resume >"$LOG_DIR/cross_judge.log" 2>&1 &
wait
echo "[$(date -Is)] first pass done; retrying failures" | tee -a "$LOG_DIR/pipeline.log"
for stage in audit inferability revision-review retest cross-judge; do
  "$PYTHON" stage_metrics.py "$stage" --workers 4 --resume >>"$LOG_DIR/${stage//-/_}.log" 2>&1
done
echo "[$(date -Is)] LLM stages complete" | tee -a "$LOG_DIR/pipeline.log"
touch "$ROOT/experiments/high_temperature_hea_qwen35b/stage_metrics/LLM_STAGES_DONE"
