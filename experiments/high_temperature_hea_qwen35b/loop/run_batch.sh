#!/bin/bash
# Usage: run_batch.sh <batch-name> <method> [<method> ...]   (dev split; generation then evaluation)
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop/logs
B=$1; shift
export MATHG_REQUEST_TIMEOUT=600
for m in "$@"; do
  ( for i in 1 2; do ./.venv/bin/python hypo_loop.py generate --method $m --split dev --workers 4; done ) >> $L/$B.$m.log 2>&1 &
done
wait
ARGS=""; for m in "$@"; do ARGS="$ARGS --method $m"; done
for i in 1 2; do ./.venv/bin/python hypo_loop.py evaluate $ARGS --workers 8 >> $L/$B.evaluate.log 2>&1; done
echo "BATCH_DONE $B $(date -Is)" >> $L/$B.evaluate.log
