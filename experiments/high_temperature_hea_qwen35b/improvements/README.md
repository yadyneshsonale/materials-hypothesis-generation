# Improvements targeted at the experiment-15 failures, compared with the baselines

**Date:** 2026-10-23. **Script:** [improvement_eval.py](../../../improvement_eval.py) (tests in
`test_improvement_eval.py`; runner `run_improvements.sh`). **Tables:** [results/tables.md](results/tables.md).
**Data:** [results/analysis.json](results/analysis.json).

## Proposed improvements

Each improvement targets a failure found in the extraction-rubric failure analysis (experiment 15).

| Failure (experiment 15) | Proposed improvement | Run? |
|---|---|---|
| Closed-book prompt says "use only supplied evidence" with none supplied: one unit refuses, 76% of runs add a no-evidence caveat | **closed_book_fixed**: closed-book with its own prompt that allows the model's own pre-cutoff knowledge | Yes |
| Relevant prior work pulls in other systems' mechanisms; wrong mechanism in 69–87% of failures | **text_systemmatch / card_systemmatch**: before writing the hypothesis, the model appraises each record it may use (alloy system, conditions, how it differs from the target system, transfer verdict) and may use only mechanisms that transfer | Yes |
| Mechanisms from the model's own reasoning fail least | **knowledge_first**: draft from own knowledge (the closed_book_fixed run of the same sample), then revise with raw-text evidence used only to correct and test the draft | Yes |
| No arm wins most units (best–worst gap 0.68) | **ensemble_select**: the local model picks one of six blinded candidates per unit and sample (closed_book_fixed, text_chunks, card, both system-match arms, knowledge_first), without seeing the target | Yes |
| Broad queries fail 79–96% for every arm | Repair the benchmark (several valid targets, or drop the level). Reported separately here as non-broad scores | Analysis only |
| Mechanisms rubric's scope fields are the least faithful | Re-extract scope fields with per-field quotes and paraphrase checks | Not run |
| Large pools defeat lexical retrieval | Embedding retrieval or reranking | Not run |

## Design

**Baselines.** The experiment-14 runs and judgments: closed_book (original prompt), text_chunks, card and v2_units. The new
arms use the same:

- generator: Qwen3.5-35B-A3B, temperature 0.2, thinking disabled
- evidence pools, retrieval and 16,000-character budget (cards capped at 3,200 characters, others at 1,600)
- 12 papers × 3 query levels × 2 samples
- judges: GPT-5.6 and DeepSeek-V4-Pro, with the same blinding
- target-free GPT-5.6 audit

The only change in each new arm is the prompt, or for knowledge_first the extra step. The generation output cap is
7,000 tokens, up from 5,000, because the system-match JSON includes the appraisal. The ensemble's score for a unit
is the score of the candidate it chose; nothing is rejudged.

**Statistics.** Each unit is the mean of its two samples. Comparisons are paired by unit, with a paper-clustered
bootstrap (10,000 resamples, seed 20260421) and an exact sign test. Holm correction covers the five new arms against
text_chunks (the best evidence baseline). Comparisons with closed_book and on the non-broad levels are secondary.

**Integrity.**

- 288 of 288 new runs succeeded, all judged by both judges and audited; 72 selections, no fallbacks.
- Zero temporal violations, zero held-out-paper or family leaks, zero invalid citations, zero stage errors.
- Two system-match runs failed validation on the first pass. Each was retried once and succeeded; copies of the
  failed attempts are in `failed_attempts/`. Their two ensemble selections were deleted and redone with all six
  candidates.
- The selector's leak check initially rejected one selection because "card" appeared inside "discarded". The check
  now only looks for the distinctive arm identifiers (tested).
- Another job started on GPUs 0–2 during generation and halved throughput. This does not affect results.

## Results

Reconstruction (0–4; mean of two samples per unit, 36 units per arm, 35 for closed_book):

