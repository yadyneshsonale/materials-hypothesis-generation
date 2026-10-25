# loop.md: iterative method development on leak-free queries

Started 2026-10-25. Everything here follows [must_obey.md](./must_obey.md). Every run is checked by
`must_obey_check.py --loop`, and every number below is on the **dev split** (8 papers × 3 levels = 24 units, 2 samples
each) unless a section says *test*. The test split (4 papers) is touched only by the pre-registered final runs in
section 6.

**Code.**
- [hypo_loop.py](./hypo_loop.py): the harness, with rule enforcement, logging and evaluation.
- [loop_methods.py](./loop_methods.py): the methods.
- [test_hypo_loop.py](./test_hypo_loop.py): tests.
- [failure_clean.py](./failure_clean.py): the failure analysis.
- [query_builder_v3_1.py](./query_builder_v3_1.py): the benchmark fix.

**Outputs.** `experiments/high_temperature_hea_qwen35b/loop/<method>/` holds `runs/`, `judgments/{gpt56,deepseek}/`,
`audit/` and `labels/`. The reports are `report_dev.md` and `report_test.md`.

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

_Filled in section 7 (summary table)._

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

### Iteration 1: harness-controlled reasoning with a fixed weak model

_Results pending; see section 7._
