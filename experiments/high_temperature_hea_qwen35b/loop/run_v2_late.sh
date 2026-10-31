#!/bin/bash
# Experiment 42: the GPT-5.6 measurement-v2 and pairwise-quality jobs, paused at 07:33 so that the primary v1 judging
# and the same-session baselines finished first (GPT-5.6 throughput was about 29 calls a minute; loop.md 23.1
# operational note). They resume here once the v1 judgments of the new runs and the 540 baseline re-judgments exist.
# Nothing about what is judged, or how, changes.
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
P=$E/loop_v2
L=$P/logs
export MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
SHARED=https://trapi.research.microsoft.com/gcr/shared
ALT=https://trapi.research.microsoft.com/redmond/interactive
while true; do
  left=$(MATHG_LOOP_ROOT=$P ./.venv/bin/python -c "import hypo_loop as H; print(len(H._pending(None, 'judgments/gpt56')))")
  rejudged=$(find "$P/same_session" -name "PMC*.json" 2>/dev/null | wc -l)
  if [ "$left" = 0 ] && [ "$rejudged" -ge 540 ]; then break; fi
  sleep 60
done
echo "RESUMED $(date -Is)" >> "$L/late.log"
for i in 1 2 3 4 5 6; do MATHG_PENDING_SHUFFLE=81 JUDGE_TRAPI_ENDPOINT=$ALT ./.venv/bin/python v2_analysis.py judge2 \
  --judge gpt56 --workers 8; done >> "$L/judge2_gpt_alt_late.log" 2>&1 &
for i in 1 2 3 4 5 6; do MATHG_PENDING_SHUFFLE=82 JUDGE_TRAPI_ENDPOINT=$SHARED ./.venv/bin/python v2_analysis.py judge2 \
  --judge gpt56 --workers 4; done >> "$L/judge2_gpt_shared_late.log" 2>&1 &
for i in 1 2 3 4; do MATHG_PENDING_SHUFFLE=83 JUDGE_TRAPI_ENDPOINT=$ALT ./.venv/bin/python v2_analysis.py pairwise \
  --judge gpt56 --workers 6; done >> "$L/pairwise_gpt56_late.log" 2>&1 &
wait
./.venv/bin/python v2_analysis.py report > "$L/report_late.log" 2>&1
echo "LATE_DONE $(date -Is)" >> "$L/late.log"
