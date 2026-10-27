#!/bin/bash
# Experiment 34 (loop.md 16.1): generate the given configurations on the 36 spent papers (split all36, v3.1 input),
# then both judges, target-free audits, lever labels and checklist scores (both judges).
# Usage: run_review_b.sh <method> [<method> ...]
cd /home/t-ydsonale/materials-hypothesis-generation
export MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
L=experiments/high_temperature_hea_qwen35b/loop/logs
TAG=$(date +%H%M%S)
for m in "$@"; do
  ( for i in 1 2; do ./.venv/bin/python hypo_loop.py generate --method $m --split all36 --workers 4; done ) >> $L/review_b.$m.log 2>&1 &
done
wait
ARGS=""; for m in "$@"; do ARGS="$ARGS --method $m"; done
( for i in 1 2 3; do ./.venv/bin/python hypo_loop.py cross_judge $ARGS --workers 8; done ) >> $L/review_b.cross.$TAG.log 2>&1 &
( for i in 1 2 3; do ./.venv/bin/python hypo_loop.py judge $ARGS --workers 8; done ) >> $L/review_b.judge.$TAG.log 2>&1 &
wait
for i in 1 2; do ./.venv/bin/python hypo_loop.py audit $ARGS --workers 8; ./.venv/bin/python hypo_loop.py label $ARGS --workers 8; done >> $L/review_b.audit.$TAG.log 2>&1
for i in 1 2 3; do ./.venv/bin/python checklist_judge.py score --target phaseb --workers 8; done >> $L/review_b.checklist.$TAG.log 2>&1
echo "REVIEW_B_DONE $* $(date -Is)" >> $L/review_b.done
