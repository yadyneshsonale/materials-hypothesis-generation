# Failure analysis: extraction-rubric experiment

Runs analysed: 574; coded fatal errors: 2282; failure = reconstruction ≤ 1.0.

## 1. Extraction fidelity (random sample per rubric)

| Metric | card | effects | mechanisms | gaps |
|---|---:|---:|---:|---:|
| records_checked | 40 | 40 | 40 | 40 |
| fields_checked | 310 | 316 | 278 | 160 |
| supported | 0.90 | 0.93 | 0.87 | 0.86 |
| distorted | 0.09 | 0.07 | 0.13 | 0.10 |
| unsupported | 0.01 | 0.00 | 0.00 | 0.04 |
| records_fully_supported | 0.50 | 0.65 | 0.33 | 0.70 |
| ownership | own_work: 26, mixed: 14 | own_work: 34, mixed: 6 | own_work: 28, mixed: 12 | mixed: 6, own_work: 34 |
| worst_fields | key_findings; 0.17; 35; mechanism; 0.15; 40; limitations; 0.15; 39 | processing; 0.10; 40; structure_change; 0.08; 38; test_conditions; 0.07; 40 | scope_limits; 0.25; 40; alternatives_considered; 0.24; 38; mechanism; 0.12; 40 | lever; 0.23; 40; statement; 0.17; 40; type; 0.15; 40 |

- card: key_findings: Most findings are supported, but the record states that the vacuum oxide scale was <0.5 μm, whereas the paper explicitly gives >0.5 μm (despite also describing it as very thin). | key_findings: The 14.7% value for the Ho alloy is true fracture strain, not uniform tensile elongation. The deformation mechanisms were progressively activated at different strains rather than all sim | limitations: Difficulty predicting HPHT behavior is presented as a general field-level challenge, not a limitation of this study; the paper also says properties can be tuned, not that further tuning i | processing_route: The paper states that the ingot was melted over 10 times, not exactly 10 times.
- effects: property_change: The He-only increase from the annealed grain size was 10.0 nm (26.3 to 36.3 nm), not 11.8 nm; 11.8 nm is the increase relative to the as-deposited size of 24.5 nm. The dual-beam chang | intervention: The paper’s intervention is varying the degree of SRO within HfNbTaTiZr, not comparing its SRO alloy directly with random samples of other HEAs. | processing: The paper reports original Monte Carlo and molecular-dynamics simulations; literature comparison is contextual rather than the primary method. | test_conditions: The main conductivity simulations use equiatomic HfNbTaTiZr at 300 K with varying SRO, rather than various compositions and temperatures.
- mechanisms: alternatives_considered: Cr0 had the lowest corrosion potential, but not the highest corrosion rate; Cr0.75 had the highest reported rate at 7.329 mm/a, versus 2.959 mm/a for Cr0. | mechanism: Ballistic mixing was proposed to enable homogenization below the ODTT, not necessarily to drive the system past it; the 1073 K irradiation was below the thick-film ODTT of ~1120 K. | alternatives_considered: Cr–V precipitation in the quaternary alloy was a comparison, and annealing-induced Hf grain-boundary segregation was a separate observation, not alternative mechanisms conside | operating_conditions: The δ phase was assessed after annealing at 800 °C for 50 h, whereas the γ″ phase was assessed after aging at 800 °C for 40 h, not annealing.
- gaps: type: The paper reports that Cr improves oxidation resistance and promotes Laves-phase precipitation, but it does not demonstrate a corresponding performance tradeoff or ductility loss. | statement: Cr-induced Laves-phase precipitation and improved oxidation resistance are supported, but the paper does not specifically characterize the precipitated Laves phase as brittle; brittleness i | type: The paper describes an observational time-resolution limitation, not an open problem. | statement: The paper reports that Cr2O3 and Fe2O3 were absent and that this conflicts with prior isothermal studies, but it identifies Cr2O3—not Fe2O3—as the relevant protective oxide and discusses ox

## 2–3. Retrieval and use

