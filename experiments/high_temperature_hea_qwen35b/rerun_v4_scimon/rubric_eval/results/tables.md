# Extraction-rubric experiment

Integrity: expected_runs: 192, runs: 192, ok: 192, judged_gpt56: 192, judged_deepseek: 192, audited: 192, ceiling_files: 84, temporal_violations: 0, test_paper_leaks: 0, family_leaks: 0, invalid_citations: 0, stage_errors: audit: 0, ceiling: 0, cross_judge: 0, generate: 0, judge: 0, generators: trapi:Llama-3.3-70B-Instruct_5, verified: True

## Extraction

| Metric | card | effects | mechanisms | gaps |
|---|---:|---:|---:|---:|
| papers | 50 | 50 | 50 | 50 |
| windows | 55 | 55 | 55 | 55 |
| records | 55 | 609 | 423 | 426 |
| records_per_paper | 1.10 | 12.18 | 8.46 | 8.52 |
| proposed_items | 55 | 626 | 433 | 429 |
| kept_rate | 1.00 | 0.97 | 0.98 | 0.99 |
| dropped_no_valid_quote | 0 | 16 | 9 | 3 |
| dropped_empty | 0 | 0 | 0 | 0 |
| dropped_malformed | 0 | 1 | 1 | 0 |
| valid_quotes_per_kept_item | 2.67 | 2.62 | 2.70 | 2.70 |
| quote_validity_of_kept_items | 0.90 | 0.90 | 0.91 | 0.95 |
| mean_record_chars | 2945.82 | 789.13 | 1029.75 | 460.10 |
| compression_vs_source | 0.09 | 0.28 | 0.25 | 0.11 |

## Evidence ceiling per representation

| Metric | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|
| cases | 12 | 12 | 12 | 12 | 12 | 12 | 12 |
| reconstructibility_mean | 1.25 | 1.25 | 1.42 | 1.33 | 1.25 | 1.17 | 1.33 |
| supportive_in_top20 | 13.33 | 15.25 | 14.58 | 15.58 | 16.17 | 12.75 | 16.92 |
| strongly_supportive_in_top20 | 2.83 | 1.92 | 2.08 | 3.92 | 3.50 | 2.17 | 4.75 |
| mean_pool_size | 259.92 | 249.92 | 46.33 | 508.17 | 357.25 | 362.42 | 1227.83 |

## Scores

| Metric | closed_book | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| reconstruction_gpt56 | 0.43 | 0.44 | 0.43 | 0.46 | 0.31 | 0.40 | 0.44 | 0.39 |
| reconstruction_gpt56_by_sample | 1: 0.40, 2: 0.46 | 1: 0.56, 2: 0.31 | 1: 0.44, 2: 0.42 | 1: 0.46, 2: 0.46 | 1: 0.31, 2: 0.31 | 1: 0.38, 2: 0.42 | 1: 0.40, 2: 0.48 | 1: 0.42, 2: 0.35 |
| reconstruction_deepseek | 0.20 | 0.28 | 0.15 | 0.12 | 0.20 | 0.18 | 0.14 | 0.16 |
| overall_gpt56 | 0.62 | 0.82 | 0.77 | 0.89 | 0.78 | 0.96 | 0.73 | 0.92 |
| hard_failure_rate | 0.67 | 0.58 | 0.83 | 0.75 | 0.83 | 0.83 | 0.75 | 0.67 |
| sample_to_sample_abs_diff | 0.19 | 0.33 | 0.10 | 0.17 | 0.04 | 0.12 | 0.21 | 0.15 |
| classifications | unsupported: 22, partial_reconstruction: 2 | plausible_alternative: 6, unsupported: 14, partial_reconstruction: 4 | plausible_alternative: 5, unsupported: 16, partial_reconstruction: 3 | plausible_alternative: 7, unsupported: 13, partial_reconstruction: 4 | plausible_alternative: 7, unsupported: 16, partial_reconstruction: 1 | plausible_alternative: 8, unsupported: 16 | unsupported: 17, plausible_alternative: 5, partial_reconstruction: 2 | plausible_alternative: 6, unsupported: 17, partial_reconstruction: 1 |
| failed | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Reconstruction by query level (GPT-5.6)

