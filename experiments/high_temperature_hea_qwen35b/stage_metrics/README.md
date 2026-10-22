# Intermediate-stage metrics for all methods

**Date:** 2026-10-22. **Script:** [stage_metrics.py](../../../stage_metrics.py) (tests in `test_stage_metrics.py`,
runner `run_stage_metrics.sh`). **Full tables:** [results/stage_tables.md](results/stage_tables.md).
**Machine-readable:** [results/stage_metrics.json](results/stage_metrics.json).

**What was run.** The proposed metrics were computed for every existing method: closed_book, text_oneshot,
v2_oneshot, tool_agent, resample (a second tool_agent sample), tool_agent_kg, self_revise and critique. That is
288 units (8 methods × 36 paper-by-query units), of which 287 were judged. No method was regenerated. The judge
reliability metrics needed new judgments, so every judged output was rejudged twice by GPT-5.6 and once by a
judge from a different model family.

| Stage | Computation | Calls | Status |
|---|---|---:|---|
| Replay | Deterministic re-execution of every tool run's searches, reads and MatKG lookups, to recover per-step results | 0 | 108 of 108 runs reproduce the stored accessed records exactly |
| Embeddings | `text-embedding-3-large`, 256 dimensions, for queries, search strings, results and interventions | 1,742 texts | done |
| Audit (target-free) | GPT-5.6 per hypothesis: claims and their support, causal chain, contradictions, mechanism source, falsifiability, specificity, stated uncertainty, composition claims | 287 | 0 errors |
| Inferability (diagnostic) | GPT-5.6 per query: how much of the hidden target the query states or implies; answer-space size | 36 | 0 errors |
| Revision review (target-free) | GPT-5.6 per revision: critic-finding validity, uptake and fix type; change type per field | 72 | 0 errors |
| Judge retest | GPT-5.6 judge run twice more on every judged output, same blinded payload | 574 | 0 errors |
| Cross-family judge | `DeepSeek-V4-Pro_2026-04-23` judge on every judged output, same rubric and payload | 287 | 0 errors |

**Leakage.** The audit and revision review are target-free: they never receive the hidden target, which is
asserted on every call and tested. Inferability and the judges read the target, as judges must; nothing they
produce feeds back into any generation. Supportive-evidence metrics reuse the evidence-ceiling ratings from the
failure analysis (records rated as supporting the target's intervention or mechanism among the 20 earlier
records most similar to the target).

## Main findings

1. **The query decides most of the score.** How much of the target the query states or implies correlates
   ρ = 0.82 with reconstruction. Broad queries give away 0.61 of 2 on average and admit "many" valid
   interventions in 11 of 12 cases; expert-context queries give away 1.55.
2. **Agents find the right evidence but don't read it.** Tool agents surface a supportive record in 94–100%
   of runs within about three tool calls, then leave 56–67% of the supportive records they saw unread. They
   read only 6–7% of the supportive records, against 14–27% for the one-shot methods, which see whole records
   by construction. 23–30% of read calls are spent paging through records already open.
3. **Most claims are not grounded.** A hypothesis makes about 19 claims. Only 12–15% are entailed by the
   cited evidence and 33–41% are at least partly supported. Of the supported claims, 48–61% rest on a different
   alloy system. Between 32% and 44% of the numbers in a generated hypothesis cannot be traced to any evidence the
   method saw.
4. **Mechanisms are borrowed without justification.** In 39–56% of evidence-using hypotheses, the mechanism is
   transferred from a different system without justification. Same-system support appears in only 0–19%. This
   quantifies the anchoring seen in the failure analysis.
5. **Critique finds valid problems but fixes few of them.** 70% of critic findings were valid and 20% partly
   valid, yet only 13% were corrected. 36% were hedged, 16% deleted and 35% left alone. Critique halves the
   complete-causal-chain rate (33% against 57–69% elsewhere) and gives the lowest falsifiability score, although
   one critic was checking falsifiability. A verifiable physics error (Nb → Mo said to lower density) survived
   both the self-revise and critique passes.
6. **The judge is reliable; the method ranking is not.** Rejudging gives ICC 0.96 and a per-unit SD of 0.10, so
   most run-to-run variation (0.31 per unit) comes from generation. A second judge from another family agrees on
   units (ρ = 0.90) but is 0.42 more lenient, matches the classification in only 52% of units, and orders the
   methods differently (Kendall τ = 0.32). Both judges score critique lowest (GPT-5.6 on the mean of its three
   judgments); the order of the rest depends on the judge.
