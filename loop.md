# loop.md: iterative method development on leak-free queries

Started 2026-10-25. Everything here follows [must_obey.md](./must_obey.md). Every run is checked by
`must_obey_check.py --loop`, and every number below is on the **dev split** (8 papers × 3 levels = 24 units, 2 samples
each) unless a section says *test*. The test split (4 papers) is touched only by the pre-registered final runs of
section 6, reported in section 7. Section 8 summarises what made a difference and why.

Round 2 is section 10: a failure analysis of the round-1 best, iterations 6–8, and a fresh held-out set (test2,
12 papers) with its pre-registered results. Its summary is section 10.7. **On fresh papers the best-supported
configuration is o3-mini with the conservative writer (one call per hypothesis).**

Round 3 is section 11: a 24-paper development set, writer-level methods, and a third fresh set (test3). Its
summary is section 11.8. **No further increase was found.** The round-3 dev winner failed on test3. Over all 28
fresh held-out papers the same one-call configuration scores 0.60 against 0.49 for the Llama baseline (GPT-5.6,
sign p = 0.009).

Section 12 (experiment 29) varies one input at a time. **Adding research papers as context lowers the score.** One
to three paper summaries cost 0.10 (GPT-5.6) and 0.24 (DeepSeek), replicated on test3. Thirty papers return toward
the no-paper level without exceeding it. Raw text, relevance, reasoning effort and question detail have no
significant effect.

**Code.**
- [hypo_loop.py](./hypo_loop.py): the harness, with rule enforcement, logging and evaluation.
- [loop_methods.py](./loop_methods.py): the methods.
- [loop_analysis.py](./loop_analysis.py): decision diagnostics (section 5).
- [loop_final.py](./loop_final.py): the pre-registered test analysis and the style checks (section 7).
- [test_hypo_loop.py](./test_hypo_loop.py): tests.
- [failure_clean.py](./failure_clean.py): the failure analysis.
- [query_builder_v3_1.py](./query_builder_v3_1.py): the benchmark fix.

**Outputs.** `experiments/high_temperature_hea_qwen35b/loop/<method>/` holds `runs/`, `judgments/{gpt56,deepseek}/`,
`audit/` and `labels/`. The reports are `report_dev.md`, `report_test.md` and `report_all.md`. The pre-registered
analysis is `final_{dev,test,all}.json`, and the style checks and per-paper scores are `final_robustness.json`.

---

## 0. Setup

