Integrity verified: True. Runs judged 144/144; pairs judged 108/108; judge errors 0; generator openai:Qwen3.5-35B-A3B-Q4_K_M.gguf; judge trapi:gpt-5.6-sol_2026-07-09.

| Setting | Runs judged | Reconstruction (0-4) | Overall (0-4) | Failed | Tool calls | Records accessed |
|---|---:|---:|---:|---:|---:|---:|
| closed_book | 36/36 | 0.45 | 1.11 | 0 | 0.0 | 0.0 |
| text_oneshot | 36/36 | 0.55 | 1.52 | 0 | 0.0 | 14.0 |
| v2_oneshot | 36/36 | 0.46 | 1.42 | 0 | 0.0 | 14.0 |
| tool_agent | 36/36 | 0.53 | 1.42 | 0 | 11.9 | 18.9 |

| A | B | Role | Units | Mean difference (A-B) | 95% CI (papers bootstrap) | Papers A higher / B higher | Sign-test p | Holm p (primary family) |
|---|---|---|---:|---:|---|---:|---:|---:|
| tool_agent | text_oneshot | primary | 36 | -0.02 | [-0.10, +0.06] | 4 / 5 | 1.000 | 1.000 |
| tool_agent | v2_oneshot | primary | 36 | +0.07 | [-0.04, +0.19] | 5 / 4 | 1.000 | 1.000 |
| tool_agent | closed_book | primary | 36 | +0.08 | [-0.12, +0.28] | 6 / 4 | 0.754 | 1.000 |
| closed_book | text_oneshot | exploratory | 36 | -0.10 | [-0.35, +0.12] | 5 / 5 | 1.000 | n/a |
| closed_book | v2_oneshot | exploratory | 36 | -0.01 | [-0.23, +0.24] | 6 / 4 | 0.754 | n/a |
| text_oneshot | v2_oneshot | exploratory | 36 | +0.09 | [-0.01, +0.21] | 6 / 3 | 0.508 | n/a |

| A | B | Judged units | A wins | B wins | Ties | Position-inconsistent | A win rate (no ties) |
|---|---|---:|---:|---:|---:|---:|---:|
| tool_agent | text_oneshot | 36 | 13 | 16 | 7 | 7 | 0.45 |
| tool_agent | v2_oneshot | 36 | 18 | 8 | 10 | 9 | 0.69 |
| tool_agent | closed_book | 36 | 20 | 7 | 9 | 9 | 0.74 |
