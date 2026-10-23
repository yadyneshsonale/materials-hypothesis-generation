# Improvement experiment

Integrity: expected_new_runs: 288, new_runs: 288, ok: 288, judged_gpt56: 288, judged_deepseek: 288, audited: 288, selections: 72, temporal_violations: 0, test_paper_leaks: 0, family_leaks: 0, invalid_citations: 0, stage_errors: audit: 0, cross_judge: 0, generate_closed_book_fixed_text_systemmatch_card_systemmatch: 0, generate_knowledge_first: 0, judge: 0, select: 0, generators: openai:Qwen3.5-35B-A3B-Q4_K_M.gguf, verified: True

## By arm

| Metric | closed_book | text_chunks | card | v2_units | closed_book_fixed | text_systemmatch | card_systemmatch | knowledge_first | ensemble_select |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| runs | 72 | 72 | 72 | 72 | 72 | 72 | 72 | 72 | 72 |
| failed | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| judged | 70 | 72 | 72 | 72 | 72 | 72 | 72 | 72 | 72 |
| reconstruction_gpt56 | 1.65 | 1.56 | 1.52 | 1.52 | 1.49 | 1.57 | 1.62 | 1.42 | 1.59 |
| reconstruction_deepseek | 2.20 | 2.00 | 1.98 | 1.96 | 1.97 | 2.13 | 2.02 | 1.99 | 2.12 |
| reconstruction_gpt56_non_broad | 2.06 | 2.00 | 1.92 | 1.99 | 1.84 | 1.96 | 2.02 | 1.77 | 2.00 |
| by_level | broad: 0.77, problem_constrained: 1.68, expert_context: 2.44 | broad: 0.67, problem_constrained: 1.50, expert_context: 2.50 | broad: 0.74, problem_constrained: 1.43, expert_context: 2.41 | broad: 0.58, problem_constrained: 1.54, expert_context: 2.44 | broad: 0.79, problem_constrained: 1.34, expert_context: 2.33 | broad: 0.78, problem_constrained: 1.45, expert_context: 2.48 | broad: 0.81, problem_constrained: 1.42, expert_context: 2.62 | broad: 0.72, problem_constrained: 1.25, expert_context: 2.28 | broad: 0.75, problem_constrained: 1.46, expert_context: 2.55 |
| failure_rate_by_level | broad: 0.82, problem_constrained: 0.17, expert_context: 0.04 | broad: 0.83, problem_constrained: 0.25, expert_context: 0.00 | broad: 0.79, problem_constrained: 0.38, expert_context: 0.00 | broad: 0.96, problem_constrained: 0.21, expert_context: 0.00 | broad: 0.83, problem_constrained: 0.42, expert_context: 0.08 | broad: 0.83, problem_constrained: 0.25, expert_context: 0.00 | broad: 0.71, problem_constrained: 0.21, expert_context: 0.00 | broad: 0.83, problem_constrained: 0.38, expert_context: 0.00 | broad: 0.88, problem_constrained: 0.29, expert_context: 0.00 |
| intervention | 1.83 | 1.67 | 1.58 | 1.60 | 1.51 | 1.67 | 1.72 | 1.42 | 1.64 |
| mechanism | 1.59 | 1.53 | 1.50 | 1.53 | 1.51 | 1.62 | 1.64 | 1.50 | 1.64 |
| outcome | 1.73 | 1.68 | 1.67 | 1.65 | 1.62 | 1.61 | 1.60 | 1.54 | 1.67 |
| evidence_validity | 1.14 | 1.10 | 0.86 | 1.00 | 0.68 | 1.39 | 1.25 | 0.74 | 1.14 |
| novelty | 1.90 | 2.11 | 2.18 | 2.32 | 2.31 | 2.07 | 2.11 | 2.32 | 2.18 |
| mechanism_own_reasoning | 1.00 | 0.31 | 0.46 | 0.35 | 1.00 | 0.26 | 0.31 | 0.46 | 0.46 |
| mechanism_transferred_unjustified | 0.00 | 0.58 | 0.47 | 0.54 | 0.00 | 0.49 | 0.57 | 0.53 | 0.43 |
| mechanism_transferred_justified | 0.00 | 0.10 | 0.06 | 0.11 | 0.00 | 0.25 | 0.11 | 0.00 | 0.11 |
| complete_chain_rate | 0.66 | 0.60 | 0.67 | 0.60 | 0.74 | 0.67 | 0.69 | 0.74 | 0.72 |
| contradictions_per_hypothesis | 0.64 | 1.08 | 1.12 | 1.03 | 1.14 | 0.97 | 1.04 | 1.00 | 1.04 |
| specificity | 0.47 | 0.60 | 0.63 | 0.61 | 0.71 | 0.76 | 0.74 | 0.74 | 0.73 |
| citations_per_hypothesis | 0.00 | 3.88 | 2.46 | 4.07 | 0.00 | 2.92 | 2.49 | 3.06 | 2.49 |
| supportive_share_of_citations | n/a | 0.55 | 0.81 | n/a | n/a | 0.58 | 0.85 | 0.57 | 0.73 |
| hedges_per_hypothesis | 0.07 | 0.04 | 0.11 | 0.03 | 0.01 | 0.49 | 0.53 | 0.01 | 0.22 |
| evidence_caveat_rate | 0.76 | n/a | n/a | n/a | 0.15 | n/a | n/a | n/a | n/a |

