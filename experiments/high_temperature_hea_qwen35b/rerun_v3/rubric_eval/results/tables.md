# Extraction-rubric experiment

Integrity: expected_runs: 576, runs: 576, ok: 576, judged_gpt56: 576, judged_deepseek: 576, audited: 576, ceiling_files: 84, temporal_violations: 0, test_paper_leaks: 0, family_leaks: 0, invalid_citations: 0, stage_errors: audit: 0, ceiling: 0, cross_judge: 0, generate: 0, judge: 0, generators: trapi:Llama-3.3-70B-Instruct_5, verified: True

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
| reconstructibility_mean | 1.17 | 1.25 | 1.50 | 1.42 | 1.25 | 1.17 | 1.42 |
| supportive_in_top20 | 14.08 | 14.83 | 14.08 | 15.92 | 16.58 | 12.75 | 17.17 |
| strongly_supportive_in_top20 | 1.75 | 2.25 | 1.50 | 4.17 | 3.42 | 1.75 | 5.58 |
| mean_pool_size | 259.92 | 249.92 | 46.33 | 508.17 | 357.25 | 362.42 | 1227.83 |

## Scores

| Metric | closed_book | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| reconstruction_gpt56 | 0.60 | 0.47 | 0.38 | 0.48 | 0.46 | 0.42 | 0.45 | 0.40 |
| reconstruction_gpt56_by_sample | 1: 0.60, 2: 0.60 | 1: 0.49, 2: 0.45 | 1: 0.37, 2: 0.40 | 1: 0.49, 2: 0.46 | 1: 0.44, 2: 0.47 | 1: 0.40, 2: 0.45 | 1: 0.45, 2: 0.45 | 1: 0.41, 2: 0.39 |
| reconstruction_deepseek | 0.28 | 0.26 | 0.16 | 0.20 | 0.23 | 0.24 | 0.15 | 0.19 |
| overall_gpt56 | 1.11 | 1.03 | 0.94 | 1.05 | 1.00 | 1.10 | 1.00 | 0.99 |
| hard_failure_rate | 0.53 | 0.69 | 0.78 | 0.69 | 0.75 | 0.78 | 0.75 | 0.75 |
| sample_to_sample_abs_diff | 0.17 | 0.16 | 0.17 | 0.19 | 0.19 | 0.18 | 0.17 | 0.16 |
| classifications | unsupported: 58, plausible_alternative: 7, partial_reconstruction: 7 | unsupported: 48, plausible_alternative: 24 | unsupported: 56, plausible_alternative: 16 | unsupported: 52, plausible_alternative: 16, partial_reconstruction: 4 | unsupported: 52, plausible_alternative: 14, partial_reconstruction: 6 | plausible_alternative: 25, unsupported: 47 | unsupported: 64, plausible_alternative: 7, partial_reconstruction: 1 | unsupported: 56, plausible_alternative: 16 |
| failed | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Reconstruction by query level (GPT-5.6)

| Level | closed_book | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| broad | 0.62 | 0.51 | 0.31 | 0.39 | 0.33 | 0.47 | 0.45 | 0.40 |
| problem_constrained | 0.55 | 0.46 | 0.45 | 0.51 | 0.55 | 0.38 | 0.47 | 0.39 |
| expert_context | 0.62 | 0.44 | 0.39 | 0.53 | 0.49 | 0.43 | 0.44 | 0.42 |

## Judge dimensions (GPT-5.6, mean over runs)