| Arm | GPT-5.6 | DeepSeek-V4-Pro | Non-broad (GPT-5.6) | broad | problem_constrained | expert_context |
|---|---:|---:|---:|---:|---:|---:|
| closed_book (baseline) | **1.65** | **2.20** | **2.06** | 0.77 | **1.68** | 2.44 |
| card_systemmatch | 1.62 | 2.02 | 2.02 | **0.81** | 1.42 | **2.62** |
| ensemble_select | 1.59 | 2.12 | 2.00 | 0.75 | 1.46 | 2.55 |
| text_systemmatch | 1.57 | 2.13 | 1.96 | 0.78 | 1.45 | 2.48 |
| text_chunks (baseline) | 1.56 | 2.00 | 2.00 | 0.67 | 1.50 | 2.50 |
| card (baseline) | 1.52 | 1.98 | 1.92 | 0.74 | 1.43 | 2.41 |
| v2_units (baseline) | 1.52 | 1.96 | 1.99 | 0.58 | 1.54 | 2.44 |
| closed_book_fixed | 1.49 | 1.97 | 1.84 | 0.79 | 1.34 | 2.33 |
| knowledge_first | 1.42 | 1.99 | 1.77 | 0.72 | 1.25 | 2.28 |

**Paired comparisons** (new arm minus baseline):

| Comparison | GPT-5.6 | 95% CI | DeepSeek-V4-Pro | 95% CI |
|---|---:|---|---:|---|
| text_systemmatch − text_chunks *(primary)* | +0.01 | −0.08 to +0.11 | **+0.14** | **+0.02 to +0.25** |
| card_systemmatch − text_chunks *(primary)* | +0.06 | −0.08 to +0.22 | +0.02 | −0.16 to +0.18 |
| ensemble_select − text_chunks *(primary)* | +0.03 | −0.10 to +0.17 | +0.12 | −0.03 to +0.27 |
| closed_book_fixed − text_chunks *(primary)* | −0.07 | −0.20 to +0.08 | −0.03 | −0.17 to +0.13 |
| knowledge_first − text_chunks *(primary)* | **−0.14** | **−0.26 to −0.00** | −0.01 | −0.15 to +0.14 |
| card_systemmatch − card | +0.09 | −0.03 to +0.24 | +0.04 | −0.16 to +0.23 |
| closed_book_fixed − closed_book | **−0.13** | **−0.25 to −0.00** | **−0.18** | **−0.31 to −0.06** |
| knowledge_first − its own draft (closed_book_fixed) | **−0.07** | **−0.13 to −0.01** | +0.02 | −0.07 to +0.10 |

No primary comparison survives the Holm correction (smallest Holm p = 0.11). Non-broad, knowledge_first is lower than
text_chunks in 10 of 10 papers that differ (−0.23, CI −0.35 to −0.13, GPT-5.6).

**Which method is best?**

- No improvement reliably beats the best baselines.
- The original closed-book is still highest under both judges.
- Among evidence-based methods, **system-match** is the only change that moves in the right direction under both
  judges for both representations:
  - text: +0.01 (GPT-5.6) and +0.14 (DeepSeek, CI excludes zero)
  - cards: +0.09 and +0.04 against plain cards
- **card_systemmatch** is the best evidence arm under GPT-5.6 (1.62), and the best of all arms on expert queries
  (2.62).
- The fixed closed-book and knowledge-first changes make things worse.

## Why

**1. System-match improves evidence use, as intended, but only partly controls transfer.**

| | text_chunks | text_systemmatch | card | card_systemmatch |
|---|---:|---:|---:|---:|
| Mechanism agreement | 1.53 | **1.62** | 1.50 | **1.64** |
| Evidence validity (judge) | 1.10 | **1.39** | 0.86 | **1.25** |
| Complete causal chain | 60% | 67% | 67% | 69% |
| Specificity checklist | 0.60 | **0.76** | 0.63 | **0.74** |
| Mechanism transferred, justified | 10% | **25%** | 6% | 11% |
| Mechanism transferred, unjustified | 58% | 49% | 47% | 57% |
| Supportive share of citations | 55% | 58% | 81% | **85%** |
| Hedge words per hypothesis | 0.04 | 0.49 | 0.11 | 0.53 |
| Hypothesis length (characters) | 456 | 958 | 449 | 1,054 |

