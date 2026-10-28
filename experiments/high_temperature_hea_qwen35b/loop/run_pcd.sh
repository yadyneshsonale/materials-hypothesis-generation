#!/bin/bash
# Experiment 37 (loop.md 18.1-18.2): propose, critique, decide.
# - Generation: 16 configurations on the 45 papers (all36 + test4), 3 levels x 2 samples, in loop_pcd/; 12 at a time,
#   two passes (the second retries failures).
# - Baseline completions: closed_book_o3mini on test3 + test4 (loop/), web_text_64k_b_o3mini on test4 (loop_web/).
# - Evaluation from the start, as loop.md 17.3 learned: the GPT-5.6 judge and the target-free audit run on two TRAPI
#   instances of the same deployment, in opposite priority orders (a job written by the other loop is skipped); the
#   DeepSeek cross-judge runs on the shared instance. Then the Q6 lever labels and the report.
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
P=$E/loop_pcd
L=$P/logs
mkdir -p "$L"
export MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
SHARED=https://trapi.research.microsoft.com/gcr/shared
ALT=https://trapi.research.microsoft.com/redmond/interactive
M="pcd_PCD_o3mini pcd_none_o3mini pcd_P_o3mini pcd_C_o3mini pcd_D_o3mini pcd_PC_o3mini pcd_PD_o3mini pcd_CD_o3mini
pcd_nocritic_PCD_o3mini pcd_nodecider_PCD_o3mini pcd_k1_PCD_o3mini pcd_nocritic_none_o3mini pcd_nodecider_none_o3mini
pcd_k1_none_o3mini pcd_PCD_llama pcd_none_llama"
REVERSED=$(printf '%s\n' $M | tac | tr '\n' ' ')
export P L

pending() {  # pending <output folder>: successful loop_pcd runs without it
  MATHG_LOOP_ROOT=$P ./.venv/bin/python -c "import hypo_loop as H; print(len(H._pending(None, '$1')))"
}
export -f pending

evaluate() {  # evaluate <endpoint> <methods...>: GPT-5.6 judge and audit, in this priority order
  local endpoint=$1; shift
  local args=""; for m in "$@"; do args="$args --method $m"; done
  while true; do
    TRAPI_ENDPOINT=$endpoint MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py judge $args --workers 8
    TRAPI_ENDPOINT=$endpoint MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py audit $args --workers 8
    if [ -f "$L/gen37.done" ] && [ "$(pending judgments/gpt56)" = 0 ] && [ "$(pending audit)" = 0 ]; then break; fi
    sleep 60
  done
}

baselines() {  # complete two baselines on all 45 papers, with both judges and audits
  for i in 1 2; do
    MATHG_LOOP_ROOT=$E/loop ./.venv/bin/python hypo_loop.py generate --method closed_book_o3mini --split fresh37 --workers 4
    MATHG_LOOP_ROOT=$E/loop_web ./.venv/bin/python hypo_loop.py generate --method web_text_64k_b_o3mini --split test4 \
      --workers 4
  done
  for i in 1 2 3; do
    for pair in "loop closed_book_o3mini" "loop_web web_text_64k_b_o3mini"; do
      set -- $pair
      TRAPI_ENDPOINT=$ALT MATHG_LOOP_ROOT=$E/$1 ./.venv/bin/python hypo_loop.py judge --method $2 --workers 4
      MATHG_LOOP_ROOT=$E/$1 ./.venv/bin/python hypo_loop.py cross_judge --method $2 --workers 4
      TRAPI_ENDPOINT=$ALT MATHG_LOOP_ROOT=$E/$1 ./.venv/bin/python hypo_loop.py audit --method $2 --workers 4
    done
  done
  echo "BASELINES_DONE $(date -Is)"
}

echo "START $(date -Is) configurations=$(echo $M | wc -w)" >> "$L/gen37.done.log"
baselines >> "$L/baselines.log" 2>&1 &
( printf '%s\n' $M | xargs -P 12 -I{} bash -c 'for i in 1 2; do for s in all36 test4; do
    MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py generate --method {} --split $s --workers 3; done; done \
    >> "$L/gen37.{}.log" 2>&1'
  echo "GEN_DONE $(date -Is)" > "$L/gen37.done" ) &
sleep 300
evaluate $SHARED $M >> "$L/eval_shared.log" 2>&1 &
evaluate $ALT $REVERSED >> "$L/eval_alt.log" 2>&1 &
( args=""; for m in $M; do args="$args --method $m"; done
  while true; do
    MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py cross_judge $args --workers 8
    if [ -f "$L/gen37.done" ] && [ "$(pending judgments/deepseek)" = 0 ]; then break; fi
    sleep 60
  done ) >> "$L/cross.log" 2>&1 &
wait
echo "EVALUATED $(date -Is)" >> "$L/gen37.done.log"
# Q6: lever labels for the two configurations (standard labels on one instance, per-idea labels on the other).
( for i in 1 2; do TRAPI_ENDPOINT=$ALT MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py label --method pcd_PCD_o3mini \
    --method pcd_none_o3mini --workers 8; done ) >> "$L/labels.log" 2>&1 &
( for i in 1 2; do TRAPI_ENDPOINT=$SHARED MATHG_LOOP_ROOT=$P ./.venv/bin/python pcd_analysis.py labels --workers 8; done ) \
  >> "$L/idea_labels.log" 2>&1 &
wait
MATHG_LOOP_ROOT=$P ./.venv/bin/python pcd_analysis.py report > "$L/report.log" 2>&1
echo "PCD_ALL_DONE $(date -Is)" >> "$L/gen37.done.log"
