#!/bin/bash
# Experiment 44 (loop.md 25.1), generation: the focused corpora, then all seven arms in one process, so that
# MATHG_MAX_PER_DEPLOYMENT=6 caps every model's requests in flight (must_obey.md 7), then the same screener on the
# experiment-36 corpora (diagnostic). Each stage is resumable; failed runs are retried by a further pass. Version 2:
# calls go to whichever of the two TRAPI instances (each with its own token quota) is not rate-limited.
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop_rx/logs
mkdir -p "$L"
export MATHG_MAX_PER_DEPLOYMENT=6 MATHG_REQUEST_TIMEOUT=600 MATHG_TRAPI_LOG=$L/trapi_main.jsonl \
  MATHG_TRAPI_INSTANCES=https://trapi.research.microsoft.com/gcr/shared,https://trapi.research.microsoft.com/redmond/interactive
echo "START $(date -Is)" >> "$L/main.log"
for pass in 1 2 3; do
  MATHG_WORKLOAD_ID=mathg-exp44-build ./.venv/bin/python rx_experiment.py build --workers 6 >> "$L/build.log" 2>&1
done
echo "BUILD_DONE $(date -Is)" >> "$L/main.log"
for pass in 1 2 3; do
  MATHG_WORKLOAD_ID=mathg-exp44-generate ./.venv/bin/python rx_experiment.py generate --workers 24 \
    >> "$L/generate.log" 2>&1
done
echo "GENERATE_DONE $(date -Is)" >> "$L/main.log"
for pass in 1 2; do
  MATHG_WORKLOAD_ID=mathg-exp44-screen-old ./.venv/bin/python rx_experiment.py screen_old --workers 6 \
    >> "$L/screen_old.log" 2>&1
done
echo "MAIN_DONE $(date -Is)" >> "$L/main.log"
