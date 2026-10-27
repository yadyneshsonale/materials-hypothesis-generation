# Improvement experiment

Integrity: expected_new_runs: 288, new_runs: 288, ok: 288, judged_gpt56: 288, judged_deepseek: 288, audited: 288, selections: 72, temporal_violations: 0, test_paper_leaks: 0, family_leaks: 0, invalid_citations: 0, stage_errors: audit: 0, cross_judge: 0, generate_knowledge_first: 0, generate_text_systemmatch_card_systemmatch: 0, judge: 0, select: 0, generators: trapi:Llama-3.3-70B-Instruct_5, verified: True

## By arm

| Metric | closed_book | text_chunks | card | v2_units | closed_book_fixed | text_systemmatch | card_systemmatch | knowledge_first | ensemble_select |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| runs | 72 | 72 | 72 | 0 | 72 | 72 | 72 | 72 | 72 |
| failed | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| judged | 72 | 72 | 72 | 0 | 72 | 72 | 72 | 72 | 72 |
| reconstruction_gpt56 | 0.60 | 0.48 | 0.45 | n/a | 0.53 | 0.48 | 0.44 | 0.48 | 0.51 |
| reconstruction_deepseek | 0.28 | 0.28 | 0.27 | n/a | 0.27 | 0.33 | 0.31 | 0.26 | 0.26 |
| reconstruction_gpt56_non_broad | 0.59 | 0.55 | 0.50 | n/a | 0.54 | 0.52 | 0.46 | 0.49 | 0.53 |
| by_level | broad: 0.62, problem_constrained: 0.55, expert_context: 0.62 | broad: 0.33, problem_constrained: 0.64, expert_context: 0.46 | broad: 0.34, problem_constrained: 0.53, expert_context: 0.47 | broad: n/a, problem_constrained: n/a, expert_context: n/a | broad: 0.51, problem_constrained: 0.52, expert_context: 0.56 | broad: 0.41, problem_constrained: 0.57, expert_context: 0.47 | broad: 0.40, problem_constrained: 0.49, expert_context: 0.43 | broad: 0.46, problem_constrained: 0.48, expert_context: 0.51 | broad: 0.47, problem_constrained: 0.54, expert_context: 0.52 |
| failure_rate_by_level | broad: 0.96, problem_constrained: 0.92, expert_context: 0.83 | broad: 1.00, problem_constrained: 0.92, expert_context: 0.96 | broad: 1.00, problem_constrained: 0.96, expert_context: 1.00 | broad: n/a, problem_constrained: n/a, expert_context: n/a | broad: 1.00, problem_constrained: 0.83, expert_context: 0.92 | broad: 1.00, problem_constrained: 0.88, expert_context: 1.00 | broad: 0.96, problem_constrained: 1.00, expert_context: 0.96 | broad: 1.00, problem_constrained: 0.92, expert_context: 0.92 | broad: 1.00, problem_constrained: 0.92, expert_context: 0.92 |
| intervention | 0.28 | 0.15 | 0.18 | n/a | 0.18 | 0.19 | 0.12 | 0.18 | 0.18 |
| mechanism | 0.65 | 0.43 | 0.43 | n/a | 0.53 | 0.44 | 0.46 | 0.44 | 0.49 |
| outcome | 0.93 | 0.81 | 0.74 | n/a | 0.85 | 0.79 | 0.72 | 0.71 | 0.78 |
| evidence_validity | 0.03 | 1.31 | 1.03 | n/a | 0.00 | 1.07 | 1.25 | 0.57 | 0.71 |
| novelty | 1.21 | 1.24 | 1.32 | n/a | 1.40 | 1.12 | 1.40 | 1.51 | 1.42 |
| mechanism_own_reasoning | 1.00 | 0.19 | 0.21 | 0.00 | 1.00 | 0.43 | 0.19 | 0.61 | 0.56 |
| mechanism_transferred_unjustified | 0.00 | 0.60 | 0.69 | 0.00 | 0.00 | 0.44 | 0.62 | 0.33 | 0.35 |
| mechanism_transferred_justified | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.04 | 0.01 | 0.03 |
| complete_chain_rate | 0.47 | 0.17 | 0.19 | n/a | 0.68 | 0.31 | 0.22 | 0.60 | 0.51 |
| contradictions_per_hypothesis | 0.22 | 0.36 | 0.36 | n/a | 0.40 | 0.22 | 0.24 | 0.35 | 0.44 |
| specificity | 0.17 | 0.17 | 0.20 | n/a | 0.39 | 0.19 | 0.18 | 0.39 | 0.43 |
| citations_per_hypothesis | 0.00 | 2.60 | 2.28 | n/a | 0.00 | 3.29 | 3.17 | 4.15 | 2.65 |
| supportive_share_of_citations | n/a | 0.00 | 0.00 | n/a | n/a | 0.00 | 0.00 | 0.00 | 0.00 |
| hedges_per_hypothesis | 0.07 | 0.01 | 0.11 | n/a | 0.01 | 0.17 | 0.26 | 0.01 | 0.04 |
| evidence_caveat_rate | 0.03 | n/a | n/a | n/a | 0.00 | n/a | n/a | n/a | n/a |

