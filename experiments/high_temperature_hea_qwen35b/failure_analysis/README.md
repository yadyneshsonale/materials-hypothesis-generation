# Failure analysis: where and why each method fails

**Scope.** Every judged unit from every method on the 12 held-out HEA cases. That is 8 methods × 36
paper-by-query units = 288 units, of which 287 were judged and 1 failed to generate. The judge recorded
1,087 fatal errors across them.

**Date:** 2026-10-22. **Script:** [failure_analysis.py](../../../failure_analysis.py) (tests in
`test_failure_analysis.py`). **Full tables:** [results/tables.md](results/tables.md).
**Machine-readable:** [results/analysis.json](results/analysis.json).

| Method | Source | What it is |
|---|---|---|
| `closed_book` | eval_v3 | Query and cutoff only |
| `text_oneshot` | eval_v3 | Top 14 earlier text chunks in one prompt |
| `v2_oneshot` | eval_v3 | Top 14 earlier structured evidence units in one prompt |
| `tool_agent` | eval_v3 | Searches and reads earlier papers (12-call budget) |
| `resample` | eval_critique | A second, independent `tool_agent` sample (noise reference) |
| `tool_agent_kg` | eval_v4_matkg | `tool_agent` plus pre-cutoff MatKG lookups |
| `self_revise` | eval_critique | `tool_agent` output revised by a reviser with no critics |
| `critique` | eval_critique | `tool_agent` output revised after three critic models |

## Main findings

1. **The query level matters far more than the method.** Every method scores about 0.7 to 1.0 on
   `broad` queries and about 2.1 to 2.6 on `expert_context` queries. The spread across levels (about 1.7
   points) is more than ten times the spread across methods (about 0.15 points).
2. **The most common failure is getting the mechanism wrong, not the intervention.** For every method,
   the largest error categories are a wrong mechanism (19–24% of errors), unsupported evidence claims
   (20–26% for evidence-using methods), and wrong conditions (10–18%). Physics errors are rare (1–7%).
3. **Missing evidence is not the main bottleneck.** For each case, GPT-5.6 rated whether the 20 earlier
   records most similar to the target anticipate it. No case was rated "no support". Nine were rated "right
   direction, but the specific intervention needs a new idea", and three were rated "plausibly
   reconstructible". Those three did **not** score higher than the others. Reading supportive records did
   not reliably help either: the average within-paper effect was −0.11, ranging from −1.82 to +1.28.
4. **When the query is specific, reading prior art is associated with worse mechanism and outcome
   scores.** On `expert_context` queries, runs that read supportive earlier records had the same
   intervention score as those that didn't (2.96 vs 2.92), but lower mechanism (2.26 vs 2.85), outcome
   (1.96 vs 3.23) and condition (1.96 vs 2.38) scores. They also had more errors per unit (3.30 vs 2.23).
   This fits the agent importing the earlier system's mechanism and results. It is an observed association
   (23 vs 13 units), not a tested cause.
5. **Differences between methods are near the noise floor.** Two independent samples of the same tool
   agent differ by 0.31 points per unit on average, and their mean differs by 0.09. One pairwise verdict in
   five flips when the two candidates swap positions.

## How the analysis was done

1. **Deterministic tables** over all units: scores, classifications, zero-score rates per dimension,
   breakdowns by paper, target type, query level and publication date, tool-trace behaviour, hedging,
   run-to-run noise, and pairwise position bias.
2. **Fatal-error coding.** GPT-5.6 (`gpt-5.6-sol_2026-07-09`) assigned each of the 1,087 judge-written fatal
   errors to one of 11 fixed categories. I reviewed a random sample of 40 labels by hand
   ([results/spot_check_sample.md](results/spot_check_sample.md)) and agreed with 37 (93%). All three
   disagreements were between neighbouring categories (`wrong_intervention`, `wrong_conditions`,
   `wrong_baseline`, `untestable_or_vague`), so shares within those groups are approximate.
