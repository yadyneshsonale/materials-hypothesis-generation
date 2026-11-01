#!/bin/bash
# Experiment 43, amendment 24.2: DeepSeek-3. Two more independent DeepSeek calls for every phase-A and phase-B item,
# and two more re-test calls for the 135 re-test items, so that the re-test of the three-call mean is measured.
# Starts after DeepSeek's phase B (PHASE_B_DONE deepseek), so that DeepSeek never has more than 5 workers.
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop_rq/logs
export MATHG_TRAPI_LOG=$L/trapi_responses.jsonl MATHG_REQUEST_TIMEOUT=600
until grep -q "PHASE_B_DONE deepseek" "$L/phase_b.log" 2>/dev/null; do sleep 60; done
METHODS="--method writer_only_b_o3mini --method web_text_64k_b_o3mini --method web64k_v2_b_o3mini --method writer_study_b_o3mini --method closed_book --method closed_book_o3mini --method oracle_hint_full_b_o3mini"
for rep in 2 3; do
  for stage in controls expert retest "runs $METHODS"; do
    for attempt in 1 2 3; do
      MATHG_WORKLOAD_ID=mathg-exp43-deepseek-rep$rep ./.venv/bin/python rq_judge.py $stage --judge deepseek \
        --rep $rep --workers 5 >> "$L/reps_deepseek.log" 2>&1
    done
  done
done
echo "REPS_DONE deepseek $(date -Is)" >> "$L/phase_b.log"
