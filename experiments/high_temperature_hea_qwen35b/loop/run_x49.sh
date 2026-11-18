#!/bin/bash
# Experiment 49 pilot (loop.md 28.1): per-paper generate -> critique -> narrow on the 8 dev papers (48 runs), then the
# pre-registered evaluation. Generation is split over both TRAPI instances; MATHG_MAX_PER_DEPLOYMENT=6 caps o3-mini
# requests in flight per process, i.e. per instance (must_obey.md 7). Judges run after generation, each model at most
# 6 per instance.
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop_quality/logs
mkdir -p "$L"
GS=https://trapi.research.microsoft.com/gcr/shared
RI=https://trapi.research.microsoft.com/redmond/interactive
export MATHG_REQUEST_TIMEOUT=600 MATHG_MAX_PER_DEPLOYMENT=6 MATHG_PERPAPER_WORKERS=4
E() {  # E <instance URL> <tag> <perpaper_eval arguments...>
  local url=$1 tag=$2; shift 2
  TRAPI_ENDPOINT=$url JUDGE_TRAPI_ENDPOINT=$url MATHG_TRAPI_LOG=$L/trapi_x49_$tag.jsonl MATHG_WORKLOAD_ID=mathg-exp49-$tag \
    ./.venv/bin/python perpaper_eval.py "$@" >> "$L/x49_$tag.log" 2>&1
}
echo "X49_START $(date -Is)" >> "$L/main.log"
for pass in 1 2; do  # the second pass retries failed runs
  E $GS gen0 generate --part 0 --parts 2 --workers 3 &
  E $RI gen1 generate --part 1 --parts 2 --workers 3 &
  wait
done
echo "X49_GEN_DONE $(date -Is)" >> "$L/main.log"
( for rep in 1 2 3; do E $RI rq rq --rep $rep --workers 6; done
  E $RI o1 pairwise --judge o1 --base draft --workers 6
  E $RI o1 pairwise --judge o1 --base writer --workers 6 ) &
( E $GS ds noncopy --workers 6
  E $GS ds noncopy_source --workers 6
  E $GS ds pairwise --judge deepseek --base draft --workers 6
  E $GS ds pairwise --judge deepseek --base writer --workers 6 ) &
wait
./.venv/bin/python perpaper_eval.py report > "$L/x49_report.log" 2>&1
echo "X49_DONE $(date -Is)" >> "$L/main.log"
