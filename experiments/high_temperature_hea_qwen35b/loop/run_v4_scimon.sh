#!/bin/bash
# Experiment 31 (loop.md section 14): the four pre-registered configurations on benchmark v4 (SciMON-style input),
# all 36 papers, one input per paper, 2 samples. Separate run root; the v3.1 runs are untouched.
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
export MATHG_CASES_DIR=$E/benchmark_v4_scimon/cases MATHG_LEVELS=scimon MATHG_LOOP_ROOT=$E/loop_v4_scimon
export MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
L=$MATHG_LOOP_ROOT/logs; mkdir -p $L
M="closed_book closed_book_o3mini writer_only_b_o3mini text_chunks_b_o3mini"
for m in $M; do
  ( for i in 1 2; do ./.venv/bin/python hypo_loop.py generate --method $m --split all36 --workers 4; done ) >> $L/gen.$m.log 2>&1 &
done
wait
ARGS=""; for m in $M; do ARGS="$ARGS --method $m"; done
( for i in 1 2 3; do ./.venv/bin/python hypo_loop.py cross_judge $ARGS --workers 8; done ) >> $L/cross.log 2>&1 &
for i in 1 2 3; do ./.venv/bin/python hypo_loop.py judge $ARGS --workers 10; done >> $L/judge.log 2>&1
wait
echo "JUDGED $(date -Is)" >> $L/judge.log
for i in 1 2; do ./.venv/bin/python hypo_loop.py audit $ARGS --workers 10; ./.venv/bin/python hypo_loop.py label $ARGS --workers 10; done >> $L/audit.log 2>&1
echo "V4_DONE $(date -Is)" >> $L/audit.log
