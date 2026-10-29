# Experiment 40: an agent that chooses its approach from the evidence

Pre-registered in loop.md 21.1. GPT-5.6 baselines are judged again in the same session (must_obey.md 6.10).

**Decision:** the pre-registered rule is not met.

## Q1 (primary): the agent vs the baselines

| comparison | GPT-5.6 [CI] | DeepSeek [CI] | decision |
|---|---|---|---|
| agent_choose_ground_b_o3mini vs writer_only_b_o3mini | -0.037 [-0.10, +0.03] (45 papers, 15/23, Holm p 0.5118) | -0.006 [-0.12, +0.11] (45 papers, 25/18, Holm p 0.7208) | no detectable difference |
| agent_choose_ground_b_o3mini vs web_text_64k_b_o3mini | -0.036 [-0.08, +0.01] (45 papers, 18/23, Holm p 0.5327) | -0.086 [-0.17, -0.00] (45 papers, 19/25, Holm p 0.7208) | no detectable difference |

## Q2: the 2 × 2 (approach chosen by the model or from the evidence × focused writing evidence)

| effect | GPT-5.6 [CI] | DeepSeek [CI] |
|---|---|---|
| choose the approach from the evidence | -0.010 [-0.06, +0.04] (45 papers, 19/25, Holm p 0.9028) | -0.044 [-0.12, +0.03] (45 papers, 21/23, Holm p 0.8804) |
| focused writing evidence | -0.027 [-0.06, +0.01] (45 papers, 20/25, Holm p 0.9028) | +0.038 [-0.02, +0.09] (45 papers, 30/14, Holm p 0.0452) |
| interaction | +0.056 [+0.00, +0.11] (45 papers, 28/16, Holm p 0.2883) | +0.128 [+0.03, +0.23] (45 papers, 31/13, Holm p 0.0288) |

Cell means, GPT-5.6: {"model choice, none evidence": 0.621, "model choice, focused evidence": 0.567, "evidence choice, none evidence": 0.583, "evidence choice, focused evidence": 0.584}
Cell means, DeepSeek: {"model choice, none evidence": 0.575, "model choice, focused evidence": 0.549, "evidence choice, none evidence": 0.468, "evidence choice, focused evidence": 0.569}

## Q3: the chooser

- `agent_choose_ground_b_o3mini`: {"runs": 270, "fallbacks": 0, "groups_per_run": 7.759, "chosen_addresses": {"0": 8, "1": 8, "2": 22, "3": 232}, "chosen_papers": 3.404, "chosen_passages": 5.185, "focused_pack_records": 13.193, "focused_pack_from_group": 4.574, "same_choice_both_samples": 0.0}
- `agent_choose_only_b_o3mini`: {"runs": 270, "fallbacks": 0, "groups_per_run": 7.452, "chosen_addresses": {"0": 9, "1": 9, "2": 23, "3": 229}, "chosen_papers": 3.478, "chosen_passages": 5.215, "focused_pack_records": null, "focused_pack_from_group": null, "same_choice_both_samples": 0.0}

## Q4: target-free quality (pairwise, both orders; +1 when the agent wins both orders)

| comparison | judge | pairs | agent wins | baseline wins | tie or inconsistent | first position wins | net preference for the agent [CI] |
|---|---|---:|---:|---:|---:|---:|---|
| agent_vs_writer | gpt56 | 270 | 0.556 | 0.27 | 0.174 | 0.583 | +0.285 [+0.15, +0.42] (45 papers, 30/10, Holm p 0.0088) |
| agent_vs_writer | deepseek | 270 | 0.256 | 0.067 | 0.678 | 0.839 | +0.189 [+0.10, +0.28] (45 papers, 29/8, Holm p 0.004) |
| agent_vs_writer | o1 | 270 | 0.356 | 0.119 | 0.526 | 0.763 | +0.237 [+0.14, +0.33] (45 papers, 35/6, Holm p 0.0) |
| agent_vs_q64 | gpt56 | 270 | 0.448 | 0.315 | 0.237 | 0.606 | +0.133 [+0.03, +0.24] (45 papers, 26/11, Holm p 0.0402) |
| agent_vs_q64 | deepseek | 270 | 0.126 | 0.211 | 0.663 | 0.828 | -0.085 [-0.17, +0.00] (45 papers, 13/25, Holm p 0.073) |
| agent_vs_q64 | o1 | 270 | 0.122 | 0.311 | 0.567 | 0.77 | -0.189 [-0.28, -0.10] (45 papers, 9/26, Holm p 0.018) |

## Profiles

| configuration | runs | GPT-5.6 | DeepSeek | lever ≥ 2 | class hit | intervention | conditions | mechanism | outcome | novelty | unsupported | complete chain | specificity | calls | seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| writer_only_b_o3mini | 270 | 0.621 | 0.575 | 0.189 | 0.404 | 0.315 | 0.578 | 0.748 | 0.852 | 1.556 | 0.726 | 0.837 | 0.306 | 1.03 | 10.459 |
| web_text_64k_b_o3mini | 270 | 0.62 | 0.656 | 0.207 | 0.426 | 0.319 | 0.67 | 0.696 | 0.859 | 1.796 | 0.47 | 0.693 | 0.405 | 1.256 | 17.857 |
| agent_choose_ground_b_o3mini | 270 | 0.584 | 0.569 | 0.193 | 0.333 | 0.278 | 0.604 | 0.656 | 0.8 | 1.752 | 0.407 | 0.7 | 0.401 | 2.111 | 49.131 |
| agent_choose_only_b_o3mini | 270 | 0.583 | 0.468 | 0.185 | 0.378 | 0.248 | 0.607 | 0.663 | 0.815 | 1.533 | 0.804 | 0.793 | 0.252 | 2.363 | 48.252 |
| agent_draft_ground_b_o3mini | 270 | 0.567 | 0.549 | 0.152 | 0.419 | 0.219 | 0.563 | 0.641 | 0.844 | 1.785 | 0.567 | 0.733 | 0.326 | 2.159 | 27.086 |
| oracle_targetpack_b_o3mini | 270 | 0.739 | 0.696 | 0.256 | 0.396 | 0.352 | 0.73 | 0.948 | 0.926 | 1.752 | 0.474 | 0.685 | 0.386 | 1.167 | 15.428 |

GPT-5.6 of the baselines in the profiles and Q1–Q2: same-session judgments. {"writer_only_b_o3mini": {"original_gpt": 0.623, "same_session_gpt": 0.621, "rejudged_runs": 270}, "web_text_64k_b_o3mini": {"original_gpt": 0.636, "same_session_gpt": 0.62, "rejudged_runs": 270}}

The oracle pack (`oracle_targetpack_b_o3mini`) is an upper reference from experiment 39, not a comparison.

## Leakage

Counters over 810 runs: {}; web records re-checked: 33848, date violations: 0, unresolved: 0.
