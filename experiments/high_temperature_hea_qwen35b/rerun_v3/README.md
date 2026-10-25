# Experiment 21: all evaluations rerun on leak-free queries with a pre-cutoff generator

Run 2026-10-23/24. Runner: [run_clean_rerun.sh](../../../run_clean_rerun.sh); factorial:
[run_factorial.sh](../../../run_factorial.sh); comparison: [compare_rerun.py](../../../compare_rerun.py)
(`comparison/tables.md`, `comparison/analysis.json`).

## What changed and why

| | Original runs (experiments 7–17) | This rerun |
|---|---|---|
| Queries | Experiment-3 queries, written by Qwen in the same call that saw the held-out paper's results; 47% of the answer's words appear in expert queries (experiment 19) | [benchmark_v3](../benchmark_v3/README.md): introduction only, writer never sees the answer, separate leakage checker, lexical gate; 5% at the expert level |
| Generator | Qwen3.5-35B-A3B, released 2026-02, after the held-out papers (2024-01 to 2026-02); recalled specific details beyond the title in 33% of probes | Llama-3.3-70B-Instruct (TRAPI), knowledge cutoff 2023-12, before every held-out paper; 8% |
| Unchanged | Hidden targets, corpus and temporal filters, evidence pools and budgets, extractions of pre-cutoff papers, judges (GPT-5.6, DeepSeek-V4-Pro), target-free audit, statistics | same |

**Why Llama.**

- gpt-4o (cutoff October 2023, used by MOOSE-Chem and IdeaBench) was rate-limited at the time: 1 success in 8
  requests.
- Llama-3.3 was the strongest pre-2024 model with a stable quota. Its cutoff had already been checked for
  experiment 11.
- Azure's Llama accepts only one tool definition per request, so agent tools are wrapped into a single `act`
  tool ([llm_client.py](../../../llm_client.py), tested).

**Other leakage paths checked.**

- **Citation-graph search phrases** are now written by the pre-cutoff generator from the clean query. Before, the
  post-cutoff Qwen wrote them from the leaky query.
- **Ensemble selection, knowledge-first refinement and the critique reviser** also run on the pre-cutoff
  generator. The critics were already pre-cutoff.
- **Extractions of pre-cutoff papers** (v2 evidence units, rubric records, citation-graph cards and citer
  statements) are reused, and new citation-graph papers are extracted with the same Qwen extractor. The extractor
  never sees a query or a target, so it could leak only by writing knowledge of a later paper into an earlier
  paper's record. This was measured with [extractor_leakage_audit.py](../../../extractor_leakage_audit.py)
  (`extractor_leakage/analysis.json`), and there is no sign of it:

  | Records (case × record pairs) | With an answer word not in their own source | Control: other cases' answer words | Ratio |
  |---|---:|---:|---:|
  | v2 evidence units (2,999) | 0.76% | 0.93% | 0.81 |
  | Rubric cards (556) | 2.09% | 2.84% | 0.74 |
  | Rubric effects (6,098) | 0.41% | 0.58% | 0.72 |
  | Rubric mechanisms (4,287) | 1.11% | 1.18% | 0.94 |
  | Rubric gaps (4,349) | 0.53% | 0.55% | 0.96 |
  | Citation-graph cards (354) | 3.75% | 2.64% | 1.42 |
  | Citer statements (12,633) | 0.00% | 0.01% | 0.00 |

  - An "answer word" is a stem of the hidden target's intervention, mediator, mechanism or outcome. Stems of its
    starting material, conditions and baseline, of the v3 query, and those found in more than 20% of corpus
    papers are removed.
  - A memorising extractor would inject the true case's answer words more often than other cases' words. The
    ratios are at or below 1, except citation-graph cards (14 versus about 9 expected records).
  - All 14 of those hits are generic words (arise, converge, double, drive, enable, hour, negligible, pinning,
    relieve, sensitive, variant); none carries the answer's specific content.
  - Word variants are matched by a suffix stemmer, so reticulated, reticulation and reticulate count as one word.
- Temporal, test-paper, work-family, target DOI/title and invalid-citation audits are all zero in every rerun.

## Integrity

