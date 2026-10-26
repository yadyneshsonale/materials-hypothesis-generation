# Experiment 32 (suite): the experiment-21 evaluations on the SciMON-style input

**Date.** 2026-10-26.
**Plan.** Pre-registered in [loop.md](../../../loop.md) section 15.1; results are in sections 15.2–15.5.

**Runners.**
- [run_v4_suite.sh](../../../run_v4_suite.sh);
- [run_v4_citegraph.sh](../../../run_v4_citegraph.sh), the citation-graph chain restarted after two fixes;
- [suite_extra_eval.py](../../../suite_extra_eval.py), the DeepSeek judge and audits for experiments 7, 9 and 11.

**Analysis.** [v4_all_analysis.py](../../../v4_all_analysis.py) writes `comparison/analysis.json` and
`comparison/tables.md`.

## What changed relative to experiment 21 ([rerun_v3](../rerun_v3/README.md))

| | Experiment 21 (`rerun_v3/`) | This rerun |
|---|---|---|
| User input | benchmark v3 (3 levels per paper) | benchmark v4, SciMON-style, one input per paper ([cases_original12](../benchmark_v4_scimon/cases_original12/)) |
| Papers | 12 | the same 12 |
| Generator | Llama-3.3-70B-Instruct | same |
| Citation graphs | built from the v3 problem-level question | built from the v4 input (`MATHG_GRAPH_LEVEL=scimon`) |
| Extractor of new graph papers | local Qwen3.5-35B-A3B | Llama-3.3 (GPUs in use; must_obey.md 4.5 prefers pre-cutoff extractors); cached Qwen extractions reused |
| Judges | GPT-5.6; DeepSeek on experiments 14, 16, 17 | GPT-5.6 and DeepSeek on every run, plus target-free audits |
| Factorial (generator × queries) | yes | not re-run (it tested Qwen and the leaky experiment-3 queries) |

## Integrity

| Experiment | Runs ok / expected | GPT-5.6 | DeepSeek | Audits |
|---|---|---|---|---|
| 7 eval_v3 | 48/48 (plus 36 pairwise judgments) | 48 | 48 | 48 |
| 9 MatKG | 12/12 KG runs (plus 48 copied baselines; 48 pairwise judgments) | 60 | 60 | 60 |
| 11 critique | resample 12/12; revisions 24/24 | 36 | 36 | 36 |
| 14 rubrics | 192/192 | 192 | 192 | 192 |
| 16 improvements | 96/96 + 24 selections | 96 | 96 | 96 |
| 17 citation graph | 120/120 | 120 | 120 | 120 |

`must_obey_check.py --bench v4_scimon` passes on every run directory. The only warnings are the known one-month
margins for Llama-3.3.

## Citation graphs (experiment 17)

- **Different literature.** On average 1.0 of 10 seeds is shared with experiment 21's graphs.
- **Size.** 213 full-text papers in total (94 newly extracted by Llama-3.3). Per graph: 1,336 nodes, 24 full-text
  nodes and 857 citer statements; experiment 21's graphs had 1,259, 30 and 1,053.
- **Two fixes** (loop.md 15.2).
  1. Europe PMC never delivered one full text (HTTP 500 every time). It is now skipped as unavailable.
  2. Llama wrote the cited title instead of the marker label in most citer statements, so the parser rejected them.
     - `citegraph.marker_label` now maps copied titles back to labels. The 91 affected statement files were
       re-extracted, giving 30 statements per paper against Qwen's 37.
     - The first graphs and runs are kept in [citegraph_superseded/](./citegraph_superseded/README.md) and not
       analysed.

## Results (GPT-5.6, 12 papers)

- **v4 against v3.** No arm changes significantly (mean −0.05; 20 of 26 lower; smallest Holm p = 0.30). The
  citation-graph arms graph profiles (−0.12) and graph tool agent (−0.18) have CIs below zero.
- **Against the baselines.** No arm beats closed-book or raw text chunks on v4 with either judge, as on v3. The
  fixed closed-book prompt has the only CI above closed-book (+0.16 [+0.02, +0.31]), not significant after Holm.
- **Full table.** [comparison/tables.md](./comparison/tables.md).
