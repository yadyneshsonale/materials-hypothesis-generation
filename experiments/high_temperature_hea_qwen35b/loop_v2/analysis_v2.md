# Experiment 42: stage changes from six reviews

Pre-registered in loop.md 23.1. Primary metric: the original judge (v1); GPT-5.6 baselines judged again in this session. Measurement v2 is secondary.

## Completeness (items on disk when this report was written; loop.md 23.1 finalisation notes)

- v1 GPT-5.6, new runs: {"writer_v2_b_o3mini": 270, "web64k_r2_b_o3mini": 270, "web64k_v2_b_o3mini": 270} of 270 each
- v1 DeepSeek, new runs: {"writer_v2_b_o3mini": 270, "web64k_r2_b_o3mini": 270, "web64k_v2_b_o3mini": 270} of 270 each
- same-session GPT-5.6 baselines: {"writer_only_b_o3mini": 270, "web_text_64k_b_o3mini": 270} of 270 each
- audits: {"writer_v2_b_o3mini": 0, "web64k_r2_b_o3mini": 0, "web64k_v2_b_o3mini": 4}; lever labels: {"writer_v2_b_o3mini": 106, "web64k_r2_b_o3mini": 88, "web64k_v2_b_o3mini": 86} (of 270 each)
- pack labels: 107 of 135; pairwise: {"gpt56": 85, "deepseek": 540, "o1": 540} of 540 each
- measurement v2: {"gpt56": {"runs": {"writer_v2_b_o3mini": 5, "web64k_r2_b_o3mini": 11, "web64k_v2_b_o3mini": 5, "writer_only_b_o3mini": 7, "web_text_64k_b_o3mini": 7, "closed_book_o3mini": 7, "closed_book": 7, "writer_study_b_o3mini": 7, "oracle_hint_lever_b_o3mini": 4}, "controls": 4, "retest": 3}, "deepseek": {"runs": {"writer_v2_b_o3mini": 270, "web64k_r2_b_o3mini": 270, "web64k_v2_b_o3mini": 270, "writer_only_b_o3mini": 270, "web_text_64k_b_o3mini": 270, "closed_book_o3mini": 270, "closed_book": 270, "writer_study_b_o3mini": 270, "oracle_hint_lever_b_o3mini": 270}, "controls": 216, "retest": 135}} (runs of 270 each; controls of 216; retest of 135)

## Q1 (primary, v1): the combined configuration

| comparison | GPT-5.6 [CI] | DeepSeek [CI] | decision |
|---|---|---|---|
| web64k_v2_b_o3mini vs writer_only_b_o3mini | -0.027 [-0.08, +0.02] (45 papers, 15/23, Holm p 0.5118) | -0.023 [-0.13, +0.08] (45 papers, 21/24, Holm p 0.766) | no detectable difference |
| web64k_v2_b_o3mini vs web_text_64k_b_o3mini | -0.009 [-0.05, +0.03] (45 papers, 20/20, Holm p 1.0) | -0.104 [-0.20, -0.02] (45 papers, 15/26, Holm p 0.2346) | no detectable difference |

## Q2 (v1): each stage

| comparison | GPT-5.6 [CI] | DeepSeek [CI] | decision |
|---|---|---|---|
| writer_v2_b_o3mini vs writer_only_b_o3mini | -0.056 [-0.11, -0.01] (45 papers, 15/26, Holm p 0.3519) | -0.069 [-0.13, -0.01] (45 papers, 14/25, Holm p 0.3243) | lowers the score |
| web64k_r2_b_o3mini vs web_text_64k_b_o3mini | +0.016 [-0.02, +0.06] (45 papers, 17/20, Holm p 0.7428) | -0.046 [-0.12, +0.02] (45 papers, 15/26, Holm p 0.3243) | no detectable difference |
| web64k_v2_b_o3mini vs web64k_r2_b_o3mini | -0.025 [-0.07, +0.02] (45 papers, 16/25, Holm p 0.422) | -0.057 [-0.14, +0.02] (45 papers, 14/25, Holm p 0.3243) | no detectable difference |

