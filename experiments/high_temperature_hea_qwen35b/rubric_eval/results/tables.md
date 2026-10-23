# Extraction-rubric experiment

Integrity: expected_runs: 576, runs: 576, ok: 574, judged_gpt56: 574, judged_deepseek: 574, audited: 574, ceiling_files: 84, temporal_violations: 0, test_paper_leaks: 0, family_leaks: 0, invalid_citations: 0, stage_errors: audit: 0, ceiling: 0, cross_judge: 0, extract: 0, generate: 0, judge: 0, generators: openai:Qwen3.5-35B-A3B-Q4_K_M.gguf, verified: False

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
| reconstructibility_mean | 1.25 | 1.08 | 1.42 | 1.17 | 1.25 | 1.00 | 1.42 |
| supportive_in_top20 | 14.08 | 15.75 | 14.33 | 16.33 | 16.17 | 13.17 | 16.83 |
| strongly_supportive_in_top20 | 2.00 | 2.67 | 1.75 | 4.08 | 2.83 | 1.92 | 5.25 |
| mean_pool_size | 259.92 | 249.92 | 46.33 | 508.17 | 357.25 | 362.42 | 1227.83 |

## Scores

| Metric | closed_book | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| reconstruction_gpt56 | 1.65 | 1.56 | 1.52 | 1.52 | 1.51 | 1.46 | 1.48 | 1.39 |
| reconstruction_gpt56_by_sample | 1: 1.63, 2: 1.68 | 1: 1.61, 2: 1.50 | 1: 1.56, 2: 1.49 | 1: 1.50, 2: 1.55 | 1: 1.53, 2: 1.49 | 1: 1.44, 2: 1.47 | 1: 1.46, 2: 1.49 | 1: 1.39, 2: 1.39 |
| reconstruction_deepseek | 2.20 | 2.00 | 1.96 | 1.98 | 1.95 | 1.90 | 1.89 | 1.86 |
| overall_gpt56 | 1.95 | 1.90 | 1.87 | 1.85 | 1.88 | 1.87 | 1.85 | 1.81 |
| hard_failure_rate | 0.11 | 0.14 | 0.17 | 0.14 | 0.22 | 0.17 | 0.19 | 0.28 |
| sample_to_sample_abs_diff | 0.31 | 0.38 | 0.24 | 0.33 | 0.26 | 0.24 | 0.26 | 0.19 |
| classifications | unsupported: 23, partial_reconstruction: 36, plausible_alternative: 10, exact_reconstruction: 1 | plausible_alternative: 15, partial_reconstruction: 37, unsupported: 20 | plausible_alternative: 15, unsupported: 17, partial_reconstruction: 39, exact_reconstruction: 1 | unsupported: 24, partial_reconstruction: 35, plausible_alternative: 13 | unsupported: 30, partial_reconstruction: 34, plausible_alternative: 7, exact_reconstruction: 1 | unsupported: 26, partial_reconstruction: 33, plausible_alternative: 13 | unsupported: 22, partial_reconstruction: 34, plausible_alternative: 16 | unsupported: 27, partial_reconstruction: 32, plausible_alternative: 12, exact_reconstruction: 1 |
| failed | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Reconstruction by query level (GPT-5.6)

| Level | closed_book | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| broad | 0.77 | 0.67 | 0.58 | 0.74 | 0.59 | 0.55 | 0.58 | 0.54 |
| problem_constrained | 1.68 | 1.50 | 1.54 | 1.43 | 1.53 | 1.45 | 1.47 | 1.38 |
| expert_context | 2.44 | 2.50 | 2.44 | 2.41 | 2.42 | 2.37 | 2.38 | 2.25 |

## Judge dimensions (GPT-5.6, mean over runs)

