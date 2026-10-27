#!/bin/bash
# Experiment 35 (loop.md 16.1 C3, addendum 2): the pre-registered test4 finals, run once. There is no finalist, so only
# the replication runs: the incumbent writer and the Llama baseline. Then both judges, audits, labels, checklist
# scores and the A6 answer-key audit on the test4 keys.
cd /home/t-ydsonale/materials-hypothesis-generation
export MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
L=experiments/high_temperature_hea_qwen35b/loop/logs
M="writer_only_b_o3mini closed_book"
for m in $M; do
  ( for i in 1 2; do ./.venv/bin/python hypo_loop.py generate --method $m --split test4 --final --workers 4; done ) >> $L/test4.$m.log 2>&1 &
done
wait
ARGS=""; for m in $M; do ARGS="$ARGS --method $m"; done
( for i in 1 2 3; do ./.venv/bin/python hypo_loop.py cross_judge $ARGS --workers 6; done ) >> $L/test4.cross.log 2>&1 &
( for i in 1 2 3; do ./.venv/bin/python hypo_loop.py judge $ARGS --workers 6; done ) >> $L/test4.judge.log 2>&1 &
wait
for i in 1 2; do ./.venv/bin/python hypo_loop.py audit $ARGS --workers 6; ./.venv/bin/python hypo_loop.py label $ARGS --workers 6; done >> $L/test4.audit.log 2>&1
echo "TEST4_FINALS_DONE $(date -Is)" >> $L/test4.done
