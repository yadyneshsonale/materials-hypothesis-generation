#!/bin/bash
# Experiment 42 (loop.md 23.1): stage changes from six reviews. Generation of the 3 configurations on the 45 spent
# papers; v1 GPT-5.6 judge and lever labels on both TRAPI instances (seeded random job orders; outputs another loop
# wrote are skipped); DeepSeek cross-judge; same-session v1 re-judging of the baselines; measurement v2 (both judges,
# all compared configurations, sanity controls, test-retest); pack labels of the retrieval-v2 packs; target-free
# pairwise quality; the report; then the audits, and the report again.
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
P=$E/loop_v2
L=$P/logs
mkdir -p "$L"
export MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
SHARED=https://trapi.research.microsoft.com/gcr/shared
ALT=https://trapi.research.microsoft.com/redmond/interactive
M="writer_v2_b_o3mini web64k_r2_b_o3mini web64k_v2_b_o3mini"
export P L

pending() {  # pending <output folder>: successful loop_v2 runs without it
  MATHG_LOOP_ROOT=$P ./.venv/bin/python -c "import hypo_loop as H; print(len(H._pending(None, '$1')))"
}

stage_loop() {  # stage_loop <stage> <output folder> <endpoint> <seed>
  local stage=$1 rel=$2 endpoint=$3 seed=$4
  local args=""; for m in $M; do args="$args --method $m"; done
  while true; do
    MATHG_PENDING_SHUFFLE=$seed TRAPI_ENDPOINT=$endpoint MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py $stage \
      $args --workers 6
    if [ -f "$L/gen42.done" ] && [ "$(pending $rel)" = 0 ]; then break; fi
    sleep 60
  done
}

repeat() {  # repeat <passes> <log> <command...>: passes of a resumable stage
  local n=$1 log=$2; shift 2
  for i in $(seq 1 $n); do "$@" >> "$L/$log" 2>&1; done
}

echo "START $(date -Is)" >> "$L/gen42.done.log"
( printf '%s\n' $M | xargs -P 3 -I{} bash -c 'for i in 1 2; do for s in all36 test4; do
    MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py generate --method {} --split $s --workers 8; done; done \
    >> "$L/gen42.{}.log" 2>&1'
  echo "GEN_DONE $(date -Is)" > "$L/gen42.done" ) &
# Same-session v1 baselines start at once (they do not depend on the new runs).
( repeat 4 rejudge.log env MATHG_PENDING_SHUFFLE=71 JUDGE_TRAPI_ENDPOINT=$ALT ./.venv/bin/python v2_analysis.py rejudge \
    --workers 6 ) &
sleep 180
n=1
for endpoint in $SHARED $ALT; do
  stage_loop judge judgments/gpt56 $endpoint $n >> "$L/judge_$n.log" 2>&1 &
  stage_loop label labels $endpoint $((n + 20)) >> "$L/label_$n.log" 2>&1 &
  n=$((n + 1))
done
( args=""; for m in $M; do args="$args --method $m"; done
  while true; do
    MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py cross_judge $args --workers 8
    if [ -f "$L/gen42.done" ] && [ "$(pending judgments/deepseek)" = 0 ]; then break; fi
    sleep 60
  done ) >> "$L/cross.log" 2>&1 &
# After generation: measurement v2 (both judges), pack labels, pairwise quality.
( while [ ! -f "$L/gen42.done" ]; do sleep 30; done
  ( repeat 6 judge2_deepseek.log env MATHG_PENDING_SHUFFLE=72 ./.venv/bin/python v2_analysis.py judge2 --judge deepseek \
      --workers 10 ) &
  ( repeat 6 judge2_gpt_shared.log env MATHG_PENDING_SHUFFLE=73 JUDGE_TRAPI_ENDPOINT=$SHARED ./.venv/bin/python \
      v2_analysis.py judge2 --judge gpt56 --workers 5 ) &
  ( repeat 6 judge2_gpt_alt.log env MATHG_PENDING_SHUFFLE=74 JUDGE_TRAPI_ENDPOINT=$ALT ./.venv/bin/python \
      v2_analysis.py judge2 --judge gpt56 --workers 5 ) &
  ( repeat 4 packlabels.log env TRAPI_ENDPOINT=$ALT ./.venv/bin/python v2_analysis.py packlabels --workers 6 ) &
  for judge in deepseek o1; do
    ( repeat 4 pairwise_$judge.log env MATHG_PENDING_SHUFFLE=75 ./.venv/bin/python v2_analysis.py pairwise \
        --judge $judge --workers 8 ) &
  done
  repeat 4 pairwise_gpt56.log env MATHG_PENDING_SHUFFLE=76 JUDGE_TRAPI_ENDPOINT=$ALT ./.venv/bin/python \
    v2_analysis.py pairwise --judge gpt56 --workers 5
  wait ) &
wait
echo "EVALUATED $(date -Is)" >> "$L/gen42.done.log"
./.venv/bin/python v2_analysis.py report > "$L/report.log" 2>&1
# The audits run last so that they do not compete with the judgments for the shared GPT-5.6 quota.
n=1
for endpoint in $SHARED $ALT; do
  stage_loop audit audit $endpoint $((n + 10)) >> "$L/audit_$n.log" 2>&1 &
  n=$((n + 1))
done
wait
./.venv/bin/python v2_analysis.py report > "$L/report.log" 2>&1
echo "V2_ALL_DONE $(date -Is)" >> "$L/gen42.done.log"
