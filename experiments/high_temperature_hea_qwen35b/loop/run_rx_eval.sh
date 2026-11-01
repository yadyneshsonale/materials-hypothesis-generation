#!/bin/bash
# Experiment 44, DeepSeek evaluation (reconstruction, research quality x3, pairwise quality, pack labels), one stage
# at a time (at most 6 DeepSeek workers in total). Passes repeat while generation runs; a final pass follows it.
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop_rx/logs
mkdir -p "$L"
export MATHG_REQUEST_TIMEOUT=600 MATHG_TRAPI_LOG=$L/trapi_eval.jsonl
evaluate() {
  for stage in deepseek "rq --rep 1" "rq --rep 2" "rq --rep 3" pairwise packlabels; do
    MATHG_WORKLOAD_ID=mathg-exp44-eval-${stage// /} ./.venv/bin/python rx_experiment.py $stage --workers 6 \
      >> "$L/eval.log" 2>&1
  done
}
until grep -q "GENERATE_DONE" "$L/main.log" 2>/dev/null; do
  evaluate
  sleep 600
done
evaluate
evaluate
./.venv/bin/python rx_experiment.py report > "$L/report.log" 2>&1
echo "EVAL_DONE $(date -Is)" >> "$L/main.log"
