# Experiment log: high-temperature HEA hypothesis generation (experiments 0 to 11)

This document is the full record of every experiment on the 50-paper high-temperature HEA corpus: date,
configuration, results, integrity and status. Experiments 0 to 7 are described in detail in the committed
[EXPERIMENT_LOG.md](./EXPERIMENT_LOG.md) and summarised here. Experiments 8 to 11 are documented in full here,
and they supersede section 8 ("MatKG, planned, blocked") of that log. The committed log is not edited here,
because its working-tree copy has uncommitted changes from another session (it is empty in the working tree).
Once that is resolved, this document can be merged into the log.

Last updated 2026-10-22 (adds the shared configuration reference and experiment 11).

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

1. Index: [matkg_index.py](../../../matkg_index.py) streams `ENTPTNERDOI.csv.tar.gz` into SQLite
   (84.1 M rows, 4.14 M DOIs, years 1885 to 2023, built 2026-10-22 00:15 to 00:26 PDT).
2. Tool: `kg_lookup(topic)` returns neighbours of query terms, ranked by association, from papers with
   `Year < cutoff year`, excluding the held-out DOI and its work family. Each fact is a readable record, so
   the read-before-cite rule still applies.
3. Evaluation: [temporal_eval_kg.py](../../../temporal_eval_kg.py), with the same generator, budget (12
   calls), temperature (0.2), blinding, judge (GPT-5.6) and statistics as v3. Baseline runs and absolute
   judgments are copied from v3 ([eval_v4_matkg/](./eval_v4_matkg/)).
4. Pipeline: [run_eval_kg.sh](../../../run_eval_kg.sh), in tmux session `mathg-eval-kg`. Generation ran
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
See [citation_graph/README.md](./citation_graph/README.md) and [citation_graph.py](../../../citation_graph.py).

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

## Comparability and limits, experiments 8 to 11

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
