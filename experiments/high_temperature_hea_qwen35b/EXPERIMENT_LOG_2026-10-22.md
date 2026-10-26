# Experiment log: high-temperature HEA hypothesis generation (experiments 0 to 29)

Related work (9 hypothesis-generation and materials-KG papers, with how each separates input from answer):
[RELATED_WORK.md](./RELATED_WORK.md).

This document is the full record of every experiment on the 50-paper high-temperature HEA corpus: date,
configuration, results, integrity and status. Experiments 0 to 7 are described in detail in the committed
[EXPERIMENT_LOG.md](./EXPERIMENT_LOG.md) and summarised here. Experiments 8 to 11 are documented in full here,
and they supersede section 8 ("MatKG, planned, blocked") of that log. The committed log is not edited here,
because its working-tree copy has uncommitted changes from another session (it is empty in the working tree).
Once that is resolved, this document can be merged into the log.

Last updated 2026-10-25. Experiment 29 (sensitivity) shows that **adding research papers as context lowers the score**. One to three paper summaries cost 0.10 on GPT-5.6 and 0.24 on DeepSeek (replicated on test3; pooled over 36 papers, sign p ≤ 0.024). Thirty papers return toward the no-paper level without exceeding it. Raw text, relevance and reasoning effort have no significant effect. Round 3 adds experiments 27 (test3: 12 more fresh held-out papers) and 28 (writer-level
methods developed on 24 papers, with a pre-registered test3 evaluation). **No further increase was found.** The
round-3 dev winner failed on test3. Over all 28 fresh held-out papers, o3-mini with the conservative writer (one
call) scores 0.60 against 0.49 for the Llama baseline (GPT-5.6, sign p = 0.009). Round 2 added experiments 25
(test2: 12 fresh held-out papers, 5 of them after every model's cutoff) and 26 (method iterations 6–8 and the
pre-registered test2 evaluation). **On fresh papers the best-supported configuration is o3-mini with the
conservative writer (one call); the round-1 harness beats the baseline but adds nothing over that model.** The previous update added experiments 22 (failure analysis of the
clean rerun), 23 (benchmark v3.1, the [must_obey.md](../../must_obey.md) rules and model clearance) and 24 (a
harness-engineered method loop with a pre-registered test; full write-up in [loop.md](../../loop.md)). **All work
from experiment 23 on follows must_obey.md.** The 2026-10-24 update added experiments 17–18 (citation-graph variants and their failure analysis),
19 (the benchmark queries leak the answer), 20 (leak-free benchmark v3) and 21 (every evaluation rerun on it with a
pre-cutoff generator). **Read experiments 19 to 21 before using any absolute score or query-level effect from
experiments 3 to 18.**

Dates are the dates the runs or commits were made (Pacific time for 2026-10-21 and 2026-10-22 runs).

## All experiments

