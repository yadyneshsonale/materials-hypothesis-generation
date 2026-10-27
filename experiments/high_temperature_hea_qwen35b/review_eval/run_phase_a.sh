#!/bin/bash
# Experiment 33 (loop.md 16.1): API stages of the measurement checks. GPT-5.6 is rate-limited (shared quota), so each
# stage interleaves its GPT-5.6 and DeepSeek jobs and repeats to retry failures. Logs in review_eval/logs/.
cd /home/t-ydsonale/materials-hypothesis-generation
export MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
L=experiments/high_temperature_hea_qwen35b/review_eval/logs
( for i in 1 2 3; do ./.venv/bin/python review_measurement.py controls-judge --workers 6; done ) >> $L/controls.log 2>&1 &
( for i in 1 2 3; do ./.venv/bin/python review_measurement.py key-audit --workers 3; done ) >> $L/key_audit.log 2>&1 &
( for i in 1 2 3; do ./.venv/bin/python review_measurement.py triage --workers 3; done ) >> $L/triage.log 2>&1 &
( for i in 1 2 3; do ./.venv/bin/python checklist_judge.py facts --workers 4; done
  for t in controls runs retest; do
    for i in 1 2 3; do ./.venv/bin/python checklist_judge.py score --target $t --workers 8; done
  done ) >> $L/checklist.log 2>&1 &
wait
echo "PHASE_A_API_DONE $(date -Is)" >> $L/checklist.log
