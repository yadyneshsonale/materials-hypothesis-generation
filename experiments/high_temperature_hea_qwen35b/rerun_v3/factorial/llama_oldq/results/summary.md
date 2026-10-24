Integrity verified: True. Runs judged 144/144; pairs judged 108/108; judge errors 0; generator trapi:Llama-3.3-70B-Instruct_5; judge trapi:gpt-5.6-sol_2026-07-09.

| Setting | Runs judged | Reconstruction (0-4) | Overall (0-4) | Failed | Tool calls | Records accessed |
|---|---:|---:|---:|---:|---:|---:|
| closed_book | 36/36 | 1.57 | 1.58 | 0 | 0.0 | 0.0 |
| text_oneshot | 36/36 | 1.43 | 1.40 | 0 | 0.0 | 14.0 |
| v2_oneshot | 36/36 | 1.38 | 1.37 | 0 | 0.0 | 14.0 |
| tool_agent | 36/36 | 1.21 | 1.08 | 0 | 1.6 | 3.5 |

| A | B | Role | Units | Mean difference (A-B) | 95% CI (papers bootstrap) | Papers A higher / B higher | Sign-test p | Holm p (primary family) |
|---|---|---|---:|---:|---|---:|---:|---:|
| tool_agent | text_oneshot | primary | 36 | -0.22 | [-0.31, -0.14] | 1 / 11 | 0.006 | 0.013 |
| tool_agent | v2_oneshot | primary | 36 | -0.17 | [-0.30, -0.05] | 2 / 9 | 0.065 | 0.065 |
| tool_agent | closed_book | primary | 36 | -0.36 | [-0.46, -0.26] | 0 / 12 | 0.001 | 0.002 |
| closed_book | text_oneshot | exploratory | 36 | +0.14 | [+0.03, +0.25] | 8 / 3 | 0.227 | n/a |
| closed_book | v2_oneshot | exploratory | 36 | +0.19 | [+0.05, +0.31] | 8 / 2 | 0.109 | n/a |
| text_oneshot | v2_oneshot | exploratory | 36 | +0.05 | [-0.06, +0.16] | 7 / 4 | 0.549 | n/a |

| A | B | Judged units | A wins | B wins | Ties | Position-inconsistent | A win rate (no ties) |
|---|---|---:|---:|---:|---:|---:|---:|
| tool_agent | text_oneshot | 36 | 8 | 24 | 4 | 4 | 0.25 |
| tool_agent | v2_oneshot | 36 | 6 | 27 | 3 | 3 | 0.18 |
| tool_agent | closed_book | 36 | 3 | 31 | 2 | 2 | 0.09 |
