# Experiment 23: benchmark v3.1 (question type from the introduction's gap) and model clearance

**Date.** 2026-10-25.
**Code.**
- [query_builder_v3_1.py](../../../query_builder_v3_1.py)
- [memorisation_probe.py](../../../memorisation_probe.py)
- [must_obey_check.py](../../../must_obey_check.py)

**Rules.** [must_obey.md](../../../must_obey.md), first written in this experiment.
**Write-up.** [loop.md](../../../loop.md), sections 0 and 4 (iteration 0).

## Why

Experiment 22 found a construction error in benchmark v3. Every question asked for "a single intervention", but 4
of 12 hidden targets are studies. Those cases could not be reached.

## Rule (applied to all 12 cases, blind to targets and results)

1. A gap classifier (GPT-5.6) reads only the redacted introduction, with the paper's own contribution removed. It
   labels the gap the introduction motivates as one of:
   - design: a limitation to overcome;
   - understanding: an unknown behaviour or mechanism;
   - method: a limitation of existing methods or tools.
2. Design cases keep their v3 queries.
3. Understanding and method cases are rewritten by the v3 writer with a template for their gap type. The writer
   never sees the answer. The leakage checker, the lexical gate (answer-word overlap ≤ 10%) and up to 4 rewrite
   rounds apply unchanged.
4. The hidden targets are unchanged (one answer key). `cases/` is frozen; its SHA-256 hashes are checked by
   `must_obey_check.py --bench v3.1`.

## Result

| Split | Kept (design) | Rewritten |
|---|---|---|
| dev | PMC10759803, PMC11077685, PMC11087546, PMC11375712 | PMC11355469, PMC11775865 (understanding); PMC11375216, PMC11606917 (method) |
| test | – | PMC12029629, PMC12298864, PMC12806431, PMC12941549 (all understanding) |

- **Overlap:** mean answer-word overlap is 2.1% (broad), 5.0% (problem) and 4.0% (expert).
- **Gate:** 34 of 36 levels pass. PMC11606917's problem (8.2%) and expert levels fail the checker or gate after 4
  rounds. They are flagged and kept.
- **Caveat:** two processing-route targets (PMC12298864, PMC12941549; both test) now carry understanding questions,
  because their introductions state an understanding gap. The rule was not adjusted after seeing this.
  `build_log/` holds the classifier's evidence and every rewrite round.

## Model clearance (must_obey.md section 2)

- **Cutoffs:** knowledge cutoffs come from vendor documentation (table in must_obey.md). Only Llama-3.3 and 3.1
  (December 2023) and gpt-4o, gpt-4o-mini, o1 and o3-mini (2023-10-01) are pre-cutoff for every case.
- **Memorisation probe:** title and year only, 12 papers × 2 samples, recall scored by GPT-5.6 against the target.
  Runs are in `benchmark_v3/memorisation_probe/runs`.

| Model | Specific recall | Use |
|---|---:|---|
| Qwen3.5 | 33% | forbidden |
| Llama-3.3 | 8% | allowed |
| o3-mini | 17% | allowed; every hit is inferable from the title |
| gpt-4o-mini | 0% | allowed |

## Limits

- The query writer and gap classifier (GPT-5.6, cutoff 2026-02-16) are post-cutoff. They see only the redacted
  introduction; the separate checker and the lexical gate are the safeguards.
- The gap classifier is a single model call per case, not validated by an expert.
