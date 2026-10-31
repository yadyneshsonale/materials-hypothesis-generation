#!/bin/bash
# Experiment 42: second resumption after the TRAPI identity block (loop.md 23.1 incident notes). Replaces
# run_v2_resume.sh, whose probe every 5 minutes might have kept the block alive: TRAPI lifts a retry-flood block
# automatically after 60 minutes. No request before NOT_BEFORE (65 minutes after the last blocked request); while
# blocked, one probe every 65 minutes. At most 6 parallel GPT-5.6 workers in total (must_obey.md 7): one stage at a
# time, in priority order (the must_obey essentials first, measurement v2 last), each with a stable workload ID.
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
P=$E/loop_v2
L=$P/logs
ALT=https://trapi.research.microsoft.com/redmond/interactive
NOT_BEFORE="2026-10-30 10:50"
export MATHG_REQUEST_TIMEOUT=600 JUDGE_TRAPI_ENDPOINT=$ALT
ARGS="--method writer_v2_b_o3mini --method web64k_r2_b_o3mini --method web64k_v2_b_o3mini"

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
  MATHG_WORKLOAD_ID=mathg-exp42-probe ./.venv/bin/python -c "
import llm_client as lc
try:
    lc.judge_chat_json('Return JSON {\"ok\": true}.', '{}', max_tokens=200, retries=1)
except lc.TrapiBlocked:
    raise SystemExit(0)
except Exception:
    raise SystemExit(1)
raise SystemExit(1)"
}

wait_unblocked() {
  while blocked; do echo "blocked $(date -Is)" >> "$L/resume.log"; sleep 3900; done
}

run_stage() {  # run_stage <stage> <command...>
  local stage=$1; shift
  for attempt in 1 2 3 4 5 6 7 8; do
    [ "$(remaining $stage)" = 0 ] && break
    wait_unblocked
    echo "$stage attempt $attempt start $(date -Is) remaining $(remaining $stage)" >> "$L/resume.log"
    MATHG_WORKLOAD_ID=mathg-exp42-$stage "$@" >> "$L/resume_$stage.log" 2>&1
  done
  echo "$stage done $(date -Is) remaining $(remaining $stage)" >> "$L/resume.log"
}

echo "RESUME2_START $(date -Is); no request before $NOT_BEFORE" >> "$L/resume.log"
now=$(date +%s); target=$(date -d "$NOT_BEFORE" +%s)
[ "$now" -lt "$target" ] && sleep $((target - now))
run_stage judge env TRAPI_ENDPOINT=$ALT MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py judge $ARGS --workers 6
run_stage rejudge ./.venv/bin/python v2_analysis.py rejudge --workers 6
run_stage pairwise ./.venv/bin/python v2_analysis.py pairwise --judge gpt56 --workers 6
run_stage audit env TRAPI_ENDPOINT=$ALT MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py audit $ARGS --workers 6
run_stage packlabels ./.venv/bin/python v2_analysis.py packlabels --workers 6
./.venv/bin/python v2_analysis.py report > "$L/report_primary.log" 2>&1
run_stage label env TRAPI_ENDPOINT=$ALT MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py label $ARGS --workers 6
run_stage judge2 ./.venv/bin/python v2_analysis.py judge2 --judge gpt56 --workers 6
./.venv/bin/python v2_analysis.py report > "$L/report.log" 2>&1
echo "V2_ALL_DONE $(date -Is)" >> "$L/gen42.done.log"
