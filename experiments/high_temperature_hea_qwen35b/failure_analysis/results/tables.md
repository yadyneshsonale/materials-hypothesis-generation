## Overview

| Method | Judged | Failed gen. | Reconstruction | Overall | Hard failure (≤0.5) | Exact / partial / plausible / unsupported | Hedges per hypothesis |
|---|---:|---:|---:|---:|---:|---|---:|
| closed_book | 35 | 1 | 1.56 | 1.89 | 17% | 0 / 21 / 5 / 9 | 0.06 |
| text_oneshot | 36 | 0 | 1.56 | 1.90 | 11% | 1 / 19 / 7 / 9 | 0.03 |
| v2_oneshot | 36 | 0 | 1.49 | 1.85 | 17% | 0 / 19 / 5 / 12 | 0.03 |
| tool_agent | 36 | 0 | 1.64 | 1.84 | 14% | 1 / 20 / 6 / 9 | 0.14 |
| resample | 36 | 0 | 1.55 | 1.82 | 14% | 0 / 18 / 7 / 11 | 0.08 |
| tool_agent_kg | 36 | 0 | 1.63 | 1.85 | 22% | 0 / 21 / 8 / 7 | 0.11 |
| self_revise | 36 | 0 | 1.60 | 1.79 | 17% | 1 / 19 / 7 / 9 | 0.22 |
| critique | 36 | 0 | 1.49 | 1.64 | 11% | 0 / 16 / 7 / 13 | 3.47 |

## Zero-score rate by dimension

| Dimension | closed_book | text_oneshot | v2_oneshot | tool_agent | resample | tool_agent_kg | self_revise | critique |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| problem_alignment | 3% | 0% | 0% | 3% | 0% | 0% | 0% | 3% |
| intervention_reconstruction | 20% | 25% | 22% | 14% | 17% | 22% | 14% | 11% |
| condition_agreement | 20% | 17% | 17% | 17% | 17% | 17% | 17% | 17% |
| mechanism_agreement | 20% | 14% | 8% | 8% | 19% | 14% | 19% | 19% |
| outcome_agreement | 20% | 11% | 11% | 8% | 17% | 14% | 11% | 17% |
| baseline_quality | 11% | 8% | 8% | 11% | 11% | 6% | 11% | 14% |
| boundary_quality | 11% | 8% | 11% | 8% | 11% | 3% | 11% | 19% |
| experiment_discriminability | 9% | 0% | 0% | 3% | 0% | 3% | 3% | 6% |
| evidence_validity | 11% | 14% | 11% | 22% | 31% | 25% | 33% | 25% |
| novelty | 9% | 0% | 0% | 0% | 0% | 0% | 3% | 6% |

## Fatal-error categories (share of each method's errors)

| Category | closed_book | text_oneshot | v2_oneshot | tool_agent | resample | tool_agent_kg | self_revise | critique |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| wrong_intervention | 12% | 14% | 13% | 11% | 10% | 9% | 14% | 12% |
| wrong_mechanism | 24% | 20% | 19% | 21% | 21% | 23% | 22% | 22% |
| wrong_outcome | 12% | 8% | 11% | 10% | 6% | 7% | 7% | 9% |
| wrong_baseline | 8% | 5% | 4% | 7% | 6% | 7% | 7% | 6% |
| wrong_conditions | 14% | 16% | 10% | 17% | 18% | 15% | 15% | 15% |
| physical_error | 6% | 5% | 7% | 4% | 3% | 2% | 2% | 1% |
| evidence_unsupported | 11% | 24% | 23% | 20% | 25% | 26% | 22% | 22% |
| evidence_contradicted | 0% | 1% | 1% | 2% | 2% | 2% | 1% | 1% |
| internal_inconsistency | 2% | 2% | 3% | 4% | 2% | 2% | 3% | 1% |
| untestable_or_vague | 12% | 6% | 8% | 4% | 6% | 7% | 8% | 12% |
| other | 1% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| errors per unit | 3.49 | 3.64 | 4.00 | 3.67 | 3.89 | 3.78 | 3.61 | 4.22 |

## Reconstruction by target type

