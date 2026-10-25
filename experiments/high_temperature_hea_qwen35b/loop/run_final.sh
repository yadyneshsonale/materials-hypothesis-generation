#!/bin/bash
# Pre-registered final runs on the TEST split (loop.md section 6). Run once.
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop/logs
export MATHG_REQUEST_TIMEOUT=600
M="trend_ground_b_o3mini scaffold_ensemble closed_book text_chunks closed_book_o3mini writer_only_b_o3mini"
for m in $M; do
  ( for i in 1 2; do ./.venv/bin/python hypo_loop.py generate --method $m --split test --final --workers 4; done ) >> $L/final.$m.log 2>&1 &
done
wait
ARGS=""; for m in $M; do ARGS="$ARGS --method $m"; done
for i in 1 2 3; do ./.venv/bin/python hypo_loop.py evaluate $ARGS --workers 8 >> $L/final.evaluate.log 2>&1; done
echo "FINAL_DONE $(date -Is)" >> $L/final.evaluate.log
