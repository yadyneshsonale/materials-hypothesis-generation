#!/bin/bash
# Experiment 29 (loop.md section 12): sensitivity runs on dev3. Generation in parallel, then the GPT-5.6 judge and the
# DeepSeek cross-judge in parallel (the two use different deployments), then target-free audits.
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop/logs
export MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
M="papers_n1_b_o3mini papers_n3_b_o3mini papers_n10_b_o3mini papers_n30_b_o3mini papers_random10_b_o3mini text_4k_b_o3mini text_64k_b_o3mini writer_only_b_o3mini_low"
for m in $M; do
  ( for i in 1 2; do ./.venv/bin/python hypo_loop.py generate --method $m --split dev3 --workers 3; done ) >> $L/sens.$m.log 2>&1 &
done
wait
ARGS=""; for m in $M; do ARGS="$ARGS --method $m"; done
( for i in 1 2 3; do ./.venv/bin/python hypo_loop.py cross_judge $ARGS --workers 8; done ) >> $L/sens.cross.log 2>&1 &
for i in 1 2 3; do ./.venv/bin/python hypo_loop.py judge $ARGS --workers 12; done >> $L/sens.judge.log 2>&1
wait
echo "JUDGED $(date -Is)" >> $L/sens.judge.log
for i in 1 2; do ./.venv/bin/python hypo_loop.py audit $ARGS --workers 12; done >> $L/sens.audit.log 2>&1
echo "SENS_DONE $(date -Is)" >> $L/sens.audit.log