| Target type (cases) | closed_book | text_oneshot | v2_oneshot | tool_agent | resample | tool_agent_kg | self_revise | critique |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| composition (1) | 1.50 | 1.33 | 1.58 | 1.67 | 1.25 | 1.75 | 1.50 | 1.58 |
| processing (6) | 1.43 | 1.50 | 1.40 | 1.64 | 1.53 | 1.57 | 1.56 | 1.33 |
| computational (4) | 1.65 | 1.60 | 1.48 | 1.54 | 1.54 | 1.65 | 1.56 | 1.52 |
| characterization (1) | 2.00 | 2.00 | 1.92 | 2.00 | 2.00 | 1.83 | 2.08 | 2.17 |

## Reconstruction by query level

| Level | closed_book | text_oneshot | v2_oneshot | tool_agent | resample | tool_agent_kg | self_revise | critique |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| broad | 0.75 | 0.79 | 0.73 | 0.79 | 0.79 | 0.69 | 0.75 | 0.96 |
| problem_constrained | 1.46 | 1.52 | 1.44 | 1.65 | 1.48 | 1.60 | 1.69 | 1.40 |
| expert_context | 2.40 | 2.38 | 2.29 | 2.48 | 2.38 | 2.60 | 2.35 | 2.10 |

## Reconstruction by paper

| Paper | Type | closed_book | text_oneshot | v2_oneshot | tool_agent | resample | tool_agent_kg | self_revise | critique |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| PMC10759803 | composition | 1.50 | 1.33 | 1.58 | 1.67 | 1.25 | 1.75 | 1.50 | 1.58 |
| PMC11077685 | processing | 0.92 | 0.83 | 1.17 | 1.00 | 1.08 | 1.17 | 0.92 | 0.92 |
| PMC11087546 | processing | 1.50 | 1.67 | 1.42 | 1.75 | 1.58 | 1.58 | 1.75 | 1.67 |
| PMC11355469 | computational | 1.75 | 1.33 | 1.33 | 1.08 | 1.42 | 1.50 | 1.00 | 1.50 |
| PMC11375216 | computational | 1.58 | 2.00 | 1.58 | 2.00 | 2.00 | 2.00 | 1.92 | 1.50 |
| PMC11375712 | processing | 2.25 | 1.42 | 1.17 | 1.75 | 1.58 | 1.50 | 1.67 | 1.17 |
| PMC11606917 | computational | 2.00 | 1.58 | 1.67 | 2.00 | 1.92 | 1.83 | 2.17 | 2.00 |
| PMC11775865 | characterization | 2.00 | 2.00 | 1.92 | 2.00 | 2.00 | 1.83 | 2.08 | 2.17 |
| PMC12029629 | computational | 1.25 | 1.50 | 1.33 | 1.08 | 0.83 | 1.25 | 1.17 | 1.08 |
| PMC12298864 | processing | 1.67 | 1.67 | 1.58 | 1.75 | 1.67 | 1.92 | 1.75 | 1.67 |
| PMC12806431 | processing | 2.08 | 2.50 | 2.17 | 2.33 | 2.17 | 2.33 | 2.25 | 1.42 |
| PMC12941549 | processing | 0.42 | 0.92 | 0.92 | 1.25 | 1.08 | 0.92 | 1.00 | 1.17 |

## Date effect (possible memorisation)

| Method | 2024 cases | 2025–2026 cases | Spearman (date vs score) |
|---|---:|---:|---:|
| closed_book | 1.66 | 1.35 | -0.04 |
| text_oneshot | 1.52 | 1.65 | 0.15 |
| v2_oneshot | 1.48 | 1.50 | 0.08 |
| tool_agent | 1.66 | 1.60 | 0.11 |
| resample | 1.60 | 1.44 | 0.13 |
| tool_agent_kg | 1.65 | 1.60 | 0.05 |
| self_revise | 1.62 | 1.54 | 0.10 |
| critique | 1.56 | 1.33 | 0.05 |

## Evidence ceiling

| Paper | Type | Reconstructibility (0–2) | Supportive records in oracle top-20 (any / strong) |
|---|---|---:|---|
| PMC10759803 | composition | 1 | 15 / 6 |
| PMC11077685 | processing | 1 | 18 / 1 |
| PMC11087546 | processing | 1 | 16 / 3 |
| PMC11355469 | computational | 2 | 15 / 3 |
| PMC11375216 | computational | 1 | 10 / 3 |
| PMC11375712 | processing | 1 | 19 / 0 |
| PMC11606917 | computational | 1 | 9 / 2 |
| PMC11775865 | characterization | 1 | 16 / 0 |
| PMC12029629 | computational | 1 | 17 / 3 |
| PMC12298864 | processing | 2 | 20 / 16 |
| PMC12806431 | processing | 1 | 12 / 0 |
| PMC12941549 | processing | 2 | 17 / 4 |

