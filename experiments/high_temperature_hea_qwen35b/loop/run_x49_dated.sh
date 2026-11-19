#!/bin/bash
# loop.md 28.4: perpaper_dated (the per-paper method with full log, dated teaching corpus).
# 1. all 45 papers x 3 levels x sample 1, then the 8 dev papers x 3 levels x sample 2, on both TRAPI instances;
# 2. the pilot evaluation of 28.1 on the 48 dev runs; 3. the hypotheses/ export.
# MATHG_MAX_PER_DEPLOYMENT=6 caps requests in flight per model per process, i.e. per instance (must_obey.md 7).
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop_quality/logs
GS=https://trapi.research.microsoft.com/gcr/shared
RI=https://trapi.research.microsoft.com/redmond/interactive
export MATHG_REQUEST_TIMEOUT=600 MATHG_MAX_PER_DEPLOYMENT=6 MATHG_PERPAPER_WORKERS=4
E() {  # E <instance URL> <tag> <perpaper_eval arguments...>
  local url=$1 tag=$2; shift 2
  TRAPI_ENDPOINT=$url JUDGE_TRAPI_ENDPOINT=$url MATHG_TRAPI_LOG=$L/trapi_x49d_$tag.jsonl MATHG_WORKLOAD_ID=mathg-exp49d-$tag \
    ./.venv/bin/python perpaper_eval.py "$@" --arm perpaper_dated >> "$L/x49d_$tag.log" 2>&1
}
echo "X49D_START $(date -Is)" >> "$L/main.log"
for pass in 1 2; do  # the second pass retries failed runs
  E $GS gs generate --scope all45 --samples 1 --part 0 --parts 2 --workers 3 &
  E $RI ri generate --scope all45 --samples 1 --part 1 --parts 2 --workers 3 &
  wait
  ./.venv/bin/python build_hypothesis_folder.py >> "$L/x49d_export.log" 2>&1
  E $GS gs generate --scope dev --samples 2 --part 0 --parts 2 --workers 3 &
  E $RI ri generate --scope dev --samples 2 --part 1 --parts 2 --workers 3 &
  wait
done
echo "X49D_GEN_DONE $(date -Is)" >> "$L/main.log"
( for rep in 1 2 3; do E $RI rq rq --rep $rep --workers 6; done
  E $RI o1 pairwise --judge o1 --base draft --workers 6
  E $RI o1 pairwise --judge o1 --base writer --workers 6 ) &
( E $GS ds noncopy --workers 6
  E $GS ds noncopy_source --workers 6
  E $GS ds pairwise --judge deepseek --base draft --workers 6
  E $GS ds pairwise --judge deepseek --base writer --workers 6 ) &
wait
./.venv/bin/python perpaper_eval.py report --arm perpaper_dated > "$L/x49d_report.log" 2>&1
./.venv/bin/python build_hypothesis_folder.py >> "$L/x49d_export.log" 2>&1
echo "X49D_DONE $(date -Is)" >> "$L/main.log"
