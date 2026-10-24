# Temporal eval v4: MatKG-augmented tool agent

> **Caveat (added 2026-10-23, experiment 19).** The benchmark queries used here leak the held-out answer: 8% of the answer's words appear in broad queries, 20% in problem_constrained and 47% in expert_context, and per-unit overlap correlates 0.77–0.86 with judge scores. Paired comparisons between methods on the same query remain fair. Absolute scores, differences between query levels and conclusions about query inferability or evidence use are confounded. See [query_leakage/README.md](../query_leakage/README.md).


**Question:** does adding an existing materials knowledge graph (MatKG, CC BY 4.0) to the cutoff-audited
tool agent improve reconstruction of held-out HEA papers, compared with the v3 settings?

**Status (2026-10-22):** complete. 36 KG runs generated and judged. Integrity is not fully verified because
one closed-book baseline unit (`PMC11375712`, broad) failed in v3 and is missing here, as in v3. Every leakage,
temporal and citation check is zero. `COMPLETE` is not written, by design.

## What was added to the v3 design

| Item | v3 (`eval_v3/`) | v4 (`eval_v4_matkg/`) |
|---|---|---|
| Tool agent | list_papers, search_corpus, read_record, submit_hypothesis | adds **kg_lookup(topic)** |
| Evidence the agent can cite | paper text chunks and v2 evidence units | the same, plus **MatKG co-occurrence facts** |
| Settings compared | closed_book, text_oneshot, v2_oneshot, tool_agent | tool_agent_kg, against the four v3 settings |
| Generator, judge, blinding, budget, temperature | as described in eval_v3 | unchanged |

Baseline runs and their absolute judgments are copied from v3 (the same generator, judge and blinding
code), so only the new setting was generated and judged here. The copy step is `temporal_eval_kg.py prepare`.

## MatKG and why it needed a temporal filter

MatKG is built by mining materials entities from paper abstracts. The dump has three parts:

- `ENTPTNERDOI.csv`: one row per entity mention, with `DOI`, `Preferred_Entity`, `NER_Tag` and **`Year`**
  (the publication year of that DOI). This is the table used here.
- `SUBRELOBJ.csv`: aggregated subject-object-relation counts. It has **no DOI and no year**, so it cannot be
  filtered by date. It is not used.
- `entity_uri_mapping.pickle`: not used.

An earlier plan said MatKG "does not store dates" and needed OpenAlex to supply them. That is wrong for
`ENTPTNERDOI`, which carries the year on every row. It is corrected in the
[experiment log addendum](../EXPERIMENT_LOG_2026-10-22.md).

The index ([matkg_index.py](../../../../matkg_index.py)) loads the table into SQLite
(`~/matkg_index/entdoi.sqlite`, 9.2 GB, not in the repository):

| Measure | Value |
|---|---:|
| Rows read | 84,659,831 |
| Rows loaded | 84,101,859 |
| Rows skipped (missing DOI, entity or usable year) | 557,972 |
| Distinct DOIs | 4,141,080 |
| Publication years | 1885 to 2023 |
| Build time | about 11 minutes (00:15 to 00:26 PDT) |

## Temporal rules for KG facts

For a case with cutoff date `C`, `kg_lookup` uses only rows with `Year < year(C)`. Year granularity is
coarse, so this excludes papers from the cutoff year even when they were published before `C`. That is
deliberately conservative.

Excluded from every KG lookup:

1. the held-out paper's own DOI, and
2. DOIs of any paper in the same `work_family_id` as the held-out paper.

Each fact is aggregated over the eligible papers, and its record is dated the most recent year in its support
(`YYYY-12-31`). That date is always earlier than the cutoff, so the existing audit covers KG facts with the
same `temporal_violations` check as paper records.

**Target DOIs in the index:** none of the 12 held-out DOIs appears in MatKG, which stops at 2023. The
exclusion is therefore a guard rather than something that removed facts in this run. It is still tested.

**Association ranking.** Raw co-occurrence counts are dominated by generic terms (`sem`, `xrd`,
`microstructure`). Neighbours are ranked by association: the share of a neighbour's eligible papers that also
mention the query terms. Example for "Hf Mo Ta Ti Zr refractory high entropy alloy ductility" with cutoff 2021:
`enthalpy` (0.34), `nb` (0.26), `zr` (0.18), `strengths` (0.14), `hardness` (0.08).

**Blinding.** The judge sees KG facts as text. A fact reads as "Co-occurrence statistic from earlier materials
abstracts", so a judge can recognise KG-based evidence even without the source label. This is a limitation
of pairwise judging (see below).

## Agent behaviour

Every KG run used the full 12-call budget, as in v3.

| Measure | tool_agent_kg | tool_agent (v3) |
|---|---:|---:|
| Mean `kg_lookup` calls per run | 1.9 | 0 |
| Runs that read at least one KG fact | 6 of 36 | 0 |
| Runs that cited at least one KG fact | 5 of 36 | 0 |
| KG facts cited in total | 11 | 0 |
| Mean paper records accessed | 29.1 (includes KG facts surfaced) | 18.9 |
| Rejected submissions (citation not read) | 2 | 8 across all v3 tool runs |

