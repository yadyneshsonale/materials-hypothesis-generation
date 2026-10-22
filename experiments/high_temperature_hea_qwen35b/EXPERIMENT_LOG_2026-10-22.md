# Experiment log addendum: MatKG augmentation and citation-graph selection (2026-10-22)

This addendum lists every experiment on the 50-paper high-temperature HEA corpus with its date, method,
results and status. It adds experiments 9 and 10 and supersedes section 8 ("MatKG, planned, blocked") of
[EXPERIMENT_LOG.md](./EXPERIMENT_LOG.md). The committed log is not edited here, because its working-tree copy
currently has uncommitted changes from another session (the file is empty in the working tree). Once that
is resolved, this addendum can be merged into the log.

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

## Correction to section 8 (MatKG)

The committed section 8 said MatKG "does not store dates" and that OpenAlex or Crossref would be needed for
publication dates. That is incorrect for the per-DOI table `ENTPTNERDOI.csv`. Each row carries a `Year`
value for its DOI, and the index filters on it directly. The co-occurrence file `SUBRELOBJ.csv` has no DOI or
year and cannot be date-filtered, so it is not used. The rest of section 8's leakage analysis still holds, and
it is what the design implements.

The section 8 blocker is also resolved. The MatKG files are in `matkg/` (five files, about 3.8 GB, CC BY 4.0), and that folder is excluded from git.

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

## Comparability and limits, added for experiments 9 and 10

- Experiment 9 uses the v3 generator, judge and blinding, so its scores are comparable with v3. The judge is
  not calibrated against experts, and KG facts are recognisable to the judge from their wording.
- Experiment 9 has 12 papers. Intervals are wide, and no comparison survives multiple-comparison correction.
- The KG audit is at fact level, not paper level. The guarantee is the SQL filter (cutoff year, target DOI,
  family DOIs), not a per-paper trace.
- Experiment 10 scores candidates with OpenAlex citation counts and selected the corpus with Europe PMC counts,
  so "kept from current corpus" is not a neutral test of agreement.
- Experiment 10 has no outcome measure. It compares selection rules and their topic fit only.
