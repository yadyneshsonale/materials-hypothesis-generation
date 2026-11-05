#!/bin/bash
# Experiment 46 (loop.md 27.1), GPT-5.6 held out (must_obey.md 6.12): pairwise confirmation for the three
# configurations with the highest lower CI bound of DeepSeek's preference over the writer, after phase 1a and again
# after phase 1b. Two loops of 3 workers, one per TRAPI instance, from opposite ends of one seeded order (6 in total,
# must_obey.md 7). While an instance blocks the identity, one probe every 65 minutes.
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop_quality/logs
mkdir -p "$L"
export MATHG_REQUEST_TIMEOUT=600 MATHG_PENDING_SHUFFLE=46
args() { for m in "$@"; do printf -- "--method %s " "$m"; done; }
blocked() {
  MATHG_WORKLOAD_ID=mathg-exp46-gpt-probe ./.venv/bin/python -c "
import llm_client as lc
try:
    lc.judge_chat_json('Return JSON {\"ok\": true}.', '{}', max_tokens=200, retries=1)
except lc.TrapiBlocked:
    raise SystemExit(0)
except Exception:
    raise SystemExit(1)
raise SystemExit(1)"
}
confirm() {  # confirm <names...>: both instances until no job is left
  local names="$*"
  run_loop() {  # run_loop <instance URL> <tag> <reverse 0|1>
    export JUDGE_TRAPI_ENDPOINT=$1 TRAPI_ENDPOINT=$1 MATHG_TRAPI_LOG=$L/trapi_gpt_$2.jsonl
    if [ "$3" = 1 ]; then export MATHG_PENDING_REVERSE=1; fi
    for pass in 1 2 3 4 5 6; do
      while blocked; do echo "blocked $2 $(date -Is)" >> "$L/gpt.log"; sleep 3900; done
      out=$(MATHG_WORKLOAD_ID=mathg-exp46-gpt-$2 ./.venv/bin/python quality_eval.py pairwise --judge gpt56 \
        $(args $names) --workers 3 2>>"$L/gpt.log")
      echo "pass $2 $(date -Is) $out" >> "$L/gpt.log"
      case "$out" in *"'jobs': 0"*) break;; esac
      sleep 300
    done
  }
  run_loop https://trapi.research.microsoft.com/redmond/interactive ri 0 &
  run_loop https://trapi.research.microsoft.com/gcr/shared gs 1 &
  wait
}
until grep -q "^X46_A_PAIRWISE_DONE" "$L/main.log" 2>/dev/null; do sleep 300; done
F1=$(./.venv/bin/python quality_eval.py finalists --n 3 2>/dev/null)
echo "X46_GPT_FINALISTS_A $F1 $(date -Is)" >> "$L/main.log"
[ -n "$F1" ] && confirm $F1
echo "X46_GPT_A_DONE $(date -Is)" >> "$L/main.log"
until grep -q "^X46_B_PAIRWISE_DONE" "$L/main.log" 2>/dev/null; do sleep 600; done
F2=$(./.venv/bin/python quality_eval.py finalists --n 3 2>/dev/null)
echo "X46_GPT_FINALISTS_B $F2 $(date -Is)" >> "$L/main.log"
[ -n "$F2" ] && confirm $F2
echo "X46_GPT_DONE $(date -Is)" >> "$L/main.log"
