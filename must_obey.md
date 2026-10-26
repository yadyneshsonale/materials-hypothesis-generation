# must_obey.md: rules for building and evaluating the hypothesis-generation benchmark

These rules apply to **every prompt, change and experiment** in this repository. Read this file before any work.
If a rule cannot be met, stop, write down why, and do not report the result as clean. The automated part of these
rules is [must_obey_check.py](./must_obey_check.py); it must pass before results are reported. Every experiment
README and every [loop.md](./loop.md) entry carries the checklist in section 9.

Last updated: 2026-10-25 (see the change log at the end).

---

## 1. The benchmark

- **Task: retrospective hypothesis reconstruction.** For a held-out paper, the generator receives a research
  question written only from that paper's introduction. It must propose the intervention, mechanism, predicted
  outcome, boundary and falsification test. A judge compares the proposal with a hidden target extracted from the
  paper's results.
- **Corpus.** 50 open-access, high-temperature HEA papers in `experiments/high_temperature_hea_qwen35b/data/corpus`.
  For each case, eligible evidence is the corpus papers with an earliest public date before the case's date,
  excluding the case paper and its work family.
- **Held-out cases (12).** They are split into dev and test:

  | Split | Cases (earliest public date) |
  |---|---|
  | **dev** (8, used for method development) | PMC10759803 (2024-01-02), PMC11077685 (2024-02-28), PMC11087546 (2024-05-10), PMC11355469 (2024-08-07), PMC11375712 (2024-08-22), PMC11375216 (2024-09-04), PMC11775865 (2024-11-21), PMC11606917 (2024-11-29) |
  | **test** (4, used once per pre-registered final configuration) | PMC12029629 (2025-04-19), PMC12298864 (2025-07-09), PMC12806431 (2025-10-27), PMC12941549 (2026-02-16) |
  | **test2** (12, fresh held-out set, used once for the round-2 pre-registered finals) | 12 open-access papers dated 2025-07-01 to 2026-07-01, not in the corpus; 5 are after GPT-5.6's cutoff. Built by [benchmark_test2.py](./benchmark_test2.py) under the rule in [loop.md](./loop.md) section 10.1; cases in `experiments/high_temperature_hea_qwen35b/benchmark_test2/cases` |
  | **test3** (12, fresh held-out set for round 3) | 12 open-access papers dated 2024-01-01 to 2025-06-01, not in the corpus or test2; all precede GPT-5.6's cutoff (flagged). Built by `benchmark_test2.py --set test3` under loop.md 11.1; cases in `experiments/high_temperature_hea_qwen35b/benchmark_test3/cases` |

  test2 and test3 papers are not evidence for any case. Their evidence pool is the 50-paper corpus filtered by date,
  and "all" still means the original 12 cases.
  - **Spent splits.** A held-out split used once for its pre-registered finals is *spent*. It becomes development
    data, and no later claim rests on it.
  - From round 3, development uses **dev3** = dev + test + test2 (24 papers). Claims rest on test3 (loop.md 11.1).

- **Queries.** `experiments/high_temperature_hea_qwen35b/benchmark_v3_1/cases` is the current frozen version
  (section 3).
  - v3.1 fixes the v3 construction error that always asked for an intervention, even when the paper is a study.
  - A gap classifier that sees only the redacted introduction labels each case design, understanding or method.
    Design cases keep their v3 queries; the others are rewritten through the same leakage checker and gate
    ([query_builder_v3_1.py](./query_builder_v3_1.py)).
  - v3 remains valid for experiments 20–22.
- **Hidden targets.** Unchanged since experiment 3 (one answer key for every query version).
- **Levels.** Three query levels (broad, problem_constrained, expert_context); one unit is a paper × level.

## 2. Model knowledge cutoffs

**2.1 Query-facing models must be pre-cutoff.** A "query-facing" model is any model that sees a benchmark query
or influences what is generated. That includes generators, planners, search-phrase writers, retrievers that use an
LLM, critics, revisers, rankers, selectors, tournament judges and summarisers of retrieved evidence. Its documented
knowledge cutoff must be strictly before the earliest public date of **every** case it is run on. A ranker or
selector that knows the paper could recognise the true result among the candidates, so it is query-facing too.

**2.2 Margin.** Prefer at least one month between the model's cutoff and a case's date. Cases inside that margin
are flagged in the results. PMC10759803 (2024-01-02) is 2 days after Llama-3.3's December 2023 cutoff.

**2.3 Memorisation probe.** Before a new generator is used, run
[memorisation_probe.py](./memorisation_probe.py): title and year only, recall scored against the target. Report its
rate of specific recall beside the Llama-3.3 control. A model with a clearly higher rate than the control must not
be used as a generator.

