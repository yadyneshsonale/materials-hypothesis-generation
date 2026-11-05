#!/bin/bash
# Experiment 46 (loop.md 27.1), DeepSeek: phase 0 (sanity controls this session, grounding checks G1-G4), phase 1a
# (grounding and pairwise against the writer for the 15 configurations already scored on RQ, and the reference),
# phase 1b (the writer's RQ again in this session; RQ x3 and grounding for 35 more configurations, one at a time; then
# pairwise for the five with the highest SP), diagnostics. One stage at a time, 6 workers (must_obey.md 7).
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop_quality/logs
mkdir -p "$L"
export MATHG_REQUEST_TIMEOUT=600 MATHG_TRAPI_LOG=$L/trapi_deepseek.jsonl
Q() {  # Q <workload tag> <quality_eval arguments...>
  local tag=$1; shift
  MATHG_WORKLOAD_ID=mathg-exp46-$tag ./.venv/bin/python quality_eval.py "$@" --workers 6 >> "$L/deepseek.log" 2>&1
}
args() { for m in "$@"; do printf -- "--method %s " "$m"; done; }
report() { ./.venv/bin/python quality_eval.py report > "$L/report.log" 2>&1; }
list() { ./.venv/bin/python quality_eval.py list --phase "$1" 2>/dev/null; }
PA=$(list a); PAV=$(list a_vs); PB=$(list b); DIAG=$(list diag)
echo "X46_START $(date -Is)" >> "$L/main.log"
for pass in 1 2; do
  Q controls controls
  Q ground-validate ground_validate
done
report
echo "X46_VALIDATION_DONE $(date -Is)" >> "$L/main.log"
for pass in 1 2; do
  Q ground-a ground $(args writer_only_b_o3mini $PAV)
  Q pairwise-a pairwise --judge deepseek $(args $PAV)
done
report
echo "X46_A_PAIRWISE_DONE $(date -Is)" >> "$L/main.log"
for pass in 1 2; do
  for rep in 1 2 3; do Q rq-writer-session rq --kind rerun46 --rep $rep --method writer_only_b_o3mini; done
done
for m in $PB; do
  for pass in 1 2; do
    for rep in 1 2 3; do Q rq-b rq --rep $rep --method $m; done
    Q ground-b ground --method $m
  done
  report
  echo "X46_B_DONE $m $(date -Is)" >> "$L/main.log"
done
TOP=$(./.venv/bin/python quality_eval.py top_b --n 5 2>/dev/null)
echo "X46_TOP_B $TOP" >> "$L/main.log"
for pass in 1 2; do Q pairwise-b pairwise --judge deepseek $(args $TOP); done
report
echo "X46_B_PAIRWISE_DONE $(date -Is)" >> "$L/main.log"
for m in $DIAG; do
  for pass in 1 2; do for rep in 1 2 3; do Q rq-diag rq --rep $rep --method $m; done; done
done
report
echo "X46_DONE $(date -Is)" >> "$L/main.log"
