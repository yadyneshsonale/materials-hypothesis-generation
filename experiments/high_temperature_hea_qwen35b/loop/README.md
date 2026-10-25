# Experiment 24: harness-engineered method loop and pre-registered test

**Date.** 2026-10-25.
**Code.**
- [hypo_loop.py](../../../hypo_loop.py): harness and evaluation.
- [loop_methods.py](../../../loop_methods.py): methods.
- [loop_analysis.py](../../../loop_analysis.py): decision diagnostics.
- [loop_final.py](../../../loop_final.py): pre-registered analysis and style checks.
- [test_hypo_loop.py](../../../test_hypo_loop.py): tests.

**Rules.** [must_obey.md](../../../must_obey.md). **Full write-up, sources and results.** [loop.md](../../../loop.md).

## Configuration

- **Benchmark:** v3.1, frozen. The 12 held-out papers are split into dev (8) and test (4); each unit is a paper ×
  level (3 levels), with 2 samples.
- **Generators:** pre-cutoff only. Llama-3.3-70B (temperature 0.2), o3-mini and gpt-4o-mini.
- **Evidence:** the experiment-21 pools, temporally filtered, with a 16,000-character budget.
- **Judging:** GPT-5.6 reconstruction (primary, 0–4) and the DeepSeek-V4-Pro cross-judge. GPT-5.6 also does the
  target-free audit and the lever labels (analysis only).
- **Harness:** `Harness.guard` blocks target text in every payload, and every call is logged with its role and
  model.
- **Development:** iterations 1–5 on dev only, 29 configurations, each tied to a failure from experiment 22 and a
  cited source.
- **Pre-registration:** the finalists and the analysis were fixed in loop.md section 6 before any test run. Test
  was run once.

## Results

- **Dev:** the best configuration is `trend_ground_b_o3mini`. It frames the question, forecasts the next step from
  a chronological chain of earlier papers, retrieves aimed evidence and writes conservatively. GPT-5.6 0.73 vs 0.51
  for Llama closed-book (+0.22, CI +0.12 to +0.31).
- **Test (pre-registered primary):** +0.125 (CI +0.04 to +0.23); every test paper up; DeepSeek +0.52 (CI +0.30 to
  +0.84).
- **Gain decomposition (test):** intervention agreement does not improve (core +0.02). The gain is in condition,
  mechanism and outcome. GPT-5.6 does not reward length (within-configuration ρ −0.17 to −0.36).
- **All 12 papers:** +0.19 (CI +0.11 to +0.27); 11 of 12 papers up; sign p = 0.006.
- **Did not replicate:** the best Llama configuration (`scaffold_ensemble`) went from +0.10 on dev to −0.09 on
  test.
- **Reports:** `report_{dev,test,all}.md`, `final_{dev,test,all}.json`, `final_robustness.json` and
  `decision_diagnostics_dev.json`.

## Integrity

- `must_obey_check.py --loop` passes on all 29 method directories: 0 failed runs and zero leakage counters. Test
  runs are marked `final` and target-free asserted.
- The only warning is the known PMC10759803 margin (2 days after Llama's cutoff) for the 16 Llama configurations.
- Runner scripts: `run_baselines.sh`, `run_batch.sh` and `run_final.sh`. `logs/` and `errors/` are not committed.

## Limits

- 12 papers in total (4 on test), so the intervals are wide.
- The judges disagree, and DeepSeek partly rewards length.
- The judge is not calibrated against experts.
- The query writer is post-cutoff.
- All test questions are understanding questions under v3.1.
- 29 configurations were tried on dev, so dev numbers are optimistic.
