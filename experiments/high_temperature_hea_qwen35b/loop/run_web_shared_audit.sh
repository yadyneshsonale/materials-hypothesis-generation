#!/bin/bash
# Experiment 36 (loop.md 17.3): target-free audits on the shared TRAPI instance, once it served GPT-5.6 again
# (afternoon), alongside the second-instance loops. Configurations in the reverse of their order, so the loops rarely
# meet; a run audited by another loop meanwhile is skipped; every audit records its instance.
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
export MATHG_LOOP_ROOT=$E/loop_web MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
L=$MATHG_LOOP_ROOT/logs
ORDER="web_scaffold_ensemble web_multi_decision_ground_o3mini web_scaffold_ensemble_o3mini web_niche_ground_b_o1
web_trend_ground_b_o1 web_trend_o1_ground_b_o3mini web_text_chunks_mbr_b_o3mini web_trend_ground_iter_b_o3mini
web_precedent_decide web_decide_then_ground web_trend_niche_ground_b_o3mini web_decide_then_ground_b web_trend_ground_b
web_decide_then_ground_b_o3mini web_trend_chain_o3mini web_trend_focus_ground_b_o3mini web_trend_ground_b_o3mini
web_trend_ground_bm25_b_o3mini web_decide_then_ground_v2_o3mini web_niche_ground_b_o3mini web_trend_chain
web_papers_n30_b_o3mini web_papers_random10_b_o3mini web_papers_n10_b_o3mini web_text_64k_b_o3mini
web_papers_n3_b_o3mini web_papers_n1_b_o3mini web_text_4k_b_o3mini web_agent web_agent_o3mini web_agent_b_o3mini
web_text_chunks_b_o3mini web_text_chunks"
ARGS=""; for m in $ORDER; do ARGS="$ARGS --method $m"; done
pending() {
  ./.venv/bin/python -c "import hypo_loop as H; print(len(H._pending(None, '$1')))"
}
until [ "$(pending audit)" = 0 ]; do
  ./.venv/bin/python hypo_loop.py audit $ARGS --workers 8
  sleep 60
done >> "$L/shared_audit36.log" 2>&1
echo "SHARED_AUDIT_DONE $(date -Is)" >> "$L/shared_audit36.log"