The appraisal shows how mismatched the earlier corpus is to each target. The model judged 53% of appraised records
"does_not_transfer", 39–42% "partially" and only 5–8% "transfers". It mostly respected its own verdicts: 3 of 210
citations (text) and 17 of 179 (cards) were records it had judged non-transferable. So system-match makes the model
more selective and its mechanisms better grounded. It does not change how often the final mechanism is classed as
transferred without justification on cards, and it roughly doubles hypothesis length and adds some hedging.

**2. Closed-book's "prompt conflict" was helping it.** The fixed prompt removed the refusal and cut the
no-evidence caveat from 76% to 15% of runs, yet scored lower (−0.13 and −0.18).

| Dimension (GPT-5.6) | closed_book | closed_book_fixed |
|---|---:|---:|
| Intervention reconstruction | **1.83** | 1.51 |
| Problem alignment | **3.40** | 3.22 |
| Conditions | **1.47** | 1.31 |
| Novelty | 1.90 | **2.31** |

Told to use its own knowledge freely, the model proposes bolder, more novel interventions, which match the target
paper less. The original cautious prompt kept proposals close to the query's own framing, and the target papers
mostly made those incremental changes. The benchmark rewards conservative, query-adjacent hypotheses. That is
worth knowing for both method design and benchmark design.

**3. Knowledge-first barely uses the evidence.** The final hypothesis shares 97% of its intervention words and 94% of
its mechanism words with the draft. Revision helped 12 of 72 samples and hurt 28. Knowledge-first inherits the
weaker closed_book_fixed draft (above) and adds little, so it is the lowest arm.

**4. The local selector has a strong position bias.** Candidates were shown in a shuffled order. The selector chose
the first one (C1) in 52 of 72 cases (72%, against about 17% expected by chance). Its picks score 1.59, against
1.53 for a random pick among the same candidates and 1.93 for an oracle that picks the judge's best. Most of the
gain from combining arms is still untapped, and a 35B local model is not a reliable selector in this setup.

## Recommendations

1. **Adopt system-match appraisal with cards** as the default evidence path. It is the best evidence arm, improves
   mechanism agreement, evidence validity and specificity, and moves the right way under both judges. Add a rule
   against hedging in the hypothesis fields (as in the critique experiment).
2. **Keep the cautious closed-book prompt as the baseline**, and report that it is conservative. Treat "bolder
   proposals score lower" as a property of the benchmark: the hidden targets are mostly incremental.
3. **Don't use knowledge-first refinement** in this form.
4. **Fix the selector before relying on ensembles.** Present candidates pairwise in both orders (as the judge
   does), or use a stronger target-free selector. The oracle gap (1.93 vs 1.59) is the largest remaining
   headroom.
5. **Repair the broad level**, which still fails 71–88% for every arm.

## Limitations

- 12 papers and 36 units per arm. No primary comparison survives the Holm correction, and the two judges disagree
  on the size of the system-match effect (+0.01 vs +0.14 on text).
- The GPT-5.6 audit (mechanism source, chain, specificity) shares a family with the main judge.
- The system-match and knowledge-first arms use a 7,000-token output cap, against 5,000 for the baselines. In
  experiment 14, four baseline generations (two closed-book, two v2_units) hit the 5,000 cap on their first attempt.
  All four succeeded on retry, so every scored baseline run fit within the cap. The difference should not favour the
  new arms, but the caps are not identical.
- Ensemble scores reuse candidate judgments. The ensemble is not a separately generated hypothesis.
- Word overlap is a crude measure of how much knowledge-first changed its draft.

## Reproduce

```bash
tmux new-session -d -s mathg-improvements -c "$PWD" 'bash run_improvements.sh; exec bash'
.venv/bin/python improvement_eval.py report
.venv/bin/python -m unittest test_improvement_eval.py
```
