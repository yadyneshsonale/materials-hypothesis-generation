#!/bin/bash
# Experiment 45 (loop.md 26.1): DeepSeek reconstruction while generation runs; then RQ x3, target-free pairwise
# (DeepSeek, o1; both orders) and the report. One stage at a time, at most 6 workers per model.
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop_rx/logs
mkdir -p "$L"
export MATHG_REQUEST_TIMEOUT=600 MATHG_TRAPI_LOG=$L/trapi_x45_eval.jsonl
stage() {  # stage <args...>
  MATHG_WORKLOAD_ID=mathg-exp45-eval-$(echo "$*" | tr -d ' -') ./.venv/bin/python edit_experiment.py "$@" --workers 6 \
    >> "$L/x45_eval.log" 2>&1
}
until grep -q "X45_GENERATE_DONE" "$L/x45_main.log" 2>/dev/null; do
  stage deepseek
  sleep 300
done
for pass in 1 2; do
  stage deepseek
done
echo "X45_DEEPSEEK_DONE $(date -Is)" >> "$L/x45_main.log"
./.venv/bin/python edit_experiment.py report > "$L/x45_report.log" 2>&1
for pass in 1 2; do
  stage rq --rep 1
  stage rq --rep 2
  stage rq --rep 3
  stage pairwise --judge deepseek
  stage pairwise --judge o1
done
./.venv/bin/python edit_experiment.py report > "$L/x45_report.log" 2>&1
echo "X45_EVAL_DONE $(date -Is)" >> "$L/x45_main.log"