The agent mostly cited paper chunks even when KG facts were available. The 11 cited facts all predate their
cutoffs (dated 2020 to 2022, checked directly against each run's cutoff).

## Results

Primary metric: reconstruction mean (intervention, condition, mechanism, outcome; 0 to 4). Units are
paper-by-query pairs (12 papers × 3 query levels). Intervals are paper-clustered bootstrap, with 10,000
resamples and seed 20260421. Holm correction spans the four KG comparisons.

| Setting | Runs judged | Reconstruction | Overall (10 dims) |
|---|---:|---:|---:|
| tool_agent_kg | 36/36 | 1.63 | 1.85 |
| tool_agent (v3) | 36/36 | 1.64 | 1.84 |
| text_oneshot (v3) | 36/36 | 1.56 | 1.90 |
| closed_book (v3) | 35/36 | 1.56 | 1.89 |
| v2_oneshot (v3) | 36/36 | 1.49 | 1.85 |

| Comparison (KG minus baseline) | Mean difference | 95% CI | Papers KG higher / lower | Sign-test p | Holm p |
|---|---:|---|---:|---:|---:|
| vs tool_agent | −0.01 | −0.12 to +0.11 | 5 / 5 | 1.00 | 1.00 |
| vs text_oneshot | +0.07 | −0.05 to +0.19 | 6 / 4 | 0.75 | 1.00 |
| vs closed_book | +0.12 | −0.01 to +0.24 | 7 / 3 | 0.34 | 1.00 |
| vs v2_oneshot | +0.15 | +0.06 to +0.24 | 8 / 2 | 0.11 | 0.44 |

Pairwise GPT-5.6 judgments (both orders; order-inconsistent verdicts count as ties):

| Comparison | KG wins | Baseline wins | Ties | KG win rate (no ties) |
|---|---:|---:|---:|---:|
| vs tool_agent | 10 | 18 | 8 | 0.36 |
| vs text_oneshot | 15 | 19 | 2 | 0.44 |
| vs closed_book | 14 | 12 | 9 | 0.54 |
| vs v2_oneshot | 15 | 11 | 10 | 0.58 |

**Reading the results**

- **Adding MatKG did not change reconstruction against the plain tool agent** (1.63 vs 1.64). It also
  did not win the pairwise comparison with that baseline (10 wins to 18 losses).
- The apparent gain over v2 one-shot (+0.15) is the largest difference here, but it does not survive Holm
  correction (adjusted p = 0.44). No KG comparison is significant after correction.
- **The test is weak.** The agent read KG facts in only 6 of 36 runs, so the augmentation was barely
  exercised. Even when read, facts are generic co-occurrence statistics that carry little design
  information.
- A stronger test would force KG use (for example, one required `kg_lookup` per run) or use a narrower KG
  relation (for example, element-to-property pairs with the processing route), and it would need more papers.

## Leakage and integrity

Integrity (see [`results/integrity_kg.json`](results/integrity_kg.json)):

- Temporal violations: 0. Test-paper leaks: 0. Family leaks: 0. Unknown record IDs: 0. Invalid citations: 0.
  Query leaks: 0.
- Judge errors: 0. Single generator identity (`openai:Qwen3.5-35B-A3B-Q4_K_M.gguf`) and single judge
  identity (`trapi:gpt-5.6-sol_2026-07-09`).
- One closed-book baseline unit failed in v3 and is copied here as failed. The gate therefore reports
  `verified: false` (179 of 180 runs judged, 143 of 144 pairs judged).

Limits of the KG audit:

- KG facts are aggregated over many abstracts, so they cannot be traced to one paper in the audit. The
  guarantee is that the SQL excludes the target DOI, the family DOIs and any year at or after the cutoff year.
- Entity-level leakage is not checked. A later paper's wording can appear in an earlier abstract's entity
  list, and nothing in the audit prevents that.
- DOI matching assumes the target has one DOI. A preprint with a different DOI would not be excluded. For the
  12 cases this does not arise, because none of their DOIs appears in MatKG.

## Limitations

- 12 papers × 3 queries. Intervals are wide, and results describe this corpus only.
- The judge is uncalibrated against human experts, as in v3.
- The KG was built from abstracts of more than 4 million papers, so it contains many general HEA facts that
  overlap with the paper evidence.
- Judging is by GPT-5.6 on blinded text. KG-based evidence is recognisable from its wording, so pairwise
  verdicts may partly reflect evidence type rather than quality.

## Reproduce

```bash
# 1. Build the temporal index (once, about 11 minutes; the archive stays in matkg/)
.venv/bin/python matkg_index.py build

# 2. Run the full pipeline (server, prepare, generate, judge, analyze, integrity gate), in tmux
tmux new-session -d -s mathg-eval-kg -c "$PWD" 'bash run_eval_kg.sh; exec bash'

# 3. Tests for the KG path and the v3 path
.venv/bin/python -m unittest test_matkg_eval.py test_temporal_eval_v3.py
```

Outputs: `runs/` (generation records, with KG facts in `accessed_record_ids` and `cited_evidence`),
`judgments/absolute/`, `judgments/pairwise/`, `judgments/errors/` (empty), `results/analysis_kg.json`,
`results/integrity_kg.json` and `results/summary_kg.md`.
