#!/bin/bash
# Experiment 36 (loop.md 17.3): target-free audits (required, must_obey.md 6.3) on the second TRAPI instance, run
# alongside run_web_alt_eval.sh's judging so that the two overlap. Four workers; the same priority order; a run
# audited by the other loop meanwhile is skipped.
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
export MATHG_LOOP_ROOT=$E/loop_web MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
export TRAPI_ENDPOINT=https://trapi.research.microsoft.com/redmond/interactive
L=$MATHG_LOOP_ROOT/logs
ORDER="web_text_chunks web_text_chunks_b_o3mini web_agent_b_o3mini web_agent_o3mini web_agent"
ARGS=""; for m in $ORDER; do ARGS="$ARGS --method $m"; done
pending() {
  ./.venv/bin/python -c "import hypo_loop as H; print(len(H._pending(None, '$1')))"
}
until [ "$(pending audit)" = 0 ]; do
  ./.venv/bin/python hypo_loop.py audit $ARGS --workers 4  # Tier 1 first
  ./.venv/bin/python hypo_loop.py audit --workers 4
  sleep 60
done >> "$L/alt_audit36.log" 2>&1
echo "ALT_AUDIT_DONE $(date -Is)" >> "$L/alt_audit36.log"
