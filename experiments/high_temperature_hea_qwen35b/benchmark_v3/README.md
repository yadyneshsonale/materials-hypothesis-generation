# Benchmark v3: leak-free queries

Built 2026-10-23 by [query_builder_v3.py](../../../query_builder_v3.py) (tests:
[test_query_builder_v3.py](../../../test_query_builder_v3.py)). It replaces the experiment-3 queries, which leaked the
answer (experiment 19, [query_leakage/README.md](../query_leakage/README.md)). Design follows the published
benchmarks surveyed in [RELATED_WORK.md](../RELATED_WORK.md).

## What other benchmarks do, and what we adopt

| Benchmark | How the input is built | Leakage control | Adopted here |
|---|---|---|---|
| MOOSE-Chem (ICLR 2025) | Chemistry PhDs write the question and background survey | Written rule: the background may not contain any method from the hypothesis or its inspirations, and the question must not hint at the direction; a stricter variant removes directional hints | Rule given to the writer and enforced by the checker |
| ResearchBench (ACL Findings 2026) | LLM summarises the question and background from the introduction and related work | Undocumented prompt instruction; expert check of accuracy, not of leakage | Introduction as the only source |
| IdeaBench (2024) | Only the abstracts of the target's cited papers; the target paper is never shown | Leak-free by construction; answer paraphrased without numbers | Writer never sees the target |
| SCIMON (ACL 2024) | Background sentences of the abstract are the input; other sentences are targets | Similarity filter plus manual check, but only for the gold subset | Lexical gate on every query |
| MatDesign (NAACL Findings 2025) | Experts hand-write goal and constraints | None; several constraints name the answer's material | The lexical and checker gates exist to catch exactly this |
| All of the above | Papers published after the generator's training cutoff | Date cutoff | Pre-cutoff generator for the rerun |

## Procedure

1. **Source.** Only the held-out paper's Introduction. Sentences announcing the paper's own work ("in this
   study", "herein", "here we", "we propose…", "this study aimed…") and everything after the first of them are
   removed. 1–15 sentences were removed per paper; the remaining text is 2.0–8.4 k characters. The title, abstract,
   methods, results and conclusions are never shown.
2. **Writer** (GPT-5.6, never shown the target).
   - Writes broad, problem_constrained and expert_context questions under MOOSE-Chem's rule.
   - The background may mention earlier work on the problem and its limits.
   - No proposed material change, element, route, structure, phase, mechanism or value.
   - The question must not hint at the solution's class.
3. **Checker** (separate GPT-5.6 call, shown the query and the hidden target).
   - Lists every phrase revealing the intervention or its class, the structural mediator, the mechanism or a
     quantified outcome.
   - Judges whether the question steers toward the answer's class.
4. **Lexical gate.** The answer's intervention, mediator and mechanism words are compared with the query, after
   removing words that describe the allowed context (starting material, conditions, baseline). The share must be
   ≤ 10%.
5. **Rewrite.** Failing levels are rewritten with the checker's offending phrases (never the target), up to 4
   rounds.
6. **Answer key.** The hidden target is copied unchanged from the experiment-3 case, so old and new results are
   scored against the same answer.

## Result

| Level | Answer words in query, old (max) | New (max) | Passed gate |
|---|---:|---:|---:|
| broad | 7.6% (16.2%) | 2.4% (6.0%) | 12/12 |
| problem_constrained | 20.0% (27.3%) | 5.8% (11.6%) | 12/12 |
| expert_context | 46.9% (65.1%) | 5.4% (8.6%) | 10/12 |

These figures use the experiment-19 metric, with no allowed-word removal.

- Rounds needed: 1 (2 cases), 2 (7), 4 (3).
- The two expert queries that still fail are computational-method papers. PMC11355469's "intervention" is a
  molecular-dynamics study at several temperatures; PMC11606917's is a machine-learning potential with free-energy
  perturbation. Any honest description of their background points at simulation, and the checker kept flagging
  background the introduction legitimately contains. They are kept, flagged `passed_gate: false`, and results are
  also reported without them.

**Example, PMC10759803** (answer: add 4.2 at.% Cr to form a reticulated Laves network).

- Old expert query: "…addition of ~4 at.% of a specific transition metal (Cr) drives the formation of a complex
  multicomponent Laves phase…reticulated…".
- New expert query: earlier RHEA results (MoNbTaW, HfNbTaTiZr, as-cast HfMoTaTiZr at 10.21 g cm⁻³), then "Given
  the constraint that density must be reduced without sacrificing the strong room- and high-temperature mechanical
  performance of as-cast HfMoTaTiZr, what single intervention should be tested?"

## Files

- `cases/<paper>.json`: the new queries, gate results per level (`passed_gate`, `overlap`,
  `raw_overlap_exp19_metric`), the unchanged `hidden_target`, the source statistics and the old queries for
  comparison.
- `build_log/<paper>.json`: the redacted introduction and every writer and checker round.
- `memorisation_probe/`: the generator contamination probe ([memorisation_probe.py](../../../memorisation_probe.py)).

## Memorisation probe

Each generator saw only the held-out paper's title and year and was asked what the paper did and found. GPT-5.6
scored the recollection against the hidden target: 0 = wrong, 1 = generic or title-level, 2 = specific beyond the
title. There were 12 papers and 2 samples per model.

| Model (knowledge cutoff) | Claims to remember | Intervention | Structure | Mechanism | Numbers | Probes with a specific correct detail |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3.5-35B-A3B (released 2026-02; late 2025) | 0% | 1.08 | 0.71 | 0.88 | 0.08 | **33%** |
| Llama-3.3-70B (2023-12) | 0% | 0.83 | 0.67 | 0.96 | 0.04 | 8% |

Neither model claims to know any paper, and average recall is similar. But Qwen produced specific details beyond
what the title states four times as often as the pre-cutoff control. That is weak evidence of contamination, and
no evidence that it is absent. Together with Qwen's release date, it is why the rerun uses a pre-cutoff generator.