| Metric | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|
| runs | 72 | 72 | 72 | 72 | 72 | 72 | 72 |
| failures | 26 | 28 | 28 | 28 | 30 | 30 | 32 |
| failure_rate | 0.36 | 0.39 | 0.39 | 0.39 | 0.42 | 0.42 | 0.44 |
| failure_stage | no_supportive_in_context: 2, supportive_in_context_not_cited: 1, supportive_cited: 23 | no_supportive_in_context: 4, supportive_in_context_not_cited: 1, supportive_cited: 23 | no_supportive_in_context: 2, supportive_in_context_not_cited: 0, supportive_cited: 26 | no_supportive_in_context: 6, supportive_in_context_not_cited: 3, supportive_cited: 19 | no_supportive_in_context: 4, supportive_in_context_not_cited: 3, supportive_cited: 23 | no_supportive_in_context: 4, supportive_in_context_not_cited: 8, supportive_cited: 18 | no_supportive_in_context: 7, supportive_in_context_not_cited: 7, supportive_cited: 18 |
| failure_rate_by_stage | no_supportive_in_context: 1.00, supportive_in_context_not_cited: 0.17, supportive_cited: 0.36 | no_supportive_in_context: 1.00, supportive_in_context_not_cited: 1.00, supportive_cited: 0.34 | no_supportive_in_context: 1.00, supportive_in_context_not_cited: n/a, supportive_cited: 0.37 | no_supportive_in_context: 0.50, supportive_in_context_not_cited: 0.33, supportive_cited: 0.37 | no_supportive_in_context: 1.00, supportive_in_context_not_cited: 0.50, supportive_cited: 0.37 | no_supportive_in_context: 1.00, supportive_in_context_not_cited: 0.40, supportive_cited: 0.38 | no_supportive_in_context: 0.88, supportive_in_context_not_cited: 0.70, supportive_cited: 0.33 |
| runs_by_stage | supportive_cited: 64, no_supportive_in_context: 2, supportive_in_context_not_cited: 6 | supportive_cited: 67, no_supportive_in_context: 4, supportive_in_context_not_cited: 1 | supportive_cited: 70, no_supportive_in_context: 2 | no_supportive_in_context: 12, supportive_cited: 51, supportive_in_context_not_cited: 9 | supportive_cited: 62, supportive_in_context_not_cited: 6, no_supportive_in_context: 4 | supportive_cited: 48, supportive_in_context_not_cited: 20, no_supportive_in_context: 4 | supportive_cited: 54, supportive_in_context_not_cited: 10, no_supportive_in_context: 8 |
| mean_supportive_packed | 4.03 | 3.56 | 3.67 | 3.94 | 4.14 | 3.97 | 2.61 |
| mean_strong_packed | 0.83 | 0.83 | 0.58 | 1.25 | 0.72 | 0.67 | 0.83 |
| share_supportive_packed_that_is_cited | 0.53 | 0.61 | 0.55 | 0.48 | 0.52 | 0.30 | 0.55 |
| share_cited_that_is_supportive | 0.55 | 0.53 | 0.81 | 0.37 | 0.44 | 0.25 | 0.27 |

## 3b. Effect of citing supportive evidence (evidence arms pooled, within level)

| Level | Group | Runs | Reconstruction | Intervention | Mechanism |
|---|---|---:|---:|---:|---:|
| broad | no_supportive_in_context | 28 | 0.56 | 0.32 | 0.57 |
| broad | in_context_not_cited | 21 | 0.50 | 0.24 | 0.52 |
| broad | supportive_cited | 119 | 0.64 | 0.50 | 0.59 |
| broad | strong_cited | 49 | 0.68 | 0.61 | 0.73 |
| problem_constrained | no_supportive_in_context | 4 | 0.44 | 0.00 | 0.25 |
| problem_constrained | in_context_not_cited | 20 | 1.56 | 1.70 | 1.10 |
| problem_constrained | supportive_cited | 144 | 1.49 | 1.47 | 1.44 |
| problem_constrained | strong_cited | 66 | 1.54 | 1.62 | 1.54 |
| expert_context | no_supportive_in_context | 4 | 3.44 | 4.00 | 3.50 |
| expert_context | in_context_not_cited | 11 | 2.79 | 3.00 | 2.36 |
| expert_context | supportive_cited | 153 | 2.34 | 2.78 | 2.33 |
| expert_context | strong_cited | 82 | 2.08 | 2.65 | 2.06 |

