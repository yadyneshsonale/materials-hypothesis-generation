#!/bin/bash
# Experiment 45 (loop.md 26.1): generation. D on the questions that do not name the alloy class and E on the
# experiment-44 bases, then E on D. At most 6 o3-mini calls at once (MATHG_MAX_PER_DEPLOYMENT) over both instances.
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop_rx/logs
mkdir -p "$L"
export MATHG_MAX_PER_DEPLOYMENT=6 MATHG_REQUEST_TIMEOUT=600 MATHG_TRAPI_LOG=$L/trapi_x45.jsonl \
  MATHG_TRAPI_INSTANCES=https://trapi.research.microsoft.com/gcr/shared,https://trapi.research.microsoft.com/redmond/interactive
echo "X45_START $(date -Is)" >> "$L/x45_main.log"
for pass in 1 2 3; do
  MATHG_WORKLOAD_ID=mathg-exp45-generate ./.venv/bin/python edit_experiment.py generate --workers 6 \
    >> "$L/x45_generate.log" 2>&1
done
echo "X45_GENERATE_DONE $(date -Is)" >> "$L/x45_main.log"
