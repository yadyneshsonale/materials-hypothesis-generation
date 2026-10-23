# Extraction rubrics: what should the agent be shown from earlier papers?

**Date:** 2026-10-22 to 2026-10-23. **Script:** [rubric_eval.py](../../../rubric_eval.py) (tests in
`test_rubric_eval.py`; runner `run_rubric_eval.sh`; reverse-order speed-up helper `rubric_eval_helper.py`).
**Full tables:** [results/tables.md](results/tables.md). **Machine-readable:** [results/analysis.json](results/analysis.json).

## Question

Earlier experiments gave the generator either raw text chunks or the v2 structured evidence units. The failure
analysis and stage metrics showed that most errors are wrong mechanisms and claims grounded in a different alloy
system. Would a different extraction rubric, meaning a different choice of what to pull out of each earlier paper,
give the agent better evidence and better hypotheses?

## Rubric ideas

Ideas considered. The first four, the mixed pool, and the two existing representations were run.

| Rubric | What is extracted per paper | Failure it targets | Run? |
|---|---|---|---|
| **card** | One digest per paper: question, system, route and parameters, test conditions, key findings with numbers, the authors' mechanism, limitations, future work | Evidence without context (v2 units lose the surrounding study) | Yes |
| **effects** | Intervention → effect records from the authors' own results: base system, change and amount, processing, conditions, structure change, property change with direction and magnitude, attributed mechanism | Wrong intervention and wrong outcome | Yes |
| **mechanisms** | Mechanisms with scope: the mechanism, the system it was shown for, operating conditions, evidence type, supporting observation, where it does not hold, alternatives | Mechanisms borrowed from other systems | Yes |
| **gaps** | Stated limitations, open problems, failed attempts, trade-offs and future work, each with the lever to change | Generating the intervention (the next paper often addresses a stated gap) | Yes |
| **mixed** | Effects, mechanisms and gaps in one retrieval pool | Combining complementary records | Yes |
| text_chunks | Raw section text (existing baseline) | — | Yes (baseline) |
| v2_units | Existing sample-level PSPP units | — | Yes (baseline) |
| design rules | Quantitative relations and thresholds (VEC and phase, density per at.%, strengthening per element) | Physical errors | No |
| protocol cards | Synthesis and characterisation recipes with parameters | Wrong conditions | No |
| cross-paper tables | One property compared across papers and systems | Context for magnitudes | No (needs aggregation) |
| contradiction map | Findings that disagree across papers | Over-confident transfer | No |
| precedent hypotheses | Each paper's own hypothesis, test and verdict | Hypothesis form | No |
| query-conditioned extraction | Extract on demand for the specific query | Retrieval misses | No |

## Design

**Extraction.**

- **Extractor model:** the local generator, Qwen3.5-35B-A3B, with thinking disabled. Using the generator itself
  means extraction adds no knowledge source the generator doesn't already have. A model with a later training
  cutoff could have written later findings into the extracted notes.
- **Input:** each paper's text from the JATS corpus, with back matter (references, funding, contributions and
  similar) stripped. Long papers are split into windows of up to 48,000 characters at paragraph boundaries, which
  gives 55 windows for 50 papers. A window that overflows the output limit is split in half and retried.
- **Own work only.** The authors' own results and arguments; claims the paper attributes to cited works are
  excluded.
- **Quote-grounding.** Every item needs one to three verbatim quotes of 20–300 characters. A quote counts as valid
  if its normalised form (lowercase, alphanumerics only) appears in the source window. Items with no valid quote
  are dropped.
- **Leakage.** Each paper is extracted on its own. Temporal eligibility is enforced when the evidence pool is
  built: only papers public before the held-out paper's date, and not the held-out paper or its work family.

**Generation.**

- One-shot, with the same prompt and settings as earlier experiments (temperature 0.2, 5,000-token cap).
- Every arm gets the **same evidence budget**: the top-ranked records by the shared lexical `retrieve` function
  until 16,000 characters, at most 24 records, each capped at 1,600 characters.
