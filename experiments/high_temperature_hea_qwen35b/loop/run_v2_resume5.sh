#!/bin/bash
# Experiment 42: fifth resumption (loop.md 23.1, throughput notes). As run_v2_resume4.sh: one runner per TRAPI
# instance, 3 workers each (6 GPT-5.6 workers in total, must_obey.md 7). A stage written <stage>:rev takes its jobs in
# reverse order, so each runner also works on the other's primary stage from the other end once its own is done.
# Usage: run_v2_resume5.sh <instance> <tag> <stage>[:rev]...
# Paced client with its response log; while the identity is blocked, one probe every 65 minutes.
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
P=$E/loop_v2
L=$P/logs
INSTANCE=https://trapi.research.microsoft.com/$1
TAG=$2
shift 2
export MATHG_REQUEST_TIMEOUT=600 JUDGE_TRAPI_ENDPOINT=$INSTANCE TRAPI_ENDPOINT=$INSTANCE \
  MATHG_TRAPI_LOG=$L/trapi_responses.jsonl
ARGS="--method writer_v2_b_o3mini --method web64k_r2_b_o3mini --method web64k_v2_b_o3mini"
W=3

remaining() {  # remaining <stage>
  MATHG_LOOP_ROOT=$P ./.venv/bin/python - "$1" <<'PY'
import sys, hypo_loop as H, v2_analysis as VA
stage = sys.argv[1]
count = lambda pattern: len(list(VA.V2.glob(pattern)))
if stage in ("judge", "label", "audit"):
    print(len(H._pending(None, {"judge": "judgments/gpt56", "label": "labels", "audit": "audit"}[stage])))
elif stage == "rejudge":
    print(max(0, 540 - count("same_session/*/PMC*.json")))
elif stage == "packlabels":
    print(max(0, 135 - count("pack_labels/R2/*.json")))
elif stage == "pairwise":
    print(max(0, 540 - count("pairwise/best_vs_writer/gpt56/*.json")))
elif stage == "judge2":
    print(max(0, 2781 - count("judge_v2/*/*/gpt56/*.json")))
PY
}

blocked() {  # 0 if the identity is blocked (one call)
  MATHG_WORKLOAD_ID=mathg-exp42-$TAG-probe ./.venv/bin/python -c "
import llm_client as lc
try:
    lc.judge_chat_json('Return JSON {\"ok\": true}.', '{}', max_tokens=200, retries=1)
except lc.TrapiBlocked:
    raise SystemExit(0)
except Exception:
    raise SystemExit(1)
raise SystemExit(1)"
}

command_for() {  # command_for <stage>
  case $1 in
    judge|label|audit) echo "env MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py $1 $ARGS --workers $W" ;;
    pairwise) echo "./.venv/bin/python v2_analysis.py pairwise --judge gpt56 --workers $W" ;;
    judge2) echo "./.venv/bin/python v2_analysis.py judge2 --judge gpt56 --workers $W" ;;
    *) echo "./.venv/bin/python v2_analysis.py $1 --workers $W" ;;
  esac
}

echo "RESUME5_$TAG START $(date -Is) on $INSTANCE: $*" >> "$L/resume.log"
for item in "$@"; do
  stage=${item%:rev}
  reverse=""
  [ "$item" != "$stage" ] && reverse=1
  for attempt in 1 2 3 4 5 6 7 8; do
    [ "$(remaining $stage)" = 0 ] && break
    while blocked; do echo "blocked $(date -Is)" >> "$L/resume.log"; sleep 3900; done
    echo "$TAG $item attempt $attempt start $(date -Is) remaining $(remaining $stage)" >> "$L/resume.log"
    MATHG_PENDING_REVERSE=$reverse MATHG_WORKLOAD_ID=mathg-exp42-$TAG-$stage $(command_for $stage) \
      >> "$L/resume_$stage.log" 2>&1
  done
  echo "$TAG $item done $(date -Is) remaining $(remaining $stage)" >> "$L/resume.log"
done
echo "RESUME5_$TAG DONE $(date -Is)" >> "$L/resume.log"
