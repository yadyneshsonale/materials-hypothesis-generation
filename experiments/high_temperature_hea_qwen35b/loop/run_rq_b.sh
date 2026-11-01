#!/bin/bash
# Experiment 43, phase B (loop.md 24.1): RQ for the existing configurations and the reference (the authors' study
# written by the same writer). Each judge starts after its phase-A work (EXPERT_DONE), so that no model has more than
# 5 workers. No new generation.
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop_rq/logs
export MATHG_TRAPI_LOG=$L/trapi_responses.jsonl MATHG_REQUEST_TIMEOUT=600
METHODS="web_text_64k_b_o3mini web64k_v2_b_o3mini writer_study_b_o3mini closed_book closed_book_o3mini oracle_hint_full_b_o3mini"
for judge in deepseek o1; do
  (
    until grep -q "EXPERT_DONE $judge" "$L/phase_a.log" 2>/dev/null; do sleep 60; done
    for method in $METHODS; do
      for attempt in 1 2 3; do
        MATHG_WORKLOAD_ID=mathg-exp43-$judge-runs ./.venv/bin/python rq_judge.py runs --judge $judge \
          --method $method --workers 5 >> "$L/phase_b_$judge.log" 2>&1
      done
    done
    echo "PHASE_B_DONE $judge $(date -Is)" >> "$L/phase_b.log"
  ) &
done
wait
./.venv/bin/python rq_judge.py report > "$L/report_b.log" 2>&1
echo "PHASE_B_ALL_DONE $(date -Is)" >> "$L/phase_b.log"