| Reconstructibility | Cases | closed_book | text_oneshot | v2_oneshot | tool_agent | resample | tool_agent_kg | self_revise | critique |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 1 | 9 | 1.65 | 1.65 | 1.56 | 1.73 | 1.60 | 1.69 | 1.71 | 1.50 |
| 2 | 3 | 1.28 | 1.31 | 1.28 | 1.36 | 1.39 | 1.44 | 1.25 | 1.44 |

| Method | Read any supportive record | Read a strongly supportive record | Cited any supportive record | Reconstruction when read supportive | when not |
|---|---:|---:|---:|---:|---:|
| text_oneshot | 100% | 47% | 94% | 1.56 | n/a |
| v2_oneshot | 81% | 50% | 72% | 1.51 | 1.39 |
| tool_agent | 61% | 31% | 61% | 1.42 | 1.98 |
| resample | 58% | 28% | 56% | 1.48 | 1.65 |
| tool_agent_kg | 75% | 33% | 75% | 1.56 | 1.86 |
| self_revise | 61% | 31% | 56% | 1.36 | 1.96 |
| critique | 61% | 31% | 64% | 1.36 | 1.68 |

## Tool-agent process

| Measure | tool_agent | resample | tool_agent_kg |
|---|---:|---:|---:|
| budget_exhausted | 1.00 | 1.00 | 1.00 |
| mean_searches | 5.97 | 5.47 | 3.81 |
| mean_reads | 5.11 | 5.61 | 5.39 |
| mean_distinct_records_read | 3.61 | 4.19 | 4.11 |
| mean_paging_reads | 1.50 | 1.42 | 1.28 |
| mean_repeated_searches | 0.42 | 0.36 | 0.00 |
| runs_with_rejected_submit | 7 | 3 | 2 |
| mean_cited | 2.44 | 2.86 | 3.11 |
| mean_read_but_uncited | 1.17 | 1.33 | 1.00 |
| spearman_distinct_reads_vs_score | -0.14 | -0.23 | -0.29 |
| spearman_searches_vs_score | 0.17 | 0.31 | 0.10 |
| recon_when_kg_cited | n/a | n/a | 1.95 |
| recon_when_kg_not_cited | n/a | n/a | 1.58 |
| runs_citing_kg | n/a | n/a | 5 |

## Run-to-run noise (tool_agent vs fresh resample, same units)

Units 36; mean difference -0.090; SD of unit differences 0.378; mean absolute difference 0.312; units changing by ≥1 point 0; classification changed 7.

## Pairwise position bias

- eval_v3: 20 of 107 pairs flip with presentation order (19%).
- eval_v4_matkg: 29 of 143 pairs flip with presentation order (20%).

## Revision arms vs original (same units)

resample is a fresh tool_agent sample with no revision, so its rows show how much change regression to the mean alone produces.

| Measure | critique | self_revise | resample |
|---|---:|---:|---:|
| units | 36 | 36 | 36 |
| improved | 12 | 5 | 11 |
| worse | 15 | 9 | 17 |
| unchanged | 9 | 22 | 8 |
| delta_when_citations_changed | -0.32 | -0.04 | n/a |
| delta_when_citations_kept | -0.05 | -0.04 | n/a |
| spearman_hedges_vs_delta | -0.18 | -0.04 | n/a |
| spearman_findings_vs_delta | -0.02 | n/a | n/a |
| spearman_original_vs_delta | -0.52 | -0.22 | -0.33 |
| delta_when_original_low | 0.07 | -0.04 | -0.04 |
| delta_when_original_high | -0.38 | -0.04 | -0.14 |

## Confound checks (within query level)

Tool arms pooled (tool_agent, resample, tool_agent_kg). 'Read supportive' means the run read at least one oracle record rated as supporting the target's intervention or mechanism.

| Level | Read-supportive rate | n read | Reconstruction (read) | n not | Reconstruction (not) |
|---|---:|---:|---:|---:|---:|
| broad | 81% | 29 | 0.75 | 7 | 0.79 |
| problem_constrained | 50% | 18 | 1.67 | 18 | 1.49 |
| expert_context | 64% | 23 | 2.28 | 13 | 2.85 |

