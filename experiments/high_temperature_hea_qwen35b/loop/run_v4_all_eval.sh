#!/bin/bash
# Experiment 32 (loop.md section 15.1): target-free audits and lever labels run alongside generation. The GPT-5.6
# judge keeps up with the slow Llama-heavy configurations, so its spare capacity is used now instead of after
# generation. These are the same stages as the final phase of run_v4_all.sh; both skip finished runs.
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
export MATHG_CASES_DIR=$E/benchmark_v4_scimon/cases MATHG_LEVELS=scimon MATHG_LOOP_ROOT=$E/loop_v4_scimon
export MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
L=$MATHG_LOOP_ROOT/logs
M=$(sed -n '/^M="/,/"$/p' experiments/high_temperature_hea_qwen35b/loop/run_v4_all.sh | tr -d '"' | sed 's/^M=//')
ARGS=""; for m in $M; do ARGS="$ARGS --method $m"; done
echo "START $(date -Is) configurations=$(echo $M | wc -w)" >> "$L/early_eval32.log"
while ! grep -q GEN_DONE "$L/gen32.done"; do
  ./.venv/bin/python hypo_loop.py audit $ARGS --workers 6
  ./.venv/bin/python hypo_loop.py label $ARGS --workers 6
  sleep 120
done >> "$L/early_eval32.log" 2>&1
echo "EARLY_EVAL_DONE $(date -Is)" >> "$L/early_eval32.log"
