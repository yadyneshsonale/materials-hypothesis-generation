#!/bin/bash
# Experiment 37: the pre-registered Q6 labels (loop.md 18.1), started at about 05:35 while the last audits ran.
# run_pcd.sh makes the same labels after its evaluation loops end: standard lever labels on the second instance and
# idea labels on the shared one, in the default job order. These loops use the other instance for each label type and
# a seeded random job order; a label another loop already wrote is skipped. What is labelled, and how, is unchanged.
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
P=$E/loop_pcd
L=$P/logs
export MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
SHARED=https://trapi.research.microsoft.com/gcr/shared
ALT=https://trapi.research.microsoft.com/redmond/interactive
Q6="--method pcd_PCD_o3mini --method pcd_none_o3mini"
( for i in 1 2; do
    MATHG_PENDING_SHUFFLE=3 TRAPI_ENDPOINT=$SHARED MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py label $Q6 \
      --workers 8
  done ) >> "$L/labels_extra.log" 2>&1 &
( for i in 1 2; do
    MATHG_PENDING_SHUFFLE=4 TRAPI_ENDPOINT=$ALT MATHG_LOOP_ROOT=$P ./.venv/bin/python pcd_analysis.py labels $Q6 \
      --workers 8
  done ) >> "$L/idea_labels_extra.log" 2>&1 &
wait
echo "LABELS_EXTRA_DONE $(date -Is)" >> "$L/labels_extra.log"