Within-paper difference (read minus not), mean over papers with both groups: -0.11; per paper: PMC10759803 +0.91 (4/5), PMC11077685 -0.19 (8/1), PMC11087546 +1.28 (8/1), PMC11355469 +0.75 (6/3), PMC11375216 -1.45 (7/2), PMC11375712 -1.82 (5/4), PMC11606917 -0.64 (4/5), PMC11775865 -0.32 (5/4), PMC12029629 +0.06 (8/1), PMC12298864 +0.03 (8/1), PMC12806431 +0.29 (2/7), PMC12941549 -0.19 (5/4).

| Level | Group | Units | Errors per unit | Intervention | Condition | Mechanism | Outcome |
|---|---|---:|---:|---:|---:|---:|---:|
| broad | read_supportive | 29 | 4.14 | 0.72 | 0.66 | 0.86 | 0.76 |
| broad | not_read | 7 | 5.00 | 0.57 | 0.57 | 0.71 | 1.29 |
| problem_constrained | read_supportive | 18 | 4.00 | 1.56 | 1.39 | 1.72 | 2.00 |
| problem_constrained | not_read | 18 | 4.22 | 1.44 | 1.44 | 1.50 | 1.56 |
| expert_context | read_supportive | 23 | 3.30 | 2.96 | 1.96 | 2.26 | 1.96 |
| expert_context | not_read | 13 | 2.23 | 2.92 | 2.38 | 2.85 | 3.23 |

| Level | Reconstructibility 1 | Reconstructibility 2 |
|---|---:|---:|
| broad | 0.76 | 0.84 |
| problem_constrained | 1.61 | 1.28 |
| expert_context | 2.53 | 1.91 |

| Level | wrong_intervention | wrong_mechanism | wrong_outcome | wrong_baseline | wrong_conditions | physical_error | evidence_unsupported | evidence_contradicted | internal_inconsistency | untestable_or_vague | other |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| broad | 16% | 20% | 8% | 9% | 11% | 5% | 22% | 2% | 1% | 7% | 0% |
| problem_constrained | 12% | 24% | 7% | 5% | 18% | 2% | 19% | 1% | 3% | 9% | 0% |
| expert_context | 5% | 21% | 12% | 5% | 16% | 4% | 26% | 0% | 3% | 8% | 0% |

| Paper | Type | wrong_intervention | wrong_mechanism | wrong_outcome | wrong_baseline | wrong_conditions | physical_error | evidence_unsupported | evidence_contradicted | internal_inconsistency | untestable_or_vague | other |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PMC10759803 | composition | 16% | 8% | 9% | 11% | 6% | 10% | 21% | 3% | 5% | 10% | 0% |
| PMC11077685 | processing | 32% | 21% | 8% | 1% | 18% | 2% | 13% | 1% | 2% | 1% | 0% |
| PMC11087546 | processing | 18% | 12% | 9% | 15% | 13% | 2% | 19% | 1% | 2% | 8% | 0% |
| PMC11355469 | computational | 9% | 20% | 12% | 0% | 15% | 1% | 27% | 2% | 8% | 6% | 0% |
| PMC11375216 | computational | 5% | 23% | 23% | 3% | 5% | 2% | 30% | 0% | 0% | 10% | 0% |
| PMC11375712 | processing | 9% | 38% | 17% | 8% | 1% | 1% | 22% | 0% | 1% | 1% | 0% |
| PMC11606917 | computational | 19% | 16% | 5% | 5% | 13% | 9% | 23% | 0% | 0% | 9% | 0% |
| PMC11775865 | characterization | 7% | 31% | 10% | 4% | 16% | 1% | 20% | 0% | 0% | 10% | 0% |
| PMC12029629 | computational | 0% | 32% | 9% | 11% | 19% | 6% | 20% | 0% | 2% | 1% | 0% |
| PMC12298864 | processing | 8% | 9% | 0% | 4% | 18% | 2% | 29% | 6% | 1% | 24% | 0% |
| PMC12806431 | processing | 1% | 37% | 1% | 9% | 18% | 0% | 28% | 0% | 0% | 6% | 0% |
| PMC12941549 | processing | 11% | 13% | 6% | 4% | 30% | 5% | 16% | 0% | 3% | 12% | 1% |

## Generation health

- closed_book: failed ['PMC11375712__broad']; citation status {'valid': 35}
- text_oneshot: failed none; citation status {'valid': 36}
- v2_oneshot: failed none; citation status {'valid': 36}
- tool_agent: failed none; citation status {'valid': 36}
- resample: failed none; citation status {'valid': 36}
- tool_agent_kg: failed none; citation status {'valid': 36}
