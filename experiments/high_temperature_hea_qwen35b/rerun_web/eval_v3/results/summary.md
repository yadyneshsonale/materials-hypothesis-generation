Integrity verified: False. Runs judged 108/144; pairs judged 72/108; judge errors 0; generator trapi:Llama-3.3-70B-Instruct_5; judge trapi:gpt-5.6-sol_2026-07-09.

| Setting | Runs judged | Reconstruction (0-4) | Overall (0-4) | Failed | Tool calls | Records accessed |
|---|---:|---:|---:|---:|---:|---:|
| closed_book | 36/36 | 0.57 | 1.09 | 0 | 0.0 | 0.0 |
| text_oneshot | 36/36 | 0.44 | 1.09 | 0 | 0.0 | 14.0 |
| v2_oneshot | 0/36 | nan | nan | 0 | nan | nan |
| tool_agent | 36/36 | 0.35 | 0.67 | 0 | 1.7 | 5.5 |

| A | B | Role | Units | Mean difference (A-B) | 95% CI (papers bootstrap) | Papers A higher / B higher | Sign-test p | Holm p (primary family) |
|---|---|---|---:|---:|---|---:|---:|---:|
| tool_agent | text_oneshot | primary | 36 | -0.09 | [-0.19, -0.01] | 3 / 7 | 0.344 | 0.344 |
| tool_agent | closed_book | primary | 36 | -0.22 | [-0.33, -0.12] | 0 / 10 | 0.002 | 0.004 |
| closed_book | text_oneshot | exploratory | 36 | +0.12 | [+0.02, +0.22] | 10 / 2 | 0.039 | n/a |

| A | B | Judged units | A wins | B wins | Ties | Position-inconsistent | A win rate (no ties) |
|---|---|---:|---:|---:|---:|---:|---:|
| tool_agent | text_oneshot | 36 | 7 | 23 | 6 | 6 | 0.23 |
| tool_agent | v2_oneshot | 0 | 0 | 0 | 0 | 0 | n/a |
| tool_agent | closed_book | 36 | 8 | 22 | 6 | 6 | 0.27 |