| Dimension | closed_book | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| problem_alignment | 2.79 | 2.29 | 2.15 | 2.29 | 2.04 | 2.36 | 2.38 | 2.06 |
| intervention_reconstruction | 0.28 | 0.11 | 0.04 | 0.21 | 0.38 | 0.03 | 0.10 | 0.04 |
| condition_agreement | 0.54 | 0.50 | 0.40 | 0.46 | 0.36 | 0.40 | 0.47 | 0.46 |
| mechanism_agreement | 0.65 | 0.56 | 0.39 | 0.47 | 0.33 | 0.44 | 0.40 | 0.35 |
| outcome_agreement | 0.93 | 0.71 | 0.69 | 0.76 | 0.76 | 0.82 | 0.83 | 0.75 |
| baseline_quality | 1.94 | 1.68 | 1.62 | 1.74 | 1.69 | 1.69 | 1.74 | 1.51 |
| boundary_quality | 0.99 | 0.76 | 0.79 | 0.86 | 0.67 | 1.04 | 0.88 | 0.88 |
| experiment_discriminability | 1.79 | 1.53 | 1.43 | 1.56 | 1.51 | 1.65 | 1.60 | 1.49 |
| evidence_validity | 0.03 | 1.08 | 0.81 | 0.75 | 0.94 | 1.11 | 0.47 | 1.12 |
| novelty | 1.21 | 1.12 | 1.10 | 1.44 | 1.31 | 1.44 | 1.12 | 1.29 |

## Context and process (why)

| Metric | closed_book | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| packed_records | 0 | 12.94 | 11.47 | 5.67 | 19.64 | 15.25 | 24.00 | 18.03 |
| packed_chars | 0 | 15895.42 | 15815.08 | 15443.56 | 15917.75 | 15836.81 | 11944.69 | 15906.92 |
| packed_papers | 0 | 11.31 | 9.33 | 5.47 | 12.33 | 10.94 | 16.42 | 11.64 |
| supportive_records_in_context | n/a | 2.97 | 2.03 | 2.47 | 1.75 | 2.19 | 2.19 | 1.08 |
| citations_per_hypothesis | 0.00 | 1.99 | 2.18 | 1.53 | 1.97 | 1.46 | 2.36 | 1.53 |
| claim_entailed_rate | 0.00 | 0.18 | 0.18 | 0.09 | 0.24 | 0.26 | 0.07 | 0.27 |
| claim_supported_rate | 0.00 | 0.54 | 0.55 | 0.32 | 0.55 | 0.66 | 0.29 | 0.65 |
| cross_system_support_rate | n/a | 0.49 | 0.49 | 0.51 | 0.47 | 0.47 | 0.52 | 0.40 |
| mechanism_transferred_without_justification | 0.00 | 0.61 | 0.53 | 0.18 | 0.56 | 0.82 | 0.39 | 0.71 |
| complete_chain_rate | 0.47 | 0.24 | 0.17 | 0.36 | 0.25 | 0.26 | 0.22 | 0.25 |
| contradictions_per_hypothesis | 0.22 | 0.22 | 0.21 | 0.24 | 0.22 | 0.21 | 0.15 | 0.17 |
| falsifiability | 0.75 | 0.66 | 0.68 | 0.70 | 0.68 | 0.70 | 0.70 | 0.67 |
| specificity | 0.17 | 0.12 | 0.10 | 0.15 | 0.23 | 0.18 | 0.12 | 0.23 |
| hedges_per_hypothesis | 0.07 | 0.08 | 0.11 | 0.06 | 0.12 | 0.07 | 0.10 | 0.04 |

## Paired comparisons (gpt56, unit = mean of 2 samples, papers bootstrap)