## 4. Error categories (share of each arm's coded fatal errors)

| Metric | closed_book | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| errors_per_run | 3.53 | 3.81 | 4.10 | 4.18 | 3.94 | 4.10 | 4.06 | 4.08 |
| wrong_intervention | 0.13 | 0.13 | 0.14 | 0.13 | 0.12 | 0.10 | 0.15 | 0.10 |
| wrong_mechanism | 0.25 | 0.20 | 0.19 | 0.18 | 0.20 | 0.22 | 0.20 | 0.22 |
| wrong_outcome | 0.10 | 0.09 | 0.09 | 0.09 | 0.08 | 0.07 | 0.10 | 0.10 |
| wrong_baseline | 0.05 | 0.04 | 0.06 | 0.05 | 0.07 | 0.06 | 0.03 | 0.06 |
| wrong_conditions | 0.17 | 0.15 | 0.18 | 0.16 | 0.12 | 0.16 | 0.16 | 0.14 |
| physical_error | 0.05 | 0.04 | 0.05 | 0.07 | 0.06 | 0.04 | 0.04 | 0.04 |
| evidence_unsupported | 0.13 | 0.21 | 0.20 | 0.21 | 0.23 | 0.22 | 0.21 | 0.22 |
| evidence_contradicted | 0.00 | 0.03 | 0.00 | 0.01 | 0.04 | 0.03 | 0.02 | 0.03 |
| internal_inconsistency | 0.01 | 0.02 | 0.02 | 0.02 | 0.02 | 0.02 | 0.01 | 0.01 |
| untestable_or_vague | 0.09 | 0.08 | 0.07 | 0.08 | 0.07 | 0.07 | 0.07 | 0.07 |
| other | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

## 4b. Share of failing runs with at least one error of each category

| Metric | closed_book | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| wrong_intervention | 0.74 | 0.77 | 0.71 | 0.61 | 0.57 | 0.63 | 0.77 | 0.53 |
| wrong_mechanism | 0.70 | 0.69 | 0.82 | 0.71 | 0.75 | 0.87 | 0.83 | 0.78 |
| wrong_outcome | 0.39 | 0.54 | 0.36 | 0.39 | 0.32 | 0.33 | 0.33 | 0.44 |
| wrong_baseline | 0.26 | 0.27 | 0.36 | 0.29 | 0.54 | 0.43 | 0.23 | 0.44 |
| wrong_conditions | 0.48 | 0.54 | 0.61 | 0.46 | 0.46 | 0.57 | 0.63 | 0.44 |
| physical_error | 0.13 | 0.12 | 0.18 | 0.14 | 0.21 | 0.10 | 0.17 | 0.19 |
| evidence_unsupported | 0.65 | 0.81 | 0.79 | 0.79 | 0.82 | 0.80 | 0.83 | 0.81 |
| evidence_contradicted | 0.00 | 0.12 | 0.00 | 0.04 | 0.29 | 0.20 | 0.03 | 0.19 |
| internal_inconsistency | 0.04 | 0.12 | 0.07 | 0.07 | 0.11 | 0.13 | 0.03 | 0.03 |
| untestable_or_vague | 0.35 | 0.15 | 0.25 | 0.36 | 0.36 | 0.23 | 0.13 | 0.16 |
| other | 0.04 | 0.04 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

## 4c. Mechanism source vs outcome (evidence arms pooled, within level)

| Level | Mechanism source | Runs | Reconstruction | Failure rate |
|---|---|---:|---:|---:|
| broad | not_from_evidence | 37 | 0.72 | 0.78 |
| broad | same_system_evidence | 12 | 0.42 | 0.92 |
| broad | transferred_with_justification | 21 | 0.55 | 1.00 |
| broad | transferred_without_justification | 98 | 0.60 | 0.88 |
| problem_constrained | not_from_evidence | 56 | 1.74 | 0.16 |
| problem_constrained | same_system_evidence | 1 | 1.00 | 1.00 |
| problem_constrained | transferred_with_justification | 27 | 1.36 | 0.41 |
| problem_constrained | transferred_without_justification | 84 | 1.33 | 0.34 |
| expert_context | not_from_evidence | 45 | 2.66 | 0.00 |
| expert_context | transferred_with_justification | 7 | 2.21 | 0.14 |
| expert_context | transferred_without_justification | 116 | 2.30 | 0.03 |

