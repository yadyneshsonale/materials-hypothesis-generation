#!/bin/bash
# Experiment 47 (loop.md 27.5), DeepSeek: non-copying for rx_r and the closed-book writer, then pairwise v2 (rx_r vs
# the writer, both orders), then the report. One stage at a time, 6 workers (must_obey.md 7).
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop_quality/logs
mkdir -p "$L"
export MATHG_REQUEST_TIMEOUT=600 MATHG_TRAPI_LOG=$L/trapi_x47_deepseek.jsonl
N() { local tag=$1; shift; MATHG_WORKLOAD_ID=mathg-exp47-$tag ./.venv/bin/python noncopy_eval.py "$@" --workers 6 \
  >> "$L/x47.log" 2>&1; }
echo "X47_START $(date -Is)" >> "$L/main.log"
for pass in 1 2 3; do N noncopy noncopy; done
echo "X47_NONCOPY_DONE $(date -Is)" >> "$L/main.log"
for pass in 1 2 3; do N pairwise pairwise --judge deepseek; done
./.venv/bin/python noncopy_eval.py report > "$L/x47_report.log" 2>&1
echo "X47_DEEPSEEK_DONE $(date -Is)" >> "$L/main.log"
