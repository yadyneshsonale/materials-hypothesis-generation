# Failure analysis: what breaks in the extraction-rubric pipeline

**Date:** 2026-10-23. **Script:** [failure_rubric.py](../../../../failure_rubric.py) (tests in
`test_failure_rubric.py`). **Tables:** [results/tables.md](results/tables.md). **Data:**
[results/analysis.json](results/analysis.json).

**Scope.** All 574 judged runs of the extraction-rubric experiment (8 arms × 12 papers × 3 query levels × 2 samples,
minus 2 failed runs) and their 2,282 judge-written fatal errors. A run counts as a **failure** if its
reconstruction score (mean of intervention, condition, mechanism and outcome, 0–4) is 1.0 or less.

**What was checked, in pipeline order:**

| Stage | Check | Data |
|---|---|---|
| Extraction | GPT-5.6 compares 40 random records per rubric (160 total) field by field with the source paper: supported, distorted or unsupported; own work or cited work. Target-free | 1,064 fields |
| Retrieval | Does the packed context contain a record that the evidence ceiling rated as anticipating the target? | 504 evidence runs |
| Use | Is such a record cited, and does citing it go with a better score (within level and within paper)? | 504 evidence runs |
| Reasoning | Each fatal error coded into the 11-category taxonomy from the earlier failure analysis (GPT-5.6); mechanism source from the target-free audit | 2,282 errors |
| Generation | The closed-book unit that fails reproducibly, rerun three times with the raw model output saved | 3 calls |

## What breaks, ranked by impact

### 1. Broad queries fail for every method (benchmark)

| Failure rate | closed_book | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| broad | 82% | 83% | 96% | 79% | 88% | 88% | 88% | 92% |
| problem_constrained | 17% | 25% | 21% | 38% | 21% | 38% | 33% | 33% |
| expert_context | 4% | 0% | 0% | 0% | 8% | 0% | 4% | 8% |

Six of the 12 broad units fail in **all eight** arms. Most failures in every arm are broad-query failures, so the
broad level mostly measures whether a method happens to pick the one target among many valid answers. This was
already seen in the earlier failure analysis and stage metrics (broad queries state about 0.6 of 2 of the target).
It is a benchmark problem, and no extraction choice fixes it.

### 2. The evidence arrives, but using it doesn't make hypotheses more correct (reasoning)

Retrieval is mostly not the problem. In 83–97% of runs (effects lowest), at least one record that anticipates the
target is in the context (from the evidence-ceiling ratings). Most failures happen *with* such a record cited:

| | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|
| Failures | 26 | 28 | 28 | 28 | 30 | 30 | 32 |
| … no supportive record in context | 2 | 4 | 2 | 6 | 4 | 4 | 7 |
| … supportive record in context, not cited | 1 | 1 | 0 | 3 | 3 | 8 | 7 |
| … supportive record cited | **23** | **23** | **26** | **19** | **23** | **18** | **18** |

Comparing runs of the same paper and query level, citing a supportive record does not raise scores:

| Query level | Units compared | Any supportive record cited vs none (mean difference) | Strongly supportive record cited vs none |
|---|---:|---:|---:|
| broad | 11 / 7 | −0.01 | +0.10 (better in 5 of 7 units) |
| problem_constrained | 9 / 9 | +0.06 | +0.15 (better in 6 of 9 units) |
| expert_context | 8 / 8 | −0.10 | **−0.13 (worse in 6 of 8 units)** |

When the query is open, strongly relevant prior work helps a little. When the query already sets out the system
and problem, citing even strongly relevant prior work goes with lower scores. That fits anchoring: the model copies
the earlier study's specifics instead of reasoning about the target system.

The mechanism-source labels from the target-free audit, within level, show the same thing:

| Mechanism source | problem_constrained: failure rate | expert_context: reconstruction |
|---|---:|---:|
| Model's own reasoning | **16%** (56 runs) | **2.66** (45 runs) |
| Transferred from another system, justified | 41% (27) | 2.21 (7) |
| Transferred from another system, unjustified | 34% (84) | 2.30 (116) |

Wrong mechanism appears in **69–87%** of failing runs in every arm, and in 87% for the mechanisms rubric. Unsupported
evidence claims appear in 79–83% of failing evidence-arm runs (65% for closed-book).

### 3. Some rubrics dilute the context with records that don't help (use)

Share of citations that are supportive records: card **81%**, text chunks 55%, v2 units 53%, mechanisms 44%,
effects 37%, mixed 27%, gaps 25%. The gaps rubric also leaves the most supportive records uncited: 20 of its
72 runs had one in context and didn't cite it.

Rubric-specific breakage, from the failing runs' error codes:

- **effects:** wrong baseline in 54% of failures and evidence contradicted in 29%. Effect records describe other
  base alloys, and the model adopts that baseline. It also has the most runs with no supportive record in
  context (12 of 72): many short records crowd the budget.
- **mechanisms:** wrong mechanism in 87% of failures, the highest of any arm.
- **mixed:** the fewest supportive records in context on average (2.6 against 3.6–4.1), with no supportive
  record in 8 of 72 runs. Its pool of about 1,230 records defeats lexical retrieval.

### 4. Extraction is mostly faithful, but the fields meant to prevent transfer are the weakest (extraction)

