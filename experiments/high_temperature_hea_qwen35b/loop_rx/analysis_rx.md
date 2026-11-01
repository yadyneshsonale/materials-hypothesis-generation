# Experiment 44: focused retrieval, evidence use and a multi-critic refinement loop

Pre-registered in loop.md 25.1. Interim decision judge: DeepSeek reconstruction (GPT-5.6 in the background); research quality (RQ, mean of three DeepSeek calls) and DeepSeek target-free pairwise quality alongside.

## Arms

| arm | runs ok | failed | DeepSeek judged | GPT-5.6 judged | DeepSeek recon | GPT-5.6 recon | RQ (3 calls) | calls | input chars | seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rx_base | 270 | 0 | 270 | 44 | 0.63 | 0.646 | 3.051 | 1.0 | 72320.281 | 39.271 |
| rx_r | 270 | 0 | 270 | 43 | 0.662 | 0.646 | 3.034 | 1.0 | 71040.03 | 40.152 |
| rx_u | 270 | 0 | 270 | 42 | 0.569 | 0.655 | 2.974 | 2.015 | 154859.096 | 89.455 |
| rx_ru | 270 | 0 | 270 | 4 | 0.554 | 0.875 | 2.995 | 2.019 | 154160.026 | 90.754 |
| rx_c | 270 | 0 | 270 | 28 | 0.48 | 0.625 | 3.056 | 10.241 | 325755.096 | 246.729 |
| rx_ruc_select | 270 | 0 | 270 | 0 | 0.447 | None | 2.863 | 5.0 | 174843.422 | 155.824 |
| rx_ruc | 270 | 0 | 270 | 26 | 0.402 | 0.587 | 2.977 | 13.881 | 441389.907 | 311.397 |

Reference: writer_only_b_o3mini DeepSeek 0.575, RQ 3.102.

## DeepSeek reconstruction (interim decision)

| comparison | difference [CI] |
|---|---|
| rx_r vs rx_base | +0.032 [-0.05, +0.11] (45 papers, 19/20, Holm p 1.0) |
| rx_u vs rx_base | -0.060 [-0.13, +0.01] (45 papers, 14/25, Holm p 0.3243) |
| rx_c vs rx_base | -0.150 [-0.23, -0.07] (45 papers, 12/31, Holm p 0.027) |
| rx_ru vs rx_base | -0.076 [-0.17, +0.01] (45 papers, 14/27, Holm p 0.2384) |
| rx_ruc vs rx_base | -0.228 [-0.31, -0.15] (45 papers, 8/36, Holm p 0.0) |
| rx_ruc vs rx_ru | -0.152 [-0.22, -0.08] (45 papers, 10/30, Holm p 0.0132) |
| rx_ruc vs rx_ruc_select | -0.045 [-0.11, +0.02] (45 papers, 16/20, Holm p 1.0) |

## GPT-5.6 reconstruction (as complete)

| comparison | difference [CI] |
|---|---|
| rx_r vs rx_base | +0.000 [-0.22, +0.17] (8 papers, 4/3, Holm p 1.0) |
| rx_u vs rx_base | -0.048 [-0.13, +0.05] (7 papers, 2/4, Holm p 1.0) |
| rx_c vs rx_base | -0.077 [-0.27, +0.09] (7 papers, 3/3, Holm p 1.0) |
| rx_ru vs rx_base | -0.125 [-0.33, +0.08] (2 papers, 1/1, Holm p 1.0) |
| rx_ruc vs rx_base | -0.101 [-0.35, +0.12] (6 papers, 3/3, Holm p 1.0) |
| rx_ruc vs rx_ru | -0.083 [-0.33, +0.17] (2 papers, 1/1, Holm p 1.0) |

## Research quality (RQ, three DeepSeek calls)

| comparison | difference [CI] |
|---|---|
| rx_r vs rx_base | -0.017 [-0.12, +0.08] (45 papers, 24/21, Holm p 1.0) |
| rx_u vs rx_base | -0.076 [-0.16, +0.01] (45 papers, 19/26, Holm p 1.0) |
| rx_c vs rx_base | +0.005 [-0.10, +0.11] (45 papers, 23/22, Holm p 1.0) |
| rx_ru vs rx_base | -0.056 [-0.15, +0.04] (45 papers, 17/27, Holm p 1.0) |
| rx_ruc vs rx_base | -0.074 [-0.17, +0.01] (45 papers, 19/26, Holm p 1.0) |
| rx_ruc vs rx_ru | -0.019 [-0.12, +0.09] (45 papers, 24/21, Holm p 1.0) |
| rx_ruc vs rx_ruc_select | +0.114 [-0.00, +0.22] (45 papers, 28/17, Holm p 0.9464) |

R x U interaction (DeepSeek): -0.048 [-0.12, +0.02] (45 papers, 16/27)