| # | Dates | Experiment | Scale | Generator | Judge | Status | Main location |
|---|---|---|---|---|---|---|---|
| 0 | 2026-09-17 to 2026-09-18 | Early workflow, 67-paper evidence graph, gold comparison | 67 papers; 7 gold papers | Earlier pipeline | Earlier judge | Historical | [README.md](../../README.md) |
| 1 | 2026-09-23 | Screened 50-paper HEA corpus and extraction recall | 50 papers | Qwen3.5-35B-A3B | none | Complete | [data/](./data/) |
| 2 | 2026-10-02 | Grounded role and question extraction, review interface, reader questions | 50 papers | Qwen | none | Complete | [outputs/](./outputs/) |
| 3 | 2026-10-03 to 2026-10-04 | Temporal hypothesis reconstruction v2 (4 representations) | 12 cases, 144 runs | Qwen | Qwen | Complete | [temporal_v2/](./temporal_v2/) |
| 4 | 2026-10-05 | Question-centred evidence pipeline and benchmark | 8,848 questions, 180 runs | Qwen | Qwen | Complete | [question_centered/](./question_centered/) |
| 5 | 2026-10-06 | Section-aware data-extraction agent | 50 papers, 276 triggers | Qwen | none (exact-span validation) | Complete | [section_aware/](./section_aware/) |
| 6 | 2026-10-19 | Numbered output bundles and v2 evidence documentation | 50 papers | none | none | Complete | [outputs/](./outputs/) |
| 7 | 2026-10-21 | Temporal eval v3: cutoff-audited tool agent vs baselines | 12 cases, 144 runs | Qwen | TRAPI GPT-5.6 | Complete; 1 unit missing (not verified) | [eval_v3/](./eval_v3/) |
| 8 | 2026-10-21 | MatKG download, data check and leakage design (replaces the "blocked" status) | 1.2 GB of MatKG files | none | none | Complete (see correction below) | [matkg/](../../matkg/) (not committed) |
| 9 | 2026-10-22 | MatKG temporal index and augmented tool agent (eval v4) | 84.1 M rows; 12 cases, 36 KG runs | Qwen | TRAPI GPT-5.6 | Complete; 1 baseline unit missing (not verified) | [eval_v4_matkg/](./eval_v4_matkg/) |
| 10 | 2026-10-22 | Citation-graph and citation-count paper selection | 50 corpus papers; 224 candidates; 37 with PMC text | none | none | Complete (analysis only) | [citation_graph/](./citation_graph/) |
| 11 | 2026-10-22 | Critique-augmented hypothesis revision (3 critics + reviser, self-revise control, fresh baseline) | 12 cases, 36 units per arm | Qwen (baseline), Llama 3.3 70B (reviser) | TRAPI GPT-5.6 | Complete, verified | [eval_critique/](./eval_critique/) |
| 12 | 2026-10-22 | Failure analysis across all 8 methods (error coding, evidence ceiling, confound checks) | 288 units, 1,087 fatal errors | none | GPT-5.6 (coder) | Complete (analysis only) | [failure_analysis/](./failure_analysis/) |
| 13 | 2026-10-22 | Intermediate-stage metrics for all 8 methods (replay, grounding audit, inferability, critique review, judge retest, cross-family judge) | 288 units; 1,256 LLM calls; 108 replays | none | GPT-5.6 (×3), DeepSeek-V4-Pro | Complete (analysis only) | [stage_metrics/](./stage_metrics/) |
| 14 | 2026-10-22 to 2026-10-23 | Extraction rubrics (card, effects, mechanisms, gaps, mixed) vs raw text, v2 units and closed-book, equal evidence budget, 2 samples | 50 papers × 4 rubrics extracted; 576 runs | Qwen | GPT-5.6, DeepSeek-V4-Pro | Complete; 2 runs (1 closed-book unit) failed after retry | [rubric_eval/](./rubric_eval/) |
| 15 | 2026-10-23 | Failure analysis of experiment 14 (extraction fidelity, retrieval, evidence use, error coding, reproduced generation failure) | 574 runs, 2,282 fatal errors, 160 records checked | none | GPT-5.6 (coder) | Complete (analysis only) | [rubric_eval/failure/](./rubric_eval/failure/) |
| 16 | 2026-10-23 | Targeted improvements (fixed closed-book prompt, system-match appraisal on text and cards, knowledge-first refinement, ensemble selection) vs experiment-14 baselines | 288 new runs + 72 selections | Qwen | GPT-5.6, DeepSeek-V4-Pro | Complete, verified | [improvements/](./improvements/) |
| 17 | 2026-10-23 | Citation-graph evidence: per-case graph of 10 best-cited relevant seeds + co-cited references, node profiles with citer statements; 5 variants (selection, profiles, profiles + system-match, corroboration-weighted, graph tool agent) | 264 full-text papers, 9,899 citer statements, 12 graphs; 360 runs | Qwen | GPT-5.6, DeepSeek-V4-Pro | Complete, verified; 1 run failed after retry | [citegraph/](./citegraph/) |
| 18 | 2026-10-23 | Failure analysis of experiment 17 (statement fidelity, graph evidence ceiling, retrieval and use, error coding, tool traces) | 90 statements, 24 ceilings, 408 runs coded | none | GPT-5.6 (checker, coder) | Complete (analysis only) | [citegraph/failure/](./citegraph/failure/) |
| 19 | 2026-10-23 | Audit of answer leakage in the benchmark queries (roles used to write each query, answer-word overlap, correlation with scores) | 36 queries; 7 methods | none | none | Complete (analysis only); affects experiments 3 to 18 | [query_leakage/](./query_leakage/) |
| 20 | 2026-10-23 | Leak-free benchmark v3 (introduction-only queries, writer never sees the answer, separate checker, lexical gate) and generator memorisation probe | 12 cases × 3 levels; 48 probes | GPT-5.6 (writer, checker) | GPT-5.6 | Complete; 34/36 queries pass the gate | [benchmark_v3/](./benchmark_v3/) |
| 21 | 2026-10-23 to 2026-10-24 | All evaluations (experiments 7, 9, 11, 14, 16, 17) rerun on benchmark v3 with a pre-cutoff generator, plus a generator × queries factorial | 1,512 generation runs + 72 selections + 288 factorial runs | Llama-3.3-70B (cutoff 2023-12) | GPT-5.6, DeepSeek-V4-Pro | Complete; verified except 1 critique resample run | [rerun_v3/](./rerun_v3/) |
| 22 | 2026-10-24 to 2026-10-25 | Failure analysis of the clean rerun (lever match, question fit, coverage, error mix, judge agreement) | 1,476 hypotheses, 26 arms | none | GPT-5.6 (labeller, coder) | Complete (analysis only) | [rerun_v3/failure/](./rerun_v3/failure/) |
| 23 | 2026-10-25 | Benchmark v3.1 (question type from the introduction's gap), must_obey.md rules and checker, memorisation probes of o3-mini and gpt-4o-mini | 12 cases × 3 levels; 48 probes | GPT-5.6 (classifier, writer, checker) | GPT-5.6 | Complete; 34/36 levels pass the gate | [benchmark_v3_1/](./benchmark_v3_1/) |
| 24 | 2026-10-25 | Harness-engineered method loop (5 iterations, 29 configurations on dev) and a pre-registered test of 6 configurations | 1,392 dev runs + 144 test runs | Llama-3.3-70B, o3-mini, gpt-4o-mini (all pre-cutoff) | GPT-5.6, DeepSeek-V4-Pro | Complete, verified (`must_obey_check.py --loop` passes on all 29 configurations) | [loop/](./loop/), [loop.md](../../loop.md) |
| 25 | 2026-10-25 | Fresh held-out test set (test2) by a rule pre-registered before any search: 12 open-access papers, 2025-07 to 2026-07, 5 after GPT-5.6's cutoff | 41 screened, 12 cases × 3 levels | GPT-5.6 (screen, target extractor, writer, checker) | none | Complete; 34/36 levels pass the gate | [benchmark_test2/](./benchmark_test2/) |
| 26 | 2026-10-25 | Method loop round 2 (iterations 6–8: niche occupation, o1, BM25, planner/executor, iterative retrieval, relevance-focused grounding; offline voting and consensus checks) and the pre-registered test2 evaluation | 480 dev runs + 360 test2 runs | o3-mini, o1, Llama-3.3-70B (all pre-cutoff) | GPT-5.6, DeepSeek-V4-Pro | Complete, verified | [loop/](./loop/), [loop.md](../../loop.md) section 10 |
| 27 | 2026-10-25 | Fresh held-out test set test3 (12 papers, 2024-01 to 2025-06) by a rule pre-registered before any search | 37 screened, 12 cases × 3 levels | GPT-5.6 (screen, target extractor, writer, checker) | none | Complete; 35/36 levels pass the gate | [benchmark_test3/](./benchmark_test3/) |
| 28 | 2026-10-25 | Method loop round 3 on dev3 (24 papers): forecasting framing, recalled analogies, high reasoning effort, MBR, evidence, evidence + MBR; offline selector checks; pre-registered test3 evaluation | 1,008 dev3 runs + 288 test3 runs | o3-mini, Llama-3.3-70B (pre-cutoff) | GPT-5.6, DeepSeek-V4-Pro | Complete. Exception: dev3 round-3 runs are judged but mostly not audited (GPT-5.6 rate limits) | [loop/](./loop/), [loop.md](../../loop.md) section 11 |
| 29 | 2026-10-25 | Sensitivity of the score to one input at a time: papers as context (0–30), raw text (0–64k characters), relevance vs random papers, reasoning effort, question detail; replication of the paper-count dip on test3 | 1,152 dev3 runs + 216 test3 runs | o3-mini (pre-cutoff) | GPT-5.6, DeepSeek-V4-Pro | Complete | [loop/](./loop/), [loop.md](../../loop.md) section 12 |

## Correction to section 8 (MatKG)

The committed section 8 said MatKG "does not store dates" and that OpenAlex or Crossref would be needed for
publication dates. That is incorrect for the per-DOI table `ENTPTNERDOI.csv`. Each row carries a `Year`
value for its DOI, and the index filters on it directly. The co-occurrence file `SUBRELOBJ.csv` has no DOI or
year and cannot be date-filtered, so it is not used. The rest of section 8's leakage analysis still holds, and
it is what the design implements.

The section 8 blocker is also resolved. The MatKG files are in `matkg/` (five files, about 3.8 GB, CC BY 4.0), and that folder is excluded from git.

## Shared configuration

Experiments 7, 9 and 11 use one evaluation protocol. Only the setting or arm under test changes between them.

**Data and units**

| Item | Value |
|---|---|
| Corpus | 50 open-access, non-review high-temperature HEA papers (JATS XML) |
| Held-out cases | 12 papers (`temporal_v2/benchmark_cases/`), each with a hidden target |
| Query levels | `broad`, `problem_constrained`, `expert_context` (3 per case) |
| Units per setting or arm | 12 × 3 = 36 |
| Cutoff | The held-out paper's earliest public date (range 2024-01-02 to 2026-02-16) |
| Eligible records | Published before the cutoff, not the held-out paper, not in its work family |

**Generator (local)**

| Item | Value |
|---|---|
| Model | Qwen3.5-35B-A3B, Q4_K_M GGUF, served by llama.cpp `llama-server` |
| Hardware | 4 × Tesla V100-DGXS (32 GB each), `--n-gpu-layers 99`, `--split-mode layer` |
| Server | `--ctx-size 131072 --parallel 4` (32k context per slot), `--jinja`, `--flash-attn off` |
| Sampling | `--temp 0.2`; request `temperature` 0.2 for the tool agent |
| Thinking | Disabled (`enable_thinking: false`). No hidden reasoning is generated |
| Output cap | `max_tokens` 5000 for every setting (aligned in commit `072cecd`) |
| Timeout | 300 s per request |

**Settings**

| Setting | What it sees | Citable records |
|---|---|---|
| `closed_book` | Query and cutoff | None |
| `text_oneshot` | Top 14 text chunks from eligible papers (one prompt) | Those 14 |
| `v2_oneshot` | Top 14 v2 evidence units from eligible papers (one prompt) | Those 14 |
| `tool_agent` | Query and cutoff; tools `list_papers`, `search_corpus` (k ≤ 8), `read_record` (2400-char pages), `submit_hypothesis` | Records the agent has read |
| `tool_agent_kg` (exp 9) | As `tool_agent`, plus `kg_lookup(topic)` | As above, plus MatKG facts once read |

Tool-agent budget: at most 12 tool calls and 16 model turns. Calls past the budget are refused and logged.
Submissions that cite an unread record are rejected with the reason, and the agent may resubmit.

**Judge (blinded)**

| Item | Value |
|---|---|
| Model | GPT-5.6 on TRAPI, deployment `gpt-5.6-sol_2026-07-09` (chosen; `luna` and `terra` were reachable but not compared) |
| Request | JSON object, `max_completion_tokens` 12000, no temperature |
| Absolute scoring | 10 integer dimensions, 0 to 4, plus one classification |
| Pairwise scoring | Both presentation orders. If the verdict flips with order, it is a tie |
| Blinding | Record IDs, source kinds, citation metadata and setting names removed. Cited records relabelled E1, E2, … Evidence text is shown, up to 1200 characters per record |
| Retries | Rate limits (HTTP 429) are retried after the wait TRAPI reports |

**Statistics (pre-specified in code)**

| Item | Value |
|---|---|
| Primary metric | Reconstruction mean: mean of intervention, condition, mechanism and outcome scores (0 to 4) |
| Unit for inference | Paper (per-paper mean of its query-level differences) |
| Interval | Paper-clustered bootstrap, 10,000 resamples, seed 20260421 |
| Test | Two-sided exact sign test on per-paper differences |
| Multiplicity | Holm correction across the primary comparisons of each experiment |
| Integrity gate | `verified` requires every expected run and judgment present, zero failed runs, zero judge errors, zero temporal, leak, unknown-ID or invalid-citation violations, and one generator and one judge identity |

## Experiment 9: MatKG temporal index and augmented tool agent

**Question.** Does giving the cutoff-audited tool agent access to MatKG co-occurrence facts (built only from
papers before the cutoff year) improve reconstruction of held-out HEA papers?

**Method.**

1. Index: [matkg_index.py](../../matkg_index.py) streams `ENTPTNERDOI.csv.tar.gz` into SQLite
   (84.1 M rows, 4.14 M DOIs, years 1885 to 2023, built 2026-10-22 00:15 to 00:26 PDT).
2. Tool: `kg_lookup(topic)` returns neighbours of query terms, ranked by association, from papers with
   `Year < cutoff year`, excluding the held-out DOI and its work family. Each fact is a readable record, so
   the read-before-cite rule still applies.
3. Evaluation: [temporal_eval_kg.py](../../temporal_eval_kg.py), with the same generator, budget (12
   calls), temperature (0.2), blinding, judge (GPT-5.6) and statistics as v3. Baseline runs and absolute
   judgments are copied from v3 ([eval_v4_matkg/](./eval_v4_matkg/)).
4. Pipeline: [run_eval_kg.sh](../../run_eval_kg.sh), in tmux session `mathg-eval-kg`. Generation ran
   2026-10-22 00:30 to 00:59 PDT and judging 00:59 to 01:20 PDT. A bug in the analysis
   (`NameError` in case loading) was fixed and the analysis re-run at 01:21.

**Results.**

| Setting | Reconstruction | Overall | Runs citing a KG fact | KG facts cited |
|---|---:|---:|---:|---:|
| tool_agent_kg | 1.63 | 1.85 | 5 of 36 | 11 |
| tool_agent (v3) | 1.64 | 1.84 | 0 | 0 |
| text_oneshot (v3) | 1.56 | 1.90 | 0 | 0 |
| closed_book (v3) | 1.56 | 1.89 | 0 | 0 |
| v2_oneshot (v3) | 1.49 | 1.85 | 0 | 0 |

- KG minus tool agent: −0.01 (95% CI −0.12 to +0.11; Holm p = 1.00). Pairwise: KG wins 10, loses 18.
- KG minus v2 one-shot: +0.15 (95% CI +0.06 to +0.24), but Holm p = 0.44, so not significant after correction.
- Integrity: 0 temporal violations, 0 test-paper or family leaks, 0 invalid citations, 0 judge errors. The
  gate reports `verified: false` because the v3 closed-book unit `PMC11375712` (broad) is missing, as in v3.

**Interpretation.** Adding MatKG did not change reconstruction, and the agent rarely cited KG facts (5 of 36
runs). The test therefore says little about whether a materials knowledge graph helps. A stronger test would
require KG use or a narrower relation type.

Full details: [eval_v4_matkg/README.md](./eval_v4_matkg/README.md).

## Experiment 10: citation-graph and citation-count paper selection

**Question.** Can citation links and citation counts improve how the 50-paper corpus is selected?

**Method.** The corpus was selected on Europe PMC citation counts. This analysis uses OpenAlex metadata and
reference lists for the 50 corpus papers, an in-corpus citation graph with PageRank, and candidates that
cite the top 10 seeds. Candidates must be open-access alloy articles (not reviews, not catalysis or battery
work) and must have PMC full text, checked in Europe PMC. Three scores are compared against the current
selection: citation count per year, bibliographic coupling with the corpus, and a combination of the two.
See [citation_graph/README.md](./citation_graph/README.md) and [citation_graph.py](../../citation_graph.py).

**Results.**

| Selection (top 50 of 87) | Kept from current corpus | New | Share with a high-temperature term in title |
|---|---:|---:|---:|
| current corpus | 50 | 0 | 60% |
| graph coupling | 42 | 8 | 54% |
| combined | 32 | 18 | 48% |
| citation count only | 24 | 26 | 40% |

Within the corpus there are 21 links among 50 papers; 26 papers have at least one link.

**Interpretation.** Ranking by citation count alone drifts away from the high-temperature topic. Graph
coupling stays closest to it. Neither has been tested against hypothesis quality, so the current corpus should
not change until a combined rule with a topic filter has been evaluated.

## Experiment 11: critique-augmented hypothesis revision

**Question.** Does a panel of critic LLMs, each checking one aspect of a tool-agent hypothesis against the
evidence the agent read, improve the hypothesis when a reviser rewrites it?

**Method.** The baseline is the 36 `tool_agent` runs of experiment 7, reused without regeneration. Three arms
were run on top of them:

- `critique`: three critics in sequence (evidence, consistency, falsifiability), then the reviser with their
  findings.
- `self_revise` (control): the reviser alone, asked to check and revise its own hypothesis. This separates the
  effect of critiques from the effect of an extra revision pass.
- `resample` (noise check): a fresh `tool_agent` sample with the same settings, to measure run-to-run variation.

Each revised or resampled hypothesis is judged by the same blinded GPT-5.6 judge as experiment 7.

**Critic and reviser configuration**

| Stage | Model (TRAPI deployment) | Knowledge cutoff | Temperature | Output cap | Role |
|---|---|---|---|---|---|
| Evidence critic | Llama 3.3 70B Instruct (`Llama-3.3-70B-Instruct_5`) | Dec 2023 | 0.0 | `max_tokens` 3000 (71 units); 6000 (1 unit rerun after truncation) | Each supporting claim is backed by the text of the record it cites |
| Consistency critic | OpenAI o1 (`o1_2024-12-17`) | Oct 1, 2023 | not set (o-series) | `max_completion_tokens` 12000 (reasoning tokens count against it) | Arithmetic, composition, direction of property changes, phase plausibility |
| Falsifiability critic | GPT-4o (`gpt-4o_2024-11-20`) | Oct 1, 2023 | 0.0 | `max_completion_tokens` 3000 | Experiment concreteness, measurable thresholds, specific boundary and uncertainty |
| Reviser | Llama 3.3 70B Instruct (`Llama-3.3-70B-Instruct_5`) | Dec 2023 | 0.0 | `max_tokens` 8000 | Rewrites the 14 hypothesis fields; one repair attempt on invalid citations, then keeps the original |

Critics return at most 8 findings each, with a type (unsupported, miscited, inconsistent, implausible,
untestable, other), severity 1 to 3, the evidence labels relied on, and a suggested fix. They do not write a
hypothesis. Critic inputs show up to 3000 characters per record.

**Model selection by cutoff.** The held-out papers date from 2024-01-02 to 2026-02-16, so each critic and the
reviser must have a training cutoff before 2024-01-02. The rule is checked at run time, and tests cover it.

| Model | Cutoff | Source | Decision |
|---|---|---|---|
| Llama 3.3 70B | Dec 2023 | Meta model card, fetched (llama-models `llama3_3/MODEL_CARD.md`) | Used |
| o1 | Oct 1, 2023 | OpenAI model page, fetched | Used |
| GPT-4o | Oct 1, 2023 | OpenAI model page, fetched | Used |
| GPT-OSS-120B | June 2024 | Web search summary; official page not fetched | Excluded (after cutoff) |
| Mistral Large 3 | Oct 2024 | Third-party listing | Excluded (after cutoff) |
| DeepSeek-V3.2 | May 2025 | Third-party listing | Excluded (after cutoff) |

The other deployments on the TRAPI list were not checked individually. They were not used, because they are
later models whose cutoffs were not confirmed from the sources consulted.

**Leakage controls**

1. The hidden target is never sent. Critic and reviser payloads have a fixed key set. `assert_payload` rejects
   any other key and any payload containing `hidden_target`, on every call.
2. Records from the held-out paper or its work family are rejected before any critic runs
   (`assert_no_target_records`).
3. Critic inputs use blinded labels (E1, E2, …). Findings are mapped back to real record IDs for the reviser.
4. Model cutoffs are checked before the run starts.
5. The judge sees the revised hypothesis under the same blinding as experiment 7.

**Run history**

| Date (PDT) | Event |
|---|---|
| 2026-10-22 ~02:05 to 02:20 | Module written; 14 unit tests added; smoke test on one case (PMC10759803) |
| Smoke | Found and fixed: prompt-formatting bug (`KeyError` from `str.format` on JSON braces); o1 truncated at 3000 tokens (raised to 12000); reviser truncated at 5000 (raised to 8000); one evidence-critic unit truncated at 3000 (raised to 6000 and that unit rerun). Smoke outputs were deleted before the full run |
| 02:24 | Full run started in tmux `mathg-eval-critique` |
| 02:24 to 02:45 | Baseline resample generated (36 of 36) |
| 02:45 to 02:47 | Baseline resample judged (36 of 36) |
| 02:47 to 03:02 | Revisions generated: 72 of 72 (one critique unit `critic_incomplete`, from the evidence-critic cap) |
| 03:02 to 03:06 | Judging: 71 of 72 revisions judged. Integrity gate reported "not verified" for the one incomplete unit |
| 03:06 to 03:09 | Incomplete unit rerun with the 6000-token cap, judged, analysed. Integrity verified. Pipeline rerun to write the final status |

**Results.** Reconstruction (0 to 4), 36 units per arm:

| Arm | Reconstruction | Overall (10 dims) | Classifications (exact / partial / plausible / unsupported) |
|---|---:|---:|---|
| original (experiment 7 `tool_agent`) | **1.64** | 1.84 | 1 / 20 / 6 / 9 |
| resample (fresh sample, noise check) | 1.55 | 1.82 | 0 / 18 / 7 / 11 |
| self_revise (reviser only) | 1.60 | 1.79 | 1 / 19 / 7 / 9 |
| critique (3 critics and reviser) | 1.49 | 1.64 | 0 / 16 / 7 / 13 |

| Comparison | Mean difference | 95% CI (papers bootstrap) | Papers A higher / B higher | Sign-test p | Holm p |
|---|---:|---|---:|---:|---:|
| critique − original | −0.15 | −0.36 to +0.03 | 2 / 8 | 0.109 | 0.328 |
| self_revise − original | −0.04 | −0.10 to +0.02 | 3 / 7 | 0.344 | 0.688 |
| critique − self_revise | −0.11 | −0.31 to +0.07 | 4 / 7 | 0.549 | 0.688 |
| resample − original (noise) | −0.09 | −0.19 to +0.01 | 2 / 8 | 0.109 | n/a |

Dimension means, original vs critique (0 to 4):

| Dimension | Original | Critique | Change | Self-revise |
|---|---:|---:|---:|---:|
| problem alignment | 3.19 | 2.89 | −0.31 | 3.19 |
| intervention reconstruction | 1.83 | 1.83 | 0.00 | 1.86 |
| condition agreement | 1.36 | 1.36 | 0.00 | 1.33 |
| mechanism agreement | 1.67 | 1.39 | −0.28 | 1.53 |
| outcome agreement | 1.69 | 1.36 | −0.33 | 1.67 |
| baseline quality | 1.97 | 1.89 | −0.08 | 1.92 |
| boundary quality | 1.58 | 1.31 | −0.28 | 1.64 |
| experiment discriminability | 2.25 | 1.89 | −0.36 | 2.22 |
| evidence validity | 0.92 | 1.00 | +0.08 | 0.81 |
| novelty | 1.97 | 1.47 | −0.50 | 1.78 |

Revision behaviour:

| Measure | Critique | Self-revise |
|---|---:|---:|
| Records revised successfully | 36 of 36 | 36 of 36 |
| Findings (unsupported / untestable / miscited / inconsistent / implausible / other) | 111 / 93 / 42 / 26 / 24 / 10 | not applicable |
| Citation set changed | 14 | 7 |
| Hedge words per hypothesis + outcome (original 0.14) | 3.33 | not measured |
| Mean hypothesis length, characters (original 728) | 807 | not measured |

**Integrity** ([results/integrity_critique.json](./eval_critique/results/integrity_critique.json)): verified.
36 judged units per arm, 0 judge errors, 0 incomplete critic sets, 0 invalid revised citations, 0 hidden-target
sends, 0 target-family records in payloads. The baseline's own integrity gap (one closed-book unit in
experiment 7) does not affect this experiment, which uses only the tool-agent arm.

