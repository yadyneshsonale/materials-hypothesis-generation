#!/bin/bash
# Experiment 38 (loop.md 19.1): synthesis configurations on the 45 spent papers (all36 + test4, 3 levels x 2 samples).
# Generation, then GPT-5.6 judge, target-free audit and lever labels (judge, audit and label loops on both TRAPI
# instances, each in its own seeded random job order so that loops rarely meet; an output another loop wrote is
# skipped), the DeepSeek cross-judge, the draft class labels and the report.
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
P=$E/loop_r4
L=$P/logs
mkdir -p "$L"
export MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
SHARED=https://trapi.research.microsoft.com/gcr/shared
ALT=https://trapi.research.microsoft.com/redmond/interactive
M="synth_k4_b_o3mini synth_crowd_b_o3mini synth_mixed_b_o3mini synth_k1_b_o3mini writer_only_b_o3mini_r5"
export P L

pending() {  # pending <output folder>: successful loop_r4 runs without it
  MATHG_LOOP_ROOT=$P ./.venv/bin/python -c "import hypo_loop as H; print(len(H._pending(None, '$1')))"
}

stage_loop() {  # stage_loop <stage> <output folder> <endpoint> <seed>
  local stage=$1 rel=$2 endpoint=$3 seed=$4
  local args=""; for m in $M; do args="$args --method $m"; done
  while true; do
    MATHG_PENDING_SHUFFLE=$seed TRAPI_ENDPOINT=$endpoint MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py $stage \
      $args --workers 8
    if [ -f "$L/gen38.done" ] && [ "$(pending $rel)" = 0 ]; then break; fi
    sleep 60
  done
}

echo "START $(date -Is) configurations=$(echo $M | wc -w)" >> "$L/gen38.done.log"
( printf '%s\n' $M | xargs -P 5 -I{} bash -c 'for i in 1 2; do for s in all36 test4; do
    MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py generate --method {} --split $s --workers 6; done; done \
    >> "$L/gen38.{}.log" 2>&1'
  echo "GEN_DONE $(date -Is)" > "$L/gen38.done" ) &
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
    if [ -f "$L/gen38.done" ] && [ "$(pending judgments/deepseek)" = 0 ]; then break; fi
    sleep 60
  done ) >> "$L/cross.log" 2>&1 &
wait
echo "EVALUATED $(date -Is)" >> "$L/gen38.done.log"
MATHG_LOOP_ROOT=$P ./.venv/bin/python round4_analysis.py drafts >> "$L/drafts.log" 2>&1
MATHG_LOOP_ROOT=$P ./.venv/bin/python round4_analysis.py report > "$L/report.log" 2>&1
echo "R4_ALL_DONE $(date -Is)" >> "$L/gen38.done.log"
