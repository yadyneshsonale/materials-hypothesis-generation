#!/bin/bash
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop/logs
export MATHG_REQUEST_TIMEOUT=600
for i in 1 2; do ./.venv/bin/python hypo_loop.py generate --method closed_book --method text_chunks --split dev --workers 6 >> $L/baselines.log 2>&1; done
./.venv/bin/python hypo_loop.py evaluate --method closed_book --method text_chunks --workers 8 >> $L/baselines.log 2>&1
./.venv/bin/python hypo_loop.py evaluate --method closed_book --method text_chunks --workers 4 >> $L/baselines.log 2>&1
echo BASELINES_DONE >> $L/baselines.log
