#!/bin/bash
# Experiment 36 (loop.md 17.3): replaces run_web.sh's evaluation stages after generation. run_web.sh is stopped once
# generation is done, because its GPT-5.6 passes on the shared instance only add load to a rate-limited service;
# run_web_alt_eval.sh does the GPT-5.6 judge, audits and labels on the second instance. This script runs DeepSeek
# cross-judge passes (shared instance, which DeepSeek does not rate-limit) until every run has one, then marks the
# harness evaluations as handed over.
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
export MATHG_LOOP_ROOT=$E/loop_web MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
L=$MATHG_LOOP_ROOT/logs
pending() {
  ./.venv/bin/python -c "import hypo_loop as H; print(len(H._pending(None, '$1')))"
}
until [ "$(pending judgments/deepseek)" = 0 ]; do
  ./.venv/bin/python hypo_loop.py cross_judge --workers 8
  sleep 60
done >> "$L/cross36_finish.log" 2>&1
echo "CROSS_DONE $(date -Is)" >> "$L/cross36_finish.log"
echo "WEB_ALL_DONE $(date -Is) (GPT-5.6 stages by run_web_alt_eval.sh, DeepSeek by run_web_finish.sh)" >> "$L/label36.log"
