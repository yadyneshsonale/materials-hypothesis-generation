#!/bin/bash
# Experiment 36 (loop.md 17.1): web search for every baseline. The 30 analysed evidence configurations are re-run as
# web_<name> with each question's web-search corpus in place of the fixed corpus, and three web-search agents are
# added. Tier 1 (the three agents, web_text_chunks, web_text_chunks_b_o3mini) runs on all 45 papers (all36 + test4);
# Tier 2 (the other 25) on all36. All papers are spent, so no run is a final (must_obey.md 6.5).
# Generation keeps 12 configurations running at a time, slowest first. Both judges run alongside it and catch up at
# the end; then target-free audits, then lever labels. Nothing starts before the corpus gate passes.
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
export MATHG_LOOP_ROOT=$E/loop_web MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
export L=$MATHG_LOOP_ROOT/logs
mkdir -p "$L"
until grep -q BUILD_DONE "$E/websearch/logs/build.log" 2>/dev/null; do sleep 60; done
./.venv/bin/python websearch.py gate > "$L/gate.log" 2>&1
if ./.venv/bin/python -c "import json,sys; sys.exit(0 if json.load(open('$E/websearch/gate.json'))['passed'] else 1)"; then
  echo "GATE_PASSED $(date -Is)" > "$E/websearch/logs/gate.status"
else
  echo "GATE_FAILED $(date -Is)" > "$E/websearch/logs/gate.status"
  echo "GATE_FAILED $(date -Is)" >> "$L/gen36.done"
  exit 1
fi
./.venv/bin/python websearch.py stats > "$L/stats.log" 2>&1
TIER1="web_agent web_agent_o3mini web_agent_b_o3mini web_text_chunks_b_o3mini web_text_chunks"
TIER2="web_scaffold_ensemble web_multi_decision_ground_o3mini web_scaffold_ensemble_o3mini web_niche_ground_b_o1
web_trend_ground_b_o1 web_trend_o1_ground_b_o3mini web_text_chunks_mbr_b_o3mini web_trend_ground_iter_b_o3mini
web_precedent_decide web_decide_then_ground web_trend_niche_ground_b_o3mini web_decide_then_ground_b web_trend_ground_b
web_decide_then_ground_b_o3mini web_trend_chain_o3mini web_trend_focus_ground_b_o3mini web_trend_ground_b_o3mini
web_trend_ground_bm25_b_o3mini web_decide_then_ground_v2_o3mini web_niche_ground_b_o3mini web_trend_chain
web_papers_n30_b_o3mini web_papers_random10_b_o3mini web_papers_n10_b_o3mini web_text_64k_b_o3mini
web_papers_n3_b_o3mini web_papers_n1_b_o3mini web_text_4k_b_o3mini"
ARGS=""; for m in $TIER1 $TIER2; do ARGS="$ARGS --method $m"; done
gen() {  # gen <method> <split>...
  local m=$1; shift
  for i in 1 2; do
    for s in "$@"; do ./.venv/bin/python hypo_loop.py generate --method "$m" --split "$s" --workers 3; done
  done >> "$L/gen36.$m.log" 2>&1
}
export -f gen
echo "START $(date -Is) configurations=$(echo $TIER1 $TIER2 | wc -w)" >> "$L/gen36.done"
( { for m in $TIER1; do echo "$m all36 test4"; done; for m in $TIER2; do echo "$m all36"; done; } \
    | xargs -P 12 -I{} bash -c 'gen {}'
  echo "GEN_DONE $(date -Is)" >> "$L/gen36.done" ) &
GEN=$!
( while kill -0 $GEN 2>/dev/null; do ./.venv/bin/python hypo_loop.py cross_judge $ARGS --workers 8; sleep 120; done
  for i in 1 2 3; do ./.venv/bin/python hypo_loop.py cross_judge $ARGS --workers 8; done ) >> "$L/cross36.log" 2>&1 &
( while kill -0 $GEN 2>/dev/null; do ./.venv/bin/python hypo_loop.py judge $ARGS --workers 10; sleep 120; done
  for i in 1 2 3; do ./.venv/bin/python hypo_loop.py judge $ARGS --workers 10; done ) >> "$L/judge36.log" 2>&1
wait
echo "JUDGED $(date -Is)" >> "$L/judge36.log"
for i in 1 2 3; do ./.venv/bin/python hypo_loop.py audit $ARGS --workers 10; done >> "$L/audit36.log" 2>&1
echo "AUDITED $(date -Is)" >> "$L/audit36.log"
for i in 1 2 3; do ./.venv/bin/python hypo_loop.py label $ARGS --workers 10; done >> "$L/label36.log" 2>&1
echo "WEB_ALL_DONE $(date -Is)" >> "$L/label36.log"
