#!/bin/bash
# Experiment 40 (loop.md 21.1): the evidence-choosing agent and its 2 x 2 ablations on the 45 spent papers. Generation,
# then GPT-5.6 judge, audit and lever labels on both TRAPI instances (seeded random job orders; an output another loop
# wrote is skipped), the DeepSeek cross-judge, same-session GPT-5.6 re-judging of the baselines (must_obey.md 6.10),
# the target-free pairwise quality judges (GPT-5.6, DeepSeek, o1; must_obey.md 6.11), and the report.
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
P=$E/loop_agent
L=$P/logs
mkdir -p "$L"
export MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
SHARED=https://trapi.research.microsoft.com/gcr/shared
ALT=https://trapi.research.microsoft.com/redmond/interactive
M="agent_choose_ground_b_o3mini agent_choose_only_b_o3mini agent_draft_ground_b_o3mini"
export P L

pending() {  # pending <output folder>: successful loop_agent runs without it
  MATHG_LOOP_ROOT=$P ./.venv/bin/python -c "import hypo_loop as H; print(len(H._pending(None, '$1')))"
}

stage_loop() {  # stage_loop <stage> <output folder> <endpoint> <seed>
  local stage=$1 rel=$2 endpoint=$3 seed=$4
  local args=""; for m in $M; do args="$args --method $m"; done
  while true; do
    MATHG_PENDING_SHUFFLE=$seed TRAPI_ENDPOINT=$endpoint MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py $stage \
      $args --workers 6
    if [ -f "$L/gen40.done" ] && [ "$(pending $rel)" = 0 ]; then break; fi
    sleep 60
  done
}

repeat() {  # repeat <log> <command...>: up to 3 passes of a resumable stage
  local log=$1; shift
  for i in 1 2 3; do "$@" >> "$L/$log" 2>&1; done
}

echo "START $(date -Is)" >> "$L/gen40.done.log"
( printf '%s\n' $M | xargs -P 3 -I{} bash -c 'for i in 1 2; do for s in all36 test4; do
    MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py generate --method {} --split $s --workers 8; done; done \
    >> "$L/gen40.{}.log" 2>&1'
  echo "GEN_DONE $(date -Is)" > "$L/gen40.done" ) &
sleep 240
n=1
for endpoint in $SHARED $ALT; do
  stage_loop judge judgments/gpt56 $endpoint $n >> "$L/judge_$n.log" 2>&1 &
  stage_loop audit audit $endpoint $((n + 10)) >> "$L/audit_$n.log" 2>&1 &
  stage_loop label labels $endpoint $((n + 20)) >> "$L/label_$n.log" 2>&1 &
  n=$((n + 1))
done
( args=""; for m in $M; do args="$args --method $m"; done
  while true; do
    MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py cross_judge $args --workers 8
    if [ -f "$L/gen40.done" ] && [ "$(pending judgments/deepseek)" = 0 ]; then break; fi
    sleep 60
  done ) >> "$L/cross.log" 2>&1 &
# Same-session baselines, judged while the new runs are judged (must_obey.md 6.10).
( repeat rejudge_1.log env MATHG_PENDING_SHUFFLE=41 JUDGE_TRAPI_ENDPOINT=$ALT ./.venv/bin/python agent_analysis.py rejudge \
    --workers 6 ) &
( repeat rejudge_2.log env MATHG_PENDING_SHUFFLE=42 JUDGE_TRAPI_ENDPOINT=$SHARED ./.venv/bin/python agent_analysis.py \
    rejudge --workers 4 ) &
# After generation: the target-free pairwise quality judges.
( while [ ! -f "$L/gen40.done" ]; do sleep 30; done
  for judge in deepseek o1; do
    ( repeat pairwise_$judge.log env MATHG_PENDING_SHUFFLE=43 ./.venv/bin/python agent_analysis.py pairwise \
        --judge $judge --workers 8 ) &
  done
  repeat pairwise_gpt56.log env MATHG_PENDING_SHUFFLE=44 JUDGE_TRAPI_ENDPOINT=$ALT ./.venv/bin/python \
    agent_analysis.py pairwise --judge gpt56 --workers 6
  wait ) &
wait
echo "EVALUATED $(date -Is)" >> "$L/gen40.done.log"
./.venv/bin/python agent_analysis.py report > "$L/report.log" 2>&1
echo "AGENT_ALL_DONE $(date -Is)" >> "$L/gen40.done.log"
