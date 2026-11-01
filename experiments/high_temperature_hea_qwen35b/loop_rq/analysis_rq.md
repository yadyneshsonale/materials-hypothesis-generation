# Experiment 43: research quality (RQ) on the expert's blind scales

Pre-registered in loop.md 24.1. RQ = mean of plausibility, testability and usefulness (1-5) minus 1, on 0-4; target-free and evidence-blind. Judges: o1 (primary; cannot know the papers) and DeepSeek. deepseek3 = the mean of three DeepSeek calls per item: a post-hoc amendment (loop.md 24.2), reported beside the pre-registered single-call views. RQ is not reconstruction.

## Validation (sanity controls of experiment 33; re-test on 135 writer runs)

- **o1** (1 call(s) per item): internally validated False (controls complete True); checks {"C1_relevance_usefulness_gap_ge_1": true, "C2_specificity_rq_gap_ge_1": true, "C3_consistency_plausibility_gaps_ge_0.5": false, "C4_retest_rho_ge_0.80": false}; gaps {"usefulness_positive_minus_random": 2.694, "rq_positive_minus_generic": 1.194, "plausibility_positive_minus_intervention_swap": 0.445, "plausibility_positive_minus_mechanism_swap": 0.695, "rq_positive_minus_hard_negative": 1.148}; re-test {"pairs": 135, "rho": 0.16, "spearman_brown_two_calls": 0.276, "mean_abs_diff": 0.198}
- **deepseek** (1 call(s) per item): internally validated False (controls complete True); checks {"C1_relevance_usefulness_gap_ge_1": true, "C2_specificity_rq_gap_ge_1": true, "C3_consistency_plausibility_gaps_ge_0.5": true, "C4_retest_rho_ge_0.80": false}; gaps {"usefulness_positive_minus_random": 1.361, "rq_positive_minus_generic": 1.009, "plausibility_positive_minus_intervention_swap": 0.639, "plausibility_positive_minus_mechanism_swap": 1.334, "rq_positive_minus_hard_negative": 0.972}; re-test {"pairs": 135, "rho": 0.637, "spearman_brown_two_calls": 0.778, "mean_abs_diff": 0.336}
- **deepseek3** (3 call(s) per item): internally validated True (controls complete True); checks {"C1_relevance_usefulness_gap_ge_1": true, "C2_specificity_rq_gap_ge_1": true, "C3_consistency_plausibility_gaps_ge_0.5": true, "C4_retest_rho_ge_0.80": true}; gaps {"usefulness_positive_minus_random": 1.454, "rq_positive_minus_generic": 1.118, "plausibility_positive_minus_intervention_swap": 0.676, "plausibility_positive_minus_mechanism_swap": 1.371, "rq_positive_minus_hard_negative": 1.056}; re-test {"pairs": 135, "rho": 0.817, "spearman_brown_two_calls": 0.899, "mean_abs_diff": 0.202}

| control | o1 RQ | deepseek RQ | deepseek3 RQ |
|---|---:|---:|---:|
| positive | 3.287 | 1.426 | 1.491 |
| hard_negative | 2.139 | 0.454 | 0.435 |
| random_negative | 1.889 | 0.296 | 0.262 |
| intervention_swap | 2.667 | 0.917 | 0.886 |
| mechanism_swap | 2.657 | 0.352 | 0.336 |
| generic | 2.093 | 0.417 | 0.373 |

## Expert-package items (the authors' study, the Llama baseline, the writer)

- **o1**: {"llama_baseline": {"n": 20, "rq": 3.167, "plausibility": 3.9, "testability": 4.55, "usefulness": 4.05}, "o3mini_writer": {"n": 20, "rq": 3.75, "plausibility": 4.35, "testability": 4.95, "usefulness": 4.95}, "reference": {"n": 20, "rq": 3.733, "plausibility": 4.3, "testability": 5.0, "usefulness": 4.9}}
- **deepseek**: {"llama_baseline": {"n": 20, "rq": 1.15, "plausibility": 2.1, "testability": 2.45, "usefulness": 1.9}, "o3mini_writer": {"n": 20, "rq": 3.067, "plausibility": 3.65, "testability": 4.1, "usefulness": 4.45}, "reference": {"n": 20, "rq": 2.983, "plausibility": 3.25, "testability": 4.4, "usefulness": 4.3}}
- **deepseek3**: {"llama_baseline": {"n": 20, "rq": 1.189, "plausibility": 2.15, "testability": 2.467, "usefulness": 1.95}, "o3mini_writer": {"n": 20, "rq": 3.111, "plausibility": 3.683, "testability": 4.2, "usefulness": 4.45}, "reference": {"n": 20, "rq": 3.111, "plausibility": 3.4, "testability": 4.467, "usefulness": 4.467}}