| Experiment | Runs ok / expected | Judged | Notes |
|---|---|---|---|
| 7 eval_v3 | 144/144 | 144 absolute, 108 pairwise | verified |
| 9 MatKG | 36/36 KG runs (+144 copied baselines) | 180 absolute, 144 pairwise | verified |
| 11 critique | 72/72 revisions; resample control 35/36 | 36/36/36/35 | One resample run (PMC12298864 expert) ended without a valid submission after 16 turns, twice, and stays failed. One revision crashed on a null citation list and succeeded on retry; the cause is fixed at the source (`_validate_generation` now normalises null or string ID lists, with a regression test). |
| 14 rubrics | 576/576 | 576 GPT-5.6, 576 DeepSeek, 576 audits, 84 ceilings | verified |
| 16 improvements | 288/288 + 72 selections | 288 / 288 / 288 | verified |
| 17 citation graph | 360/360 (12 graphs rebuilt from the clean queries; 248 full-text papers, 119 newly extracted) | 360 / 360 / 360 | verified |
| Factorial cells | 144 + 144 | 288 absolute + pairwise | complete |

## Results

**Queries no longer leak.** Answer-word overlap fell from 8% / 20% / 47% (broad / problem / expert) to
2% / 6% / 5%.

**Scores collapse, and the level gradient disappears** (GPT-5.6 reconstruction, 0–4, mean of 36 units):

| Arm | Original | Rerun | Rerun broad / problem / expert | Rerun DeepSeek |
|---|---:|---:|---|---:|
| exp14 closed_book | 1.65 | **0.60** | 0.62 / 0.55 / 0.62 | 0.28 |
| exp7 closed_book | 1.56 | 0.57 | 0.56 / 0.50 / 0.65 | – |
| exp17 graph_profiles | 1.52 | 0.55 | 0.51 / 0.60 / 0.54 | 0.27 |
| exp16 ensemble_select | 1.59 | 0.54 | 0.50 / 0.56 / 0.56 | 0.27 |
| exp17 graph_selection | 1.52 | 0.54 | 0.46 / 0.60 / 0.54 | 0.22 |
| exp16 closed_book_fixed | 1.49 | 0.53 | 0.51 / 0.52 / 0.56 | 0.27 |
| exp16 knowledge_first | 1.42 | 0.53 | 0.50 / 0.53 / 0.56 | 0.23 |
| exp16 card_systemmatch | 1.62 | 0.49 | 0.48 / 0.55 / 0.45 | 0.20 |
| exp14 card | 1.52 | 0.48 | 0.39 / 0.51 / 0.53 | 0.20 |
| exp16 text_systemmatch | 1.57 | 0.48 | 0.49 / 0.47 / 0.49 | **0.32** |
| exp17 graph_profiles_systemmatch | 1.49 | 0.48 | 0.50 / 0.49 / 0.45 | 0.27 |
| exp14 text_chunks | 1.56 | 0.47 | 0.51 / 0.46 / 0.44 | 0.26 |
| exp17 corroboration_weighted | 1.49 | 0.47 | 0.47 / 0.50 / 0.44 | 0.28 |
| exp14 effects | 1.51 | 0.46 | 0.33 / 0.55 / 0.49 | 0.23 |
| exp17 graph_tool_agent | 1.52 | 0.46 | 0.41 / 0.44 / 0.54 | 0.12 |
| exp14 gaps | 1.48 | 0.45 | 0.45 / 0.47 / 0.44 | 0.15 |
| exp7 text_oneshot | 1.56 | 0.43 | 0.42 / 0.48 / 0.40 | – |
| exp14 mechanisms | 1.46 | 0.42 | 0.47 / 0.38 / 0.43 | 0.24 |
| exp7 v2_oneshot | 1.49 | 0.41 | 0.38 / 0.44 / 0.42 | – |
| exp7 tool_agent | 1.64 | 0.40 | 0.44 / 0.38 / 0.40 | – |
| exp14 mixed | 1.39 | 0.40 | 0.40 / 0.39 / 0.42 | 0.19 |
| exp14 v2_units | 1.52 | 0.38 | 0.31 / 0.45 / 0.39 | 0.16 |
| exp11 self_revise | 1.60 | 0.38 | 0.40 / 0.33 / 0.42 | – |
| exp11 tool_agent_resample | 1.55 | 0.36 | 0.25 / 0.44 / 0.39 | – |
| exp11 critique | 1.49 | 0.35 | 0.40 / 0.31 / 0.35 | – |
| exp9 tool_agent_kg | 1.63 | 0.35 | 0.29 / 0.38 / 0.40 | – |

- **Overlap no longer predicts the score.** Spearman correlation between answer overlap and score was 0.72–0.88 in
  the original runs; in the rerun it is −0.05 to 0.50 (median about 0.23).
- **Excluding the two gate-failed expert queries** changes no arm by more than 0.03.

**Factorial on experiment 7: the queries, not the generator, explain the drop.**

