# Related work: LLM hypothesis generation for materials science

This is the survey table supplied on 2026-10-23, restructured. Citation counts, grades and GitHub stars are as
recorded in that table. Each entry ends with how it relates to the experiments in
[EXPERIMENT_LOG_2026-10-22.md](./EXPERIMENT_LOG_2026-10-22.md).

## Overview

| # | Work | Venue, year | Grade | Citations | Code (stars) | Generator input | Ground truth / evaluation | Paper |
|---|---|---|---|---:|---|---|---|---|
| 1 | ACCELMAT: goal-driven, constraint-guided LLM agents | NAACL Findings 2025 | A | 40 | [yes](https://github.com/shri071/Hypothesis-Generation-for-Materials-Discovery-and-Design-Using-Goal-Driven-and-Constraint-Guided-LLM) (3) | Goal statement + constraints (expert-extracted), optional MatKG context | Paper's materials + methods; closeness (3 criteria) and quality (6 criteria), 1–5 | [link](https://aclanthology.org/2025.findings-naacl.420.pdf) |
| 2 | SCIMON: Scientific Inspiration Machines Optimized for Novelty | ACL 2024 | A* | 263 | [yes](https://github.com/EagleW/Scientific-Inspiration-Machines-Optimized-for-Novelty) (98) | Background sentences + seed term + retrieved inspirations (semantic, KG, citation neighbours) | Target sentences and terms from the same abstract; novelty against a reference corpus | [link](https://aclanthology.org/2024.acl-long.18.pdf) |
| 3 | Predicting new research directions in materials science with LLMs and concept graphs | Nature Machine Intelligence 2026 | – | 11 | [yes](https://github.com/aimat-lab/materials_concepts) (30) | Time-dependent concept graph from 221k abstracts | Future concept links (AUC 0.943), expert review | [link](https://www.nature.com/articles/s42256-026-01206-y) |
| 4 | Toward Auditable AI Scientists: a Hypothesis Evolution Protocol (HEP) | preprint 2026 | – | – | – | Task + tool evidence + hypothesis registry | Process metrics on 3 tasks (belief updates, lifecycle) | [link](https://arxiv.org/pdf/2607.09195) |
| 5 | ResearchBench: inspiration-based task decomposition | ACL Findings 2026 | A* | 65 | [yes](https://github.com/ankitala/ResearchBench) | Research question + background survey (+ inspirations) | Inspiration retrieval hit ratio; hypothesis coverage 0–5; pairwise ranking in both orders | [link](https://aclanthology.org/2026.findings-acl.644.pdf) |
| 6 | PriM: principle-inspired material discovery via multi-agent collaboration | ICLR 2025 workshop (AI4Mat) | – | – | [yes](https://github.com/amair-lab/PriM) | Literature principles + virtual-lab results | Exploration rate and property value against BO, DQN and MAS baselines | [link](https://arxiv.org/abs/2504.08810) |
| 7 | Beyond Designer's Knowledge: materials design hypotheses via an LLM | Acta Materialia 2025 | – | – | – | Literature knowledge in the LLM + design goal | – | [link](https://doi.org/10.1016/j.actamat.2025.121307) |
| 8 | TopoMAS: LLM-driven topological-materials multi-agent system | Materials Genome Engineering Advances 2026 | – | – | – | Natural-language query + literature/database + self-updating TopoKG | Task benchmark; DFT-confirmed new phase (SrSbO₃) | [link](https://onlinelibrary.wiley.com/doi/10.1002/mgea.70045) |
| 9 | MatKG: an autonomously generated materials knowledge graph | Scientific Data 2024 | – | – | [yes](https://github.com/olivettigroup/MatKG) (37) | Resource, not a generator | Manual check of predicted links (47% direct, 29% broad) | [link](https://www.nature.com/articles/s41597-024-03039-z) |

## Details

### 1. ACCELMAT and the MatDesign dataset (NAACL Findings 2025)

- **Method.**
  - A Hypotheses Generation Agent (GPT-4o) proposes 20 hypotheses from a goal statement and constraints.
  - Three critics (GPT-4o, Claude-3.5-Sonnet, Gemini-1.5-Flash) review them.
  - A Summarizer (GPT-4o) merges the feedback, and generation repeats until the critics agree.
  - An Evaluation Agent (o1-preview) scores the result.
  - In the KG setting, keywords from the inputs retrieve related materials and properties from MatKG.
- **Dataset.** MatDesign: 50 papers from January 2024 onward (Nature, Nature Communications, Progress in Organic
  Coatings), built with materials-science experts. Goal statement and constraints are the input; materials
  (compositions) and methods (synthesis) are the ground truth. Extraction was manual and structured. The materials
  and methods are never given to the generator.
- **Metrics.**
  - Closeness (1–5 each): concept overlap, property overlap, keyword matching.
  - Quality (expert-defined): alignment with goal and constraints, plausibility, novelty, testability,
    feasibility and scalability, impact.
- **Limits.** 50 papers. Agreement among LLM critics does not guarantee scientific accuracy.
- **Relation to our work.**
  - Closest to our setup. Our critique experiment (11) and MatKG experiment (9) follow its design.
  - Its key difference from our benchmark is the input: only goal and constraints, extracted by people, with the
    answer kept apart. Our expert_context queries break exactly this separation (experiment 19).
  - Its keyword-matching closeness would also reward a leaking query.

### 2. SCIMON (ACL 2024)

- **Method.**
  - Retrieves inspirations three ways: semantic neighbours (related problems in the training set and their
    ideas), KG neighbours (a background KG of tasks, methods, materials and metrics from papers before year Y),
    and citation neighbours (titles cited by the source paper before year Y, ranked by SentenceBERT similarity).
  - GPT-3.5 or GPT-4 generates the idea, zero-shot, few-shot or with retrieved examples.
  - Iterative novelty boosting: retrieve the 20 nearest ideas in the literature, give those above cosine 0.6 as
    negatives, and repeat until none pass.
- **Dataset.**
  - 67,408 ACL Anthology papers from S2ORC.
  - The abstract is split by sentence classification. Background sentences become the input (problem and
    motivation); Method and Objective sentences become targets.
  - A scientific IE system extracts seed and target terms. Target information is removed at evaluation.
  - Temporal split: before 2021 for training, 2021 for development, 2022 for testing.
- **Limits.** Earlier literature-based discovery reduced hypotheses to links between concept pairs; SCIMON
  generates free-text ideas and optimises for novelty.
- **Relation to our work.**
  - The input/target split is done by sentence role, and the generator never sees target sentences. That is the
    separation our case builder lacked: it saw result roles while writing queries.
  - Its citation-neighbour retrieval is the same idea as our experiment 17. Note that the paper calls access to
    the source paper's citations a "stronger assumption", because it uses knowledge of what the target paper read.
    Our graph avoids that by starting from the query.
- **Tried here (experiment 31, loop.md section 14).** We built SCIMON's input for our 36 papers: abstract Background
  sentences, a task-side seed and its template (benchmark v4).
  - Only 9 papers give a clean input. Many alloy abstracts have no background sentence, and the seed often names
    the study design.
  - Scores did not improve, and the input drops the operating conditions. v3.1 stays the main input.

### 3. Concept graphs for new research directions in materials science (Nature Machine Intelligence 2026)

- **Method.**
  - A fine-tuned LLaMA-2-13B extracts concepts from 221k materials-science abstracts (1955–2022).
  - The result is a time-dependent concept graph: 137k nodes and 13M edges.
  - Link prediction combines graph topology with MatSciBERT embeddings to predict combinations not yet studied.
  - The predictions become personalised research suggestions.
- **Data.** Built from OpenAlex. 200 hand-annotated abstracts were used for the extractor.
- **Results.** AUC 0.943, against a 0.911 baseline. For distant links, recall is 35.3% against 5.9%.
- **Limits.**
  - Short-distance links dominate (94.5%).
  - Only 10 experts evaluated the suggestions.
  - The predicted links are directions, not tested hypotheses.
- **Relation to our work.** A temporal concept graph is a cleaner use of MatKG-style co-occurrence than raw facts
  (experiment 9). Its strict year split matches our cutoff design.

### 4. Hypothesis Evolution Protocol, HEP (preprint 2026)

- **Method.**
  - A persistent hypothesis registry. Each hypothesis has an ID, belief P(H), lifecycle state, provenance,
    predicted observable and an append-only history.
  - Hypotheses are created de novo, inspired by others, refined or merged.
  - Belief changes only through validated evidence: supported when P(H) ≥ 0.8, refuted when P(H) ≤ 0.2.
- **Evaluation.**
  - Three open-ended tasks: AO₂ polymorphs, A₂BB′O₆ B-site ordering and MX structures, with tools for MLIP,
    molecular dynamics and databases.
  - Process metrics, plus prediction for unseen compositions.
- **Limits.**
  - Beliefs are self-reported.
  - The same agent validates its own evidence.
  - Three runs per condition.
- **Relation to our work.** This is an audit trail for revisions such as our critique loop (experiment 11). Our
  failure analyses had to reconstruct why a hypothesis changed; a registry would record it.

### 5. ResearchBench (ACL Findings 2026)

- **Method.** Discovery is split into three steps:
  - Inspiration retrieval: about 75 candidates, with negatives that are citation or semantic neighbours, from the
    same discipline, or from other disciplines.
  - Hypothesis composition from background plus the true inspirations.
  - Hypothesis ranking: the true hypothesis against 15 negatives, pairwise, in both orders.
- **Data.**
  - 1,369 papers, mostly from 2024 onward, across 12 disciplines including materials science.
  - An LLM agent with self-refinement extracts the question, background, inspirations and hypothesis.
  - Inspirations are cited works that were checked to be necessary and sufficient.
  - Expert validation: 91.9% accuracy on major issues.
- **Metrics.** Hit ratio at 20% and 4% retention; coverage of the true hypothesis on a 0–5 scale; pairwise ranking
  accuracy.
- **Limits.**
  - It scores reconstruction of known hypotheses, not truth.
  - It assumes hypothesis = f(background, inspirations).
  - Models retrieve close papers more readily than distant ones.
- **Relation to our work.**
  - Its decomposition would have separated our failures: did the graph or corpus contain the inspiration, and did
    the model use it?
  - Ranking in both orders fixes the position bias of our ensemble selector (experiment 16).
  - Its extraction is expert-validated; ours never was.

### 6. PriM (ICLR 2025 AI4Mat workshop)

- **Method.** A multi-agent loop:
  - A literature agent gathers knowledge.
  - A hypothesis agent uses chain-of-principles prompting, constrained by symmetry, thermodynamics and synthesis.
  - An experiment agent runs a surrogate "virtual lab".
  - An optimizer runs Monte Carlo tree search.
  - An analysis agent maps the results back to mechanisms.
- **Data.** A private nano-helix case study.
- **Metrics.** Exploration rate and g-factor, against BO, DQN and MAS baselines.
- **Limits.** One private case, and a surrogate in place of real experiments.
- **Relation to our work.** It uses principle constraints instead of retrieved evidence. That matches our finding
  that mechanisms from the model's own reasoning do best (experiments 15–18).

### 7. Beyond Designer's Knowledge (Acta Materialia 2025)

- **Method.** An LLM prompted or tuned with materials literature proposes design hypotheses beyond a single
  designer's knowledge, aimed at property goals.
- **Relation to our work.** A design-goal input like our broad queries. It is a published materials-design
  baseline in the same journal family as our corpus.

### 8. TopoMAS (Materials Genome Engineering Advances 2026)

- **Method.**
  - A human-in-the-loop hierarchical multi-agent system: query understanding, retrieval from the literature and
    databases via a self-refining TopoKG, crystal-structure generation, and DFT validation.
  - Validated results feed back into the KG.
- **Results.**
  - Qwen2.5-72B matches or beats larger models.
  - A new topological phase, SrSbO₃, was found and confirmed by DFT.
- **Limits.** Not autonomous; DFT cost; one subdomain.
- **Relation to our work.** It verifies hypotheses with computation, which we cannot do for high-temperature HEA
  mechanical properties. Its self-updating KG corresponds to our pre-cutoff graph, without the temporal
  restriction.

### 9. MatKG (Scientific Data 2024)

- **Method.**
  - MatBERT entity extraction from about 4–5M papers, with relations from statistical co-occurrence.
  - Reported sizes vary by version: about 70k entities and 5.4M triples (final), 80k and 2M+ (2022), 150k and
    3.5M (code base).
  - KG embeddings are used for link prediction.
- **Evaluation.** 47% of predicted links judged directly relevant and 29% broadly plausible.
- **Limits.** Co-occurrence is not a verified relation, and the schema is pseudo-ontological.
- **Relation to our work.**
  - Used in experiment 9, filtered by year through `ENTPTNERDOI.csv`.
  - Its co-occurrence file has no DOI or year, so it cannot be date-filtered. That is why only the per-DOI table
    was used.

## How each work separates input from answer, compared with our benchmark

| Work | Who writes the input | What the input may contain | What is held out | Leakage control |
|---|---|---|---|---|
| ACCELMAT / MatDesign | Experts, by hand | Goal statement, constraints | Materials (compositions), methods (synthesis) | Manual separation; papers after the model cutoff |
| SCIMON | Sentence classifier + IE | Background sentences, seed term | Method and Objective sentences, target term | Separation by sentence role; temporal split; citation neighbours only before year Y |
| ResearchBench | LLM agent with self-refinement, expert-validated | Research question, background survey | Hypothesis (and inspirations for retrieval) | Recent papers; necessary and sufficient checks; 91.9% expert-validated |
| **Ours (experiments 3–18)** | **Qwen, the generator under test, in one call** | **Problem roles, plus result roles and result evidence given to the same call** | **Intervention, mediator, mechanism, outcome, values** | **Prompt instruction plus a title/DOI string check only; 47% of answer words in expert queries (experiment 19)** |

**Lessons for rebuilding the queries.**

1. **Separate by role before writing** (SCIMON, ACCELMAT). The query writer receives only problem_motivation,
   prior_limitation and constraint content, never result roles or result evidence. The target is built in a
   separate call.
2. **Fix the input form** (ACCELMAT). Use a goal statement plus constraints. Levels add context (baseline alloy,
   failure mode, regime, earlier attempts), never the type of intervention or the mechanism.
3. **Validate with people** (MatDesign, ResearchBench). Have the materials expert review the 36 queries and
   targets, as MatDesign and ResearchBench do (91.9% validated).
4. **Score retrieval separately** (ResearchBench). Measure whether the evidence pool (corpus or citation graph)
   contains the target's actual inspirations, which are its cited pre-cutoff works, before scoring generation.
   That separates the evidence ceiling from use, the main open question in experiments 15 and 18.
5. **Rank in both orders** (ResearchBench) for any selector or pairwise judge, to remove position bias.
6. **Report a target-free quality score** (ACCELMAT quality criteria). It is not affected by query leakage, and it
   lets runs on queries without a single correct answer still be scored.

## How each benchmark builds its evaluation inputs (checked 2026-10-23 against the papers and repositories)

| Work | Input written by | Source of the input | Answer kept out by | Contamination control | Gaps found |
|---|---|---|---|---|---|
| MatDesign / ACCELMAT | Materials experts, by hand (no script) | Whole paper | Nothing formal | Papers from January 2024; models with late-2023 cutoffs | Several rows leak the answer: row 40's constraint says "must be cerium-based (cerium nitrate, cerium oxide)", the exact ground-truth material; row 26's goal statement names the answer's composite. The paper never discusses this. |
| SCIMON | Sentence classifier and IE system | Abstract only: Background sentences are input, Method/Objective sentences are target | Similarity filter (background–target cosine ≤ 10th percentile) plus manual check, only on the 194-item gold subset | Temporal split (train < 2021, test 2022); background KG and citation neighbours restricted to before year Y | Seed terms come from the target side; only about 16% appear in the background |
| MOOSE-Chem | 3 chemistry PhD students | Paper | Written guideline: "Background survey shouldn't contain any information/method in inspiration or hypothesis… Background question cannot contain any information in inspiration or hypothesis"; a "strict" variant removes directional hints | 51 papers from 2024; GPT-4o (Oct 2023 cutoff) | — (the clearest positive example) |
| ResearchBench | LLM agent with self-refinement | Introduction and related work | Only an undocumented prompt phrase ("without referencing specific inspirations or conclusions") | Papers from 2024, plus a post-July-2024 subset | The expert checklist (91.9% accuracy) does not ask about leakage |
| IdeaBench | Rule | Abstracts of the target's background-cited references only; the target paper is never shown | By construction; the ground truth is a GPT-4o paraphrase without results or numbers | 2024 papers; models with pre-2024 cutoffs | — |
| Concept-graph link prediction | Fine-tuned LLaMA-2 concept extraction | 221k OpenAlex abstracts | Temporal split: train edges 2017–2019, test 2020–2022; embeddings computed only from text before the cutoff year | Feature gating only | No check of LLM pretraining contamination |
| Beyond Designer's Knowledge | Authors | Author-written design problems; literature retrieved only before the gpt-4-1106 cutoff (April 2023) | Flagship ideas published after the cutoff | Explicit | Admits that other ideas may reflect references in the training data |
| HEP, PriM, TopoMAS | Authors (HEP, PriM); not stated (TopoMAS) | Task statements | Ground truth from tools or simulators, not from the literature | None discussed | No leakage discussion |

**Rules adopted for benchmark v3** ([benchmark_v3/README.md](./benchmark_v3/README.md)):

1. Introduction-only source with the paper's own contribution removed (ResearchBench source, SCIMON split).
2. The writer never sees the answer, and MOOSE-Chem's background/question rule is applied.
3. A separate checker with the answer lists leaking phrases and steering (MOOSE-Chem guideline, automated).
4. A lexical gate on every query, not only a gold subset (SCIMON's filter, applied to all).
5. Failed levels are rewritten or flagged, never silently kept (MatDesign's failure mode).
6. The generator's training cutoff precedes every held-out paper (all benchmarks), and a memorisation probe checks
   it (a gap in all of them).
