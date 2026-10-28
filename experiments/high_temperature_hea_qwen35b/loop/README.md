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

## Round 2 (experiment 26; loop.md section 10)

- **Dev.** 10 new configurations (480 runs), all compared with a fresh-sample replicate of the round-1 best
  (`trend_ground_b_o3mini_r2`, 0.719 vs the original 0.729):
  - niche occupation (`niche_ground_b_*`, `trend_niche_ground_b_o3mini`);
  - o1 (`*_o1`, `trend_o1_ground_b_o3mini`);
  - BM25 grounding (`trend_ground_bm25_b_o3mini`);
  - iterative retrieval (`trend_ground_iter_b_o3mini`);
  - relevance-focused grounding (`trend_focus_ground_b_o3mini`).

  All are lower (−0.05 to −0.16), so the pre-registered rule selected no new finalist.
- **test2** (12 fresh papers, `../benchmark_test2/`). [run_final2.sh](./run_final2.sh) ran 5 configurations once
  (360 runs). Analysis: `final2_test2.json`, `final2_test2_after_gpt56_cutoff.json`, `final2_robustness.json` and
  `final2_heldout16_exploratory.json` (`loop_final.py --round round2`).
- **Result.** The round-1 method beats the Llama baseline on test2 (+0.11 [+0.01, +0.22]), but o3-mini with the
  conservative writer alone is the best configuration: 0.65 vs 0.46 baseline, Holm p = 0.043. On the 5 papers
  after every model's cutoff it scores 0.76 vs 0.41.

## Round 3 (experiment 28; loop.md section 11)

- **Development set dev3.** dev plus the spent test and test2 splits: 24 papers, 72 units. The reference is a
  fresh-sample replicate of the incumbent (`writer_only_b_o3mini_r3`, 0.642).
- **Runs.** [run_batch3.sh](./run_batch3.sh) ran 7 configurations on dev3 (1,008 runs); comparison in
  `round3_dev3.json`:
  - `forecast_writer_b_o3mini`;
  - `analogy_writer_b_o3mini`;
  - `writer_only_b_o3mini_high`;
  - `writer_mbr_b_o3mini`;
  - `text_chunks_b_o3mini`;
  - `text_chunks_mbr_b_o3mini`;
  - the replicate itself.
- **Failure analysis.** `failure_r3.json` (with `failure_r3_codes.json`).
- **test3** (12 fresh papers, `../benchmark_test3/`). [run_final3.sh](./run_final3.sh) ran 4 configurations once
  (288 runs). Analysis: `final3_test3.json`, `final3_robustness.json` and `final3_heldout28_exploratory.json`
  (`loop_final.py --round round3`).
- **Result.**
  - The dev3 winner (evidence + MBR, +0.045) is −0.045 against the incumbent on test3.
  - Over 28 fresh papers, the incumbent (o3-mini with the conservative writer) is the best configuration: 0.60 vs
    0.49 baseline (GPT-5.6, p = 0.009).
- **Exception.** dev3 runs are judged by both judges, but only F3's are audited, and none are labelled (GPT-5.6 rate
  limits).

## Experiment 29: sensitivity (loop.md section 12)

- **Runs.** [run_sensitivity.sh](./run_sensitivity.sh) ran 8 configurations on dev3 (1,152 runs):
  - `papers_n{1,3,10,30}_b_o3mini`;
  - `papers_random10_b_o3mini`;
  - `text_{4k,64k}_b_o3mini`;
  - `writer_only_b_o3mini_low`.
- **Replication.** `papers_n{1,3,30}_b_o3mini` ran once on test3 (216 runs).
- **Analysis.** `sensitivity.json` (from [sensitivity.py](../../../sensitivity.py)), `sensitivity_test3_replication.json`
  and `sensitivity_pooled36.json`.
- **Result.** A few papers as context lower the score (−0.10 GPT-5.6, −0.24 DeepSeek over 36 papers), and 30 papers
  return toward the no-paper level. Raw text, relevance, reasoning effort and question detail have no significant
  effect.

## Experiment 31: SciMON-style input (loop.md section 14)

- **Runs.** [run_v4_scimon.sh](./run_v4_scimon.sh) ran `closed_book`, `closed_book_o3mini`, `writer_only_b_o3mini`
  and `text_chunks_b_o3mini` on benchmark v4 ([../benchmark_v4_scimon/](../benchmark_v4_scimon/README.md)) for all
  36 papers: 288 runs in a separate root, [../loop_v4_scimon/](../loop_v4_scimon/README.md). The runs in this folder
  are untouched.
- **Analysis.** [v4_scimon_analysis.py](../../../v4_scimon_analysis.py) writes `../loop_v4_scimon/analysis.json`.
- **Result.** No GPT-5.6 change against v3.1 is significant, and DeepSeek scores v4 lower. The only significant
  GPT-5.6 gains are on inputs that steer toward the answer. The ranking is unchanged: writer − Llama +0.22 (GPT-5.6)
  / +0.23 (DeepSeek).

## Experiment 32: every configuration on the SciMON-style input (loop.md section 15)

- **Runs.** [run_v4_all.sh](./run_v4_all.sh) ran the other 48 configurations on benchmark v4 for all 36 papers: 3,456
  runs in [../loop_v4_scimon/](../loop_v4_scimon/README.md). [run_v4_all_eval.sh](./run_v4_all_eval.sh) ran audits
  and labels alongside generation.
