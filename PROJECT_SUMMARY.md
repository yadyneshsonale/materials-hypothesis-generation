# Project summary: AI hypothesis generation for high-temperature high-entropy alloys

**Status.** 2026-10-27, after experiment 36. This file gathers everything done so far and every main result in one
place.

**Details.**
- [Experiment log](./experiments/high_temperature_hea_qwen35b/EXPERIMENT_LOG_2026-10-22.md): one section per
  experiment.
- [loop.md](./loop.md): method work, pre-registrations and full statistics.
- [must_obey.md](./must_obey.md): the rules every experiment follows.

Scores are on the judges' 0–4 scale (section 2). Unless stated otherwise, "GPT-5.6 / DeepSeek" gives the two
judges' values, and differences come with paper-clustered 95% confidence intervals.

## 1. In short

- **Goal.** Given a research question about high-temperature high-entropy alloys (HEAs), an AI model proposes a
  testable hypothesis: what to change (the intervention), the mechanism, the predicted outcome, its limits and a
  falsifying experiment.
- **How it is tested.** The question comes from a real paper that is newer than the model's knowledge cutoff.
  Two AI judges then score how far the hypothesis agrees with what the paper actually did and found.
- **What exists now.**
  - A 50-paper open-access corpus with quote-grounded evidence extraction.
  - 45 held-out papers in four sets (36 with leakage-checked research questions in two formats, plus test4).
  - A test harness that lets only pre-cutoff models see a question, with two judges, audits and an automatic
    integrity check.
  - 52 harness method configurations and 26 arms of an earlier evaluation suite: evidence pipelines, agents,
    critics, extraction rubrics, a materials knowledge graph and citation graphs.
  - A strictly date-filtered web search ([websearch/](./experiments/high_temperature_hea_qwen35b/websearch/README.md)):
    159 per-question corpora (1,315 papers) and a live search tool for agents.
  - A blind rating package for a materials expert.
  - Measurement checks suggested by two model reviews: judge sanity controls, a checklist judge, failure triage
    and an answer-key audit.
  - Roughly 24,000 hypothesis-generation runs in total.
- **Best method found: the simplest one.** o3-mini with a conservative writer prompt and no retrieved evidence
  (`writer_only_b_o3mini`).
  - Over all 37 fresh held-out papers it scores 0.61 against 0.50 for the Llama-3.3 baseline: +0.11
    [+0.06, +0.17], 26 papers up and 8 down, p = 0.003 (DeepSeek +0.27, p = 0.0001). This includes the fresh test4,
    where it replicated (+0.12 / +0.26).
  - No other method beat it on fresh papers. Stronger allowed models, few-shot examples and a question router did not
    either (experiment 34).
  - Its lead is in overall closeness. On a strict checklist of each paper's specific facts, it and the baseline both
    match only about 6–15% (experiments 33, 35).
- **The absolute level is low.** About 0.6 out of 4, while the paper's actual study, rewritten as a proposal, scores
  3.83. Choosing the paper's specific intervention is the unsolved part.
- **Main lessons.**
  1. **The first benchmark leaked the answer.**
     - Expert-level questions contained 47% of the answer's words, and the generator (Qwen3.5) was newer than the
       papers.
     - Fixing both cut scores from about 1.5 to about 0.5 and erased most differences between methods.
  2. **Evidence does not help.** On clean questions, no evidence pipeline, agent, critic, rubric, knowledge graph
     or citation graph beats a good model answering closed-book. A live, strictly date-filtered web search does not
     help either: neither as corpora from the first 50 search results plus their citation neighbourhood, nor as
     agents that search themselves (experiment 36).
  3. **A few papers as context make results worse.** The model copies their study design. With 30 papers the
     score returns to the closed-book level.
  4. **The two AI judges agree only weakly on clean questions** (ρ ≈ 0.39), so they must be checked against an
     expert.
  5. **The SciMON-style question format changes no conclusion.** It drops the operating conditions, and for a
     quarter of papers it reveals the study design.
  6. **The measurement holds up** (experiment 33).
     - Both judges score the true answer about 4 and wrong or generic answers about 0 (AUC 1.00).
     - Low scores are real differences, not judge or answer-key errors.
     - The judges disagree on whether a hypothesis that differs from the paper is a valid alternative or wrong.
  7. **A stated knowledge cutoff is not enough.** o3 and gpt-5 recall details of 2024–2026 papers from their titles
     alone and were excluded by the memorisation probe.
- **Open items.**
  - The expert's ratings, which will show whether the AI judge can be trusted.
  - Every held-out set, including test4, is used up, so a new method claim needs test5. Only 9 papers qualified
    for test4, so test5 needs a wider topic or later papers.

## 2. How the evaluation works

- **Corpus (evidence for the models)**
  ([data/corpus/README.md](./experiments/high_temperature_hea_qwen35b/data/corpus/README.md)).
  - **Selection.** 50 papers from a Europe PMC search combining HEA terms with high-temperature terms (refractory,
    creep, oxidation, hot corrosion, phase or thermal stability, superalloy, extreme temperature).
  - **Eligibility.** Open access with JATS XML full text; primary research articles (no reviews, corrections,
    data records or retractions); directly on topic.
  - **Ranking.** By citation count, from 88 down to 2.
  - **Conferences.** No eligible conference paper had comparable XML full text.
  - **Filtering per case.** Each case may use only corpus papers published before it, excluding itself and its
    work family.