| Item | Setting |
|---|---|
| Queries | benchmark v3.1 (iteration 0 below), frozen |
| Generator | Llama-3.3-70B-Instruct (cutoff December 2023) unless a method says otherwise; temperature 0.2 |
| Other cleared generators | o3-mini, gpt-4o-mini (cutoff 2023-10-01) after the memorisation probe below |
| Evidence | the same temporally filtered pools as the baselines (raw text chunks, rubric cards), 16,000-character budget |
| Judges | GPT-5.6 reconstruction (mean of intervention, condition, mechanism, outcome; 0–4); DeepSeek-V4-Pro cross-judge |
| Analysis labels | GPT-5.6 target-free audit; GPT-5.6 lever label (0 different kind … 3 the target's intervention). Analysis only, never shown to a method |
| Statistics | paired per unit against a baseline; paper-clustered bootstrap 95% CI; sign test over papers; Holm across methods |

**Memorisation probe** (must_obey.md 2.3; title and year only; GPT-5.6 scores the recall; 12 papers × 2 samples):

| Model | Claims to remember | Recall beyond the title on any dimension | Notes |
|---|---:|---:|---|
| Qwen3.5-35B-A3B (post-cutoff, old generator) | 0% | **33%** | forbidden |
| Llama-3.3-70B (control) | 0% | 8% | allowed |
| o3-mini | 0% | 17% | allowed: all 4 hits are inferences from titles that name the method (SRO; mechanical alloying + SPS), and Llama scores the same on the SRO paper |
| gpt-4o-mini | 0% | 0% | allowed |

---

## 1. Failure analysis before any method (experiment 22)

[failure_clean.py](./failure_clean.py) covers all 1,476 judged hypotheses of the clean rerun (experiment 21: 26 arms,
benchmark v3, Llama-3.3). Results are in `experiments/high_temperature_hea_qwen35b/rerun_v3/failure/analysis.json`.

| Finding | Number | What it implies |
|---|---|---|
| **F1** Generators propose the wrong *kind* of intervention | intervention 0.16/4. Lever match: 79% a different kind, 15% the same kind but a different lever, 6% the same lever, 0% the target | Need better choice of solution family |
| **F1b** Strong default to composition changes | e.g. CoCrFeNiTi (target: ball milling + SPS): 36 of 41 hypotheses proposed alloying additions although the question cites casting porosity | The cues in the question are ignored; make the choice explicit and cue-based |
| **F2** Question type does not fit the target for 4 of 12 cases (simulation or characterization studies asked as "which intervention") | 0% of hypotheses in the right class for those cases | Construction error, fixed by benchmark v3.1 (iteration 0) |
| **F3** Right kind, wrong lever | 15% | Coarse-to-fine search inside the chosen family |
| **F4** Coverage, not selection, is the bottleneck | pass@1 0.06, pass@5 0.16, pass@10 0.21; 25 of 36 units have no lever hit among 41 hypotheses; best-of-41 reconstruction 1.0 vs mean 0.47 | A better selector alone cannot help; generate in the right family first |
| **F5** Evidence distracts | problem alignment: closed-book 2.79, evidence arms 2.04–2.40 | Retrieve after the decision, aimed at the chosen lever |
| **F6** Vague or untestable claims | 25% of 1,495 coded fatal errors; evidence-unsupported 22%, wrong intervention 20% | Deterministic checks for numbers, thresholds and baselines |
| **F7** Judges disagree | GPT-5.6 vs DeepSeek ρ = 0.39 (hypothesis level); DeepSeek is harsher (0.23 vs 0.48) | Report both; treat small differences as noise |
| **F8** Extra context is unused | broad 0.45, problem 0.48, expert 0.48 | Frame the question explicitly (limitation, constraints, earlier attempts) |

---

## 2. What I read, what I understood, what I integrated

I read sources H1–H4 and the arXiv records myself. A research sub-agent fetched sources A–C, and I checked the
load-bearing claims against arXiv (authors and dates verified through the arXiv API). One correction: the first
author of Step-Back prompting is Huaixiu Steven Zheng, not Swaroop Mishra, who submitted it.

### Harness and loop engineering

| ID | Source | What I understood | What we integrate (where) |
|---|---|---|---|
| H1 | **Harness engineering: leveraging Codex in an agent-first world**, Ryan Lopopolo, OpenAI, Feb 2026. https://openai.com/index/harness-engineering/ (page returns 403; read through the full-article summary at https://businessdatasolutions.github.io/ai-wiki/sources/2026-02-11-lopopolo-codex-harness-engineering) | "Humans steer, agents execute." The repository is the system of record. AGENTS.md is a short table of contents, not an encyclopedia. Rules are enforced mechanically (linters, structural tests), and every agent failure becomes a harness fix. | [AGENTS.md](./AGENTS.md) and `.github/copilot-instructions.md` point to [must_obey.md](./must_obey.md) (progressive disclosure). Rules are enforced in code: [must_obey_check.py](./must_obey_check.py) and `Harness.guard`. Failures become harness rules, e.g. the truncation retry in `Harness.ask`. |
| H2 | **Agent harness engineering**, Addy Osmani, 2026. https://addyosmani.com/blog/agent-harness-engineering/ | Agent = model + harness. "A decent model with a great harness beats a great model with a bad harness." The ratchet: every observed mistake becomes a permanent rule. Derive each harness component from a behaviour; split planner from executor. | The whole design starts from a weak pre-cutoff model plus a strong harness. Every component in [loop_methods.py](./loop_methods.py) is tied to a finding F1–F8. |
| H3 | **Loop engineering**, Addy Osmani, June 2026 (O'Reilly Radar repost). https://www.oreilly.com/radar/loop-engineering/ | You stop prompting; you design the loop that prompts. It has five pieces (automations, worktrees, skills, connectors, maker/checker subagents) plus memory on disk ("the agent forgets; the repo doesn't"). `/goal` is checked by a separate model, so the writer is not the grader. | The outer loop of this document: method → evaluate → failure analysis → next method. Memory lives in loop.md and the per-run notebooks (`notes`). Maker/checker: the judges are never the generator, and the verifier is a separate call. |
| H4 | **Loop engineering explained: beyond prompt engineering**, freeacademy.ai, 2026. https://freeacademy.ai/blog/loop-engineering-beyond-prompt-engineering-ai-agents-2026 | A loop has trigger, goal, actions, verification and memory. Prefer deterministic checks over self-grading. The trajectory, not the response, is the unit. Failure modes: no progress, hallucinated success, cost blowup. Several independent exits. | Deterministic checks (`deterministic_problems`) before inferential ones. Every method has a fixed call budget and stop rule. |
| A2 | **Effective harnesses for long-running agents**, Anthropic, Nov 2025. https://www.anthropic.com/research/effective-harnesses-for-long-running-agents | Initializer and continuation agents; a JSON feature list whose items can only be flipped to `passes`; progress files; end-to-end verification. | The JSON notebook per run (frame, families, decision, verification) is typed state, not chat history. |
| A3 | **Harness design for long-running apps**, Anthropic, Mar 2026. https://www.anthropic.com/research/harness-design-long-running-apps | Separating generator and evaluator fixes self-evaluation leniency. Named rubric axes with hard per-criterion thresholds. | Verifier separate from writer (L4). Independent per-criterion scoring (iteration 2). |
| A4 | **Harness engineering**, Birgitta Böckeler, martinfowler.com, Feb and Apr 2026. https://martinfowler.com/articles/harness-engineering.html | Guides (feedforward) vs sensors (feedback). Computational (cheap, deterministic) vs inferential (LLM) checks; run the cheap ones first. The "behaviour harness" for semantic correctness is the least solved. | Computational sensors first: lexical gate, deterministic hypothesis checks, leakage counters. LLM verifiers come after. |
| A5 | **My AI adoption journey**, Mitchell Hashimoto, 2026. https://mitchellh.com/writing/my-ai-adoption-journey | Engineer every mistake away. Newer models are post-trained to use tools; older ones are not. | Llama-3.3 made 2.1 tool calls per run in experiment 21, so retrieval is a code step, not a tool the model may choose (L3, L7). |
| A6 | **The anatomy of an agent harness**, LangChain, Mar 2026. https://www.langchain.com/blog/the-anatomy-of-an-agent-harness | "If you're not the model, you're the harness." A harness change alone moved an agent from Top-30 to Top-5 on Terminal-Bench 2.0. | Motivates keeping the model fixed and changing only the harness (iterations 1–2) before changing the model (iteration 3). |
| B1 | **Ralph Wiggum as a "software engineer"**, Geoffrey Huntley, Jul 2025. https://ghuntley.com/ralph/ | A loop with no in-process memory: state lives in files, and backpressure from checks rejects bad generations. | Each iteration restarts from frozen files and loop.md. Checks are backpressure. |
| B3 | **12-Factor Agents**, HumanLayer (Dex Horthy). https://github.com/humanlayer/12-factor-agents | Own your control flow and your context window; the LLM fills steps and deterministic code dispatches. | All methods are code-controlled workflows: the harness decides the steps and the model fills them. |
| B4 | **Building effective agents**, Erik Schluntz and Barry Zhang, Anthropic, Dec 2024. https://www.anthropic.com/engineering/building-effective-agents | Workflows (prompt chaining, routing, parallelization by sectioning or voting, orchestrator-workers, evaluator-optimizer) vs agents. Add complexity only when it measurably helps; evaluator-optimizer needs clear criteria. | L1 = chaining + routing (gap → family). L2 = parallelization by family + voting. L4 = evaluator-optimizer with explicit criteria. Each is compared against simpler baselines. |
| B5 | **Effective context engineering for AI agents**, Anthropic, Sep 2025. https://www.anthropic.com/research/effective-context-engineering-for-ai-agents | Context rot; structured note-taking; sub-agents with clean context; just-in-time retrieval. | L2 candidates are written in separate clean contexts. L7 retrieves just in time, for the chosen lever only. |
| B6 | **How we built our multi-agent research system**, Anthropic, Jun 2025. https://www.anthropic.com/research/multi-agent-research-system | Orchestrator-workers with explicit subtask specs (objective, format, boundary); a single rubric judge. | Every candidate writer gets an explicit spec (family, lever, principle). |
| B8 | **Context engineering for agents**, LangChain, Jul 2025. https://www.langchain.com/blog/context-engineering-for-agents | Write, select, compress, isolate; context poisoning and distraction. | Analysis notes are passed instead of raw history. The verifier is isolated from the generator's reasoning. |
| B9, B10 | **Don't build multi-agents** (Jun 2025) and **Multi-agents: what's actually working** (Apr 2026), Walden Yan, Cognition. https://cognition.com/blog/dont-build-multi-agents , https://cognition.com/blog/multi-agents-working | Keep writes single-threaded. Review works better when the reviewer does not share the generator's context. | The final hypothesis is written by one call. The L4 verifier sees only the question and the draft. |
| B11 | **AI loop engineering**, Ben Dickson, bdtechtalks, Jun 2026. https://bdtechtalks.com/2026/06/22/ai-loop-engineering/ | Provenance: the term was named by Osmani, synthesising Steinberger and Cherny. | Umbrella term only. |

### Hypothesis generation, selection and retrieval

| ID | Source | What I understood | What we integrate (where) |
|---|---|---|---|
| C1 | **Towards an AI co-scientist** (v2: Accelerating scientific discovery with Co-Scientist), Juraj Gottweis et al., Google, Feb 2025. https://arxiv.org/abs/2502.18864 | Generation, reflection, an Elo tournament (with debate for top pairs, to reduce ordering bias), evolution and meta-review. | L2: candidates from different families compete in a round-robin. Each pair is judged in both orders, and a win counts only if both orders agree. |
| C2 | **MOOSE-Chem**, Zonglin Yang et al., ICLR 2025. https://arxiv.org/abs/2410.07076 | Hypothesis = background + inspirations; inspirations are retrieved and screened; validated by rediscovering post-cutoff papers (our setting). | L3: precedents from earlier papers (problem → lever → outcome) act as inspirations that inform the family choice. |
| C3 | **MOOSE-Chem2**, Zonglin Yang et al., NeurIPS 2025. https://arxiv.org/abs/2505.19209 | Coarse-to-fine hierarchical search from direction to lab-actionable details. Each pair is compared six times with alternating order to remove position bias. | L1 locks the coarse family first. Iteration 2 adds fine lever search inside the family. Pairwise judgments are order-controlled. |
| C4 | **SciMON**, Qingyun Wang, Doug Downey, Heng Ji, Tom Hope, ACL 2024. https://arxiv.org/abs/2305.14259 | Retrieval of semantic, KG and citation neighbours as inspirations; an iterative novelty-boosting loop. | L3 uses semantic neighbours from earlier papers. Novelty boosting is deliberately not used: this benchmark rewards reconstruction, and novelty is reported separately. |
| C5 | **ResearchAgent**, Jinheon Baek et al., NAACL 2025. https://arxiv.org/abs/2404.07738 | Reviewing agents with narrow criteria; gains saturate after about 3 refinement rounds; retrieval is a mandatory pipeline stage. | Iteration 2: narrow-criterion, independent scoring. Retrieval is always a code step. |
| C6 | **Chain of Ideas**, Long Li et al., EMNLP 2025 Findings. https://arxiv.org/abs/2410.13185 | Organise literature as a chronological chain, state the trend and predict the next step; removing the chain was the largest ablation loss. | Iteration 2 `trend_chain`: a chronological chain of earlier papers on the same problem → trend → predicted next step. |
| C7 | **Large Language Monkeys**, Bradley Brown et al., 2024. https://arxiv.org/abs/2407.21787 | Coverage (any of k correct) and selection are decoupled; coverage grows with k, while selection plateaus. | Diagnostic in section 1 (pass@k): coverage is our bottleneck (F4). |
| C8 | **Universal Self-Consistency**, Xinyun Chen et al., 2023. https://arxiv.org/abs/2311.17311 | An LLM picks the most consistent of k free-form answers; position bias remains open. | Not used as a selector, because majority voting would amplify the composition default (F1b). |
| C9 | **Take a step back: evoking reasoning via abstraction**, Huaixiu Steven Zheng et al., ICLR 2024. https://arxiv.org/abs/2310.06117 | Abstract to principles first, then reason; works for Llama-2-70B too. | L1 framing: governing principle and solution families before any specifics. L7 uses the abstraction as the retrieval query. |
| C10 | **Large language models as analogical reasoners**, Michihiro Yasunaga et al., ICLR 2024. https://arxiv.org/abs/2310.01714 | Self-generated exemplars help strong models; weaker models do better with retrieved exemplars. | L3 uses retrieved real precedents, not self-generated ones, because Llama is the weaker model. |
| C11 | **HyDE: precise zero-shot dense retrieval without relevance labels**, Luyu Gao et al., ACL 2023. https://arxiv.org/abs/2212.10496 | Retrieve with a hypothetical answer instead of the bare question. | L7: the grounding query is built from the chosen family, lever and principle (written from the query only, by the pre-cutoff model). |
| C12 | **Approaching human-level forecasting with language models**, Danny Halawi et al., 2024. https://arxiv.org/abs/2402.18563 | Retrieval, base-rate reasoning, then aggregation; a trimmed mean beat an LLM-judge selector. The temporal split matches ours. | Forecasting framing in the tournament judge ("what would a competent group most plausibly pursue and succeed with"). Iteration 2 uses trimmed-mean aggregation of independent scores. |

Benchmark-construction sources (MatDesign, SciMON, MOOSE-Chem, ResearchBench, IdeaBench) are in
[RELATED_WORK.md](./experiments/high_temperature_hea_qwen35b/RELATED_WORK.md). Model cutoff sources are in
[must_obey.md](./must_obey.md) section 2.

---

## 3. Baselines on dev (benchmark v3.1, Llama-3.3-70B, 2 samples)

The same code path as experiment 21 (`generate_with_citation_repair`), re-run on v3.1 inside the harness.

| Baseline | GPT-5.6 | DeepSeek | core GPT | intervention | condition | mechanism | outcome |
|---|---:|---:|---:|---:|---:|---:|---:|
| `closed_book` | 0.51 | 0.32 | 0.43 | 0.33 | 0.50 | 0.52 | 0.69 |
| `text_chunks` | 0.43 | 0.26 | 0.32 | 0.17 | 0.48 | 0.48 | 0.58 |

Every Δ in sections 5 and 7 is against `closed_book` unless stated. The test-split and all-12 baselines are in
section 7.

---

## 4. Iterations

### Iteration 0: fix the question-type construction error (benchmark v3.1)

- **Failure targeted:** F2.
- **Source:** MOOSE-Chem's background/question rules (in RELATED_WORK.md). The question must ask for the kind of
  contribution the introduction motivates, without hinting at the answer.
- **Change.** A gap classifier that sees only the redacted introduction labels each case design, understanding or
  method. Design cases keep their v3 queries. The other cases get a question template for their gap type ("which
  testable mechanism governs X, and what controlled change would reveal it" / "which method would overcome the
  limitation"), using the same writer, leakage checker, lexical gate and rewrite loop.
- **Result.**
  - 4 dev cases kept (PMC10759803, PMC11077685, PMC11087546, PMC11375712).
  - 4 dev cases rewritten (PMC11355469, PMC11775865 understanding; PMC11375216, PMC11606917 method).
  - All 4 test cases rewritten (understanding).
  - 34 of 36 levels pass the gate. PMC11606917 problem and expert levels fail it and are flagged.
  - The rule was applied blind. Two processing-route targets (PMC12298864, PMC12941549, both test) now carry
    understanding questions because their introductions state an understanding gap; this is a recorded caveat, not
    a tuned exception.

### Iteration 1: harness-controlled reasoning with a fixed weak model (Llama-3.3)

The model stays fixed (A6, H2). Each method is a code-controlled workflow (B3, B4): the harness decides the steps,
the model fills them, and every call is guarded and logged.

| Method | Failures targeted | Design (what is new here) | Sources |
|---|---|---|---|
| `writer_only` (L0, control) | none (control) | The method writer prompt alone, closed-book. It demands named parameters, quantified outcome and a numeric falsification threshold. | control for the writer prompt |
| `frame_decide` (L1) | F1, F1b, F8 | (1) A problem frame: system, goal, limitation, root-cause cues, constraints, regime, earlier attempts, gap type. (2) A family map: every family of answers for that gap type gets its governing principle, cues for and against, and a fit score 0–5 from the cues only ("alloying is not a default"). (3) **Code** picks the top family; no model discretion. (4) The writer must use the chosen family and lever. | C9 step-back; B4 chaining and routing; B3 control flow; C3 coarse first |
| `breadth_tournament` (L2) | F4 (coverage), F1 | One candidate per top-4 family, each written in a clean context. A round-robin of pairwise judgments in **both orders**; a pair point counts only if the two orders agree. The judge's criterion is a forecasting framing: what a competent group would most plausibly pursue and succeed with. | C1 co-scientist tournament; C3 order control; B5 clean contexts; C12 forecasting |
| `precedent_decide` (L3) | F1, F3 | Earlier papers' cards (temporally filtered) are read into a precedent table (problem → family → lever → outcome). The table is a prior in the family map; the question's cues still decide. | C2 MOOSE-Chem inspirations; C4 SciMON neighbours; C10 retrieved, not self-generated, exemplars for a weak model |
| `frame_decide_verify` (L4) | F6 | L1, then **computational sensors** (numbers in the outcome, a numeric threshold, a named baseline) and a separate inferential verifier that sees only the question and the draft. One repair pass. | A4 guides and sensors; A3 separate evaluator; B4 evaluator-optimizer; B10 reviewer without generator context |
| `decide_then_ground` (L7) | F5 | Decide first (L1), then retrieve raw text aimed at the chosen family, lever and principle, then write with citations. | C11 HyDE; C9 abstraction as retrieval query; B5 just-in-time retrieval; A5 retrieval as a code step |

### Iteration 2: fix the writer, then search and select inside the harness (Llama-3.3)

Lesson from iteration 1 (the ratchet, H2). The method writer's demand for quantified outcomes lowers outcome
agreement (0.69 → 0.42), because the judge penalises invented exact numbers that differ from the paper. Every
iteration-2 method therefore uses `WRITER_B`: the baseline's conservative style ("state the uncertainty instead of
inventing support or precise values") plus the notes. `writer_only_b` is its control.

| Method | Failures targeted | Design | Sources |
|---|---|---|---|
| `writer_only_b` (control) | | WRITER_B alone | |
| `frame_decide_b` | F1, F8 | L1 with WRITER_B | as L1 |
| `trend_chain` | F1, F3 | Frame → earlier papers' cards in **chronological order** → state the trend, what is unsolved, and forecast the most plausible next step (family and lever) → write | C6 Chain of Ideas; C12 forecasting |
| `coarse_to_fine` | F3 | Lock the family (L1), list 4 distinct levers inside it, then score each lever **independently**: root cause, constraints, physics, next step; 3 samples, trimmed mean. Write the best. | C3 coarse to fine; C5 narrow criteria; C12 trimmed mean; A3 per-criterion scoring |
| `family_scored` | F4, F1 | One candidate per top-4 family, selected by independent absolute scoring (trimmed mean) instead of a pairwise tournament | C12; A3; C7 (selection after coverage) |

### Iteration 3: change the model, keep the harness (pre-cutoff models only)

"A decent model with a great harness beats a great model with a bad harness" (H2). Here we measure the other axis:
o3-mini and gpt-4o-mini (both cutoff 2023-10-01, memorisation probe clean) in closed-book, writer-only-B and
frame-decide-B.

### Iteration 4: harness pieces on top of the best model, and combinations

Recursive step from iteration 3: on o3-mini the frame/decide step no longer helped, so the question becomes which
harness pieces still add value to a stronger model. Tested on o3-mini and on Llama:
- `trend_chain`: forecast from the chronological chain.
- `decide_then_ground_b`: decide, then ground the chosen lever (WRITER_B).
- `trend_ground_b`: forecast, then ground.
- `scaffold_ensemble`: one candidate each from closed-book, frame-decide and trend-chain, selected by independent
  trimmed-mean scoring (C12, A3).
- `coarse_to_fine` (o3-mini).

---

## 5. Results on dev (24 units × 2 samples; GPT-5.6 primary, DeepSeek cross-judge)

The full table, with all 10 dimensions, lever labels, hedges and novelty, is in
`experiments/high_temperature_hea_qwen35b/loop/report_dev.md`. Δ is the paired difference against the Llama-3.3
`closed_book` baseline (paper-clustered bootstrap).

| Method | GPT-5.6 | Δ vs closed_book [95% CI] | DeepSeek | Δ DeepSeek [95% CI] | core GPT | intervention | mechanism | outcome | specificity (audit) | calls/run |
|---|---:|---|---:|---|---:|---:|---:|---:|---:|---:|
| **Baselines (Llama-3.3)** | | | | | | | | | | |
| `closed_book` | 0.51 | – | 0.32 | – | 0.43 | 0.33 | 0.52 | 0.69 | 0.26 | 1.00 |
| `text_chunks` | 0.43 | -0.08 [-0.34, +0.15] | 0.26 | -0.06 [-0.23, +0.10] | 0.32 | 0.17 | 0.48 | 0.58 | 0.19 | 1.00 |
| **Iteration 1 (Llama, method writer)** | | | | | | | | | | |
| `writer_only` | 0.44 | -0.07 [-0.14, +0.01] | 0.20 | -0.12 [-0.22, -0.01] | 0.41 | 0.29 | 0.52 | 0.42 | 0.68 | 1.04 |
| `frame_decide` | 0.47 | -0.04 [-0.18, +0.09] | 0.31 | -0.01 [-0.18, +0.16] | 0.36 | 0.23 | 0.50 | 0.50 | 0.67 | 3.00 |
| `breadth_tournament` | 0.46 | -0.05 [-0.14, +0.05] | 0.30 | -0.02 [-0.08, +0.05] | 0.41 | 0.29 | 0.52 | 0.50 | 0.66 | 18.00 |
| `precedent_decide` | 0.45 | -0.06 [-0.15, +0.04] | 0.29 | -0.03 [-0.14, +0.08] | 0.35 | 0.29 | 0.42 | 0.50 | 0.64 | 4.00 |
| `frame_decide_verify` | 0.44 | -0.07 [-0.22, +0.06] | 0.27 | -0.05 [-0.19, +0.07] | 0.41 | 0.27 | 0.54 | 0.40 | 0.71 | 5.00 |
| `decide_then_ground` | 0.56 | +0.05 [-0.14, +0.20] | 0.23 | -0.09 [-0.19, +0.01] | 0.48 | 0.38 | 0.58 | 0.71 | 0.43 | 3.73 |
| **Iteration 2 (Llama, conservative writer)** | | | | | | | | | | |
| `writer_only_b` | 0.59 | +0.08 [-0.03, +0.20] | 0.35 | +0.03 [-0.09, +0.16] | 0.47 | 0.35 | 0.58 | 0.75 | 0.33 | 1.00 |
| `frame_decide_b` | 0.59 | +0.08 [-0.03, +0.17] | 0.36 | +0.04 [-0.08, +0.18] | 0.52 | 0.42 | 0.62 | 0.69 | 0.20 | 3.00 |
| `trend_chain` | 0.57 | +0.06 [-0.04, +0.16] | 0.35 | +0.03 [-0.06, +0.12] | 0.47 | 0.46 | 0.48 | 0.71 | 0.24 | 3.08 |
| `coarse_to_fine` | 0.53 | +0.02 [-0.11, +0.16] | 0.28 | -0.04 [-0.16, +0.09] | 0.40 | 0.31 | 0.48 | 0.77 | 0.37 | 16.00 |
| `family_scored` | 0.48 | -0.03 [-0.24, +0.15] | 0.29 | -0.03 [-0.14, +0.07] | 0.34 | 0.19 | 0.50 | 0.62 | 0.30 | 18.00 |
| **Iteration 3 (model swap)** | | | | | | | | | | |
| `closed_book_4omini` | 0.61 | +0.10 [-0.08, +0.26] | 0.28 | -0.04 [-0.14, +0.06] | 0.47 | 0.40 | 0.54 | 0.85 | 0.22 | 1.00 |
| `writer_only_b_4omini` | 0.52 | +0.01 [-0.18, +0.18] | 0.30 | -0.02 [-0.16, +0.11] | 0.40 | 0.31 | 0.48 | 0.75 | 0.41 | 1.00 |
| `frame_decide_b_4omini` | 0.54 | +0.03 [-0.12, +0.19] | 0.23 | -0.09 [-0.24, +0.04] | 0.38 | 0.25 | 0.50 | 0.77 | 0.24 | 3.00 |
| `closed_book_o3mini` | 0.63 | +0.12 [+0.01, +0.23] | 0.53 | +0.21 [+0.08, +0.33] | 0.47 | 0.31 | 0.62 | 0.90 | 0.37 | 1.02 |
| `writer_only_b_o3mini` | 0.67 | +0.16 [+0.05, +0.24] | 0.59 | +0.27 [+0.12, +0.45] | 0.52 | 0.33 | 0.71 | 0.92 | 0.38 | 1.00 |
| `frame_decide_b_o3mini` | 0.63 | +0.12 [+0.05, +0.20] | 0.58 | +0.27 [+0.04, +0.51] | 0.46 | 0.29 | 0.62 | 0.81 | 0.35 | 3.04 |
| **Iteration 4 (harness pieces and combinations)** | | | | | | | | | | |
| `trend_chain_o3mini` | 0.62 | +0.11 [-0.06, +0.27] | 0.60 | +0.28 [+0.03, +0.54] | 0.46 | 0.25 | 0.67 | 0.88 | 0.33 | 3.48 |
| `decide_then_ground_b_o3mini` | 0.69 | +0.18 [+0.08, +0.30] | 0.68 | +0.36 [+0.22, +0.50] | 0.54 | 0.25 | 0.83 | 0.94 | 0.38 | 3.19 |
| `trend_ground_b_o3mini` | 0.73 | +0.22 [+0.12, +0.31] | 0.64 | +0.32 [+0.11, +0.49] | 0.59 | 0.38 | 0.81 | 0.94 | 0.39 | 3.12 |
| `scaffold_ensemble_o3mini` | 0.66 | +0.15 [+0.05, +0.23] | 0.52 | +0.20 [-0.03, +0.40] | 0.53 | 0.25 | 0.81 | 0.88 | 0.33 | 16.44 |
| `coarse_to_fine_o3mini` | 0.61 | +0.10 [-0.05, +0.24] | 0.55 | +0.23 [-0.04, +0.55] | 0.43 | 0.21 | 0.65 | 0.85 | 0.56 | 16.04 |
| `decide_then_ground_b` | 0.54 | +0.03 [-0.09, +0.16] | 0.31 | -0.01 [-0.08, +0.07] | 0.48 | 0.46 | 0.50 | 0.69 | 0.12 | 3.10 |
| `trend_ground_b` | 0.51 | -0.00 [-0.19, +0.14] | 0.29 | -0.03 [-0.17, +0.10] | 0.46 | 0.35 | 0.56 | 0.65 | 0.14 | 3.12 |
| `scaffold_ensemble` | 0.61 | +0.10 [-0.01, +0.22] | 0.33 | +0.01 [-0.03, +0.05] | 0.56 | 0.40 | 0.73 | 0.79 | 0.25 | 16.02 |

### What each iteration taught (the loop)

**Iteration 1: the writer prompt dominates and the decision step helps a little.**
- `writer_only` scores 0.07 below `closed_book` (DeepSeek −0.12, CI −0.22 to −0.005). Its quantified outcomes cut
  outcome agreement from 0.69 to 0.42, because the judge penalises invented exact numbers.
- Within the same writer, `frame_decide` adds +0.03 over `writer_only`, and grounding the decided lever
  (`decide_then_ground`) adds +0.12, since evidence anchors the numbers (outcome 0.71).
- The tournament, precedents and the verifier did not help Llama:
  - the Llama tournament judge did not move coverage (same class 0.38);
  - precedents pulled in other systems' mechanisms (mechanism 0.42; the cross-system transfer failure of
    experiment 15);
  - the verifier demanded more numbers (specificity 0.71, outcome 0.40).
- **Rule added (ratchet):** a conservative writer (WRITER_B) for every later method.

**Iteration 2: with the writer fixed, a cue-based family decision adds to the core.**
- `writer_only_b` scores 0.59 (+0.08); most of the gain is outcome agreement.
- `frame_decide_b` has the best Llama core (0.52, intervention 0.42), and `trend_chain` the best Llama intervention
  (0.46).
- Lever search (`coarse_to_fine`) and independent selection across families (`family_scored`) did not help with
  Llama as scorer.

**Iteration 3: the model is the biggest single lever, and both judges agree.**
- o3-mini closed-book: +0.12 (CI 0.01 to 0.23); DeepSeek +0.21 (CI 0.08 to 0.33).
- o3-mini with the conservative writer: +0.16 (CI 0.05 to 0.25); DeepSeek +0.27 (CI 0.12 to 0.45).
- gpt-4o-mini looks good on GPT-5.6 (0.61) but not on DeepSeek (0.28, Llama level). It is not robust and was dropped.
- On o3-mini, forcing a family (`frame_decide_b_o3mini`, 0.63) is *below* the plain writer (0.67). The scaffold that
  helped the weak model constrains the stronger one (H2, C10).

**Iteration 4: on the strong model, retrieval aimed at a decided lever is what helps.**
- `trend_ground_b_o3mini`: chronological chain → forecast the next step → retrieve for that lever → conservative
  writer. GPT-5.6 0.73 (+0.22, CI 0.12 to 0.31); DeepSeek 0.64 (+0.32, CI 0.11 to 0.49); core 0.59; mechanism 0.81.
- `decide_then_ground_b_o3mini` scores 0.69 and has the best DeepSeek score (0.68, +0.37, CI 0.22 to 0.50).
- The same aimed retrieval is neutral for Llama (`trend_ground_b` 0.51, `decide_then_ground_b` 0.54). Evidence helps
  only a model that can use it, which reverses failure F5 for o3-mini.
- Ensembles: `scaffold_ensemble` is the best Llama core (0.56). On o3-mini (0.66) it beats each of its ungrounded
  parts (0.62–0.63) but not the grounded methods.
- Quality check (must_obey.md 6.8): the leader is *more* specific than the baseline in the target-free audit (0.39 vs
  0.26), with a low hedge rate and higher novelty (1.94 vs 1.06). The gain is not vagueness.

**Iteration 5: both ratchet rules from the iteration-4 failure analysis fail to raise the score (negative result,
kept).**

| Method | GPT-5.6 | Δ vs `trend_ground_b_o3mini` | DeepSeek | Δ DeepSeek | core GPT | lever ≥ 2 | calls/run |
|---|---:|---|---:|---|---:|---:|---:|
| `decide_then_ground_v2_o3mini` (cue rule; compare with `decide_then_ground_b_o3mini` 0.69) | 0.68 | −0.02 vs v1 (CI −0.08 to +0.04) | 0.64 | −0.05 vs v1 (CI −0.10 to +0.01) | 0.54 | 0.19 (v1 0.15) | 3.2 |
| `multi_decision_ground_o3mini` (trend + top-2 families, each grounded, selected by o3-mini scoring) | 0.69 | −0.04 (CI −0.10 to +0.02) | 0.53 | −0.11 (CI −0.27 to +0.05) | 0.52 | 0.19 | 15.5 |

- The cue rule changed the decisions as intended. On the in situ STEM case, 5 of 6 decisions are now in situ
  characterization and lever hits rose from 2/6 to 4/6. Reconstruction did not follow (0.67 → 0.67), and the MD case
  barely moved.
- Coverage then selection costs 5× more calls and loses to the single forecast-and-ground decision. o3-mini's own
  independent scoring does not pick the best candidate, the result Large Language Monkeys (C7) predicts for
  domains without a verifier.
- The loop therefore stops at iteration 4's `trend_ground_b_o3mini`.

**Iteration-4 failure analysis (decision diagnostics, [loop_analysis.py](./loop_analysis.py)).**
- Every decision method picks the target's kind of answer only 35–38% of the time. When it does, reconstruction is
  much higher (`trend_ground_b_o3mini` 0.82 vs 0.68).
- For understanding gaps whose question says the mechanism is hard to observe, the planner chose ordinary controlled
  experiments 11 of 12 times (target: MD simulation) and 8 of 12 times (target: in situ STEM).
- Ambiguous design cases split across 2–3 plausible families.
- Iteration 5 adds two rules from these dev-only observations: a cue rule in the family map, and keeping the top
  decisions (trend + top-2 families), each grounded, then selecting.
- **Dev/test discipline note:** experiment 22's example of the composition default (CoCrFeNiTi) is a test-split
  case. No rule was derived from it.

---

## 6. Pre-registration for the test split (written 2026-10-25 01:40, before any test-split run of a loop method)

The test split (PMC12029629, PMC12298864, PMC12806431, PMC12941549; 12 units) is run once, with `--final`, for the
configurations fixed by these rules:

1. **Finalists (chosen by rule, not by hand).**
   - F-best: the dev method with the highest GPT-5.6 reconstruction among all methods of iterations 1–5. Ties within
     0.01 are broken by DeepSeek.
   - F-llama: the best Llama-3.3 method by the same rule (does the harness effect on a weak model replicate?).
2. **Controls.**
   - `closed_book` (Llama): the primary baseline, the same as experiment 21.
   - `text_chunks` (Llama).
   - `closed_book_o3mini`: model only.
   - `writer_only_b_o3mini`: model plus the conservative writer, with no harness.
3. **Primary hypothesis (one test, no multiplicity).** F-best − closed_book > 0 on GPT-5.6 reconstruction. Paired
   over the 12 test units (2 samples each), with a paper-clustered bootstrap 95% CI and a sign test over 4 papers.
   With 4 papers the sign test cannot reach p < 0.05, so the CI is the primary evidence.
4. **Secondary comparisons.** Holm across the set:
   - F-best − closed_book_o3mini (harness on top of the model);
   - F-best − writer_only_b_o3mini;
   - F-llama − closed_book;
   - the same comparisons on DeepSeek and on the core metric.
5. **Reporting.** Dev, test and all 12 cases. Test results are reported whatever they show. No further method change
   is made after the test run.

**Finalists, fixed by the rule above on 2026-10-25 02:20, before any test-split run.** 29 configurations were tried
on dev.

| Role | Configuration | Dev GPT-5.6 / DeepSeek |
|---|---|---|
| F-best | `trend_ground_b_o3mini` | 0.729 / 0.635 (next best 0.693) |
| F-llama | `scaffold_ensemble` (Llama-3.3) | 0.615 / 0.328 |
| Controls | `closed_book` (Llama, primary baseline), `text_chunks` (Llama), `closed_book_o3mini`, `writer_only_b_o3mini` | |

---

## 7. Test results (pre-registered, run once on 2026-10-25)

**Integrity.**
- 6 configurations × 12 test units × 2 samples = 144 runs, all generated with `--final`, 0 failures. Every run is
  judged by GPT-5.6 and DeepSeek, audited and labelled.
- `must_obey_check.py --loop` passes on all six directories (72 runs each: 48 dev + 24 test). Test runs are marked
  `final` and `target_free_asserted`. The only warning is the known PMC10759803 margin (a dev case) for the Llama
  arms.
- No method, prompt, query or analysis rule was changed after the test run. The only later code changes are
  reporting: test and all-12 tables omit dev-only methods, and the style checks below were added. Neither changes
  any score.

**Test split (4 papers × 3 levels, 2 samples; GPT-5.6 is primary).**

| Configuration | GPT-5.6 | DeepSeek | core GPT | core DS | intervention | condition | mechanism | outcome | lever ≥ 2 | specificity | calls/run |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `closed_book` (Llama, primary baseline) | 0.52 | 0.35 | 0.58 | 0.25 | 0.46 | 0.21 | 0.71 | 0.71 | 0.21 | 0.28 | 1.0 |
| `text_chunks` (Llama) | 0.36 | 0.26 | 0.44 | 0.25 | 0.25 | 0.17 | 0.62 | 0.42 | 0.12 | 0.14 | 1.0 |
| `closed_book_o3mini` | 0.47 | 0.53 | 0.46 | 0.54 | 0.46 | 0.29 | 0.46 | 0.67 | 0.08 | 0.17 | 1.0 |
| `writer_only_b_o3mini` | 0.52 | 0.69 | 0.58 | 0.65 | 0.46 | 0.21 | 0.71 | 0.71 | 0.12 | 0.19 | 1.0 |
| **`trend_ground_b_o3mini` (F-best)** | **0.65** | **0.88** | 0.60 | **0.85** | 0.38 | **0.50** | **0.83** | **0.88** | 0.17 | 0.24 | 3.1 |
| `scaffold_ensemble` (F-llama) | 0.43 | 0.40 | 0.52 | 0.35 | 0.29 | 0.08 | 0.75 | 0.58 | 0.21 | 0.30 | 16.0 |

**Pre-registered comparisons.** Each cell is the paired difference over units, with its paper-clustered bootstrap
95% CI and papers up/down. Holm runs across the three secondaries within each judge and metric. With 4 papers the
smallest possible two-sided sign-test p is 0.125, so on test the CI is the evidence, as pre-registered.

| Comparison | Dev (8 papers) | **Test (4 papers)** | All 12 papers |
|---|---|---|---|
| **Primary:** F-best − `closed_book`, GPT-5.6 | +0.22 [+0.12, +0.31], 7/1 | **+0.125 [+0.04, +0.23], 4/0** | +0.19 [+0.11, +0.27], 11/1, p = 0.006 |
| same, DeepSeek | +0.32 [+0.11, +0.49], 7/1 | **+0.52 [+0.30, +0.84], 4/0** | +0.39 [+0.22, +0.55], 11/1, p = 0.006 |
| same, core GPT-5.6 | +0.17 [+0.02, +0.30], 7/1 | +0.02 [−0.17, +0.21], 2/2 | +0.12 [−0.01, +0.24], 9/3 |
| same, core DeepSeek | +0.33 [+0.07, +0.56], 7/1 | +0.60 [+0.33, +0.92], 4/0 | +0.42 [+0.22, +0.62], 11/1, p = 0.006 |
| F-best − `closed_book_o3mini` (harness over the model), GPT-5.6 | +0.10 [+0.03, +0.17], 6/2 | +0.18 [+0.06, +0.29], 4/0, Holm 0.38 | +0.125 [+0.06, +0.19], 10/2, Holm 0.12 |
| same, DeepSeek | +0.10 [−0.03, +0.22], 5/3 | +0.34 [+0.21, +0.48], 4/0, Holm 0.38 | +0.18 [+0.07, +0.30], 9/3, Holm 0.44 |
| F-best − `writer_only_b_o3mini` (same model and writer: isolates forecast + grounding), GPT-5.6 | +0.06 [−0.03, +0.16], 4/4 | +0.125 [−0.02, +0.27], 2/1, Holm 1.0 | +0.08 [+0.01, +0.16], 6/5, Holm 1.0 |
| same, DeepSeek | +0.05 [−0.09, +0.19], 4/4 | +0.19 [+0.08, +0.29], 4/0, Holm 0.38 | +0.09 [−0.01, +0.20], 8/4, Holm 0.78 |
| F-llama − `closed_book`, GPT-5.6 | +0.10 [−0.01, +0.22], 5/2 | **−0.09 [−0.18, −0.00], 1/3** | +0.04 [−0.05, +0.14], 6/5 |
| same, DeepSeek | +0.01 [−0.03, +0.05], 3/2 | +0.04 [−0.10, +0.17], 3/1 | +0.02 [−0.03, +0.07], 6/3 |

**Verdict.**
1. **The primary hypothesis replicates.** On test, F-best beats the Llama closed-book baseline on both judges.
   Both CIs are above zero and every test paper is up on both judges. The GPT-5.6 effect is smaller than on dev
   (+0.125 vs +0.22), as expected after picking the best of 29 configurations (winner's curse). Over all 12 papers it
   is +0.19 (CI +0.11 to +0.27; 11 of 12 papers up; sign p = 0.006).
2. **The harness adds to the model.**
   - Against o3-mini closed-book, F-best is up on test on both judges (GPT-5.6 +0.18, DeepSeek +0.34; CIs above
     zero; Holm 0.38 with 4 papers).
   - Against the same model with the same writer, the forecast-and-ground step adds +0.125 on GPT-5.6 (CI crosses
     zero) and +0.19 on DeepSeek (CI above zero).
3. **The gain is not in the intervention.** On test, core GPT-5.6 (intervention + mechanism) is flat (+0.02), and
   intervention agreement is below the baseline (0.38 vs 0.46).
   - The test gain decomposes into condition +0.29, outcome +0.17, mechanism +0.125 and intervention −0.08.
   - The dev core gain (+0.17) does not replicate on GPT-5.6; it does on DeepSeek (+0.60).
4. **The Llama harness result does not replicate.** `scaffold_ensemble` was +0.10 on dev and is −0.09 on test (CI
   −0.18 to 0.00). The Llama gains of iterations 1–2 should be read as dev noise.
5. **The model-only effect depends on the judge.**
   - On test, o3-mini closed-book is below Llama closed-book on GPT-5.6 (−0.05, CI −0.19 to +0.03) and above it on
     DeepSeek (+0.18, CI −0.13 to +0.52).
   - With the conservative writer, o3-mini ties Llama on GPT-5.6 (0.00) and is +0.33 on DeepSeek (CI +0.13 to
     +0.59).

**Is the gain style rather than content?** These are the must_obey.md 6.8 checks, written to
`final_robustness.json`. They cover 432 judged runs of the six finalists over all 12 papers.
- **Length.** F-best's hypotheses are 2.3–2.7 times longer than the baseline's (1,171 vs 500 characters over the
  main fields).
  - GPT-5.6 does not reward length. Overall, ρ(length, score) = 0.05, and within every configuration longer outputs
    score *lower* (ρ −0.17 to −0.36).
  - DeepSeek partly does: ρ = 0.25 overall and 0.23 within F-best. Its larger margins should be discounted, and
    the GPT-5.6 result is the primary evidence.
- **Conditions.** Most of the test gain is condition agreement, so I checked whether listing more conditions wins by
  coverage. It does not.
  - The o3-mini controls write equally long condition fields (226–237 vs 233 characters) but score 0.21–0.29,
    against F-best's 0.50.
  - Within each configuration, ρ(condition length, condition score) is about 0.
  - The retrieved evidence supplies the test regimes (temperatures, loading modes) that the target paper used.
- **Hedging.** Hedges are rare (0.11 per output for F-best and 0.01 for the baseline). They track score weakly,
  with ρ ≤ 0.24 within configurations.
- **Specificity.** The target-free audit's specificity does not track score (|ρ| ≤ 0.13). F-best is more specific
  than the baseline on dev (0.39 vs 0.26) and similar on test (0.24 vs 0.28).

**Per paper (test; GPT-5.6 / DeepSeek, mean of the 3 levels).**

| Paper (all are understanding questions under v3.1) | `closed_book` | `closed_book_o3mini` | `writer_only_b_o3mini` | F-best | F-llama |
|---|---|---|---|---|---|
| PMC12029629 | 0.46 / 0.71 | 0.50 / 0.50 | 0.62 / 0.83 | 0.58 / 0.96 | 0.50 / 0.79 |
| PMC12298864 (processing-route target) | 0.42 / 0.17 | 0.42 / 0.42 | 0.46 / 0.50 | 0.71 / 0.54 | 0.33 / 0.21 |
| PMC12806431 | 0.54 / 0.38 | 0.29 / 0.33 | 0.29 / 0.50 | 0.58 / 0.83 | 0.33 / 0.21 |
| PMC12941549 (processing-route target) | 0.67 / 0.17 | 0.67 / 0.88 | 0.71 / 0.92 | 0.71 / 1.17 | 0.54 / 0.38 |

F-best is above the baseline on all four papers on both judges. The largest GPT-5.6 gain is on PMC12298864, one of
the two processing-route targets that carry understanding questions under v3.1 (the recorded caveat). The gain is
not confined to those two papers.

**Caveats.**
- 4 test papers (12 units) show the direction and a CI, not a precise effect size.
- All four test cases are understanding questions under v3.1, and two have processing-route targets.
- 29 configurations were tried on dev, so the finalists' dev numbers are optimistic; the test is the evidence.
- The judges disagree (ρ = 0.39 in experiment 22), and DeepSeek partly rewards length.
- The judge is not calibrated against experts. It rewards closeness to one paper, not truth.
- The query writer (GPT-5.6) is post-cutoff, a residual risk under must_obey.md 2.4.
- o3-mini's memorisation probe gave 17% specific recall against Llama's 8%. Every hit was inferable from the
  title.

---

## 8. Summary: from failure analysis to the final method

**Where we started.**
- On leak-free queries with a pre-cutoff generator, every experiment-21 arm scored 0.35–0.60 of 4, and no arm beat
  raw text after Holm.
- The failure analysis (section 1) found that generators propose the wrong kind of intervention (79%), default to
  composition changes and ignore the cues in the question.
- Coverage, not selection, limits them.
- 4 of 12 questions asked for the wrong kind of contribution.

**What each change did.** Dev effects are the GPT-5.6 Δ against Llama `closed_book` unless stated. Test effects
(GPT-5.6 / DeepSeek) exist only for the pre-registered configurations.

| # | Change | Inspired by (section 2) | Failure targeted | Dev effect | Test effect | Kept? Why |
|---|---|---|---|---|---|---|
| 0 | Benchmark v3.1: question type from the introduction's gap | C2 (MOOSE-Chem question rules) | F2 | Construction fix; every arm re-run | – | Yes. A rule-level fix, applied blind |
| 1 | Method writer that demands quantified outcomes | H4 (deterministic checks) | F6 | −0.07 | – | No. The judge penalises invented numbers (outcome 0.69 → 0.42) |
| 2 | Frame → family map → family chosen by code | C9, B3, B4, C3 | F1, F1b, F8 | −0.04; +0.08 with the conservative writer | – | Llama only. On o3-mini it constrains the model (0.63 vs 0.67) |
| 3 | Both-order pairwise tournament across families | C1, C3, B5, C12 | F4 | −0.05 | – | No. A pre-cutoff judge does not pick the right family (C7) |
| 4 | Precedent table from earlier papers | C2, C4, C10 | F1, F3 | −0.06 | – | No. It pulls in other alloy systems' mechanisms |
| 5 | Computational sensors plus a separate verifier | A3, A4, B4, B10 | F6 | −0.07 | – | No. It pushes invented numbers |
| 6 | Conservative writer (`WRITER_B`): the ratchet rule | H1, H2 (each failure becomes a harness rule) | Iteration 1 | +0.08 (Llama); +0.04 over o3-mini closed-book | +0.05 / +0.16 over o3-mini closed-book | Yes |
| 7 | Chronological chain → forecast of the next step | C6, C12 | F1, F3 | +0.06 (Llama; best Llama intervention, 0.46); alone on o3-mini −0.05 vs #6 + #9 (0.62 vs 0.67) | – | Only with retrieval, as part of #11 |
| 8 | Coarse-to-fine lever search; independent family scoring | C3, C5, C12, A3 | F3, F4 | +0.02 / −0.03 | – | No. Self-scoring does not select well |
| 9 | Stronger pre-cutoff model (o3-mini, cutoff 2023-10-01) | H2, A6 | All | +0.12 (closed-book) | −0.05 / +0.18 | Only with #6 and #10; alone it depends on the judge |
| 10 | Retrieval aimed at the decided or forecast step | C11, C9, B5, A5 | F5 | On o3-mini, +0.11 [−0.03, +0.26] over the same chain without retrieval (0.62 → 0.73; DeepSeek +0.04); neutral for Llama | #7 + #10 together: +0.125 / +0.19 over #6 + #9 | Yes. It grounds conditions, mechanism and outcome |
| 11 | **#6 + #7 + #9 + #10 = `trend_ground_b_o3mini`** | combination | F1, F5, F6 | **+0.22** | **+0.125 / +0.52** | **Final method** |
| 12 | Ensemble of three scaffolds with trimmed-mean selection (Llama) | C12, A3 | F4 | +0.10 | −0.09 / +0.04 | No. It did not replicate |
| 13 | Cue rule for understanding gaps; multi-decision with selection | Iteration-4 failure analysis, C7 | Family hit rate 35–38% | −0.02 / −0.04 vs their parents | – | No. The decisions changed, the scores did not |

**Bottom line.**
- **Best method: `trend_ground_b_o3mini`**, at 3.1 calls per run. With o3-mini (cutoff 2023-10-01), it:
  1. frames the question;
  2. orders the earlier papers chronologically and forecasts the next step;
  3. retrieves raw text aimed at that step;
  4. writes conservatively.
- **Results.**
  - Over all 12 papers: GPT-5.6 0.70 vs 0.51 (+0.19, CI +0.11 to +0.27, 11 of 12 papers up) and DeepSeek 0.72 vs
    0.33 (+0.39, CI +0.22 to +0.55).
  - The pre-registered test replicates the direction on both judges, with a smaller GPT-5.6 effect (+0.125).
- **What made the difference, and why.**
  1. A stronger pre-cutoff model that can use evidence. With Llama the same pipeline is neutral.
  2. A writer that states uncertainty instead of inventing numbers, which the judge penalises.
  3. Deciding *what to look for* before retrieving: forecast the next step from the chronological chain of earlier
     work, then retrieve evidence aimed at it. This reverses F5 (unaimed evidence distracts) and mainly improves
     conditions, mechanism and outcome.
- **What did not work.**
  - Selection: tournaments, self-scoring and multi-decision.
  - Verifiers that demand numbers.
  - Precedents from other alloy systems.
  - Scaffolds that force a solution family on the stronger model.
  - The Llama harness gains did not replicate on test.
- **Still unsolved: choosing the paper's actual intervention.**
  - Intervention agreement stays about 0.4 of 4 for every configuration.
  - The lever hit rate is at most 0.24.
  - The decision step picks the target's kind of answer only 35–38% of the time.
  - Absolute scores remain low (0.70 of 4). The method is better at *how and under which conditions* than at *what
    to do*.

**Next steps (not run).**
- Run a stronger pre-cutoff model (o1, cutoff 2023-10-01) in the same pipeline once quota allows.
- Add more held-out post-cutoff papers; 12 give wide intervals.
- Calibrate the judge: the materials expert scores a blind sample of F-best and baseline outputs.
- Add a non-LLM verifier for the coverage problem (for example phase-stability or CALPHAD checks of candidate
  interventions), since LLM self-selection does not work here (C7).

---

## 9. must_obey.md checklist (section 9) for this loop

- [x] Query-facing models are all pre-cutoff: Llama-3.3-70B (December 2023), o3-mini and gpt-4o-mini (2023-10-01).
  Every new generator had a memorisation probe (section 0).
- [x] Queries are benchmark v3.1, hash-checked by `must_obey_check.py`. No query was edited after seeing results;
  v3.1 was built from the experiment-22 construction error before any method ran.
- [x] Evidence: the same temporally filtered, family-excluded pools as experiment 21, with no web or live API
  tools. The extractions were audited in experiment 21.
- [x] Payloads are target-free: `Harness.guard` checks every call and every run records `target_free_asserted`.
  Judging is blinded, and tournament pairs run in both orders.
- [x] Development used dev only (29 configurations). Test was used only for the six pre-registered configurations,
  run once.
- [x] Same evidence budget, temperature, output cap and samples as the baselines. Declared differences: the
  generator model (iterations 3–5, an explicit factor) and calls per run (shown in every table).
- [x] GPT-5.6 judge, DeepSeek cross-judge and target-free audit done for every run. The integrity gate passes with
  0 failed runs, and the Llama arms carry the PMC10759803 margin flag.
- [x] Paired statistics with clustered-bootstrap CIs and Holm. Negative results are recorded: iterations 1 and 5,
  F-llama on test, and core on test.
- [x] Experiment log (experiments 22–24) and loop.md updated; `must_obey_check.py --loop` passes on every method
  directory.

---

## 10. Second round ("get better results"): iterations 6–7 and a fresh test set

### 10.1 Pre-registered construction rule for a fresh test set (test2), written 2026-10-25 04:20, before any search

**Why a new test set.** The 4-paper test split was used once (section 7). Since then, its paper titles were printed
by the memorisation probe and one of its targets was quoted in experiment 22, so a second look would not be blind
to rules that favour study-type answers. All conclusions of this round therefore come from a new held-out set
whose titles, queries and targets I do not read before the final runs. Only automated summaries are inspected
(counts, gate pass rates, gap types, dates).

**Rule.**
1. **Search.** The corpus query of `data/corpus/README.md` (same topic terms, `OPEN_ACCESS:Y AND HAS_FT:Y`,
   `sort_cited:y`), restricted to `FIRST_PDATE:[2026-02-17 TO 2026-10-15]`. That date is after the cutoff of every
   model used to build or judge cases (GPT-5.6, 2026-02-16). So, unlike the 12 original cases, no query writer,
   checker or judge can know these papers. If fewer than 12 papers qualify, the window is extended back one month
   at a time (never before 2024-02-01). Papers dated before 2026-02-17 are then flagged.
2. **Eligibility.** The same as the corpus:
   - a research article, not a review, correction or retraction (`import_jats_corpus.validate_primary_research`);
   - open-access JATS XML;
   - methods/results-style sections;
   - the topic rule ("directly studies elevated-temperature, refractory/extreme-environment, creep, oxidation,
     hot-corrosion, melting, thermal/phase-stability or temperature-dependent behaviour of a high-entropy alloy"),
     checked by GPT-5.6 on the title and abstract only.

   Further, a test2 paper:
   - is not in the 50-paper corpus and is not a near-duplicate of one (title token Jaccard ≥ 0.8);
   - has an Introduction whose redacted text (v3 rule) is at least 1,000 characters.
3. **Ranking.** Europe PMC `citedByCount`, then Europe PMC order. The first 12 eligible papers are taken.
4. **Construction.** No step is changed after seeing any output:
   - The hidden target comes from the paper's abstract, methods, results, discussion and conclusions, never the
     Introduction. GPT-5.6 extracts it into the 10-field schema of experiment 3, with the experiment-3 instruction
     to "preserve uncertainty rather than filling absent details". The target is never shown to a query-facing
     model.
   - Queries are written from the redacted Introduction by the v3 writer, then checked by the v3 checker and
     lexical gate, with up to 4 rounds.
   - The v3.1 gap classifier then labels the gap. Non-design gaps are rewritten with the v3.1 templates.
   - Failing levels are flagged and kept.
5. **Evidence.** The 50-paper corpus filtered by date (all 50 predate the window), with the same exclusions.
6. **Use.** test2 is used once, for configurations pre-registered at the end of iteration 7 plus the baselines
   (`closed_book`, `text_chunks`) and the round-1 final method (`trend_ground_b_o3mini`).

### 10.2 Failure analysis of the round-1 best method on dev (before iteration 6)

Dev only (`trend_ground_b_o3mini` and all 10 o3-mini configurations; GPT-5.6 labels; analysis only).

| Finding | Number | What it implies |
|---|---|---|
| **F9** Decision errors are systematic, not random | Class hit: a single hypothesis 0.33; the majority class over the 20 o3-mini hypotheses of a unit 0.375. 4 of 8 dev cases have 0–1 class hits in 60 hypotheses: both simulation studies and both processing-route targets | Voting (self-consistency, S4) cannot fix this; the reasoning frame must change |
| **F10** Coverage is better with o3-mini | Lever ≥ 2 in any of 20 hypotheses: 42% of units; in one hypothesis: 17% | Headroom exists, but self-scoring selection already failed (iteration 5) |
| **F11** The question's niche is ignored | e.g. "earlier studies … addressed a limited thermal regime rather than … across different temperatures" (target: a temperature series), "simulations generally represented perfect, defect-free bulk crystals" (target: simulated short-range order), "FeCoNiPd and FeCoNiPt exhibited soft ferromagnetism" (target: a dual-phase alloy). The forecaster proposed oxidation treatments, ML models and annealing | Reconstruct move 3 of the introduction from its move 2 (S1, S2) |
| **F12** The intervention is not in the evidence | Experiment-18 evidence ceiling: with the top-20 records retrieved *by the target text*, every case is reconstructible only 1–2 of 4 | Retrieval cannot supply the intervention; it has to be forecast |
| **F13** The write-up drifts from the decision | The final hypothesis is in the decided class 65–69% of the time. Drift turns study decisions into material treatments; net cost 1–4 class hits of 48 | Minor; the decision itself is the problem |
| **F14** The gap type is right; the family inside it is not | The framer's gap type matches benchmark v3.1 in 48/48 runs. Understanding questions: `controlled_variable_experiment` chosen 10/12 and filled with material changes. Method questions: ML models chosen 8/12 | Decide from the niche, not from the question's wording ("controlled change") |

### 10.3 What I read for iterations 6–7, what I understood, what I integrated

| ID | Source | What I understood | What we integrate (where) |
|---|---|---|---|
| S1 | **Genre Analysis: English in Academic and Research Settings**, John M. Swales, Cambridge University Press, 1990 (CARS model; read through the Purdue OWL summary, https://owl.purdue.edu/owl/general_writing/the_writing_process/organization_CARS_Model.html) | Research introductions make three moves: establish a territory (importance, generalisations, earlier research), establish a niche (counter-claim, gap, question, continuing a tradition), occupy the niche (purposes, present research, findings). | Our queries are moves 1–2 of a held-out introduction, with move 3 removed by construction. `niche_*` methods quote the niche statements and invert each one into the move that would occupy it (F11). |
| S2 | **Summarizing scientific articles: experiments with relevance and rhetorical status**, Simone Teufel and Marc Moens, Computational Linguistics 28(4):409–445, 2002. https://aclanthology.org/J02-4002/ | Argumentative zoning: sentences of scientific articles can be classified by rhetorical status (aim, basis, contrast with earlier work, …), and the zones carry the paper's argument. | The niche extractor is a two-zone classifier (territory vs niche) restricted to verbatim quotes, checked in code. |
| S3 | **OpenAI o1 System Card**, OpenAI, Dec 2024. https://arxiv.org/abs/2412.16720 (knowledge cutoff 2023-10-01 per the OpenAI model page in must_obey.md) | o1 is trained with reinforcement learning to reason with a long private chain of thought before answering. | The model axis of iteration 3, repeated with a stronger pre-cutoff reasoner. It has its own memorisation probe (section 10.4). |
| S4 | **Self-consistency improves chain of thought reasoning in language models**, Xuezhi Wang et al., ICLR 2023. https://arxiv.org/abs/2203.11171 | Sample diverse reasoning paths and take the most consistent answer. It helps when errors are independent across samples. | Tested offline first (F9): the majority class over 20 o3-mini hypotheses beats a single one only 0.375 vs 0.33. Errors are shared across samples, so voting was **not** built. |
| S5 | **Plan-and-solve prompting**, Lei Wang et al., ACL 2023. https://arxiv.org/abs/2305.04091 | Make a plan, then carry it out step by step. Failures split into planning errors and execution errors. | Measured plan-to-execution fidelity (F13). Execution drift is minor, so the work targets the plan (decision). |
| A4 | Böckeler, harness engineering (section 2) | Computational sensors between inferential steps. | Niche quotes that are not verbatim in the question are dropped in code before the next call (`verified_niches`); a hallucinated niche never reaches the planner. |

### 10.4 Iteration 6 (dev): niche occupation and a stronger reasoner

**o1 memorisation probe** (must_obey.md 2.3; same protocol as section 0):
- o1 claims to remember none of the papers. Specific recall is 21% (5/24), against Llama-3.3 8% and o3-mini 17%;
  quantitative recall is 0.04 (Llama 0.04).
- All 5 hits are inferable from the title or are textbook facts: the BCC structure of TaVCrW, the FCC structure of
  FeNiCrMn, an SRO mechanism stated in the title, and milling refinement in a title that names mechanical
  alloying.
- o1 is allowed, under the same reasoning as o3-mini.

| Method | Failure targeted | Design | Sources |
|---|---|---|---|
| `niche_ground_b_o3mini` | F11, F14 | Each step is a separate call:<br>1. The niche extractor quotes every niche statement verbatim.<br>2. Code keeps only quotes found in the question; if none survive, the whole question is the niche.<br>3. The niche mover inverts each niche into an occupying move (contribution type, lever, technique, conditions) and chooses the most specific one, "from the niche, not from the wording".<br>4. Retrieval is aimed at that move, then WRITER_B writes. | S1, S2, A4, C11 |
| `trend_niche_ground_b_o3mini` | F11 + F1 | Steps 1–3 above, then the chronological chain of iteration 4. The forecaster must pick a next step that occupies one of the verified niches. Then aimed retrieval and WRITER_B. | S1, C6, C12 |
| `writer_only_b_o1` | model control | o1 with the conservative writer, closed-book (compare with `writer_only_b_o3mini`) | S3 |
| `trend_ground_b_o1` | model × harness | The round-1 best pipeline with o1 | S3, C6, C11 |
| `niche_ground_b_o1` | model × niche | `niche_ground_b` with o1 | S1, S3 |

**Two more sources, read for iteration 7.**

| ID | Source | What I understood | What we integrate (where) |
|---|---|---|---|
| S6 | **The probabilistic relevance framework: BM25 and beyond**, Stephen Robertson and Hugo Zaragoza, Foundations and Trends in Information Retrieval, 2009. https://doi.org/10.1561/1500000019 | BM25 ranks documents by term frequency with saturation (k1), length normalisation (b) and inverse document frequency, so rare, distinctive terms count more than common ones. | Our shared retriever scores raw token overlap without IDF, so words such as "alloy", "temperature" and "entropy" decide what is retrieved. `trend_ground_bm25_b_o3mini` ranks the same pool with BM25; budget and record cap are unchanged (iteration 7a). |
| S7 | **Wisdom of the silicon crowd: LLM ensemble prediction capabilities rival human crowd accuracy**, Philipp Schoenegger, Indre Tuminauskaite, Peter S. Park and Philip E. Tetlock, 2024. https://arxiv.org/abs/2402.19379 | Aggregating forecasts from several *different* LLMs can match a human crowd. Diversity across models matters more than repeated samples of one model. | Tested offline before building, on dev decisions (F9). The majority of the *decided* families across Llama and o3-mini is right 42% of the time, against 41% for a single Llama decision. Restricted to the trend forecasters, voting is level with a single decision (37.5% vs 38%). Errors are shared across models too, so a crowd-decision method was **not** built (negative result, no runs). |

**Iteration 7a (dev), designed before iteration-6 results.** `trend_ground_bm25_b_o3mini` is the round-1 best
pipeline with BM25 grounding (S6). It isolates retrieval quality (F5, F12: grounding is where round 1's condition,
mechanism and outcome gains came from).

### 10.5 Round-2 finalist rule (written 2026-10-25 04:45, before the iteration-7b results)

1. **Unbiased reference.** The round-1 best's dev score (0.729) is the maximum of 29 configurations. Round-2
   configurations are therefore compared on dev with `trend_ground_b_o3mini_r2`: the same code with fresh samples.
2. **F2.** Among the round-2 configurations (iterations 6–7), F2 is the one with the highest dev GPT-5.6
   reconstruction, provided it is at least the replicate's score. Ties within 0.01 are broken by DeepSeek.
   Otherwise there is no F2, and round 1's method is the round-2 final.
3. **test2 runs (once, `--final`).**
   - Baselines: `closed_book` and `text_chunks` (Llama-3.3).
   - Model controls: `closed_book_o3mini` and `writer_only_b_o3mini`.
   - The round-1 best: `trend_ground_b_o3mini`.
   - F2, if it exists, plus the writer-only control for F2's model if that model is not o3-mini.
4. **Primary hypothesis on test2** (GPT-5.6 reconstruction, 12 papers × 3 levels, paper-clustered bootstrap, sign
   test over 12 papers):
   - If F2 exists: F2 − `trend_ground_b_o3mini` > 0 (does round 2 improve on round 1?).
   - Otherwise: `trend_ground_b_o3mini` − `closed_book` > 0, a replication of round 1 on fresh papers.
5. **Secondary (Holm within each judge and metric).**
   - `trend_ground_b_o3mini` − `closed_book` (when it is not the primary).
   - F2 − `closed_book`.
   - `writer_only_b_o3mini` − `closed_book` and `closed_book_o3mini` − `closed_book`.
   - The same comparisons on DeepSeek and on core.
   - The 5 test2 papers dated after GPT-5.6's cutoff are reported separately.

**Iteration 7b–7c designs (written before their results).**

| Method | Failure targeted | Design | Sources |
|---|---|---|---|
| `trend_ground_b_o3mini_r2` | winner's curse | The round-1 best, unchanged, with fresh samples: the unbiased dev reference of 10.5 | must_obey.md 6.5 |
| `trend_o1_ground_b_o3mini` | F1 (decision) without o1's outcome cost | Planner/executor split: o1 frames and forecasts (it had the best intervention score in iteration 6); o3-mini grounds and writes (best outcome agreement) | H2 (split planner from executor), S3 |
| `trend_ground_iter_b_o3mini` | F5 (grounding of mechanism and conditions) | Trend forecast → grounded draft → a second retrieval aimed at the draft's intervention, mediator, mechanism and conditions → revision that may change mechanism, conditions and outcome only where the new evidence supports it. Declared difference: two retrievals | S8: **Enhancing retrieval-augmented large language models with iterative retrieval-generation synergy** (ITER-RETGEN), Zhihong Shao et al., Findings of EMNLP 2023, https://arxiv.org/abs/2305.15294. A model's own output is a better query for the knowledge it needs next than the original question. |

**Consensus selection, tested offline instead of built.** S9: **It's MBR all the way down: modern generation
techniques through the lens of minimum Bayes risk**, Amanda Bertsch et al., 2023, https://arxiv.org/abs/2310.01387.
Choose the candidate most similar to the others (the medoid), which approximates the minimum-risk output.
- On dev, the medoid by content-word Jaccard among a unit's 24 o3-mini hypotheses scores 0.719. That is above a
  random member of the pool (0.651) but below the round-1 best's own mean (0.729).
- Among grounded methods only, the medoid scores 0.708 against a mean of 0.698.
- Not built: consensus favours the systematic default (F9). The oracle best-of-pool is 1.10, so the headroom is in
  selection, but no available signal finds it.

**Iteration 6 and 7a results (dev, 24 units × 2 samples).** Δ is against the fresh-sample replicate of the round-1
best (`trend_ground_b_o3mini_r2`, 10.5).

| Method | GPT-5.6 | Δ vs replicate [95% CI] | DeepSeek | Δ DeepSeek [95% CI] | core GPT | intervention | mechanism | outcome | lever ≥ 2 | calls/run |
|---|---:|---|---:|---|---:|---:|---:|---:|---:|---:|
| `trend_ground_b_o3mini` (round 1, original samples) | 0.73 | +0.01 [−0.09, +0.12] | 0.64 | −0.03 [−0.10, +0.05] | 0.59 | 0.38 | 0.81 | 0.94 | 0.19 | 3.1 |
| `trend_ground_b_o3mini_r2` (same code, fresh samples) | 0.72 | – | 0.66 | – | 0.57 | 0.31 | 0.83 | 0.96 | 0.15 | 3.2 |
| `niche_ground_b_o3mini` | 0.56 | −0.16 [−0.28, −0.06] | 0.64 | −0.03 [−0.12, +0.09] | 0.40 | 0.21 | 0.58 | 0.83 | 0.21 | 3.1 |
| `trend_niche_ground_b_o3mini` | 0.65 | −0.07 [−0.14, +0.01] | 0.59 | −0.07 [−0.15, +0.01] | 0.49 | 0.23 | 0.75 | 0.90 | 0.15 | 5.2 |
| `writer_only_b_o1` | 0.63 | −0.09 [−0.26, +0.06] | 0.51 | −0.15 [−0.38, +0.08] | 0.45 | 0.25 | 0.65 | 0.79 | 0.17 | 1.0 |
| `trend_ground_b_o1` | 0.67 | −0.05 [−0.20, +0.10] | 0.57 | −0.09 [−0.26, +0.06] | 0.56 | 0.42 | 0.71 | 0.79 | 0.15 | 3.0 |
| `niche_ground_b_o1` | 0.56 | −0.16 [−0.30, −0.04] | 0.57 | −0.09 [−0.22, +0.05] | 0.42 | 0.25 | 0.58 | 0.77 | 0.25 | 3.0 |
| `trend_ground_bm25_b_o3mini` (7a) | 0.65 | −0.07 [−0.16, +0.02] | 0.62 | −0.04 [−0.18, +0.11] | 0.45 | 0.21 | 0.69 | 0.96 | 0.10 | 3.0 |

**What iteration 6 and 7a taught.**
- **The winner's curse on dev was small.** Fresh samples of the round-1 best score 0.72 against 0.73, so it is a
  genuinely strong reference.
- **Niche occupation fails (S1, S2).** Quote verification works: hallucinated niches are dropped, and on the
  wear-coating question the expert level quotes exactly the niche the paper fills ("limited thermal regime rather
  than … across different temperatures"). But the decision does not follow the niche: o3-mini still chose
  pre-oxidation treatments there, and ML or DFT frameworks for the short-range-order question.
  - The niche methods hit the target's lever *more* often (lever ≥ 2: 0.21–0.25 vs 0.15–0.19), yet reconstruction
    falls. Mechanism drops from about 0.8 to 0.58, because removing the chronological chain removes the earlier
    papers that anchored the mechanism.
  - Adding the niche to the trend chain costs 0.07.
- **A stronger reasoner does not help (S3).** o1 decides slightly better (intervention 0.42, the best of any
  configuration) but has lower outcome agreement (0.79 vs 0.94–0.96).
  - The target-free audit shows o1 quantifies outcomes and process parameters more often (outcomes 0.71–0.73 vs
    0.38–0.52; process parameters 0.62–0.81 vs 0.33–0.35).
  - That does not explain the outcome deficit: within o1, quantified outcomes score *higher* than unquantified
    ones (0.85–0.94 vs 0.38–0.64). The cause is not identified.
  - With the writer only, o1 is below o3-mini (0.63 vs 0.67). Iteration 7b therefore tests o1 as planner only.
- **BM25 grounding hurts (S6).** Mechanism falls from 0.83 to 0.69 and intervention from 0.31 to 0.21; outcome is
  unchanged. A likely cause, not verified: IDF weighting favours chunks that share rare tokens (specific element
  or technique names) over chunks that cover the whole problem, which the coverage term of the shared retriever
  rewards. Negative result.

**Iteration 7b–7c results (dev; Δ against the replicate).**

| Method | GPT-5.6 | Δ [95% CI] | DeepSeek | Δ DeepSeek [95% CI] | core | intervention | condition | mechanism | outcome |
|---|---:|---|---:|---|---:|---:|---:|---:|---:|
| `trend_o1_ground_b_o3mini` (o1 plans, o3-mini writes) | 0.65 | −0.07 [−0.17, +0.02] | 0.54 | −0.13 [−0.21, −0.02] | 0.56 | 0.35 | 0.65 | 0.77 | 0.81 |
| `trend_ground_iter_b_o3mini` (second, draft-aimed retrieval) | 0.66 | −0.06 [−0.18, +0.07] | 0.58 | −0.08 [−0.23, +0.08] | 0.47 | 0.26 | 0.74 | 0.70 | 0.94 |

- The planner/executor split does not recover o1's better decisions: intervention is 0.35, and conditions (0.65)
  and outcome (0.81) are lower than the replicate's. The cause was not analysed.
- A second retrieval aimed at the draft lowers mechanism (0.83 → 0.70) and intervention (0.31 → 0.26). A likely
  cause, not verified: evidence retrieved for the draft's own claims pulls the revision toward other systems, as
  precedents did in iteration 1.

**F2 decision (rule 10.5, recorded 2026-10-25 05:06, before any test2 result was seen).** No round-2 configuration
reaches the replicate (0.719). The best is `trend_ground_b_o1` at 0.672. So there is **no F2**: the round-2 final
is the round-1 method. test2 runs only the five configurations fixed by rule 3, and the primary hypothesis is
`trend_ground_b_o3mini` − `closed_book` > 0 on test2 (replication on 12 fresh papers).

**Iteration 8 (exploratory, dev only; designed after the F2 decision, so it cannot enter the test2 evaluation).**

| Method | Failure targeted | Design | Source |
|---|---|---|---|
| `trend_focus_ground_b_o3mini` | F5, F12 (grounding relevance) | The trend forecaster already names the earlier papers that address the same problem, but grounding ignored that list and searched the whole pool lexically. Grounding now fills the budget first from those papers' chunks, ranked by the usual retriever, then tops up from the rest; same budget and cap | S10: **Corrective retrieval augmented generation**, Shi-Qi Yan, Jia-Chen Gu, Yun Zhu and Zhen-Hua Ling, 2024, https://arxiv.org/abs/2401.15884. Evaluate the relevance of retrieved documents before generating and act on it. Here the relevance judgement comes from the forecaster that already read the earlier papers. |

**Iteration 8 result (dev, exploratory).**

| Method | GPT-5.6 | Δ vs replicate [95% CI] | DeepSeek | Δ DeepSeek [95% CI] | core | intervention | condition | mechanism | outcome |
|---|---:|---|---:|---|---:|---:|---:|---:|---:|
| `trend_focus_ground_b_o3mini` | 0.65 | −0.07 [−0.17, +0.02] | 0.71 | +0.05 [−0.07, +0.19] | 0.52 | 0.23 | 0.71 | 0.81 | 0.83 |

- Not an improvement, and the judges disagree. The method also did not work as designed: the forecaster names a
  valid relevant earlier paper only 0.5 times per run, so grounding changed little (on average 2.8 grounding
  records per run come from those papers).
- All 10 round-2 dev directories pass `must_obey_check.py --loop` (480 runs, 0 failed).

### 10.6 test2 results (pre-registered in 10.5; run once on 2026-10-25)

**Integrity.** 5 configurations × 36 units × 2 samples = 360 runs, all `--final`, 0 failures. Every run is judged by
GPT-5.6 and DeepSeek. Audits, labels and the `must_obey_check.py --loop` result are in 10.6b. I did not read any
test2 title, query or target before these runs; only automated summaries were inspected.

**test2, 12 fresh papers (GPT-5.6 is primary).**

| Configuration | GPT-5.6 | DeepSeek | core GPT | core DS | intervention | condition | mechanism | outcome | broad / problem / expert | calls/run |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| `closed_book` (Llama-3.3, baseline) | 0.46 | 0.30 | 0.40 | 0.21 | 0.21 | 0.38 | 0.60 | 0.67 | 0.40 / 0.50 / 0.49 | 1 |
| `text_chunks` (Llama-3.3) | 0.40 | 0.25 | 0.31 | 0.15 | 0.22 | 0.33 | 0.39 | 0.65 | 0.38 / 0.44 / 0.39 | 1 |
| `closed_book_o3mini` | 0.57 | 0.55 | 0.50 | 0.49 | 0.38 | 0.51 | 0.62 | 0.78 | 0.56 / 0.52 / 0.64 | 1 |
| **`writer_only_b_o3mini`** (o3-mini, conservative writer) | **0.65** | **0.64** | **0.62** | **0.60** | **0.43** | **0.53** | **0.81** | **0.82** | 0.65 / 0.66 / 0.64 | 1 |
| `trend_ground_b_o3mini` (round-1 final) | 0.57 | 0.52 | 0.52 | 0.47 | 0.36 | 0.51 | 0.68 | 0.72 | 0.74 / 0.46 / 0.51 | 3.1 |

**Pre-registered comparisons on test2.** Each cell is the paired difference, its paper-clustered bootstrap 95% CI
and papers up/down. Holm runs across the two secondaries.

| Comparison | GPT-5.6 | DeepSeek | core GPT | core DS |
|---|---|---|---|---|
| **Primary:** `trend_ground_b_o3mini` − `closed_book` | **+0.11 [+0.01, +0.22]**, 8/3, p = 0.23 | +0.23 [+0.06, +0.41], 7/5 | +0.12 [−0.06, +0.33] | +0.26 [+0.09, +0.44], 8/1, p = 0.04 |
| Secondary: `writer_only_b_o3mini` − `closed_book` | **+0.18 [+0.07, +0.31], 9/1, Holm p = 0.043** | +0.34 [+0.15, +0.56] | +0.22 [+0.06, +0.41] | +0.40 [+0.19, +0.61], Holm p = 0.008 |
| Secondary: `closed_book_o3mini` − `closed_book` | +0.11 [0.00, +0.22], 9/3 | +0.26 [+0.09, +0.45] | +0.10 [−0.06, +0.27] | +0.29 [+0.11, +0.49], Holm p = 0.008 |
| Exploratory: `trend_ground_b_o3mini` − `closed_book_o3mini` | −0.003 [−0.10, +0.10], 5/5 | −0.03 [−0.17, +0.09] | +0.02 [−0.13, +0.17] | −0.02 [−0.17, +0.10] |
| Exploratory: `trend_ground_b_o3mini` − `writer_only_b_o3mini` | −0.08 [−0.20, +0.05], 4/8 | −0.12 [−0.25, +0.03] | −0.10 [−0.25, +0.05] | −0.13 [−0.27, 0.00] |
| Exploratory: `text_chunks` − `closed_book` | −0.06 [−0.13, +0.01], 3/9 | −0.04 [−0.13, +0.05] | −0.10 [−0.19, 0.00] | −0.06 [−0.15, +0.04] |

**The 5 test2 papers dated after GPT-5.6's cutoff** (no model used to build, run or judge them can know them;
pre-registered separate report):

| Configuration | GPT-5.6 | DeepSeek |
|---|---:|---:|
| `closed_book` | 0.41 | 0.29 |
| `closed_book_o3mini` | 0.65 | 0.78 |
| `writer_only_b_o3mini` | **0.76** | **0.87** |
| `trend_ground_b_o3mini` | 0.55 | 0.66 |

On this subset, `writer_only_b_o3mini` − `closed_book` is +0.35 [+0.18, +0.53] and `trend_ground_b_o3mini` −
`writer_only_b_o3mini` is −0.21 [−0.38, −0.05]; 5 papers, exploratory.

**All 16 held-out papers** (test + test2, exploratory; the two sets' targets were built by different extractors).

| Comparison | GPT-5.6 | DeepSeek |
|---|---|---|
| `writer_only_b_o3mini` − `closed_book` | +0.14 [+0.04, +0.25], 12/2, p = 0.013 | +0.34 [+0.19, +0.52], 13/2, p = 0.007 |
| `trend_ground_b_o3mini` − `closed_book` | +0.11 [+0.03, +0.20], 12/3, p = 0.035 | +0.30 [+0.15, +0.47], 11/5 |
| `trend_ground_b_o3mini` − `writer_only_b_o3mini` | −0.03 [−0.14, +0.08], 6/9 | −0.04 [−0.17, +0.09], 8/7 |

Means over the 16 papers (GPT-5.6 / DeepSeek):

| Configuration | GPT-5.6 | DeepSeek |
|---|---:|---:|
| `closed_book` | 0.48 | 0.31 |
| `closed_book_o3mini` | 0.55 | 0.55 |
| `writer_only_b_o3mini` | **0.62** | **0.65** |
| `trend_ground_b_o3mini` | 0.59 | 0.61 |

**Verdict.**
1. **The primary hypothesis replicates on fresh papers, more weakly.** The round-1 method beats the Llama baseline
   on test2 on both judges (CIs above zero), with a smaller effect than on the original split (+0.11 vs +0.19 over
   all 12 original papers).
2. **The harness does not add to the model on fresh papers.** On test2 the round-1 method is level with o3-mini
   closed-book and below o3-mini with the conservative writer alone. The difference comes from understanding
   questions (writer-only 0.82 vs 0.67) and is largest on the 5 papers after GPT-5.6's cutoff. Design questions
   are level (0.57 vs 0.56).
   - The labels show why. The trend forecast puts the hypothesis in the target's class less often than o3-mini
     alone: lever match ≥ 1 is 0.35 vs 0.53 (writer-only) and 0.56 (closed-book).
   - On dev, where the forecaster was selected, it was slightly *more* often right (0.38 vs 0.31). The
     dev-selected decision step does not generalise.
   - Problem alignment is not the cause. The harness trails the writer by the same 0.14 on dev and on test2.
   - Over all 16 held-out papers the two are indistinguishable (−0.03).
3. **The best-supported configuration is the simplest.** o3-mini with the conservative writer, one call:
   - It is the only Holm-significant pre-registered result on test2: +0.18, 9 of 10 papers with a difference up.
   - It is the highest-scoring configuration on test2, on its post-cutoff subset and over all 16 held-out papers,
     on both judges.
   - It is chosen by parsimony, not by a significant win over the harness; that difference is not claimed.
4. **Evidence still hurts the weak model.** `text_chunks` is below closed-book on test2 (−0.06, 9 of 12 papers
   down), as in experiment 21.

#### 10.6b test2 integrity and style checks

- **Integrity.** `must_obey_check.py --loop` passes on all five configurations: 144 runs each (48 dev, 24 test, 72
  test2), 0 failed, zero leakage counters, every test2 run marked final and target-free asserted. The only warning
  is the known PMC10759803 margin (a dev case) for the Llama arms.
- **Style (must_obey.md 6.8, 360 test2 runs).**

  | Configuration | length (characters) | hedges | specificity (audit) |
  |---|---:|---:|---:|
  | `closed_book` (Llama) | 530 | 0.10 | 0.32 |
  | `closed_book_o3mini` | 1,166 | 0.07 | 0.30 |
  | `writer_only_b_o3mini` | 1,197 | 0.14 | 0.31 |
  | `trend_ground_b_o3mini` | 1,239 | 0.17 | 0.31 |

  - Among the o3-mini configurations, the best one is neither the longest nor the most hedged, and specificity is
    the same. Its advantage over the other o3-mini configurations is not a style effect.
  - Within configurations, GPT-5.6 scores do not track length for the o3-mini arms (ρ −0.06 to +0.06), and more
    specific hypotheses score slightly *lower* (ρ −0.08 to −0.22).
  - DeepSeek rewards length within configurations (ρ +0.05 to +0.29), so its larger margins over the shorter Llama
    baseline should be discounted. The GPT-5.6 result is primary.

### 10.7 Summary of round 2: what was tried, what made a difference, and why

| # | Change | Inspired by | Failure targeted | Dev effect (vs fresh replicate) | Held-out effect | Kept? Why |
|---|---|---|---|---|---|---|
| 14 | Majority vote over decisions, across samples or across models (offline) | S4, S7 | F9 | Class hit 0.38 → 0.42 at best; level with single decisions for trend forecasters | – | No. Errors are shared, not independent |
| 15 | Niche occupation (CARS), verified quotes | S1, S2, A4 | F11, F14 | −0.16 (o3-mini), −0.16 (o1); with the trend chain −0.07 | – | No. Decisions do not follow the niche, and mechanism falls |
| 16 | Stronger pre-cutoff reasoner (o1) | S3 | F1 | −0.05 (with the harness), −0.09 (writer only) | – | No. Better intervention (0.42), worse outcome |
| 17 | BM25 grounding | S6 | F5, F12 | −0.07 | – | No. Mechanism 0.83 → 0.69 |
| 18 | Planner/executor split (o1 plans, o3-mini writes) | H2, S3 | F1 | −0.07 (DeepSeek −0.13) | – | No |
| 19 | Second retrieval aimed at the draft (ITER-RETGEN) | S8 | F5 | −0.06 | – | No. Mechanism 0.83 → 0.70 |
| 20 | Consensus (MBR) selection (offline) | S9 | F10 | Medoid 0.72 vs incumbent 0.73 | – | No. Consensus favours the systematic default |
| 21 | Grounding focused on the forecaster's relevant papers | S10 | F5 | −0.07 (DeepSeek +0.05) | – | No. The relevance list is mostly empty |
| 22 | Fresh-sample replicate of the incumbent | must_obey 6.5 | winner's curse | 0.72 vs 0.73 | – | Yes, as the reference |
| 23 | **Fresh held-out set (test2)** | must_obey 6.5, 2.1 | non-blind test split | – | 12 papers; 5 unknowable to every model involved | **Yes** |
| 24 | **o3-mini with the conservative writer, one call** (round-1 control) | rounds 1–2 | – | 0.67 (round 1) | **test2 +0.18 over the baseline (Holm p = 0.043); best on test2, on its post-cutoff subset and over all 16 held-out papers** | **Yes: the recommended configuration (parsimony)** |

**Bottom line of round 2.**
- **The better result is a simpler method that holds up on fresh papers.** On 12 papers that no model saw, o3-mini
  with the conservative writer scores 0.65 against 0.46 for the Llama baseline (DeepSeek 0.64 vs 0.30). On the 5
  papers that no model involved could know, it scores 0.76 against 0.41. It needs one call per hypothesis instead
  of 3.1.
- **Why:** the two changes that generalise are the model (a pre-cutoff reasoning model) and the writer (state
  uncertainty instead of inventing numbers). The harness steps that won on dev do not transfer:
  - the trend forecast and grounding are level with o3-mini closed-book on test2;
  - the dev-selected forecast picks the target's class less often on fresh papers (0.35 vs 0.53 for the writer
    alone).
- **What does not help, measured:** prompting the decision (frames, niches, cue rules), stronger reasoning (o1),
  voting, consensus and self-scoring selection, alternative retrievers and iterative retrieval. In both rounds,
  every attempt to steer which kind of contribution the model proposes failed. The decision bottleneck (F1, F9)
  remains: intervention agreement stays below 0.5 of 4 for every configuration on every split.
- **Next:**
  - a verifier that is not an LLM (phase stability, CALPHAD or simulation checks) to break the shared prior;
  - test3 (2024-02 to 2025-07 papers) to test any new method;
  - expert calibration of the judge.

### 10.8 must_obey.md checklist for round 2

- [x] Query-facing models are all pre-cutoff (o3-mini, o1, Llama-3.3). o1 was probed first (10.4).
- [x] Queries are frozen: v3.1 for dev, and test2 built once by a pre-registered rule. `must_obey_check.py` checks
  both.
- [x] Evidence: the same date-filtered corpus pools, with no web or live API tools in any method. BM25 and focused
  grounding keep the pool, budget and cap. ITER-RETGEN's second retrieval is declared.
- [x] Payloads are target-free (`Harness.guard`); niche quotes are verified in code.
- [x] Dev only during development (10 configurations, 480 runs). test2 was used once, for configurations fixed by
  the rule in 10.5 before any test2 result was seen. The old test split was not reused.
- [x] Comparisons use a fresh-sample replicate of the incumbent.
- [x] GPT-5.6 judge, DeepSeek cross-judge, target-free audit and labels for every run; the integrity gate passes
  with 0 failed runs (10.6b).
- [x] Paired statistics with clustered-bootstrap CIs and Holm. Negative results are recorded (iterations 6–8, two
  offline negatives).
- [x] Experiment log (experiments 25–26), READMEs and loop.md updated.

---

## 11. Round 3 ("increase it more"): a larger development set, writer-level methods and a fresh test3

### 11.1 Protocol and pre-registered test3 rule (written 2026-10-25 09:31, before any test3 search or round-3 result)

1. **Development set dev3 = dev (8) + test (4) + test2 (12) = 24 papers, 72 units.**
   - test and test2 are spent: each was used once for its pre-registered finals. They become development data, and
     no further claim rests on them.
   - Reason: round 2 showed that a method selected on 8 papers does not generalise (the trend forecaster: class
     hit 0.38 on dev, 0.35 on test2 vs 0.53 for the plain writer).
2. **Incumbent.** `writer_only_b_o3mini`, the round-2 recommendation. Its fresh-sample replicate on dev3
   (`writer_only_b_o3mini_r3`) is the reference for every round-3 comparison (must_obey.md 6.5).
3. **test3: built like test2** (`benchmark_test2.py`, set `test3`).
   - The corpus query restricted to `FIRST_PDATE:[2024-02-01 TO 2025-07-16]`: the window just before test2, and
     at least one month after every generator's cutoff.
   - Ranked by Europe PMC `citedByCount`, which is meaningful here because these papers have had time to be cited.
   - Excludes corpus papers (including the 12 original cases), test2 papers and near-duplicates.
   - The same topic rule and Introduction rule; the first 12 eligible papers are taken.
   - All test3 papers precede GPT-5.6's cutoff, so the query writer could know them. They are flagged, which is the
     same residual risk as the original 12.
   - Targets from the non-Introduction sections; queries from the v3 writer, checker and gate, then the v3.1 gap
     templates.
   - Nobody reads test3 titles, queries or targets before the final runs.
4. **Finalist rule.** F3 is the dev3 configuration with the highest GPT-5.6 reconstruction, provided it is above
   the incumbent's replicate. Ties within 0.01 are broken by DeepSeek.
   - test3 is run once with `closed_book`, `writer_only_b_o3mini`, `trend_ground_b_o3mini`, F3, and F3's
     model-only control if F3 uses another model.
   - **Primary:** F3 − `writer_only_b_o3mini` on test3, if F3 exists; otherwise `writer_only_b_o3mini` −
     `closed_book`.
   - **Secondary (Holm):** F3 − `closed_book`, `writer_only_b_o3mini` − `closed_book` and `trend_ground_b_o3mini`
     − `closed_book`, on GPT-5.6, DeepSeek and core.

### 11.2 Failure analysis of the incumbent on dev3 (before any round-3 result)

[failure_r3.py](./failure_r3.py) covers `writer_only_b_o3mini`, 144 runs on 24 papers (GPT-5.6 labels and the
experiment-12 error coder; analysis only). Output: `loop/failure_r3.json`.

| Finding | Number | What it implies |
|---|---|---|
| **F15** Design questions: right class, wrong specifics | Class hit 0.46, yet intervention agreement 0.13/4; outcome is the strongest dimension (1.15) | Push toward the lever a typical group would use |
| **F16** Method questions are the weakest | Reconstruction 0.43, outcome 0.22, class hit 0.28 | As F15 |
| **F17** Understanding questions lose on conditions | Conditions 0.46 (intervention 0.61, mechanism 0.83) | Evidence on typical regimes and techniques may help |
| **F18** Even a class hit gives few intervention points | Intervention 0.70/4 given a hit vs 0.21 given a miss; mechanism 0.91 vs 0.66 | The specific lever and parameters are the gap |
| **Regime anchoring is not the problem** | 87% of hypotheses already repeat a quantity the question states, and those do not score higher on conditions (0.96 vs 1.25, n = 4 not anchored) | No regime-anchoring method |
| **Error mix** (4.3 fatal errors per run) | Unsupported claims 24%, wrong intervention 19%, wrong mechanism 19%, wrong conditions 11%, wrong outcome 9%, wrong baseline 8%, vague 8% | Evidence could address unsupported claims |

**gpt-4o was not used.** Its memorisation probe (must_obey.md 2.3) could not run: 0 of 24 calls completed because of
rate limits. A generator that cannot finish its probe, a 144-run dev3 batch and a test3 evaluation is not usable.

### 11.3 What I read for round 3, and what I integrated

| ID | Source | What I understood | What we integrate (where) |
|---|---|---|---|
| S11 | **Large language models surpass human experts in predicting neuroscience results**, Xiaoliang Luo et al., Nature Human Behaviour 2024. https://arxiv.org/abs/2403.03230 | LLMs predict which of two versions of a published result is the real one better than experts. Prediction of an existing result is a different task from proposing a novel idea. | R1: the writer is told the result already exists and is asked for the most probable study and outcome, not the most novel (F15, F16, F18). |
| C10 | **Large language models as analogical reasoners**, Yasunaga et al., ICLR 2024 (section 2) | Self-generated exemplars help strong models. | R2: o3-mini first recalls up to three earlier studies on the same kind of gap. The recall is a separate call, so it never enters the judged hypothesis. |
| S12 | **Scaling LLM test-time compute optimally can be more effective than scaling model parameters**, Charlie Snell et al., 2024. https://arxiv.org/abs/2408.03314 | More inference-time computation helps when it is allocated to the problem's difficulty. A reasoning model's effort setting is one such knob. | R3: the same writer and model with `reasoning_effort="high"`. o1 (a bigger model) did not help in round 2; this tests more thinking with the same model. |
| S9 | MBR (Bertsch et al. 2023; section 10.5) | The candidate closest to the others approximates the minimum-risk output. | R4: medoid of five independent writer samples (content-word Jaccard). Offline in round 2 it was +0.01 over a pool mean; here it is the incumbent's own samples. |

### 11.4 Round-3 designs (dev3: 24 papers × 3 levels × 2 samples = 144 runs each)

| Method | Failure targeted | Design | Calls |
|---|---|---|---:|
| `writer_only_b_o3mini_r3` | reference | The incumbent with fresh samples (11.1) | 1 |
| `forecast_writer_b_o3mini` (R1) | F15, F16, F18 | WRITER_B plus the forecasting framing (S11) | 1 |
| `analogy_writer_b_o3mini` (R2) | F15, F18 | Recall up to three precedent studies, then WRITER_B with them as notes (C10) | 2 |
| `writer_only_b_o3mini_high` (R3) | all | WRITER_B with `reasoning_effort="high"` (S12) | 1 |
| `writer_mbr_b_o3mini` (R4) | F10 (variance) | Five WRITER_B samples, keep the medoid (S9) | 5 |
| `text_chunks_b_o3mini` (R5) | F17, unsupported claims | WRITER_B with question-retrieved chunks and no forecast step; isolates evidence for o3-mini | 1 |

Harness change before these runs: a final hypothesis keeps only the shared schema fields, so no method can hand the
judge extra content. None of the 2,376 earlier runs had an extra field, so earlier results are unaffected.

### 11.5 Combination R6 (designed before its results and before the replicate's judgments)

- **Preliminary signal.** On GPT-5.6 against the incumbent's *original* dev3 runs (the replicate was still being
  judged), R5 evidence (+0.03 [−0.04, +0.10]) and R4 MBR (+0.03 [−0.03, +0.09]) are the two slightly positive
  pieces. They address different failures: F17 conditions and unsupported claims for R5, sample variance for R4.
- **Design.** `text_chunks_mbr_b_o3mini`: one question-retrieved evidence pack, five WRITER_B samples with that
  pack, and the medoid is kept (5 calls). It enters the 11.1 finalist rule like every other round-3 configuration.

**Two offline checks on dev3 (no runs).**
- **Consensus over a mixed pool does not help.** Pooling the original writer, forecast, analogy and evidence
  variants gives 8 candidates per unit. Their medoid scores 0.625 against a pool mean of 0.637 (vs the incumbent
  −0.007 [−0.07, +0.06]). The best candidate in each pool averages 0.99, so the headroom is in selection.
- **No cheap, target-free feature finds that best candidate.** Within units of 7 o3-mini variants, the mean
  Spearman ρ between score and query overlap is +0.02, length −0.03, number count −0.01, consensus +0.03 and hedges
  +0.03. Without a verifier, selection among similar candidates is close to random (C7).

### 11.6 Round-3 results on dev3 and the F3 decision

**dev3 (24 papers × 3 levels × 2 samples).** Δ is against the incumbent's fresh-sample replicate
(`writer_only_b_o3mini_r3`; GPT-5.6 0.642, DeepSeek 0.632).

| Method | GPT-5.6 | Δ [95% CI], papers up/down | DeepSeek | Δ DeepSeek [95% CI] | core GPT | Δ core GPT | calls/run |
|---|---:|---|---:|---|---:|---:|---:|
| `writer_only_b_o3mini` (incumbent, original samples) | 0.632 | −0.010 [−0.06, +0.04], 13/8 | 0.630 | −0.002 [−0.07, +0.06] | 0.580 | +0.007 | 1 |
| `forecast_writer_b_o3mini` (R1) | 0.616 | −0.026 [−0.09, +0.03], 7/11 | 0.644 | +0.012 [−0.07, +0.10] | 0.517 | −0.056 | 1 |
| `analogy_writer_b_o3mini` (R2) | 0.641 | −0.002 [−0.06, +0.06], 8/11 | 0.637 | +0.005 [−0.07, +0.09] | 0.552 | −0.021 | 2 |
| `writer_only_b_o3mini_high` (R3) | 0.641 | −0.002 [−0.06, +0.06], 10/12 | 0.648 | +0.016 [−0.06, +0.09] | 0.562 | −0.010 | 1 |
| `writer_mbr_b_o3mini` (R4) | 0.644 | +0.002 [−0.05, +0.05], 11/10 | 0.615 | −0.017 [−0.07, +0.04] | 0.538 | −0.035 | 5 |
| `text_chunks_b_o3mini` (R5) | 0.658 | +0.016 [−0.05, +0.09], 10/12 | **0.705** | **+0.073** [−0.04, +0.18] | 0.542 | −0.031 | 1 |
| **`text_chunks_mbr_b_o3mini` (R6)** | **0.688** | **+0.045 [−0.01, +0.10], 16/8** | 0.649 | +0.017 [−0.11, +0.14] | **0.611** | **+0.038** | 5 |
| `trend_ground_b_o3mini` (round 1) | 0.635 | −0.007 [−0.08, +0.06], 6/8 | 0.620 | −0.012 [−0.11, +0.09] | 0.559 | −0.014 | 3.1 |
| `closed_book_o3mini` | 0.575 | −0.068 [−0.13, −0.01], 6/17 | 0.542 | −0.090 [−0.16, −0.02] | 0.483 | −0.090 | 1 |
| `closed_book` (Llama) | 0.488 | −0.155 [−0.22, −0.10], 2/21 | 0.312 | −0.319 [−0.46, −0.19] | 0.441 | −0.132 | 1 |

**What round 3 shows on dev3.**
- **On their own, the writer-level changes do nothing.** Forecasting framing, recalled analogies, high reasoning
  effort and MBR alone are all within ±0.03 of the replicate.
- **Evidence without a forecast step (R5) is the only single change ahead on both judges.** DeepSeek +0.07, GPT-5.6
  +0.02, neither significant.
- **Combining evidence with MBR (R6) is the best on GPT-5.6 and core.** GPT-5.6 +0.045, core +0.038, 16 of 24
  papers up. It is not significant, and DeepSeek is only +0.02.
- **The replicate reproduces the incumbent:** 0.642 vs 0.632.

**F3 decision (rule 11.1, recorded 2026-10-25 11:51, before any test3 result was seen).**
- F3 = `text_chunks_mbr_b_o3mini`: the highest dev3 GPT-5.6 score (0.688), above the replicate (0.642). No other
  configuration is within 0.01.
- F3 uses o3-mini like the incumbent, so no extra model control is needed.
- test3 runs: `closed_book`, `writer_only_b_o3mini`, `trend_ground_b_o3mini` and F3.
- **Primary:** F3 − `writer_only_b_o3mini` on test3.
- **Secondary (Holm):** F3 − `closed_book`, `writer_only_b_o3mini` − `closed_book`, `trend_ground_b_o3mini` −
  `closed_book`.

### 11.7 test3 results (pre-registered in 11.1 and 11.6; run once on 2026-10-25)

**Integrity.** 4 configurations × 36 units × 2 samples = 288 runs, all `--final`, 0 failures. All are judged by
GPT-5.6 and DeepSeek; the audits and the gate are in 11.9. No test3 title, query or target was read before these
runs.

**test3, 12 fresh papers (GPT-5.6 primary).**

| Configuration | GPT-5.6 | DeepSeek | core GPT | core DS | intervention | condition | mechanism | outcome | design / understanding | calls/run |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| `closed_book` (Llama-3.3, baseline) | 0.50 | 0.33 | 0.45 | 0.29 | 0.33 | 0.38 | 0.57 | 0.72 | 0.51 / 0.49 | 1 |
| **`writer_only_b_o3mini`** (incumbent) | **0.58** | **0.51** | **0.49** | **0.47** | 0.29 | 0.63 | **0.68** | 0.72 | 0.50 / **0.62** | 1 |
| `trend_ground_b_o3mini` (round 1) | 0.51 | 0.40 | 0.38 | 0.33 | 0.19 | 0.50 | 0.56 | 0.78 | 0.46 / 0.53 | 3.2 |
| `text_chunks_mbr_b_o3mini` (F3) | 0.54 | 0.44 | 0.40 | 0.39 | 0.26 | 0.64 | 0.53 | 0.71 | 0.48 / 0.56 | 5.4 |

**Pre-registered comparisons (test3).** Each cell is the paired difference, its 95% CI and papers up/down; Holm
runs across the three secondaries.

| Comparison | GPT-5.6 | DeepSeek | core GPT | core DS |
|---|---|---|---|---|
| **Primary: F3 − `writer_only_b_o3mini`** | **−0.045 [−0.15, +0.06]**, 5/6, p = 1.0 | −0.08 [−0.18, +0.04], 3/8 | −0.09 [−0.19, +0.01], 3/7 | −0.08 [−0.17, +0.01] |
| F3 − `closed_book` | +0.04 [−0.09, +0.18] | +0.10 [−0.02, +0.24] | −0.06 [−0.21, +0.13] | +0.10 [−0.04, +0.27] |
| `writer_only_b_o3mini` − `closed_book` | +0.08 [−0.01, +0.17], Holm 1.0 | +0.18 [+0.08, +0.29], Holm 0.12 | +0.04 [−0.08, +0.16] | +0.18 [+0.07, +0.31] |
| `trend_ground_b_o3mini` − `closed_book` | +0.01 [−0.09, +0.11] | +0.07 [0.00, +0.14] | −0.08 [−0.22, +0.06] | +0.04 [−0.06, +0.13] |

**Verdict.**
- **The round-3 improvement does not replicate.** F3 was +0.045 on dev3 (24 papers) and is −0.045 on test3, below
  the incumbent on both judges and on core.
  - Its mechanism agreement is 0.53, against the incumbent's 0.68. A likely cause, not verified: corpus evidence
    pulls the hypothesis toward what earlier papers did.
  - The incumbent is again the best configuration on fresh papers, on both judges.
- **Three fresh held-out sets now agree.** 28 papers in total: test 4, test2 12, test3 12. This analysis is
  exploratory, with different target extractors (`final3_heldout28_exploratory.json`).

  | Comparison | GPT-5.6 | DeepSeek |
  |---|---|---|
  | `writer_only_b_o3mini` − `closed_book` | **+0.11 [+0.05, +0.19]**, 20 of 26 papers with a difference up, sign p = 0.009 | **+0.27 [+0.17, +0.39]**, 23/4, p = 0.0003 |
  | `trend_ground_b_o3mini` − `closed_book` | +0.07 [0.00, +0.14] | +0.20 [+0.10, +0.31] |
  | `trend_ground_b_o3mini` − `writer_only_b_o3mini` | −0.05 [−0.12, +0.03] | −0.07 [−0.16, +0.02] |

  Means over the 28 papers (GPT-5.6 / DeepSeek):

  | Configuration | GPT-5.6 | DeepSeek |
  |---|---:|---:|
  | Llama baseline | 0.49 | 0.32 |
  | **o3-mini + conservative writer** | **0.60** | **0.59** |
  | Round-1 harness | 0.55 | 0.52 |

### 11.8 Summary of round 3: could it be increased further?

| # | Change | Inspired by | Failure targeted | dev3 effect (vs replicate) | Held-out effect | Kept? Why |
|---|---|---|---|---|---|---|
| 25 | Development on 24 papers instead of 8 (spent test + test2) | round-2 lesson | dev overfitting | – | – | Yes: tighter dev intervals, though still not enough (see #31) |
| 26 | Forecasting framing (R1) | S11, C12 | F15, F16, F18 | −0.03 | – | No |
| 27 | Self-recalled analogies (R2) | C10 | F15, F18 | −0.00 | – | No |
| 28 | High reasoning effort (R3) | S12 | all | −0.00 | – | No |
| 29 | Medoid of 5 samples, alone (R4) or over mixed prompts (offline) | S9 | variance | +0.00; offline −0.01 | – | No |
| 30 | Question-retrieved evidence without a forecast (R5) | C11, B5 | F17 | +0.02 (DeepSeek +0.07) | – | Only as part of #31 |
| 31 | **Evidence + medoid of 5 (R6, F3)** | combination | F17 + variance | **+0.045**, 16/8 papers | **test3 −0.045** vs incumbent | **No.** It did not replicate |
| 32 | Target-free selectors (offline: query overlap, length, numbers, consensus, hedging) | C7 | selection headroom (oracle 0.99 vs mean 0.64) | within-unit ρ −0.03 to +0.03 | – | No signal to build on |

**Bottom line of round 3.**
- **No further increase was found.** Seven new configurations, two offline checks and a dev set three times
  larger produced one dev winner (+0.045, not significant). That winner fell below the incumbent on 12 fresh
  papers.
- **The best-supported method is still o3-mini with the conservative writer, one call per hypothesis.** Across 28
  fresh held-out papers it scores 0.60 against 0.49 for the Llama baseline (GPT-5.6, p = 0.009) and 0.59 against
  0.32 on DeepSeek. Every added step (forecasting, grounding, decision rules, selection) helps on dev at most and
  fails on fresh papers.
- **Why it plateaus.** Points are lost on the specific intervention (below 0.5 of 4 everywhere), and the right
  answer is often among the candidates (oracle 0.99). But no target-free signal identifies it, and corpus evidence
  biases hypotheses toward what earlier papers did rather than what new papers do.
- **What would be needed:**
  - a real verifier: experiments, or simulations such as CALPHAD or DFT checks on candidate interventions;
  - a better pre-cutoff model: none available beyond o1 and o3-mini, and gpt-4o is rate limited;
  - a judge calibrated against experts, which might change what "better" means.
- **Process lesson** (added to must_obey.md 6.5): spend a fresh held-out set only on a dev gain over the
  *incumbent* whose CI excludes zero. Both dev winners that failed on fresh papers had CIs against the simpler
  incumbent crossing zero: round 1 vs the plain writer +0.06 [−0.03, +0.16], round 3 +0.045 [−0.01, +0.10].

### 11.9 Integrity, style and the must_obey.md checklist for round 3

- **Integrity.** `must_obey_check.py --loop` passes on all 10 directories involved:
  - the 7 round-3 configurations;
  - the 4 test3 configurations, 216 runs each (dev3 144 + test3 72; `closed_book` also has its 72 original-split
    runs).

  All have 0 failed runs and zero leakage counters, and every test3 run is final. Two warnings are the known
  one-month margin cases for Llama-3.3: PMC10759803 (dev) and PMC11302478 (test3, 1 day).
- **Exception (must_obey.md 6.7, not met in full).** The 1,008 round-3 dev3 runs all have GPT-5.6 and DeepSeek
  judgments. Only F3's 144 are audited, and none are labelled.
  - GPT-5.6 throughput fell to 2–37 calls a minute under shared rate limits, so the remaining roughly 1,700 calls
    were not made.
  - Selection used only the two judges; audits and labels are descriptive.
  - All 288 test3 runs are audited. The round-3 dev3 results are therefore not "clean" under 6.7, and the round-3
    claims rest on test3.
- **Style (test3).**

  | Configuration | length (characters) | hedges | specificity |
  |---|---:|---:|---:|
  | `closed_book` | 512 | 0.01 | 0.19 |
  | `writer_only_b_o3mini` | 1,150 | 0.07 | 0.24 |
  | `trend_ground_b_o3mini` | 1,206 | 0.12 | 0.22 |
  | F3 | 1,240 | 0.15 | 0.28 |

  - F3 is longer, slightly more hedged and more specific than the incumbent, yet scores lower. The incumbent's lead
    is not a style effect.
  - On test3, GPT-5.6 rewards length somewhat within configurations (ρ +0.10 to +0.26), unlike on test2. Since
    the shorter incumbent wins, this works against it rather than for it.
  - Its margin over the Llama baseline (about 640 characters shorter) should be read with that in mind; the
    DeepSeek margin is larger still.

**Checklist.**
- [x] Query-facing models are pre-cutoff (o3-mini, Llama-3.3). gpt-4o was not used because its probe could not run.
- [x] Queries are frozen: v3.1 for dev, test2 and test3 built once by pre-registered rules, all hash-checked.
- [x] Evidence: date-filtered corpus pools only; no web or live API tools in any method.
- [x] Payloads are target-free. Final hypotheses are restricted to schema fields (new); the recalled analogies
  never reach the judge.
- [x] Development on dev3 only, with test and test2 spent and declared. test3 was used once for configurations
  fixed before any test3 result was seen.
- [x] Same budgets and samples as the baselines. Declared differences: calls per run (MBR 5) and reasoning effort
  (R3).
- [~] Both judges on every run; audits on all test3 runs and F3's dev3 runs only (exception above); integrity gate
  passes.
- [x] Paired statistics with clustered-bootstrap CIs and Holm. Negative results are recorded: R1–R4, F3 on test3,
  and two offline checks.
- [x] Experiment log (experiments 27–28), READMEs and loop.md updated.

---

## 12. Sensitivity: what happens to the score when inputs are increased or decreased (experiment 29)

### 12.1 Pre-registered plan (written 2026-10-25 20:20, before any run of this experiment)

**Question.** Holding the recommended configuration fixed (o3-mini, conservative writer WRITER_B), how does the
GPT-5.6 reconstruction score respond to one input at a time? This is a characterisation, not a method search.
Every factor below changes the evidence budget or the reasoning budget on purpose (must_obey.md 6.1, declared).

| Factor | Levels | What varies | Configurations |
|---|---|---|---|
| **A. Number of papers as context** | N = 0, 1, 3, 10, 30 | The top-N most relevant earlier papers, one card per paper (cards are paper summaries, capped at 3,200 characters), ranked by the shared retriever against the question | N = 0 is the closed-book incumbent (`writer_only_b_o3mini` plus its replicate, 4 samples); `papers_n{1,3,10,30}_b_o3mini` |
| **B. Amount of raw text** | 0, 4k, 16k, 64k characters | Top-ranked text chunks (1,600-character cap each), with the record limit scaled with the budget | 0 = closed-book; 16k = `text_chunks_b_o3mini` (round 3); `text_{4k,64k}_b_o3mini` |
| **C. Relevance vs volume** | 10 relevant vs 10 random papers | The same N, with cards chosen at random (seed fixed per case) instead of by relevance | `papers_random10_b_o3mini` vs `papers_n10_b_o3mini` |
| **D. Reasoning effort** | low, medium, high | o3-mini `reasoning_effort` | `writer_only_b_o3mini_low`, closed-book (medium), `writer_only_b_o3mini_high` (round 3) |
| **E. Detail in the question** (existing runs, no new calls) | broad, problem, expert | The query level | The incumbent on all 36 papers |

**Data.** dev3 (24 papers × 3 levels × 2 samples). Evidence pools are date-filtered and family-excluded as always.

**Analysis.**
- **Trend test (primary, factors A and B).** Within each paper, average the score per dose, then take Spearman's ρ
  between dose and score. The statistic is the mean ρ over papers; its p-value comes from permuting dose labels
  within papers (10,000 permutations, fixed seed).
- **Effect sizes.** Paired differences of every dose against N = 0, with paper-clustered bootstrap CIs.
- **Also reported:** DeepSeek, core, the four dimensions, and input size and calls.
- **Factor C:** relevant − random, paired.
- **Factor D:** low and high vs medium.

**Decision rule.**
- A factor counts as "affecting the score" if its trend p < 0.05 on GPT-5.6 and DeepSeek agrees in sign.
- Only then is factor A re-run on test3 (12 papers, spent but unused for this question) as a replication of the
  trend's sign.
- No dose becomes a new recommended method from this experiment alone. That would need a dev gain with a CI
  excluding zero and a fresh held-out set (must_obey.md 6.5).

### 12.2 Replication on test3, decided after the dev3 results (written 2026-10-25 21:06, before any test3 run of these configurations)

The pre-registered trend rule (12.1) was not met: no factor has a monotone trend. dev3 instead shows a significant
*dip* when 1–3 paper cards are added (12.3). This is a new, post-hoc hypothesis. It is tested once on test3, whose 12
papers were not used to form it; closed-book runs already exist there.
- **Hypotheses.** On test3, GPT-5.6 reconstruction is lower than closed-book (`writer_only_b_o3mini`) with N = 1
  and with N = 3 paper cards, and does not differ with N = 30. DeepSeek is reported alongside.
- **Configurations.** `papers_n1_b_o3mini`, `papers_n3_b_o3mini` and `papers_n30_b_o3mini`, run once on test3
  with `--final`. Holm runs across the three comparisons.

### 12.3 Results on dev3 (24 papers × 3 levels × 2 samples; 1,152 new runs, 0 failed)

Dose 0 (closed-book) pools the incumbent and its replicate (4 samples per unit). All runs are judged by GPT-5.6 and
DeepSeek.

**A. Papers given as context (one card each).**

| Papers | GPT-5.6 | Δ vs 0 [95% CI], papers up/down | DeepSeek | Δ DeepSeek [95% CI] | core GPT | intervention | condition | mechanism | outcome | input chars/run |
|---|---:|---|---:|---|---:|---:|---:|---:|---:|---:|
| 0 | 0.637 | – | 0.631 | – | 0.576 | 0.38 | 0.57 | 0.77 | 0.83 | 1,833 |
| 1 | 0.533 | **−0.10 [−0.18, −0.03]**, 6/17 | 0.363 | **−0.27 [−0.41, −0.14]** | 0.448 | 0.28 | 0.49 | 0.62 | 0.75 | 4,907 |
| 3 | 0.535 | **−0.10 [−0.16, −0.04]**, 8/14 | 0.398 | **−0.23 [−0.34, −0.13]** | 0.448 | 0.25 | 0.53 | 0.65 | 0.71 | 13,251 |
| 10 | 0.568 | −0.07 [−0.14, +0.00], 6/15 | 0.493 | **−0.14 [−0.25, −0.03]** | 0.483 | 0.30 | 0.57 | 0.67 | 0.74 | 47,018 |
| 30 | 0.632 | −0.01 [−0.09, +0.08], 11/12 | 0.547 | −0.08 [−0.22, +0.04] | 0.573 | 0.37 | 0.58 | 0.78 | 0.80 | 139,383 |

Monotone trend: GPT-5.6 ρ = +0.01 (p = 0.95); DeepSeek +0.07 (p = 0.54). The response is U-shaped, not monotone.

**B. Raw text (characters of the top chunks).**

| Characters | GPT-5.6 | Δ vs 0 [95% CI], papers up/down | DeepSeek | Δ DeepSeek [95% CI] | core GPT | intervention | condition | mechanism | outcome |
|---|---:|---|---:|---|---:|---:|---:|---:|---:|
| 0 | 0.637 | – | 0.631 | – | 0.576 | 0.38 | 0.57 | 0.77 | 0.83 |
| 4,000 | 0.606 | −0.03 [−0.11, +0.04], 11/13 | 0.627 | −0.00 [−0.14, +0.13] | 0.503 | 0.28 | 0.57 | 0.73 | 0.85 |
| 16,000 (round-3 R5) | 0.658 | +0.02 [−0.04, +0.09], 11/12 | 0.705 | +0.07 [−0.04, +0.19] | 0.542 | 0.38 | 0.65 | 0.71 | 0.90 |
| 64,000 | 0.648 | +0.01 [−0.07, +0.09], 12/11 | 0.724 | +0.09 [−0.03, +0.21] | 0.580 | 0.35 | 0.59 | 0.81 | 0.84 |

Monotone trend: GPT-5.6 ρ = +0.05 (p = 0.66); DeepSeek +0.22 (p = 0.058).

**C. Relevance vs volume (10 papers).** The 10 most relevant papers minus 10 random papers: GPT-5.6 −0.04
[−0.10, +0.03] (9/15 papers); DeepSeek +0.03 [−0.07, +0.13]. Choosing the relevant papers does not matter.

**D. Reasoning effort.** Low −0.01 [−0.04, +0.02] and high +0.00 [−0.04, +0.06] against medium (GPT-5.6); DeepSeek
−0.00 and +0.02. Effort does not matter.

**E. Detail in the question** (incumbent, 36 papers, existing runs).

| Question level | GPT-5.6 | DeepSeek |
|---|---:|---:|
| broad | 0.58 | 0.57 |
| problem | 0.63 | 0.57 |
| expert | 0.64 | 0.64 |

The within-paper trend is not significant: GPT-5.6 ρ = +0.12 (p = 0.34); DeepSeek −0.04 (p = 0.77). The Llama
baseline shows the same small rise, 0.44 → 0.51 → 0.52 (p = 0.11).

**Why a few papers hurt: anchoring (target-free check).** Measure: the share of the hypothesis's content words
(intervention, mechanism, starting material) that appear in the top-ranked paper's card. Configurations that did not
see that card give the chance level.

| Papers given | Words borrowed from the top card | GPT-5.6, above / below the median borrowing |
|---|---:|---|
| 0 (never saw it) | 0.20 | 0.60 / 0.67 |
| 1 | **0.30** | 0.46 / 0.61 |
| 3 | 0.27 | 0.48 / 0.59 |
| 10 | 0.23 | 0.51 / 0.63 |
| 30 | 0.22 | 0.56 / 0.71 |
| 10 random (top card not given) | 0.20 | 0.62 / 0.59 |

- With one card, the hypothesis borrows about 50% more of it than chance, and hypotheses that borrow more score
  lower.
- As more papers are added, borrowing falls back toward chance and the score recovers. No single earlier paper
  dominates, so the model relies on its own prior, which is the closed-book level.
- Raw chunks are fragments rather than whole-study summaries, so they anchor less: 4k characters −0.03, against
  −0.10 for one card.
- **Not a selector (offline).** Within units of about 45 o3-mini candidates, similarity to the top prior paper does
  not predict score (ρ −0.04 to −0.06). Picking the least similar candidate scores 0.58–0.62 against a pool mean
  of 0.62.

### 12.4 Replication on test3 (12 papers; hypotheses of 12.2)

| Papers given | GPT-5.6 (closed-book 0.580) | Δ [95% CI], papers up/down | DeepSeek (closed-book 0.514) | Δ DeepSeek [95% CI] |
|---|---:|---|---:|---|
| 1 | 0.479 | **−0.10 [−0.19, −0.02]**, 3/8, Holm 0.45 | 0.309 | **−0.21 [−0.33, −0.08]** |
| 3 | 0.476 | **−0.10 [−0.20, −0.01]**, 2/10, Holm 0.12 | 0.285 | **−0.23 [−0.37, −0.10]** |
| 30 | 0.510 | −0.07 [−0.16, +0.00], 3/6 | 0.351 | **−0.16 [−0.31, −0.06]** |

- **The dip replicates.** With 1 and 3 papers the effect sizes match dev3 almost exactly: GPT-5.6 −0.10 and −0.10
  (dev3 −0.10, −0.10); DeepSeek −0.21 and −0.23 (dev3 −0.27, −0.23). The bootstrap CIs exclude zero. With 12 papers
  the sign tests are not significant after Holm.
- **The recovery at 30 papers is weaker on test3.** GPT-5.6 is −0.07, and DeepSeek −0.16 with a CI excluding zero.
  So the hypothesis that 30 papers "do not differ" is not supported on DeepSeek.

**All 36 papers (dev3 + test3, exploratory pooling).**

| Papers given | GPT-5.6 Δ vs none [95% CI], papers up/down, sign p | DeepSeek Δ [95% CI], sign p |
|---|---|---|
| 1 | **−0.10 [−0.16, −0.05]**, 9/25, p = 0.009 | **−0.25 [−0.35, −0.15]**, p = 0.009 |
| 3 | **−0.10 [−0.15, −0.05]**, 10/24, p = 0.024 | **−0.23 [−0.32, −0.15]**, p = 0.001 |
| 30 | −0.03 [−0.09, +0.04], 14/18 | **−0.11 [−0.21, −0.02]**, p = 0.11 |

### 12.5 Answer: what changes the score when it is increased or decreased?

| Input | Change | Effect on the score | Confidence |
|---|---|---|---|
| **Research papers given as context** (summaries) | 0 → 1 or 3 papers | **Down by 0.10 (GPT-5.6, −16%) and 0.24 (DeepSeek, −40%)** | Replicated on 12 independent papers; pooled over 36, sign p ≤ 0.024 on both judges |
| | 3 → 10 → 30 papers | Recovers toward the no-paper level but never exceeds it: GPT-5.6 −0.03 at 30; DeepSeek still −0.11 | The recovery is weaker on test3 |
| Raw text excerpts | 0 → 4k → 16k → 64k characters | No significant change (GPT-5.6 −0.03 to +0.02). DeepSeek drifts up to +0.09 (trend p = 0.058) | dev3 only |
| Relevance of the papers | 10 most relevant vs 10 random | No difference (−0.04 [−0.10, +0.03]) | dev3 only |
| Reasoning effort (o3-mini) | low → medium → high | No change (±0.01) | dev3 only |
| Detail in the question | broad → problem → expert | Small rise (0.58 → 0.64), not significant within papers (p = 0.34) | 36 papers |

**Why.**
- **Anchoring.** Given one paper, the hypothesis borrows about 50% more of that paper's wording than chance: 30% of
  its content words versus 20%. Hypotheses that borrow more score lower.
- **The answer is not in the earlier literature.** Experiment 18's evidence ceiling was 1–2 of 4 even with oracle
  retrieval. A new paper does something its predecessors did not, so a predecessor's study is the wrong template.
  This is also why relevance does not help (C) and why more text is at best neutral (B).
- **More papers dilute the anchor without adding the missing information.** Borrowing falls back to chance at 30
  papers, and the score returns toward, but not above, the closed-book level.

**Practical consequence.** For this task, more papers in the context do not raise the score. A few paper summaries
lower it significantly, and the best configuration remains the closed-book conservative writer.

### 12.6 Integrity, style and checklist (experiment 29)

- **Integrity.** `must_obey_check.py --loop` passes on all 8 directories with no warnings: 1,368 runs (1,152 dev3
  + 216 test3), 0 failed, zero leakage counters, and every test3 replication run is final. Every run is judged by
  GPT-5.6 and DeepSeek and has a target-free audit.
- **Style (must_obey.md 6.8).** Hypothesis length changes little across doses: 1,176 characters closed-book; 1,254,
  1,258, 1,263 and 1,371 with 1, 3, 10 and 30 papers. Length does not predict score within configurations
  (ρ −0.05 to +0.03, except +0.20 for random-10) or overall (ρ −0.004). The one-paper dip comes at almost the same
  length, so it is not a length effect. Hedges rise slightly with evidence (0.15–0.22 vs 0.12).

**Checklist.**
- [x] Query-facing model is pre-cutoff (o3-mini at low, medium or high reasoning effort).
- [x] Queries are frozen (v3.1, test2 and test3; hash-checked).
- [x] Evidence comes from date-filtered, family-excluded corpus pools; no web or API tools; leakage counters are
  zero.
- [x] Payloads are target-free; final hypotheses contain only schema fields; judging is blinded.
- [x] Plan pre-registered (12.1). The test3 replication was decided after dev3, declared post hoc and written down
  before its run (12.2).
- [x] Budgets are the declared variable (evidence characters and records, reasoning effort). Samples are the same
  as the baselines (2 per unit; 4 for the pooled closed-book reference).
- [x] GPT-5.6 judge, DeepSeek cross-judge and target-free audit on every run; integrity gate passes.
- [x] Paired statistics with clustered-bootstrap CIs, a permutation trend test and Holm for the replication.
  Negative results recorded (B, C, D, E; the offline selector).
- [x] Experiment log (experiment 29), loop README and loop.md updated.

---

## 13. Expert evaluation of the judge (experiment 30)

### 13.1 Pre-registered design and analysis (written 2026-10-26 04:34, before any item was selected or rendered)

**Why.** Every conclusion so far rests on GPT-5.6 scoring how close a hypothesis is to one paper's result. The two
judges agree only weakly (ρ = 0.39), and the materials expert's earlier feedback was that outputs did not make
sense. A human calibration is the most valuable next step. The package for the expert is in
[expert_evaluation/](./expert_evaluation/); the key and analysis are in
`experiments/high_temperature_hea_qwen35b/expert_eval/`.

**Items: 20 questions × 3 hypotheses = 60 items.**
- **Papers.** 10 of the original 12 (answer keys built from experiment 3), 5 of test2 and 5 of test3 (answer keys
  extracted by GPT-5.6). They are drawn at random within each set with seed 20261026; every one of these sets is
  already spent.
- **Question.** The `problem_constrained` level: it names the material and the limitation, which an expert needs to
  judge plausibility.
- **Three hypotheses per question, all for that question.**
  1. The recommended configuration, `writer_only_b_o3mini`, sample 1.
  2. The Llama-3.3 baseline, `closed_book`, sample 1.
  3. A **reference**: the paper's actual study, rewritten by GPT-5.6 as a forward-looking proposal in the same
     field schema (future tense, approximate rather than exact values, nothing added). It is the positive control.
     If GPT-5.6's judge gives the rewrite an intervention score below 3, the rewrite is redone once (a construction
     rule, recorded).
- **Blinding.** Questions are in random order and relabelled Q01–Q20. Within each question the three sources are
  labelled A, B, C by a balanced scheme: each of the 6 orders is used 3–4 times, assigned at random.
  - No model names, run IDs, paper IDs or titles appear in Part 1.
  - A target-free scan found no source-revealing meta statements in the 72 candidate hypotheses (only 2 scientific
    uses of "benchmark"), so nothing is redacted.
- **Judge scores for all 60 items.** GPT-5.6 and DeepSeek already scored the 40 generated items with the same
  prompt; the 20 references are scored the same way.

**What the expert does.**
- **Part 1, blind.** For each question, rate each hypothesis for plausibility, testability and usefulness (1–5).
  For the question itself, rate whether it makes sense (1–5) and guess which hypothesis is closest to what the
  authors did.
- **Part 2, after Part 1 is finished.** With the answer key and the paper link, rate each hypothesis's agreement
  with the paper on intervention, conditions, mechanism and outcome (0–4, the judge's four dimensions). Per
  question, rate the answer key's accuracy (1–5) and whether the question hints at the answer (no, slightly,
  strongly).

**Analysis, fixed now.**
- **Primary: is the judge valid?** Spearman ρ between the expert's agreement (mean of the 4 dimensions) and GPT-5.6
  reconstruction, over the **40 generated items**, with a question-clustered bootstrap 95% CI. References are
  excluded from the primary, because they would inflate ρ.
  - Interpretation: ρ ≥ 0.6, the judge tracks the expert; 0.3–0.6, partially; below 0.3, judge-based conclusions
    are not reliable.
- **Secondary.**
  1. ρ per dimension and for DeepSeek, and ρ over all 60 items.
  2. Per question: does the judge order the two generated hypotheses the same way as the expert? (sign agreement,
     ties excluded).
  3. Does the expert confirm the main result? o3-mini − Llama on agreement and on Part-1 quality, paired by
     question (bootstrap CI, sign test).
  4. Ceiling: the expert's and the judges' scores for the references; a judge mean well below 4 means a compressed
     scale.
  5. Answer-key accuracy by extractor (experiment 3 vs GPT-5.6).
  6. Question quality and human-rated leakage (the share of "strongly" hints).
  7. Identification of the reference against chance (1/3, binomial test).
- **Partial completion.** Questions are rated in order; any completed prefix (for example Q01–Q10) is analysed
  as is.

### 13.2 Construction (2026-10-26) and status

- **Package.** [expert_evaluation/](./expert_evaluation/) has a start page, a page of rating scales, 20 Part-1 pages,
  20 Part-2 pages, one-page versions for printing, and an Excel rating sheet with drop-down lists (plus CSV
  versions). Every page has step-by-step instructions.
- **Key, judge scores and analysis.** In
  [experiments/high_temperature_hea_qwen35b/expert_eval/](./experiments/high_temperature_hea_qwen35b/expert_eval/README.md).
- **References.** The first rendering kept methods-section detail (die size, rotation speed, exact values), against
  the pre-registered "approximate values" rule, and would have let the expert spot the real study by style. The
  prompt was tightened and all 20 re-rendered before release; there was no expert data, and no score was used.
  All 20 pass the fidelity rule at the first attempt.
- **Judges on the 60 items.** References: GPT-5.6 3.83, DeepSeek 4.00 (the judges' ceiling works). o3-mini writer:
  0.61 and 0.66. Llama baseline: 0.49 and 0.29.
- **Blinding check.** It passes: no model or source names anywhere; no paper identifiers in Part 1 or the sheet.
- **Status.** Awaiting the expert's ratings. Analyse them with `expert_eval_analysis.py <returned sheet>`.

---

## 14. SciMON-style user input (benchmark v4, experiment 31)

### 14.1 Pre-registered design (written 2026-10-26 05:34, before any v4 input was built)

**Request.** Build the user input the way SciMON does: Qingyun Wang, Doug Downey, Heng Ji and Tom Hope, *SciMON:
Scientific Inspiration Machines Optimized for Novelty*, ACL 2024, https://aclanthology.org/2024.acl-long.18.pdf (read
in full; sections 2.1–2.2 and appendices B.2 and C).

**What SciMON does (from the paper).**
- **Background context M** (§2.2): a scientific sentence classifier (Cohan et al. 2019) labels the sentences of the
  paper's *abstract*. The Background sentences become M; the remaining Method and Objective sentences are the target
  sentences T.
- **Seed term v** (§2.2): a scientific information-extraction system (Ye et al. 2022) is run on T to find
  `[method, used-for, task]` relations, and one entity of the relation is the seed. The other entity, the target
  term, stays hidden. The paper's running example uses the task as the seed ("knowledge acquisition") and asks for
  the method.
- **Prompt** (appendix B.2.1, GPT-4): "Consider the following context: M In that context, which p can be used for v,
  and why?", where p is the type of the hidden entity (Method, Material, Task or Metric). There are no levels: one
  input per paper.
- **Gold test filter** (§2.2, appendix C):
  - drop instances whose background overlaps the ground truth (lowest-similarity tenth only);
  - drop cases with irrelevant background;
  - keep only instances whose target relation is salient to the paper's idea.

**Our v4 builder** (`query_builder_v4_scimon.py`), applied to all 36 case papers. All are spent (test3 was used for
the round-3 finals), so this is a comparison of input formats, not a method claim.
1. **M.** The abstract is split into sentences. o3-mini (pre-cutoff) labels each one Background, Objective, Method,
   Result or Other. M is the Background sentences, verbatim and in order. Code verifies that each is an exact
   abstract sentence.
2. **Seed.** From the non-background sentences T, o3-mini lists `[head, used-for, tail]` relations with entity types
   and ranks them by salience to the paper's main contribution. For the most salient relation:
   - the seed v is the **tail (task) entity**;
   - p is the head's type (Method or Material);
   - the head (method or material) stays hidden.

   This is the direction of SciMON's own example. The other direction would hand the model the intervention our
   judge scores. Code verifies that v is an exact span of T.
3. **Input.** "Consider the following context: {M} In that context, which {p} can be used for {v}, and why?"
   (SciMON's template, verbatim).
4. **Gold filter, our analogue.** The v3 leakage checker (GPT-5.6, sees the hidden target) and the lexical gate
   (answer-word overlap ≤ 10%) check the composed input.
   - If it fails, the next relation in salience order is tried, up to 3.
   - Text is never rewritten, because SciMON uses verbatim context.
   - A paper whose abstract has no Background sentence, or that fails all 3 tries, is **flagged**. Results are
     reported with and without flagged cases.
5. **Unchanged.** The hidden targets (must_obey.md 3.5), the generators' system prompts and output schema, and the
   judges. Only the user input changes, so v4 scores are comparable with v3.1 on the same papers.

**Runs.** 36 papers × 1 input × 2 samples with 4 configurations (288 runs, new root `loop_v4_scimon/`):
- `closed_book` (Llama-3.3 baseline);
- `closed_book_o3mini`;
- `writer_only_b_o3mini` (the recommended configuration);
- `text_chunks_b_o3mini` (question-retrieved evidence, the retrieval side of SciMON).

**Analysis, fixed now.**
- **Primary.** For each configuration, v4 − v3.1 GPT-5.6 reconstruction per paper, with v3.1 as the mean of its
  three levels. Paired over the 36 papers with a paper-clustered bootstrap CI and sign test; Holm across the 4
  configurations.
- **Secondary.**
  - v4 against each v3.1 level separately.
  - Ranking of configurations on v4 (o3-mini writer − Llama, and so on).
  - DeepSeek and core.
  - Leakage audit: answer-word overlap of v4 inputs against the v3.1 levels, and ρ(overlap, score) on v4
    (must_obey.md 3.6).
  - Results without flagged cases.
- **Interpretation rule.** If v4 scores rise, check the leakage audit before attributing the rise to the format.

### 14.2 Construction (2026-10-26)

Builder: [query_builder_v4_scimon.py](./query_builder_v4_scimon.py). Frozen inputs, with a README covering the
construction rule, flags and examples: [benchmark_v4_scimon/](./experiments/high_temperature_hea_qwen35b/benchmark_v4_scimon/README.md).

| | Count (of 36 papers) |
|---|---:|
| Clean (no flag) | **9** (dev 3, test 0, test2 4, test3 2) |
| `no_background`: no Background sentence in the abstract, so the input is the bare question | 14 (13 alone, 1 also `failed_gate`) |
| `failed_gate`: all tried inputs fail the leakage gate | 13 (11 steer toward the answer, 2 contain answer phrases) |
| `no_relation`: no usable relation, so the seed is "the stated problem" (passed the gate) | 1 |
| Pass the gate (including flagged inputs) | 23 |
| Relation used: most salient / second / none | 33 / 2 / 1 |
| Hidden side: method / material / none | 18 / 17 / 1 |
| Mean answer-word overlap (v3 gate metric) | 2.3% (v3.1 on the same papers: broad 1.9%, problem 3.5%, expert 4.4%) |

*Correction, made after the runs:*
- The builder flagged the `no_relation` case (PMC12029629) `failed_gate` although its fallback input passed the gate.
  The flag logic is fixed and has a regression test.
- The case's flags were corrected; its input text, hash and runs are unchanged.
- The case was flagged either way, so the clean subset and the pre-registered analyses are unaffected. Only the
  exploratory flag groups (14.4) moved by one paper.

Two problems show up in HEA abstracts.
- **No background.** Many abstracts open with the paper's own work ("In this work, …"), so M is empty. The input
  becomes a one-line question such as "Which material can be used for ductility, and why?", the kind of question
  the expert earlier said does not make sense.
- **The seed names the study.** The salient task phrase comes from the paper's own objective sentence, so it often
  states the study design. Example: "… which method can be used for the effects of changing the percentage of
  elements of HfNbTaTiZr-HEA on the mechanical properties, and why?"

SciMON hit the same problem at scale: its gold filter kept 194 of 5,309 test instances (3.7%). Here 9 of 36 papers
(25%) give a clean input.

### 14.3 Results, pre-registered analysis (288 runs, 0 failed; both judges on every run)

Scores are mean reconstruction on the 0–4 scale, paired per paper. v3.1 is the mean of its three levels, on the
same papers. `closed_book_o3mini` and `text_chunks_b_o3mini` have v3.1 runs on 24 papers only (no test3).
Script: [v4_scimon_analysis.py](./v4_scimon_analysis.py); output
`experiments/high_temperature_hea_qwen35b/loop_v4_scimon/analysis.json`.

**Primary: v4 − v3.1 (GPT-5.6), with DeepSeek alongside.**

| Configuration | Papers | v4 | v3.1 | Δ GPT-5.6 [95% CI] | up/down | Holm p | Δ DeepSeek [95% CI] | Holm p |
|---|---:|---:|---:|---|---:|---:|---|---:|
| `closed_book` (Llama) | 36 | 0.47 | 0.49 | −0.02 [−0.14, +0.10] | 14/20 | 1.0 | **−0.13 [−0.24, −0.02]** | **0.045** |
| `closed_book_o3mini` | 24 | 0.70 | 0.58 | +0.12 [−0.07, +0.34] | 13/10 | 1.0 | −0.26 [−0.45, −0.07] | 0.11 |
| `writer_only_b_o3mini` | 36 | 0.69 | 0.62 | +0.08 [−0.09, +0.26] | 17/17 | 1.0 | −0.17 [−0.33, +0.01] | 0.11 |
| `text_chunks_b_o3mini` | 24 | 0.59 | 0.66 | −0.07 [−0.22, +0.09] | 8/15 | 0.84 | −0.33 [−0.50, −0.14] | 0.10 |

- **GPT-5.6: no significant change in any configuration.** Up and down papers are roughly balanced; the writer is
  17/17.
- **DeepSeek: v4 is lower in all four configurations.** The drop is significant after Holm for the Llama baseline,
  and on the core metric for `closed_book_o3mini` (−0.26 [−0.44, −0.08], Holm p = 0.010).
- **Core metric, GPT-5.6:** −0.01 to +0.14, none significant.
- **Without flagged cases** (9 papers; 7 for the 24-paper configurations):
  - GPT-5.6: +0.005, −0.06, −0.12, −0.10;
  - DeepSeek: −0.03, −0.33, −0.06, −0.39.

  There is no gain on clean inputs.
- **Against each v3.1 level** (GPT-5.6, writer): +0.12 vs broad, +0.07 vs problem, +0.06 vs expert, none
  significant. DeepSeek: −0.14, −0.15, −0.22.
- **Ranking on v4.** The input format does not change the ranking.

  | Comparison | GPT-5.6 | DeepSeek |
  |---|---|---|
  | o3-mini writer − Llama | +0.22 [+0.08, +0.38] | +0.23 [+0.10, +0.39] |
  | o3-mini closed-book − Llama | +0.18 [+0.05, +0.32] | +0.12 [−0.01, +0.26] |
  | writer − o3-mini closed-book | +0.04 [−0.07, +0.16] | +0.12 [−0.02, +0.26] |
  | evidence (`text_chunks`) − writer | −0.10 [−0.27, +0.06] | +0.02 [−0.17, +0.20] |

- **Leakage audit** (must_obey.md 3.6).
  - Answer-word overlap of v4 inputs is 2.3%, between v3.1 broad and problem.
  - ρ(overlap, v4 score) = 0.18, 0.26, 0.16, −0.05 for the four configurations: weak.
  - Lexical overlap misses the main leak, which is semantic (14.4).

### 14.4 Applying the interpretation rule: where the GPT-5.6 gains come from (exploratory, added after the results)

The pre-registered rule says to check leakage before crediting the format. Here v4 − v3.1 is split by the leakage
checker's verdict on the v4 input, by flag group, and by judge dimension. This split was not pre-registered; it is
in `analysis.json` under `exploratory_not_preregistered`.

**By checker verdict** (steers toward the answer: 11 papers; does not: 25. For the 24-paper configurations, 8 and
16.)

| Configuration | GPT-5.6, steers | GPT-5.6, does not steer | DeepSeek, steers | DeepSeek, does not steer |
|---|---|---|---|---|
| `closed_book` (Llama) | **+0.23 [+0.07, +0.40]** | −0.13 [−0.26, +0.01] | −0.08 | −0.15 [−0.29, −0.01] |
| `closed_book_o3mini` | +0.27 [−0.12, +0.68] | +0.05 | −0.10 | −0.34 [−0.54, −0.14] |
| `writer_only_b_o3mini` | **+0.29 [+0.03, +0.59]** | −0.01 | −0.02 | −0.24 [−0.43, −0.03] |
| `text_chunks_b_o3mini` | −0.06 | −0.07 | −0.20 | −0.39 [−0.60, −0.15] |

**By gate result, GPT-5.6 / DeepSeek.** Groups: clean (9 papers); flagged but passed the gate, i.e. no background
or no relation (14); failed the gate (13). For the 24-paper configurations, 7 / 8 / 9.
- **Clean:** GPT-5.6 +0.005 to −0.12.
- **Failed the gate:**
  - GPT-5.6 +0.16 to +0.21 for the three configurations without retrieval; Llama +0.21 [+0.03, +0.38].
  - DeepSeek −0.04 to −0.23.
- **Flagged but passed:**
  - GPT-5.6: Llama −0.24 [−0.39, −0.10]; o3-mini +0.13 to +0.22; retrieval −0.03.
  - DeepSeek −0.25 to −0.38.

**Condition agreement drops with both judges** (dimension score v4 vs v3.1).

| Configuration | GPT-5.6 | DeepSeek |
|---|---|---|
| `closed_book` (Llama) | 0.22 vs 0.38 (−0.16 [−0.30, −0.02]) | 0.06 vs 0.33 (−0.28 [−0.40, −0.16]) |
| `closed_book_o3mini` | 0.52 vs 0.54 | 0.19 vs 0.65 (−0.46 [−0.66, −0.24]) |
| `writer_only_b_o3mini` | 0.50 vs 0.57 | 0.36 vs 0.66 (−0.30 [−0.47, −0.13]) |
| `text_chunks_b_o3mini` | 0.44 vs 0.65 (−0.21 [−0.40, −0.01]) | 0.33 vs 0.83 (−0.49 [−0.65, −0.34]) |

On intervention, GPT-5.6 is +0.04 to +0.16 (none significant); DeepSeek is −0.02 to −0.35.

**Reading.**
1. **The only significant GPT-5.6 gains are on leaky inputs.** Llama and the writer gain on inputs whose seed
   carries the study's own objective (steering: +0.23 and +0.29, CIs above zero). Both judges rate steering inputs
   higher relative to non-steering ones.
   - On clean inputs, v4 is level with or below v3.1.
   - On flagged inputs that passed the gate, GPT-5.6 has o3-mini higher (+0.13 to +0.22, CIs cross zero). DeepSeek
     has them lower (−0.25 to −0.28), so that part is within noise.
2. **SciMON's context drops the operating conditions.** Abstract background sentences rarely give temperature,
   atmosphere or exposure time; v3.1's problem and expert levels do. For high-temperature alloys the conditions are
   part of the answer, so both judges mark condition agreement down.
3. **The judges disagree on the overall level** (GPT-5.6 flat, DeepSeek lower). This matches their weak agreement
   (ρ ≈ 0.39, section 13), and the expert ratings remain the arbiter.

### 14.5 Answer: is a SciMON-style input better for this task?

No. Applied to these 36 high-temperature HEA papers:
- **Coverage.** Only 9 papers give a clean input. 14 abstracts have no background, so the input is a bare one-line
  question. In 13 the input fails the leakage gate: 11 steer toward the answer, and 2 contain answer phrases.
- **Scores.** GPT-5.6 shows no significant change in any configuration, and DeepSeek scores v4 lower in all four.
  The only significant GPT-5.6 gains are on inputs that steer toward the answer.
- **Content.** The input loses the operating conditions, which matter for this topic.
- **Robustness.** The earlier conclusions do not depend on the v3.1 input format: o3-mini (writer or closed-book)
  beats the Llama baseline on v4 by the same margin or more, and retrieval still does not help.

**Decision.**
- v3.1 stays the main benchmark input.
- v4 is kept frozen as a SciMON-comparable variant. Its only leak-free subset is the 9 unflagged cases, too few for a
  claim on their own.

**What a SciMON-style input would need here** (not run):
- a background drawn from the introduction, not only the abstract;
- a seed taken from the problem statement rather than the paper's own objective sentence;
- a conditions slot.

Each moves it toward v3.1's problem-constrained level, which is what v3.1 already does with the checker.

### 14.6 Integrity, style and checklist (experiment 31)

- **Pre-registration.** Design and analysis were written (14.1) before any v4 input was built. The exploratory
  split (14.4) is labelled.
- **Models.** Query-facing models are pre-cutoff: o3-mini for sentence labels, relations and generation, and
  Llama-3.3. GPT-5.6 only checks inputs and judges, and never feeds a generator.
- **Inputs.** Inputs are frozen and hash-checked: `must_obey_check.py` maps each run's `benchmark` field
  (`v4_scimon`) to its query set.
- **Hidden targets.** Unchanged (tested in [test_v4_scimon.py](./test_v4_scimon.py)).
- **Runs and judging.** 288 runs, 0 failed. GPT-5.6 and DeepSeek judged all 288. Every run has a target-free audit
  and a lever label.
- **Integrity gate.** `must_obey_check.py --loop` passes on all 4 directories (72 runs each, 0 failed). The only
  warnings are the known one-month margin cases for Llama-3.3: PMC10759803 (2 days) and PMC11302478 (1 day), as in
  11.9.
- **Style (must_obey.md 6.8).** v4 hypotheses are shorter and less specific than v3.1 ones in every configuration.

  | Configuration | Length, v4 vs v3.1 (characters) | Audited specificity, v4 vs v3.1 | ρ(length, GPT-5.6) on v4 |
  |---|---|---|---:|
  | `closed_book` (Llama) | 265 vs 514 | 0.07 vs 0.26 | 0.39 |
  | `closed_book_o3mini` | 732 vs 1,120 | 0.11 vs 0.30 | 0.15 |
  | `writer_only_b_o3mini` | 845 vs 1,168 | 0.13 vs 0.29 | 0.04 |
  | `text_chunks_b_o3mini` | 971 vs 1,241 | 0.21 vs (8 audited v3.1 runs only) | −0.02 |

  Length is hypothesis + intervention + mechanism + predicted outcome, as in `loop_final.style_features`.
  - **Generic inputs, generic hypotheses.** The short background gives fewer alloy systems, temperatures and
    environments to build on, so hypotheses name fewer of them. This matches the drop in condition agreement
    (14.4).
  - **Not a length effect.** The GPT-5.6 rise for o3-mini comes despite shorter outputs, and for the recommended
    writer length does not predict the score (ρ = 0.04).
  - **Hedges.** Rare in both (0.01–0.13 per run).
  - **One abstention.** On the bare no-background input "Which method can be used for oxidation resistance, and
    why?", one Llama run answered that the method is unknown for lack of evidence and scored 0. It is counted, not
    dropped.
- **Splits.** All splits are spent (test3 in round 3), so this is a comparison of input formats on the same papers,
  not a method claim. A new method claim needs a fresh test4 (must_obey.md section 1).
- **Deviations from SciMON** (declared in 14.1 and the benchmark README):
  - task-side seed only;
  - an LLM labeller and extractor with verified spans, instead of trained models;
  - our leakage gate instead of a cosine filter;
  - flagged cases kept and reported;
  - lower-case p.
- Checklist:
  - [x] pre-registered;
  - [x] pre-cutoff query-facing models;
  - [x] leakage gate and audit, with ρ reported;
  - [x] both judges, a target-free audit and a lever label on every run; integrity gate passes;
  - [x] style check (length, hedges, specificity) reported;
  - [x] frozen, hash-checked inputs;
  - [x] results with and without flagged cases;
  - [x] exploratory analysis labelled;
  - [x] recorded in loop.md, the experiment log (experiment 31) and the READMEs.
