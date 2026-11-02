#!/bin/bash
# Experiment 45 (loop.md 26.1), GPT-5.6 (must_obey.md 6): the v1 judge, then the target-free audit, for every run.
# Waits until generation is done, so that the new arms and the rest of their bases (rx_base, rx_r) are judged in one
# shuffled order (must_obey.md 6.10); until then experiment 44's runner (tmux rx_gpt) keeps going, and is stopped here.
# Two loops of 3 workers, one per TRAPI instance (6 in total, must_obey.md 7), on the same seeded order from opposite
# ends: first the experiment-45 arms with their bases, then the rest of experiment 44, then the audits in that order.
# While an instance blocks the identity, one probe every 65 minutes.
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
P=$E/loop_rx
L=$P/logs
mkdir -p "$L"
export MATHG_REQUEST_TIMEOUT=600 MATHG_LOOP_ROOT=$P MATHG_PENDING_SHUFFLE=45
FIRST="edit_rx_base domain_rx_base domain_edit_rx_base rx_base edit_rx_r domain_rx_r domain_edit_rx_r rx_r"
REST="rx_u rx_c rx_ruc rx_ru rx_ruc_select"
args() { for m in $1; do printf -- "--method %s " "$m"; done; }
pending() {  # pending <rel> <methods>
  ./.venv/bin/python -c "
import sys, hypo_loop as H
print(len(H._pending(sys.argv[2].split(), sys.argv[1])))" "$1" "$2"
}
blocked() {
  MATHG_WORKLOAD_ID=mathg-exp45-gpt-probe ./.venv/bin/python -c "
import llm_client as lc
try:
    lc.judge_chat_json('Return JSON {\"ok\": true}.', '{}', max_tokens=200, retries=1)
except lc.TrapiBlocked:
    raise SystemExit(0)
except Exception:
    raise SystemExit(1)
raise SystemExit(1)"
}
run_loop() {  # run_loop <instance URL> <tag> <reverse: 0|1>
  export JUDGE_TRAPI_ENDPOINT=$1 TRAPI_ENDPOINT=$1 MATHG_TRAPI_LOG=$L/trapi_x45_gpt_$2.jsonl
  if [ "$3" = 1 ]; then export MATHG_PENDING_REVERSE=1; fi
  while true; do
    while blocked; do echo "blocked $2 $(date -Is)" >> "$L/x45_gpt.log"; sleep 3900; done
    MATHG_WORKLOAD_ID=mathg-exp45-gpt-judge-$2 ./.venv/bin/python hypo_loop.py judge $(args "$FIRST") --workers 3 \
      >> "$L/x45_gpt_judge_$2.log" 2>&1
    jf=$(pending judgments/gpt56 "$FIRST")
    if [ "$jf" = 0 ]; then
      MATHG_WORKLOAD_ID=mathg-exp44-gpt-judge-$2 ./.venv/bin/python hypo_loop.py judge $(args "$REST") --workers 3 \
        >> "$L/x45_gpt_judge_$2.log" 2>&1
    fi
    jr=$(pending judgments/gpt56 "$REST")
    if [ "$jf" = 0 ] && [ "$jr" = 0 ]; then
      MATHG_WORKLOAD_ID=mathg-exp45-gpt-audit-$2 ./.venv/bin/python hypo_loop.py audit $(args "$FIRST") --workers 3 \
        >> "$L/x45_gpt_audit_$2.log" 2>&1
      if [ "$(pending audit "$FIRST")" = 0 ]; then
        MATHG_WORKLOAD_ID=mathg-exp44-gpt-audit-$2 ./.venv/bin/python hypo_loop.py audit $(args "$REST") --workers 3 \
          >> "$L/x45_gpt_audit_$2.log" 2>&1
      fi
    fi
    af=$(pending audit "$FIRST"); ar=$(pending audit "$REST")
    echo "pass $2 $(date -Is) judge_first $jf judge_rest $jr audit_first $af audit_rest $ar" >> "$L/x45_gpt.log"
    if [ "$jf" = 0 ] && [ "$jr" = 0 ] && [ "$af" = 0 ] && [ "$ar" = 0 ]; then break; fi
    sleep 300
  done
  echo "X45_GPT_DONE $2 $(date -Is)" >> "$L/x45_gpt.log"
}
until grep -q "X45_GENERATE_DONE" "$L/x45_main.log" 2>/dev/null; do sleep 120; done
tmux kill-session -t rx_gpt 2>/dev/null && echo "rx_gpt stopped $(date -Is)" >> "$L/x45_gpt.log"
echo "X45_GPT_START $(date -Is)" >> "$L/x45_gpt.log"
run_loop https://trapi.research.microsoft.com/redmond/interactive ri 0 &
run_loop https://trapi.research.microsoft.com/gcr/shared gs 1 &
wait
