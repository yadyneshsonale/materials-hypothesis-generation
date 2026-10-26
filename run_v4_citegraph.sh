#!/usr/bin/env bash
# Experiment 32 (loop.md section 15.1): the citation-graph chain of run_v4_suite.sh, restarted after two fixes.
# 1. The first acquire stopped on a full text that Europe PMC kept failing to deliver (HTTP 500 on every try,
#    PMC9520225). Such papers now count as unavailable, like a 404 (citegraph.fetch_xml), and are skipped by the same
#    rule as papers without open full text.
# 2. Llama-3.3 wrote the cited title instead of the marker label in most citer statements, so the parser rejected
#    them (0.9 statements per new paper against 37 for the cached Qwen extractions). citegraph.marker_label maps a
#    copied marker text back to its label. The 91 affected statement files were re-extracted; the first graphs and
#    runs are kept in rerun_v4_scimon/citegraph_superseded/ and are not analysed. Seeds and expansions are copied
#    from there, so retrieval is unchanged.
# Same environment as run_v4_suite.sh; every stage resumes from the cached seeds, expansions, papers and extractions.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP="$ROOT/experiments/high_temperature_hea_qwen35b"
export MATHG_RUN_ROOT="$EXP/rerun_v4_scimon"
export MATHG_CASES_DIR="$EXP/benchmark_v4_scimon/cases_original12"
export MATHG_LEVELS=scimon MATHG_GRAPH_LEVEL=scimon MATHG_MIN_RETRIES=20
LOG_DIR="$MATHG_RUN_ROOT/logs"
PY="$ROOT/.venv/bin/python"
mkdir -p "$LOG_DIR"
cd "$ROOT"

GEN_ENV=(MATHG_PROVIDER=trapi TRAPI_DEPLOYMENT=Llama-3.3-70B-Instruct_5 MATHG_TEMPERATURE=0.2
         MATHG_REQUEST_TIMEOUT=600 JUDGE_PROVIDER=trapi JUDGE_TRAPI_DEPLOYMENT=gpt-5.6-sol_2026-07-09)

stage() {  # stage <chain> <name> <command...>
  local chain="$1" name="$2"
  shift 2
  echo "[$(date -Is)] START $chain/$name" | tee -a "$LOG_DIR/pipeline.log"
  if env "${GEN_ENV[@]}" "$@" >>"$LOG_DIR/$chain.$name.log" 2>&1; then
    echo "[$(date -Is)] DONE $chain/$name" | tee -a "$LOG_DIR/pipeline.log"
  else
    echo "[$(date -Is)] FAILED $chain/$name (exit $?)" | tee -a "$LOG_DIR/pipeline.log"
  fi
}

stage citegraph acquire_restart "$PY" citegraph.py acquire
for attempt in 1 2; do
  stage citegraph "extract_restart_$attempt" "$PY" citegraph.py extract --workers 6
done
stage citegraph graph "$PY" citegraph.py graph
stage citegraph generate "$PY" citegraph.py generate --workers 4
stage citegraph generate_retry "$PY" citegraph.py generate --workers 4
for s in judge cross_judge audit; do
  stage citegraph "$s" "$PY" citegraph.py "$s" --workers 6
done
for s in judge cross_judge audit; do
  stage citegraph "${s}_final" "$PY" citegraph.py "$s" --workers 4
done
stage citegraph report "$PY" citegraph.py report
echo "[$(date -Is)] CITEGRAPH CHAIN FINISHED" | tee -a "$LOG_DIR/pipeline.log"
touch "$MATHG_RUN_ROOT/CITEGRAPH_FINISHED"
