#!/bin/bash
# Experiment 43, phase A: the 60 expert-package items, after run_rq_a.sh's expert stage failed (it read the runs
# from loop_rq; fixed in rq_judge.expert_entries). Each judge starts after its phase-A runner is done, so that no
# model has more than 5 workers.
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop_rq/logs
export MATHG_TRAPI_LOG=$L/trapi_responses.jsonl MATHG_REQUEST_TIMEOUT=600
for judge in deepseek o1; do
  (
    until grep -q "PHASE_A_DONE $judge" "$L/phase_a.log" 2>/dev/null; do sleep 60; done
    for attempt in 1 2 3; do
      MATHG_WORKLOAD_ID=mathg-exp43-$judge-expert ./.venv/bin/python rq_judge.py expert --judge $judge --workers 5 \
        >> "$L/phase_a_expert_$judge.log" 2>&1
    done
    echo "EXPERT_DONE $judge $(date -Is)" >> "$L/phase_a.log"
  ) &
done
wait