7. **Selection has more headroom than any method change.** Picking the better of two tool-agent samples gives
   1.75 (+0.11). Picking the best of the eight methods per unit gives 1.97, 0.33 above the best single method.
   Every method difference measured so far is within 0.15.

## Results by stage

### 1. Query (diagnostic)

| Metric | broad | problem_constrained | expert_context |
|---|---:|---:|---:|
| Target fields stated or implied (mean, 0–2) | 0.61 | 1.05 | 1.55 |
| Intervention stated or implied (share of maximum) | 0.33 | 0.54 | 0.83 |
| Mechanism stated or implied | 0.38 | 0.58 | 0.92 |
| Outcome stated or implied | 0.46 | 0.54 | 0.71 |
| Answer space (cases) | many 11, few 1 | many 12 | few 6, many 5, single 1 |
| Cross-method intervention diversity (embedding distance) | 0.20 | 0.17 | 0.11 |

Inferability vs reconstruction across all units: Spearman ρ = 0.82.

### 2–3. Retrieval and reading

| Metric | text_oneshot | v2_oneshot | tool_agent | resample | tool_agent_kg |
|---|---:|---:|---:|---:|---:|
| Supportive records surfaced (recall) | 0.27 | 0.14 | 0.23 | 0.21 | 0.18 |
| Supportive records read | 0.27 | 0.14 | 0.06 | 0.06 | 0.07 |
| Runs that surfaced any supportive record | 100% | 81% | 100% | 94% | 97% |
| Tool calls to first supportive hit | n/a | n/a | 2.7 | 2.8 | 3.1 |
| Supportive records surfaced but not read | n/a | n/a | 67% | 64% | 56% |
| Search novelty (embedding distance between consecutive searches) | n/a | n/a | 0.24 | 0.25 | 0.27 |
| Result relevance to the task query (cosine) | 0.64 | 0.65 | 0.63 | 0.63 | 0.64 |
| Distinct papers surfaced | 11.8 | 10.9 | 11.3 | 10.6 | 9.1 |
| Read calls spent paging | n/a | n/a | 30% | 23% | 23% |
| Distinct records read per tool call | n/a | n/a | 0.30 | 0.35 | 0.34 |
| Share of read records that get cited | 0.30 | 0.32 | 0.76 | 0.73 | 0.81 |
| Spearman, supportive recall vs score | 0.41 | 0.37 | 0.41 | 0.33 | 0.48 |

The positive recall–score correlations are partly a query-level effect (see the failure analysis, where reading
supportive records did not help within level).

### 4. Grounding (target-free)

| Metric | closed_book | text_oneshot | v2_oneshot | tool_agent | resample | tool_agent_kg | self_revise | critique |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Claims per hypothesis | 17.5 | 19.4 | 19.6 | 19.6 | 19.8 | 19.6 | 19.4 | 18.9 |
| Claims entailed by cited evidence | 0.00 | 0.12 | 0.12 | 0.12 | 0.13 | 0.13 | 0.12 | 0.15 |
| Claims at least partly supported | 0.00 | 0.41 | 0.40 | 0.33 | 0.36 | 0.39 | 0.34 | 0.38 |
| Cited records that support a claim | n/a | 0.88 | 0.83 | 0.98 | 0.86 | 0.88 | 0.93 | 0.94 |
| Supported claims resting on another alloy system | n/a | 0.61 | 0.57 | 0.53 | 0.52 | 0.52 | 0.48 | 0.52 |
| Numbers traceable to evidence the method saw | 0.00 | 0.56 | 0.68 | 0.63 | 0.57 | 0.58 | 0.85 | 0.85 |

Citations are precise (cited records usually support something) but sparse: most claims cite nothing that backs
them. The revision arms' number tracing (0.85) is inflated, because they saw more evidence text (every record the
original agent accessed, up to 3,000 characters) and inherit numbers from the original hypothesis.

### 5. Reasoning (target-free)

| Metric | closed_book | text_oneshot | v2_oneshot | tool_agent | resample | tool_agent_kg | self_revise | critique |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Causal-chain score (0–1) | 0.84 | 0.91 | 0.92 | 0.91 | 0.91 | 0.92 | 0.93 | **0.74** |
| Complete chain (all three links explicit) | 57% | 64% | 61% | 58% | 64% | 67% | 69% | **33%** |
| Contradictions per hypothesis | 0.60 | 0.89 | **1.17** | 0.75 | 0.81 | 0.94 | 0.78 | 0.58 |
| Hypotheses with a contradiction | 43% | 53% | **64%** | 50% | 47% | 50% | 47% | 39% |
| Mechanism transferred without justification | 0% | **56%** | 44% | 42% | 39% | 50% | 44% | 39% |
| Mechanism from same-system evidence | 0% | 0% | 3% | 8% | 17% | 19% | 11% | 11% |

