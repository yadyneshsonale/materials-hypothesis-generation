#!/usr/bin/env bash
# 2x2 factorial for experiment 7 (eval_v3): {old leaky queries, new clean queries} x {Qwen3.5 (post-cutoff), Llama-3.3 (pre-cutoff)}.
# The two diagonal cells exist already (original eval_v3 and rerun_v3/eval_v3); this runs the off-diagonal cells.
set -uo pipefail
cd "/home/t-ydsonale/materials-hypothesis-generation"
PY=./.venv/bin/python
J="JUDGE_PROVIDER=trapi JUDGE_TRAPI_DEPLOYMENT=gpt-5.6-sol_2026-07-09"
( env $J MATHG_PROVIDER=trapi TRAPI_DEPLOYMENT=Llama-3.3-70B-Instruct_5 MATHG_TEMPERATURE=0.2 MATHG_REQUEST_TIMEOUT=600 \
    MATHG_CASES_DIR=/home/t-ydsonale/materials-hypothesis-generation/experiments/high_temperature_hea_qwen35b/temporal_v2/benchmark_cases \
    bash -c "for i in 1 2; do $PY temporal_eval_v3.py --output-dir /home/t-ydsonale/materials-hypothesis-generation/experiments/high_temperature_hea_qwen35b/rerun_v3/factorial/llama_oldq generate --workers 4 --resume; done; $PY temporal_eval_v3.py --output-dir /home/t-ydsonale/materials-hypothesis-generation/experiments/high_temperature_hea_qwen35b/rerun_v3/factorial/llama_oldq judge --workers 6 --resume; $PY temporal_eval_v3.py --output-dir /home/t-ydsonale/materials-hypothesis-generation/experiments/high_temperature_hea_qwen35b/rerun_v3/factorial/llama_oldq analyze" \
    > /home/t-ydsonale/materials-hypothesis-generation/experiments/high_temperature_hea_qwen35b/rerun_v3/logs/factorial_llama_oldq.log 2>&1 ) &
( env $J MATHG_PROVIDER=openai OPENAI_BASE_URL=http://127.0.0.1:8000/v1 OPENAI_API_KEY=local OPENAI_MODEL=Qwen3.5-35B-A3B-Q4_K_M.gguf \
    'OPENAI_CHAT_TEMPLATE_KWARGS={"enable_thinking":false}' MATHG_CONTEXT_WINDOW=32768 MATHG_REQUEST_TIMEOUT=900 \
    MATHG_CASES_DIR=/home/t-ydsonale/materials-hypothesis-generation/experiments/high_temperature_hea_qwen35b/benchmark_v3/cases \
    bash -c "for i in 1 2; do $PY temporal_eval_v3.py --output-dir /home/t-ydsonale/materials-hypothesis-generation/experiments/high_temperature_hea_qwen35b/rerun_v3/factorial/qwen_newq generate --workers 2 --resume; done; $PY temporal_eval_v3.py --output-dir /home/t-ydsonale/materials-hypothesis-generation/experiments/high_temperature_hea_qwen35b/rerun_v3/factorial/qwen_newq judge --workers 6 --resume; $PY temporal_eval_v3.py --output-dir /home/t-ydsonale/materials-hypothesis-generation/experiments/high_temperature_hea_qwen35b/rerun_v3/factorial/qwen_newq analyze" \
    > /home/t-ydsonale/materials-hypothesis-generation/experiments/high_temperature_hea_qwen35b/rerun_v3/logs/factorial_qwen_newq.log 2>&1 ) &
wait
touch /home/t-ydsonale/materials-hypothesis-generation/experiments/high_temperature_hea_qwen35b/rerun_v3/factorial/FINISHED
