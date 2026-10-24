# Improvement experiment

Integrity: expected_new_runs: 288, new_runs: 288, ok: 288, judged_gpt56: 288, judged_deepseek: 288, audited: 288, selections: 72, temporal_violations: 0, test_paper_leaks: 0, family_leaks: 0, invalid_citations: 0, stage_errors: audit: 0, cross_judge: 0, generate_closed_book_fixed_text_systemmatch_card_systemmatch: 0, generate_knowledge_first: 0, judge: 0, select: 0, generators: trapi:Llama-3.3-70B-Instruct_5, verified: True

## By arm

| Metric | closed_book | text_chunks | card | v2_units | closed_book_fixed | text_systemmatch | card_systemmatch | knowledge_first | ensemble_select |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| runs | 72 | 72 | 72 | 72 | 72 | 72 | 72 | 72 | 72 |
| failed | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| judged | 72 | 72 | 72 | 72 | 72 | 72 | 72 | 72 | 72 |
| reconstruction_gpt56 | 0.60 | 0.47 | 0.48 | 0.38 | 0.53 | 0.48 | 0.49 | 0.53 | 0.54 |
| reconstruction_deepseek | 0.28 | 0.26 | 0.20 | 0.16 | 0.27 | 0.32 | 0.20 | 0.23 | 0.27 |
| reconstruction_gpt56_non_broad | 0.59 | 0.45 | 0.52 | 0.42 | 0.54 | 0.48 | 0.50 | 0.55 | 0.56 |
| by_level | broad: 0.62, problem_constrained: 0.55, expert_context: 0.62 | broad: 0.51, problem_constrained: 0.46, expert_context: 0.44 | broad: 0.39, problem_constrained: 0.51, expert_context: 0.53 | broad: 0.31, problem_constrained: 0.45, expert_context: 0.39 | broad: 0.51, problem_constrained: 0.52, expert_context: 0.56 | broad: 0.49, problem_constrained: 0.47, expert_context: 0.49 | broad: 0.48, problem_constrained: 0.55, expert_context: 0.45 | broad: 0.50, problem_constrained: 0.53, expert_context: 0.56 | broad: 0.50, problem_constrained: 0.56, expert_context: 0.56 |
| failure_rate_by_level | broad: 0.96, problem_constrained: 0.92, expert_context: 0.83 | broad: 1.00, problem_constrained: 0.92, expert_context: 0.96 | broad: 0.96, problem_constrained: 0.92, expert_context: 0.92 | broad: 1.00, problem_constrained: 0.96, expert_context: 1.00 | broad: 1.00, problem_constrained: 0.83, expert_context: 0.92 | broad: 0.92, problem_constrained: 0.96, expert_context: 0.96 | broad: 1.00, problem_constrained: 0.88, expert_context: 0.92 | broad: 1.00, problem_constrained: 0.92, expert_context: 0.92 | broad: 1.00, problem_constrained: 0.92, expert_context: 0.92 |
| intervention | 0.28 | 0.11 | 0.21 | 0.04 | 0.18 | 0.19 | 0.19 | 0.17 | 0.17 |
| mechanism | 0.65 | 0.56 | 0.47 | 0.39 | 0.53 | 0.54 | 0.53 | 0.53 | 0.60 |
| outcome | 0.93 | 0.71 | 0.76 | 0.69 | 0.85 | 0.74 | 0.81 | 0.76 | 0.78 |
| evidence_validity | 0.03 | 1.08 | 0.75 | 0.81 | 0.00 | 1.17 | 0.75 | 0.32 | 0.44 |
| novelty | 1.21 | 1.12 | 1.44 | 1.10 | 1.40 | 1.31 | 1.25 | 1.62 | 1.54 |
| mechanism_own_reasoning | 1.00 | 0.29 | 0.79 | 0.28 | 1.00 | 0.40 | 0.74 | 0.72 | 0.78 |
| mechanism_transferred_unjustified | 0.00 | 0.61 | 0.18 | 0.53 | 0.00 | 0.50 | 0.26 | 0.28 | 0.21 |
| mechanism_transferred_justified | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.04 | 0.00 | 0.00 | 0.00 |
| complete_chain_rate | 0.47 | 0.24 | 0.36 | 0.17 | 0.68 | 0.22 | 0.24 | 0.51 | 0.54 |
| contradictions_per_hypothesis | 0.22 | 0.22 | 0.24 | 0.21 | 0.40 | 0.22 | 0.24 | 0.32 | 0.42 |
| specificity | 0.17 | 0.12 | 0.15 | 0.10 | 0.39 | 0.14 | 0.17 | 0.40 | 0.38 |
| citations_per_hypothesis | 0.00 | 1.99 | 1.53 | 2.18 | 0.00 | 2.54 | 2.11 | 2.24 | 1.40 |
| supportive_share_of_citations | n/a | 0.34 | 0.51 | n/a | n/a | 0.28 | 0.53 | 0.31 | 0.44 |
| hedges_per_hypothesis | 0.07 | 0.08 | 0.06 | 0.11 | 0.01 | 0.21 | 0.47 | 0.01 | 0.06 |
| evidence_caveat_rate | 0.03 | n/a | n/a | n/a | 0.00 | n/a | n/a | n/a | n/a |