- **Held-out papers (45).** Each split was used once for a pre-registered test, so all are now "spent".

  | Set | Papers | Dates | Role |
  |---|---:|---|---|
  | dev | 8 | 2024-01 to 2024-11 | method development |
  | test | 4 | 2025-04 to 2026-02 | round-1 test |
  | test2 | 12 | 2025-07 to 2026-07; 5 after every model's cutoff | round-2 test |
  | test3 | 12 | 2024-01 to 2025-06 | round-3 test |
  | test4 | 9 | 2024-11 to 2026-03 | experiment-35 test (the rule targeted 24; only 9 qualified) |

- **The research question (user input).**
  - **v3.1, the main format** ([benchmark_v3_1/](./experiments/high_temperature_hea_qwen35b/benchmark_v3_1/)).
    - Written only from the paper's introduction, with every sentence about the paper's own work removed.
    - The writer never sees the answer. A separate checker that does see it rejects questions that leak or steer.
    - A gate rejects any question sharing more than 10% of the answer's words.
    - Three levels: broad, problem-constrained, expert-context. The question type (design, understanding or
      method) follows the gap the introduction states.
  - **v4, SciMON-style** ([benchmark_v4_scimon/](./experiments/high_temperature_hea_qwen35b/benchmark_v4_scimon/README.md)).
    - "Consider the following context: [abstract background sentences] In that context, which method/material can
      be used for [task], and why?"
    - Built the way SciMON (ACL 2024) builds its input.
- **The hidden answer (target).** Extracted from the paper's results: starting material, intervention, conditions,
  structural change, mechanism, outcome and baseline. There is one frozen answer key per paper.
- **Generators.** Only models whose knowledge cutoff is before the paper are allowed to see a question:
  - Llama-3.3-70B (December 2023);
  - o3-mini, o1 and gpt-4o-mini (October 2023).

  Qwen3.5-35B, released February 2026, was dropped in experiment 21.
- **Judges.**
  - GPT-5.6 (primary) and DeepSeek-V4-Pro (cross-check) each score agreement from 0 to 4 on intervention,
    conditions, mechanism and outcome. The reconstruction score is the mean of the four.
  - Evidence is blinded for the judges.
  - Every run also gets a target-free audit (specificity, chain completeness) and a lever label.
- **Statistics and discipline.**
  - Per-paper paired differences, paper-clustered bootstrap, exact sign test, and Holm correction for multiple
    comparisons.
  - Every held-out test is pre-registered in loop.md before it runs, and runs once.
  - `must_obey_check.py` checks every run directory.

## 3. What you asked for and what was done

| # | Your request | What was done | Experiments |
|---:|---|---|---|
| 1 | Clone and read the repository | Read the existing workflow (67-paper evidence graph, gold comparison) | 0 |
| 2 | The 50 most-cited papers on high-temperature HEAs: no reviews, XML, open access, best venues | Built the 50-paper corpus and checked extraction recall | 1 |
| 3 | The expert: the 11-role extraction and the generated questions make no sense | Redesigned extraction around linked, quote-grounded materials evidence, with question tasks (details in 4.1); built a review interface, a question-centred pipeline and a section-aware extraction agent | 2, 4, 5, 6 |
| 4 | Build and run evaluations | Temporal reconstruction benchmarks with a GPT-5.6 judge; MatKG; citation-count selection; critique; failure analyses; stage metrics; extraction rubrics | 3, 7–15 |
| 5 | Suggest improvements from the failures and compare with the baselines | Five targeted improvements | 16 |
| 6 | A citation-graph variant (N papers, rubrics, node data, top-k) | Five citation-graph variants and their failure analysis | 17, 18 |
| 7 | Is something wrong with the user query? | Yes: the questions leaked the answer | 19 |
| 8 | Check how each paper in the sheet builds its user queries, fix leakage, rerun everything | Related-work survey (9 systems); leak-free benchmark v3; every evaluation rerun with a pre-cutoff generator; failure analysis | 20, 21, 22 |
| 9 | Write must_obey.md and loop.md; try methods recursively, cite sources, failure analysis first | must_obey.md; benchmark v3.1; harness method loop, round 1, with a pre-registered test | 23, 24 |
| 10 | Get better results | Fresh test set test2; round 2 | 25, 26 |
| 11 | Increase it more | Fresh test set test3; round 3 | 27, 28 |
| 12 | Increase or decrease inputs, such as the number of papers as context | Sensitivity study | 29 |
| 13 | What should the next steps be? | Advice: check the judge against the expert first, then coverage evaluation, a non-LLM verifier, a bigger test set, write-up | – |
| 14 | A GitHub folder with everything the expert needs | Blind expert-rating package | 30 |
| 15 | Where is the literature survey? | Pointed to RELATED_WORK.md and loop.md sections 2, 10.3 and 11.3 (about 40 sources) | – |
| 16 | Make the user input like the SciMON paper | Benchmark v4 and a comparison with v3.1 | 31 |
| 17 | Rerun all the experiments this way | Every experiment rerun on v4 | 32 |
| 18 | Two model reviews (Opus 5.5, GPT 6.1): suggest changes and run them | Mapped their generic advice onto the project: measurement checks (judge controls, checklist judge, triage, answer-key audit); stronger generators with a memorisation probe; few-shot examples; a router; a fresh test4 | 33, 34, 35 |
| 19 | Add a web search tool to all the baselines and rerun all the experiments: the first N papers of a web search, strictly date-filtered, expanded through the citation graph, from the XML, with no leakage | Europe PMC web search with Crossref dates and code-enforced filters; 159 corpora (first 50 results + co-cited references); a live search tool for agents; all 30 evidence configurations, 3 new web agents and the whole suite re-run; leakage checks | 36 |

