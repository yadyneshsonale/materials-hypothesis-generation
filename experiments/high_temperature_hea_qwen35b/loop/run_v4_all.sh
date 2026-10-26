#!/bin/bash
# Experiment 32 (loop.md section 15.1): every harness configuration re-run on benchmark v4 (SciMON-style input),
# all 36 papers, 2 samples, in the root loop_v4_scimon/. Experiment 31's four configurations are already there and are
# not re-run; nor are the replicates trend_ground_b_o3mini_r2 and writer_only_b_o3mini_r3.
# Generation keeps 12 configurations running at a time, heaviest first. The GPT-5.6 judge and the DeepSeek
# cross-judge run alongside it and catch up at the end; then target-free audits, then lever labels.
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
export MATHG_CASES_DIR=$E/benchmark_v4_scimon/cases MATHG_LEVELS=scimon MATHG_LOOP_ROOT=$E/loop_v4_scimon
export MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
export L=$MATHG_LOOP_ROOT/logs
mkdir -p "$L"
M="breadth_tournament family_scored coarse_to_fine scaffold_ensemble coarse_to_fine_o3mini
multi_decision_ground_o3mini scaffold_ensemble_o3mini niche_ground_b_o1 trend_ground_b_o1 trend_o1_ground_b_o3mini
writer_only_b_o1 frame_decide_verify decide_then_ground precedent_decide frame_decide trend_niche_ground_b_o3mini
text_chunks_mbr_b_o3mini writer_mbr_b_o3mini trend_ground_iter_b_o3mini decide_then_ground_b trend_ground_b
decide_then_ground_b_o3mini trend_chain_o3mini trend_focus_ground_b_o3mini trend_ground_b_o3mini
trend_ground_bm25_b_o3mini decide_then_ground_v2_o3mini niche_ground_b_o3mini analogy_writer_b_o3mini
frame_decide_b_o3mini trend_chain frame_decide_b papers_n30_b_o3mini writer_only papers_random10_b_o3mini
frame_decide_b_4omini papers_n10_b_o3mini text_64k_b_o3mini text_chunks writer_only_b_o3mini_high papers_n3_b_o3mini
papers_n1_b_o3mini text_4k_b_o3mini writer_only_b forecast_writer_b_o3mini writer_only_b_o3mini_low closed_book_4omini
writer_only_b_4omini"
ARGS=""; for m in $M; do ARGS="$ARGS --method $m"; done
echo "START $(date -Is) configurations=$(echo $M | wc -w)" >> "$L/gen32.done"
( printf '%s\n' $M | xargs -P 12 -I{} bash -c \
    'for i in 1 2; do ./.venv/bin/python hypo_loop.py generate --method {} --split all36 --workers 3; done >> "$L/gen32.{}.log" 2>&1'
  echo "GEN_DONE $(date -Is)" >> "$L/gen32.done" ) &
GEN=$!
( while kill -0 $GEN 2>/dev/null; do ./.venv/bin/python hypo_loop.py cross_judge $ARGS --workers 8; sleep 120; done
  for i in 1 2 3; do ./.venv/bin/python hypo_loop.py cross_judge $ARGS --workers 8; done ) >> "$L/cross32.log" 2>&1 &
( while kill -0 $GEN 2>/dev/null; do ./.venv/bin/python hypo_loop.py judge $ARGS --workers 10; sleep 120; done
  for i in 1 2 3; do ./.venv/bin/python hypo_loop.py judge $ARGS --workers 10; done ) >> "$L/judge32.log" 2>&1
wait
echo "JUDGED $(date -Is)" >> "$L/judge32.log"
for i in 1 2 3; do ./.venv/bin/python hypo_loop.py audit $ARGS --workers 10; done >> "$L/audit32.log" 2>&1
echo "AUDITED $(date -Is)" >> "$L/audit32.log"
for i in 1 2 3; do ./.venv/bin/python hypo_loop.py label $ARGS --workers 10; done >> "$L/label32.log" 2>&1
echo "V4_ALL_DONE $(date -Is)" >> "$L/label32.log"
