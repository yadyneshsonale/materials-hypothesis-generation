#!/bin/bash
# Experiment 44, GPT-5.6 (must_obey.md 6): v1 judgments, then target-free audits, for every run, at most 6 workers on
# one instance, the paced client; the key contrasts' arms first. While the identity is blocked, one probe every 65
# minutes. Passes repeat until generation is done and nothing is pending.
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
P=$E/loop_rx
L=$P/logs
INSTANCE=https://trapi.research.microsoft.com/redmond/interactive
export MATHG_REQUEST_TIMEOUT=600 JUDGE_TRAPI_ENDPOINT=$INSTANCE TRAPI_ENDPOINT=$INSTANCE MATHG_LOOP_ROOT=$P \
  MATHG_TRAPI_LOG=$L/trapi_gpt.jsonl
ARMS="--method rx_base --method rx_r --method rx_u --method rx_c --method rx_ruc --method rx_ru --method rx_ruc_select"
pending() {  # pending <rel>
  ./.venv/bin/python -c "
import sys, hypo_loop as H
print(len(H._pending(['rx_base','rx_r','rx_u','rx_c','rx_ruc','rx_ru','rx_ruc_select'], sys.argv[1])))" "$1"
}
blocked() {
  MATHG_WORKLOAD_ID=mathg-exp44-gpt-probe ./.venv/bin/python -c "
import llm_client as lc
try:
    lc.judge_chat_json('Return JSON {\"ok\": true}.', '{}', max_tokens=200, retries=1)
except lc.TrapiBlocked:
    raise SystemExit(0)
except Exception:
    raise SystemExit(1)
raise SystemExit(1)"
}
mkdir -p "$L"
echo "GPT_START $(date -Is)" >> "$L/gpt.log"
while true; do
  while blocked; do echo "blocked $(date -Is)" >> "$L/gpt.log"; sleep 3900; done
  MATHG_WORKLOAD_ID=mathg-exp44-gpt-judge ./.venv/bin/python hypo_loop.py judge $ARMS --workers 6 >> "$L/gpt_judge.log" 2>&1
  if [ "$(pending judgments/gpt56)" = 0 ]; then
    MATHG_WORKLOAD_ID=mathg-exp44-gpt-audit ./.venv/bin/python hypo_loop.py audit $ARMS --workers 6 >> "$L/gpt_audit.log" 2>&1
  fi
  done_gen=$(grep -c "GENERATE_DONE" "$L/main.log" 2>/dev/null)
  if [ "$done_gen" != 0 ] && [ "$(pending judgments/gpt56)" = 0 ] && [ "$(pending audit)" = 0 ]; then break; fi
  echo "pass $(date -Is) judge_pending $(pending judgments/gpt56) audit_pending $(pending audit)" >> "$L/gpt.log"
  sleep 600
done
echo "GPT_DONE $(date -Is)" >> "$L/gpt.log"
