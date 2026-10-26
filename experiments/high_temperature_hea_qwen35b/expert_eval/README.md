# Experiment 30: expert evaluation of the AI judge (internal: not for the expert)

> **For the research team only.** This folder holds the key that unblinds the expert package (which source wrote
> hypothesis A, B or C). The expert must not open it before returning the ratings. The expert's material is in
> [expert_evaluation/](../../../expert_evaluation/).

**Date.** 2026-10-26.
**Design and analysis.** Pre-registered in [loop.md](../../../loop.md) section 13.1 before any item was selected.
**Code.**
- [expert_eval_builder.py](../../../expert_eval_builder.py): builds the package.
- [expert_eval_analysis.py](../../../expert_eval_analysis.py): analyses a returned sheet.
- [test_expert_eval.py](../../../test_expert_eval.py): tests.

## Why

Every conclusion of experiments 21–29 rests on GPT-5.6 scoring a hypothesis's agreement with one paper. The two
judges agree only weakly (ρ = 0.39), and the materials expert's earlier feedback was that outputs did not make sense.
This experiment measures whether the judge tracks a materials expert.

## Items (20 questions × 3 hypotheses)

- **Papers.** 10 of the original 12 (answer keys from experiment 3), 5 of test2 and 5 of test3 (answer keys extracted
  by GPT-5.6). They are drawn at random within each set with seed 20261026; all of these sets are already spent.
- **Question.** The `problem_constrained` level; each hypothesis is sample 1 of its configuration.
- **Sources (hidden from the expert).**
  - `o3mini_writer`: `writer_only_b_o3mini`, the recommended configuration.
  - `llama_baseline`: `closed_book`, Llama-3.3.
  - `reference`: the paper's actual study, rewritten as a forward-looking proposal in the same schema by GPT-5.6.
    These are in `references/`. The rewriter is not query-facing (must_obey.md 2.4).
- **Order.** Questions are in random order (Q01–Q20). The six A/B/C orders are used 3–4 times each; every source
  appears 6–8 times in every position.

## Construction log

1. **Selection.** `key.json` was written by `expert_eval_builder.py select`, and is deterministic (tested).
2. **Meta-statement scan** of the 72 candidate generations (both configurations × 36 papers): no source-revealing
   phrases (2 scientific uses of "benchmark"), so nothing is redacted.
3. **References, first rendering (rejected, kept in `references_v1_rejected/`).**
   - The rewrites kept methods-section detail: die size, ball-to-powder ratio, rotation speed, instrument settings,
     exact property values.
   - That breaks the pre-registered "approximate rather than exact values" rule and would let the expert identify
     the reference by style.
   - The prompt was tightened: proposal-level parameters only, rounded, no equipment or procedural details, and
     250–400 words. All 20 were re-rendered.
   - This happened before any expert data existed, and not because of any score.
4. **References, final.**
   - All 20 pass the fidelity rule at the first attempt (GPT-5.6 intervention ≥ 3).
   - Length: median 470 words (418–528), close to the o3-mini hypotheses (median 455). The Llama hypotheses have a
     median of 187.
   - Two keep minor procedural detail ("high-purity powders"; a wear test's load, frequency and stroke). This was
     accepted as normal for a proposal.
5. **Blinding check** (`expert_eval_builder.py check`, also a unit test): no model, method or source words anywhere in
   the package; no paper ID, DOI or title in Part 1, the workbook or the CSVs.

## Judge scores of the 60 items (`judge_scores.json`)

| Source | GPT-5.6 reconstruction | DeepSeek | GPT-5.6 intervention |
|---|---:|---:|---:|
| reference (actual study, rewritten) | 3.83 | 4.00 | 3.90 |
| o3-mini writer | 0.61 | 0.66 | 0.55 |
| Llama baseline | 0.49 | 0.29 | 0.45 |

Both judges place the rewritten actual study near the top of the scale, so the judges' ceiling works. The open
question is whether the low scores of the AI hypotheses, and the order between them, match the expert's view.

## Files

| File | Content |
|---|---|
| `key.json` | For each question: the paper, set, split, level, sample, and for A, B and C the source, configuration and run ID |
| `references/<paper>.json` | The final reference rewrite with its GPT-5.6 and DeepSeek judgments and the fidelity check |
| `references_v1_rejected/` | The first renderings (rejected; see the construction log) |
| `judge_scores.json` | GPT-5.6 and DeepSeek scores (all 10 dimensions, reconstruction, core) for the 60 items |
| `analysis_<rater>.json`, `.md` | Written by the analysis script when a sheet is returned |

## When the ratings come back

```bash
./.venv/bin/python expert_eval_analysis.py expert_evaluation/5_returned_ratings/expert_ratings_<initials>.xlsx
# or the CSV folder: ./.venv/bin/python expert_eval_analysis.py path/to/csv_folder
```

The script implements the pre-registered analysis (loop.md 13.1). A partly completed sheet is analysed as is.

**Primary.** Spearman ρ between the expert's agreement (mean of the four 0–4 dimensions) and GPT-5.6 reconstruction
over the 40 generated items, with a question-clustered bootstrap CI.
- ρ ≥ 0.6: the judge tracks the expert.
- 0.3 to 0.6: partially.
- Below 0.3: judge-based conclusions are not reliable.

**Secondary.**
- ρ per dimension, for DeepSeek, and over all 60 items.
- Within-question order agreement.
- Expert-rated o3-mini − Llama (agreement and Part-1 quality).
- The reference ceiling.
- Answer-key accuracy by extractor.
- Question sense and hints.
- Identification of the reference against chance.

## Limits

- **One expert.** There is no inter-rater reliability; a second expert can rate the same package independently.
- **Small sample.** 40 generated items in 20 clusters give a wide CI on ρ.
- **The reference is a rewrite by GPT-5.6**, which is also the judge, so the ceiling check is partly circular.
  DeepSeek and the expert are independent of it.
- **The expert could identify the reference** by content (it is the real study). Part-1 quality ratings for the
  reference may therefore be biased; Part-1 comparisons between the two AI sources are not affected.
