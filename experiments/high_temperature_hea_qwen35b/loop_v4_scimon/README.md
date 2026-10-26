# loop_v4_scimon: runs on the SciMON-style input (experiment 31)

These are the harness runs for [loop.md](../../../loop.md) section 14. The four pre-registered configurations were
run on benchmark v4 ([../benchmark_v4_scimon/](../benchmark_v4_scimon/README.md)) for all 36 papers, one input per
paper (level `scimon`), 2 samples each: 288 runs, 0 failed. The v3.1 runs in [../loop/](../loop/) are untouched.

| Folder | Configuration |
|---|---|
| `closed_book/` | Llama-3.3-70B baseline |
| `closed_book_o3mini/` | o3-mini, closed-book |
| `writer_only_b_o3mini/` | o3-mini with the conservative writer (recommended configuration) |
| `text_chunks_b_o3mini/` | o3-mini with question-retrieved text chunks |

Each configuration folder contains:
- `runs/`: generations;
- `judgments/gpt56/` and `judgments/deepseek/`: the two judges;
- `audit/`: target-free audit;
- `labels/`: lever labels.

`analysis.json` holds the pre-registered comparison with v3.1, the exploratory breakdown (labelled) and the style
check. `report_all36.md` is the harness's standard table.

**Reproduce.**
1. Run [../loop/run_v4_scimon.sh](../loop/run_v4_scimon.sh). It sets `MATHG_CASES_DIR`, `MATHG_LEVELS=scimon` and
   `MATHG_LOOP_ROOT` to this folder, then runs generate, judge, cross_judge, audit and label.
2. Run `./.venv/bin/python v4_scimon_analysis.py`.

**Result in one line.** The SciMON-style input changes no GPT-5.6 score significantly, and DeepSeek scores it lower.
The only significant gains are on inputs that steer toward the answer. The configuration ranking is unchanged.