| Level | closed_book | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| scimon | 0.43 | 0.44 | 0.43 | 0.46 | 0.31 | 0.40 | 0.44 | 0.39 |

## Judge dimensions (GPT-5.6, mean over runs)

| Dimension | closed_book | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| problem_alignment | 1.67 | 2.00 | 1.75 | 1.71 | 1.71 | 1.79 | 1.71 | 1.75 |
| intervention_reconstruction | 0.29 | 0.25 | 0.25 | 0.58 | 0.25 | 0.12 | 0.33 | 0.21 |
| condition_agreement | 0.42 | 0.33 | 0.29 | 0.25 | 0.17 | 0.25 | 0.38 | 0.25 |
| mechanism_agreement | 0.29 | 0.50 | 0.46 | 0.38 | 0.29 | 0.50 | 0.33 | 0.42 |
| outcome_agreement | 0.71 | 0.67 | 0.71 | 0.62 | 0.54 | 0.71 | 0.71 | 0.67 |
| baseline_quality | 0.79 | 0.71 | 0.67 | 0.83 | 0.67 | 0.83 | 0.33 | 0.88 |
| boundary_quality | 0.46 | 0.42 | 0.54 | 0.54 | 0.54 | 1.04 | 0.50 | 0.96 |
| experiment_discriminability | 1.17 | 1.21 | 1.38 | 1.38 | 1.38 | 1.62 | 1.42 | 1.46 |
| evidence_validity | 0.38 | 1.29 | 0.79 | 1.42 | 1.42 | 1.58 | 0.75 | 1.54 |
| novelty | 0.08 | 0.79 | 0.83 | 1.17 | 0.83 | 1.17 | 0.83 | 1.04 |

## Context and process (why)

| Metric | closed_book | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| packed_records | 0 | 11.50 | 10.92 | 5.67 | 20.50 | 15.75 | 24.00 | 21.50 |
| packed_chars | 0 | 15928.92 | 15800.50 | 15561.50 | 15894.08 | 15827.75 | 11511.75 | 15910.50 |
| packed_papers | 0 | 9.75 | 8.92 | 5.58 | 14.00 | 11.50 | 16.50 | 13.50 |
| supportive_records_in_context | n/a | 1.08 | 1.75 | 2.50 | 1.92 | 1.42 | 0.92 | 0.92 |
| citations_per_hypothesis | 0.00 | 2.58 | 2.21 | 2.42 | 2.33 | 1.33 | 2.00 | 1.67 |
| claim_entailed_rate | 0.00 | 0.29 | 0.33 | 0.26 | 0.35 | 0.56 | 0.18 | 0.44 |
| claim_supported_rate | 0.00 | 0.59 | 0.59 | 0.47 | 0.61 | 0.78 | 0.43 | 0.71 |
| cross_system_support_rate | n/a | 0.17 | 0.25 | 0.18 | 0.31 | 0.19 | 0.14 | 0.24 |
| mechanism_transferred_without_justification | 0.00 | 0.21 | 0.25 | 0.29 | 0.38 | 0.38 | 0.08 | 0.42 |
| complete_chain_rate | 0.17 | 0.21 | 0.04 | 0.12 | 0.04 | 0.25 | 0.12 | 0.29 |
| contradictions_per_hypothesis | 0.17 | 0.04 | 0.17 | 0.04 | 0.04 | 0.08 | 0.12 | 0.08 |
| falsifiability | 0.66 | 0.76 | 0.73 | 0.68 | 0.78 | 0.79 | 0.78 | 0.73 |
| specificity | 0.00 | 0.10 | 0.00 | 0.35 | 0.24 | 0.39 | 0.07 | 0.31 |
| hedges_per_hypothesis | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.04 |

## Paired comparisons (gpt56, unit = mean of 2 samples, papers bootstrap)