| | card | effects | mechanisms | gaps |
|---|---:|---:|---:|---:|
| Fields supported by the paper | 90% | 93% | 87% | 86% |
| Fields distorted (wrong number, scope, system, role) | 9% | 7% | 13% | 10% |
| Fields not in the paper | 1% | 0% | 0% | 4% |
| Records with every field supported | 50% | 65% | **33%** | 70% |
| Records mixing in cited work (despite the own-work rule) | 35% | 15% | 30% | 15% |
| Worst field (share not supported) | key findings 17% | processing 10% | **scope limits 25%**, alternatives 24% | lever 23% |

The mechanisms rubric's scope-limit and alternative-mechanism fields are the least reliable. Those are exactly the
fields that were supposed to stop mechanisms being transferred to the wrong system. Typical distortions: wrong
number or comparison base (an 11.8 nm increase measured from the wrong baseline), wrong condition (annealing
reported where the paper says aging), roles swapped (a comparison sample reported as an alternative mechanism), and
inflated claims (a Laves phase called brittle when the paper doesn't say so). The gaps rubric invents levers 23% of
the time. Quote checking caught invented quotes but not distorted paraphrases, because an item passes if any of
its quotes is real.

### 5. Closed-book generation conflicts with its prompt (generation)

The one reproducible generation failure (closed-book, `PMC11375712` broad, a magnetism paper) was rerun three times.
All three times the model returned the full JSON schema with every field empty, and wrote in `uncertainty` that "the
supplied evidence list is empty… no hypothesis can be generated without violating the constraint to use only
supplied temporally eligible evidence."

- The cause is the shared generation prompt ("Use ONLY the supplied temporally eligible evidence"), which
  conflicts with an empty evidence list.
- The same pressure appears in the closed-book runs that succeeded: **52 of 70** here and **29 of 35** in eval v3
  add a "no supplied evidence" caveat.
- So "closed-book" has really been "closed-book while told to use only evidence". Its scores may understate the
  model's own knowledge, yet it is still the top arm.

### 6. No single arm wins most units

The best arm per unit is spread across all eight arms: closed-book 9, card 9, effects 5, v2 units 4, text chunks 4,
mechanisms 2, gaps 2, mixed 1. The mean gap between the best and worst arm on a unit is 0.68. Choosing per unit (or
combining representations) has more headroom than choosing one rubric.

## Paper-level hot spots

| Paper | Reconstruction | Failure rate | Main error categories |
|---|---:|---:|---|
| PMC12941549 | 0.86 | 73% | wrong conditions 26%, unsupported 17%, wrong mechanism 16% |
| PMC11077685 | 0.95 | 56% | wrong intervention 34%, wrong mechanism 19%, wrong conditions 16% |
| PMC11087546 | 1.47 | 60% | wrong mechanism 22%, unsupported 20%, wrong intervention 17% |
| PMC12806431 | 2.34 | 4% | wrong mechanism 31%, unsupported 28% (minor errors) |

`PMC12941549` asks about conditions the query does not imply. `PMC11077685` has an unusual processing route (3D
ink extrusion of hydrides) that no method proposes. These match the earlier failure analysis.

## Fixes, in order of expected payoff

1. **Fix the benchmark's broad level.** Drop it, score it against several valid targets, or report it separately.
   It accounts for most failures and doesn't discriminate between methods.
2. **Give closed-book its own prompt** ("use your own knowledge; no evidence is supplied") and rerun it. That
   removes the refusal and the caveat pressure, and gives a fair memorisation baseline.
3. **Add a system-match step before evidence use.** For each cited record, state the record's alloy system and
   conditions, how they differ from the target system, and why the claim transfers. Reject unjustified transfers.
   This targets the largest failure (wrong mechanism after citing relevant evidence) and the expert-level
   anchoring.
4. **Re-extract scope fields with quote-level grounding**, so each field must quote its own source sentence. Drop
   sentences with citation markers to enforce the own-work rule, and verify paraphrases (a fidelity pass), not just
   that a quote exists.
5. **Don't serve gaps or mixed pools as primary evidence.** Use cards (81% of citations supportive) or raw text.
   Use better retrieval (embeddings or reranking) before trying large pools.
6. **Use selection or ensembling across representations**, since no arm wins most units.

## Limitations

- "Supportive" means rated as anticipating the target among each representation's 20 records most similar to the
  target. Records outside that top 20 are treated as not supportive, so counts of supportive records in context
  are lower bounds.
- Fidelity, error coding and the ceiling were all rated by GPT-5.6, the same family as the main judge. The fidelity
  check covers 40 random records per rubric. It sees only the source window, so a distortion judged against a
  different window of a long paper could be mislabelled.
- The within-paper comparisons cover 7–11 units per level and are associations, not controlled tests.
- The failure threshold (≤ 1.0) is a choice. The broad-level conclusion holds with any reasonable threshold, since
  broad-level reconstruction averages 0.5–0.8 in every arm.

## Reproduce

```bash
.venv/bin/python failure_rubric.py code-errors --workers 8 --resume   # 549 GPT-5.6 calls
.venv/bin/python failure_rubric.py fidelity --workers 6 --resume      # 160 GPT-5.6 calls
.venv/bin/python failure_rubric.py reproduce                          # needs the local Qwen server on :8000
.venv/bin/python failure_rubric.py report
.venv/bin/python -m unittest test_failure_rubric.py
```