**Interpretation.** As implemented, critique lowers reconstruction (1.64 to 1.49). The drop is larger than the
run-to-run noise (0.09) but is not significant after correction, with 36 units. The loss is in specificity:
the reviser answers the critics' "untestable" and "unsupported" findings with hedging, and the judge scores
novelty, experiment discriminability, outcome agreement and boundary quality lower. Intervention and condition
scores, which depend on the design choice itself, do not move. Evidence validity rises slightly (+0.08), which is
within noise. The self-revise control also loses a little (−0.04), so part of the effect is general to revision,
but most of it is specific to the critique prompts.

**Next steps (not run).** Instruct the reviser not to hedge: keep specific claims that the evidence supports, and
put uncertainty only in the `uncertainty` field. Add a judge-side check for hedge density so that softening
cannot count as improvement. Repeat the noise check on more papers before reading effects of about 0.1.

Full details: [eval_critique/README.md](./eval_critique/README.md).

## Experiment 12: failure analysis across all methods

**Question.** Where and why does each method fail?

**Method.** The analysis covers all 288 units (8 methods × 36) and the judge's 1,087 fatal errors. GPT-5.6
coded each error into 11 categories (a hand spot-check agreed on 37 of 40). An evidence-ceiling test rated
the 20 pre-cutoff records most similar to each target. Confound checks compared effects within query level
and paper, and used the resample arm to measure regression to the mean.

**Main results.**

- Query level drives scores far more than method (broad about 0.7–1.0, expert_context about 2.1–2.6, methods
  within 0.15 of each other).
- Wrong mechanism (19–24%), unsupported evidence claims (20–26%) and wrong conditions (10–18%) are the largest
  error categories for every method. Physics errors are rare (1–7%).
- Missing evidence is not the bottleneck. No case lacked supportive earlier records, and the cases rated most
  reconstructible did not score higher.
- On expert_context queries, tool-agent runs that read supportive prior art scored lower on mechanism and
  outcome (association, 23 vs 13 units).
- Critique helps weak hypotheses (about +0.11 beyond regression) and hurts strong ones (about −0.24).
- Run-to-run noise is about 0.31 per unit, and 19–20% of pairwise verdicts flip with presentation order.

**Configuration.**

| Item | Value |
|---|---|
| Date | 2026-10-22 |
| Units | 288 (8 methods × 36); 287 judged, 1 generation failure (closed_book, PMC11375712 broad) |
| Error coder | GPT-5.6 (`gpt-5.6-sol_2026-07-09`), one call per judged unit with errors (273 calls), 11 fixed categories |
| Coder check | 40 random labels reviewed by hand: 37 agree. The 3 disagreements were between neighbouring categories |
| Evidence ceiling | Top 20 eligible pre-cutoff records per case, retrieved with the hidden target as the query (same `retrieve` as the methods). GPT-5.6 rated each record 0–2 for intervention and mechanism support and the set 0–2 for reconstructibility (12 calls) |
| Hard failure | Reconstruction ≤ 0.5 |
| Hedge counter | may, might, could, potentially, possibly, uncertain, unclear, likely, perhaps, suggest(s), further investigation, require(s) further |

**Failures by method.**

| Method | Reconstruction | Hard failures | Zero on intervention | Zero on evidence validity | Errors per unit | Where it fails | Why |
|---|---:|---:|---:|---:|---:|---|---|
| tool_agent | 1.64 | 14% | 14% | 22% | 3.67 | Unsupported claims | Uses all 12 calls every run; reads 3.6 distinct records; ~1.5 calls spent paging; cites 2.4 |
| tool_agent_kg | 1.63 | 22% | 22% | 25% | 3.78 | Most hard failures | KG lookups displace searches (3.8 vs 6.0 per run); KG cited in 5 of 36 runs |
| self_revise | 1.60 | 17% | 14% | 33% | 3.61 | Little change (22 of 36 units unchanged) | No new information; change (−0.04) within noise |
| closed_book | 1.56 | 17% | 20% | 11% | 3.49 | Highest zero rate on all four core dimensions (20%) | No grounding; generic design. 2024 papers 1.66 vs 2025–26 1.35, possible prior knowledge (4 late papers only) |
| text_oneshot | 1.56 | 11% | 25% | 14% | 3.64 | Misses the intervention most often | Shown supportive evidence in 100% of runs, cited it in 94%, but did not turn it into the target's intervention |
| resample | 1.55 | 14% | 17% | 31% | 3.89 | As tool_agent | Second sample of tool_agent; measures noise |
| v2_oneshot | 1.49 | 17% | 22% | 11% | 4.00 | Most unsupported verdicts of the eval_v3 methods (12) | Structured units drop context; highest physics-error share (7%) |
| critique | 1.49 | 11% | 11% | 25% | 4.22 | Most errors per unit; 3.47 hedge words per hypothesis | Reviser answers critiques by softening claims; judge rates them vague |

