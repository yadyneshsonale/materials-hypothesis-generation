#!/bin/bash
# Experiment 39 (loop.md 20.1): why more information does not raise the score. Generation of the 6 diagnostic
# configurations on the 45 spent papers (oracle_* are target-aware diagnostics, never methods), then GPT-5.6 judge,
# audit and lever labels on both TRAPI instances (each loop in its own seeded random job order; an output another
# loop wrote is skipped), the DeepSeek cross-judge, the pack and corpus labels, the target-free pairwise quality judge
# (GPT-5.6, DeepSeek, o1), the judge test-retest, the standard labels of web_text_64k_b_o3mini, and the report.
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
P=$E/loop_diag
L=$P/logs
mkdir -p "$L"
export MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
SHARED=https://trapi.research.microsoft.com/gcr/shared
ALT=https://trapi.research.microsoft.com/redmond/interactive
M="oracle_targetpack_b_o3mini oracle_targetpack_read_b_o3mini read_web_chunks_b_o3mini oracle_hint_class_b_o3mini
oracle_hint_lever_b_o3mini oracle_hint_full_b_o3mini"
export P L

pending() {  # pending <output folder>: successful loop_diag runs without it
  MATHG_LOOP_ROOT=$P ./.venv/bin/python -c "import hypo_loop as H; print(len(H._pending(None, '$1')))"
}

stage_loop() {  # stage_loop <stage> <output folder> <endpoint> <seed>
  local stage=$1 rel=$2 endpoint=$3 seed=$4
  local args=""; for m in $M; do args="$args --method $m"; done
  while true; do
    MATHG_PENDING_SHUFFLE=$seed TRAPI_ENDPOINT=$endpoint MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py $stage \
      $args --workers 6
    if [ -f "$L/gen39.done" ] && [ "$(pending $rel)" = 0 ]; then break; fi
    sleep 60
  done
}

repeat() {  # repeat <log> <command...>: up to 3 passes of a resumable stage
  local log=$1; shift
  for i in 1 2 3; do "$@" >> "$L/$log" 2>&1; done
}

echo "START $(date -Is)" >> "$L/gen39.done.log"
( printf '%s\n' $M | xargs -P 6 -I{} bash -c 'for i in 1 2; do for s in all36 test4; do
    MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py generate --method {} --split $s --workers 6; done; done \
    >> "$L/gen39.{}.log" 2>&1'
  echo "GEN_DONE $(date -Is)" > "$L/gen39.done" ) &
# Independent of the new runs: corpus labels, test-retest, the 64k pack's standard labels, the Q64 pairwise judge.
( repeat corpuslabels.log env TRAPI_ENDPOINT=$ALT ./.venv/bin/python diag_analysis.py corpuslabels --workers 6 ) &
( repeat retest.log env JUDGE_TRAPI_ENDPOINT=$ALT ./.venv/bin/python diag_analysis.py retest --workers 6 ) &
( for i in 1 2 3; do TRAPI_ENDPOINT=$SHARED MATHG_LOOP_ROOT=$E/loop_web ./.venv/bin/python hypo_loop.py label \
    --method web_text_64k_b_o3mini --workers 6; done >> "$L/labels64k.log" 2>&1 ) &
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
    if [ -f "$L/gen39.done" ] && [ "$(pending judgments/deepseek)" = 0 ]; then break; fi
    sleep 60
  done ) >> "$L/cross.log" 2>&1 &
# After generation: the pack labels (T16 needs its runs), classification of pack papers, the pairwise judges.
( while [ ! -f "$L/gen39.done" ]; do sleep 30; done
  repeat packlabels.log env TRAPI_ENDPOINT=$ALT ./.venv/bin/python diag_analysis.py packlabels --workers 6
  repeat classify.log ./.venv/bin/python diag_analysis.py classify --workers 16 ) &
( while [ ! -f "$L/gen39.done" ]; do sleep 30; done
  for judge in deepseek o1; do
    ( repeat pairwise_$judge.log env MATHG_PENDING_SHUFFLE=5 ./.venv/bin/python diag_analysis.py pairwise --judge $judge \
      --workers 8 ) &
  done
  repeat pairwise_gpt56.log env MATHG_PENDING_SHUFFLE=6 JUDGE_TRAPI_ENDPOINT=$SHARED ./.venv/bin/python \
    diag_analysis.py pairwise --judge gpt56 --workers 6
  wait ) &
wait
echo "EVALUATED $(date -Is)" >> "$L/gen39.done.log"
./.venv/bin/python diag_analysis.py report > "$L/report.log" 2>&1
echo "DIAG_ALL_DONE $(date -Is)" >> "$L/gen39.done.log"
