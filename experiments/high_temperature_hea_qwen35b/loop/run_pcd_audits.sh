#!/bin/bash
# Experiment 37: extra GPT-5.6 audit-only loops (one per TRAPI instance), started at 04:33 for the same reason as
# run_pcd_judges.sh: run_pcd.sh's loops alternate judge and audit passes, and neither instance was rate limiting.
# A run whose audit another loop already wrote is skipped. Restarted at 05:00 with MATHG_PENDING_SHUFFLE (a seeded
# random job order per loop): in the same order as run_pcd.sh's loops, each pair duplicated much of the other's work.
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
P=$E/loop_pcd
L=$P/logs
export MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
M="pcd_PCD_o3mini pcd_none_o3mini pcd_P_o3mini pcd_C_o3mini pcd_D_o3mini pcd_PC_o3mini pcd_PD_o3mini pcd_CD_o3mini
pcd_nocritic_PCD_o3mini pcd_nodecider_PCD_o3mini pcd_k1_PCD_o3mini pcd_nocritic_none_o3mini pcd_nodecider_none_o3mini
pcd_k1_none_o3mini pcd_PCD_llama pcd_none_llama"
audit_loop() {  # audit_loop <endpoint> <methods...>
  local endpoint=$1; shift
  local args=""; for m in "$@"; do args="$args --method $m"; done
  while true; do
    TRAPI_ENDPOINT=$endpoint MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py audit $args --workers 8
    left=$(MATHG_LOOP_ROOT=$P ./.venv/bin/python -c "import hypo_loop as H; print(len(H._pending(None, 'audit')))")
    if [ -f "$L/gen37.done" ] && [ "$left" = 0 ]; then break; fi
    sleep 30
  done
}
MATHG_PENDING_SHUFFLE=1 audit_loop https://trapi.research.microsoft.com/gcr/shared $M >> "$L/audit_shared.log" 2>&1 &
MATHG_PENDING_SHUFFLE=2 audit_loop https://trapi.research.microsoft.com/redmond/interactive $M >> "$L/audit_alt.log" 2>&1 &
wait
echo "AUDITS_DONE $(date -Is)" >> "$L/audit_alt.log"