**Physical checks.** The audit extracted only 24 explicit base-to-modified compositions across all methods; most
hypotheses do not state compositions numerically. Seven checks were flagged; manual review found 3 genuine
(the same Nb → Mo density error, carried from tool_agent into self_revise and critique) and 4 false positives
(two "density" claims that meant sintered densification, one identical extracted composition, and one VEC rule
applied to a W–Ni–Fe heavy alloy, where the HEA rule does not hold). The checks catch real errors but need manual
confirmation.

### 6. Hypothesis form

| Metric | closed_book | text_oneshot | v2_oneshot | tool_agent | resample | tool_agent_kg | self_revise | critique |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Hedge words per hypothesis | 0.06 | 0.03 | 0.03 | 0.14 | 0.08 | 0.11 | 0.22 | **3.47** |
| Quantities with units per hypothesis | 3.2 | 5.4 | 5.9 | 6.0 | 6.3 | 6.3 | 6.0 | 4.8 |
| Specificity checklist (0–1) | 0.41 | 0.62 | 0.61 | 0.69 | 0.64 | 0.64 | 0.67 | 0.65 |
| Falsifiability checklist (0–1) | 0.79 | 0.89 | 0.91 | 0.83 | 0.81 | 0.85 | 0.83 | **0.69** |
| Stated uncertainty (0–2) | 1.97 | 1.89 | 1.86 | 1.83 | 1.69 | 1.56 | 1.81 | 1.89 |
| Calibration: Spearman, stated uncertainty vs score | −0.15 | 0.09 | 0.09 | 0.13 | −0.24 | −0.02 | 0.14 | −0.02 |

Every method states high uncertainty, and that uncertainty does not track actual correctness.

| Sampling | Value |
|---|---:|
| tool_agent | 1.64 |
| resample | 1.55 |
| Best of the two tool-agent samples | 1.75 |
| Embedding distance between the two samples' interventions | 0.12 |
| Best of all eight methods per unit | 1.97 |
| Gain over the best single method | 0.33 |

### 7. Critique and revision (target-free review)

| Metric | critique | self_revise |
|---|---:|---:|
| Critic findings reviewed | 306 | n/a |
| Finding validity: valid / partly / invalid | 70% / 20% / 10% | n/a |
| Uptake: addressed / partly / ignored | 39% / 30% / 31% | n/a |
| Fix: corrected / hedged / deleted / none | 13% / 36% / 16% / 35% | n/a |
| Changed fields: corrected / hedged / deleted / rephrased / new claim | 49 / 107 / 23 / 25 / 7 | 3 / 4 / 7 / 6 / 1 |
| Primary dimensions that dropped ≥1 point (harm) | 0.20 | 0.09 |
| Primary dimensions that rose ≥1 point (help) | 0.12 | 0.05 |
| Citations swapped per unit | 0.78 | 0.42 |

For reference, a fresh tool-agent sample (no revision) changes the primary dimensions by at least a point 24%
(down) and 16% (up) of the time, so revisions move scores less than resampling does.

### 8. Knowledge graph

| Metric | Value |
|---|---:|
| KG lookups (36 runs) | 66 |
| KG facts read or cited per lookup | 0.23 |
| Relevance of KG facts to the task query (cosine) | 0.48 |
| Relevance of paper search results (cosine) | 0.64 |
| Searches per run: KG agent / plain agent | 3.8 / 5.9 |
| Supportive recall: KG agent / plain agent | 0.18 / 0.23 |

KG lookups return less relevant text than paper search and displace searches, which lowers supportive recall.

### 9. Judge reliability

| Metric | Value |
|---|---:|
| Units judged three times by GPT-5.6 | 287 |
| Mean within-unit SD of reconstruction | 0.10 |
| Mean absolute difference, original vs rejudgment | 0.15 |
| ICC(1), reconstruction | 0.96 |
| Classification identical across all three judgments | 78% |
| Reference: tool_agent vs resample (generation plus judge) | 0.31 |

