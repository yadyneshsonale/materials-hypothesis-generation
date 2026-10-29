# Experiment 39: why more information does not raise the score

Pre-registered in loop.md 20.1. Oracle configurations use the answer key on purpose: diagnostics, not methods.

## Decisions (pre-registered rules)

- A_bad_information: **not supported**
- B_not_using_information: **supported**
- B_repeating_instead_of_reasoning: **not supported**
- C_unfair_to_information: **supported**
- C_little_credit_for_the_right_idea: **supported**

## A. Does the information contain the paper's lever?

| information | units | lever ≥ 2 (same lever) | lever ≥ 1 (same kind) |
|---|---:|---:|---:|
| question-retrieved 16,000 characters | 135 | 0.778 | 1.0 |
| question-retrieved 64,000 characters | 135 | 0.933 | 1.0 |
| oracle-selected 16,000 characters | 135 | 0.874 | 1.0 |
| whole web corpus (titles and abstracts) | 135 | 0.941 | 1.0 |

Pack identity across samples: {"Q16": {"units": 135, "identical": 135}, "Q64": {"units": 135, "identical": 135}, "T16": {"units": 135, "identical": 135}}

**A4. Oracle-selected vs question-retrieved evidence** (same retriever, corpus, budget and writer): GPT-5.6 0.739 vs 0.607, +0.131 [+0.07, +0.20] (45 papers, 29/12, Holm p 0.0115); DeepSeek 0.696 vs 0.61, +0.086 [-0.02, +0.19] (45 papers, 26/17, Holm p 0.2221).

## B. Does the model use the information?

**B1. Uptake** (lever ≥ 2 with the pack minus closed-book, same units)

| pack | group | runs | with pack | closed-book | uptake [CI] |
|---|---|---:|---:|---:|---|
| Q16 | pack_has_lever | 210 | 0.238 | 0.214 | +0.002 [-0.08, +0.07] (43 papers, None/None) |
| Q16 | pack_lacks_lever | 60 | 0.1 | 0.1 | -0.062 [-0.23, +0.07] (20 papers, None/None) |
| Q64 | pack_has_lever | 252 | 0.222 | 0.198 | +0.017 [-0.06, +0.09] (45 papers, None/None) |
| Q64 | pack_lacks_lever | 18 | 0.0 | 0.056 | -0.071 [-0.21, +0.00] (7 papers, None/None) |
| T16 | pack_has_lever | 236 | 0.267 | 0.182 | +0.093 [+0.03, +0.17] (42 papers, None/None) |
| T16 | pack_lacks_lever | 34 | 0.176 | 0.235 | -0.046 [-0.11, +0.00] (9 papers, None/None) |
| T16_read | pack_has_lever | 236 | 0.246 | 0.182 | +0.063 [+0.00, +0.14] (42 papers, None/None) |
| T16_read | pack_lacks_lever | 34 | 0.147 | 0.235 | -0.065 [-0.16, +0.00] (9 papers, None/None) |
| Q16_read | pack_has_lever | 210 | 0.214 | 0.214 | -0.012 [-0.10, +0.08] (43 papers, None/None) |
| Q16_read | pack_lacks_lever | 60 | 0.1 | 0.1 | -0.025 [-0.17, +0.12] (20 papers, None/None) |