- Paper cards are capped at 3,200 characters instead. They average 2,946 characters, so a 1,600 cap would have cut
  their mechanism and limitation fields. This was caught and fixed after the first 8 card runs; those runs were
  deleted and regenerated.
- **Two samples** per unit, to reduce generation noise. 8 arms × 12 papers × 3 query levels × 2 samples = 576 runs.

**Judging and analysis.**

- **Judges:** GPT-5.6 (`gpt-5.6-sol_2026-07-09`) and DeepSeek-V4-Pro (`DeepSeek-V4-Pro_2026-04-23`), with the same
  blinded rubric as earlier experiments. Each unit's score is the mean of its two samples.
- **Grounding audit:** a target-free GPT-5.6 audit of every hypothesis (claims and their support, mechanism
  source, causal chain, contradictions).
- **Evidence ceiling:** for each case and representation, GPT-5.6 rated whether the 20 records most similar to the
  hidden target anticipate it. This is diagnostic only.
- **Statistics:** paired by unit, paper-clustered bootstrap (10,000 resamples, seed 20260421), exact sign test,
  and Holm correction over the five rubric arms compared with text chunks.

**Integrity.**

- 574 of 576 runs succeeded; each was judged by both judges and audited. Zero temporal violations, zero
  held-out-paper or family leaks, zero invalid citations, zero stage errors.
- Six runs failed the first time and got one retry. The two that still failed are both samples of
  `closed_book` for `PMC11375712` broad. That unit also failed in v3, so it is a reproducible format failure rather
  than noise. Closed-book is therefore scored on 35 units, and its comparisons use the 35 shared units. Copies of
  the failed attempts are in `failed_attempts/`.

## Extraction results

| Metric | card | effects | mechanisms | gaps |
|---|---:|---:|---:|---:|
| Records | 55 | 609 | 423 | 426 |
| Records per paper | 1.1 | 12.2 | 8.5 | 8.5 |
| Items kept after quote check | 100% | 97% | 98% | 99% |
| Dropped (no valid quote) | 0 | 16 | 9 | 3 |
| Valid quotes per kept item | 2.67 | 2.62 | 2.70 | 2.70 |
| Quotes that verified | 90% | 90% | 91% | 95% |
| Mean record length (characters) | 2,946 | 789 | 1,030 | 460 |
| Extracted text as share of source | 9% | 28% | 25% | 11% |

The extractor followed the rubrics well and hardly ever invented quotes.

**Does the representation still hold the information?** For each case, the 20 records most similar to the hidden
target were rated. Reconstructibility: 2 means an expert could plausibly propose the target's intervention and
mechanism from those records alone.

| Representation | Reconstructibility (0–2) | Supportive records in top 20 | Strongly supportive |
|---|---:|---:|---:|
| text_chunks | 1.25 | 14.1 | 2.0 |
| v2_units | 1.08 | 15.8 | 2.7 |
| card | **1.42** | 14.3 | 1.8 |
| effects | 1.17 | 16.3 | 4.1 |
| mechanisms | 1.25 | 16.2 | 2.8 |
| gaps | 1.00 | 13.2 | 1.9 |
| mixed | **1.42** | **16.8** | **5.3** |

Distilling does not lose the anticipating information; the mixed pool concentrates the most of it. So any
difference in final scores comes from how the generator uses the evidence, not from what the evidence contains.

## Results

Reconstruction is scored 0–4. Each unit is the mean of two samples. There are 36 units per arm (35 for closed-book).