## 4. Results by phase

### 4.1 Corpus and extraction (experiments 0–6)

- **Experiment 0.** The original workflow: a 67-paper evidence graph compared with 7 gold papers (historical).
- **Experiment 1.** The 50-paper corpus (section 2).
- **Experiment 2.** Grounded extraction of roles and questions, a review interface, and questions written for the
  reader.
- **The expert's criticism.**
  - The 11 argumentative roles (problem motivation, prior limitation, hypothesis, causal claim, mechanism, evidence,
    limitation and others) made no sense alone or together.
  - The generated questions added no value.
  - Diagnosis: rhetorical roles split apart the chain a materials scientist reasons with: material → intervention →
    structure → mechanism → property, under stated conditions and against a baseline.
- **Response.**
  - Linked, quote-grounded materials evidence units (v2).
  - Question tasks for baseline, causal chain, intervention, boundary or failure regime, and discriminating evidence.
  - The 11 roles were kept only for compatibility.
- **Experiment 4.** A question-centred evidence pipeline: 8,848 questions grounded in v2 evidence.
- **Experiment 5.** A section-aware extraction agent. It starts from a validated result, finds the related methods,
  figures and tables in the same paper, and checks that they concern the same sample (276 triggers, exact-span
  validation).
- **Experiment 6.** Numbered output bundles and documentation.

### 4.2 First evaluations, later found invalid (experiments 3–18)

These experiments used leaky questions and a generator newer than the papers (found in experiment 19). Their
absolute scores and their broad-to-expert gradients are not meaningful. They were all rerun cleanly in experiment
21.

| Exp. | What | Main result at the time |
|---:|---|---|
| 3 | Four evidence representations | Retrieving roles only gave the best intervention and mechanism scores |
| 7 | Cutoff-audited tool agent vs baselines | Tool agent 1.64; text one-shot 1.56; closed-book 1.56; v2 evidence 1.49 |
| 9 | Agent with a MatKG knowledge-graph tool | 1.63 vs 1.64 without; the KG was cited in 5 of 36 runs |
| 10 | Corpus by citation count or citation graph | Ranking by count alone keeps 24 of the 50 papers and drifts off topic; corpus kept |
| 11 | Three critics plus a reviser | 1.49 vs 1.64 for the original (−0.15, not significant); revisions hedge; novelty −0.50 |
| 12 | Failure analysis of 8 methods | Score tracks how inferable the answer is from the query (ρ 0.82). Supportive records surfaced in 94–100% of runs, but only 6–7% were read. Unsupported mechanism transfer in 39–56% |
| 13 | Stage metrics | Best-of-2 sampling +0.11; best method per unit +0.33, so selection had headroom |
| 14 | Extraction rubrics | Closed-book 1.65 > raw text 1.56 > cards 1.52 > … > mixed 1.39; no rubric beats raw text |
| 15 | Rubric failure analysis | Broad-level failure 79–96%; a wrong mechanism in 69–87% of failures; extracted fields 86–93% supported |
| 16 | Targeted improvements | System matching raised mechanism agreement (1.53 → 1.62) and evidence validity, but nothing beat closed-book after correction. The selector picked the first candidate 72% of the time |
| 17 | Citation-graph evidence (264 full-text papers, 9,899 citer statements) | Every variant scored 1.49–1.52, against raw text 1.56 and closed-book 1.65 |
| 18 | Citation-graph failure analysis | 72% of citer statements faithful; the graph did not add target-relevant evidence |

### 4.3 Finding and fixing the leak (experiments 19–23)

- **Experiment 19: the questions leaked the answer.** The questions had been written in the same call that saw the
  paper's results.

  | Question level | Answer words in the question, mean | Maximum |
  |---|---:|---:|
  | Broad | 8% | 16% |
  | Problem-constrained | 20% | 27% |
  | Expert-context | 47% | 65% |

  Overlap predicted the score: ρ = 0.77–0.86 across methods.
- **Experiment 20: leak-free benchmark v3.**
  - Questions are written from the redacted introduction, with a separate checker and the 10% gate. Overlap fell to
    2% / 6% / 5%, and 34 of 36 questions pass the gate.
  - Memorisation probe: Qwen recalled specific details in 33% of probes, Llama-3.3 in 8%.