| Method | GPT-5.6 original | Mean of 3 GPT-5.6 judgments | DeepSeek-V4-Pro |
|---|---:|---:|---:|
| closed_book | 1.56 | 1.59 | 2.16 |
| text_oneshot | 1.56 | 1.57 | 2.08 |
| v2_oneshot | 1.49 | 1.45 | 1.94 |
| tool_agent | 1.64 | 1.66 | 2.09 |
| resample | 1.55 | 1.55 | 1.96 |
| tool_agent_kg | 1.63 | 1.62 | 1.92 |
| self_revise | 1.60 | 1.65 | 2.16 |
| critique | 1.49 | 1.41 | 1.55 |

| Cross-judge agreement | Value |
|---|---:|
| Spearman, unit scores | 0.90 |
| Mean difference (DeepSeek minus GPT-5.6) | +0.42 |
| Mean absolute difference | 0.54 |
| Kendall τ, method ranking | 0.32 |
| Classification agreement | 52% |

| Style feature | Spearman with score (all units) | Mean within-level Spearman |
|---|---:|---:|
| Length | 0.01 | −0.12 |
| Hedge words | −0.02 | −0.04 |
| Citations | −0.16 | 0.00 |
| Quantities | −0.02 | −0.13 |

The judge does not reward length, hedging, citation count or quantities. Pairwise position consistency: 81%
(eval_v3) and 80% (eval_v4).

### 10. Cost

| Metric | closed_book | text_oneshot | v2_oneshot | tool_agent | resample | tool_agent_kg | self_revise | critique |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Model calls per unit | 1.0 | 1.0 | 1.0 | 11.8 | 11.7 | 11.6 | 12.9 | 15.9 |
| Generation seconds per unit | 33 | 52 | 55 | 77 | 136 | 186 | n/a | n/a |
| Reconstruction per 10 calls | 15.6 | 15.6 | 14.9 | 1.4 | 1.3 | 1.4 | 1.2 | 0.9 |

Token counts were not recorded, so cost is in model calls. Generation time depends on server load (resample and the
KG agent ran while other jobs were active, and KG lookups take up to 35 s), so compare seconds with care.

## What this suggests

1. **Make the agent read what it finds.** It already surfaces supportive records within three calls. Open the
   top results automatically, return longer pages, and stop counting paging against the budget.
2. **Ground claims, not just hypotheses.** Require a citation per claim, and penalise claims supported only by a
   different alloy system unless the transfer is justified.
3. **Force an explicit system-difference step** before borrowing a mechanism (39–56% are transferred without
   justification).
4. **Turn critique into corrections.** Findings are mostly valid; the reviser should be told to correct or delete,
   never to hedge, and to keep the causal chain intact.
5. **Invest in selection.** Best-of-k and choosing between methods per unit gain more (+0.11 to +0.33) than any
   method change so far. A target-free selector could use the audit metrics (grounding, chain completeness,
   contradictions) as signals.
6. **Report results under two judges.** Method rankings change with the judge. Use the mean of repeated judgments
   and a second-family judge, and get the expert calibration set
   ([results/expert_calibration_sheet.md](results/expert_calibration_sheet.md), 30 stratified units) labelled.
7. **Fix the benchmark's broad queries**, which admit many valid answers and give away little of the target.

## Limitations

- The audit, inferability and revision review use GPT-5.6, the same family as the main judge. They are
  target-free (except inferability), but share that model's blind spots. They were not hand-validated in this
  pass; the error-coding spot check in the failure analysis (37 of 40) is the closest check.
- Supportive-evidence metrics depend on the evidence-ceiling oracle, which covers only the 20 records most
  lexically similar to each target. Recall is relative to that set.
- Embedding-based metrics (novelty, relevance, diversity) are relative measures; their absolute values have no
  fixed meaning.
- Number tracing is a string match. It misses reformatted numbers (for example "1,000") and counts coincidental
  matches.
- The composition checks cover only explicit numeric compositions, and the VEC rule applies only to HEA solid
  solutions. Flagged results need manual review.
- Best-of-k uses only two tool-agent samples; more samples would give a better estimate of reachable quality.
- The expert calibration set has been prepared but not labelled.

## Reproduce

```bash
.venv/bin/python stage_metrics.py replay --workers 6 --resume   # deterministic; needs ~/matkg_index/entdoi.sqlite
.venv/bin/python stage_metrics.py embed
bash run_stage_metrics.sh                                       # audit, inferability, revision-review, retest, cross-judge
.venv/bin/python stage_metrics.py report
.venv/bin/python -m unittest test_stage_metrics.py
```
