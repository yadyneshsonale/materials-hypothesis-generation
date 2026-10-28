#!/bin/bash
# Experiment 37: extra GPT-5.6 judge-only loops (one per TRAPI instance), started at 03:28 because run_pcd.sh's
# evaluation loops spent long passes on audits while judging waited; neither instance was rate limiting. A job whose
# judgment another loop already wrote is skipped.
cd /home/t-ydsonale/materials-hypothesis-generation
E=$PWD/experiments/high_temperature_hea_qwen35b
P=$E/loop_pcd
L=$P/logs
export MATHG_REQUEST_TIMEOUT=600 MATHG_MIN_RETRIES=20
M="pcd_PCD_o3mini pcd_none_o3mini pcd_P_o3mini pcd_C_o3mini pcd_D_o3mini pcd_PC_o3mini pcd_PD_o3mini pcd_CD_o3mini
pcd_nocritic_PCD_o3mini pcd_nodecider_PCD_o3mini pcd_k1_PCD_o3mini pcd_nocritic_none_o3mini pcd_nodecider_none_o3mini
pcd_k1_none_o3mini pcd_PCD_llama pcd_none_llama"
judge_loop() {  # judge_loop <endpoint> <methods...>
  local endpoint=$1; shift
  local args=""; for m in "$@"; do args="$args --method $m"; done
  while true; do
    TRAPI_ENDPOINT=$endpoint MATHG_LOOP_ROOT=$P ./.venv/bin/python hypo_loop.py judge $args --workers 8
    left=$(MATHG_LOOP_ROOT=$P ./.venv/bin/python -c "import hypo_loop as H; print(len(H._pending(None, 'judgments/gpt56')))")
    if [ -f "$L/gen37.done" ] && [ "$left" = 0 ]; then break; fi
    sleep 30
  done
}
judge_loop https://trapi.research.microsoft.com/gcr/shared $M >> "$L/judge_shared.log" 2>&1 &
judge_loop https://trapi.research.microsoft.com/redmond/interactive $(printf '%s\n' $M | tac) >> "$L/judge_alt.log" 2>&1 &
wait
echo "JUDGES_DONE $(date -Is)" >> "$L/judge_alt.log"