- **Experiment 21: every evaluation rerun cleanly.**
  - Experiments 7, 9, 11, 14, 16 and 17 were rerun with clean questions and Llama-3.3: 1,512 runs, plus 72
    selections and a 288-run factorial.
  - Scores fell from 1.39–1.65 to 0.35–0.60, and the level gradient vanished.
  - The factorial shows the drop came from the questions, not the generator: Qwen 1.56 → 0.50, Llama 1.40 → 0.45.
  - Best clean arm: closed-book (0.60). No evidence method beat it.
- **Experiment 22: failure analysis of the clean rerun.**
  - Intervention agreement was 0.16 of 4. 79% of hypotheses proposed a different kind of intervention, and none
    proposed the paper's exact one.
  - 4 of 12 papers were studies rather than interventions, yet every question asked for an intervention.
- **Experiment 23: benchmark v3.1 and must_obey.md.**
  - A gap classifier sets the question type (design, understanding or method). 8 cases were rewritten, and 34 of
    36 levels pass the gate.
  - must_obey.md was written, with an automatic checker.
  - o3-mini and gpt-4o-mini were cleared as generators. Their memorisation hits were 17% and 0%, and o3-mini's were
    all inferable from the title.

### 4.4 Method loop and three held-out tests (experiments 24–28)

**Round 1 (experiment 24).**
- 29 configurations on dev (1,392 runs). Each method was tied to a failure from experiment 22 and to a cited source
  on harness, loop or hypothesis engineering.
- Six configurations were pre-registered and run once on test.

| Configuration | Dev (8) | Test (4) | All 12 |
|---|---:|---:|---:|
| `closed_book` (Llama-3.3, baseline) | 0.51 | 0.52 | 0.51 |
| `closed_book_o3mini` | 0.63 | 0.47 | 0.58 |
| `writer_only_b_o3mini` (conservative writer) | 0.67 | 0.52 | 0.62 |
| `trend_ground_b_o3mini` (trend chain → forecast → targeted retrieval → conservative writer) | 0.73 | 0.65 | 0.70 |
| `scaffold_ensemble` (best Llama harness) | 0.61 | 0.43 | 0.55 |

- **Pre-registered primary test.** `trend_ground_b_o3mini` − baseline on test: +0.125 [+0.04, +0.23] (DeepSeek
  +0.52). Over all 12 papers: +0.19 [+0.11, +0.27], 11 of 12 papers up.
- **What helped.** A stronger pre-cutoff model, a writer that does not invent numbers, and retrieval aimed at a
  forecast next step.
- **What did not.** Tournaments, self-scoring selection, verifiers, precedents from other systems, forcing a
  solution family, and a cue rule.

**Round 2 (experiments 25–26).**
- **test2.** A fresh set of 12 papers from 2025-07 to 2026-07 (34 of 36 levels pass the gate). It was needed because
  the 4-paper test had been seen.
- **Development.** 10 new configurations on dev (480 runs) were all worse than a fresh replicate of the incumbent
  (−0.05 to −0.16).

| Configuration | test2 | Δ vs baseline |
|---|---:|---|
| `closed_book` (Llama-3.3) | 0.46 | – |
| `text_chunks` (Llama-3.3) | 0.40 | −0.06 [−0.13, +0.01] |
| `closed_book_o3mini` | 0.57 | +0.11 [0.00, +0.22] |
| **`writer_only_b_o3mini`** | **0.65** | **+0.18 [+0.07, +0.31], Holm p = 0.043** |
| `trend_ground_b_o3mini` (round-1 winner) | 0.57 | +0.11 [+0.01, +0.22] |

- **The harness adds nothing over the model.** It is −0.08 against the conservative writer alone.
- **On the 5 papers after every model's cutoff:** writer 0.76, harness 0.55, baseline 0.41.
- **Recommended from here on:** `writer_only_b_o3mini`, chosen by parsimony.

**Round 3 (experiments 27–28).**
- **test3.** 12 papers from 2024-01 to 2025-06 (35 of 36 levels pass the gate).
- **Development set dev3.** dev + test + test2 = 24 papers. Seven configurations (1,008 runs): forecasting framing,
  recalled analogies, high reasoning effort, MBR, evidence, evidence + MBR, and a fresh replicate of the incumbent.
- **Dev3 winner.** Evidence + MBR, +0.045 [−0.01, +0.10].
- **On test3 it did not replicate:** −0.045 [−0.15, +0.06]. Incumbent 0.58, evidence + MBR 0.54, round-1 harness
  0.51, baseline 0.50 (DeepSeek: incumbent − baseline +0.18 [+0.08, +0.29]).
- **All 28 fresh held-out papers** (exploratory): incumbent − baseline +0.11 [+0.05, +0.19], 20 papers up and 6
  down, p = 0.009 (DeepSeek +0.27, p = 0.0003).

### 4.5 Sensitivity: more or less of each input (experiment 29)

All changes are against the recommended writer (closed-book), on 24 dev3 papers, with GPT-5.6 / DeepSeek.

- **Papers as context lower the score.** The effect is U-shaped and never goes above closed-book.

  | Papers as context | Change |
  |---:|---|
  | 1 | −0.10 / −0.27 |
  | 3 | −0.10 / −0.23 |
  | 10 | −0.07 / −0.14 |
  | 30 | −0.01 / −0.08 |

