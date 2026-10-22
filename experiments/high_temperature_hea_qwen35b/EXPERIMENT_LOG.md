# Experiment log: high-temperature HEA hypothesis generation

This document records every experiment run on the 50-paper high-temperature high-entropy-alloy
(HEA) corpus, in date order. For each run it gives the date, the question, the method, the scale,
the results, the status, and where the outputs live. Dates are git commit dates (UTC-independent,
YYYY-MM-DD as recorded in the repository). Times for the 2026-10-21 eval come from the run's
status file and logs, in Pacific time.

Read this first if you want to know what has been tested, what is comparable, and what is not.

## At a glance

| # | Dates | Experiment | Scale | Generator | Judge | Status | Main location |
|---|---|---|---|---|---|---|---|
| 0 | 2026-09-17 to 2026-09-18 | Early workflow, 67-paper evidence graph, gold comparison | 67 papers; 7 gold papers | Earlier pipeline | Earlier judge | Historical | [README.md](../../README.md) |
| 1 | 2026-09-23 | Screened 50-paper HEA corpus and extraction recall | 50 papers | Qwen (see §Model) | none | Complete | [data/](./data/) |
| 2 | 2026-10-02 | Grounded role and question extraction, review UI, reader questions | 50 papers | Qwen | none | Complete | [outputs/](./outputs/) |
| 3 | 2026-10-03 to 2026-10-04 | Temporal hypothesis reconstruction v2 (4 representations) | 12 cases, 144 runs | Qwen | Qwen | Complete | [temporal_v2/](./temporal_v2/) |
| 4 | 2026-10-05 | Question-centered evidence pipeline and benchmark | 8,848 questions, 180 runs | Qwen | Qwen | Complete | [question_centered/](./question_centered/) |
| 5 | 2026-10-06 | Section-aware data-extraction agent | 50 papers, 276 triggers | Qwen | none (exact-span validation) | Complete | [section_aware/](./section_aware/) |
| 6 | 2026-10-19 | Numbered output bundles and v2 evidence documentation | 50 papers | none | none | Complete | [outputs/](./outputs/) |
| 7 | 2026-10-21 | Temporal eval v3: cutoff-audited tool agent vs baselines | 12 cases, 144 runs | Qwen | TRAPI GPT-5.6 | Complete, 1 unit missing | [eval_v3/](./eval_v3/) |
| 8 | Not started | MatKG knowledge-graph augmentation | Planned | Qwen | GPT-5.6 | Blocked (see §8) | none |

Two judges appear in this log. Experiments 3 and 4 were judged by the same local Qwen model that
generated the hypotheses. Experiment 7 was judged by GPT-5.6 on TRAPI. **Scores from experiments
3 and 4 cannot be compared with experiment 7.**

## Shared setup

### Corpus

- **Papers:** 50 high-temperature HEA papers, JATS XML, open access, not review articles, selected
  by citation rank (screening and download are in `data/corpus/`).
- **Held-out cases:** 12 papers, each with three query levels (`broad`, `problem_constrained`,
  `expert_context`). Each case has a hidden target: the paper's intervention, conditions,
  mechanism, and outcome.
- **Temporal split (experiment 3):** 38 training papers published through 2023, 8 validation
  papers from 2024, and 4 test papers from 2025–2026. The 12 held-out cases are the validation
  and test papers.

### Model

- **Generator:** Qwen3.5-35B-A3B, Q4_K_M quantization, served by llama.cpp (`llama-server`, CUDA 12).
- **Hardware:** 4 × Tesla V100-DGXS, 32 GB each. Four slots, 32k context per slot.
- **Hidden thinking:** disabled (`enable_thinking: false`).
- **Documented training cutoff:** none. This matters for interpreting every experiment (see §Limits).
- **Measured throughput (server logs during the 2026-10 runs):** roughly 2,450–2,740 prompt
  tokens/s and 77–81 generated tokens/s.

### Earlier pipeline (experiment 0)