## Q1 (v1) without the three question-key mismatches (sensitivity)

| comparison | GPT-5.6 [CI] | DeepSeek [CI] | decision |
|---|---|---|---|
| web64k_v2_b_o3mini vs writer_only_b_o3mini | -0.029 [-0.08, +0.03] (42 papers, 14/22, Holm p 0.486) | -0.020 [-0.13, +0.09] (42 papers, 20/22, Holm p 0.8776) | no detectable difference |
| web64k_v2_b_o3mini vs web_text_64k_b_o3mini | -0.017 [-0.06, +0.03] (42 papers, 18/20, Holm p 0.8714) | -0.107 [-0.21, -0.01] (42 papers, 14/24, Holm p 0.2866) | no detectable difference |

## Q3: quality without the answer key (web64k_v2_b_o3mini vs the writer)

| judge | pairs | new wins | writer wins | net preference [CI] |
|---|---:|---:|---:|---|
| gpt56 | 16 | incomplete (16 of 270 pairs): not interpretable | | |
| deepseek | 270 | 0.352 | 0.026 | +0.326 [+0.25, +0.40] (45 papers, 39/2, Holm p 0.0) |
| o1 | 270 | 0.5 | 0.063 | +0.437 [+0.35, +0.53] (45 papers, 38/0, Holm p 0.0) |

## Q4: measurement v2 (anchored, evidence-blind)

- gpt56: incomplete (4 of 216 controls, 3 of 135 re-test items), so not evaluated; its numbers below are not interpretable
- deepseek: validated False; checks {"C1_auc_ge_0.90": true, "C2_positive_ge_3_and_random_le_1": true, "C3_swaps_hit_their_dimension": true, "C4_generic_2_below_positive": true, "C5_monotonic_partial_credit": true, "C6_retest_rho_ge_0.80": false}; intervention by lever label {"0": 0.131, "1": 0.248, "2": 0.764, "3": 1.589}; retest {"runs": 135, "rho": 0.751, "mean_abs_diff": 0.137}; controls means {"positive": 4.0, "hard_negative": 0.104, "random_negative": 0.0, "intervention_swap": 1.729, "mechanism_swap": 3.021, "generic": 0.09}, AUC 1.0

| configuration | v1 GPT-5.6 | v2 GPT-5.6 (incomplete) | v1 DeepSeek | v2 DeepSeek |
|---|---:|---:|---:|---:|
| writer_v2_b_o3mini | 0.591 | 0.6 | 0.506 | 0.331 |
| web64k_r2_b_o3mini | 0.644 | 0.583 | 0.609 | 0.381 |
| web64k_v2_b_o3mini | 0.619 | 0.45 | 0.552 | 0.357 |
| writer_only_b_o3mini | 0.646 | 0.893 | 0.575 | 0.37 |
| web_text_64k_b_o3mini | 0.629 | 1.071 | 0.656 | 0.403 |
| closed_book_o3mini | 0.591 | 0.786 | 0.503 | 0.353 |
| closed_book | 0.502 | 0.5 | 0.306 | 0.353 |
| writer_study_b_o3mini | 0.601 | 0.679 | 0.538 | 0.352 |
| oracle_hint_lever_b_o3mini | 1.26 | 1.312 | 1.502 | 0.953 |

Rank agreement v1 vs v2: {"gpt": "GPT-5.6 v2 incomplete", "deep": {"configurations": 9, "spearman_v1_v2": 0.862}}

## Q1 under measurement v2

| comparison | GPT-5.6 [CI] | DeepSeek [CI] | decision |
|---|---|---|---|
| web64k_v2_b_o3mini vs writer_only_b_o3mini | incomplete | -0.013 [-0.07, +0.05] (45 papers, 20/23, Holm p 0.7608) | no GPT-5.6 data |
| web64k_v2_b_o3mini vs web_text_64k_b_o3mini | incomplete | -0.045 [-0.11, +0.01] (45 papers, 15/22, Holm p 0.648) | no GPT-5.6 data |