- **The dip replicated on test3.** Pooled over 36 papers, 1–3 papers cost −0.10 (p ≤ 0.024) / −0.24 (p ≤ 0.009).
- **Mechanism: anchoring.** With one paper, 30% of the hypothesis's content words come from that paper's summary,
  against 20% by chance, and more borrowing goes with lower scores.
- **No significant effect from:**
  - raw text from 0 to 64,000 characters;
  - relevant vs random papers (−0.04 [−0.10, +0.03]);
  - reasoning effort (±0.01);
  - question detail level (0.58 → 0.64, p = 0.34).

### 4.6 Expert evaluation package (experiment 30)

- **Why.** Every result rests on an AI judge, and the two judges agree only weakly on clean questions (ρ ≈ 0.39).
- **Package** ([expert_evaluation/](./expert_evaluation/README.md)). 20 papers, each with its question and three
  blinded hypotheses:
  - the o3-mini writer;
  - the Llama baseline;
  - the paper's real study, rewritten as a proposal.
- **Rating.**
  - Part 1 (blind): plausibility, testability, usefulness, whether the question makes sense, and which hypothesis
    the authors pursued.
  - Part 2 (with the paper): agreement on the judge's four dimensions, accuracy of the answer key, and hints in the
    question.
  - The package includes step-by-step READMEs and an Excel sheet with drop-down lists. The key is kept outside the
    expert's folder.
- **AI judges on the same 60 items.**

  | Hypothesis | GPT-5.6 | DeepSeek |
  |---|---:|---:|
  | Real study, rewritten | 3.83 | 4.00 |
  | o3-mini writer | 0.61 | 0.66 |
  | Llama baseline | 0.49 | 0.29 |

- **Status.** Awaiting the expert's ratings. The pre-registered analysis (expert vs GPT-5.6 rank correlation) is
  ready in `expert_eval_analysis.py`.

### 4.7 SciMON-style input (experiment 31) and every experiment rerun on it (experiment 32)

**Experiment 31: building the input the SciMON way.**
- **Construction.** Abstract sentences labelled Background, a task-side seed term from the paper's most important
  relation, and SciMON's template, all checked by the same leakage gate.
- **Only 9 of 36 papers give a clean input.**
  - 14 abstracts have no background sentence, so the input is a bare one-line question such as "Which material can
    be used for ductility, and why?"
  - 13 fail the leakage gate: in 11 the seed names the study's own design, and 2 contain answer phrases.
- **Four configurations against v3.1** (v4 − v3.1, GPT-5.6 / DeepSeek):

  | Configuration | Change |
  |---|---|
  | Llama baseline | −0.02 / **−0.13** (significant) |
  | o3-mini closed-book | +0.12 / −0.26 |
  | o3-mini writer | +0.08 / −0.17 |
  | o3-mini with evidence | −0.07 / −0.33 |

- **Where the gains come from.** The only significant GPT-5.6 gains are on inputs that steer toward the answer
  (+0.23 to +0.29). Both judges mark condition agreement down, because abstract background sentences rarely state
  temperature or environment.

**Experiment 32: every experiment rerun on v4.**
- **Harness.** All 52 configurations on 36 papers: 3,456 new runs, plus experiment 31's 288.
- **Suite.** Experiments 7, 9, 11, 14, 16 and 17 on their 12 papers: 504 runs, 24 revisions and 24 selections. The
  citation graphs were rebuilt from the v4 input.
- **Evaluation.** Every run has both judges, an audit and a lever label. The integrity check passes on all 58 run
  directories.

| | GPT-5.6 | DeepSeek |
|---|---|---|
| Harness, v4 − v3.1 (mean of 52 configurations) | +0.02, none significant after correction | −0.16, lower for 49 of 52 |
| Suite, v4 − experiment 21 (mean of 26 arms) | −0.05, none significant | −0.05 |
| Rank agreement of configurations between formats | ρ = 0.77 | ρ = 0.72 |

- **Unchanged conclusions.** By the pre-registered rule the conclusions do not depend on the input format: the
  rankings agree well above the 0.5 threshold, and no comparison flips significantly.
- **Still holds on v4:**
  - nothing beats the o3-mini writer, and six Llama multi-step methods are significantly worse with both judges;
  - one to three papers as context hurt, more than on v3.1 (one paper −0.24 / −0.23);
  - in the suite, nothing beats closed-book.
- **Weaker on v4.** The writer's lead over Llama (+0.22 / +0.23) is absent on the 9 clean inputs with GPT-5.6
  (−0.01).
- **Retrieval methods depend on the input format.** The citation graphs found almost entirely different literature
  (1 of 10 seed papers shared), and three graph arms fell by 0.12–0.18.
- **Decision.** v3.1 stays the main input. v4 is kept as a SciMON-comparable variant.

### 4.8 Changes suggested by two model reviews (experiments 33–35)

Two model reviews (Opus 5.5 and GPT 6.1) gave generic advice, because their models never saw the project. The
suggestions that were new here were run under a pre-registered plan (loop.md section 16).