## Configurations (per-paper means, 95% CI; target 2.5)

| configuration | o1 RQ [CI] | deepseek RQ [CI] | deepseek3 RQ [CI] | o1 plaus/test/use | deepseek plaus/test/use | deepseek3 plaus/test/use | words | ≥ 2.5 (o1) |
|---|---|---|---|---|---|---|---|---|
| writer_only_b_o3mini | 3.691 [3.65, 3.73] | 3.091 [3.00, 3.18] | 3.102 [3.00, 3.20] | 4.341/4.944/4.789 | 3.696/4.144/4.433 | 3.714/4.163/4.428 | 487.7 | 1.0 |
| web_text_64k_b_o3mini | incomplete (150 of 270) | 3.017 [2.92, 3.12] | 3.026 [2.93, 3.13] | 4.333/4.973/4.84 | 3.548/4.104/4.4 | 3.56/4.152/4.367 | 525.1 | 1.0 |
| web64k_v2_b_o3mini | - | 3.072 [2.97, 3.17] | 3.062 [2.97, 3.15] | None/None/None | 3.615/4.278/4.322 | 3.616/4.272/4.299 | 530.4 | None |
| writer_study_b_o3mini | - | 3.091 [2.99, 3.19] | 3.131 [3.04, 3.22] | None/None/None | 3.685/4.219/4.37 | 3.707/4.254/4.432 | 529.2 | None |
| closed_book | - | 1.363 [1.22, 1.51] | 1.399 [1.26, 1.54] | None/None/None | 2.333/2.578/2.178 | 2.348/2.643/2.205 | 226.2 | None |
| closed_book_o3mini | - | 2.938 [2.84, 3.04] | 2.972 [2.88, 3.06] | None/None/None | 3.504/4.156/4.156 | 3.52/4.184/4.211 | 473.1 | None |
| oracle_hint_full_b_o3mini | - | 2.735 [2.55, 2.90] | 2.713 [2.53, 2.88] | None/None/None | 3.207/4.107/3.889 | 3.181/4.089/3.869 | 606.7 | None |

## Against the writer (paired per paper, Holm)

- deepseek: web_text_64k_b_o3mini − writer -0.074 [-0.18, +0.02] (19/25 papers, Holm p 1.0)
- deepseek: web64k_v2_b_o3mini − writer -0.020 [-0.12, +0.07] (22/23 papers, Holm p 1.0)
- deepseek: writer_study_b_o3mini − writer -0.000 [-0.09, +0.08] (22/22 papers, Holm p 1.0)
- deepseek: closed_book − writer -1.728 [-1.85, -1.60] (0/45 papers, Holm p 0.0)
- deepseek: closed_book_o3mini − writer -0.153 [-0.24, -0.07] (14/30 papers, Holm p 0.0904)
- deepseek3: web_text_64k_b_o3mini − writer -0.075 [-0.18, +0.03] (20/25 papers, Holm p 1.0)
- deepseek3: web64k_v2_b_o3mini − writer -0.040 [-0.14, +0.05] (21/24 papers, Holm p 1.0)
- deepseek3: writer_study_b_o3mini − writer +0.030 [-0.05, +0.11] (20/25 papers, Holm p 1.0)
- deepseek3: closed_book − writer -1.703 [-1.82, -1.58] (0/45 papers, Holm p 0.0)
- deepseek3: closed_book_o3mini − writer -0.130 [-0.21, -0.05] (14/31 papers, Holm p 0.0644)

Judge agreement (run level): {"o1_vs_deepseek": {"runs": 420, "spearman": 0.157}, "o1_vs_deepseek3": {"runs": 420, "spearman": 0.17}}

Convergence with the GPT-5.6 audits: {"o1": {"testability_vs_falsifiability": 0.057, "plausibility_vs_contradictions": -0.01, "runs": 420}, "deepseek": {"testability_vs_falsifiability": 0.23, "plausibility_vs_contradictions": -0.026, "runs": 1620}, "deepseek3": {"testability_vs_falsifiability": 0.245, "plausibility_vs_contradictions": -0.042, "runs": 1620}}
