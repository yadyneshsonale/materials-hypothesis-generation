# loop.md: iterative method development on leak-free queries

Started 2026-10-25. Everything here follows [must_obey.md](./must_obey.md). Every run is checked by
`must_obey_check.py --loop`, and every number below is on the **dev split** (8 papers × 3 levels = 24 units, 2 samples
each) unless a section says *test*. The test split (4 papers) is touched only by the pre-registered final runs of
section 6, reported in section 7. Section 8 summarises what made a difference and why.

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