3. **Evidence ceiling.** For each case, the 20 eligible pre-cutoff records most lexically similar to the
   hidden target were retrieved with the same `retrieve` function the methods use. GPT-5.6 rated each record
   for intervention and mechanism support (0 to 2) and the whole set for reconstructibility (0 to 2). This
   analysis reads the hidden target; nothing it produces feeds back into any generation. Supportive records
   outside the top 20 are not found, so "not read" is an underestimate of what was available.
4. **Confound checks.** Because query level dominates scores, evidence and difficulty effects were compared
   within each level and within each paper. Regression to the mean in the revision arms was measured with
   the `resample` arm, which revises nothing.

Error categories: `wrong_intervention`, `wrong_mechanism`, `wrong_outcome`, `wrong_baseline`,
`wrong_conditions`, `physical_error`, `evidence_unsupported`, `evidence_contradicted`,
`internal_inconsistency`, `untestable_or_vague`, `other`. Definitions are in `ERROR_CATEGORIES` in the script.

## Overview across methods

| Method | Reconstruction | Hard failures (≤0.5) | Zero on intervention | Zero on evidence validity | Errors per unit | Top error categories |
|---|---:|---:|---:|---:|---:|---|
| tool_agent | 1.64 | 14% | 14% | 22% | 3.67 | mechanism 21%, unsupported 20%, conditions 17% |
| tool_agent_kg | 1.63 | **22%** | 22% | 25% | 3.78 | unsupported 26%, mechanism 23%, conditions 15% |
| self_revise | 1.60 | 17% | 14% | **33%** | 3.61 | mechanism 22%, unsupported 22%, conditions 15% |
| closed_book | 1.56 | 17% | 20% | 11% | 3.49 | mechanism 24%, conditions 14%, untestable 12% |
| text_oneshot | 1.56 | 11% | **25%** | 14% | 3.64 | unsupported 24%, mechanism 20%, conditions 16% |
| resample | 1.55 | 14% | 17% | 31% | 3.89 | unsupported 25%, mechanism 21%, conditions 18% |
| v2_oneshot | 1.49 | 17% | 22% | 11% | 4.00 | unsupported 23%, mechanism 19%, intervention 13% |
| critique | 1.49 | 11% | 11% | 25% | **4.22** | unsupported 22%, mechanism 22%, conditions 15% |

Only one unit defeated every method: `PMC11375712` broad (best score 0.25; closed-book also failed to
generate on it).

## Failures by method

### closed_book (1.56)

- **Where it fails.** It has the highest zero rate on all four primary dimensions (20% each). It is the
  only method with non-trivial zero rates on novelty (9%) and experiment discriminability (9%). It is
  bimodal: either it lands in the right general area, or it misses entirely.
- **Why.** With no evidence, it falls back on generic HEA design. Its errors are wrong mechanism (24%),
  untestable or vague (12%) and wrong outcome (12%). It has the fewest unsupported-evidence errors (11%),
  because it cites nothing. The judge noted for one run that no materials hypothesis was proposed, and one
  generation (`PMC11375712` broad) failed twice with no `hypothesis` field.
- **Possible memorisation.** On 2024 papers it averages 1.66, and on 2025–2026 papers 1.35. That −0.31 drop
  is the largest of any method (the tool agent drops only 0.06), and it would fit some prior knowledge of
  older papers. It rests on only 4 late cases and is driven by one paper (`PMC12941549`, 0.42), so it is
  suggestive, not shown. It also scores best of all methods on `PMC11375712` (2.25) and `PMC11355469` (1.75),
  so parametric knowledge sometimes beats retrieval.

### text_oneshot (1.56)

- **Where it fails.** It has the highest intervention zero rate of any method (25%), but the lowest
  hard-failure rate (11%).
- **Why.** It sees the evidence: 100% of its runs were shown at least one supportive record, and 94% cited
  one. It still does not turn that prior art into the target's intervention. Its largest error category is
  unsupported evidence claims (24%): it cites related records for claims they do not make.