## 5. Units and papers

Best arm per unit: v2_units: 4, card: 9, closed_book: 9, effects: 5, text_chunks: 4, mechanisms: 2, gaps: 2, mixed: 1. Mean best-minus-worst spread per unit: 0.68.
Units where every arm fails: PMC10759803; broad; 0.88; PMC11077685; broad; 0.75; PMC11375216; broad; 0.88; PMC11375712; broad; 0.12; PMC11606917; broad; 0.88; PMC12941549; broad; 0.88.

| Paper | Reconstruction | Failure rate | Top error categories |
|---|---:|---:|---|
| PMC10759803 | 1.60 | 0.33 | evidence_unsupported; 0.18; wrong_intervention; 0.15; wrong_outcome; 0.13 |
| PMC11077685 | 0.95 | 0.56 | wrong_intervention; 0.34; wrong_mechanism; 0.19; wrong_conditions; 0.16 |
| PMC11087546 | 1.47 | 0.60 | wrong_mechanism; 0.22; evidence_unsupported; 0.20; wrong_intervention; 0.17 |
| PMC11355469 | 1.37 | 0.33 | wrong_mechanism; 0.27; wrong_conditions; 0.20; evidence_unsupported; 0.17 |
| PMC11375216 | 1.86 | 0.33 | evidence_unsupported; 0.28; wrong_mechanism; 0.19; wrong_outcome; 0.16 |
| PMC11375712 | 1.44 | 0.33 | wrong_mechanism; 0.31; evidence_unsupported; 0.25; wrong_outcome; 0.14 |
| PMC11606917 | 1.48 | 0.42 | evidence_unsupported; 0.26; wrong_intervention; 0.21; wrong_mechanism; 0.16 |
| PMC11775865 | 1.73 | 0.27 | wrong_mechanism; 0.26; evidence_unsupported; 0.22; wrong_conditions; 0.18 |
| PMC12029629 | 1.41 | 0.44 | wrong_mechanism; 0.26; wrong_conditions; 0.24; evidence_unsupported; 0.21 |
| PMC12298864 | 1.60 | 0.31 | evidence_unsupported; 0.24; untestable_or_vague; 0.22; wrong_conditions; 0.16 |
| PMC12806431 | 2.34 | 0.04 | wrong_mechanism; 0.31; evidence_unsupported; 0.28; wrong_conditions; 0.18 |
| PMC12941549 | 0.86 | 0.73 | wrong_conditions; 0.26; evidence_unsupported; 0.17; wrong_mechanism; 0.16 |

## 6. Reproduced generation failure (closed_book, PMC11375712 broad)

- attempt 1: finish=stop, chars=706, keys=['baseline', 'boundary', 'conditions', 'conflicting_evidence_ids', 'falsification_experiment', 'hypothesis', 'intervention', 'material_initial_state', 'mechanism', 'predicted_outcome', 'structural_mediator', 'supporting_evidence_ids', 'uncertainty'], has hypothesis string=False
- attempt 2: finish=stop, chars=795, keys=['baseline', 'boundary', 'conditions', 'conflicting_evidence_ids', 'falsification_experiment', 'hypothesis', 'intervention', 'material_initial_state', 'mechanism', 'predicted_outcome', 'structural_mediator', 'supporting_evidence_ids', 'uncertainty'], has hypothesis string=False
- attempt 3: finish=stop, chars=736, keys=['baseline', 'boundary', 'conditions', 'conflicting_evidence_ids', 'falsification_experiment', 'hypothesis', 'intervention', 'material_initial_state', 'mechanism', 'predicted_outcome', 'structural_mediator', 'supporting_evidence_ids', 'uncertainty'], has hypothesis string=False
