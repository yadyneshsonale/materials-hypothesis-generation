#!/bin/bash
# Experiment 48 (loop.md 27.7, addition of 01:37): the draft-then-ground agent of experiment 40 (agent_draft_ground_b_o3mini;
# existing runs, no generation) is scored like the synthesis writers: non-copying, and pairwise v2 against rx_r on DeepSeek
# and GPT-5.6. Starts when run_x48_par.sh has finished, so the per-instance limit of 6 workers holds (must_obey.md 7).
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop_quality/logs
GS=https://trapi.research.microsoft.com/gcr/shared
RI=https://trapi.research.microsoft.com/redmond/interactive
M=agent_draft_ground_b_o3mini
export MATHG_REQUEST_TIMEOUT=600
until grep -q "^X48_DONE" "$L/main.log" 2>/dev/null; do sleep 120; done
P() {  # P <url> <tag> <python statement>
  TRAPI_ENDPOINT=$1 JUDGE_TRAPI_ENDPOINT=$1 MATHG_TRAPI_LOG=$L/trapi_x48_$2.jsonl MATHG_WORKLOAD_ID=mathg-exp48-$2 \
    ./.venv/bin/python -c "import rx_experiment, noncopy_eval as N, quality_eval as Q; print($3)" >> "$L/x48_$2.log" 2>&1
}
PW="Q.pairwise_stage(['$M'], '%s', %d, 'rx_r', N.PAIR_SYSTEM_V2, N.PAIR_DIR)"
for pass in 1 2; do
  P $GS draft_nc "N.noncopy_stage(['$M'], 'deepseek', 6)" &
  P $RI draft_ds "$(printf "$PW" deepseek 6)" &
  P $RI draft_gpt_ri "$(printf "$PW" gpt56 3)" &
  MATHG_PENDING_REVERSE=1 P $GS draft_gpt_gs "$(printf "$PW" gpt56 3)" &
  wait
done
echo "X48_DRAFT_DONE $(date -Is)" >> "$L/main.log"
