# Experiment 39: why more information does not raise the score

**Plan.** [loop.md](../../../loop.md) section 20: 20.1 pre-registered diagnostic plan, 20.2 post hoc same-session
check, 20.3 results. **Code.**
- The diagnostic configurations at the end of [loop_methods.py](../../../loop_methods.py), tested in
  [test_diag.py](../../../test_diag.py).
- Labels, pairwise judges, re-test and report in [diag_analysis.py](../../../diag_analysis.py).

**Runners.** [loop/run_diag.sh](../loop/run_diag.sh) and [loop/run_diag_audits.sh](../loop/run_diag_audits.sh).
**Report.** [analysis_diag.md](./analysis_diag.md) and `analysis_diag.json`. **Progress.**
`python web_status.py loop_diag`.

## The question and the tests

"More information should give better results. Either the information is bad, or the model is not thinking and just
repeating it, or the judging is not fair."

| Explanation | Test |
|---|---|
| The information is bad | GPT-5.6 rates every passage the model saw against the answer key (`pack_labels/`), and every paper of the corpus (`corpus_labels/`). An oracle pack (`oracle_targetpack_b_o3mini`) uses the same retriever, corpus and budget, queried with the answer key; every passage is still dated before the paper |
| The model does not use it, or just repeats it | Uptake of the paper's lever when the evidence contains it; how many numbers and alloy names are copied from the evidence; a reading step (`oracle_targetpack_read_b_o3mini`, and the target-free `read_web_chunks_b_o3mini`) |
| The judging is unfair | Oracle hints (`oracle_hint_class/lever/full_b_o3mini`); a target-free pairwise quality judge (`pairwise/`: GPT-5.6, DeepSeek and o1, which cannot know the papers; both orders); a judge test-retest (`retest/`); same-session re-judging of the baselines (`same_session/`) |

**Oracle configurations use the answer key on purpose.** They are diagnostics, not methods (must_obey.md 5.4):
- every run records `oracle_diagnostic` and `target_free_asserted: false`;
- `must_obey_check.py` accepts them only with `--oracle`, and only in `oracle_*` directories;
- the hints are frozen in `oracle_hints.json`, written before any run.

## Results

All 45 papers are spent, so these are exploratory diagnostics. GPT-5.6 is shown first and DeepSeek second.

| Explanation | Finding | Key numbers |
|---|---|---|
| The information is bad | **Diluted, not missing** | The paper's lever is in 78% of 16,000-character packs and 93% of 64,000-character packs, but in only 16–18% of their passages. Evidence selected to match the paper (37% of passages on the lever) beats the normal evidence: +0.13 [+0.07, +0.20] (DeepSeek +0.09), and +0.10 over no evidence in the same session |
| The model does not use it | **It copies details, not the decision** | With the lever in the evidence, the lever is used only 0–9 points more often than without evidence. 46% of numbers and 52% of alloy formulas come from the evidence (controls: 19% and 31%). Told the lever directly, it uses it in 93% of runs. A reading step makes things worse (−0.04 to −0.05; DeepSeek −0.10 to −0.12) |
| The judging is unfair | **Consistent, but it measures one paper's study, not quality** | Given the right lever: 1.26 / 1.50 of 4. Given the whole answer key: 3.38 / 3.64. Without the answer key, all three judges prefer the evidence-based hypotheses (o1 in 41 of 45 papers, net +0.44), while reconstruction moves +0.01. Re-test ρ 0.84 / 0.91. GPT-5.6 drifted +0.04 between occasions |

**Answer.**
- More information does make better hypotheses, but the reported score measures how closely one paper's study is
  reconstructed.
- Information helps that score only when it points at the paper's own direction, and the model rarely picks that
  direction out of a pack of options; it copies the details instead.