## Paired comparisons (GPT-5.6; unit = mean of 2 samples)

| A | B | Role | Units | Mean diff | 95% CI | Papers A higher / B higher | Sign p | Holm p |
|---|---|---|---:|---:|---|---:|---:|---:|
| closed_book_fixed | text_chunks | primary | 36 | -0.066 | [-0.198, +0.080] | 3 / 8 | 0.227 | 0.91 |
| text_systemmatch | text_chunks | primary | 36 | +0.014 | [-0.080, +0.111] | 5 / 6 | 1.000 | 1.00 |
| card_systemmatch | text_chunks | primary | 36 | +0.063 | [-0.083, +0.219] | 6 / 5 | 1.000 | 1.00 |
| knowledge_first | text_chunks | primary | 36 | -0.139 | [-0.264, -0.000] | 1 / 9 | 0.021 | 0.11 |
| ensemble_select | text_chunks | primary | 36 | +0.031 | [-0.097, +0.167] | 5 / 3 | 0.727 | 1.00 |
| closed_book_fixed | closed_book | secondary | 35 | -0.130 | [-0.245, -0.003] | 2 / 10 | 0.039 | n/a |
| text_systemmatch | closed_book | secondary | 35 | -0.047 | [-0.151, +0.056] | 5 / 7 | 0.774 | n/a |
| card_systemmatch | closed_book | secondary | 35 | +0.007 | [-0.142, +0.160] | 6 / 4 | 0.754 | n/a |
| knowledge_first | closed_book | secondary | 35 | -0.210 | [-0.358, -0.056] | 3 / 9 | 0.146 | n/a |
| ensemble_select | closed_book | secondary | 35 | -0.035 | [-0.191, +0.118] | 6 / 6 | 1.000 | n/a |
| closed_book_fixed (non-broad) | text_chunks (non-broad) | secondary | 24 | -0.161 | [-0.276, -0.052] | 3 / 8 | 0.227 | n/a |
| text_systemmatch (non-broad) | text_chunks (non-broad) | secondary | 24 | -0.036 | [-0.156, +0.089] | 3 / 6 | 0.508 | n/a |
| card_systemmatch (non-broad) | text_chunks (non-broad) | secondary | 24 | +0.021 | [-0.151, +0.172] | 6 / 6 | 1.000 | n/a |
| knowledge_first (non-broad) | text_chunks (non-broad) | secondary | 24 | -0.234 | [-0.349, -0.130] | 0 / 10 | 0.002 | n/a |
| ensemble_select (non-broad) | text_chunks (non-broad) | secondary | 24 | +0.005 | [-0.115, +0.125] | 5 / 5 | 1.000 | n/a |

