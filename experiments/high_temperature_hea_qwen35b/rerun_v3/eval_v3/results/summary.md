Integrity verified: True. Runs judged 144/144; pairs judged 108/108; judge errors 0; generator trapi:Llama-3.3-70B-Instruct_5; judge trapi:gpt-5.6-sol_2026-07-09.

| Setting | Runs judged | Reconstruction (0-4) | Overall (0-4) | Failed | Tool calls | Records accessed |
|---|---:|---:|---:|---:|---:|---:|
| closed_book | 36/36 | 0.57 | 1.09 | 0 | 0.0 | 0.0 |
| text_oneshot | 36/36 | 0.43 | 1.02 | 0 | 0.0 | 14.0 |
| v2_oneshot | 36/36 | 0.41 | 0.97 | 0 | 0.0 | 14.0 |
| tool_agent | 36/36 | 0.40 | 0.76 | 0 | 2.1 | 3.9 |

| A | B | Role | Units | Mean difference (A-B) | 95% CI (papers bootstrap) | Papers A higher / B higher | Sign-test p | Holm p (primary family) |
|---|---|---|---:|---:|---|---:|---:|---:|
| tool_agent | text_oneshot | primary | 36 | -0.03 | [-0.18, +0.12] | 5 / 6 | 1.000 | 1.000 |
| tool_agent | v2_oneshot | primary | 36 | -0.01 | [-0.12, +0.11] | 4 / 6 | 0.754 | 1.000 |
| tool_agent | closed_book | primary | 36 | -0.17 | [-0.28, -0.06] | 2 / 9 | 0.065 | 0.196 |
| closed_book | text_oneshot | exploratory | 36 | +0.14 | [-0.01, +0.28] | 7 / 3 | 0.344 | n/a |
| closed_book | v2_oneshot | exploratory | 36 | +0.16 | [+0.06, +0.27] | 8 / 2 | 0.109 | n/a |
| text_oneshot | v2_oneshot | exploratory | 36 | +0.02 | [-0.10, +0.16] | 3 / 4 | 1.000 | n/a |

| A | B | Judged units | A wins | B wins | Ties | Position-inconsistent | A win rate (no ties) |
|---|---|---:|---:|---:|---:|---:|---:|
| tool_agent | text_oneshot | 36 | 9 | 25 | 2 | 2 | 0.26 |
| tool_agent | v2_oneshot | 36 | 11 | 20 | 5 | 5 | 0.35 |
| tool_agent | closed_book | 36 | 12 | 21 | 3 | 3 | 0.36 |