**Experiment 33: is the measurement sound?**
- **Outputs are well formed.** In 10,896 runs: 4 empty, 23 abstentions, 15 truncation retries.
- **Both judges pass every sanity control.**

  | Control (built by code from the answer keys) | GPT-5.6 | DeepSeek |
  |---|---:|---:|
  | The paper's own answer | 3.90 | 4.00 |
  | Intervention swapped | 2.67 | 2.63 |
  | Mechanism swapped | 2.97 | 2.91 |
  | Another paper's answer | 0.00–0.15 | 0.00–0.04 |
  | Generic textbook hypothesis | 0.13 | 0.10 |

  AUC is 1.00, and each swap lowers the matching dimension most.
- **Low scores are real.** A triage of 60 runs found 0–3% judge or answer-key errors. The judges disagree on what the
  differing hypotheses are: GPT-5.6 calls most of them valid alternatives the paper did not test, DeepSeek calls them
  wrong (κ = 0.05).
- **Checklist judge** (430 yes/partial/no facts from the answer keys, quotes verified). It is stable (retest ρ 0.86)
  but makes the two judges agree less (ρ 0.45 vs 0.58), so it was not adopted. It shows that both the best method
  and the baseline match only about 6–15% of each paper's specific facts.
- **Answer keys.** No key is unusable. GPT-5.6 questioned 4 and DeepSeek none, so none was flagged.

**Experiment 34: method changes** (on the 36 spent papers, against a fresh re-run of the best method).
- **Memorisation probe.** o3 and gpt-5 recall details of these papers from the title alone: 33% and 44% against 7%
  for Llama. Both were excluded.

| Change | GPT-5.6 | DeepSeek |
|---|---|---|
| gpt-4o writer | +0.04 [−0.02, +0.10] | −0.08 |
| gpt-4.1 writer (29 papers) | +0.02 | −0.02 |
| o4-mini writer (29 papers) | −0.14 (significant) | −0.21 |
| Few-shot examples, similar / diverse | +0.01 / −0.00 | +0.04 / −0.01 |
| Question-type router | +0.01 | +0.01 |

None qualified as a finalist.

**Experiment 35: fresh test4.**
- **Build.** Under the pre-registered rule, 9 papers (2024-11 to 2026-03) qualified out of 66 screened.
- **Run.** The best method against the Llama baseline, once.
  - test4: +0.12 [+0.02, +0.21] (GPT-5.6), +0.26 (DeepSeek), +0.19 on the two-judge mean (p = 0.039).
  - All 37 fresh papers: +0.11 [+0.06, +0.17], 26 papers up and 8 down, p = 0.003 (DeepSeek +0.27, p = 0.0001).

### 4.9 Web search for every baseline (experiment 36)

**What was built** ([websearch/](./experiments/high_temperature_hea_qwen35b/websearch/README.md)).
- **Search.** For each held-out paper and question, a pre-cutoff model writes three search phrases, and Europe PMC
  (open-access JATS XML) is searched live.
- **Filter.** A paper is kept only if:
  - Europe PMC and Crossref both date it before the paper;
  - it is not the paper, a version of it, or any held-out paper;
  - it is not a preprint or review;
  - it does not cite the paper.
- **Corpus.** The first 50 survivors by relevance, plus up to 50 references co-cited by at least two of them. Text
  comes verbatim from the XML.
- **Agents' tool.** Agents get a live search with the same filters on every call.
- **Size.** 159 corpora, 1,315 papers.

**What was re-run.**
- **Harness.** All 30 harness configurations that use evidence (7,398 runs), with three new agents that search the
  web themselves.
- **Suite.** The whole experiment-21 suite (1,152 runs).

**Results** (GPT-5.6; 45 papers unless stated).

| Baseline | Without evidence | With web text | With a web-search agent |
|---|---:|---:|---:|
| Llama-3.3 | 0.50 | 0.50 (−0.00 [−0.06, +0.06]) | 0.42 (−0.08 [−0.15, −0.01], not significant after Holm) |
| o3-mini (24 papers) | 0.58 | – | 0.58 (+0.00) |
| Best method's writer (o3-mini) | 0.62 | 0.61 (−0.02 [−0.07, +0.04]) | 0.56 (−0.07 [−0.11, −0.02], not significant after Holm) |

- **Web search helps no baseline.** DeepSeek agrees, except for a +0.13 on the o3-mini agent that GPT-5.6 does not
  see.
- **No difference from the fixed corpus.** Across the 30 configurations, web corpora are no better than the fixed
  50-paper corpus with GPT-5.6, and method rankings hardly change (ρ = 0.79).
- **Suite.** No web arm beats closed-book.
- **No leakage detected.**
  - All leakage counters are zero, and every evidence record's dates were re-checked.
  - No evidence paper contains more than 1.5% of a held-out paper's text.
  - The answer-word test rises only where question-targeted search brings more on-topic evidence, and those scores
    did not rise.
- **Practical findings.**
  - OpenAlex now caps unkeyed use at 1,000 requests a day, so Crossref replaced it as the second date source.
  - Llama-3.3 on Azure stops calling tools when a fifth tool is offered.

## 5. The recommended method on every held-out comparison

`writer_only_b_o3mini` (o3-mini, conservative writer, no evidence) against the Llama-3.3 closed-book baseline.