## Pairwise quality without the answer key (DeepSeek, both orders)

- rx_r__vs__rx_base: pairs 270, new wins 0.204, base wins 0.048, net +0.156 [+0.09, +0.22] (45 papers, 26/5, Holm p 0.0008)
- rx_u__vs__rx_base: pairs 270, new wins 0.156, base wins 0.081, net +0.074 [+0.01, +0.14] (45 papers, 23/13, Holm p 0.265)
- rx_c__vs__rx_base: pairs 270, new wins 0.059, base wins 0.33, net -0.270 [-0.35, -0.19] (45 papers, 5/38, Holm p 0.0)
- rx_ruc__vs__rx_base: pairs 270, new wins 0.13, base wins 0.174, net -0.044 [-0.11, +0.02] (45 papers, 13/22, Holm p 0.265)
- rx_ruc__vs__rx_ruc_select: pairs 270, new wins 0.3, base wins 0.107, net +0.193 [+0.12, +0.27] (45 papers, 30/8, Holm p 0.0015)

## DeepSeek dimensions

| arm | intervention | conditions | mechanism | outcome |
|---|---:|---:|---:|---:|
| rx_base | 0.481 | 0.733 | 0.604 | 0.7 |
| rx_r | 0.507 | 0.778 | 0.644 | 0.719 |
| rx_u | 0.463 | 0.648 | 0.578 | 0.589 |
| rx_ru | 0.463 | 0.648 | 0.556 | 0.548 |
| rx_c | 0.344 | 0.578 | 0.441 | 0.556 |
| rx_ruc_select | 0.341 | 0.496 | 0.47 | 0.481 |
| rx_ruc | 0.311 | 0.47 | 0.407 | 0.419 |

## Retrieval

Screener grades: {"focused": {"questions": 135, "papers_per_question": 27.2, "screened_grades": {"papers": 13922, "grade_0": 0.24, "grade_1": 0.4, "grade_2": 0.267, "grade_3": 0.093}, "selected_paper_grades": {"papers": 3670, "grade_0": 0.0, "grade_1": 0.0, "grade_2": 0.646, "grade_3": 0.354}, "pack_passage_grades": {"papers": 6124, "grade_0": 0.0, "grade_1": 0.0, "grade_2": 0.152, "grade_3": 0.848}, "pack_chars_mean": 57930, "questions_with_empty_pack": 0}, "old_corpus": {"questions": 135, "paper_grades": {"papers": 8950, "grade_0": 0.21, "grade_1": 0.428, "grade_2": 0.267, "grade_3": 0.096}, "seed_grades": {"papers": 6701, "grade_0": 0.21, "grade_1": 0.415, "grade_2": 0.268, "grade_3": 0.107}, "expansion_grades": {"papers": 2249, "grade_0": 0.209, "grade_1": 0.466, "grade_2": 0.262, "grade_3": 0.063}}}

Lever density (DeepSeek labels; target-aware analysis only): {"focused": {"units": 135, "lever_passage_share": 0.016, "pack_contains_lever": 0.267}, "r2": {"units": 135, "lever_passage_share": 0.012, "pack_contains_lever": 0.311}, "focused_minus_r2": {"papers": 45, "a_mean": 0.016, "b_mean": 0.012, "diff": 0.004, "ci95": [-0.002, 0.012], "up": 18, "down": 17, "p": 1.0}}

## Loops

- rx_c: {"runs": 270, "stop": {"fine": 237, "no_improvement": 18, "max_rounds": 15}, "critique_rounds": {"2": 203, "3": 67}, "final_fine": 0.878, "round1_first_candidate_selected_and_kept": 0.0, "critic_agreement_spearman": {"4o~llama": 0.406, "4o~o1": 0.413, "llama~o1": 0.356}, "re_retrieval_added_records": 6.367}
- rx_ruc_select: {"runs": 270, "stop": {"select_only": 270}, "critique_rounds": {"1": 270}, "final_fine": 0.77, "round1_first_candidate_selected_and_kept": 0.504, "critic_agreement_spearman": {"4o~llama": 0.427, "4o~o1": 0.421, "llama~o1": 0.286}, "re_retrieval_added_records": 0.0}
- rx_ruc: {"runs": 270, "stop": {"fine": 237, "max_rounds": 8, "no_improvement": 25}, "critique_rounds": {"2": 230, "3": 40}, "final_fine": 0.878, "round1_first_candidate_selected_and_kept": 0.0, "critic_agreement_spearman": {"4o~llama": 0.373, "4o~o1": 0.402, "llama~o1": 0.343}, "re_retrieval_added_records": 4.885}

## Leakage

{"counters": {"temporal_violations": 0, "test_paper_leaks": 0, "family_leaks": 0, "target_doi_or_title_leaks": 0, "invalid_citations": 0}, "records_rechecked": 80198, "date_violations": 0}