### v2_oneshot (1.49)

- **Where it fails.** Lowest reconstruction of the generation methods, most `unsupported` classifications of
  the eval_v3 methods (12), and 4.00 errors per unit.
- **Why.** It saw a strongly supportive record more often than any other method (50%), yet scored lowest.
  The structured evidence units carry less context than raw text: they state results without the
  surrounding conditions, so the model over-generalises them. Its physical-error share (7%) is the highest
  of any method.

### tool_agent (1.64) and resample (1.55)

- **Where it fails.** Evidence validity is zero in 22% (original) and 31% (resample) of runs, against 11–14%
  for the one-shot methods. It reads fewer supportive records (58–61%) than the one-shot methods (81–100%).
- **Why: the budget runs out.** It uses all 12 tool calls in every run. It reads only 3.6–4.2 distinct records
  per run, spends about 1.5 calls paging through long records, and cites 2.4–2.9 of them. So it grounds its
  claims in fewer records, and the judge marks more of its claims as unsupported. More searches correlate
  weakly with higher scores (ρ = 0.17 and 0.31). More distinct records read correlates weakly with lower
  scores (ρ = −0.14 and −0.23).
- **Why: anchoring on precedent** (finding 4). On specific queries, reading related earlier work is
  associated with worse mechanism and outcome scores.
- **Citation mistakes.** 7 original runs and 3 resample runs had a submission rejected for citing an unread
  record, often a bare paper ID instead of a record ID.

### tool_agent_kg (1.63)

- **Where it fails.** Its mean matches the plain tool agent, but it has the highest hard-failure rate of any
  method (22%). Its outcomes are more spread out.
- **Why.** The KG lookups replace searches: it runs 3.8 searches per run against 6.0 for the plain agent,
  within the same 12-call budget. It cited a KG fact in only 5 of 36 runs. Those 5 scored 1.95 against 1.58
  for the rest, but 5 runs are too few to separate a KG effect from case selection. The KG facts are generic
  co-occurrence statistics, so the model mostly ignores them, while the calls they cost are lost to search.

### self_revise (1.60)

- **Where it fails.** It changed little: 22 of 36 units were unchanged, 5 improved and 9 got worse. It has the
  highest evidence-validity zero rate (33%).
- **Why.** Revising without new information mostly rewrites prose and keeps the same citations (7 of 36
  changed them). Its mean change (−0.04) is within run-to-run noise.

### critique (1.49)

- **Where it fails.** It has the most errors per unit (4.22) and by far the most hedging: 3.47 hedge words per
  hypothesis, against 0.03–0.22 for the other methods. Its untestable-or-vague error share (12%) is the joint
  highest, although the critics were checking for testability.
- **Why: fixes become hedges.** The critics flag unsupported and untestable claims, and the reviser responds
  by softening them. The judge then rates the hypothesis as vague.
- **It helps weak hypotheses and hurts strong ones**, beyond regression to the mean. Using the original score
  to split the units:

  | Original score | critique change | resample change (no revision) | Effect beyond regression |
  |---|---:|---:|---:|
  | below 1.5 | +0.07 | −0.04 | about +0.11 |
  | 1.5 or above | −0.38 | −0.14 | about −0.24 |

  By query level it scores best of all methods on `broad` (0.96 against 0.69–0.79) and worst on
  `expert_context` (2.10 against 2.29–2.60).
- **Swapping citations hurts.** In the 14 units where the reviser changed the cited records, the score fell
  by 0.32 on average, against 0.05 where it kept them. The number of critic findings does not predict the
  change (ρ = −0.02).

## Failures that come from the benchmark, not the methods

- **Broad queries are under-specified.** At the `broad` level, wrong intervention (16%) and wrong baseline (9%)
  are much more common than at `expert_context` (5% and 5%). A broad query admits many valid hypotheses, and
  the target is only one of them. Broad-level scores mostly measure luck in matching the target.