**2.4 Where post-cutoff models are allowed.** Only in roles that cannot change what is generated:
- judges and cross-judges, which see the target in order to score;
- target-free auditors of finished outputs;
- the benchmark query writer and leakage checker, under section 3 (the writer sees only the redacted
  introduction);
- extractors of pre-cutoff papers, which never see a query or target and are audited (section 4.5);
- extractors of a held-out paper's answer key (hidden target) from its non-Introduction sections, which never see
  a query or a generation (test2, loop.md 10.1).

A pre-cutoff model is preferred even in these roles whenever one is good enough.

**2.5 Identity.** Every output records the model's deployment name. Do not mix generators within one comparison,
except in an explicitly declared factorial.

**Model table.** Knowledge cutoffs are from vendor documentation, checked on 2026-10-25. The earliest held-out
paper is 2024-01-02.

| Deployment | Knowledge cutoff (source) | Query-facing use |
|---|---|---|
| Llama-3.3-70B-Instruct_5 | December 2023 ([Meta model card](https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct)) | allowed (flag PMC10759803) |
| gcr-llama-31-8b-instruct | December 2023 ([Meta model card](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct)) | allowed (flag PMC10759803) |
| gpt-4o_2024-11-20 | 2023-10-01 ([OpenAI](https://developers.openai.com/api/docs/models/gpt-4o)) | allowed after a probe; its probe could not complete (rate limited, 0/24 calls on 2026-10-25), so it is not used |
| gpt-4o-mini_2024-07-18 | 2023-10-01 ([OpenAI](https://developers.openai.com/api/docs/models/gpt-4o-mini)) | allowed |
| o1_2024-12-17 | 2023-10-01 ([OpenAI](https://developers.openai.com/api/docs/models/o1)) | allowed (probe: 21% specific recall, all inferable from titles; loop.md 10.4) |
| o3-mini_2025-01-31 | 2023-10-01 ([OpenAI](https://developers.openai.com/api/docs/models/o3-mini)) | allowed |
| o3, o4-mini, gpt-4.1 family, gpt-oss-120b, codex-mini | 2024-06-01 (OpenAI model pages) | forbidden |
| gpt-5, gpt-5.1 / gpt-5-mini, gpt-5-nano | 2024-09-30 / 2024-05-31 (OpenAI) | forbidden |
| gpt-5.2, gpt-5.4 / gpt-5.5 / gpt-5.6 (sol, terra, luna) | 2025-08-31 / 2025-12-01 / **2026-02-16** (OpenAI) | forbidden; gpt-5.6-sol is judge, auditor, query writer and checker only |
| Phi-4 / Phi-4-reasoning / Gemma 3 / Gemma 4 | 2024-06 / 2025-03 / 2024-08 / 2025-01 (model cards) | forbidden |
| Qwen3.5 family (local Qwen3.5-35B-A3B), Qwen2.5-VL, DeepSeek-V3.2/V4, Mistral-Large-3, Kimi-K2.5/K2.6, grok-4.x | not published by the vendor; released 2025–2026 | forbidden. Qwen3.5 only extracts pre-cutoff papers, audited; DeepSeek-V4-Pro is cross-judge only |

The query writer is post-cutoff (gpt-5.6-sol, cutoff 2026-02-16) and could know every held-out paper. It sees only
the redacted introduction, and the separate checker and lexical gate are the safeguards. A pre-cutoff writer is the
preferred future option.

## 3. Input (query) construction: no answer leakage

1. **Source.** Only the held-out paper's introduction, with every sentence announcing the paper's own work
   removed, together with everything after the first such sentence. Never use the title, abstract, methods,
   results, conclusions, figures or supplementary material.
2. **The writer never sees the answer.** No hidden target, result roles or result evidence.
3. **Separate checks.** A separate checker that sees the target lists leaking phrases and judges steering toward
   the answer. A lexical gate requires answer-word overlap ≤ 10% after removing allowed context words (starting
   material, conditions, baseline). Failing levels are rewritten from the checker's phrases (never from the
   target), up to 4 rounds. Levels that still fail are flagged, kept, and results are reported with and without
   them.
4. **Queries are frozen and versioned.** Never edit a query because of a method's score. A new version needs a
   rule-level reason (a construction error found by inspecting queries against targets), must be applied to all
   cases by the same written procedure, and every compared arm must be re-run on it.
5. **Hidden targets are frozen.** One answer key.
6. **Check every new query set.** Answer-word overlap must not predict the score; report Spearman ρ
   ([query_leakage_audit.py](./query_leakage_audit.py) and [compare_rerun.py](./compare_rerun.py)).

## 4. Evidence and tool leakage

1. **Temporal filter per case.** Every evidence record has publication date < the case's earliest public date.
2. **Exclusions.** Exclude the case paper, its work family, its DOI and near-duplicate titles (token Jaccard ≥ 0.8).
3. **Citation graph.** Expansion is backward only. Nodes and citer statements must be before the cutoff, and each
   node is dated by its latest citer.
4. **Knowledge graphs.** Use only tables with a per-record year (MatKG `ENTPTNERDOI`, Year < case year). Never use
   undated co-occurrence files.
5. **LLM-made extractions.** Prefer pre-cutoff extractors. Otherwise audit with
   [extractor_leakage_audit.py](./extractor_leakage_audit.py): the true-case injection rate must not exceed the
   other-case control.
6. **Query-derived text.** Search phrases, sub-questions and hypothetical documents built from the query must be
   written by a pre-cutoff model, from the query only.
7. **No open web search, live literature API or tool that can return post-cutoff documents** for any query-facing
   component, unless the tool applies the date filter and the exclusions of 4.1–4.2 itself and logs what it
   returned.
8. **Logging.** Every run stores the IDs and dates of everything the generator saw. Temporal, test-paper, family,
   target DOI/title and invalid-citation counts must all be zero.

## 5. Payload hygiene

1. **No target in payloads.** No hidden-target field or result-derived text may enter any query-facing payload.
   Enforce this in code with `stage_metrics.assert_target_free`, and test it.
   - The judge sees every field of a generation, so a final hypothesis keeps only the shared schema fields
     (`hypo_loop._schema_only`). A method cannot add extra judged content, such as recalled precedents or notes.
2. **Blinding.** Judges see neutral evidence labels. Selectors and rankers see shuffled candidates with neutral
   labels. Never pass arm names, model names or the held-out paper's ID or title.
3. **Pairwise judgments.** Run every pairwise judgment in both orders, and resolve ties and conflicts by a written
   rule (position bias was 72% in experiment 16).

## 6. Evaluation design

1. **Hold everything else fixed.** Compared arms use the same generator, temperature, evidence budget (16,000
   characters, ≤ 24 records), output cap and number of samples (≥ 2 per unit) unless the variable under test is
   one of these. If it is, say so.
2. **Units and metric.** The unit is a paper × level, with samples averaged. The primary metric is the GPT-5.6
   reconstruction score: the mean of intervention, condition, mechanism and outcome agreement, 0–4.
3. **Secondary metrics.**
   - DeepSeek-V4-Pro cross-judge;
   - all 10 judge dimensions and the classification;
   - target-free audit (chain completeness, specificity, mechanism source);
   - novelty, failures, cost (calls and tokens) and latency.
4. **Statistics.**
   - Paired differences per unit against a named baseline.
   - Paper-clustered bootstrap 95% CI (10,000 resamples, fixed seed, sorted keys).
   - Exact sign test over papers.
   - Holm correction across every comparison in the same family.
   - Report the effect size with its CI, not only p.
5. **Dev/test discipline.**
   - Develop and select methods on dev only.
   - Pre-register the final configurations in [loop.md](./loop.md) before running them on test, and run test once.
   - Report dev, test and all 12 cases.
   - Count every variant tried; this is the garden of forking paths.
   - A held-out split stops being blind once its titles, queries or targets have been seen during development
     (for example printed by an analysis script). New claims then need a fresh held-out set (test2). Scripts must
     not print the content of unused held-out cases.
   - Compare new variants with a fresh-sample replicate of the incumbent, not with its selected dev score (winner's
     curse).
   - Spend a fresh held-out set only on a dev gain over the incumbent whose CI excludes zero. Otherwise report "no
     improvement found". Two dev winners whose CIs crossed zero (loop.md 7, 11.7) failed on fresh papers.
6. **Failures.** Never drop failed runs. Retry once, keep the first attempt in `failed_attempts/`, and report
   failures per arm.
7. **Integrity gate.** Expected runs are present, judged and audited; leakage counts are zero; one generator
   identity per arm.
8. **Judge caveats.**
   - The judge is not calibrated against experts. It rewards closeness to one paper, not truth.
   - Exact values in the targets cap outcome scores.
   - Check that score does not simply track length, hedging or style. Report novelty separately. Do not optimise
     for judge quirks.
9. **Honest scale.** 12 papers (8 dev units ×3, 4 test units ×3) give wide intervals; treat results as
   indicative. Record negative results as fully as positive ones.

## 7. Reproducibility and records

- Write new outputs to new run roots (`MATHG_RUN_ROOT`); never overwrite earlier results.
- Stages are resumable. Runner scripts are committed; logs, errors and status files are not.
- Use fixed seeds and deterministic analysis (iterate over sorted keys).
- **Each experiment produces:**
  - code, tests, results and a README with date, configuration, results, integrity and limits;
  - an entry in `experiments/high_temperature_hea_qwen35b/EXPERIMENT_LOG_2026-10-22.md`;
  - an entry in [loop.md](./loop.md) for method work.
- **Never commit** other sessions' uncommitted files, secrets, raw downloaded papers or large caches.

## 8. Method development (the loop)

Each method or change must:

- cite the article or paper that inspired it, with its URL, and say what was understood and what was
  integrated. Build our own variant; never copy a paper's system wholesale;
- state the failure it targets (from a failure analysis);
- run on dev under this protocol and be compared with the same baselines;
- be recorded in [loop.md](./loop.md) whatever the outcome.

Ablate before combining. Combine only components that helped or that address different failures.

## 9. Checklist (copy into every experiment and loop entry)

- [ ] Query-facing models are all pre-cutoff (section 2 table); new generators have a memorisation probe.
- [ ] Queries are the current frozen version (v3.1, hash checked); no query was edited after seeing results.
- [ ] Evidence: temporal and family filters on; extraction audit clean; no unfiltered web or API tools.
- [ ] Payloads are target-free (asserted in code); judging is blinded; pairwise judgments run in both orders.
- [ ] Dev only during development; test only for pre-registered finals.
- [ ] Same budgets and samples as the baselines, or the difference is declared.
- [ ] GPT-5.6 judge, DeepSeek cross-judge and target-free audit all done; integrity gate passes; failures
  reported.
- [ ] Paired statistics with CIs and Holm; negative results recorded.
- [ ] README, experiment log and loop.md updated; `must_obey_check.py` passes.

## 10. Violations found in earlier work (do not repeat)

| Where | Violation | Fixed by |
|---|---|---|
| Experiments 3–18 | Queries written in the same call that saw the results; 47% of the answer's words in expert queries | benchmark_v3 (experiments 19–20) |
| Experiments 3–18 | Generator Qwen3.5 released after the held-out papers (33% specific recall) | Pre-cutoff generator (experiment 21) |
| Experiment 17 | Search phrases written by the post-cutoff generator from leaky queries | Pre-cutoff writer, clean query |
| Experiment 16 | Selector picked the first candidate 72% of the time | Both-order pairwise rule (5.3) |
| Experiment 21 | Bootstrap CIs depended on Python's hash seed | Sorted keys (6.4) |

## Change log

- 2026-10-24: first version, written from experiments 0–21 and the benchmark survey in
  `experiments/high_temperature_hea_qwen35b/RELATED_WORK.md`.
- 2026-10-25: benchmark v3.1 (question type from the introduction's gap: design, understanding or method) after
  experiment 22 found 4 of 12 study-type targets unreachable under intervention-only questions. The rule was
  applied blind and not adjusted after seeing which cases changed. Two processing-route targets (PMC12298864,
  PMC12941549) now carry understanding questions because their introductions state an understanding gap; this is
  recorded as a caveat.
- 2026-10-25: the six pre-registered loop configurations ran once on test under these rules (loop.md section 7).
  No rule changed. Lesson recorded for future loops: a dev gain from a harness on a weak model (Llama
  `scaffold_ensemble`, +0.10) did not replicate on test (−0.09). Report the core metric (intervention + mechanism)
  next to reconstruction, because the test gain was in conditions and outcome, not the intervention.
- 2026-10-25 (round 2):
  - The test split's titles were printed by a probe analysis and one target was quoted in experiment 22, so test
    is no longer blind. A fresh held-out set, test2, was added under a rule pre-registered before any search
    (loop.md 10.1).
  - New allowed role: answer-key extraction by a post-cutoff model.
  - New discipline rules: do not print unused held-out content; compare with a fresh-sample replicate of the
    incumbent.
  - o1 cleared by its memorisation probe.
  - `must_obey_check.py` freezes test2 queries and requires test2 runs to be final.
- 2026-10-25 (round 3):
  - test and test2 are spent and form the development set dev3 with dev (24 papers).
  - test3, 12 fresh papers from 2024-01 to 2025-06, was built under a rule pre-registered before any search
    (loop.md 11.1). `must_obey_check.py` requires final runs only on unspent held-out splits (test3).
  - Final hypotheses are restricted to the schema fields.
  - gpt-4o is not used: its memorisation probe could not complete because of rate limits.
- 2026-10-25 (experiment 29, sensitivity): no rule changed. Finding recorded for method design: on this task, a few
  paper summaries as context lower the score (anchoring on a predecessor's study), and more papers or more relevant
  papers do not raise it above closed-book. Evidence must be shown to help on held-out papers, not assumed to.
