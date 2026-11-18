#!/bin/bash
# Experiment 48 (loop.md 27.7): generation of synth_a and synth_b, then DeepSeek non-copying, RQ x3, pairwise v2 and v1
# against rx_r, and the report. One stage at a time, at most 6 workers per model (must_obey.md 7).
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop_quality/logs
mkdir -p "$L"
export MATHG_REQUEST_TIMEOUT=600 MATHG_MAX_PER_DEPLOYMENT=6 MATHG_TRAPI_LOG=$L/trapi_x48.jsonl \
  MATHG_TRAPI_INSTANCES=https://trapi.research.microsoft.com/gcr/shared,https://trapi.research.microsoft.com/redmond/interactive
S() { local tag=$1; shift; MATHG_WORKLOAD_ID=mathg-exp48-$tag ./.venv/bin/python synth_eval.py "$@" \
  >> "$L/x48.log" 2>&1; }
echo "X48_START $(date -Is)" >> "$L/main.log"
for pass in 1 2 3; do S generate generate --workers 6; done
echo "X48_GENERATE_DONE $(date -Is)" >> "$L/main.log"
for pass in 1 2; do S noncopy noncopy --workers 6; done
for pass in 1 2; do for rep in 1 2 3; do S rq$rep rq --rep $rep --workers 6; done; done
for pass in 1 2; do S pair-v2 pairwise --judge deepseek --prompt v2 --workers 6; done
for pass in 1 2; do S pair-v1 pairwise --judge deepseek --prompt v1 --workers 6; done
./.venv/bin/python synth_eval.py report > "$L/x48_report.log" 2>&1
echo "X48_DEEPSEEK_DONE $(date -Is)" >> "$L/main.log"