| Dimension | closed_book | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| problem_alignment | 3.40 | 3.17 | 3.14 | 3.12 | 3.18 | 3.14 | 3.14 | 3.08 |
| intervention_reconstruction | 1.83 | 1.67 | 1.60 | 1.58 | 1.53 | 1.62 | 1.56 | 1.47 |
| condition_agreement | 1.47 | 1.35 | 1.31 | 1.35 | 1.33 | 1.26 | 1.26 | 1.26 |
| mechanism_agreement | 1.59 | 1.53 | 1.53 | 1.50 | 1.56 | 1.31 | 1.42 | 1.21 |
| outcome_agreement | 1.73 | 1.68 | 1.65 | 1.67 | 1.64 | 1.62 | 1.67 | 1.61 |
| baseline_quality | 2.33 | 2.14 | 2.06 | 2.07 | 2.18 | 2.07 | 2.17 | 1.99 |
| boundary_quality | 1.77 | 1.88 | 1.78 | 1.76 | 1.74 | 1.85 | 1.72 | 1.71 |
| experiment_discriminability | 2.37 | 2.38 | 2.33 | 2.39 | 2.39 | 2.43 | 2.44 | 2.42 |
| evidence_validity | 1.14 | 1.10 | 1.00 | 0.86 | 0.97 | 1.17 | 0.85 | 1.12 |
| novelty | 1.90 | 2.11 | 2.32 | 2.18 | 2.25 | 2.25 | 2.29 | 2.22 |

## Context and process (why)

| Metric | closed_book | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| packed_records | 0 | 13.08 | 10.86 | 5.86 | 18.92 | 15.14 | 24.00 | 17.67 |
| packed_chars | 0 | 15907.42 | 15837.81 | 15554.94 | 15916.08 | 15778.92 | 11925.47 | 15903.83 |
| packed_papers | 0 | 11.22 | 8.69 | 5.67 | 11.39 | 10.67 | 16.14 | 11.28 |
| supportive_records_in_context | n/a | 4.03 | 3.56 | 3.67 | 3.94 | 4.14 | 3.97 | 2.61 |
| citations_per_hypothesis | 0.00 | 3.88 | 4.07 | 2.46 | 5.08 | 4.83 | 4.82 | 5.26 |
| claim_entailed_rate | 0.00 | 0.11 | 0.11 | 0.08 | 0.13 | 0.17 | 0.10 | 0.16 |
| claim_supported_rate | 0.00 | 0.38 | 0.39 | 0.27 | 0.38 | 0.46 | 0.31 | 0.47 |
| cross_system_support_rate | n/a | 0.61 | 0.59 | 0.61 | 0.57 | 0.68 | 0.71 | 0.66 |
| mechanism_transferred_without_justification | 0.00 | 0.58 | 0.54 | 0.47 | 0.65 | 0.65 | 0.49 | 0.75 |
| complete_chain_rate | 0.66 | 0.60 | 0.60 | 0.67 | 0.58 | 0.43 | 0.67 | 0.36 |
| contradictions_per_hypothesis | 0.64 | 1.08 | 1.03 | 1.12 | 1.11 | 1.18 | 0.96 | 1.19 |
| falsifiability | 0.82 | 0.86 | 0.89 | 0.87 | 0.90 | 0.90 | 0.88 | 0.91 |
| specificity | 0.47 | 0.60 | 0.61 | 0.63 | 0.61 | 0.61 | 0.51 | 0.61 |
| hedges_per_hypothesis | 0.07 | 0.04 | 0.03 | 0.11 | 0.07 | 0.07 | 0.06 | 0.03 |

## Paired comparisons (gpt56, unit = mean of 2 samples, papers bootstrap)