Before the Qwen experiments, the repository contained a typed evidence graph over a 67-paper
corpus (commit `1732cc7`, 2026-09-18), citation-augmented source context retrieval (`50d0db2`),
and an adaptive hypothesis workflow (`af63d8e`, `187ad57`, 2026-09-17 to 2026-09-18). The README
documents the 11 argumentative roles and a gold comparison against author abstracts for seven
papers. These are historical; they are not rerun here.

## Experiment details

### 1. Corpus screening and extraction recall (2026-09-23)

- **Commits:** `f094866` (screened corpus), `854daa3` (recall and role reconciliation).
- **Question:** can the extraction pipeline recover the scientific content of the 50 papers?
- **Method:** screened open-access JATS papers; improved alloy extraction recall and reconciled
  roles across chunks.
- **Status:** complete. Outputs in `data/` and `outputs/papers/`.

### 2. Grounded role, question, and review-interface work (2026-10-02)

- **Commits:** `4132393` (Qwen high-temperature experiment), `8ee7a0b` (grounded roles and
  questions), `439f431` (outputs organized by paper), `a3730f6`, `089a428`, `46867d8`,
  `1d69007`, `9658607` (review interface), `a59abd4` (high-recall reader questions).
- **Question:** after the expert criticism that the 11 roles and questions did not help
  hypothesis generation, can extraction be grounded in exact source text?
- **Method:** every role and question must cite an exact span in the paper. A review interface
  shows each claim beside its highlighted PDF location.
- **Status:** complete. The 11 roles are kept for provenance, but they are not the main
  representation.

### 3. Temporal hypothesis reconstruction v2 (2026-10-03 to 2026-10-04)

- **Commits:** `c5408bc` (benchmark v2), `d520549` (edge-case recovery), `6a262c4` (bounded
  prompts), `44a0c2f` (citation repair), `25bc74e` (results).
- **Question:** can an agent propose a hypothesis about a held-out paper using only evidence
  published before it?
- **Method:**
  - 12 cases × 3 query levels × 4 representations = 144 runs.
  - Representations: roles only, v1 linked evidence, normalized v2 evidence, and v2 evidence plus
    roles and questions.
  - Cutoff: the held-out paper's publication date.
  - Leakage audits: temporal eligibility, test-paper retrieval, work-family leakage, query
    title and DOI leaks.
  - Scoring: Qwen scores each hypothesis on 0–4 scales (same model as the generator).
- **Results** (mean scores, 0–4; 36 runs per representation):

  | Representation | Exact | Partial | Plausible alternative | Unsupported | Problem alignment | Intervention | Mechanism | Evidence validity | Novelty |
  |---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
  | Roles only | 2 | 8 | 20 | 6 | 3.72 | 2.14 | 2.08 | 2.78 | 2.61 |
  | V1 evidence | 3 | 10 | 17 | 6 | 3.72 | 1.89 | 1.94 | 2.83 | 2.53 |
  | V2 evidence | 2 | 7 | 20 | 7 | 3.39 | 1.81 | 1.75 | 2.58 | 2.42 |
  | V2 + roles + questions | 1 | 8 | 24 | 3 | 3.61 | 1.75 | 1.81 | 2.92 | 2.75 |