- **A few papers are hard for everyone.** Average reconstruction per paper, across all eight methods, ranges
  from 0.96 (`PMC12941549`) and 1.00 (`PMC11077685`) to 2.16 (`PMC12806431`).
  - `PMC12941549`: 29% of its errors are wrong conditions. The query states the 800–1000 °C trade-off, and the
    methods identify it. They then miss the specific 1000 °C optimum, the oxide barrier phases and the target's
    test conditions (900 °C air oxidation, 3.5% NaCl corrosion), none of which the query implies.
  - `PMC11077685`: 32% of its errors are wrong intervention. The target is an unusual route (3D ink extrusion of
    hydride powders, hydrogen de-binding, long vacuum sintering). Methods propose conventional powder routes.
- **Target type does not explain much.** I expected the four simulation-study targets to be harder, because a
  "propose a hypothesis" query fits them poorly. They are not: computational targets score 1.48–1.65 across
  methods, close to processing targets (1.33–1.64). The single composition and single characterisation targets
  are too few to judge.
- **Noise.** Per-unit scores change by 0.31 on average between two samples of the same method, and 7 of 36
  units change classification. The mean difference was 0.09. Differences of about 0.1 between methods on these
  36 units should not be read as real.
- **Judge position bias.** 19% (eval_v3) and 20% (eval_v4) of pairwise verdicts flip when the two candidates
  swap positions. Those are counted as ties, which protects the results but shows how unstable pairwise
  preferences are.

## What this suggests

In priority order:

1. **Fix the benchmark first.** Drop or separate the `broad` level, or score it against several valid
   targets. Remove or flag targets whose key details cannot be inferred from the query (`PMC12941549`'s test
   conditions). Report results per level.
2. **Measure noise properly.** Generate several samples per unit and judge each, so differences can be tested
   against run-to-run variation. Calibrate the judge against an expert on about 30 units.
3. **Target mechanism reasoning, not intervention search.** Mechanism errors are the largest category for
   every method. A step that checks the proposed mechanism against the base system's measured phases and
   properties would address the most common failure.
4. **Stop the agent wasting its budget.** Count paging separately from the tool budget, return longer pages,
   or summarise long records, so the agent reads more distinct sources. Make cited claims verifiable
   sentence by sentence.
5. **Guard against anchoring.** When a query is specific, ask the agent to state how the target system
   differs from the precedent it found before borrowing a mechanism.
6. **Use critique only on weak hypotheses**, and forbid the reviser from hedging. Critique helped units below
   1.5 and hurt units above it.
7. **Make KG lookups cheaper or targeted.** Don't count them against the search budget, or return
   relation-typed facts (element → phase → property) instead of raw co-occurrence.

## Limitations of this analysis

- The error categories and the evidence ceiling were coded by the same GPT-5.6 deployment that judged the
  runs, so they share its blind spots. The hand spot check covered 40 of 1,087 errors.
- The evidence ceiling uses lexical top-20 retrieval with the target as the query. Supportive records that
  are worded differently are missed, so evidence availability may be underestimated.
- All comparisons in this document are observational over 36 units per method (12 papers). The anchoring and
  memorisation findings are associations that need targeted experiments to confirm.
- The hedge counter is a keyword list (may, might, could, potentially, possibly, uncertain, unclear, likely,
  perhaps, suggest, further investigation). It gives a slightly higher critique count (3.47) than the earlier
  narrower list (3.33).

## Reproduce

```bash
.venv/bin/python failure_analysis.py code-errors --workers 8 --resume      # GPT-5.6 error coding (~273 calls)
.venv/bin/python failure_analysis.py evidence-ceiling --workers 4 --resume # GPT-5.6 evidence ceiling (12 calls)
.venv/bin/python failure_analysis.py report                                # tables, analysis.json, spot-check sample
.venv/bin/python -m unittest test_failure_analysis.py
```
