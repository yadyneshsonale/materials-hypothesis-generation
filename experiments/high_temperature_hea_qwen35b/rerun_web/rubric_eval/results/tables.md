# Extraction-rubric experiment

Integrity: expected_runs: 576, runs: 216, ok: 216, judged_gpt56: 216, judged_deepseek: 216, audited: 216, ceiling_files: 0, temporal_violations: 0, test_paper_leaks: 0, family_leaks: 0, invalid_citations: 0, stage_errors: audit: 0, cross_judge: 0, generate: 0, judge: 0, generators: trapi:Llama-3.3-70B-Instruct_5, verified: False

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
| cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| reconstructibility_mean | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| supportive_in_top20 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| strongly_supportive_in_top20 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| mean_pool_size | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Scores

| Metric | closed_book | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| reconstruction_gpt56 | 0.60 | 0.48 | n/a | 0.45 | n/a | n/a | n/a | n/a |
| reconstruction_gpt56_by_sample | 1: 0.60, 2: 0.60 | 1: 0.47, 2: 0.48 | 1: n/a, 2: n/a | 1: 0.48, 2: 0.42 | 1: n/a, 2: n/a | 1: n/a, 2: n/a | 1: n/a, 2: n/a | 1: n/a, 2: n/a |
| reconstruction_deepseek | 0.28 | 0.28 | n/a | 0.27 | n/a | n/a | n/a | n/a |
| overall_gpt56 | 1.11 | 1.10 | n/a | 1.12 | n/a | n/a | n/a | n/a |
| hard_failure_rate | 0.53 | 0.78 | n/a | 0.67 | n/a | n/a | n/a | n/a |
| sample_to_sample_abs_diff | 0.17 | 0.26 | n/a | 0.13 | n/a | n/a | n/a | n/a |
| classifications | unsupported: 58, plausible_alternative: 7, partial_reconstruction: 7 | unsupported: 34, plausible_alternative: 34, partial_reconstruction: 4 | n/a | unsupported: 42, plausible_alternative: 27, partial_reconstruction: 3 | n/a | n/a | n/a | n/a |
| failed | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Reconstruction by query level (GPT-5.6)

| Level | closed_book | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| broad | 0.62 | 0.33 | n/a | 0.34 | n/a | n/a | n/a | n/a |
| problem_constrained | 0.55 | 0.64 | n/a | 0.53 | n/a | n/a | n/a | n/a |
| expert_context | 0.62 | 0.46 | n/a | 0.47 | n/a | n/a | n/a | n/a |

## Judge dimensions (GPT-5.6, mean over runs)

| Dimension | closed_book | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| problem_alignment | 2.79 | 2.40 | n/a | 2.57 | n/a | n/a | n/a | n/a |
| intervention_reconstruction | 0.28 | 0.15 | n/a | 0.18 | n/a | n/a | n/a | n/a |
| condition_agreement | 0.54 | 0.51 | n/a | 0.44 | n/a | n/a | n/a | n/a |
| mechanism_agreement | 0.65 | 0.43 | n/a | 0.43 | n/a | n/a | n/a | n/a |
| outcome_agreement | 0.93 | 0.81 | n/a | 0.74 | n/a | n/a | n/a | n/a |
| baseline_quality | 1.94 | 1.75 | n/a | 1.96 | n/a | n/a | n/a | n/a |
| boundary_quality | 0.99 | 0.83 | n/a | 0.86 | n/a | n/a | n/a | n/a |
| experiment_discriminability | 1.79 | 1.60 | n/a | 1.69 | n/a | n/a | n/a | n/a |
| evidence_validity | 0.03 | 1.31 | n/a | 1.03 | n/a | n/a | n/a | n/a |
| novelty | 1.21 | 1.24 | n/a | 1.32 | n/a | n/a | n/a | n/a |

## Context and process (why)

| Metric | closed_book | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| packed_records | 0 | 14.31 | n/a | 7.89 | n/a | n/a | n/a | n/a |
| packed_chars | 0 | 15913.69 | n/a | 15721.47 | n/a | n/a | n/a | n/a |
| packed_papers | 0 | 11.14 | n/a | 7.89 | n/a | n/a | n/a | n/a |
| supportive_records_in_context | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| citations_per_hypothesis | 0.00 | 2.60 | n/a | 2.28 | n/a | n/a | n/a | n/a |
| claim_entailed_rate | 0.00 | 0.17 | n/a | 0.17 | n/a | n/a | n/a | n/a |
| claim_supported_rate | 0.00 | 0.57 | n/a | 0.55 | n/a | n/a | n/a | n/a |
| cross_system_support_rate | n/a | 0.39 | n/a | 0.50 | n/a | n/a | n/a | n/a |
| mechanism_transferred_without_justification | 0.00 | 0.60 | n/a | 0.69 | n/a | n/a | n/a | n/a |
| complete_chain_rate | 0.47 | 0.17 | n/a | 0.19 | n/a | n/a | n/a | n/a |
| contradictions_per_hypothesis | 0.22 | 0.36 | n/a | 0.36 | n/a | n/a | n/a | n/a |
| falsifiability | 0.75 | 0.73 | n/a | 0.70 | n/a | n/a | n/a | n/a |
| specificity | 0.17 | 0.17 | n/a | 0.20 | n/a | n/a | n/a | n/a |
| hedges_per_hypothesis | 0.07 | 0.01 | n/a | 0.11 | n/a | n/a | n/a | n/a |

## Paired comparisons (gpt56, unit = mean of 2 samples, papers bootstrap)

| A | B | Role | Units | Mean diff | 95% CI | Papers A higher / B higher | Sign p | Holm p |
|---|---|---|---:|---:|---|---:|---:|---:|
| card | text_chunks | primary | 36 | -0.028 | [-0.097, +0.045] | 5 / 5 | 1.000 | 1.00 |
| closed_book | text_chunks | secondary | 36 | +0.125 | [+0.007, +0.240] | 8 / 2 | 0.109 | n/a |
| closed_book | text_chunks | best_vs_other | 36 | +0.125 | [+0.007, +0.240] | 8 / 2 | 0.109 | n/a |
| closed_book | card | best_vs_other | 36 | +0.153 | [+0.038, +0.285] | 8 / 2 | 0.109 | n/a |

## Paired comparisons (deepseek, unit = mean of 2 samples, papers bootstrap)

| A | B | Role | Units | Mean diff | 95% CI | Papers A higher / B higher | Sign p | Holm p |
|---|---|---|---:|---:|---|---:|---:|---:|
| card | text_chunks | primary | 36 | -0.010 | [-0.111, +0.101] | 4 / 6 | 0.754 | 1.00 |
| closed_book | text_chunks | secondary | 36 | -0.007 | [-0.101, +0.090] | 4 / 6 | 0.754 | n/a |
| text_chunks | closed_book | best_vs_other | 36 | +0.007 | [-0.090, +0.101] | 6 / 4 | 0.754 | n/a |
| text_chunks | card | best_vs_other | 36 | +0.010 | [-0.101, +0.111] | 6 / 4 | 0.754 | n/a |

Ranking GPT-5.6: closed_book, text_chunks, v2_units, card, effects, mechanisms, gaps, mixed.
Ranking DeepSeek-V4-Pro: text_chunks, closed_book, v2_units, card, effects, mechanisms, gaps, mixed.
Kendall tau between the two rankings: 0.04.