| A | B | Role | Units | Mean diff | 95% CI | Papers A higher / B higher | Sign p | Holm p |
|---|---|---|---:|---:|---|---:|---:|---:|
| card | text_chunks | primary | 36 | -0.031 | [-0.135, +0.062] | 6 / 6 | 1.000 | 1.00 |
| effects | text_chunks | primary | 36 | -0.042 | [-0.156, +0.059] | 6 / 5 | 1.000 | 1.00 |
| mechanisms | text_chunks | primary | 36 | -0.101 | [-0.215, +0.007] | 4 / 8 | 0.388 | 1.00 |
| gaps | text_chunks | primary | 36 | -0.080 | [-0.212, +0.045] | 3 / 8 | 0.227 | 0.91 |
| mixed | text_chunks | primary | 36 | -0.167 | [-0.247, -0.087] | 2 / 10 | 0.039 | 0.19 |
| v2_units | text_chunks | secondary | 36 | -0.035 | [-0.122, +0.056] | 3 / 8 | 0.227 | n/a |
| closed_book | text_chunks | secondary | 35 | +0.064 | [-0.061, +0.191] | 7 / 4 | 0.549 | n/a |
| closed_book | text_chunks | best_vs_other | 35 | +0.064 | [-0.061, +0.191] | 7 / 4 | 0.549 | n/a |
| closed_book | v2_units | best_vs_other | 35 | +0.101 | [-0.007, +0.215] | 7 / 5 | 0.774 | n/a |
| closed_book | card | best_vs_other | 35 | +0.092 | [+0.000, +0.196] | 6 / 5 | 1.000 | n/a |
| closed_book | effects | best_vs_other | 35 | +0.109 | [+0.010, +0.212] | 9 / 2 | 0.065 | n/a |
| closed_book | mechanisms | best_vs_other | 35 | +0.163 | [+0.049, +0.295] | 9 / 2 | 0.065 | n/a |
| closed_book | gaps | best_vs_other | 35 | +0.141 | [+0.035, +0.245] | 8 / 3 | 0.227 | n/a |
| closed_book | mixed | best_vs_other | 35 | +0.224 | [+0.130, +0.333] | 11 / 0 | 0.001 | n/a |

## Paired comparisons (deepseek, unit = mean of 2 samples, papers bootstrap)

| A | B | Role | Units | Mean diff | 95% CI | Papers A higher / B higher | Sign p | Holm p |
|---|---|---|---:|---:|---|---:|---:|---:|
| card | text_chunks | primary | 36 | -0.017 | [-0.156, +0.132] | 6 / 6 | 1.000 | 1.00 |
| effects | text_chunks | primary | 36 | -0.045 | [-0.132, +0.042] | 4 / 6 | 0.754 | 1.00 |
| mechanisms | text_chunks | primary | 36 | -0.094 | [-0.226, +0.045] | 3 / 9 | 0.146 | 0.73 |
| gaps | text_chunks | primary | 36 | -0.104 | [-0.288, +0.069] | 4 / 7 | 0.549 | 1.00 |
| mixed | text_chunks | primary | 36 | -0.139 | [-0.271, -0.007] | 4 / 8 | 0.388 | 1.00 |
| v2_units | text_chunks | secondary | 36 | -0.038 | [-0.170, +0.097] | 4 / 8 | 0.388 | n/a |
| closed_book | text_chunks | secondary | 35 | +0.153 | [+0.031, +0.271] | 8 / 4 | 0.388 | n/a |
| closed_book | text_chunks | best_vs_other | 35 | +0.153 | [+0.031, +0.271] | 8 / 4 | 0.388 | n/a |
| closed_book | v2_units | best_vs_other | 35 | +0.196 | [+0.052, +0.351] | 7 / 4 | 0.549 | n/a |
| closed_book | card | best_vs_other | 35 | +0.168 | [+0.007, +0.337] | 8 / 4 | 0.388 | n/a |
| closed_book | effects | best_vs_other | 35 | +0.194 | [+0.097, +0.292] | 11 / 1 | 0.006 | n/a |
| closed_book | mechanisms | best_vs_other | 35 | +0.248 | [+0.064, +0.448] | 9 / 3 | 0.146 | n/a |
| closed_book | gaps | best_vs_other | 35 | +0.259 | [+0.104, +0.417] | 10 / 2 | 0.039 | n/a |
| closed_book | mixed | best_vs_other | 35 | +0.288 | [+0.108, +0.479] | 8 / 3 | 0.227 | n/a |

Ranking GPT-5.6: closed_book, text_chunks, card, v2_units, effects, gaps, mechanisms, mixed.
Ranking DeepSeek-V4-Pro: closed_book, text_chunks, card, v2_units, effects, mechanisms, gaps, mixed.
Kendall tau between the two rankings: 0.93.
