# Improvement experiment

Integrity: expected_new_runs: 96, new_runs: 96, ok: 96, judged_gpt56: 96, judged_deepseek: 96, audited: 96, selections: 24, temporal_violations: 0, test_paper_leaks: 0, family_leaks: 0, invalid_citations: 0, stage_errors: audit: 0, cross_judge: 0, generate_closed_book_fixed_text_systemmatch_card_systemmatch: 0, generate_knowledge_first: 0, judge: 0, select: 0, generators: trapi:Llama-3.3-70B-Instruct_5, verified: True

## By arm

| Metric | closed_book | text_chunks | card | v2_units | closed_book_fixed | text_systemmatch | card_systemmatch | knowledge_first | ensemble_select |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| runs | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 24 |
| failed | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| judged | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 24 |
| reconstruction_gpt56 | 0.43 | 0.44 | 0.46 | 0.43 | 0.58 | 0.50 | 0.52 | 0.53 | 0.52 |
| reconstruction_deepseek | 0.20 | 0.28 | 0.12 | 0.15 | 0.23 | 0.17 | 0.16 | 0.24 | 0.28 |
| reconstruction_gpt56_non_broad | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| by_level | scimon: 0.43 | scimon: 0.44 | scimon: 0.46 | scimon: 0.43 | scimon: 0.58 | scimon: 0.50 | scimon: 0.52 | scimon: 0.53 | scimon: 0.52 |
| failure_rate_by_level | scimon: 1.00 | scimon: 0.96 | scimon: 0.92 | scimon: 0.92 | scimon: 0.92 | scimon: 0.88 | scimon: 0.96 | scimon: 0.96 | scimon: 0.83 |
| intervention | 0.29 | 0.25 | 0.58 | 0.25 | 0.42 | 0.29 | 0.42 | 0.38 | 0.29 |
| mechanism | 0.29 | 0.50 | 0.38 | 0.46 | 0.42 | 0.62 | 0.58 | 0.46 | 0.50 |
| outcome | 0.71 | 0.67 | 0.62 | 0.71 | 1.04 | 0.67 | 0.79 | 0.88 | 0.83 |
| evidence_validity | 0.38 | 1.29 | 1.42 | 0.79 | 0.33 | 1.21 | 1.42 | 0.50 | 1.42 |
| novelty | 0.08 | 0.79 | 1.17 | 0.83 | 0.54 | 0.67 | 0.38 | 0.71 | 1.21 |
| mechanism_own_reasoning | 1.00 | 0.54 | 0.54 | 0.42 | 1.00 | 0.46 | 0.62 | 0.79 | 0.58 |
| mechanism_transferred_unjustified | 0.00 | 0.21 | 0.29 | 0.25 | 0.00 | 0.17 | 0.33 | 0.21 | 0.17 |
| mechanism_transferred_justified | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| complete_chain_rate | 0.17 | 0.21 | 0.12 | 0.04 | 0.21 | 0.25 | 0.12 | 0.21 | 0.29 |
| contradictions_per_hypothesis | 0.17 | 0.04 | 0.04 | 0.17 | 0.12 | 0.12 | 0.12 | 0.33 | 0.04 |
| specificity | 0.00 | 0.10 | 0.35 | 0.00 | 0.06 | 0.10 | 0.01 | 0.12 | 0.28 |
| citations_per_hypothesis | 0.00 | 2.58 | 2.42 | 2.21 | 0.00 | 3.12 | 2.54 | 4.08 | 2.08 |
| supportive_share_of_citations | n/a | 0.18 | 0.52 | n/a | n/a | 0.09 | 0.56 | 0.13 | 0.28 |
| hedges_per_hypothesis | 0.00 | 0.00 | 0.00 | 0.00 | 0.04 | 0.17 | 0.04 | 0.04 | 0.08 |
| evidence_caveat_rate | 0.04 | n/a | n/a | n/a | 0.00 | n/a | n/a | n/a | n/a |

## Paired comparisons (GPT-5.6; unit = mean of 2 samples)

