#!/bin/bash
# Experiment 48 (loop.md 27.7), GPT-5.6 held out: pairwise v2 of synth_a and synth_b against rx_r, both orders, after
# generation. Two loops of 3 workers, one per TRAPI instance (6 in total, must_obey.md 7).
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop_quality/logs
mkdir -p "$L"
export MATHG_REQUEST_TIMEOUT=600 MATHG_PENDING_SHUFFLE=48
until grep -q "^X48_GENERATE_DONE" "$L/main.log" 2>/dev/null; do sleep 120; done
run_loop() {
  export JUDGE_TRAPI_ENDPOINT=$1 TRAPI_ENDPOINT=$1 MATHG_TRAPI_LOG=$L/trapi_x48_gpt_$2.jsonl
  if [ "$3" = 1 ]; then export MATHG_PENDING_REVERSE=1; fi
  for pass in 1 2 3 4 5 6; do
    out=$(MATHG_WORKLOAD_ID=mathg-exp48-gpt-$2 ./.venv/bin/python synth_eval.py pairwise --judge gpt56 --prompt v2 \
      --workers 3 2>>"$L/x48_gpt.log")
    echo "pass $2 $(date -Is) $out" >> "$L/x48_gpt.log"
    case "$out" in *"'jobs': 0"*) break;; esac
    sleep 300
  done
}
run_loop https://trapi.research.microsoft.com/redmond/interactive ri 0 &
run_loop https://trapi.research.microsoft.com/gcr/shared gs 1 &
wait
echo "X48_GPT_DONE $(date -Is)" >> "$L/main.log"