## Q2 under measurement v2

| comparison | GPT-5.6 [CI] | DeepSeek [CI] | decision |
|---|---|---|---|
| writer_v2_b_o3mini vs writer_only_b_o3mini | incomplete | -0.039 [-0.08, +0.01] (45 papers, 13/25, Holm p 0.219) | no GPT-5.6 data |
| web64k_r2_b_o3mini vs web_text_64k_b_o3mini | incomplete | -0.021 [-0.08, +0.03] (45 papers, 21/17, Holm p 1.0) | no GPT-5.6 data |
| web64k_v2_b_o3mini vs web64k_r2_b_o3mini | incomplete | -0.024 [-0.08, +0.03] (45 papers, 19/24, Holm p 1.0) | no GPT-5.6 data |

## Diagnostics

| configuration | runs | lever ≥ 2 | intervention | conditions | mechanism | outcome | unsupported | invented numbers | citations filtered | calls | input chars |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| writer_v2_b_o3mini | 270 | 0.094 | 0.252 | 0.522 | 0.689 | 0.9 | 0.763 | 0.1 | 4 | 1.0 | 2690.844 |
| web64k_r2_b_o3mini | 270 | 0.125 | 0.296 | 0.637 | 0.733 | 0.911 | 0.478 | 0.57 | 56 | 1.0 | 72320.281 |
| web64k_v2_b_o3mini | 270 | 0.128 | 0.252 | 0.585 | 0.711 | 0.93 | 0.504 | 0.356 | 41 | 1.0 | 73192.281 |
| writer_only_b_o3mini | 270 | 0.189 | 0.315 | 0.578 | 0.748 | 0.852 | 0.726 | 0.47 | 0 | 1.03 | 1899.959 |
| web_text_64k_b_o3mini | 270 | 0.207 | 0.319 | 0.67 | 0.696 | 0.859 | 0.47 | 0.496 | 0 | 1.256 | 94561.144 |

Pack density: {"R2 (retrieval v2, 64,000 characters)": {"units": 107, "lever_passage_share": 0.169, "pack_contains_lever": 0.925}, "Q64 (question order, 64,000 characters)": {"units": 135, "lever_passage_share": 0.155, "pack_contains_lever": 0.933}}

Citation slips (repaired by filtering) and the v1 difference against web_text_64k by filter status: {"web64k_r2_b_o3mini": {"removed_ids": {"pack record, section suffix rewritten": 62, "pack paper, record not in pack": 27, "paper not in pack": 1}, "difference_vs_web_text_64k": {"gpt56": {"valid": {"runs": 214, "mean": 0.002}, "filtered, citations left": {"runs": 34, "mean": 0.066}, "filtered, none left": {"runs": 22, "mean": -0.023}}, "deepseek": {"valid": {"runs": 214, "mean": -0.062}, "filtered, citations left": {"runs": 34, "mean": 0.0}, "filtered, none left": {"runs": 22, "mean": 0.034}}}}, "web64k_v2_b_o3mini": {"removed_ids": {"pack record, section suffix rewritten": 32, "pack paper, record not in pack": 21}, "difference_vs_web_text_64k": {"gpt56": {"valid": {"runs": 229, "mean": -0.026}, "filtered, citations left": {"runs": 27, "mean": -0.037}, "filtered, none left": {"runs": 14, "mean": 0.179}}, "deepseek": {"valid": {"runs": 229, "mean": -0.107}, "filtered, citations left": {"runs": 27, "mean": -0.12}, "filtered, none left": {"runs": 14, "mean": -0.018}}}}}

Same-session baselines: {"writer_only_b_o3mini": {"same_session_gpt": 0.646, "original_gpt": 0.623}, "web_text_64k_b_o3mini": {"same_session_gpt": 0.629, "original_gpt": 0.636}}

## Leakage

Counters over 810 runs: {}; web records re-checked: 25036, date violations: 0.