## Paired comparisons (GPT-5.6; unit = mean of 2 samples)

| A | B | Role | Units | Mean diff | 95% CI | Papers A higher / B higher | Sign p | Holm p |
|---|---|---|---:|---:|---|---:|---:|---:|
| closed_book_fixed | text_chunks | primary | 36 | +0.062 | [-0.024, +0.149] | 8 / 3 | 0.227 | 1.00 |
| text_systemmatch | text_chunks | primary | 36 | +0.014 | [-0.059, +0.094] | 7 / 4 | 0.549 | 1.00 |
| card_systemmatch | text_chunks | primary | 36 | +0.024 | [-0.073, +0.128] | 6 / 5 | 1.000 | 1.00 |
| knowledge_first | text_chunks | primary | 36 | +0.062 | [-0.035, +0.163] | 8 / 3 | 0.227 | 1.00 |
| ensemble_select | text_chunks | primary | 36 | +0.073 | [+0.000, +0.149] | 7 / 3 | 0.344 | 1.00 |
| closed_book_fixed | closed_book | secondary | 36 | -0.069 | [-0.122, -0.024] | 1 / 8 | 0.039 | n/a |
| text_systemmatch | closed_book | secondary | 36 | -0.118 | [-0.243, +0.010] | 3 / 9 | 0.146 | n/a |
| card_systemmatch | closed_book | secondary | 36 | -0.108 | [-0.212, +0.007] | 3 / 9 | 0.146 | n/a |
| knowledge_first | closed_book | secondary | 36 | -0.069 | [-0.125, -0.014] | 2 / 8 | 0.109 | n/a |
| ensemble_select | closed_book | secondary | 36 | -0.059 | [-0.128, +0.017] | 3 / 8 | 0.227 | n/a |
| closed_book_fixed (non-broad) | text_chunks (non-broad) | secondary | 24 | +0.094 | [-0.036, +0.250] | 6 / 4 | 0.754 | n/a |
| text_systemmatch (non-broad) | text_chunks (non-broad) | secondary | 24 | +0.031 | [-0.062, +0.104] | 8 / 2 | 0.109 | n/a |
| card_systemmatch (non-broad) | text_chunks (non-broad) | secondary | 24 | +0.052 | [-0.068, +0.203] | 7 / 4 | 0.549 | n/a |
| knowledge_first (non-broad) | text_chunks (non-broad) | secondary | 24 | +0.099 | [-0.031, +0.255] | 6 / 4 | 0.754 | n/a |
| ensemble_select (non-broad) | text_chunks (non-broad) | secondary | 24 | +0.115 | [+0.016, +0.255] | 8 / 2 | 0.109 | n/a |

