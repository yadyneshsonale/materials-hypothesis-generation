#!/bin/bash
# Experiment 39: two extra audit-only loops, added at 23:50 because the audits lagged the judges (about 10 a minute).
# Each takes jobs in its own seeded random order; an audit another loop already wrote is skipped. What is audited, and
# how, is unchanged (as in experiments 37-38).
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
P=$E/loop_diag
L=$P/logs
export MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
M="oracle_targetpack_b_o3mini oracle_targetpack_read_b_o3mini read_web_chunks_b_o3mini oracle_hint_class_b_o3mini
oracle_hint_lever_b_o3mini oracle_hint_full_b_o3mini"
args=""; for m in $M; do args="$args --method $m"; done
n=31
for endpoint in https://trapi.research.microsoft.com/gcr/shared https://trapi.research.microsoft.com/redmond/interactive; do
  ( for i in 1 2 3; do MATHG_PENDING_SHUFFLE=$n TRAPI_ENDPOINT=$endpoint MATHG_LOOP_ROOT=$P ./.venv/bin/python \
      hypo_loop.py audit $args --workers 6; done ) >> "$L/audit_extra_$n.log" 2>&1 &
  n=$((n + 1))
done
wait
echo "EXTRA_AUDITS_DONE $(date -Is)" >> "$L/audit_extra_31.log"
