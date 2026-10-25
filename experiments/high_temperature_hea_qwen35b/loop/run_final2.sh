#!/bin/bash
# Pre-registered round-2 runs on the fresh TEST2 split (loop.md sections 10.1 and 10.5). Run once.
# Usage: run_final2.sh <method> [<method> ...]
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop/logs
export MATHG_REQUEST_TIMEOUT=600
for m in "$@"; do
  ( for i in 1 2; do ./.venv/bin/python hypo_loop.py generate --method $m --split test2 --final --workers 4; done ) >> $L/final2.$m.log 2>&1 &
done
wait
ARGS=""; for m in "$@"; do ARGS="$ARGS --method $m"; done
for i in 1 2 3; do ./.venv/bin/python hypo_loop.py evaluate $ARGS --workers 8 >> $L/final2.evaluate.log 2>&1; done
echo "FINAL2_DONE $(date -Is)" >> $L/final2.evaluate.log
