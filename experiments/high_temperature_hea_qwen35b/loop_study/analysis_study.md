# Experiment 41: a complete-study writer

Pre-registered in loop.md 22.1. GPT-5.6 baselines are judged again in this session (must_obey.md 6.10).

## Q1 (primary)

| comparison | GPT-5.6 [CI] | DeepSeek [CI] | decision |
|---|---|---|---|
| writer_study_b_o3mini vs writer_only_b_o3mini | -0.031 [-0.08, +0.01] (45 papers, 19/24, Holm p 1.0) | -0.037 [-0.09, +0.02] (45 papers, 21/21, Holm p 1.0) | no detectable difference |
| web_study_64k_b_o3mini vs web_text_64k_b_o3mini | -0.025 [-0.07, +0.02] (45 papers, 18/21, Holm p 1.0) | -0.026 [-0.11, +0.06] (45 papers, 19/24, Holm p 1.0) | no detectable difference |

## Q2 (components)

| comparison | GPT-5.6 [CI] | DeepSeek [CI] | decision |
|---|---|---|---|
| writer_types_b_o3mini vs writer_only_b_o3mini | -0.000 [-0.03, +0.03] (45 papers, 23/16, Holm p 0.6736) | -0.050 [-0.11, +0.01] (45 papers, 16/21, Holm p 1.0) | no detectable difference |
| writer_design_b_o3mini vs writer_only_b_o3mini | -0.019 [-0.06, +0.02] (45 papers, 19/22, Holm p 0.7552) | -0.031 [-0.09, +0.03] (45 papers, 18/20, Holm p 1.0) | no detectable difference |

## Q3: failure points

| configuration | runs | GPT-5.6 | DeepSeek | lever ≥ 2 | class hit | lever ≥ 2 on processing-route papers | on simulation papers | names a route | intervention | conditions | mechanism | outcome | unsupported |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| writer_only_b_o3mini | 270 | 0.632 | 0.575 | 0.189 | 0.404 | 0.017 | 0.0 | 0.274 | 0.315 | 0.578 | 0.748 | 0.852 | 0.726 |
| web_text_64k_b_o3mini | 270 | 0.631 | 0.656 | 0.207 | 0.426 | 0.052 | 0.0 | 0.356 | 0.319 | 0.67 | 0.696 | 0.859 | 0.47 |
| writer_study_b_o3mini | 270 | 0.601 | 0.538 | 0.119 | 0.33 | 0.034 | 0.0 | 0.504 | 0.2 | 0.596 | 0.748 | 0.859 | 0.737 |
| writer_types_b_o3mini | 270 | 0.632 | 0.525 | 0.133 | 0.363 | 0.017 | 0.0 | 0.459 | 0.259 | 0.659 | 0.77 | 0.841 | 0.752 |
| writer_design_b_o3mini | 270 | 0.614 | 0.544 | 0.17 | 0.381 | 0.0 | 0.0 | 0.441 | 0.241 | 0.585 | 0.733 | 0.896 | 0.726 |
| web_study_64k_b_o3mini | 270 | 0.606 | 0.63 | 0.2 | 0.352 | 0.052 | 0.033 | 0.537 | 0.23 | 0.644 | 0.707 | 0.841 | 0.47 |

## Q4: quality without the answer key (writer_study_b_o3mini vs the writer)

| judge | pairs | new wins | writer wins | net preference [CI] |
|---|---:|---:|---:|---|
| gpt56 | 270 | 0.574 | 0.259 | +0.315 [+0.21, +0.41] (45 papers, 34/6, Holm p 0.0) |
| deepseek | 270 | 0.319 | 0.093 | +0.226 [+0.16, +0.30] (45 papers, 33/6, Holm p 0.0) |
| o1 | 270 | 0.374 | 0.174 | +0.200 [+0.12, +0.28] (45 papers, 27/7, Holm p 0.0008) |

Same-session baselines: {"writer_only_b_o3mini": {"same_session_gpt": 0.632, "rejudged_runs": 270}, "web_text_64k_b_o3mini": {"same_session_gpt": 0.631, "rejudged_runs": 270}}

## Leakage

Counters over 1080 runs: {}; web records re-checked: 14658, date violations: 0.
