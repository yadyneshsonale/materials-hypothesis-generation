#!/bin/bash
# Experiment 48 (loop.md 27.7), parallel version (2026-11-10 01:20, at the user's request "parallelize as much as
# possible"; replaces run_x48.sh and run_x48_gpt.sh). Every stage starts at once and keeps re-running over the runs that
# exist (all stages are resumable and skip finished outputs), so scoring follows generation instead of waiting for it.
# At most 6 workers per model per TRAPI instance (must_obey.md 7, as amended 2026-11-10):
#   gen_a     o3-mini   gcr/shared            synth_a generation, 6 workers
#   gen_b     o3-mini   redmond/interactive   synth_b generation, 6 workers
#   ds_gs     DeepSeek  gcr/shared            non-copying, pairwise v2, pairwise v1, 6 workers
#   ds_ri     DeepSeek  redmond/interactive   RQ calls 1, 2, 3, 6 workers
#   gpt_ri/gs GPT-5.6   both instances        pairwise v2, 3 workers each
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop_quality/logs
mkdir -p "$L"
GS=https://trapi.research.microsoft.com/gcr/shared
RI=https://trapi.research.microsoft.com/redmond/interactive
export MATHG_REQUEST_TIMEOUT=600
S() {  # S <instance URL> <tag> <synth_eval arguments...>
  local url=$1 tag=$2; shift 2
  TRAPI_ENDPOINT=$url JUDGE_TRAPI_ENDPOINT=$url MATHG_TRAPI_LOG=$L/trapi_x48_$tag.jsonl MATHG_WORKLOAD_ID=mathg-exp48-$tag \
    ./.venv/bin/python synth_eval.py "$@" >> "$L/x48_$tag.log" 2>&1
}
generated() { grep -q "^X48_GEN_A_DONE" "$L/main.log" 2>/dev/null && grep -q "^X48_GEN_B_DONE" "$L/main.log" 2>/dev/null; }
gen() {  # gen <arm> <url> <tag> <marker>
  for pass in 1 2 3; do S "$2" "$3" generate --arm "$1" --workers 6; done
  echo "$4 $(date -Is)" >> "$L/main.log"
}
follow() {  # follow <url> <tag> <stage args...>: repeat while generation runs, then twice more
  local url=$1 tag=$2; shift 2
  while ! generated; do S "$url" "$tag" "$@"; sleep 60; done
  S "$url" "$tag" "$@"; S "$url" "$tag" "$@"
}
echo "X48_PAR_START $(date -Is)" >> "$L/main.log"
gen synth_a $GS gen_a X48_GEN_A_DONE &
gen synth_b $RI gen_b X48_GEN_B_DONE &
( follow $GS ds_gs noncopy --workers 6
  follow $GS ds_gs pairwise --judge deepseek --prompt v2 --workers 6
  follow $GS ds_gs pairwise --judge deepseek --prompt v1 --workers 6
  echo "X48_DS_GS_DONE $(date -Is)" >> "$L/main.log" ) &
( for rep in 1 2 3; do follow $RI ds_ri rq --rep $rep --workers 6; done
  echo "X48_DS_RI_DONE $(date -Is)" >> "$L/main.log" ) &
( export MATHG_PENDING_SHUFFLE=48; follow $RI gpt_ri pairwise --judge gpt56 --prompt v2 --workers 3 ) &
( export MATHG_PENDING_SHUFFLE=48 MATHG_PENDING_REVERSE=1; follow $GS gpt_gs pairwise --judge gpt56 --prompt v2 \
    --workers 3 ) &
wait
./.venv/bin/python synth_eval.py report > "$L/x48_report.log" 2>&1
echo "X48_DONE $(date -Is)" >> "$L/main.log"
