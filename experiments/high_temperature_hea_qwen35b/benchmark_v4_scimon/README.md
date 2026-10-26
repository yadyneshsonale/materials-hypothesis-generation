# Benchmark v4: SciMON-style user input (experiment 31)

**Date.** 2026-10-26.
**Design.** Pre-registered in [loop.md](../../../loop.md) section 14.1.
**Rules.** [must_obey.md](../../../must_obey.md) 3.7.
**Code.**
- [query_builder_v4_scimon.py](../../../query_builder_v4_scimon.py): builds the inputs.
- [test_v4_scimon.py](../../../test_v4_scimon.py): tests.

## What SciMON does

Source: Qingyun Wang, Doug Downey, Heng Ji and Tom Hope, *SciMON: Scientific Inspiration Machines Optimized for
Novelty*, ACL 2024. https://aclanthology.org/2024.acl-long.18.pdf

- **Input.** The input is a *background context* M plus a *seed term* v.
  - M is the sentences of the paper's abstract that a scientific sentence classifier labels **Background**.
  - v is one entity of a `[method, used-for, task]` relation extracted (SciERC-style information extraction) from the
    abstract's other sentences. The other entity of the relation stays hidden.
- **Prompt.** "Consider the following context: M In that context, which p can be used for v, and why?", where p is
  the hidden entity's type. There is one input per paper.
- **Gold test set.** It drops instances whose background overlaps the ground truth, instances with irrelevant
  background, and instances whose relation is not salient. 194 of 5,309 test instances remained.

## Our procedure (all 36 case papers: dev, test, test2, test3)

1. **Abstract sentences.** Split from the JATS abstract, with citations removed.
2. **Sentence labels.** o3-mini (pre-cutoff) labels each sentence Background, Objective, Method, Result or Other.
   - M is the Background sentences, verbatim, in order.
   - Background sentences that announce the paper's own work are dropped (v3 self-reference sensor).
3. **Relations.** o3-mini lists up to 5 `[head used-for tail]` relations from the non-background sentences, ranked by
   how central they are to the paper.
   - The **seed is the tail (task)**, and p is the head's type (method or material).
   - Code keeps only exact spans whose seed does not contain the head.
4. **Input.** SciMON's template, verbatim. With no Background sentence, the input is the question alone: "Which p can
   be used for v, and why?"
5. **Leakage gate.** The v3 checker (GPT-5.6, sees the hidden target) and the lexical gate (answer-word overlap ≤ 10%).
   - On failure the next relation is tried, up to 3.
   - Text is never rewritten.
   - Flags: `no_background`, `failed_gate`, `no_relation`.
6. **Unchanged.** Hidden targets, splits and dates are copied unchanged. Only the user input differs from v3.1.

**Deviations from SciMON, declared.**
- **Seed side.** The seed is always the task side. SciMON uses both sides, but the other side would give the model
  the intervention that our judge scores; the task side is the direction of SciMON's own running example.
- **Models.** An LLM (o3-mini) does the sentence classification and information extraction, instead of SciMON's
  trained models. Spans are verified by code.
- **Leakage filter.** Our leakage checker and lexical gate replace SciMON's cosine-similarity filter. Cases are
  flagged rather than dropped, so all 36 papers can be compared.
- **Wording.** p is written in lower case ("which method …").

## Result of construction

| | Count (of 36) |
|---|---:|
| Clean (no flag) | **9** (dev 3, test 0, test2 4, test3 2) |
| `no_background`: the abstract has no Background sentence, so the input is the bare question | 14 |
| `failed_gate`: every tried input fails the leakage gate | 13 (11 steer toward the answer, 2 contain answer phrases) |
| `no_relation`: no usable relation, so the seed is "the stated problem" (passed the gate) | 1 |
| Pass the gate (including flagged inputs) | 23 |
| Mean answer-word overlap (v3 gate metric) | 2.3% (v3.1 on the same 36 papers: broad 1.9%, problem 3.5%, expert 4.4%) |
| Hidden entity type | method 18, material 17, none 1 |

A flag was corrected after the runs. The builder had marked the `no_relation` case (PMC12029629) `failed_gate`
although its input passed the gate. The logic is fixed and tested, and the input text is unchanged (loop.md 14.2).

Many alloy abstracts open with the paper's own objective ("In this work, …") and have no separate background. For
the others, the seed (a task phrase from the paper's own sentences) often names the study's design. Only a quarter
of the papers give a clean SciMON-style input. SciMON's own gold filter kept far fewer, 194 of 5,309 test instances
(3.7%), for related reasons: background that overlaps the answer, and relations that are not salient.

**Examples.**
- **No background.** The input is a bare one-line question: "Which material can be used for ductility, and why?"
- **Seed that names the study** (failed the gate): "… which method can be used for the effects of changing the
  percentage of elements of HfNbTaTiZr-HEA on the mechanical properties, and why?"

**A clean example** (test2): "Consider the following context: High-temperature self-lubricating materials with stable
tribological performance across a wide temperature range are essential for advanced mechanical systems under extreme
conditions. However, balancing mechanical strength and lubrication efficiency remains a key challenge. In that
context, which material can be used for high-performance wide-temperature self-lubricating materials, and why?"

## Files

| Path | Content |
|---|---|
| `cases/<paper>.json` | The v4 case: the input (`queries.scimon`), gate result, flags, background sentences, seed, hidden target |
| `cases_original12/` | Symbolic links to the 12 original cases (dev 8, test 4), the papers of the experiment-21 suite; used by experiment 32 |
| `build_log/<paper>.json` | All abstract sentences, labels, relations and every tried input with its check |
| `summary.json` | Construction counts |

Results: [loop.md](../../../loop.md) section 14 (experiment 31) and section 15 (experiment 32, every experiment
re-run on v4); runs in `../loop_v4_scimon/` and `../rerun_v4_scimon/`.