| A | B | Role | Units | Mean diff | 95% CI | Papers A higher / B higher | Sign p | Holm p |
|---|---|---|---:|---:|---|---:|---:|---:|
| card | text_chunks | primary | 12 | +0.021 | [-0.167, +0.229] | 6 / 5 | 1.000 | 1.00 |
| effects | text_chunks | primary | 12 | -0.125 | [-0.281, +0.021] | 3 / 7 | 0.344 | 1.00 |
| mechanisms | text_chunks | primary | 12 | -0.042 | [-0.240, +0.135] | 6 / 6 | 1.000 | 1.00 |
| gaps | text_chunks | primary | 12 | +0.000 | [-0.146, +0.146] | 6 / 4 | 0.754 | 1.00 |
| mixed | text_chunks | primary | 12 | -0.052 | [-0.229, +0.104] | 6 / 4 | 0.754 | 1.00 |
| v2_units | text_chunks | secondary | 12 | -0.010 | [-0.135, +0.115] | 3 / 4 | 1.000 | n/a |
| closed_book | text_chunks | secondary | 12 | -0.010 | [-0.260, +0.250] | 7 / 5 | 0.774 | n/a |
| card | closed_book | best_vs_other | 12 | +0.031 | [-0.208, +0.312] | 4 / 4 | 1.000 | n/a |
| card | text_chunks | best_vs_other | 12 | +0.021 | [-0.167, +0.229] | 6 / 5 | 1.000 | n/a |
| card | v2_units | best_vs_other | 12 | +0.031 | [-0.229, +0.333] | 6 / 6 | 1.000 | n/a |
| card | effects | best_vs_other | 12 | +0.146 | [-0.062, +0.396] | 7 / 2 | 0.180 | n/a |
| card | mechanisms | best_vs_other | 12 | +0.062 | [-0.198, +0.344] | 6 / 6 | 1.000 | n/a |
| card | gaps | best_vs_other | 12 | +0.021 | [-0.167, +0.240] | 4 / 4 | 1.000 | n/a |
| card | mixed | best_vs_other | 12 | +0.073 | [-0.146, +0.323] | 7 / 3 | 0.344 | n/a |

## Paired comparisons (deepseek, unit = mean of 2 samples, papers bootstrap)

| A | B | Role | Units | Mean diff | 95% CI | Papers A higher / B higher | Sign p | Holm p |
|---|---|---|---:|---:|---|---:|---:|---:|
| card | text_chunks | primary | 12 | -0.156 | [-0.333, +0.031] | 1 / 7 | 0.070 | 0.35 |
| effects | text_chunks | primary | 12 | -0.083 | [-0.177, +0.021] | 2 / 6 | 0.289 | 0.88 |
| mechanisms | text_chunks | primary | 12 | -0.104 | [-0.312, +0.094] | 3 / 6 | 0.508 | 1.00 |
| gaps | text_chunks | primary | 12 | -0.146 | [-0.312, +0.000] | 2 / 4 | 0.688 | 1.00 |
| mixed | text_chunks | primary | 12 | -0.125 | [-0.260, -0.010] | 1 / 5 | 0.219 | 0.88 |
| v2_units | text_chunks | secondary | 12 | -0.135 | [-0.271, -0.021] | 1 / 5 | 0.219 | n/a |
| closed_book | text_chunks | secondary | 12 | -0.083 | [-0.240, +0.083] | 3 / 6 | 0.508 | n/a |
| text_chunks | closed_book | best_vs_other | 12 | +0.083 | [-0.083, +0.240] | 6 / 3 | 0.508 | n/a |
| text_chunks | v2_units | best_vs_other | 12 | +0.135 | [+0.021, +0.271] | 5 / 1 | 0.219 | n/a |
| text_chunks | card | best_vs_other | 12 | +0.156 | [-0.031, +0.333] | 7 / 1 | 0.070 | n/a |
| text_chunks | effects | best_vs_other | 12 | +0.083 | [-0.021, +0.177] | 6 / 2 | 0.289 | n/a |
| text_chunks | mechanisms | best_vs_other | 12 | +0.104 | [-0.094, +0.312] | 6 / 3 | 0.508 | n/a |
| text_chunks | gaps | best_vs_other | 12 | +0.146 | [+0.000, +0.312] | 4 / 2 | 0.688 | n/a |
| text_chunks | mixed | best_vs_other | 12 | +0.125 | [+0.010, +0.260] | 5 / 1 | 0.219 | n/a |

Ranking GPT-5.6: card, text_chunks, gaps, closed_book, v2_units, mechanisms, mixed, effects.
Ranking DeepSeek-V4-Pro: text_chunks, closed_book, effects, mechanisms, mixed, v2_units, gaps, card.
Kendall tau between the two rankings: -0.32.