| Comparison | Papers | Writer | Baseline | Difference, GPT-5.6 | DeepSeek |
|---|---:|---:|---:|---|---|
| test (round 1) | 4 | 0.52 | 0.52 | 0.00 | – |
| test2 (round 2) | 12 | 0.65 | 0.46 | +0.18 [+0.07, +0.31], Holm p = 0.043 | – |
| test3 (round 3) | 12 | 0.58 | 0.50 | +0.08 | +0.18 [+0.08, +0.29] |
| All 28 fresh held-out papers (pooled) | 28 | 0.60 | 0.49 | +0.11 [+0.05, +0.19], p = 0.009 | +0.27, p = 0.0003 |
| test4 (experiment 35) | 9 | 0.66 | 0.54 | +0.12 [+0.02, +0.21] | +0.26 [+0.10, +0.41] |
| **All 37 fresh held-out papers (pooled)** | 37 | 0.61 | 0.50 | **+0.11 [+0.06, +0.17], p = 0.003** | **+0.27 [+0.18, +0.36], p = 0.0001** |
| All 37, mean of the two judges | 37 | 0.59 | 0.40 | +0.19 [+0.13, +0.26], p = 0.0001 | – |
| Checklist judge, 36 spent papers (secondary) | 36 | 0.35 | 0.32 | +0.04 [−0.02, +0.09] | −0.01 |
| SciMON-style input (experiment 32) | 36 | 0.69 | 0.47 | +0.22 [+0.08, +0.38] | +0.23 [+0.10, +0.39] |
| SciMON-style, clean inputs only | 9 | – | – | −0.01 [−0.17, +0.15] | +0.15 |

## 6. What helps and what does not

**Helps.**
- A stronger pre-cutoff model: o3-mini over Llama-3.3.
- A conservative writer that does not invent numbers or unsupported specifics.
- In round 1, retrieval aimed at a forecast next step. It did not hold on test2, where the harness added nothing
  over the writer.

**Does not help** (on clean questions).
- **Evidence of any kind:**
  - raw text and extracted rubrics (cards, effects, mechanisms, gaps);
  - v2 evidence units;
  - tool agents and MatKG;
  - citation graphs.

  (Experiments 14–17, 21, 32.)
- **Critics and revision.** They make hypotheses hedge (experiments 11, 21).
- **Harness tricks:** tournaments, self-scoring selection, verifiers, precedents from other systems, forced solution
  families (experiment 24).
- **Search-style methods:** MBR and consensus, evidence + MBR, recalled analogies, forecasting framing, more
  reasoning effort (experiments 28–29).
- **Context and input:**
  - 1–3 related papers as context make results worse through anchoring (experiments 29, 32);
  - question detail has no significant effect (experiment 29);
  - the SciMON-style input is no improvement (experiments 31–32).
- **Web search** (experiment 36): web-search corpora (the first 50 results plus co-cited references) for all 30
  evidence configurations and the suite, and agents that search the web themselves.
- **Methods suggested by two model reviews** (experiment 34):
  - stronger allowed generators (gpt-4o, gpt-4.1, o4-mini);
  - few-shot worked examples;
  - a question-type router.

## 7. Integrity: the rules and the problems they caught

**must_obey.md**, which every prompt follows, covers:
- the benchmark and spent splits;
- model knowledge cutoffs;
- leakage-free question construction;
- evidence and tool leakage;
- payload hygiene and blinding;
- evaluation design (two judges, audits, pre-registration, Holm);
- records, the method loop, a checklist, and a log of past violations.

**Problems found and fixed.**

