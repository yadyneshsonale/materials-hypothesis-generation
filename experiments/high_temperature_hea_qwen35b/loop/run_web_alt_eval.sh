#!/bin/bash
# Experiment 36 (loop.md 17.3): GPT-5.6 evaluations on a second TRAPI instance (redmond/interactive) of the same
# deployment (gpt-5.6-sol_2026-07-09), because the shared instance rate-limited nearly every call. Eight workers (four
# for the first hour). Configurations are taken in the opposite order to run_web.sh's; a job is skipped if another
# process has already written its output; every output records the instance.
# Phases: the GPT-5.6 judge for every run; then the target-free audits (also run alongside by run_web_alt_audit.sh);
# then lever labels for the primary comparison's configurations only (labels are not required by must_obey.md 6.3,
# and the second instance is saturated at about 27 calls a minute).
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
export MATHG_LOOP_ROOT=$E/loop_web MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
export TRAPI_ENDPOINT=https://trapi.research.microsoft.com/redmond/interactive
L=$MATHG_LOOP_ROOT/logs
ORDER="web_text_chunks web_text_chunks_b_o3mini web_agent_b_o3mini web_agent_o3mini web_agent
web_text_4k_b_o3mini web_papers_n1_b_o3mini web_papers_n3_b_o3mini web_text_64k_b_o3mini web_papers_n10_b_o3mini
web_papers_random10_b_o3mini web_papers_n30_b_o3mini web_trend_chain web_niche_ground_b_o3mini
web_decide_then_ground_v2_o3mini web_trend_ground_bm25_b_o3mini web_trend_ground_b_o3mini
web_trend_focus_ground_b_o3mini web_trend_chain_o3mini web_decide_then_ground_b_o3mini web_trend_ground_b
web_decide_then_ground_b web_trend_niche_ground_b_o3mini web_decide_then_ground web_precedent_decide
web_trend_ground_iter_b_o3mini web_text_chunks_mbr_b_o3mini web_trend_o1_ground_b_o3mini web_trend_ground_b_o1
web_niche_ground_b_o1 web_scaffold_ensemble_o3mini web_multi_decision_ground_o3mini web_scaffold_ensemble"
ARGS=""; for m in $ORDER; do ARGS="$ARGS --method $m"; done
TIER1="--method web_text_chunks --method web_text_chunks_b_o3mini --method web_agent_b_o3mini --method web_agent_o3mini --method web_agent"
pending() {  # pending <output folder>: successful runs without that output
  ./.venv/bin/python -c "import hypo_loop as H; print(len(H._pending(None, '$1')))"
}
{
  until [ "$(pending judgments/gpt56)" = 0 ]; do ./.venv/bin/python hypo_loop.py judge $ARGS --workers 8; sleep 30; done
  echo "JUDGE_DONE $(date -Is)"
  until [ "$(pending audit)" = 0 ]; do ./.venv/bin/python hypo_loop.py audit $ARGS --workers 8; sleep 30; done
  echo "AUDIT_DONE $(date -Is)"
  ./.venv/bin/python hypo_loop.py label $TIER1 --workers 8
  ./.venv/bin/python hypo_loop.py label $TIER1 --workers 8
} >> "$L/alt_eval36.log" 2>&1
echo "ALT_EVAL_DONE $(date -Is)" >> "$L/alt_eval36.log"