## Paired comparisons (GPT-5.6; unit = mean of 2 samples)

| A | B | Role | Units | Mean diff | 95% CI | Papers A higher / B higher | Sign p | Holm p |
|---|---|---|---:|---:|---|---:|---:|---:|
| closed_book_fixed | text_chunks | primary | 36 | +0.056 | [-0.056, +0.160] | 8 / 2 | 0.109 | 0.55 |
| text_systemmatch | text_chunks | primary | 36 | +0.007 | [-0.042, +0.052] | 7 / 4 | 0.549 | 1.00 |
| card_systemmatch | text_chunks | primary | 36 | -0.038 | [-0.115, +0.038] | 4 / 7 | 0.549 | 1.00 |
| knowledge_first | text_chunks | primary | 36 | +0.007 | [-0.094, +0.097] | 6 / 5 | 1.000 | 1.00 |
| ensemble_select | text_chunks | primary | 36 | +0.035 | [-0.059, +0.122] | 8 / 4 | 0.388 | 1.00 |
| closed_book_fixed | closed_book | secondary | 36 | -0.069 | [-0.122, -0.024] | 1 / 8 | 0.039 | n/a |
| text_systemmatch | closed_book | secondary | 36 | -0.118 | [-0.229, -0.010] | 3 / 9 | 0.146 | n/a |
| card_systemmatch | closed_book | secondary | 36 | -0.163 | [-0.285, -0.049] | 3 / 9 | 0.146 | n/a |
| knowledge_first | closed_book | secondary | 36 | -0.118 | [-0.184, -0.052] | 1 / 10 | 0.012 | n/a |
| ensemble_select | closed_book | secondary | 36 | -0.090 | [-0.163, -0.024] | 2 / 10 | 0.039 | n/a |
| closed_book_fixed (non-broad) | text_chunks (non-broad) | secondary | 24 | -0.005 | [-0.135, +0.109] | 5 / 4 | 1.000 | n/a |
| text_systemmatch (non-broad) | text_chunks (non-broad) | secondary | 24 | -0.026 | [-0.104, +0.052] | 5 / 6 | 1.000 | n/a |
| card_systemmatch (non-broad) | text_chunks (non-broad) | secondary | 24 | -0.089 | [-0.146, -0.026] | 2 / 9 | 0.065 | n/a |
| knowledge_first (non-broad) | text_chunks (non-broad) | secondary | 24 | -0.052 | [-0.146, +0.031] | 3 / 6 | 0.508 | n/a |
| ensemble_select (non-broad) | text_chunks (non-broad) | secondary | 24 | -0.016 | [-0.109, +0.078] | 6 / 4 | 0.754 | n/a |

