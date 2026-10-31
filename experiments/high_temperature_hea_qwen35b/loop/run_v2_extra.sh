#!/bin/bash
# Experiment 42: the primary v1 GPT-5.6 judging first (07:43). One extra judge loop on the faster TRAPI instance now;
# the lever labels, paused at 07:43, resume when every new run has its v1 judgment. Seeded random job orders; outputs
# another loop wrote are skipped. Nothing about what is judged or labelled, or how, changes.
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
P=$E/loop_v2
L=$P/logs
export MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
SHARED=https://trapi.research.microsoft.com/gcr/shared
ALT=https://trapi.research.microsoft.com/redmond/interactive
ARGS="--method writer_v2_b_o3mini --method web64k_r2_b_o3mini --method web64k_v2_b_o3mini"
pending() { MATHG_LOOP_ROOT=$P ./.venv/bin/python -c "import hypo_loop as H; print(len(H._pending(None, '$1')))"; }
for i in 1 2 3 4 5; do
  MATHG_PENDING_SHUFFLE=91 TRAPI_ENDPOINT=$ALT MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py judge $ARGS --workers 8
  [ "$(pending judgments/gpt56)" = 0 ] && break
done >> "$L/judge_extra.log" 2>&1
while [ "$(pending judgments/gpt56)" != 0 ]; do sleep 60; done
echo "LABELS_RESUMED $(date -Is)" >> "$L/judge_extra.log"
n=1
for endpoint in $SHARED $ALT; do
  ( for i in 1 2 3 4 5 6; do MATHG_PENDING_SHUFFLE=$((92 + n)) TRAPI_ENDPOINT=$endpoint MATHG_LOOP_ROOT=$P \
      ./.venv/bin/python hypo_loop.py label $ARGS --workers 6; [ "$(pending labels)" = 0 ] && break; done ) \
    >> "$L/label_late_$n.log" 2>&1 &
  n=$((n + 1))
done
wait
echo "LABELS_DONE $(date -Is)" >> "$L/judge_extra.log"
