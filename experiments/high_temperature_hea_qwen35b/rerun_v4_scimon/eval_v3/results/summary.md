Integrity verified: True. Runs judged 48/48; pairs judged 36/36; judge errors 0; generator trapi:Llama-3.3-70B-Instruct_5; judge trapi:gpt-5.6-sol_2026-07-09.

| Setting | Runs judged | Reconstruction (0-4) | Overall (0-4) | Failed | Tool calls | Records accessed |
|---|---:|---:|---:|---:|---:|---:|
| closed_book | 12/12 | 0.46 | 0.64 | 0 | 0.0 | 0.0 |
| text_oneshot | 12/12 | 0.50 | 0.81 | 0 | 0.0 | 14.0 |
| v2_oneshot | 12/12 | 0.33 | 0.64 | 0 | 0.0 | 14.0 |
| tool_agent | 12/12 | 0.33 | 0.57 | 0 | 2.1 | 5.0 |

| A | B | Role | Units | Mean difference (A-B) | 95% CI (papers bootstrap) | Papers A higher / B higher | Sign-test p | Holm p (primary family) |
|---|---|---|---:|---:|---|---:|---:|---:|
| tool_agent | text_oneshot | primary | 12 | -0.17 | [-0.35, +0.02] | 4 / 8 | 0.388 | 1.000 |
| tool_agent | v2_oneshot | primary | 12 | +0.00 | [-0.19, +0.19] | 4 / 4 | 1.000 | 1.000 |
| tool_agent | closed_book | primary | 12 | -0.12 | [-0.38, +0.10] | 4 / 5 | 1.000 | 1.000 |
| closed_book | text_oneshot | exploratory | 12 | -0.04 | [-0.31, +0.21] | 5 / 5 | 1.000 | n/a |
| closed_book | v2_oneshot | exploratory | 12 | +0.12 | [-0.19, +0.40] | 7 / 3 | 0.344 | n/a |
| text_oneshot | v2_oneshot | exploratory | 12 | +0.17 | [+0.00, +0.33] | 7 / 1 | 0.070 | n/a |

| A | B | Judged units | A wins | B wins | Ties | Position-inconsistent | A win rate (no ties) |
|---|---|---:|---:|---:|---:|---:|---:|
| tool_agent | text_oneshot | 12 | 3 | 8 | 1 | 0 | 0.27 |
| tool_agent | v2_oneshot | 12 | 4 | 6 | 2 | 2 | 0.40 |
| tool_agent | closed_book | 12 | 6 | 5 | 1 | 1 | 0.55 |
