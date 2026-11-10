#!/bin/bash
# Experiment 47 (loop.md 27.5), GPT-5.6 held out: pairwise v2 of rx_r vs the closed-book writer, both orders. Two loops of
# 3 workers, one per TRAPI instance, from opposite ends of one seeded order (6 in total, must_obey.md 7).
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop_quality/logs
mkdir -p "$L"
export MATHG_REQUEST_TIMEOUT=600 MATHG_PENDING_SHUFFLE=47
run_loop() {  # run_loop <instance URL> <tag> <reverse 0|1>
  export JUDGE_TRAPI_ENDPOINT=$1 TRAPI_ENDPOINT=$1 MATHG_TRAPI_LOG=$L/trapi_x47_gpt_$2.jsonl
  if [ "$3" = 1 ]; then export MATHG_PENDING_REVERSE=1; fi
  for pass in 1 2 3 4 5 6; do
    out=$(MATHG_WORKLOAD_ID=mathg-exp47-gpt-$2 ./.venv/bin/python noncopy_eval.py pairwise --judge gpt56 --workers 3 \
      2>>"$L/x47_gpt.log")
    echo "pass $2 $(date -Is) $out" >> "$L/x47_gpt.log"
    case "$out" in *"'jobs': 0"*) break;; esac
    sleep 300
  done
}
run_loop https://trapi.research.microsoft.com/redmond/interactive ri 0 &
run_loop https://trapi.research.microsoft.com/gcr/shared gs 1 &
wait
cd /home/t-ydsonale/materials-hypothesis-generation && ./.venv/bin/python noncopy_eval.py report > "$L/x47_report.log" 2>&1
echo "X47_GPT_DONE $(date -Is)" >> "$L/main.log"