| Where | Problem | Fix |
|---|---|---|
| Experiments 3–18 | Questions written in the same call that saw the results (47% of the answer's words) | Benchmark v3 and v3.1 (experiments 20, 23) |
| Experiments 3–18 | Generator Qwen3.5 newer than the papers (33% specific recall) | Pre-cutoff generators only (experiment 21) |
| Experiment 17 | Search phrases written by the post-cutoff model from leaky questions | Pre-cutoff writer, clean question |
| Experiment 16 | Selector picked the first candidate 72% of the time | Pairwise judgments in both orders |
| Experiment 21 | Bootstrap intervals depended on Python's hash seed | Sorted keys |
| After experiment 24 | The 4 test papers had been used once, and their titles were later printed in an analysis, so the split was no longer blind | Fresh test2, then test3 |
| Rounds 2–3 | Winner's curse when comparing with a selected dev score | Fresh-sample replicates of the incumbent |
| Experiment 31 | One case wrongly flagged as failing the gate | Builder fixed and tested |
| Experiment 32 | Llama-extracted citation statements silently dropped by the parser | Parser fixed, papers re-extracted, runs redone; first attempt kept but not analysed |
| Experiment 34 | o3 and gpt-5 recall details of 2024–2026 papers despite stated cutoffs before them | Memorisation probe required for every generator; both forbidden (must_obey.md table) |
| Experiment 34 | Registering test4 changed the case pool of the frozen expert-package selection | Selection fixed to its original sets; test catches it |
| Experiment 36 | OpenAlex's daily budget ran out mid-build and failed requests silently dropped papers from corpora | Build stopped; Crossref became the second date source; all corpora rebuilt; failures now raise instead of dropping |
| Experiments 9, 21, 36 | With Llama-3.3 on Azure, a fifth tool breaks tool calling, so experiment 9's KG agent (35 of 36 runs) never used a tool | Web search placed inside the existing search tool; the KG result is reported as uninformative |

## 8. Limitations and open questions

- **The judge is not calibrated.**
  - The AI judges reward closeness to one paper's result, not truth or usefulness, so a different but valid
    hypothesis scores low.
  - On clean questions the two judges agree only weakly (ρ ≈ 0.39) and often differ in direction (experiments
    31–32).
  - The expert ratings will settle this.
- **The checklist shows the ceiling.** Both the best method and the baseline reproduce only about 6–15% of a paper's
  specific facts. The measured gains are in partial, overall closeness.
- **Small samples.**
  - 45 held-out papers in total; the pre-registered tests used 4, 12, 12 and 9.
  - Most differences between methods are within noise.
- **No unspent held-out set remains.** Any new method claim needs test5. The test4 rule yielded only 9 papers, so
  test5 needs a wider topic or later papers.
- **Residual knowledge risk.**
  - The original 12 papers and test3 predate GPT-5.6's cutoff (flagged); GPT-5.6 only writes questions and judges.
  - Two papers are dated 1–2 days after Llama-3.3's cutoff.
- **Answer-key source.** test2, test3 and test4 answer keys were extracted by GPT-5.6, the original 12 by Qwen.
  Scores are compared within each set. The experiment-33 audit found no unusable key.
- **Narrow corpus.** One topic, 50 open-access papers. 8 of the 12 test2 papers come from one MDPI journal. The web
  corpora (experiment 36) are wider but still limited to open-access papers with XML in Europe PMC.
- **Experiment 36 is exploratory.** All 45 papers were already spent. Its evaluations ran on a second instance of
  the GPT-5.6 deployment because of rate limits, and lever labels were made only for the primary comparison.
- **Low absolute level.** About 0.6 out of 4. Choosing the paper's intervention is the core unsolved problem.

## 9. Where to find everything

| What | Where |
|---|---|
| Rules; instructions for every agent | [must_obey.md](./must_obey.md), [AGENTS.md](./AGENTS.md) |
| Method work, pre-registrations, all statistics | [loop.md](./loop.md) (sections 0–17) |
| One section per experiment | [EXPERIMENT_LOG_2026-10-22.md](./experiments/high_temperature_hea_qwen35b/EXPERIMENT_LOG_2026-10-22.md) |
| Literature reviewed | [RELATED_WORK.md](./experiments/high_temperature_hea_qwen35b/RELATED_WORK.md) (9 hypothesis-generation systems); loop.md sections 2, 10.3 and 11.3 (about 40 sources) |
| Corpus | [data/corpus/](./experiments/high_temperature_hea_qwen35b/data/corpus/README.md) |
| Question sets | [benchmark_v3/](./experiments/high_temperature_hea_qwen35b/benchmark_v3/), [benchmark_v3_1/](./experiments/high_temperature_hea_qwen35b/benchmark_v3_1/), [benchmark_test2/](./experiments/high_temperature_hea_qwen35b/benchmark_test2/README.md), [benchmark_test3/](./experiments/high_temperature_hea_qwen35b/benchmark_test3/README.md), [benchmark_test4/](./experiments/high_temperature_hea_qwen35b/benchmark_test4/README.md), [benchmark_v4_scimon/](./experiments/high_temperature_hea_qwen35b/benchmark_v4_scimon/README.md) |
| Clean rerun of the suite (experiment 21) | [rerun_v3/](./experiments/high_temperature_hea_qwen35b/rerun_v3/README.md) |
| Harness runs on v3.1 (experiments 24–29, 34–35) | [loop/](./experiments/high_temperature_hea_qwen35b/loop/README.md) |
| Harness runs on v4 (experiments 31–32) | [loop_v4_scimon/](./experiments/high_temperature_hea_qwen35b/loop_v4_scimon/README.md) |
| Suite on v4 (experiment 32) | [rerun_v4_scimon/](./experiments/high_temperature_hea_qwen35b/rerun_v4_scimon/README.md) |
| Measurement checks, probe, review-suggested methods (experiments 33–35) | [review_eval/](./experiments/high_temperature_hea_qwen35b/review_eval/README.md) |
| Web-search corpora (experiment 36) | [websearch/](./experiments/high_temperature_hea_qwen35b/websearch/README.md) |
| Harness and suite with web search (experiment 36) | [loop_web/](./experiments/high_temperature_hea_qwen35b/loop_web/README.md), [rerun_web/](./experiments/high_temperature_hea_qwen35b/rerun_web/README.md) |
| Expert package; answer key and analysis | [expert_evaluation/](./expert_evaluation/README.md); [expert_eval/](./experiments/high_temperature_hea_qwen35b/expert_eval/README.md) |
| Main code | `hypo_loop.py` (harness), `loop_methods.py`, `must_obey_check.py`, `query_builder_v3.py`, `query_builder_v3_1.py`, `query_builder_v4_scimon.py`, `citegraph.py`, `rubric_eval.py`, `improvement_eval.py`, `v4_scimon_analysis.py`, `v4_all_analysis.py`, `review_measurement.py`, `checklist_judge.py`, `review_probe.py`, `review_analysis.py`, `expert_eval_analysis.py`, `websearch.py`, `web_analysis.py` |
