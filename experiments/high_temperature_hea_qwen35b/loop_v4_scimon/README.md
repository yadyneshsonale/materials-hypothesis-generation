# loop_v4_scimon: harness runs on the SciMON-style input (experiments 31 and 32)

These are the harness runs on benchmark v4 ([../benchmark_v4_scimon/](../benchmark_v4_scimon/README.md)): one input
per paper (level `scimon`), all 36 papers, 2 samples each. The v3.1 runs in [../loop/](../loop/) are untouched.

- **Experiment 31** ([loop.md](../../../loop.md) section 14). Four pre-registered configurations, 288 runs:
  - `closed_book` (Llama-3.3 baseline);
  - `closed_book_o3mini`;
  - `writer_only_b_o3mini` (recommended configuration);
  - `text_chunks_b_o3mini`.
- **Experiment 32** (loop.md section 15). The other 48 harness configurations, 3,456 runs, so all 52 configurations
  of experiments 24, 26, 28 and 29 are here. The replicates `_r2` and `_r3` are not re-run. Total 3,744 runs, 0
  failed; one run failed once and its first attempt is in `text_chunks_mbr_b_o3mini/failed_attempts/`.

Each configuration folder contains:
- `runs/`: generations;
- `judgments/gpt56/` and `judgments/deepseek/`: the two judges;
- `audit/`: target-free audit;
- `labels/`: lever labels.

**Analysis files.**

| File | Content |
|---|---|
| `analysis.json` | Experiment 31: v4 vs v3.1 for its four configurations, exploratory breakdown, style |
| `analysis_all.json`, `analysis_all.md` | Experiment 32: all 52 configurations. v4 − v3.1 (H1), leaderboard and comparisons with the baselines (H2), rank agreement (H3), earlier conclusions re-tested (H4), unflagged and non-steering subsets (H5), leakage ρ (H6) |
| `report_all36.md` | The harness's standard table |

**Reproduce.**
1. Run [../loop/run_v4_scimon.sh](../loop/run_v4_scimon.sh) (experiment 31) and
   [../loop/run_v4_all.sh](../loop/run_v4_all.sh) (experiment 32). Both set `MATHG_CASES_DIR`, `MATHG_LEVELS=scimon`
   and `MATHG_LOOP_ROOT` to this folder. [../loop/run_v4_all_eval.sh](../loop/run_v4_all_eval.sh) ran audits and
   labels alongside generation.
2. Run `./.venv/bin/python v4_scimon_analysis.py` (experiment 31) and `./.venv/bin/python v4_all_analysis.py`
   (experiment 32).

**Result in one line.** With the SciMON-style input, no GPT-5.6 score changes significantly and DeepSeek scores are
lower. Configurations rank almost the same as on v3.1 (ρ 0.77), and nothing beats the recommended writer.
