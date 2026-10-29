#!/bin/bash
# Experiment 40: the target-free audits, restarted at 04:28 after the GPT-5.6 rate limiting eased (loop.md 21.1
# operational note). Two loops, one per TRAPI instance, each in its own seeded random job order; an audit another loop
# already wrote is skipped. The second instance joins when the pairwise judging there has finished.
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
P=$E/loop_agent
L=$P/logs
export MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
M="agent_choose_ground_b_o3mini agent_choose_only_b_o3mini agent_draft_ground_b_o3mini"
args=""; for m in $M; do args="$args --method $m"; done
audit_loop() {  # audit_loop <endpoint> <seed>
  for i in 1 2 3 4 5; do
    MATHG_PENDING_SHUFFLE=$2 TRAPI_ENDPOINT=$1 MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py audit $args --workers 6
  done
}
audit_loop https://trapi.research.microsoft.com/gcr/shared 51 >> "$L/audit_resumed_1.log" 2>&1 &
( while pgrep -f "agent_analysis.py pairwise" > /dev/null; do sleep 60; done
  audit_loop https://trapi.research.microsoft.com/redmond/interactive 52 ) >> "$L/audit_resumed_2.log" 2>&1 &
wait
echo "AUDITS_DONE $(date -Is)" >> "$L/audit_resumed_1.log"