| Generator | Leaky queries | Clean queries |
|---|---:|---:|
| Qwen3.5 (post-cutoff) | 1.56 | 0.50 |
| Llama-3.3 (pre-cutoff) | 1.40 | 0.45 |

| Effect | Difference | 95% CI |
|---|---:|---|
| Queries, with Qwen (clean − leaky) | −1.07 | [−1.37, −0.77] |
| Queries, with Llama | −0.94 | [−1.18, −0.69] |
| Generator, on leaky queries (Llama − Qwen) | −0.16 | [−0.32, −0.005] |
| Generator, on clean queries | −0.04 | [−0.13, 0.03] |

About 90% of the original scores' advantage came from the answer being in the query. Generator contamination adds
at most about 0.1 (the Qwen advantage), which matches the weak memorisation-probe signal.

**Paired comparisons in the rerun** (36 units, paper-clustered bootstrap, sign test).

- Against text_chunks, with Holm correction over 17 arms, nothing survives:
  - closed_book +0.13 [0.02, 0.24], p = 0.04, Holm 0.66;
  - graph_profiles +0.08, p = 0.04, Holm 0.66;
  - ensemble_select +0.07;
  - v2_units −0.09 [−0.17, −0.01].
- Agents and critique against closed-book (exp 7):
  - critique −0.21 [−0.33, −0.11];
  - self_revise −0.19;
  - MatKG agent −0.21;
  - tool agent −0.17 [−0.28, −0.06].

**The agents are not really tested with Llama.**

| Agent | Tool calls per run | Runs with 0 calls | Records cited |
|---|---:|---:|---:|
| exp7 tool agent, original (Qwen, leaky) | 12.0 | 0 | 2.4 |
| exp7 tool agent, rerun (Llama, clean) | 2.1 | 9 of 36 | 0.9 |
| exp9 MatKG agent, rerun | 0.1 | 35 of 36 | 0.0 |
| exp7 tool agent, Qwen on clean queries | 11.9 | 0 | 2.1 |

Llama mostly answers without exploring, so the agent arms' low scores reflect the generator, not the agent
design. With Qwen on the clean queries the agent and the evidence arms are level with or slightly above
closed-book:

- text one-shot +0.10 [−0.13, 0.35];
- tool agent +0.08 [−0.13, 0.29];
- v2 one-shot +0.01.

With Llama they are below it. Whether evidence helps depends on the generator, and on clean queries no difference
in either direction is significant.

## What this means for the earlier conclusions

| Earlier conclusion | Status after the rerun |
|---|---|
| Expert queries score about 2.4 and broad about 0.7; query inferability drives scores (exp 12, 13, 15) | **Withdrawn.** It was leakage. On clean queries all three levels score about 0.45–0.6. |
| Closed-book is the best arm (exp 14–17) | **Weakened.** Still highest with Llama (0.60), not significantly so (Holm 0.66), and reversed in direction with Qwen (not significant). |
| Evidence and retrieval hurt on specific queries (exp 15, 18) | **Withdrawn** as stated. It was measured on queries that already contained the answer. |
| No rubric beats raw text (exp 14) | **Holds.** Card +0.01, other rubrics −0.01 to −0.09. |
| System-match helps (exp 16) | **Not confirmed.** +0.01 to +0.02 on GPT-5.6; text_systemmatch is highest on DeepSeek (0.32). |
| Citation-graph variants do not beat the corpus (exp 17) | **Holds**, but graph_profiles and graph_selection are now among the top arms (+0.07–0.08, not significant). |
| Critique and the KG agent do not help (exp 9, 11) | **Holds**, now partly confounded by Llama's minimal tool use. |
| Absolute ability | Every method reconstructs real 2024–25 results poorly (0.35–0.60 of 4). That is the honest baseline for future work. |

## Limits

- Twelve papers and 36 units. Paired intervals are wide, and nothing survives correction.
- The generator differs from the original runs. The factorial isolates the query effect only for experiment 7.
- The two gate-failed expert queries (computational-method papers) remain in the set and are reported separately.
- The judges and the hidden targets are unchanged and still contain exact values that no earlier literature can
  predict, which caps outcome scores.
- Llama's minimal tool use means the agentic arms need a pre-cutoff model that uses tools; gpt-4o, when its quota
  allows.

## Files

- `eval_v3/`, `eval_v4_matkg/`, `eval_critique/`, `rubric_eval/`, `improvements/`, `citegraph/`: the same
  structure as the original experiments.
- `factorial/llama_oldq/`, `factorial/qwen_newq/`: the off-diagonal cells.
- `comparison/`: the tables and analysis above.
- `extractor_leakage/`: the extractor leakage audit (summary, every flagged record with its injected word stems).