## Paired comparisons (DeepSeek-V4-Pro; unit = mean of 2 samples)

| A | B | Role | Units | Mean diff | 95% CI | Papers A higher / B higher | Sign p | Holm p |
|---|---|---|---:|---:|---|---:|---:|---:|
| closed_book_fixed | text_chunks | primary | 36 | +0.017 | [-0.087, +0.128] | 5 / 6 | 1.000 | 1.00 |
| text_systemmatch | text_chunks | primary | 36 | +0.062 | [-0.059, +0.205] | 4 / 5 | 1.000 | 1.00 |
| card_systemmatch | text_chunks | primary | 36 | -0.052 | [-0.191, +0.073] | 3 / 5 | 0.727 | 1.00 |
| knowledge_first | text_chunks | primary | 36 | -0.028 | [-0.128, +0.090] | 3 / 7 | 0.344 | 1.00 |
| ensemble_select | text_chunks | primary | 36 | +0.010 | [-0.104, +0.128] | 6 / 4 | 0.754 | 1.00 |
| closed_book_fixed | closed_book | secondary | 36 | -0.003 | [-0.076, +0.073] | 6 / 5 | 1.000 | n/a |
| text_systemmatch | closed_book | secondary | 36 | +0.042 | [-0.146, +0.243] | 4 / 7 | 0.549 | n/a |
| card_systemmatch | closed_book | secondary | 36 | -0.073 | [-0.215, +0.087] | 2 / 9 | 0.065 | n/a |
| knowledge_first | closed_book | secondary | 36 | -0.049 | [-0.153, +0.042] | 5 / 6 | 1.000 | n/a |
| ensemble_select | closed_book | secondary | 36 | -0.010 | [-0.149, +0.118] | 3 / 5 | 0.727 | n/a |
| closed_book_fixed (non-broad) | text_chunks (non-broad) | secondary | 24 | +0.000 | [-0.146, +0.151] | 4 / 7 | 0.549 | n/a |
| text_systemmatch (non-broad) | text_chunks (non-broad) | secondary | 24 | +0.005 | [-0.130, +0.151] | 3 / 6 | 0.508 | n/a |
| card_systemmatch (non-broad) | text_chunks (non-broad) | secondary | 24 | -0.073 | [-0.193, +0.052] | 3 / 6 | 0.508 | n/a |
| knowledge_first (non-broad) | text_chunks (non-broad) | secondary | 24 | -0.005 | [-0.141, +0.146] | 3 / 6 | 0.508 | n/a |
| ensemble_select (non-broad) | text_chunks (non-broad) | secondary | 24 | +0.052 | [-0.094, +0.198] | 6 / 4 | 0.754 | n/a |

## System-match appraisal

text_systemmatch: runs: 72, records_appraised_per_run: 6.75, verdicts: partially: 0.60, does_not_transfer: 0.33, transfers: 0.07, citations_of_records_judged_not_transferable: 2, citations: 183, card_systemmatch: runs: 72, records_appraised_per_run: 5.40, verdicts: partially: 0.59, does_not_transfer: 0.39, transfers: 0.02, citations_of_records_judged_not_transferable: 1, citations: 152

## Knowledge-first refinement

pairs: 72, intervention_word_overlap_with_draft: 1.00, mechanism_word_overlap_with_draft: 1.00, mean_change_vs_draft: 0.00, improved: 14, worse: 14

## Ensemble selection

selections: 72, fallbacks: 0, chosen_arm: closed_book_fixed: 20, text_chunks: 1, knowledge_first: 26, card: 13, card_systemmatch: 9, text_systemmatch: 3, chosen_position: C3: 11, C2: 19, C1: 29, C4: 5, C5: 6, C6: 2, selected_mean: 0.54, random_pick_mean: 0.50, oracle_best_mean: 0.74
