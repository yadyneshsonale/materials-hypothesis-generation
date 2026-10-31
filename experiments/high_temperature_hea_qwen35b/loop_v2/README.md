# Experiment 42: six stage reviews, and the changes they support

**Plan.** [loop.md](../../../loop.md) section 23 (23.1 reviews, offline reproductions and pre-registered plan).
**Code.**
- Configurations: the experiment-42 section at the end of [loop_methods.py](../../../loop_methods.py).
- Helpers: [stage_v2.py](../../../stage_v2.py).
- Measurement v2: [judge_v2.py](../../../judge_v2.py).
- Offline checks: [v2_offline.py](../../../v2_offline.py).
- Analysis: [v2_analysis.py](../../../v2_analysis.py).
- Tests: [test_v2.py](../../../test_v2.py).

**Runners** (in [loop/](../loop/README.md)).
- `run_v2.sh` generated and started the evaluation.
- After the TRAPI block (loop.md 23.1 notes), `run_v2_resume*.sh` resumed it with the paced client. The last
  version, `run_v2_resume5.sh`, runs one runner per instance with at most 6 GPT-5.6 workers in total.

**Report.** `analysis_v2.md` and `analysis_v2.json`, regenerated with `python v2_analysis.py report`. The report
starts with a completeness section.

## The reviews

Six independent reviewer agents (rubber-duck), one per stage, each received the full project context, every failed
idea and the rules.

| Stage | Flaws found | Proposal | Decision after my reproduction ([offline/](./offline/)) |
|---|---|---|---|
| Retrieval | The question ranker counts the question template's words ("hypothesis", "evidence" in almost every question); titles are dropped from the evidence | BM25 without template words; section and action weights; titles and sections in the evidence | **Run** without the weights. Removing the template words alone raises the share of passages carrying the paper's lever from 16.9% to 19.4%; the weights add nothing |
| Writing | Undefined schema fields; invented numbers; a citation slip regenerates the whole hypothesis | Lock the question's stated facts; define conditions and outcome; no invented numbers | **Run** |
| Selection | My experiment-41 test merged the two samples per question (corrected in loop.md 22.2) | An o1 "next study" selector | Not run: expected 0 to +0.02 |
| Judging | No per-dimension anchors (the right kind of intervention earns less than the wrong kind); evidence visible; 3 question–key mismatches | Anchored, evidence-blind rubric | **Run as measurement v2**, validated before use; the original judge stays primary |
| Question | Labels mix study mode and lever | A checked decision card | Not run: no offline signal |
| Strategy | The memorisation probe cannot test local adapters | Gap analogs; later a trained forecaster | Not run: the analog signal did not reproduce (17.0% vs the reviewer's 25.9%) |

## Configurations (270 runs each: 45 papers × 3 levels × 2 samples; o3-mini, 1 call)

| Configuration | Writer | Evidence |
|---|---|---|
| `writer_v2_b_o3mini` | the best writer + the v2 writing block | none |
| `web64k_r2_b_o3mini` | the best writer | 64,000 characters by retrieval v2, with titles and sections |
| `web64k_v2_b_o3mini` (primary) | the best writer + the v2 writing block | the same as `web64k_r2` |

A citation slip drops the unknown IDs instead of regenerating the hypothesis.

## Results

Full statistics are in [loop.md](../../../loop.md) section 23.2 and in `analysis_v2.md`. GPT-5.6 is scored against
the baselines judged again in the same session.

**No stage change raises the score, and the writing block lowers it.**

| Comparison | GPT-5.6 [CI] | DeepSeek [CI] | Decision |
|---|---|---|---|
| Both changes (`web64k_v2`) vs writer (primary) | −0.027 [−0.08, +0.02] | −0.023 [−0.13, +0.08] | no detectable difference |
| Both changes vs the 64,000-character writer | −0.009 [−0.05, +0.03] | −0.104 [−0.20, −0.02] | no detectable difference |
| Writing block: `writer_v2` vs writer | −0.056 [−0.11, −0.01] | −0.069 [−0.13, −0.01] | lowers the score (not Holm-significant) |
| Retrieval v2: `web64k_r2` vs the 64,000-character writer | +0.016 [−0.02, +0.06] | −0.046 [−0.12, +0.02] | no detectable difference |
| Writing block with evidence: `web64k_v2` vs `web64k_r2` | −0.025 [−0.07, +0.02] | −0.057 [−0.14, +0.02] | no detectable difference |

- **The writing block.**
  - It cut invented numbers from 47% to 10% of hypotheses.
  - But DeepSeek's agreement fell on every dimension, most of all the intervention (−0.11).
  - Two explanations were checked and rejected: it did not suppress processing routes, and it did not remove hedged
    interventions.
- **Retrieval v2.** It raised the share of passages carrying the paper's lever only from 15.5% to 16.9% at 64,000
  characters.
- **Citation slips.** Most dropped citations were the right passage, with its section label rewritten by the model.
  Filtered runs did not score consistently lower.
- **Quality without the answer key.** `web64k_v2` is strongly preferred to the closed-book writer: DeepSeek +0.33
  (39/2 papers), o1 +0.44 (38/0). The 64,000-character writer earned the same in experiment 39, so the evidence,
  not the v2 changes, brings the quality.
- **Measurement v2.**
  - DeepSeek passes the controls and gives monotonic partial credit, but fails re-test (ρ 0.75 < 0.80): not
    validated.
  - GPT-5.6 could not be evaluated (capacity limits).
  - Under DeepSeek v2 the writer's lead over the Llama-3.3 baseline nearly disappears (0.37 vs 0.35). The expert
    ratings should settle this.
- **Leakage: none detected.** All counters are zero, and 25,036 web-record reads were re-checked against each
  paper's date. The audits were still running when this was written (loop.md 23.2).
- **Recommended generator unchanged:** `web_text_64k_b_o3mini`.

## Checklist (must_obey.md section 9)

- [x] Query-facing models are pre-cutoff (o3-mini); o1 is used only as a target-free judge.
- [x] Frozen questions; prompts fixed before the runs (loop.md 23.1).
- [x] Date-filtered evidence, re-checked; target-free payloads; pairwise judgments in both orders.
- [x] Spent papers only (exploratory); same budgets as the baselines.
- [x] GPT-5.6 and DeepSeek judgments on every run; same-session baselines; target-free quality reported.
- [ ] Lever labels and audits on every run: still running when this was written (loop.md 23.1 finalisation rule).
- [x] Paired statistics with CIs and Holm; negative results recorded; `must_obey_check.py` passes.
