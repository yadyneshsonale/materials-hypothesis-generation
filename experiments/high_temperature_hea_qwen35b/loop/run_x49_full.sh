#!/bin/bash
# loop.md 28.3: perpaper_full (the perpaper method with full logging) on all 45 papers x 3 levels x sample 1, split over
# both TRAPI instances; MATHG_MAX_PER_DEPLOYMENT=6 caps o3-mini requests in flight per instance (must_obey.md 7).
cd /home/t-ydsonale/materials-hypothesis-generation
L=experiments/high_temperature_hea_qwen35b/loop_quality/logs
GS=https://trapi.research.microsoft.com/gcr/shared
RI=https://trapi.research.microsoft.com/redmond/interactive
export MATHG_REQUEST_TIMEOUT=600 MATHG_MAX_PER_DEPLOYMENT=6 MATHG_PERPAPER_WORKERS=4
G() {  # G <instance URL> <tag> <part>
  TRAPI_ENDPOINT=$1 MATHG_TRAPI_LOG=$L/trapi_x49full_$2.jsonl MATHG_WORKLOAD_ID=mathg-exp49full-$2 \
    ./.venv/bin/python perpaper_eval.py generate --arm perpaper_full --scope all45 --samples 1 --part $3 --parts 2 \
    --workers 3 >> "$L/x49full_$2.log" 2>&1
}
echo "X49FULL_START $(date -Is)" >> "$L/main.log"
for pass in 1 2; do G $GS gs 0 & G $RI ri 1 & wait; done
echo "X49FULL_DONE $(date -Is)" >> "$L/main.log"
