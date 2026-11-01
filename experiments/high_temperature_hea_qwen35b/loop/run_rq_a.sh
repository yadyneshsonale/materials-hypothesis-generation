#!/bin/bash
# Experiment 43, phase A (loop.md 24.1): the RQ instrument. Controls, expert items, the writer's runs (first
# judgments) and the re-test, for o1 and DeepSeek in parallel. At most 5 workers per model (must_obey.md 7), the
# paced client, a stable workload ID per stage; failed items are retried by re-running the stage (completed items
# are skipped).
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop_rq/logs
mkdir -p "$L"
export MATHG_TRAPI_LOG=$L/trapi_responses.jsonl MATHG_REQUEST_TIMEOUT=600
for judge in o1 deepseek; do
  (
    for stage in controls expert "runs --method writer_only_b_o3mini" retest; do
      for attempt in 1 2 3; do
        MATHG_WORKLOAD_ID=mathg-exp43-$judge-${stage%% *} ./.venv/bin/python rq_judge.py $stage --judge $judge \
          --workers 5 >> "$L/phase_a_$judge.log" 2>&1
      done
    done
    echo "PHASE_A_DONE $judge $(date -Is)" >> "$L/phase_a.log"
  ) &
done
wait
./.venv/bin/python rq_judge.py report > "$L/report_a.log" 2>&1
echo "PHASE_A_ALL_DONE $(date -Is)" >> "$L/phase_a.log"