**B2. Copying** (share of the hypothesis's specific terms found in the evidence it saw; control: the closed-book hypothesis against the same evidence)

| pack | term | runs | with evidence | control | difference [CI] |
|---|---|---:|---:|---:|---|
| Q16 | formulas | 32 | 0.516 | 0.312 | +0.265 [+0.05, +0.50] (13 papers, None/None) |
| Q16 | numbers | 112 | 0.458 | 0.185 | +0.271 [+0.15, +0.40] (38 papers, None/None) |
| Q16 | words | 270 | 0.468 | 0.4 | +0.068 [+0.06, +0.08] (45 papers, None/None) |
| Q64 | formulas | 28 | 0.688 | 0.536 | +0.218 [-0.03, +0.48] (13 papers, None/None) |
| Q64 | numbers | 114 | 0.654 | 0.455 | +0.245 [+0.12, +0.37] (37 papers, None/None) |
| Q64 | words | 270 | 0.706 | 0.654 | +0.053 [+0.04, +0.06] (45 papers, None/None) |
| T16 | formulas | 40 | 0.694 | 0.35 | +0.484 [+0.26, +0.70] (16 papers, None/None) |
| T16 | numbers | 115 | 0.579 | 0.232 | +0.374 [+0.26, +0.50] (35 papers, None/None) |
| T16 | words | 270 | 0.5 | 0.403 | +0.097 [+0.08, +0.12] (45 papers, None/None) |

**Study-type anchoring** (the hypothesis has the pack papers' modal study type)

| pack | runs | with pack | closed-book | difference [CI] |
|---|---:|---:|---:|---|
| Q16 | 270 | 0.389 | 0.322 | +0.067 [+0.00, +0.13] (45 papers, None/None) |
| Q64 | 270 | 0.374 | 0.33 | +0.044 [-0.01, +0.09] (45 papers, None/None) |
| T16 | 270 | 0.233 | 0.204 | +0.030 [-0.03, +0.09] (45 papers, None/None) |

**B3. Reading step**

| comparison | GPT-5.6 | DeepSeek |
|---|---|---|
| oracle_targetpack_read_b_o3mini vs oracle_targetpack_b_o3mini | -0.053 [-0.11, +0.01] (45 papers, 13/31, Holm p 0.0192) | -0.098 [-0.20, +0.01] (45 papers, 15/26, Holm p 0.1173) |
| read_web_chunks_b_o3mini vs web_text_chunks_b_o3mini | -0.037 [-0.07, +0.00] (45 papers, 15/24, Holm p 0.1996) | -0.118 [-0.19, -0.05] (45 papers, 14/28, Holm p 0.0872) |

## C. Is the judging fair?

**C1. Oracle hints** (vs the closed-book writer)

| hint | GPT-5.6 | difference [CI] | DeepSeek | difference [CI] | lever ≥ 2 |
|---|---:|---|---:|---|---:|
| oracle_hint_class_b_o3mini | 0.665 | +0.042 [-0.01, +0.10] (45 papers, 22/18, Holm p 0.6358) | 0.663 | +0.088 [+0.01, +0.16] (45 papers, 28/11, Holm p 0.0095) | 0.419 |
| oracle_hint_lever_b_o3mini | 1.26 | +0.637 [+0.53, +0.74] (45 papers, 42/2, Holm p 0.0) | 1.502 | +0.927 [+0.78, +1.07] (45 papers, 42/3, Holm p 0.0) | 0.926 |
| oracle_hint_full_b_o3mini | 3.382 | +2.759 [+2.56, +2.94] (45 papers, 45/0, Holm p 0.0) | 3.636 | +3.061 [+2.88, +3.23] (45 papers, 45/0, Holm p 0.0) | 0.933 |

**C2. Target-free quality judge** (pairwise, both orders; +1 when the information-rich hypothesis wins both orders, −1 when the closed-book one does)

| comparison | judge | pairs | info wins | closed-book wins | tie or inconsistent | first position wins | net preference for information [CI] |
|---|---|---:|---:|---:|---:|---:|---|
| Q64_vs_closed | gpt56 | 270 | 0.519 | 0.263 | 0.219 | 0.609 | +0.256 [+0.13, +0.39] (45 papers, 30/11, Holm p 0.0043) |
| Q64_vs_closed | deepseek | 270 | 0.337 | 0.044 | 0.619 | 0.809 | +0.293 [+0.20, +0.39] (45 papers, 33/6, Holm p 0.0) |
| Q64_vs_closed | o1 | 270 | 0.496 | 0.052 | 0.452 | 0.722 | +0.444 [+0.35, +0.53] (45 papers, 41/1, Holm p 0.0) |
| T16_vs_closed | gpt56 | 270 | 0.567 | 0.241 | 0.193 | 0.593 | +0.326 [+0.18, +0.47] (45 papers, 31/10, Holm p 0.003) |
| T16_vs_closed | deepseek | 270 | 0.363 | 0.033 | 0.604 | 0.802 | +0.330 [+0.24, +0.42] (45 papers, 32/3, Holm p 0.0) |
| T16_vs_closed | o1 | 270 | 0.496 | 0.063 | 0.441 | 0.715 | +0.433 [+0.34, +0.52] (45 papers, 38/4, Holm p 0.0) |

**C3. Along the amount of information** (existing runs; GPT-5.6 classification and dimensions)

| information | papers | GPT-5.6 | vs closed-book [CI] | DeepSeek | vs closed-book [CI] | unsupported | plausible alternative | partial or exact | evidence validity | novelty | intervention |
|---|---:|---:|---|---:|---|---:|---:|---:|---:|---:|---:|
| closed-book | 45 | 0.623 | - | 0.575 | - | 0.726 | 0.215 | 0.059 | 0.056 | 1.556 | 0.315 |
| text 4,000 | 36 | 0.5 | -0.115 [-0.18, -0.05] (36 papers, 8/26) | 0.506 | -0.086 [-0.18, +0.01] (36 papers, 13/20) | 0.579 | 0.389 | 0.032 | 0.972 | 1.769 | 0.213 |
| text 16,000 | 45 | 0.607 | -0.016 [-0.07, +0.04] (45 papers, 16/22) | 0.61 | +0.035 [-0.05, +0.12] (45 papers, 22/16) | 0.459 | 0.5 | 0.041 | 1.193 | 1.781 | 0.285 |
| text 64,000 | 45 | 0.636 | +0.013 [-0.05, +0.08] (45 papers, 20/19) | 0.656 | +0.081 [-0.02, +0.18] (45 papers, 27/15) | 0.47 | 0.474 | 0.056 | 1.096 | 1.796 | 0.319 |
| 1 paper | 36 | 0.495 | -0.119 [-0.19, -0.05] (36 papers, 11/23) | 0.493 | -0.098 [-0.21, +0.02] (36 papers, 12/19) | 0.63 | 0.333 | 0.037 | 0.944 | 1.833 | 0.241 |
| 3 papers | 36 | 0.525 | -0.089 [-0.15, -0.03] (36 papers, 10/24) | 0.564 | -0.028 [-0.14, +0.09] (36 papers, 16/18) | 0.588 | 0.384 | 0.028 | 1.065 | 1.856 | 0.236 |
| 10 papers | 36 | 0.574 | -0.041 [-0.10, +0.02] (36 papers, 11/20) | 0.692 | +0.101 [-0.01, +0.21] (36 papers, 21/10) | 0.519 | 0.44 | 0.042 | 1.171 | 1.782 | 0.292 |
| 30 papers | 36 | 0.59 | -0.024 [-0.07, +0.03] (36 papers, 15/17) | 0.662 | +0.071 [-0.02, +0.17] (36 papers, 18/13) | 0.421 | 0.537 | 0.042 | 1.176 | 1.769 | 0.301 |
| 10 random papers | 36 | 0.549 | -0.066 [-0.12, -0.01] (36 papers, 11/22) | 0.58 | -0.012 [-0.10, +0.08] (36 papers, 14/17) | 0.593 | 0.352 | 0.056 | 0.875 | 1.856 | 0.25 |

**C4. Test-retest:** {"gpt56": {"runs": 135, "rho_runs": 0.836, "mean_abs_diff_runs": 0.133, "identical_runs": 0.578, "first_mean": 0.624, "second_mean": 0.661, "rho_papers": 0.898, "papers": 45}, "deepseek": {"runs": 135, "rho_runs": 0.911, "mean_abs_diff_runs": 0.094, "identical_runs": 0.763, "first_mean": 0.576, "second_mean": 0.563, "rho_papers": 0.958, "papers": 45}}

## D. Post hoc: baselines re-judged in the same session (GPT-5.6)

Baseline means, original vs re-judged: {"web_text_chunks_b_o3mini": 0.607, "writer_only_b_o3mini": 0.623} vs {"web_text_chunks_b_o3mini": 0.6, "writer_only_b_o3mini": 0.639}

| comparison | GPT-5.6 difference [CI] |
|---|---|
| oracle_targetpack_b_o3mini vs web_text_chunks_b_o3mini (re-judged) | +0.139 [+0.08, +0.20] (45 papers, 33/11) |
| read_web_chunks_b_o3mini vs web_text_chunks_b_o3mini (re-judged) | -0.030 [-0.07, +0.01] (45 papers, 17/25) |
| oracle_hint_class_b_o3mini vs writer_only_b_o3mini (re-judged) | +0.026 [-0.03, +0.08] (45 papers, 20/15) |
| oracle_hint_lever_b_o3mini vs writer_only_b_o3mini (re-judged) | +0.621 [+0.52, +0.72] (45 papers, 42/3) |
| oracle_hint_full_b_o3mini vs writer_only_b_o3mini (re-judged) | +2.744 [+2.54, +2.92] (45 papers, 45/0) |

## Profiles

| configuration | runs | GPT-5.6 | DeepSeek | lever ≥ 2 | intervention | conditions | mechanism | outcome | novelty | unsupported |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| writer_only_b_o3mini | 270 | 0.623 | 0.575 | 0.189 | 0.315 | 0.578 | 0.748 | 0.852 | 1.556 | 0.726 |
| web_text_chunks_b_o3mini | 270 | 0.607 | 0.61 | 0.207 | 0.285 | 0.626 | 0.67 | 0.848 | 1.781 | 0.459 |
| web_text_64k_b_o3mini | 270 | 0.636 | 0.656 | 0.207 | 0.319 | 0.67 | 0.696 | 0.859 | 1.796 | 0.47 |
| oracle_targetpack_b_o3mini | 270 | 0.739 | 0.696 | 0.256 | 0.352 | 0.73 | 0.948 | 0.926 | 1.752 | 0.474 |
| oracle_targetpack_read_b_o3mini | 270 | 0.686 | 0.598 | 0.233 | 0.344 | 0.689 | 0.8 | 0.911 | 1.867 | 0.47 |
| read_web_chunks_b_o3mini | 270 | 0.57 | 0.493 | 0.189 | 0.226 | 0.585 | 0.633 | 0.837 | 1.859 | 0.504 |
| oracle_hint_class_b_o3mini | 270 | 0.665 | 0.663 | 0.419 | 0.474 | 0.63 | 0.726 | 0.83 | 1.419 | 0.733 |
| oracle_hint_lever_b_o3mini | 270 | 1.26 | 1.502 | 0.926 | 2.07 | 0.863 | 1.059 | 1.048 | 1.367 | 0.333 |
| oracle_hint_full_b_o3mini | 270 | 3.382 | 3.636 | 0.933 | 3.6 | 3.337 | 3.411 | 3.181 | 1.985 | 0.074 |

## Leakage

Counters over 1620 runs: {}; web records re-checked: 10986, date violations: 0, unresolved: 0.
