#!/bin/bash
# Pre-registered round-3 runs on the fresh TEST3 split (loop.md section 11.1). Run once.
# Usage: run_final3.sh <method> [<method> ...]
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop/logs
export MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
for m in "$@"; do
  ( for i in 1 2; do ./.venv/bin/python hypo_loop.py generate --method $m --split test3 --final --workers 4; done ) >> $L/final3.$m.log 2>&1 &
done
wait
ARGS=""; for m in "$@"; do ARGS="$ARGS --method $m"; done
for i in 1 2 3; do ./.venv/bin/python hypo_loop.py evaluate $ARGS --workers 8 >> $L/final3.evaluate.log 2>&1; done
echo "FINAL3_DONE $(date -Is)" >> $L/final3.evaluate.log
