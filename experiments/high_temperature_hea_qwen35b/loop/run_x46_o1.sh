#!/bin/bash
# Experiment 46 (loop.md 27.1), o1 pairwise alongside DeepSeek: phase 1a against the writer, then the phase-1b top five
# once run_x46.sh has chosen them. 6 workers (must_obey.md 7).
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop_quality/logs
mkdir -p "$L"
export MATHG_REQUEST_TIMEOUT=600 MATHG_TRAPI_LOG=$L/trapi_o1.jsonl
args() { for m in "$@"; do printf -- "--method %s " "$m"; done; }
O() { MATHG_WORKLOAD_ID=mathg-exp46-o1-$1 ./.venv/bin/python quality_eval.py pairwise --judge o1 "${@:2}" --workers 6 \
  >> "$L/o1.log" 2>&1; }
PAV=$(./.venv/bin/python quality_eval.py list --phase a_vs 2>/dev/null)
for pass in 1 2; do O a $(args $PAV); done
echo "X46_O1_A_DONE $(date -Is)" >> "$L/main.log"
until grep -q "^X46_TOP_B" "$L/main.log" 2>/dev/null; do sleep 600; done
TOP=$(grep "^X46_TOP_B" "$L/main.log" | tail -1 | cut -d' ' -f2-)
for pass in 1 2; do O b $(args $TOP); done
echo "X46_O1_DONE $(date -Is)" >> "$L/main.log"
