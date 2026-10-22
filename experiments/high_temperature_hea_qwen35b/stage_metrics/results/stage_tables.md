# Intermediate-stage metrics

## 1. Query stage (diagnostic: inferability needs the hidden target)

| Metric | broad | problem_constrained | expert_context |
|---|---:|---:|---:|
| inferability_mean | 0.61 | 1.05 | 1.55 |
| intervention_stated_or_implied | 0.33 | 0.54 | 0.83 |
| mechanism_stated_or_implied | 0.38 | 0.58 | 0.92 |
| outcome_stated_or_implied | 0.46 | 0.54 | 0.71 |
| answer_space | many: 11, few: 1 | many: 12 | few: 6, many: 5, single: 1 |

Spearman, query inferability vs reconstruction (all units): 0.82.

Cross-method intervention diversity (mean pairwise embedding distance between the methods' interventions for the same unit): broad 0.20, problem_constrained 0.17, expert_context 0.11.

## 2–3. Retrieval and reading

| Metric | text_oneshot | v2_oneshot | tool_agent | resample | tool_agent_kg |
|---|---:|---:|---:|---:|---:|
| units | 36 | 36 | 36 | 36 | 36 |
| supportive_recall | 0.27 | 0.14 | 0.23 | 0.21 | 0.18 |
| supportive_read_recall | 0.27 | 0.14 | 0.06 | 0.06 | 0.07 |
| units_with_supportive_hit | 1.00 | 0.81 | 1.00 | 0.94 | 0.97 |
| steps_to_first_supportive_hit | n/a | n/a | 2.69 | 2.79 | 3.06 |
| missed_opportunity | n/a | n/a | 0.67 | 0.64 | 0.56 |
| search_novelty | n/a | n/a | 0.24 | 0.25 | 0.27 |
| result_relevance_to_query | 0.64 | 0.65 | 0.63 | 0.63 | 0.64 |
| distinct_papers_seen | 11.81 | 10.86 | 11.31 | 10.61 | 9.14 |
| distinct_section_kinds_seen | 3.36 | 1.00 | 6.86 | 6.64 | 6.11 |
| paging_waste | n/a | n/a | 0.30 | 0.23 | 0.23 |
| distinct_reads_per_call | n/a | n/a | 0.30 | 0.35 | 0.34 |
| evidence_utilisation | 0.30 | 0.32 | 0.76 | 0.73 | 0.81 |
| spearman_recall_vs_score | 0.41 | 0.37 | 0.41 | 0.33 | 0.48 |

Replay consistency: 108 of 108 tool runs reproduce exactly the stored accessed records.

## 4. Grounding (target-free)

| Metric | closed_book | text_oneshot | v2_oneshot | tool_agent | resample | tool_agent_kg | self_revise | critique |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| audited | 35 | 36 | 36 | 36 | 36 | 36 | 36 | 36 |
| claims_per_hypothesis | 17.49 | 19.42 | 19.58 | 19.56 | 19.75 | 19.61 | 19.44 | 18.94 |
| claim_entailed_rate | 0.00 | 0.12 | 0.12 | 0.12 | 0.13 | 0.13 | 0.12 | 0.15 |
| claim_supported_rate | 0.00 | 0.41 | 0.40 | 0.33 | 0.36 | 0.39 | 0.34 | 0.38 |
| citation_precision | n/a | 0.88 | 0.83 | 0.98 | 0.86 | 0.88 | 0.93 | 0.94 |
| cross_system_support_rate | n/a | 0.61 | 0.57 | 0.53 | 0.52 | 0.52 | 0.48 | 0.52 |
| numbers_traced_to_evidence | 0.00 | 0.56 | 0.68 | 0.63 | 0.57 | 0.58 | 0.85 | 0.85 |

## 5. Reasoning (target-free)

| Metric | closed_book | text_oneshot | v2_oneshot | tool_agent | resample | tool_agent_kg | self_revise | critique |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| causal_chain_score | 0.84 | 0.91 | 0.92 | 0.91 | 0.91 | 0.92 | 0.93 | 0.74 |
| complete_chain_rate | 0.57 | 0.64 | 0.61 | 0.58 | 0.64 | 0.67 | 0.69 | 0.33 |
| contradictions_per_hypothesis | 0.60 | 0.89 | 1.17 | 0.75 | 0.81 | 0.94 | 0.78 | 0.58 |
| units_with_contradiction | 0.43 | 0.53 | 0.64 | 0.50 | 0.47 | 0.50 | 0.47 | 0.39 |
| mechanism_source | not_from_evidence: 1.00 | transferred_without_justification: 0.56, transferred_with_justification: 0.17, not_from_evidence: 0.28 | transferred_without_justification: 0.44, not_from_evidence: 0.39, transferred_with_justification: 0.14, same_system_evidence: 0.03 | not_from_evidence: 0.47, transferred_with_justification: 0.03, transferred_without_justification: 0.42, same_system_evidence: 0.08 | transferred_without_justification: 0.39, not_from_evidence: 0.44, same_system_evidence: 0.17 | transferred_without_justification: 0.50, not_from_evidence: 0.28, same_system_evidence: 0.19, transferred_with_justification: 0.03 | not_from_evidence: 0.44, transferred_without_justification: 0.44, same_system_evidence: 0.11 | not_from_evidence: 0.50, transferred_without_justification: 0.39, same_system_evidence: 0.11 |
| transferred_without_justification | 0.00 | 0.56 | 0.44 | 0.42 | 0.39 | 0.50 | 0.44 | 0.39 |

## 5b. Physical checks on extracted composition claims

| Metric | closed_book | text_oneshot | v2_oneshot | tool_agent | resample | tool_agent_kg | self_revise | critique |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| density_checks | n/a | unverifiable: 3 | unverifiable: 5 | inconsistent: 1, unverifiable: 1 | consistent: 1, unverifiable: 2 | inconsistent: 3, unverifiable: 2 | inconsistent: 1, unverifiable: 2 | inconsistent: 1, unverifiable: 2 |
| phase_checks | n/a | consistent: 2, unverifiable: 1 | unverifiable: 3, consistent: 2 | unverifiable: 2 | consistent: 1, unverifiable: 2 | consistent: 3, inconsistent: 1, unverifiable: 1 | unverifiable: 3 | consistent: 2, unverifiable: 1 |

## 6. Hypothesis form

| Metric | closed_book | text_oneshot | v2_oneshot | tool_agent | resample | tool_agent_kg | self_revise | critique |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| hedges_per_hypothesis | 0.06 | 0.03 | 0.03 | 0.14 | 0.08 | 0.11 | 0.22 | 3.47 |
| hedges_per_claim | 0.01 | 0.00 | 0.00 | 0.01 | 0.00 | 0.01 | 0.01 | 0.19 |
| quantities_per_hypothesis | 3.20 | 5.39 | 5.89 | 6.03 | 6.31 | 6.31 | 6.03 | 4.83 |
| specificity_checklist | 0.41 | 0.62 | 0.61 | 0.69 | 0.64 | 0.64 | 0.67 | 0.65 |
| falsifiability_checklist | 0.79 | 0.89 | 0.91 | 0.83 | 0.81 | 0.85 | 0.83 | 0.69 |
| stated_uncertainty | 1.97 | 1.89 | 1.86 | 1.83 | 1.69 | 1.56 | 1.81 | 1.89 |
| calibration_spearman_uncertainty_vs_score | -0.15 | 0.09 | 0.09 | 0.13 | -0.24 | -0.02 | 0.14 | -0.02 |

## 6b. Sampling

| Metric | Value |
|---|---:|
| tool_agent_mean | 1.64 |
| resample_mean | 1.55 |
| best_of_2 | 1.75 |
| sample_intervention_distance | 0.12 |
| best_of_all_methods | 1.97 |
| oracle_gain_over_best_single_method | 0.33 |

## 7. Critique and revision

| Metric | self_revise | critique | resample_reference |
|---|---:|---:|---:|
| findings_reviewed | 0 | 306 | n/a |
| finding_validity | n/a | valid: 0.70, partly_valid: 0.20, invalid: 0.10 | n/a |
| finding_uptake | n/a | partly: 0.30, ignored: 0.31, addressed: 0.39 | n/a |
| finding_fix_type | n/a | hedged: 0.36, none: 0.35, corrected: 0.13, deleted: 0.16 | n/a |
| field_change_types | deleted: 7, rephrased: 6, hedged: 4, corrected: 3, new_claim: 1 | corrected: 49, hedged: 107, new_claim: 7, rephrased: 25, deleted: 23 | n/a |
| harm_rate_per_dimension | 0.09 | 0.20 | 0.24 |
| help_rate_per_dimension | 0.05 | 0.12 | 0.16 |
| citation_churn_per_unit | 0.42 | 0.78 | n/a |

## 8. Knowledge graph

| Metric | Value |
|---|---:|
| kg_lookups | 66 |
| kg_facts_read_or_cited_per_lookup | 0.23 |
| kg_fact_relevance_to_query | 0.48 |
| paper_result_relevance_to_query | 0.64 |
| searches_per_run_kg | 3.78 |
| searches_per_run_plain | 5.89 |
| supportive_recall_kg | 0.18 |
| supportive_recall_plain | 0.23 |

## 9. Judge reliability

| Metric | Value |
|---|---:|
| units_with_3_judgments | 287 |
| mean_within_unit_sd | 0.10 |
| mean_abs_diff_original_vs_rejudge | 0.15 |
| icc1_reconstruction | 0.96 |
| classification_identical_all_3 | 0.78 |
| generation_plus_judge_abs_diff_reference | 0.31 |

| Method | Original judge | Mean of 3 GPT-5.6 judgments | DeepSeek-V4-Pro judge |
|---|---:|---:|---:|
| closed_book | 1.56 | 1.59 | 2.16 |
| text_oneshot | 1.56 | 1.57 | 2.08 |
| v2_oneshot | 1.49 | 1.45 | 1.94 |
| tool_agent | 1.64 | 1.66 | 2.09 |
| resample | 1.55 | 1.55 | 1.96 |
| tool_agent_kg | 1.63 | 1.62 | 1.92 |
| self_revise | 1.60 | 1.65 | 2.16 |
| critique | 1.49 | 1.41 | 1.55 |

| Cross-judge metric | Value |
|---|---:|
| units | 287 |
| spearman_unit_scores | 0.90 |
| mean_difference_cross_minus_gpt | 0.42 |
| mean_abs_difference | 0.54 |
| kendall_tau_method_ranking | 0.32 |
| classification_agreement | 0.52 |

| Style feature | Spearman with reconstruction (all) | Mean within-level Spearman |
|---|---:|---:|
| length_chars | 0.01 | -0.12 |
| hedges | -0.02 | -0.04 |
| citations | -0.16 | -0.00 |
| quantities | -0.02 | -0.13 |

Pairwise position consistency: eval_v3 0.81, eval_v4_matkg 0.80.

## 10. Cost

| Metric | closed_book | text_oneshot | v2_oneshot | tool_agent | resample | tool_agent_kg | self_revise | critique |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| model_calls_per_unit | 1.00 | 1.00 | 1.00 | 11.83 | 11.67 | 11.58 | 12.89 | 15.86 |
| generation_seconds_per_unit | 33.49 | 51.63 | 54.64 | 76.53 | 135.62 | 185.84 | n/a | n/a |
| reconstruction_per_10_calls | 15.57 | 15.62 | 14.86 | 1.39 | 1.33 | 1.41 | 1.24 | 0.94 |

Counts: units: 288, judged: 287, audits: 287, inferability: 36, reviews: 72, retest_units: 287, cross_judged: 287.