| Arm | GPT-5.6 | DeepSeek-V4-Pro | Hard failures (≤0.5) | broad | problem_constrained | expert_context |
|---|---:|---:|---:|---:|---:|---:|
| closed_book | **1.65** | **2.20** | 11% | **0.77** | **1.68** | 2.44 |
| text_chunks | 1.56 | 2.00 | 14% | 0.67 | 1.50 | **2.50** |
| card | 1.52 | 1.98 | 14% | 0.74 | 1.43 | 2.41 |
| v2_units | 1.52 | 1.96 | 17% | 0.58 | 1.54 | 2.44 |
| effects | 1.51 | 1.95 | 22% | 0.59 | 1.53 | 2.42 |
| gaps | 1.48 | 1.89 | 19% | 0.58 | 1.47 | 2.38 |
| mechanisms | 1.46 | 1.90 | 17% | 0.55 | 1.45 | 2.37 |
| mixed | 1.39 | 1.86 | **28%** | 0.54 | 1.38 | 2.25 |

The two judges rank the arms almost identically (Kendall τ = 0.93).

**Each rubric compared with raw text chunks** (paper-clustered, Holm over the five rubrics):

| Rubric − text_chunks | GPT-5.6 difference | 95% CI | Holm p | DeepSeek difference | 95% CI |
|---|---:|---|---:|---:|---|
| card | −0.03 | −0.14 to +0.06 | 1.00 | −0.02 | −0.16 to +0.13 |
| effects | −0.04 | −0.16 to +0.06 | 1.00 | −0.05 | −0.13 to +0.04 |
| gaps | −0.08 | −0.21 to +0.05 | 0.91 | −0.10 | −0.29 to +0.07 |
| mechanisms | −0.10 | −0.22 to +0.01 | 1.00 | −0.09 | −0.23 to +0.05 |
| mixed | **−0.17** | **−0.25 to −0.09** | 0.19 | **−0.14** | **−0.27 to −0.01** |

Closed-book − text_chunks: +0.06 (GPT-5.6, CI −0.06 to +0.19) and +0.15 (DeepSeek, CI +0.03 to +0.27).

**Which method is best?**

- No extraction rubric beats raw text.
- Card and effects are statistically tied with text chunks and v2 units.
- Mechanisms and gaps are slightly worse.
- The mixed pool is the worst evidence representation under both judges, and its interval excludes zero under
  both. It does not survive the Holm correction.
- Closed-book, with no evidence at all, scores highest under both judges. Its lead over text chunks is clear only
  under DeepSeek.

## Why

**1. Evidence anchors the generator on other systems' mechanisms.** The audit labels where each hypothesis's
mechanism came from, without seeing the target. Compared within query level and pooling the evidence arms,
mechanism agreement with the target is:

| Mechanism source | problem_constrained | expert_context |
|---|---:|---:|
| Model's own reasoning (not from evidence) | **1.80** (56 runs) | **2.73** (45 runs) |
| Transferred from another system, with justification | 1.33 (27) | 2.14 (7) |
| Transferred from another system, without justification | 1.10 (84) | 2.22 (116) |

How often each arm transfers a mechanism without justification:

| Arm | broad | problem_constrained | expert_context | Mechanism agreement (all runs) |
|---|---:|---:|---:|---:|
| card | 42% | 54% | 46% | 1.50 |
| gaps | 50% | 33% | 62% | 1.42 |
| text_chunks | 54% | 50% | 71% | 1.53 |
| v2_units | 67% | 33% | 62% | 1.53 |
| effects | 62% | 58% | 75% | 1.56 |
| mechanisms | 71% | 46% | 79% | 1.31 |
| mixed | 62% | 75% | **88%** | **1.21** |

Rubrics that put mechanisms from other alloys in front of the generator (mechanisms, and the mechanism-heavy mixed
pool) produce the most borrowed mechanisms and the lowest mechanism scores. Cards borrow least among the evidence
arms because each card keeps a mechanism tied to its own study context. This is an observed association within
level, not a controlled test.

**2. More grounding does not mean more correct.** The mechanisms and mixed arms have the best-grounded claims
(46–47% of claims at least partly supported by cited evidence, against 27–39% elsewhere), but the lowest scores. The
support is usually for a different alloy: 66–68% of supported claims rest on another system. Evidence arms also have
more internal contradictions (0.96–1.19 per hypothesis, against 0.64 for closed-book), and more contradictions go
with lower scores (ρ = −0.17).