| A | B | Role | Units | Mean diff | 95% CI | Papers A higher / B higher | Sign p | Holm p |
|---|---|---|---:|---:|---|---:|---:|---:|
| card | text_chunks | primary | 36 | +0.007 | [-0.080, +0.097] | 7 / 5 | 0.774 | 1.00 |
| effects | text_chunks | primary | 36 | -0.010 | [-0.135, +0.146] | 4 / 7 | 0.549 | 1.00 |
| mechanisms | text_chunks | primary | 36 | -0.045 | [-0.160, +0.035] | 5 / 3 | 0.727 | 1.00 |
| gaps | text_chunks | primary | 36 | -0.017 | [-0.122, +0.069] | 5 / 5 | 1.000 | 1.00 |
| mixed | text_chunks | primary | 36 | -0.069 | [-0.188, +0.031] | 4 / 4 | 1.000 | 1.00 |
| v2_units | text_chunks | secondary | 36 | -0.087 | [-0.170, -0.007] | 3 / 8 | 0.227 | n/a |
| closed_book | text_chunks | secondary | 36 | +0.132 | [+0.024, +0.243] | 10 / 2 | 0.039 | n/a |
| closed_book | text_chunks | best_vs_other | 36 | +0.132 | [+0.024, +0.243] | 10 / 2 | 0.039 | n/a |
| closed_book | v2_units | best_vs_other | 36 | +0.219 | [+0.111, +0.340] | 10 / 1 | 0.012 | n/a |
| closed_book | card | best_vs_other | 36 | +0.125 | [+0.049, +0.205] | 9 / 2 | 0.065 | n/a |
| closed_book | effects | best_vs_other | 36 | +0.142 | [-0.014, +0.278] | 10 / 2 | 0.039 | n/a |
| closed_book | mechanisms | best_vs_other | 36 | +0.177 | [+0.045, +0.333] | 10 / 2 | 0.039 | n/a |
| closed_book | gaps | best_vs_other | 36 | +0.149 | [+0.049, +0.257] | 9 / 2 | 0.065 | n/a |
| closed_book | mixed | best_vs_other | 36 | +0.201 | [+0.087, +0.333] | 10 / 2 | 0.039 | n/a |

## Paired comparisons (deepseek, unit = mean of 2 samples, papers bootstrap)

| A | B | Role | Units | Mean diff | 95% CI | Papers A higher / B higher | Sign p | Holm p |
|---|---|---|---:|---:|---|---:|---:|---:|
| card | text_chunks | primary | 36 | -0.059 | [-0.188, +0.059] | 5 / 6 | 1.000 | 1.00 |
| effects | text_chunks | primary | 36 | -0.028 | [-0.181, +0.125] | 7 / 4 | 0.549 | 1.00 |
| mechanisms | text_chunks | primary | 36 | -0.014 | [-0.115, +0.080] | 4 / 5 | 1.000 | 1.00 |
| gaps | text_chunks | primary | 36 | -0.111 | [-0.215, -0.024] | 2 / 7 | 0.180 | 0.90 |
| mixed | text_chunks | primary | 36 | -0.066 | [-0.184, +0.038] | 5 / 5 | 1.000 | 1.00 |
| v2_units | text_chunks | secondary | 36 | -0.097 | [-0.208, +0.000] | 2 / 8 | 0.109 | n/a |
| closed_book | text_chunks | secondary | 36 | +0.021 | [-0.128, +0.153] | 7 / 4 | 0.549 | n/a |
| closed_book | text_chunks | best_vs_other | 36 | +0.021 | [-0.128, +0.153] | 7 / 4 | 0.549 | n/a |
| closed_book | v2_units | best_vs_other | 36 | +0.118 | [+0.035, +0.212] | 8 / 2 | 0.109 | n/a |
| closed_book | card | best_vs_other | 36 | +0.080 | [-0.062, +0.222] | 8 / 4 | 0.388 | n/a |
| closed_book | effects | best_vs_other | 36 | +0.049 | [-0.118, +0.188] | 8 / 3 | 0.227 | n/a |
| closed_book | mechanisms | best_vs_other | 36 | +0.035 | [-0.132, +0.201] | 6 / 4 | 0.754 | n/a |
| closed_book | gaps | best_vs_other | 36 | +0.132 | [+0.035, +0.240] | 9 / 2 | 0.065 | n/a |
| closed_book | mixed | best_vs_other | 36 | +0.087 | [-0.007, +0.191] | 6 / 4 | 0.754 | n/a |

Ranking GPT-5.6: closed_book, card, text_chunks, effects, gaps, mechanisms, mixed, v2_units.
Ranking DeepSeek-V4-Pro: closed_book, text_chunks, mechanisms, effects, card, mixed, v2_units, gaps.
Kendall tau between the two rankings: 0.50.