| A | B | Role | Units | Mean diff | 95% CI | Papers A higher / B higher | Sign p | Holm p |
|---|---|---|---:|---:|---|---:|---:|---:|
| closed_book_fixed | text_chunks | primary | 12 | +0.146 | [-0.073, +0.365] | 7 / 4 | 0.549 | 1.00 |
| text_systemmatch | text_chunks | primary | 12 | +0.062 | [-0.021, +0.156] | 5 / 3 | 0.727 | 1.00 |
| card_systemmatch | text_chunks | primary | 12 | +0.083 | [-0.125, +0.271] | 8 / 3 | 0.227 | 1.00 |
| knowledge_first | text_chunks | primary | 12 | +0.094 | [-0.094, +0.281] | 7 / 4 | 0.549 | 1.00 |
| ensemble_select | text_chunks | primary | 12 | +0.083 | [-0.146, +0.312] | 6 / 3 | 0.508 | 1.00 |
| closed_book_fixed | closed_book | secondary | 12 | +0.156 | [+0.021, +0.312] | 7 / 2 | 0.180 | n/a |
| text_systemmatch | closed_book | secondary | 12 | +0.073 | [-0.198, +0.365] | 5 / 6 | 1.000 | n/a |
| card_systemmatch | closed_book | secondary | 12 | +0.094 | [-0.115, +0.323] | 6 / 4 | 0.754 | n/a |
| knowledge_first | closed_book | secondary | 12 | +0.104 | [-0.042, +0.250] | 7 / 3 | 0.344 | n/a |
| ensemble_select | closed_book | secondary | 12 | +0.094 | [-0.177, +0.365] | 5 / 4 | 1.000 | n/a |

## Paired comparisons (DeepSeek-V4-Pro; unit = mean of 2 samples)

| A | B | Role | Units | Mean diff | 95% CI | Papers A higher / B higher | Sign p | Holm p |
|---|---|---|---:|---:|---|---:|---:|---:|
| closed_book_fixed | text_chunks | primary | 12 | -0.052 | [-0.281, +0.198] | 3 / 6 | 0.508 | 1.00 |
| text_systemmatch | text_chunks | primary | 12 | -0.115 | [-0.292, +0.031] | 1 / 5 | 0.219 | 1.00 |
| card_systemmatch | text_chunks | primary | 12 | -0.125 | [-0.312, +0.052] | 3 / 6 | 0.508 | 1.00 |
| knowledge_first | text_chunks | primary | 12 | -0.042 | [-0.271, +0.208] | 4 / 6 | 0.754 | 1.00 |
| ensemble_select | text_chunks | primary | 12 | +0.000 | [-0.260, +0.271] | 5 / 6 | 1.000 | 1.00 |
| closed_book_fixed | closed_book | secondary | 12 | +0.031 | [-0.135, +0.250] | 4 / 3 | 1.000 | n/a |
| text_systemmatch | closed_book | secondary | 12 | -0.031 | [-0.198, +0.156] | 2 / 5 | 0.453 | n/a |
| card_systemmatch | closed_book | secondary | 12 | -0.042 | [-0.177, +0.104] | 3 / 4 | 1.000 | n/a |
| knowledge_first | closed_book | secondary | 12 | +0.042 | [-0.146, +0.260] | 4 / 4 | 1.000 | n/a |
| ensemble_select | closed_book | secondary | 12 | +0.083 | [-0.146, +0.344] | 5 / 5 | 1.000 | n/a |

## System-match appraisal

text_systemmatch: runs: 24, records_appraised_per_run: 6.71, verdicts: partially: 0.58, transfers: 0.21, does_not_transfer: 0.21, citations_of_records_judged_not_transferable: 0, citations: 75, card_systemmatch: runs: 24, records_appraised_per_run: 5.58, verdicts: partially: 0.57, does_not_transfer: 0.40, transfers: 0.04, citations_of_records_judged_not_transferable: 3, citations: 61

## Knowledge-first refinement

pairs: 24, intervention_word_overlap_with_draft: 1.00, mechanism_word_overlap_with_draft: 0.97, mean_change_vs_draft: -0.05, improved: 3, worse: 6

## Ensemble selection

selections: 24, fallbacks: 0, chosen_arm: text_systemmatch: 7, text_chunks: 1, card_systemmatch: 2, card: 6, knowledge_first: 6, closed_book_fixed: 2, chosen_position: C1: 8, C3: 4, C2: 8, C5: 3, C4: 1, selected_mean: 0.52, random_pick_mean: 0.51, oracle_best_mean: 0.86