**3. Retrieval, not information, limits the mixed pool.** Mixed holds the most target-anticipating records (5.3
strongly supportive in its target top 20). But its pool is the largest (about 1,230 records per case), and lexical
retrieval with the query puts the fewest of them in context (2.6 supportive records, against 3.6–4.1 for the other
evidence arms).

**4. Closed-book's lead is concentrated in older targets.**

| Arm | 2024 targets (8 papers) | 2025–26 targets (4 papers) |
|---|---:|---:|
| closed_book | **1.68** | 1.59 |
| text_chunks | 1.49 | **1.69** |
| v2_units | 1.46 | 1.65 |
| card | 1.55 | 1.48 |
| effects | 1.49 | 1.55 |

On the newest targets, the ones least likely to be in the generator's training data, raw text and v2 units beat
closed-book. On 2024 targets closed-book leads. This fits closed-book drawing on what the generator already knows
about older papers (its training cutoff is undocumented), rather than reasoning better. It rests on only 4 late
papers.

**5. Judge dimensions.** Closed-book leads on problem alignment (3.40), intervention (1.83), conditions (1.47) and
baseline quality (2.33), and has the lowest novelty (1.90). Evidence arms raise novelty (2.11–2.32) by proposing
ideas from other systems, which are rated more novel but match the target less.

## Failure analysis

A stage-by-stage failure analysis of this experiment is in [failure/README.md](failure/README.md). In short:

- Broad queries fail 79–96% in every arm.
- Target-anticipating evidence reaches the context in 83–97% of runs, but citing it doesn't raise scores within
  a paper, and it hurts on expert queries.
- Wrong mechanisms appear in 69–87% of failing runs.
- The scope fields of the mechanisms rubric are the least faithful extractions.
- The recurring closed-book failure is a prompt conflict ("use only supplied evidence" with none supplied).

## Recommendations

1. **Keep raw text or cards as the representation.** No distilled rubric beat raw text. Cards tie with it with about
   6 whole cards in context, and give the best reconstructibility, so they are a reasonable compact option.
2. **Don't serve mechanisms detached from their systems.** If mechanisms are extracted, show them inside their study
   context (as cards do), and require the generator to state why a mechanism transfers before using it.
3. **Retrieval needs to match larger pools.** A mixed or larger pool only helps with better retrieval (embedding or
   reranking), because lexical retrieval surfaced the fewest supportive records from it.
4. **Separate memorisation from reasoning before choosing a method.** Evaluate on targets published after the
   generator's training data, or test whether the generator recognises each target from its title alone. On the
   newest four targets, evidence already beats closed-book.
5. **Try the rubrics not run here**, especially precedent hypotheses and contradiction maps, which address the
   borrowing problem directly.

## Limitations

- 12 papers and 36 units per arm. No rubric difference survives the Holm correction.
- The ceiling and audit use GPT-5.6, the same family as the main judge. The audit is target-free, but it was not
  hand-validated in this run.
- Records are capped per arm (1,600 characters; 3,200 for cards). Long text chunks are truncated, as in every earlier
  experiment.
- Retrieval is lexical for every arm. A different retriever could change the ranking, especially for large pools.
- The extractor is the generator itself (Qwen). A stronger extractor could produce better records, but would add
  leakage risk unless its training cutoff predates the held-out papers.
- Quote validation checks that a quote exists in the paper, not that the extracted field is a faithful paraphrase
  of it.
- Closed-book is scored on 35 units because one unit failed reproducibly.

## Reproduce

```bash
tmux new-session -d -s mathg-rubric-eval -c "$PWD" 'bash run_rubric_eval.sh; exec bash'
.venv/bin/python rubric_eval.py report
.venv/bin/python -m unittest test_rubric_eval.py
```
