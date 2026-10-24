# Experiment 19: answer leakage in the benchmark queries

Run 2026-10-23. Code: [query_leakage_audit.py](../../../query_leakage_audit.py). Data: `analysis.json`
(per-unit overlap, result roles used, and the builder's own risk flags). Related work on how other benchmarks
separate input from answer: [RELATED_WORK.md](../RELATED_WORK.md).

## How the queries were built (experiment 3, reused in experiments 7 to 18)

`build_cases` in [temporal_hypothesis_benchmark.py](../../../temporal_hypothesis_benchmark.py) makes one Qwen
call per held-out paper (12 papers, published after the cutoff). The call receives:

- `safe_role_candidates`: the paper's problem_motivation, prior_limitation and constraint roles;
- `target_role_candidates`: its hypothesis_statement, causal_claim, mechanism_principle, evidence_result and
  contradiction roles;
- `normalized_current_paper_evidence_for_hidden_target_only`: its own result evidence (v2 units).

From that single context it writes all three queries and the hidden target. Each query records the roles it was
written from in `source_role_refs`.

- **broad:** material/application family and desired property only.
- **problem_constrained:** adds the operating regime, known failure and design constraints.
- **expert_context:** adds "all scientifically useful pre-solution context".

Safeguards: the instruction "do not reveal the exact composition, intervention, recipe, structure, mechanism,
result …", and a string check that the title and DOI are not in the query. Nothing checks the content, and the
builder's own `leakage_audit.remaining_risks` field is not acted on.

## Findings

| Level | Queries written from result roles | Answer words in query (mean) | Max |
|---|---:|---:|---:|
| broad | 2 of 12 | 7.6% | 16.2% |
| problem_constrained | 7 of 12 | 20.0% | 27.3% |
| expert_context | 12 of 12 | 46.9% | 65.1% |

"Answer words" are the content words of the hidden target's intervention, structural mediator and mechanism
fields.

**Examples.**

| Case | Hidden answer | Query text |
|---|---|---|
| PMC10759803 | Add 4.2 at.% Cr; reticulated Laves phase hinders cracks; solid-solution hardening | expert: "addition of ~4 at.% of a specific transition metal (Cr) drives the formation of a complex multicomponent Laves phase … reticulated/interconnected … impedes crack extension … solid solution hardening"; problem: "introduce a minor alloying element … induce a secondary intermetallic phase to form a reticulated network … mitigate crack propagation" |
| PMC11087546 | HPHT treatment (hexahedron anvil) turns Al0.7CoCrFeNi lamellae into a hierarchically patterned, coherent-interface structure | expert: "High-Pressure and High-Temperature (HPHT) treatment using a hexahedron-anvil apparatus … approximately 6 GPa at 1473 K … hierarchically patterned microstructure with coherent interfaces"; problem: "high-intensity thermomechanical treatment … transform the lamellar structure into a patterned configuration … conventional hot isostatic pressing" |
| PMC12298864 | High-energy ball milling 1–6 h + SPS 900–1000 °C; nanocrystalline (<48 nm) 83% FCC / 17% BCC | broad: "nanocrystalline grain sizes below 50 nm and a dual-phase solid solution"; problem: "high-energy milling followed by rapid sintering … FCC with minor BCC"; expert: "~6 hours … SPS at 1000°C" |

**Leakage predicts the score.** Spearman correlation between answer overlap and the GPT-5.6 reconstruction score
per unit:

| Method | All 36 units | broad | problem_constrained | expert_context |
|---|---:|---:|---:|---:|
| closed_book | 0.86 | 0.42 | 0.38 | 0.75 |
| text_chunks | 0.84 | 0.43 | 0.00 | 0.66 |
| card | 0.80 | 0.21 | 0.03 | 0.80 |
| card_systemmatch | 0.84 | 0.77 | 0.00 | 0.83 |
| graph_profiles | 0.77 | −0.08 | 0.02 | 0.84 |
| graph_profiles_systemmatch | 0.84 | 0.28 | 0.28 | 0.72 |
| graph_tool_agent | 0.84 | 0.48 | 0.11 | 0.85 |

The all-unit correlation is high mostly because overlap and score both rise with the level. Within the expert
level it remains 0.66–0.85: the more answer the expert query gives, the higher the score.

**Other construction problems.**

- The query writer is Qwen, the model under test.
- Many expert queries prescribe the hypothesis ("Propose a hypothesis where …") instead of posing a problem.
- Some queries prescribe the paper's own control experiment (for example the hot isostatic pressing comparison in
  PMC11087546).
- The hidden target contains exact values (for example +13.5% yield strength, 675 HV) that no earlier literature
  can predict, and the judge scores against them.
- The queries were never reviewed by a materials expert.

## Impact on earlier experiments

- **Still valid:** comparisons between methods within the same query unit, because every method saw the same text
  (paired tests in experiments 7, 9, 11, 14, 16 and 17).
- **Inflated or confounded:**
  - absolute reconstruction scores;
  - the broad-to-expert gradient;
  - "query inferability drives scores" (experiments 12, 13, 15);
  - "closed-book is best" and "evidence hurts on specific queries" (experiments 14 to 18). When the query already
    contains the answer, retrieved evidence can only distract.

## Recommended rebuild (not yet run)

This follows how ACCELMAT/MatDesign, SCIMON and ResearchBench separate input from answer
([RELATED_WORK.md](../RELATED_WORK.md)).

1. The query writer sees only problem_motivation, prior_limitation and constraint content from the introduction.
   The hidden target is built in a separate call that the writer never sees.
2. The writer is GPT-5.6, not the generator.
3. Fixed form: goal statement plus constraints. Levels add context (baseline alloy, failure mode, test regime,
   earlier attempts) and never the intervention type, mechanism or structure.
4. Automatic gate: answer-word overlap below about 10%, and a query-only guesser must score below 2 of 4 on
   intervention against the target. Otherwise rewrite, or drop the case.
5. Materials-expert review of the 36 queries and targets. Remove exact values that cannot be predicted from the
   target, or score them separately.
6. Re-run closed_book, text_chunks, card_systemmatch and graph_profiles_systemmatch on the clean queries. Report a
   target-free quality score alongside the reconstruction score, and an inspiration-retrieval score (does the
   evidence pool contain the target's cited pre-cutoff works?).