- **Analysis.** [v4_all_analysis.py](../../../v4_all_analysis.py) writes `../loop_v4_scimon/analysis_all.json` and
  `analysis_all.md`.
- **Result.** Rankings agree with v3.1 (ρ 0.77 GPT-5.6, 0.72 DeepSeek).
  - Nothing beats `writer_only_b_o3mini`.
  - The papers-as-context dip replicates, and is larger.
  - The writer's lead over Llama holds overall but not on the 9 clean v4 inputs.

## Experiments 34–35: changes suggested by two model reviews (loop.md section 16)

- **Runs.** [run_review_b.sh](./run_review_b.sh) ran seven configurations on the 36 spent papers (split `all36`):
  - the fresh replicate `writer_only_b_o3mini_r4`;
  - stronger writers `writer_only_b_4o`, `writer_only_b_41` and `writer_only_b_o4mini` (the last two on 29 papers);
  - few-shot `fewshot_similar_b_o3mini` and `fewshot_diverse_b_o3mini`;
  - `router_b_o3mini`.
- **Excluded models.** o3 and gpt-5 failed the memorisation probe, so their runs are kept unanalysed in
  [excluded_by_probe/](./excluded_by_probe/README.md).
- **test4 finals.** [run_test4_final.sh](./run_test4_final.sh) ran the test4 finals once (`writer_only_b_o3mini` and
  `closed_book`, split `test4`, marked final).
- **Analysis.** [review_analysis.py](../../../review_analysis.py), outputs in [../review_eval/](../review_eval/README.md).
- **Result.**
  - No configuration beats the incumbent.
  - The incumbent beats the Llama baseline on test4 (+0.12 / +0.26) and over all 37 fresh papers (+0.11, p = 0.003;
    DeepSeek +0.27).

## Experiment 36: web search for every baseline (loop.md section 17)

- **Generation.** [run_web.sh](./run_web.sh) ran the 30 analysed evidence configurations as `web_<name>`, with each
  question's web-search corpus in place of the fixed corpus, plus three web-search agents. That is 7,398 runs in
  [../loop_web/](../loop_web/README.md): the five primary-comparison configurations on all 45 papers, the others on
  all36. It started only after the corpus gate passed.
- **Evaluation** (loop.md 17.3). GPT-5.6 rate-limited nearly every call on the shared TRAPI instance, so:
  - [run_web_alt_eval.sh](./run_web_alt_eval.sh) and [run_web_alt_audit.sh](./run_web_alt_audit.sh) ran the GPT-5.6
    judge, audits and labels on a second instance of the same deployment;
  - [run_web_shared_audit.sh](./run_web_shared_audit.sh) added audits on the shared instance once it recovered;
  - [run_web_finish.sh](./run_web_finish.sh) finished the DeepSeek cross-judge after `run_web.sh` was stopped at the
    end of generation.
- **Result.** Web search helps no baseline (W1), and web corpora are no better than the fixed corpus (W2): see
  [../loop_web/analysis_web.md](../loop_web/analysis_web.md).

## Experiment 37: propose, critique, decide (loop.md section 18)

- **Generation.** [run_pcd.sh](./run_pcd.sh) ran the 16 configurations of the three-role method (proposer, critic,
  decider; optional web evidence at each role) on all 45 papers, 270 runs each, into
  [../loop_pcd/](../loop_pcd/README.md). It also completed two baselines on all 45 papers: `closed_book_o3mini` here
  (test3 and test4, 126 runs) and `web_text_64k_b_o3mini` in [../loop_web/](../loop_web/README.md) (test4, 54 runs).
- **Evaluation.** `run_pcd.sh` ran the GPT-5.6 judge and audits on both TRAPI instances, then the DeepSeek
  cross-judge, the Q6 labels and the report. Extra loops added throughput without changing what is evaluated (loop.md
  18.2):
  - [run_pcd_judges.sh](./run_pcd_judges.sh): judge-only loops;
  - [run_pcd_audits.sh](./run_pcd_audits.sh): audit-only loops in a seeded random job order;
  - [run_pcd_labels.sh](./run_pcd_labels.sh): the Q6 labels, started while the last audits ran.
- **Analysis.** [pcd_analysis.py](../../../pcd_analysis.py), outputs in [../loop_pcd/](../loop_pcd/README.md).
- **Result.** The three-role method is worse than one o3-mini call, with or without web evidence, and no better than
  the Llama-3.3 closed-book baseline.

## Experiment 38: round 4, synthesis (loop.md section 19)

- **Offline checks first.** [round4_offline.py](../../../round4_offline.py) and the local likelihood scorer
  [round4_pmi.py](../../../round4_pmi.py) tested four ideas on existing runs before anything was built:
  - literature base rates;
  - likelihood selection;
  - concrete conditions;
  - problem-level mechanisms.

  None passed. Outputs are in [../loop_r4/offline/](../loop_r4/README.md).
- **Generation and evaluation.** [run_r4.sh](./run_r4.sh) ran the four synthesis configurations and a fresh
  replicate of the incumbent on all 45 papers (1,350 runs) into [../loop_r4/](../loop_r4/README.md). It then ran:
  - the GPT-5.6 judge, audit and label loops on both TRAPI instances, each in a seeded random job order;
  - the DeepSeek cross-judge;
  - the draft class labels;
  - the report ([round4_analysis.py](../../../round4_analysis.py)).
- **Result.** No synthesis beats the incumbent. The final hypothesis follows the drafts' shared majority, so the
  decision does not change.