- **Interpretation (from the experiment's own README):** the normalized v2 representation did
  **not** improve exact intervention or mechanism reconstruction. Roles only was strongest on
  those. v2 plus roles and questions halved unsupported outputs relative to roles only (6 → 3),
  and had the highest evidence-validity and novelty scores.
- **Integrity:** 144 runs, 0 temporal violations, 0 test-paper retrieval violations, 0 work-family
  leaks, 0 invalid citations, 0 query title or DOI leaks. Citation validation: 74 valid on first
  generation, 5 valid after regeneration.
- **Status:** complete. `temporal_v2/COMPLETE` is present.
- **Limit:** scored by Qwen, not by an independent judge.

### 4. Question-centered evidence pipeline (2026-10-05)

- **Commits:** `1440b62` (pipeline), `2d90d32` (bounded cluster adjudication), `4bed89b` (results).
- **Question:** can the thousands of extracted reader questions be grouped into answerable,
  cross-paper questions?
- **Method:**
  - Reader questions: 8,848 across 50 papers.
  - Answers: 7,664 grounded answers, with 3 rejected.
  - Clustering: 402 coarse clusters, refined to 3,529 clusters, of which 708 span multiple papers.
  - Benchmark: 180 hypothesis-generation runs. The summary lists per-variant results. The three
    variants read in this log are `raw_questions`, `grouped_questions`, and `grouped_answers`
    (36 runs each).
  - Integrity: 0 temporal violations, as reported in the benchmark summary.
- **Results** (mean scores, 0–4, 36 runs per variant):

  | Variant | Intervention | Mechanism | Evidence validity | Novelty | Exact | Unsupported |
  |---|---:|---:|---:|---:|---:|---:|
  | Raw questions | 1.94 | 1.83 | 2.53 | 2.58 | 2 | 9 |
  | Grouped questions | 1.67 | 1.81 | 2.67 | 2.47 | 2 | 9 |
  | Grouped answers | 1.75 | 1.72 | 2.28 | 2.44 | (not read) | (not read) |

- **Status:** complete. Grouping did not improve reconstruction in these runs.
- **Limit:** scored by Qwen, not by an independent judge.

### 5. Section-aware extraction agent (2026-10-06)

- **Commits:** `18a4ac3` (agent), `083f8db` (results), `069b410` (documentation, 2026-10-15).
- **Question:** can a single paragraph be understood alone, or do results need evidence from the
  Methods, Discussion, figure captions, or tables of the same paper?
- **Method:**
  - Start from a validated v2 evidence unit (the trigger).
  - Retrieve related passages from the same paper (Methods, Results, figures, tables).
  - Qwen checks that the passages describe the same sample and experiment.
  - Generate cross-section questions and a research thread, each with exact-span provenance.
- **Results:**
  - 276 triggers, 274 of which yielded questions.
  - 482 cross-section questions.
  - 588 cross-section links.
  - 91 records rejected by validation.
  - 3,307 of 3,307 extracted spans matched the source text exactly.
- **Status:** complete. Outputs in `section_aware/`.
- **Limit:** this experiment measures extraction and provenance, not hypothesis quality.

### 6. Numbered output bundles (2026-10-19)

- **Commits:** `d25a89e` (numbered bundles), `1388318` (shared v2 evidence layer documentation).
- **Purpose:** outputs for papers 1 to 50, each with its PDF, JATS XML, metadata, and extracted
  questions, so that one folder holds everything about one paper.
- **Status:** complete. Validated for 8,848 and 482 questions.

### 7. Temporal eval v3: cutoff-audited tool agent vs baselines (2026-10-21)

This is the current evaluation. Full details are in
[eval_v3/README.md](./eval_v3/README.md). This section gives the timeline and results.

- **Commits:** `256d5f4` (eval and judge routing), `072cecd` (aligned budgets and per-call tool
  cap), `1b7f7a7` (blinded judge payloads and judge-error retry), `a442533` (results).
- **Question:** can an agent that searches only papers published before a target paper's date
  reconstruct that paper's design better than simpler baselines?
- **Settings** (each run once per case and query level):
  - `closed_book`: query and cutoff only, no evidence.
  - `text_oneshot`: top 14 text chunks from eligible papers, in one prompt.
  - `v2_oneshot`: top 14 v2 evidence units, in one prompt.
  - `tool_agent`: `list_papers`, `search_corpus`, `read_record`, then `submit_hypothesis`.
    Citations must be records it read. At most 12 tool calls and 16 model turns.
- **Cutoff:** each held-out paper's earliest public date. A record is eligible only if it is not
  the target, was public before the cutoff, and is not in the target's work family.
- **Blinding:** the judge sees neutral evidence labels (E1, E2, …), not record IDs, source kinds,
  citation metadata, or setting names.
- **Judge:** GPT-5.6 on TRAPI (`gpt-5.6-sol_2026-07-09`). Absolute scoring gives 10 integer
  dimensions on 0–4 plus a classification. Pairwise scoring compares `tool_agent` against each
  baseline in both presentation orders. Orders that disagree count as ties.
- **Pre-specified primary metric:** `reconstruction_mean`, the mean of intervention, condition,
  mechanism, and outcome scores.
- **Statistics:** the unit is the paper (12 papers, three query levels each). Intervals come from
  a cluster bootstrap over papers (10,000 resamples, seed 20260421). Significance is a two-sided
  exact sign test on per-paper differences, with Holm correction across the three primary
  comparisons.

**Timeline (Pacific time, 2026-10-21):**

| Time | Event |
|---|---|
| Before 03:35 | One-case smoke test (PMC10759803): generation, judging, and analysis. Found and fixed that the analysis read the generator identity from the environment and that the integrity flag did not check judgment completeness. |
| 03:41 | First full run launched by `run_eval_v3.sh` in tmux session `mathg-eval-v3`, starting the local Qwen server. |
| About 03:46 | First run stopped after 17 of 144 generations. Found that the one-shot and tool-agent settings had mismatched output caps (5,000 vs 1,800 tokens) and sampling temperatures, and that the tool budget could be exceeded within one batch. The partial outputs were discarded. |
| 03:47 | Relaunched in the same tmux session after aligning settings and enforcing the tool budget per call. |
| 04:20 | Generation finished: 144 runs, 1 failed. |
| 04:20–04:41 | Judging: 143 absolute judgments, 107 of 108 pairwise units. Zero judge errors. |
| 04:41 | Integrity gate not verified: 1 failed generation. Resume ran in about 27 seconds and the unit failed again. |

**Results** (reconstruction mean, 0–4):

| Setting | Units judged | Reconstruction | Overall (10 dims) | Tool calls | Records accessed |
|---|---:|---:|---:|---:|---:|
| `tool_agent` | 36/36 | **1.64** | 1.84 | 12.0 | 18.9 |
| `text_oneshot` | 36/36 | 1.56 | **1.90** | 0 | 14 |
| `closed_book` | 35/36 | 1.56 | 1.89 | 0 | 0 |
| `v2_oneshot` | 36/36 | 1.49 | 1.85 | 0 | 14 |

Primary comparisons (paper-level, 12 papers):

| Comparison | Difference | 95% CI | Papers higher / lower | Sign-test p | Holm p |
|---|---:|---|---:|---:|---:|
| tool − text | +0.08 | −0.07 to +0.21 | 7 / 3 | 0.34 | 0.34 |
| tool − v2 | +0.15 | +0.01 to +0.30 | 9 / 3 | 0.15 | 0.33 |
| tool − closed_book | +0.14 | −0.06 to +0.33 | 8 / 2 | 0.11 | 0.33 |

Pairwise judgments (both orders; ties are order-inconsistent verdicts):

| Comparison | Tool wins | Baseline wins | Ties | Tool win rate (no ties) |
|---|---:|---:|---:|---:|
| vs text | 16 | 12 | 8 | 0.57 |
| vs v2 | 20 | 10 | 6 | 0.67 |
| vs closed_book | 17 | 12 | 6 | 0.59 |

**Integrity:** 0 temporal violations, 0 test-paper or family leaks, 0 unknown record IDs, 0 invalid
citations, 0 query leaks, 0 judge errors. One closed-book unit (`PMC11375712`, broad) failed
generation twice and is missing, so `verified` is `false`. Its failed attempt is kept in
`eval_v3/failed_attempts/`.

**Status:** complete with one missing unit. `COMPLETE` is not written, by design.

**Interpretation:** the tool agent is ahead on the primary metric in all three comparisons, but no
difference survives multiple-comparison correction across 12 papers. Closed-book scores almost as
well as retrieval, so the score may come from general HEA knowledge rather than from the
cutoff-restricted evidence.

## 8. MatKG knowledge-graph augmentation (planned, blocked)

**Question:** does adding an existing materials knowledge graph (MatKG) to the tool agent improve
reconstruction, and can that be tested without leakage?

**What was checked (2026-10-21):**

- **Source and license:** MatKG 1.4 is on Zenodo (DOI `10.5281/zenodo.10144972`, published
  2023-11-16, open access, CC BY 4.0). The 2023 CSV release is `10.5281/zenodo.8349130`. Authors:
  Venugopal and Olivetti (MIT). The Nature Scientific Data paper is cited in the record.
- **Content:** entities such as materials, properties, applications, characterization and
  synthesis methods, and symmetry labels, linked by statistically weighted relations. The record
  describes over 150,000 entities and 3.5 million unique triples, extracted from over 5 million
  papers.
- **Files needed:** `SUBRELOBJ.csv` (184 MB, triples), `ENTPTNERDOI.csv.tar.gz` (970 MB, entity to
  DOI, used for date filtering), and `entity_uri_mapping.pickle` (10 MB). Total about 1.2 GB.
  Disk has about 398 GB free.

**Blocker:** the download was denied by the environment's permission check before it ran. No one
was available to approve it, and I did not retry or route around the denial. No MatKG files were
downloaded, and none are in the repository or in the working directory. Shell access was also
denied for a later read-only check, so the new log is not yet committed.

**Update (2026-10-21, later):** the user approved the download in chat. The permission gate still
blocked it, and a follow-up approval request got no answer. Nothing was downloaded, and I did not
route around the gate. The MatKG work is paused until the files are placed in
`/home/t-ydsonale/data/matkg` or the permission prompt is approved.

**Leakage risk that must be solved before any run:** MatKG was built from more than 5 million
papers, so it includes papers published after the cutoffs and possibly the held-out papers
themselves. Using it unfiltered would leak the answer. The required design is:

1. Keep only triples whose supporting DOIs resolve to papers published before the case cutoff, and
   exclude the held-out paper and its work family.
2. Obtain publication dates for those DOIs from an external bibliographic source (for example
   OpenAlex or Crossref), because MatKG does not store dates.
3. Log each KG-derived record with its DOI, date, and eligibility, and extend the leakage audit to
   cover KG-derived evidence.

**Status:** not run. Approval is needed for the 1.2 GB download, or the user can supply the files.

## Comparability and limits

- **Judges:** experiments 3 and 4 used Qwen as judge, and experiment 7 used GPT-5.6. Only scores
  within the same judge can be compared.
- **Pretraining exposure:** no Qwen training cutoff is documented. Every "temporal" result is
  retrospective. Closed-book performance in experiment 7 is close to retrieval, so memorization is
  a live explanation.
- **Sample size:** all experiments use 12 held-out papers. Intervals are wide, and none of the
  differences in experiments 3, 4, or 7 is statistically significant after correction.
- **Human validation:** no experiment has been calibrated against a materials expert. A 30-item
  blinded calibration is the recommended next step.
- **Integrity:** experiments 3 and 7 verified their audits. Experiment 7 is not fully verified
  (one missing unit), and the reasons are given above.

## File index

| Path | Contents |
|---|---|
| `data/` | Screened corpus and source preparation |
| `outputs/` | Numbered per-paper bundles (1 to 50) |
| `temporal_v2/` | Experiment 3: benchmark cases, runs, audit, and README |
| `question_centered/` | Experiment 4: questions, clusters, benchmark runs |
| `section_aware/` | Experiment 5: papers, triggers, questions, and README |
| `eval_v3/` | Experiment 7: runs, judgments, results, failed attempts, and README |
| `METHODS.md` | Shared methods for the pipeline |
| `README.md` (repository root) | High-level pipeline documentation |