## Paired comparisons (DeepSeek-V4-Pro; unit = mean of 2 samples)

| A | B | Role | Units | Mean diff | 95% CI | Papers A higher / B higher | Sign p | Holm p |
|---|---|---|---:|---:|---|---:|---:|---:|
| closed_book_fixed | text_chunks | primary | 36 | -0.028 | [-0.170, +0.128] | 5 / 7 | 0.774 | 1.00 |
| text_systemmatch | text_chunks | primary | 36 | +0.135 | [+0.017, +0.247] | 8 / 4 | 0.388 | 1.00 |
| card_systemmatch | text_chunks | primary | 36 | +0.021 | [-0.163, +0.181] | 7 / 5 | 0.774 | 1.00 |
| knowledge_first | text_chunks | primary | 36 | -0.010 | [-0.146, +0.135] | 5 / 7 | 0.774 | 1.00 |
| ensemble_select | text_chunks | primary | 36 | +0.122 | [-0.031, +0.267] | 8 / 3 | 0.227 | 1.00 |
| closed_book_fixed | closed_book | secondary | 35 | -0.182 | [-0.306, -0.057] | 2 / 9 | 0.065 | n/a |
| text_systemmatch | closed_book | secondary | 35 | -0.026 | [-0.207, +0.149] | 6 / 5 | 1.000 | n/a |
| card_systemmatch | closed_book | secondary | 35 | -0.142 | [-0.382, +0.076] | 6 / 6 | 1.000 | n/a |
| knowledge_first | closed_book | secondary | 35 | -0.168 | [-0.318, -0.026] | 3 / 8 | 0.227 | n/a |
| ensemble_select | closed_book | secondary | 35 | -0.035 | [-0.205, +0.125] | 7 / 5 | 0.774 | n/a |
| closed_book_fixed (non-broad) | text_chunks (non-broad) | secondary | 24 | -0.109 | [-0.229, +0.021] | 3 / 9 | 0.146 | n/a |
| text_systemmatch (non-broad) | text_chunks (non-broad) | secondary | 24 | +0.026 | [-0.141, +0.198] | 7 / 5 | 0.774 | n/a |
| card_systemmatch (non-broad) | text_chunks (non-broad) | secondary | 24 | -0.052 | [-0.307, +0.167] | 8 / 4 | 0.388 | n/a |
| knowledge_first (non-broad) | text_chunks (non-broad) | secondary | 24 | -0.130 | [-0.266, +0.021] | 2 / 8 | 0.109 | n/a |
| ensemble_select (non-broad) | text_chunks (non-broad) | secondary | 24 | +0.052 | [-0.115, +0.208] | 8 / 4 | 0.388 | n/a |

## System-match appraisal

text_systemmatch: runs: 72, records_appraised_per_run: 8.44, verdicts: does_not_transfer: 0.53, partially: 0.39, transfers: 0.08, citations_of_records_judged_not_transferable: 3, citations: 210, card_systemmatch: runs: 72, records_appraised_per_run: 5.85, verdicts: does_not_transfer: 0.53, partially: 0.42, transfers: 0.05, : 0.00, citations_of_records_judged_not_transferable: 17, citations: 179

## Knowledge-first refinement

pairs: 72, intervention_word_overlap_with_draft: 0.97, mechanism_word_overlap_with_draft: 0.94, mean_change_vs_draft: -0.07, improved: 12, worse: 28

## Ensemble selection

selections: 72, fallbacks: 0, chosen_arm: text_systemmatch: 16, card_systemmatch: 21, knowledge_first: 14, closed_book_fixed: 9, card: 8, text_chunks: 4, chosen_position: C1: 52, C4: 6, C5: 2, C3: 5, C2: 7, selected_mean: 1.59, random_pick_mean: 1.53, oracle_best_mean: 1.93
