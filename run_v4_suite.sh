#!/usr/bin/env bash
# Experiment 32 (loop.md section 15.1): the experiment-21 suite (experiments 7, 9, 11, 14, 16, 17) re-run on the
# SciMON-style input of benchmark v4, for the 12 papers it was built for, with the same pre-cutoff generator
# (Llama-3.3-70B-Instruct) and judges (GPT-5.6, DeepSeek-V4-Pro).
#
# Differences from run_clean_rerun.sh (experiment 21):
# - Cases: benchmark_v4_scimon/cases_original12, one level ("scimon").
# - The citation graph is built from the v4 input (MATHG_GRAPH_LEVEL=scimon).
# - New citation-graph papers are extracted by Llama-3.3, a pre-cutoff extractor (must_obey.md 4.5). The local Qwen
#   extractor needs a GPU, and all four are in use by other users. Papers already in the cache keep their Qwen
#   extractions; every card records its extractor.
# - Experiments 7, 9 and 11 also get the DeepSeek cross-judge and the target-free audit (suite_extra_eval.py).
# - The generator x queries factorial is not re-run.
# Every output goes to experiments/high_temperature_hea_qwen35b/rerun_v4_scimon; nothing earlier is overwritten.
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

chain_v3() {  # experiments 7, 9, 11
  stage v3 generate "$PY" temporal_eval_v3.py generate --workers 4 --resume
  stage v3 generate_retry "$PY" temporal_eval_v3.py generate --workers 4 --resume
  stage v3 judge "$PY" temporal_eval_v3.py judge --workers 6 --resume
  stage v3 analyze "$PY" temporal_eval_v3.py analyze
  stage kg prepare "$PY" temporal_eval_kg.py prepare
  stage kg generate "$PY" temporal_eval_kg.py generate --workers 4 --resume
  stage kg generate_retry "$PY" temporal_eval_kg.py generate --workers 4 --resume
  stage kg judge "$PY" temporal_eval_kg.py judge --workers 6 --resume
  stage kg analyze "$PY" temporal_eval_kg.py analyze
  stage critique resample_generate "$PY" temporal_eval_critique.py resample-generate --workers 4 --resume
  stage critique resample_generate_retry "$PY" temporal_eval_critique.py resample-generate --workers 4 --resume
  stage critique resample_judge "$PY" temporal_eval_critique.py resample-judge --workers 6 --resume
  stage critique revise "$PY" temporal_eval_critique.py revise --workers 4 --resume
  stage critique revise_retry "$PY" temporal_eval_critique.py revise --workers 4 --resume
  stage critique judge "$PY" temporal_eval_critique.py judge --workers 6 --resume
  stage critique analyze "$PY" temporal_eval_critique.py analyze
  for i in 1 2; do
    stage extra "cross_judge_$i" "$PY" suite_extra_eval.py cross_judge --workers 6
    stage extra "audit_$i" "$PY" suite_extra_eval.py audit --workers 6
  done
}

chain_rubric() {  # experiments 14 and 16
  stage rubric generate "$PY" rubric_eval.py generate --workers 4 --resume
  stage rubric generate_retry "$PY" rubric_eval.py generate --workers 4 --resume
  stage improvements generate "$PY" improvement_eval.py generate --workers 4 --resume
  stage improvements generate_retry "$PY" improvement_eval.py generate --workers 4 --resume
  stage improvements refine "$PY" improvement_eval.py refine --workers 4 --resume
  stage improvements refine_retry "$PY" improvement_eval.py refine --workers 4 --resume
  stage improvements select "$PY" improvement_eval.py select --workers 4 --resume
  for s in judge cross-judge audit ceiling; do
    stage rubric "$s" "$PY" rubric_eval.py "$s" --workers 6 --resume
  done
  for s in judge cross-judge audit; do
    stage improvements "$s" "$PY" improvement_eval.py "$s" --workers 6 --resume
  done
}

chain_citegraph() {  # experiment 17
  stage citegraph acquire "$PY" citegraph.py acquire
  for attempt in 1 2; do
    stage citegraph "extract_$attempt" "$PY" citegraph.py extract --workers 4
  done
  stage citegraph graph "$PY" citegraph.py graph
  stage citegraph generate "$PY" citegraph.py generate --workers 4
  stage citegraph generate_retry "$PY" citegraph.py generate --workers 4
  for s in judge cross_judge audit; do
    stage citegraph "$s" "$PY" citegraph.py "$s" --workers 6
  done
}

chain_v3 &
chain_rubric &
chain_citegraph &
wait

# Reports need every chain (citegraph compares against the rubric and improvement baselines).
for s in judge cross-judge audit; do stage rubric "${s}_final" "$PY" rubric_eval.py "$s" --workers 4 --resume; done
for s in judge cross-judge audit; do stage improvements "${s}_final" "$PY" improvement_eval.py "$s" --workers 4 --resume; done
for s in judge cross_judge audit; do stage citegraph "${s}_final" "$PY" citegraph.py "$s" --workers 4; done
for s in cross_judge audit; do stage extra "${s}_final" "$PY" suite_extra_eval.py "$s" --workers 4; done
stage rubric report "$PY" rubric_eval.py report
stage improvements report "$PY" improvement_eval.py report
stage citegraph report "$PY" citegraph.py report
echo "[$(date -Is)] ALL CHAINS FINISHED" | tee -a "$LOG_DIR/pipeline.log"
touch "$MATHG_RUN_ROOT/FINISHED"