## Paired comparisons (DeepSeek-V4-Pro; unit = mean of 2 samples)

| A | B | Role | Units | Mean diff | 95% CI | Papers A higher / B higher | Sign p | Holm p |
|---|---|---|---:|---:|---|---:|---:|---:|
| closed_book_fixed | text_chunks | primary | 36 | -0.010 | [-0.094, +0.080] | 5 / 7 | 0.774 | 1.00 |
| text_systemmatch | text_chunks | primary | 36 | +0.042 | [-0.038, +0.111] | 8 / 3 | 0.227 | 1.00 |
| card_systemmatch | text_chunks | primary | 36 | +0.024 | [-0.076, +0.118] | 6 / 5 | 1.000 | 1.00 |
| knowledge_first | text_chunks | primary | 36 | -0.024 | [-0.115, +0.094] | 3 / 8 | 0.227 | 1.00 |
| ensemble_select | text_chunks | primary | 36 | -0.021 | [-0.087, +0.045] | 5 / 5 | 1.000 | 1.00 |
| closed_book_fixed | closed_book | secondary | 36 | -0.003 | [-0.076, +0.073] | 6 / 5 | 1.000 | n/a |
| text_systemmatch | closed_book | secondary | 36 | +0.049 | [-0.104, +0.188] | 8 / 3 | 0.227 | n/a |
| card_systemmatch | closed_book | secondary | 36 | +0.031 | [-0.146, +0.194] | 6 / 5 | 1.000 | n/a |
| knowledge_first | closed_book | secondary | 36 | -0.017 | [-0.108, +0.073] | 5 / 6 | 1.000 | n/a |
| ensemble_select | closed_book | secondary | 36 | -0.014 | [-0.125, +0.090] | 5 / 5 | 1.000 | n/a |
| closed_book_fixed (non-broad) | text_chunks (non-broad) | secondary | 24 | -0.042 | [-0.161, +0.083] | 5 / 7 | 0.774 | n/a |
| text_systemmatch (non-broad) | text_chunks (non-broad) | secondary | 24 | +0.010 | [-0.099, +0.120] | 6 / 5 | 1.000 | n/a |
| card_systemmatch (non-broad) | text_chunks (non-broad) | secondary | 24 | -0.042 | [-0.146, +0.073] | 4 / 8 | 0.388 | n/a |
| knowledge_first (non-broad) | text_chunks (non-broad) | secondary | 24 | -0.047 | [-0.182, +0.125] | 3 / 8 | 0.227 | n/a |
| ensemble_select (non-broad) | text_chunks (non-broad) | secondary | 24 | -0.073 | [-0.177, +0.042] | 3 / 8 | 0.227 | n/a |

## System-match appraisal

text_systemmatch: runs: 72, records_appraised_per_run: 7.40, verdicts: partially: 0.60, does_not_transfer: 0.27, transfers: 0.13, citations_of_records_judged_not_transferable: 8, citations: 237, card_systemmatch: runs: 72, records_appraised_per_run: 7.21, verdicts: partially: 0.61, does_not_transfer: 0.32, transfers: 0.07, citations_of_records_judged_not_transferable: 3, citations: 228

## Knowledge-first refinement

pairs: 72, intervention_word_overlap_with_draft: 0.99, mechanism_word_overlap_with_draft: 0.99, mean_change_vs_draft: -0.05, improved: 15, worse: 23

## Ensemble selection

selections: 72, fallbacks: 0, chosen_arm: text_systemmatch: 6, closed_book_fixed: 19, knowledge_first: 24, card_systemmatch: 13, text_chunks: 7, card: 3, chosen_position: C1: 26, C2: 24, C6: 4, C4: 6, C3: 8, C5: 4, selected_mean: 0.51, random_pick_mean: 0.48, oracle_best_mean: 0.75
