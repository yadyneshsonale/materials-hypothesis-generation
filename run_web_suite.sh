#!/usr/bin/env bash
# Experiment 36 (loop.md 17.1-17.2): the experiment-21 suite (experiments 7, 9, 11, 14, 16, 17) re-run with web search,
# on the same 12 papers and v3 questions, with the same pre-cutoff generator (Llama-3.3-70B-Instruct) and judges
# (GPT-5.6, DeepSeek-V4-Pro).
#
# Differences from run_clean_rerun.sh (experiment 21):
# - MATHG_EVIDENCE=web: every evidence arm uses its question's web-search corpus (websearch.py), and the tool agents
#   (experiments 7, 9, 11) also get a live web_search tool.
# - Only arms whose evidence can come from XML run. LLM-extracted arms (effects, mechanisms, gaps, mixed, v2 units,
#   v2 one-shot) are not re-run. Closed-book arms are copied from rerun_v3 (web_suite_prepare.py).
# - The citation graphs are built from each paper's problem-level web corpus: XML cards and verbatim citing sentences,
#   with no extraction stage.
# - Experiments 7, 9 and 11 also get the DeepSeek cross-judge and the target-free audit (suite_extra_eval.py).
# Every output goes to experiments/high_temperature_hea_qwen35b/rerun_web; nothing earlier is overwritten.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP="$ROOT/experiments/high_temperature_hea_qwen35b"
export MATHG_RUN_ROOT="$EXP/rerun_web"
export MATHG_CASES_DIR="$EXP/benchmark_v3/cases"
export MATHG_EVIDENCE=web MATHG_MIN_RETRIES=20
LOG_DIR="$MATHG_RUN_ROOT/logs"
PY="$ROOT/.venv/bin/python"
mkdir -p "$LOG_DIR"
cd "$ROOT"

# GPT-5.6 calls go to a second TRAPI instance of the same deployment, with few workers: the shared instance
# rate-limited nearly every call (loop.md 17.3). Every other model stays on the shared instance.
GEN_ENV=(MATHG_PROVIDER=trapi TRAPI_DEPLOYMENT=Llama-3.3-70B-Instruct_5 MATHG_TEMPERATURE=0.2
         MATHG_REQUEST_TIMEOUT=600 JUDGE_PROVIDER=trapi JUDGE_TRAPI_DEPLOYMENT=gpt-5.6-sol_2026-07-09
         JUDGE_TRAPI_ENDPOINT=https://trapi.research.microsoft.com/redmond/interactive)
GW=2  # workers for GPT-5.6 stages

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

# Nothing runs before every corpus is built and the gate passes (the gate is run by loop/run_web.sh).
until [ -f "$EXP/websearch/logs/gate.status" ]; do sleep 60; done
grep -q GATE_PASSED "$EXP/websearch/logs/gate.status" \
  || { echo "[$(date -Is)] GATE FAILED" | tee -a "$LOG_DIR/pipeline.log"; exit 1; }
stage prepare copy_baselines "$PY" web_suite_prepare.py

chain_v3() {  # experiments 7, 9, 11
  for i in 1 2; do
    stage v3 "generate_$i" "$PY" temporal_eval_v3.py generate --setting text_oneshot --setting tool_agent \
      --workers 4 --resume
  done
  stage v3 judge "$PY" temporal_eval_v3.py judge --workers $GW --resume
  stage kg prepare "$PY" temporal_eval_kg.py prepare
  for i in 1 2; do stage kg "generate_$i" "$PY" temporal_eval_kg.py generate --workers 4 --resume; done
  stage kg judge "$PY" temporal_eval_kg.py judge --workers $GW --resume
  for i in 1 2; do
    stage critique "resample_generate_$i" "$PY" temporal_eval_critique.py resample-generate --workers 4 --resume
  done
  stage critique resample_judge "$PY" temporal_eval_critique.py resample-judge --workers $GW --resume
  for i in 1 2; do stage critique "revise_$i" "$PY" temporal_eval_critique.py revise --workers 4 --resume; done
  stage critique judge "$PY" temporal_eval_critique.py judge --workers $GW --resume
  for i in 1 2; do
    stage extra "cross_judge_$i" "$PY" suite_extra_eval.py cross_judge --workers 6
    stage extra "audit_$i" "$PY" suite_extra_eval.py audit --workers $GW
  done
}

chain_rubric() {  # experiments 14 and 16
  for i in 1 2; do
    stage rubric "generate_$i" "$PY" rubric_eval.py generate --arm text_chunks --arm card --workers 4 --resume
    stage improvements "generate_$i" "$PY" improvement_eval.py generate --arm text_systemmatch \
      --arm card_systemmatch --workers 4 --resume
    stage improvements "refine_$i" "$PY" improvement_eval.py refine --workers 4 --resume
  done
  stage improvements select "$PY" improvement_eval.py select --workers 4 --resume
  for s in judge cross-judge audit; do
    w=$GW; [ "$s" = cross-judge ] && w=6
    stage rubric "$s" "$PY" rubric_eval.py "$s" --workers $w --resume
    stage improvements "$s" "$PY" improvement_eval.py "$s" --workers $w --resume
  done
}

chain_citegraph() {  # experiment 17
  stage citegraph graph "$PY" citegraph.py graph
  for i in 1 2; do stage citegraph "generate_$i" "$PY" citegraph.py generate --workers 4; done
  for s in judge cross_judge audit; do
    w=$GW; [ "$s" = cross_judge ] && w=6
    stage citegraph "$s" "$PY" citegraph.py "$s" --workers $w
  done
}

chain_v3 &
chain_rubric &
chain_citegraph &
wait

for s in judge cross-judge audit; do stage rubric "${s}_final" "$PY" rubric_eval.py "$s" --workers $GW --resume; done
for s in judge cross-judge audit; do stage improvements "${s}_final" "$PY" improvement_eval.py "$s" --workers $GW --resume; done
for s in judge cross_judge audit; do stage citegraph "${s}_final" "$PY" citegraph.py "$s" --workers $GW; done
for s in cross_judge audit; do stage extra "${s}_final" "$PY" suite_extra_eval.py "$s" --workers $GW; done
stage v3 analyze "$PY" temporal_eval_v3.py analyze
stage kg analyze "$PY" temporal_eval_kg.py analyze
stage critique analyze "$PY" temporal_eval_critique.py analyze
stage rubric report "$PY" rubric_eval.py report
stage improvements report "$PY" improvement_eval.py report
stage citegraph report "$PY" citegraph.py report
echo "[$(date -Is)] ALL CHAINS FINISHED" | tee -a "$LOG_DIR/pipeline.log"
touch "$MATHG_RUN_ROOT/FINISHED"