**Error categories (share of each method's errors).**

| Category | closed_book | text_oneshot | v2_oneshot | tool_agent | resample | tool_agent_kg | self_revise | critique |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| wrong_mechanism | 24% | 20% | 19% | 21% | 21% | 23% | 22% | 22% |
| evidence_unsupported | 11% | 24% | 23% | 20% | 25% | 26% | 22% | 22% |
| wrong_conditions | 14% | 16% | 10% | 17% | 18% | 15% | 15% | 15% |
| wrong_intervention | 12% | 14% | 13% | 11% | 10% | 9% | 14% | 12% |
| wrong_outcome | 12% | 8% | 11% | 10% | 6% | 7% | 7% | 9% |
| untestable_or_vague | 12% | 6% | 8% | 4% | 6% | 7% | 8% | 12% |
| wrong_baseline | 8% | 5% | 4% | 7% | 6% | 7% | 7% | 6% |
| physical_error | 6% | 5% | 7% | 4% | 3% | 2% | 2% | 1% |
| internal_inconsistency | 2% | 2% | 3% | 4% | 2% | 2% | 3% | 1% |
| evidence_contradicted | 0% | 1% | 1% | 2% | 2% | 2% | 1% | 1% |

**Reconstruction by query level.**

| Level | closed_book | text_oneshot | v2_oneshot | tool_agent | resample | tool_agent_kg | self_revise | critique |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| broad | 0.75 | 0.79 | 0.73 | 0.79 | 0.79 | 0.69 | 0.75 | 0.96 |
| problem_constrained | 1.46 | 1.52 | 1.44 | 1.65 | 1.48 | 1.60 | 1.69 | 1.40 |
| expert_context | 2.40 | 2.38 | 2.29 | 2.48 | 2.38 | 2.60 | 2.35 | 2.10 |

**Evidence ceiling and evidence use.** No case was rated 0. Nine cases were rated 1 (right direction, but
the specific intervention needs a new idea) and three were rated 2 (`PMC11355469`, `PMC12298864`,
`PMC12941549`). The rated-2 cases scored lower, not higher, at problem_constrained (1.28 vs 1.61) and
expert_context (1.91 vs 2.53).

| Level (tool arms pooled) | Read supportive record | Reconstruction if read | Reconstruction if not |
|---|---:|---:|---:|
| broad | 81% | 0.75 | 0.79 |
| problem_constrained | 50% | 1.67 | 1.49 |
| expert_context | 64% | 2.28 | 2.85 |

On expert_context, reading supportive prior art left intervention unchanged (2.96 vs 2.92) but lowered
mechanism (2.26 vs 2.85), outcome (1.96 vs 3.23) and conditions (1.96 vs 2.38). The average within-paper
effect of reading supportive records was −0.11 (range −1.82 to +1.28).

**Critique vs regression to the mean** (split on the original tool_agent score):

| Original score | critique change | resample change (no revision) | Effect beyond regression |
|---|---:|---:|---:|
| below 1.5 | +0.07 | −0.04 | about +0.11 |
| 1.5 or above | −0.38 | −0.14 | about −0.24 |

When the reviser changed the cited records (14 units), the score fell by 0.32 on average, against 0.05
when it kept them.

**Failures from the benchmark, not the methods.**

- Broad queries are under-specified: wrong intervention is 16% of their errors and wrong baseline 9%, against
  5% and 5% at expert_context.
- Hardest papers: `PMC12941549` (0.96 average over methods; 29% wrong conditions, because its target test
  conditions are not implied by the query) and `PMC11077685` (1.00; 32% wrong intervention, because its 3D ink
  extrusion route is unusual). Easiest: `PMC12806431` (2.16).
- Target type explains little: computational targets 1.48–1.65 and processing targets 1.33–1.64.
- Noise: the two tool-agent samples differ by 0.31 per unit (SD 0.38), 7 of 36 units change classification,
  and the means differ by 0.09.
- Position bias: 20 of 107 (eval_v3) and 29 of 143 (eval_v4) pairwise verdicts flip with presentation order.
- Only one unit defeated every method: `PMC11375712` broad (best 0.25).

**Suggested fixes, in priority order.**

1. Fix the benchmark: drop or rescore broad queries, flag targets whose details the query cannot imply, and
   report results per level.
2. Generate several samples per unit and calibrate the judge against an expert.
3. Target mechanism reasoning, the largest error category for every method.
4. Stop the agent wasting budget on paging, so it reads more distinct sources.
5. Guard against copying precedent on specific queries.
6. Apply critique only to weak hypotheses, and forbid hedging in the reviser.
7. Make KG lookups free or relation-typed rather than raw co-occurrence.

**Limits.** The error coder and evidence ceiling used the same GPT-5.6 deployment as the judge. The evidence
ceiling only looks at a lexical top 20, so it may undercount available evidence. All comparisons are
observational over 12 papers. The anchoring and memorisation findings are associations, not tested causes.

Full details: [failure_analysis/README.md](./failure_analysis/README.md).

## Experiment 13: intermediate-stage metrics for all methods

**Question.** Where in the pipeline does each method lose quality: query, retrieval, reading, grounding,
reasoning, hypothesis form, revision, KG use, or judging?

**Method.** Computed over the stored outputs of all 8 methods (288 units; nothing regenerated):

- Deterministic replay of all 108 tool runs; all 108 reproduce the stored accessed records exactly.
- `text-embedding-3-large` (256 dimensions) for novelty, relevance and diversity.
- Target-free GPT-5.6 audit per hypothesis (287): claim grounding, causal chain, contradictions, mechanism
  source, falsifiability, specificity, uncertainty and composition claims.
- Diagnostic GPT-5.6 inferability rating per query (36).
- Target-free GPT-5.6 review of every revision (72).
- Two more GPT-5.6 judgments of every output (574).
- One DeepSeek-V4-Pro judgment of every output (287).

All 1,256 LLM calls completed with zero errors.

**Main results.**

| Stage | Key metric | Result |
|---|---|---|
| Query | Target stated or implied by query vs score | ρ = 0.82; broad queries give away 0.61/2, expert 1.55/2 |
| Retrieval | Tool runs that surface a supportive record | 94–100%, within about 3 calls |
| Reading | Supportive records surfaced but not read | 56–67%; only 6–7% of supportive records read |
| Reading | Read calls spent paging | 23–30% |
| Grounding | Claims entailed / at least partly supported by cited evidence | 12–15% / 33–41% |
| Grounding | Supported claims resting on another alloy system | 48–61% |
| Grounding | Numbers untraceable to seen evidence (generation methods) | 32–44% |
| Reasoning | Mechanism transferred without justification | 39–56% of evidence-using hypotheses |
| Reasoning | Complete causal chain | 57–69%; critique 33% |
| Form | Falsifiability checklist | 0.79–0.91; critique 0.69 |
| Form | Stated uncertainty vs score (calibration) | ρ between −0.24 and 0.14: uncalibrated |
| Critique | Valid findings / corrected | 70% valid (+20% partly) / 13% corrected (36% hedged) |
| KG | Facts used per lookup; searches per run (KG vs plain) | 0.23; 3.8 vs 5.9 |
| Judge | GPT-5.6 test-retest | ICC 0.96, within-unit SD 0.10 |
| Judge | Cross-family judge (DeepSeek-V4-Pro) | unit ρ 0.90, +0.42 more lenient, method-ranking τ 0.32 |
| Selection | Best of 2 samples / best of 8 methods | 1.75 (+0.11) / 1.97 (+0.33) |

**Interpretation.**

- Agents find the right evidence but don't read it, and they ground few claims.
- Mechanisms are borrowed from other systems without justification.
- Critique identifies real problems but answers them with hedges.
- The judge is consistent with itself, but method rankings change with the judge family.
- Choosing among samples or methods has more headroom than any method change so far.

**Limits.** The audit and review use the same model family as the judge. Supportive-evidence metrics depend
on the lexical top-20 oracle. Composition checks cover 24 claims and flagged 7, of which 3 were genuine on
manual review. Number tracing is a string match. The expert calibration set (30 units) is prepared but not
labelled.

Full details: [stage_metrics/README.md](./stage_metrics/README.md).

## Experiment 14: extraction rubrics

**Question.** Which extraction rubric, meaning what to pull out of each earlier paper, gives the agent the best
evidence for hypothesis generation?

**Method.**

- Four rubrics extracted by the local generator (Qwen) from all 50 papers, with references stripped and long papers
  windowed: card (one digest per paper), effects (intervention → effect records), mechanisms (mechanism with scope)
  and gaps (limitations, open problems and levers). Every item needs at least one verbatim quote verified against
  the paper.
- Eight arms: closed_book, text_chunks, v2_units, card, effects, mechanisms, gaps, and mixed (effects + mechanisms +
  gaps in one pool).
- Every evidence arm gets the same 16,000-character budget (record cap 1,600 characters; 3,200 for cards), and each
  unit gets two samples.
- Judged by GPT-5.6 and DeepSeek-V4-Pro, plus a target-free grounding audit and a per-representation evidence
  ceiling.

**Extraction.** 1,513 quote-verified records (55 cards, 609 effects, 423 mechanisms, 426 gaps). 97–100% of items
kept, and 90–95% of quotes verified.

**Results** (reconstruction 0–4, mean of 2 samples per unit):

| Arm | GPT-5.6 | DeepSeek-V4-Pro |
|---|---:|---:|
| closed_book | 1.65 | 2.20 |
| text_chunks | 1.56 | 2.00 |
| card | 1.52 | 1.98 |
| v2_units | 1.52 | 1.96 |
| effects | 1.51 | 1.95 |
| gaps | 1.48 | 1.89 |
| mechanisms | 1.46 | 1.90 |
| mixed | 1.39 | 1.86 |

- The two judges rank the arms almost identically (τ = 0.93).
- No rubric beats raw text. Card and effects tie with it.
- Mixed is lowest (−0.17 vs text under GPT-5.6, CI −0.25 to −0.09; −0.14 under DeepSeek, CI −0.27 to −0.01),
  but does not survive the Holm correction.
- Closed-book is highest, but only on 2024 targets (1.68 vs 1.49 for text). On the four 2025–26 targets, text (1.69)
  beats it (1.59), which fits memorisation of older papers.

**Why.** The distilled rubrics keep the target-anticipating information (mixed has the most strongly supportive
records). But serving mechanisms and effects detached from their study pushes the generator to borrow mechanisms from
other alloys:

- Within level, hypotheses with a borrowed mechanism score 1.10 vs 1.80 (problem_constrained) and 2.22 vs 2.73
  (expert_context) on mechanism agreement, compared with those whose mechanism came from the model's own reasoning.
- Mixed borrows without justification in up to 88% of runs, and cards in the fewest (42–54%).
- Retrieval from the large mixed pool also puts the fewest supportive records in context.

**Integrity.** 574 of 576 runs ok, each judged twice and audited. Zero temporal, family or held-out-paper leaks,
zero invalid citations. The two failed runs are both samples of the closed-book `PMC11375712` broad unit (the same
unit failed in v3), and each was retried once.

Full details: [rubric_eval/README.md](./rubric_eval/README.md).

## Experiment 15: failure analysis of the extraction-rubric experiment

**Question.** What breaks in the extraction-rubric pipeline, and at which stage?

**Method.**

- Error coding: the 2,282 fatal errors from the 574 judged runs, coded by GPT-5.6 into the 11-category taxonomy.
- Extraction fidelity: 40 random records per rubric checked field by field against the source paper (GPT-5.6,
  target-free).
- Retrieval and use: whether a target-anticipating record (evidence-ceiling rating) was in context and cited,
  compared within level and within paper.
- Generation: the reproducible closed-book failure rerun three times with the raw output saved.
- A run counts as a failure if reconstruction ≤ 1.0.

**What breaks, ranked by impact.**

1. **Broad queries (benchmark).** 79–96% failure in every arm; 6 of 12 broad units fail in all 8 arms.
2. **Evidence use (reasoning).** In 83–97% of runs, a target-anticipating record is in context, and most failures
   cite one. Citing it does not raise scores within paper (−0.01, +0.06, −0.10 by level). Strongly supportive
   records help slightly on open queries (+0.10, +0.15) but hurt on expert queries (−0.13, worse in 6 of 8
   units). Wrong mechanism appears in 69–87% of failing runs. Mechanisms from the model's own reasoning fail less
   often (16% vs 34–41% at problem_constrained).
3. **Diluted context.** Only 25–37% of citations are supportive for gaps, mixed and effects, against 81% for cards.
   The effects arm adopts the wrong baseline in 54% of its failures.
4. **Extraction.** 86–93% of fields are supported and 7–13% distorted. The mechanisms rubric's scope-limit (25%)
   and alternatives (24%) fields are the least reliable, and those are the fields meant to stop transfer. 15–35%
   of records mix in cited work despite the own-work rule.
5. **Closed-book prompt conflict.** The shared prompt says "use only supplied evidence", and closed-book supplies
   none. On `PMC11375712` broad the model refuses (empty fields) 3 of 3 times. 52 of 70 successful closed-book runs
   carry a "no evidence supplied" caveat.
6. **No dominant arm.** The best arm per unit is spread across all 8 arms (mean best–worst gap 0.68).

**Fixes.** Repair the broad level; give closed-book its own prompt; add a system-match step before using evidence;
re-extract scope fields with per-field quotes and paraphrase checks; prefer cards or raw text with better retrieval;
select or ensemble across representations.

**Configuration.**

| Item | Value |
|---|---|
| Date | 2026-10-23 |
| Runs analysed | 574 judged runs of experiment 14 (8 arms × 12 papers × 3 levels × 2 samples, minus 2 failed) |
| Failure definition | Reconstruction (mean of intervention, condition, mechanism, outcome; 0–4) ≤ 1.0 |
| Error coding | GPT-5.6 (`gpt-5.6-sol_2026-07-09`), 549 calls, 2,282 fatal errors, same 11 categories as experiment 12 |
| Extraction fidelity | GPT-5.6, 40 random records per rubric (seed 20261023), 1,064 fields checked against the paper window the record came from; target-free |
| "Supportive" record | Rated 1–2 for intervention or mechanism support among each representation's 20 records most similar to the target (experiment 14 evidence ceiling); "strongly supportive" = rated 2 |
| Generation reproduction | Local Qwen server, same prompt and settings as experiment 14, raw output saved, 3 attempts |
| Total new LLM calls | 709 GPT-5.6 + 3 Qwen; 0 errors |

**Failure rate by arm and level.**

| Level | closed_book | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| broad | 82% | 83% | 96% | 79% | 88% | 88% | 88% | 92% |
| problem_constrained | 17% | 25% | 21% | 38% | 21% | 38% | 33% | 33% |
| expert_context | 4% | 0% | 0% | 0% | 8% | 0% | 4% | 8% |

Units failing in every arm (best arm score in brackets): PMC10759803 (0.88), PMC11077685 (0.75), PMC11375216 (0.88),
PMC11375712 (0.12), PMC11606917 (0.88), PMC12941549 (0.88), all at the broad level.

**Where failures happen in the evidence pipeline.**

| | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|
| Runs with a supportive record in context | 97% | 94% | 97% | 83% | 94% | 94% | 89% |
| Supportive records in context (mean) | 4.03 | 3.56 | 3.67 | 3.94 | 4.14 | 3.97 | 2.61 |
| Share of in-context supportive records cited | 53% | 61% | 55% | 48% | 52% | 30% | 55% |
| Share of citations that are supportive | 55% | 53% | **81%** | 37% | 44% | **25%** | 27% |
| Failures | 26 | 28 | 28 | 28 | 30 | 30 | 32 |
| … no supportive record in context | 2 | 4 | 2 | 6 | 4 | 4 | 7 |
| … in context, not cited | 1 | 1 | 0 | 3 | 3 | 8 | 7 |
| … supportive record cited | 23 | 23 | 26 | 19 | 23 | 18 | 18 |

**Does citing supportive evidence help?** Mean reconstruction difference between runs of the same paper and level
(evidence arms pooled):

| Level | Any supportive cited vs none | Strongly supportive cited vs none |
|---|---:|---:|
| broad | −0.01 (11 units; 7 better, 4 worse) | +0.10 (7 units; 5 better, 2 worse) |
| problem_constrained | +0.06 (9 units; 4 better, 5 worse) | +0.15 (9 units; 6 better, 3 worse) |
| expert_context | −0.10 (8 units; 2 better, 6 worse) | −0.13 (8 units; 2 better, 6 worse) |

**Mechanism source vs outcome** (target-free audit labels, evidence arms pooled):

| Level | Mechanism source | Runs | Reconstruction | Failure rate |
|---|---|---:|---:|---:|
| broad | model's own reasoning | 37 | 0.72 | 78% |
| broad | transferred without justification | 98 | 0.60 | 88% |
| problem_constrained | model's own reasoning | 56 | 1.74 | **16%** |
| problem_constrained | transferred with justification | 27 | 1.36 | 41% |
| problem_constrained | transferred without justification | 84 | 1.33 | 34% |
| expert_context | model's own reasoning | 45 | **2.66** | 0% |
| expert_context | transferred with justification | 7 | 2.21 | 14% |
| expert_context | transferred without justification | 116 | 2.30 | 3% |

**Error categories.** Share of failing runs with at least one error of each category:

| Category | closed_book | text_chunks | v2_units | card | effects | mechanisms | gaps | mixed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| wrong_mechanism | 70% | 69% | 82% | 71% | 75% | **87%** | 83% | 78% |
| evidence_unsupported | 65% | 81% | 79% | 79% | 82% | 80% | 83% | 81% |
| wrong_intervention | 74% | 77% | 71% | 61% | 57% | 63% | 77% | 53% |
| wrong_conditions | 48% | 54% | 61% | 46% | 46% | 57% | 63% | 44% |
| wrong_outcome | 39% | 54% | 36% | 39% | 32% | 33% | 33% | 44% |
| wrong_baseline | 26% | 27% | 36% | 29% | **54%** | 43% | 23% | 44% |
| evidence_contradicted | 0% | 12% | 0% | 4% | **29%** | 20% | 3% | 19% |
| untestable_or_vague | 35% | 15% | 25% | 36% | 36% | 23% | 13% | 16% |
| physical_error | 13% | 12% | 18% | 14% | 21% | 10% | 17% | 19% |
| internal_inconsistency | 4% | 12% | 7% | 7% | 11% | 13% | 3% | 3% |
| Fatal errors per run (all runs) | 3.53 | 3.81 | 4.10 | 4.18 | 3.94 | 4.10 | 4.06 | 4.08 |

**Extraction fidelity** (40 random records per rubric):

| | card | effects | mechanisms | gaps |
|---|---:|---:|---:|---:|
| Fields supported | 90% | 93% | 87% | 86% |
| Fields distorted | 9% | 7% | 13% | 10% |
| Fields not in the paper | 1% | 0% | 0% | 4% |
| Records with every field supported | 50% | 65% | 33% | 70% |
| Records mixing in cited work | 35% | 15% | 30% | 15% |
| Least reliable field (share not supported) | key findings 17% | processing 10% | scope limits 25%, alternatives 24% | lever 23% |

Typical distortions:
- wrong comparison base (a grain-size increase measured from the wrong reference)
- wrong treatment (annealing reported where the paper says aging)
- roles swapped (a comparison sample reported as an alternative mechanism)
- added claims (a Laves phase called brittle when the paper doesn't say so)

**Reproduced generation failure.** Closed-book, PMC11375712 broad, three attempts, all `finish_reason=stop`. Every time
the model returned the full schema with every field empty, and wrote in `uncertainty`, for example, "The provided
evidence list is empty… No hypothesis can be generated without violating the constraint to use only supplied
temporally eligible evidence." The cause is the shared generation prompt, not a formatting bug. The same
pressure shows as an evidence caveat in 52 of 70 successful closed-book runs here and 29 of 35 in eval v3.

**Best arm per unit.** closed_book 9, card 9, effects 5, v2_units 4, text_chunks 4, mechanisms 2, gaps 2, mixed 1. The
mean gap between best and worst arm on a unit is 0.68.

**Paper hot spots.** PMC12941549 (0.86, 73% failures; wrong conditions 26% of errors: the query doesn't imply the target's
test conditions); PMC11077685 (0.95, 56%; wrong intervention 34%: unusual hydride ink-extrusion route); PMC11087546
(1.47, 60%). Easiest: PMC12806431 (2.34, 4%).

**Limits.** "Supportive" counts only cover each representation's top 20 records by similarity to the target, so they
are lower bounds. Coding, fidelity and ceiling all use GPT-5.6, the same family as the judge. Within-paper comparisons
cover 7–11 units per level and are associations, not controlled tests.

Full details: [rubric_eval/failure/README.md](./rubric_eval/failure/README.md).

## Experiment 16: targeted improvements vs baselines

**Question.** Do fixes aimed at the experiment-15 failures beat the baselines?

**Arms.** Each uses the same generator, evidence budget, two samples per unit and two judges as experiment 14; only
the prompt changes, or for knowledge_first an extra step.

| Arm | Change | Targets |
|---|---|---|
| closed_book_fixed | Own prompt allowing the model's own pre-cutoff knowledge | Closed-book prompt conflict |
| text_systemmatch / card_systemmatch | Appraise each record (system, conditions, difference from target, transfer verdict) before writing; use only transferable mechanisms | Cross-system mechanism transfer |
| knowledge_first | Own-knowledge draft (closed_book_fixed), then revise with raw text used only to correct and test it | Own-reasoning mechanisms fail least |
| ensemble_select | Local model picks one of six blinded candidates, without the target | No arm dominates |

**Configuration.**

- Baselines are the experiment-14 runs: closed_book, text_chunks, card, v2_units.
- Output cap 7,000 tokens for the new arms (appraisal JSON); 5,000 for the baselines.
- Primary comparison: each new arm against text_chunks, with Holm correction over 5. Units are the mean of 2
  samples, with a paper-clustered bootstrap and sign test.

**Results** (reconstruction 0–4):

| Arm | GPT-5.6 | DeepSeek-V4-Pro | Non-broad (GPT-5.6) |
|---|---:|---:|---:|
| closed_book (baseline) | **1.65** | **2.20** | **2.06** |
| card_systemmatch | 1.62 | 2.02 | 2.02 |
| ensemble_select | 1.59 | 2.12 | 2.00 |
| text_systemmatch | 1.57 | 2.13 | 1.96 |
| text_chunks (baseline) | 1.56 | 2.00 | 2.00 |
| card (baseline) | 1.52 | 1.98 | 1.92 |
| v2_units (baseline) | 1.52 | 1.96 | 1.99 |
| closed_book_fixed | 1.49 | 1.97 | 1.84 |
| knowledge_first | 1.42 | 1.99 | 1.77 |

**Main comparisons.**

- text_systemmatch − text: +0.01 (GPT-5.6) and +0.14 (DeepSeek, CI +0.02 to +0.25).
- card_systemmatch − card: +0.09 and +0.04.
- closed_book_fixed − closed_book: −0.13 and −0.18 (both CIs exclude zero).
- knowledge_first − text: −0.14 (GPT-5.6, CI −0.26 to 0.00).
- No primary comparison survives Holm (smallest p = 0.11).

**Why.**

- *System-match* raises mechanism agreement (1.53 → 1.62 on text, 1.50 → 1.64 on cards), evidence validity
  (1.10 → 1.39; 0.86 → 1.25), specificity (0.60 → 0.76) and justified transfers (10% → 25% on text). It does not
  reduce unjustified transfer on cards, and it doubles hypothesis length.
- The appraisals show the corpus mismatch: 53% of appraised records were judged non-transferable and only 5–8%
  fully transferable.
- *Fixing the closed-book prompt hurt.* Free of the evidence-only rule, the model proposes bolder, more novel
  interventions (novelty 1.90 → 2.31) that match the target less (intervention 1.83 → 1.51). The benchmark rewards
  conservative, query-adjacent hypotheses.
- *Knowledge-first* kept 94–97% of the draft's wording, improved 12 of 72 samples and hurt 28.
- *The selector has a position bias:* it picks the first candidate 72% of the time. Its picks score 1.59, against
  1.53 for a random pick and 1.93 for an oracle that picks the judge's best.

**Integrity.**

- 288 of 288 new runs succeeded, each judged twice and audited; 72 selections, no fallbacks.
- Zero leakage, zero invalid citations.
- Two runs failed on the first pass, were retried once and succeeded; their selections were redone.
- A selector leak-check false positive ("card" inside "discarded") was fixed and tested.

**Recommendation.**

- Adopt system-match appraisal with cards as the evidence path, plus a no-hedging rule.
- Keep the cautious closed-book prompt as the baseline.
- Drop knowledge-first in this form.
- Fix the selector (pairwise judging in both orders, or a stronger target-free selector) before relying on
  ensembles; the oracle gap is the largest headroom.
- Repair the broad level.

Full details: [improvements/README.md](./improvements/README.md).

## Experiment 17: citation-graph evidence variants

**Question.** Does evidence from a per-query citation graph beat the fixed 50-paper corpus, and which way of
using the graph works best? The user chose every design option and asked for all variants to be run and
compared with a failure analysis.

**Graph.** One graph per case, built from the problem_constrained query and shared by all three levels.

- Qwen writes search phrases from the query only.
- Seeds: Europe PMC open-access full text before the cutoff, anchored to the HEA domain and re-ranked by BM25.
  The top 40 by relevance are ordered by citations before the cutoff year; N = 10, reviews allowed.
- Backward expansion: k = 3 per seed, ranked by co-citation among seeds, then relevance, then pre-cutoff
  citations. References without full text are skipped.
- References resolve to OpenAlex works by DOI, PMID or title (92% resolved).
- Qwen writes a card per full-text paper and one statement per (citing sentence, cited work) with relation,
  claim, system and numbers.
- Nodes are the seeds, the expansion papers and all their pre-cutoff references. A statement from paper A about
  work C is attached to node C.
- Built: 264 full-text papers, 9,899 statements; per case 1,298 nodes, 30 full text, 71 with ≥ 2 independent
  citers.

**Variants.**

- graph_selection: cards of graph papers (control).
- graph_profiles: card plus citer statements.
- graph_profiles_systemmatch: profiles with the experiment-16 appraisal.
- corroboration_weighted: ranked by relevance × independent citers.
- graph_tool_agent: search_nodes, read_node, who_cites, references, path; 12 calls.

Generator, budget (16,000 characters), two samples, judges and statistics are as in experiments 14 and 16.

**Results** (reconstruction 0–4):

| Arm | GPT-5.6 | DeepSeek-V4-Pro | Non-broad (GPT-5.6) |
|---|---:|---:|---:|
| closed_book (baseline) | **1.65** | **2.20** | **2.06** |
| card_systemmatch (exp 16) | 1.62 | 2.02 | 2.02 |
| text_chunks (baseline) | 1.56 | 2.00 | 2.00 |
| graph_selection | 1.52 | 1.91 | 1.97 |
| graph_profiles | 1.52 | 1.97 | 1.95 |
| card (baseline) | 1.52 | 1.98 | 1.92 |
| graph_tool_agent | 1.52 | 1.98 | 1.92 |
| graph_profiles_systemmatch | 1.49 | 2.06 | 1.91 |
| corroboration_weighted | 1.49 | 1.97 | 1.93 |

- Against text_chunks, every variant is between −0.07 and −0.03 on GPT-5.6 and between −0.09 and +0.06 on
  DeepSeek. No Holm-adjusted p is below 0.73.
- Every variant is below closed_book. The interval excludes zero for graph_selection and corroboration_weighted
  on both judges.
- Adding citer statements to the same graph (profiles − selection) changes nothing: 0.00 and +0.06.
- graph_profiles_systemmatch has the highest evidence validity (1.28) and specificity (0.81) of any arm.
- The tool agent always exhausts its budget and almost never uses citation edges.

**Integrity.**

- 359 of 360 runs ok. One system-match run hit the output cap on its first attempt and on its single retry.
- Every ok run judged twice and audited.
- Zero temporal, target, family or title leaks and zero invalid citations. Nodes are dated by their latest
  citer.

**Answer.** No graph variant improves on the corpus baselines. The best graph variant, graph_profiles_systemmatch,
equals card_systemmatch on DeepSeek and is lower on GPT-5.6.

Full details: [citegraph/README.md](./citegraph/README.md).

## Experiment 18: failure analysis of the citation-graph variants

**Findings, in pipeline order.**

- *Statements.* 72% of the 90 checked citer statements are faithful to their sentence, and 90% have the right
  relation.
  - Method statements are faithful only 47% of the time (often a restated title), and compares statements 60%
    (the citing paper's comparison attributed to the cited work).
  - The cited system is right in only 68% of statements that state one.
- *Ceiling.* The graph anticipates the target no better than the corpus: 1.25 for profiles and 1.33 for selected
  cards, against 1.25 for corpus text and 1.42 for corpus cards; about 2 strongly supportive records per case
  either way.
  - Half the supportive profiles are reference-only nodes, so statements add coverage but not more anticipation.
- *Use.* Profiles spread the budget over 13.6 papers instead of 5.7. Supportive citations fall to 46% (85% for
  cards), and 57% of citations are reference-only nodes.
  - Corroboration ranking cuts supportive records in context from 3.8 to 1.3 by promoting central, general works.
  - The agent reads 7 nodes and sees 1.6 supportive records. It uses citation edges in 20 of 72 runs, with no
    effect on the score (1.53 with, 1.52 without).
- *Reasoning.* Wrong-baseline (up to 0.46) and wrong-conditions (up to 0.62) errors rise in the graph arms,
  because the model borrows other alloy classes' starting materials and regimes.
  - System-match on profiles has the most mechanism (82%) and physical (29%) errors in its failures; citer
    statements rarely say which system they concern.
  - Own-reasoning mechanisms still score highest (1.80–1.85 in the profile arms).

**Why the graph does not help.**

1. The evidence ceiling does not rise.
2. Citation counts and corroboration measure centrality, not query relevance.
3. Reference-only nodes are thin and partly unfaithful.
4. The agent does not exploit the structure.

**Best variant.** graph_profiles_systemmatch: highest DeepSeek score, evidence validity and specificity, with
fixable failure causes. Drop corroboration_weighted.

**Fixes if pursued.**

- Rank by relevance first.
- Keep reference-only nodes only with at least 2 consistent citers and an explicit system.
- Take the system from the reference entry. Drop method and compares statements.
- Give the agent a graph-first protocol with more reads.

Full details: [citegraph/failure/README.md](./citegraph/failure/README.md).

## Experiment 19: answer leakage in the benchmark queries

**Question.** How are the queries built, and do they reveal the answer?

**How queries are built.**

- `build_cases` in `temporal_hypothesis_benchmark.py` makes one Qwen call per held-out paper. Into it go the
  paper's "safe" roles (problem_motivation, prior_limitation, constraint), its result roles (hypothesis_statement,
  causal_claim, mechanism_principle, evidence_result, contradiction) and its own result evidence.
- That call writes the three queries and the hidden target together.
- The only safeguards are the prompt instruction "do not reveal the result" and a check that the title and DOI do
  not appear in the query.

**Findings** (`query_leakage_audit.py`, `query_leakage/analysis.json`).

| Level | Queries written from result roles | Answer words in query (mean, max) |
|---|---:|---:|
| broad | 2 of 12 | 8%, 16% |
| problem_constrained | 7 of 12 | 20%, 27% |
| expert_context | 12 of 12 | 47%, 65% |

"Answer words" are the content words of the hidden target's intervention, structural mediator and mechanism.

- Expert queries state the answer outright:
  - PMC10759803: "addition of ~4 at.% … (Cr) … Laves phase … reticulated … impedes crack extension".
  - PMC11087546: "approximately 6 GPa at 1473 K … hierarchically patterned microstructure with coherent
    interfaces".
- Problem queries give the type of intervention ("introduce a minor alloying element … to induce a secondary
  intermetallic phase to form a reticulated network").
- Some broad queries state the outcome. PMC12298864: "grain sizes below 50 nm and a dual-phase solid solution".
- The builder listed these risks itself in `leakage_audit.remaining_risks`, but nothing acted on them.
- Other problems:
  - The query writer is the generator under test (Qwen).
  - Many expert queries ask the model to justify a stated hypothesis ("Propose a hypothesis where…").
  - Some queries prescribe the paper's own control experiment.
  - The hidden target contains exact values (for example 13.5% strength gain, 675 HV) that earlier literature
    cannot predict.
- **Leakage predicts the score.** Across the 36 units, Spearman correlation between answer overlap and GPT-5.6
  score is 0.77–0.86 for all seven methods checked: closed_book 0.86, text_chunks 0.84, card 0.80,
  card_systemmatch 0.84, graph_profiles 0.77, graph_profiles_systemmatch 0.84, graph_tool_agent 0.84. Within
  the expert level alone it is 0.66–0.85.

**Impact on earlier experiments.**

- Comparisons between methods on the same query unit stay fair, because every method saw the same text.
- Absolute scores, the broad-to-expert gradient and the "query inferability drives scores" finding (experiments
  12, 13 and 15) mostly measure how much of the answer the query gives.
- "Closed-book is best" and "evidence hurts on specific queries" (experiments 14 to 18) are confounded: when the
  query already contains the answer, retrieved evidence can only distract.

**Recommended rebuild** (not yet run).

1. Write queries only from pre-result content (introduction, limits of prior work). The query writer never sees
   result roles or result evidence, and the target is built in a separate call.
2. Use a model other than the generator as the writer.
3. Define levels by context, not by answer: broad = family + goal; problem = + baseline alloy, failure mode, test
   regime; expert = + earlier attempts and constraints. No level names the intervention type.
4. Gate each query: answer-word overlap below about 10%, and a query-only guesser must score below 2 of 4 on
   intervention against the target. Otherwise rewrite or drop.
5. Expert review of the 36 queries, then re-run the key methods (closed_book, text_chunks, card_systemmatch,
   graph_profiles_systemmatch).

**How published benchmarks handle this** ([RELATED_WORK.md](./RELATED_WORK.md)).

- ACCELMAT/MatDesign (NAACL Findings 2025): experts extract only a goal statement and constraints as input; the
  paper's materials and methods are the held-out answer.
- SCIMON (ACL 2024): abstract sentences are split by role, so Background sentences are input and Method/Objective
  sentences are targets.
- ResearchBench (ACL Findings 2026): an LLM agent extracts question and background separately from the hypothesis,
  and experts validate the extraction (91.9%).

All three keep the answer out of the generator's input by construction, not by instruction; our case builder
relied on the instruction alone. ResearchBench also scores inspiration retrieval separately and ranks in both
orders, which addresses two open problems here: the evidence ceiling against its use, and selector position bias.

Full details: [query_leakage/README.md](./query_leakage/README.md).

## Experiment 20: leak-free benchmark v3 and memorisation probe

**Why.**

- Experiment 19 showed the queries leaked the answer.
- The generator, Qwen3.5-35B-A3B (released 2026-02), may also have been trained on the held-out papers (2024-01
  to 2026-02). Every published benchmark checked requires papers published after the generator's training cutoff
  (MatDesign, MOOSE-Chem, IdeaBench, ResearchBench); see [RELATED_WORK.md](./RELATED_WORK.md).

**Queries** ([benchmark_v3/README.md](./benchmark_v3/README.md), `query_builder_v3.py`).

- The source is the Introduction only, with the paper's own contribution removed.
- The writer (GPT-5.6) never sees the answer and follows MOOSE-Chem's rule: the background may cover earlier work,
  but no method, material change, structure or mechanism of the answer, and no hint of the solution's direction.
- A separate checker with the answer lists leaking phrases and steering.
- A lexical gate (≤ 10% of answer words outside the allowed context) applies to every query.
- Failed levels are rewritten up to 4 times.
- The hidden targets are unchanged.

**Result.**

- Answer-word overlap fell from 8% / 20% / 47% to 2% / 6% / 5% (broad / problem / expert).
- 34 of 36 queries pass the gate. The two that fail are expert queries of computational-method papers, whose
  background inherently names simulation. They are flagged and reported separately.

**Memorisation probe** (`memorisation_probe.py`). Each model saw a held-out paper's title and year; GPT-5.6 scored
its recollection against the target.

- Qwen recalled specific correct details beyond the title in 33% of probes, against 8% for Llama-3.3 (cutoff
  2023-12).
- Neither claimed to remember any paper.
- This is weak evidence of contamination.

## Experiment 21: all evaluations rerun on leak-free queries with a pre-cutoff generator

**Setup.**

- Experiments 7, 9, 11, 14, 16 and 17 were rerun unchanged except for two things: the queries (benchmark v3) and
  the generator, Llama-3.3-70B-Instruct (cutoff 2023-12). Its search phrases, selector, refiner and reviser are
  also pre-cutoff.
- Outputs are in `rerun_v3/`; the earlier results are untouched.
- A factorial runs both generators on both query sets for experiment 7.

**Integrity.**

- 1,512 generation runs and 72 selections.
- Every rerun experiment is verified except one critique resample run, which twice ended without a submission.
- Zero temporal, family, target and citation leaks.
- One critique revision crashed on a null citation list from Llama and succeeded on retry. The cause is fixed at
  the source: `_validate_generation` now normalises null or string ID lists (regression test).
- The factorial bootstrap is now deterministic: its papers are sorted, so the CIs no longer depend on Python's hash
  seed. CIs moved by at most 0.007.
- **Extractor leakage measured, not assumed** ([extractor_leakage_audit.py](../../extractor_leakage_audit.py)).
  - The rerun reads Qwen-made extractions of pre-cutoff papers: v2 units, rubric records, citation-graph cards and
    citer statements.
  - Records containing an answer word absent from their own source paper occur at 0.00–3.8% per representation.
  - That is no more often than for other cases' answer words (ratio ≤ 0.96). The exception is citation-graph cards
    (1.42; 14 versus about 9 expected records), and all 14 hits are generic words (enable, hour, pinning…).
  - There is no evidence of later-paper knowledge in the extractions.

**Results** (GPT-5.6 reconstruction, 0–4; full table in [rerun_v3/README.md](./rerun_v3/README.md)).

- **Scores fall from 1.39–1.65 to 0.35–0.60, and the level gradient disappears** (broad, problem and expert all
  about 0.45–0.6).
- **Answer overlap no longer predicts the score:** ρ = 0.72–0.88 before, −0.05 to 0.50 after.
- **Factorial, experiment 7:**

| Generator | Leaky queries | Clean queries |
|---|---:|---:|
| Qwen3.5 (post-cutoff) | 1.56 | 0.50 |
| Llama-3.3 (pre-cutoff) | 1.40 | 0.45 |

  - Query effect: −1.07 [−1.37, −0.77] with Qwen and −0.94 with Llama.
  - Generator effect: −0.16 on leaky queries and −0.04 on clean queries.
  - The leakage, not memorisation, inflated the original scores.
- **Rerun ranking.**
  - closed_book 0.60 is highest, then graph_profiles 0.55, ensemble_select 0.54 and graph_selection 0.54.
  - text_chunks scores 0.47 and the agents and critique 0.35–0.46.
  - No arm beats text_chunks after Holm correction (closed_book +0.13, p = 0.04, Holm 0.66).
- **Agents are under-tested with Llama.** It made 2.1 tool calls per run (9 of 36 runs had none), and the MatKG
  agent made calls in only 1 of 36 runs. With Qwen on the clean queries, the evidence arms and the agent are level
  with or slightly above closed-book (text +0.10, agent +0.08; neither significant).

**Earlier conclusions, revised.**

| Conclusion | Status |
|---|---|
| Query inferability drives scores | Withdrawn: it was leakage |
| Evidence hurts on specific queries | Withdrawn: measured on leaky queries |
| Closed-book is best | Weakened: not significant, and generator-dependent |
| No rubric beats raw text | Holds |
| System-match helps | Not confirmed (+0.01–0.02 on GPT-5.6; highest on DeepSeek) |
| Citation graph does not beat the corpus | Holds; graph_profiles and graph_selection are now near the top (not significant) |
| Critique and KG do not help | Hold, but confounded by Llama's minimal tool use |

**Next.**

- Use benchmark v3 for all future work.
- Have the materials expert review the 36 queries.
- Rerun the agent arms with a pre-cutoff model that uses tools (gpt-4o when its quota allows).
- Consider removing exact values from the targets (IdeaBench's paraphrase).

## Experiment 22: failure analysis of the clean rerun

**Why.** On leak-free queries every arm scored 0.35–0.60 of 4, and no method beat raw text. Before designing new
methods, find what breaks.

**Setup.** [failure_clean.py](../../failure_clean.py) covers all 1,476 judged hypotheses of experiment 21 (26 arms).
- GPT-5.6, which sees the target, labels each hypothesis's lever match (0 different kind … 3 the target's
  intervention) and each target's type. This is analysis only.
- It also covers fatal-error coding, pass@k, question fit, levels and judge agreement.
- Details: [rerun_v3/failure/README.md](./rerun_v3/failure/README.md).

**Results** (F1–F8 in [loop.md](../../loop.md) section 1).
- Intervention reconstruction is 0.16 of 4. 79% of hypotheses propose a different kind of intervention, and 0% the
  target's. There is a strong default to composition changes.
- 4 of 12 targets are studies, but every question asked for an intervention, so those cases were unreachable.
- Coverage is the bottleneck, not selection: pass@10 = 0.21, and 25 of 36 units have no lever hit in 41
  hypotheses.
- Evidence lowers problem alignment; 25% of fatal errors are vague claims; GPT-5.6 vs DeepSeek ρ = 0.39; query
  levels are flat.

## Experiment 23: benchmark v3.1, must_obey.md and model clearance

**Rules.** [must_obey.md](../../must_obey.md) collects every rule learned so far:
- splits;
- sourced model cutoffs;
- query, evidence and payload leakage rules;
- statistics;
- dev/test discipline;
- a checklist.

It is enforced by [must_obey_check.py](../../must_obey_check.py) (model whitelist, frozen-query hashes, leakage
counters, judged and audited runs, test runs marked final) and pointed to by `AGENTS.md` and
`.github/copilot-instructions.md`.

**Benchmark v3.1** ([benchmark_v3_1/README.md](./benchmark_v3_1/README.md)) fixes experiment 22's construction
error.
- A gap classifier sees only the redacted introduction and labels each case design, understanding or method.
- Design cases keep their v3 queries; the others are rewritten with the v3 writer, checker and gate.
- 8 cases are rewritten (all 4 test cases as understanding). 34 of 36 levels pass the gate.
- Two processing-route test targets now carry understanding questions; this is a recorded caveat.

**Model clearance.**
- Knowledge cutoffs come from vendor documentation.
- Memorisation probe (specific recall): o3-mini 17% (every hit inferable from the title), gpt-4o-mini 0%, Llama-3.3
  8%, Qwen3.5 33%.
- o3-mini and gpt-4o-mini (cutoff 2023-10-01) are cleared as generators.

## Experiment 24: harness-engineered method loop and pre-registered test

**Setup** ([loop.md](../../loop.md), [loop/README.md](./loop/README.md)).
- The code-controlled harness is [hypo_loop.py](../../hypo_loop.py). It guards every payload against target text,
  logs every call with its role and model, and only allows pre-cutoff models.
- There are 5 iterations of methods ([loop_methods.py](../../loop_methods.py)). Each is tied to a failure from
  experiment 22 and to a cited article or paper on harness engineering, loop engineering or hypothesis generation
  (30+ sources, loop.md section 2).
- Dev only: 29 configurations, 1,392 runs.
- Six configurations were pre-registered and then run once on test (144 runs).

**Results** (GPT-5.6 reconstruction, 0–4; Δ against Llama closed-book).

| Configuration | Dev | Test | All 12 |
|---|---:|---:|---:|
| `closed_book` (Llama-3.3, baseline) | 0.51 | 0.52 | 0.51 |
| `closed_book_o3mini` | 0.63 | 0.47 | 0.58 |
| `writer_only_b_o3mini` (conservative writer) | 0.67 | 0.52 | 0.62 |
| **`trend_ground_b_o3mini`** (chronological chain → forecast → aimed retrieval → conservative writer) | **0.73** | **0.65** | **0.70** |
| `scaffold_ensemble` (best Llama harness) | 0.61 | 0.43 | 0.55 |

- **Primary pre-registered test:** `trend_ground_b_o3mini` − closed_book.
  - GPT-5.6: +0.125 (CI +0.04 to +0.23), all 4 test papers up.
  - DeepSeek: +0.52 (CI +0.30 to +0.84).
  - All 12 papers: +0.19 (CI +0.11 to +0.27), 11 of 12 up, sign p = 0.006.
- **What helped:** a stronger pre-cutoff model, a writer that does not invent numbers, and retrieval aimed at a
  forecast next step.
- **What did not:** tournaments, self-scoring selection, verifiers, precedents from other systems, forcing a
  solution family on the stronger model, and a cue rule. The Llama harness gain (+0.10 on dev) did not replicate
  (−0.09 on test).
- **What remains unsolved:** the intervention itself. Core (intervention + mechanism) is flat on test (+0.02); the
  gain is in condition, mechanism and outcome.
- **Style check:** GPT-5.6 does not reward length (within-configuration ρ −0.17 to −0.36); DeepSeek partly does.

**Integrity.**
- `must_obey_check.py --loop` passes on all 29 configurations.
- 0 failed runs; leakage counters are zero; test runs are marked final.
- PMC10759803 is flagged for the Llama arms (2 days after the cutoff).

## Experiment 25: fresh held-out test set (test2)

**Why.** The 4-paper test split had been used once, and its titles were later printed during a probe analysis. A
second look would not be blind, and 4 papers give wide intervals.

**Construction** ([benchmark_test2/README.md](./benchmark_test2/README.md), [benchmark_test2.py](../../benchmark_test2.py)).
The rule was pre-registered in loop.md 10.1 before any search.
- The corpus query, restricted to papers after GPT-5.6's cutoff and extended back by month to reach 12.
- The corpus eligibility rules, plus a GPT-5.6 topic screen on the title and abstract.
- The hidden target is extracted from non-Introduction sections. Queries are built by the v3 writer, checker and
  gate, then the v3.1 gap templates.

**Result.**
- 12 papers (2025-07 to 2026-07). 5 are dated after every model's cutoff; 7 are flagged, because the query writer
  could know them.
- Gap types: 6 understanding, 5 design, 1 method.
- 34/36 levels pass the gate; mean answer-word overlap is 2.0–4.9%.
- Evidence pools: 0 late or self records.
- The designer read no title, query or target before the final runs.

**Limits.**
- Recent papers have no citations to rank by, and 8 of 12 are from one MDPI journal.
- The targets come from a different extractor than the original 12, so test2 scores are compared within test2.

## Experiment 26: method loop round 2 and the pre-registered test2 evaluation

**Setup** ([loop.md](../../loop.md) section 10).
- A dev failure analysis of the round-1 best (F9–F14): systematic decision errors that voting cannot fix, and
  niches in the question that the forecaster ignores.
- Iterations 6–8 on dev: 10 configurations, 480 runs. They covered CARS niche occupation (Swales), o1, BM25
  grounding, planner/executor, ITER-RETGEN and relevance-focused grounding.
- Two ideas were tested offline instead of built: cross-model voting and MBR consensus selection.
- A fresh-sample replicate of the incumbent removed the winner's-curse bias from dev comparisons.
- The finalist rule was pre-registered (10.5). No round-2 configuration reached the replicate (0.719), so the
  round-1 method was the round-2 final. 5 configurations were run once on test2 (360 runs).

**Results** (GPT-5.6 reconstruction, test2, 12 fresh papers).

| Configuration | test2 | Δ vs `closed_book` [95% CI] |
|---|---:|---|
| `closed_book` (Llama-3.3, baseline) | 0.46 | – |
| `text_chunks` (Llama-3.3) | 0.40 | −0.06 [−0.13, +0.01] |
| `closed_book_o3mini` | 0.57 | +0.11 [0.00, +0.22] |
| **`writer_only_b_o3mini`** | **0.65** | **+0.18 [+0.07, +0.31], Holm p = 0.043** |
| `trend_ground_b_o3mini` (round-1 final, primary) | 0.57 | +0.11 [+0.01, +0.22] |

- **The primary replicates** on fresh papers on both judges (DeepSeek +0.23), with a smaller effect than before.
- **The harness adds nothing over the model** on test2: −0.003 vs o3-mini closed-book and −0.08 vs the
  conservative writer alone. The difference comes from understanding questions. The trend forecast lands in the
  target's class less often than o3-mini alone (0.35 vs 0.53), although it was slightly more often right on dev,
  where it was selected.
- **On the 5 papers after every cutoff:** writer-only 0.76, harness 0.55, baseline 0.41.
- **Over all 16 held-out papers:** writer-only +0.14 vs the baseline (p = 0.013); harness +0.11; harness −
  writer-only −0.03.
- **Recommended configuration:** o3-mini with the conservative writer, chosen by parsimony; no significant win
  over the harness is claimed.
- **All round-2 dev methods were negative** against the replicate (−0.05 to −0.16).

**Integrity.**
- `must_obey_check.py --loop` passes on all round-2 directories and on the 5 test2 configurations.
- 0 failed runs; leakage counters are zero; test2 runs are final.

## Experiment 27: fresh held-out test set (test3)

**Why.** test and test2 were spent, each used once for its pre-registered finals, and became round-3 development
data. Any round-3 claim needed papers that no round-3 decision had seen.

**Construction** ([benchmark_test3/README.md](./benchmark_test3/README.md); `benchmark_test2.py --set test3`). The rule
was pre-registered in loop.md 11.1 before any search.
- The corpus query with `FIRST_PDATE` from 2024-02-01 to 2025-07-16, ranked by citations.
- Excludes the corpus and test2.
- The same screening, target extraction and query procedure as test2.

**Result.**
- 12 papers (2024-01 to 2025-06): 8 understanding questions and 4 design questions.
- 35/36 levels pass the gate; answer-word overlap is 1.7–4.1%.
- More varied venues than test2.
- All papers precede GPT-5.6's cutoff, so they are flagged, the same residual risk as the original 12.

## Experiment 28: method loop round 3 and the pre-registered test3 evaluation

**Setup** ([loop.md](../../loop.md) section 11).
- Development on dev3 (24 papers) against a fresh-sample replicate of the incumbent (`writer_only_b_o3mini`).
- A failure analysis first ([failure_r3.py](../../failure_r3.py), F15–F18): design questions get the class but not
  the specific lever; method questions are weakest; understanding questions lose on conditions.
- Seven configurations (1,008 runs):
  - forecasting framing;
  - recalled analogies;
  - high reasoning effort;
  - MBR of 5 samples;
  - question-retrieved evidence;
  - evidence + MBR;
  - the replicate itself.
- Two offline checks: consensus over mixed prompts, and target-free selectors.
- gpt-4o could not be probed (rate limits) and was not used.

**Results.**
- **dev3.** Every writer-level change is within ±0.03 of the replicate (0.642). Evidence + MBR (F3) is best at 0.688
  (+0.045 [−0.01, +0.10], 16/8 papers), selected by the pre-registered rule.
- **test3 primary** (12 fresh papers): F3 − incumbent −0.045 [−0.15, +0.06]. **Not replicated.**
  - Incumbent 0.58, F3 0.54, round-1 harness 0.51, Llama baseline 0.50.
  - DeepSeek: incumbent − baseline +0.18 [+0.08, +0.29].
- **All 28 fresh held-out papers** (exploratory): incumbent − baseline +0.11 [+0.05, +0.19], 20/6 papers, p = 0.009
  (DeepSeek +0.27, p = 0.0003). Harness − incumbent −0.05.

**Integrity.**
- `must_obey_check.py --loop` passes on all round-3 directories and the test3 configurations (0 failed runs, zero
  leakage counters, test3 runs final).
- **Exception (must_obey.md 6.7).** The 1,008 dev3 runs have GPT-5.6 and DeepSeek judgments, but target-free audits
  only for F3, and no labels. GPT-5.6 throughput (2–37 calls a minute under shared rate limits) made 2,000 more calls
  impractical. Selection did not use audits. All test3 runs are audited.

## Experiment 29: sensitivity of the score to the amount of context and other inputs

**Question.** Around the recommended configuration (o3-mini with the conservative writer), does increasing or
decreasing one input change the score? Plan pre-registered in loop.md 12.1; script
[sensitivity.py](../../sensitivity.py).

**Setup.** On dev3 (24 papers), 8 new configurations (1,152 runs):
- A. 1, 3, 10 or 30 paper summaries (cards) as context, against closed-book;
- B. 4k or 64k characters of raw text chunks (16k from round 3);
- C. 10 random papers vs the 10 most relevant;
- D. low reasoning effort (medium and high from earlier runs).

E (question detail) uses existing runs on 36 papers.

**Results** (Δ vs closed-book, GPT-5.6 / DeepSeek).
- **Papers as context: U-shaped, never above closed-book.**
  - 1 paper: −0.10 / −0.27.
  - 3 papers: −0.10 / −0.23.
  - 10 papers: −0.07 / −0.14.
  - 30 papers: −0.01 / −0.08.
  - The monotone trend test is not significant, because the response is not monotone.
- **Replication.** The dip, a hypothesis formed after dev3 and written down before the run (loop.md 12.2), replicates
  on test3: 1 paper −0.10 / −0.21; 3 papers −0.10 / −0.23; 30 papers −0.07 / −0.16. Pooled over 36 papers, 1–3
  papers cost −0.10 on GPT-5.6 (p ≤ 0.024) and −0.24 on DeepSeek (p ≤ 0.009).
- **No significant effect from:**
  - raw text, 0 to 64k characters: −0.03 to +0.02 (DeepSeek up to +0.09, trend p = 0.058);
  - relevance, top-10 vs random-10: −0.04 [−0.10, +0.03];
  - reasoning effort: ±0.01;
  - question detail: 0.58 → 0.64, p = 0.34.
- **Mechanism: anchoring** (target-free). With one paper, 30% of the hypothesis's content words come from that
  paper's summary, against 20% by chance, and borrowing goes with lower scores. Borrowing returns to chance as more
  papers are added.

**Integrity.** Both judges on every run. `must_obey_check.py --loop` passes on all 8 directories (0 failed runs; the
test3 replication runs are final). Audits: see loop.md 12.6.

## Comparability and limits, experiments 8 to 29

- Experiment 9 uses the v3 generator, judge and blinding, so its scores are comparable with v3. The judge is
  not calibrated against experts, and KG facts are recognisable to the judge from their wording.
- Experiment 9 has 12 papers. Intervals are wide, and no comparison survives multiple-comparison correction.
- The KG audit is at fact level, not paper level. The guarantee is the SQL filter (cutoff year, target DOI,
  family DOIs), not a per-paper trace.
- Experiment 10 scores candidates with OpenAlex citation counts and selected the corpus with Europe PMC counts,
  so "kept from current corpus" is not a neutral test of agreement.
- Experiment 10 has no outcome measure. It compares selection rules and their topic fit only.
- Experiment 11 reuses experiment 7's tool-agent runs, so its baseline arm has the same gap (one closed-book unit
  missing in experiment 7, which does not enter this comparison). Its critics and reviser are non-Qwen models
  with pre-2024 cutoffs. Two critics share a family with the GPT-5.6 judge, so judge scores may favour their
  wording.
- Across experiments 7, 9 and 11 the judge is the same and is not calibrated against human experts. The
  comparisons are within this protocol, and cross-experiment differences should be read with that in mind.
- Experiments 7, 9 and 11 each use 12 papers. No comparison in any of them survives multiple-comparison
  correction, so none shows a demonstrated improvement.
- Experiments 17 and 18 build a different evidence pool per case from Europe PMC open-access papers outside the
  50-paper corpus. Their ceilings are directly comparable with experiment 14's, but the papers are not the same
  papers. Seed relevance is lexical, and paywalled works enter only as reference-only nodes.
- Experiment 19 shows that the queries used in experiments 3 to 18 leak the answer, increasingly from broad to
  expert. Absolute scores and level effects in those experiments should not be read as hypothesis-generation
  ability. Only within-unit comparisons between methods are fair.
- Experiments 20 and 21 replace the queries and the generator. Rerun scores are comparable with one another, and
  with the original runs only through the experiment-7 factorial. The hidden targets and judges are unchanged.
- Experiment 24 uses benchmark v3.1, so its scores are not directly comparable with experiment 21 (v3). Its
  baselines were re-run on v3.1 inside the harness. Only 4 test papers were held back, and 29 configurations were
  tried on dev, so its dev numbers are optimistic and its test intervals are wide.
- Experiments 25–26 add test2. Its targets were extracted by GPT-5.6 rather than by experiment 3's Qwen pipeline,
  so test2 scores are compared within test2. The pooled 16-paper analysis is exploratory. 39 configurations were
  tried on dev across both rounds; the claims rest on the pre-registered held-out comparisons.
- Experiments 27–28 develop on dev3 (dev + the spent test and test2), so dev3 scores mix two target extractors.
  test3 claims compare configurations within test3. The pooled 28-paper analysis is exploratory. 46 configurations
  have been tried on dev across three rounds; the claims rest on the three pre-registered held-out evaluations.
- Experiment 29 changes the evidence and reasoning budgets on purpose (declared). Its replication on test3 was decided
  after seeing dev3 and is labelled post hoc. The pooled 36-paper estimates are exploratory.
