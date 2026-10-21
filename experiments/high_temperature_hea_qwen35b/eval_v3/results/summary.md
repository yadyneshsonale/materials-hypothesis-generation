Integrity verified: False. Runs judged 143/144; pairs judged 107/108; judge errors 0; generator openai:Qwen3.5-35B-A3B-Q4_K_M.gguf; judge trapi:gpt-5.6-sol_2026-07-09.

| Setting | Runs judged | Reconstruction (0-4) | Overall (0-4) | Failed | Tool calls | Records accessed |
|---|---:|---:|---:|---:|---:|---:|
| closed_book | 35/36 | 1.56 | 1.89 | 1 | 0.0 | 0.0 |
| text_oneshot | 36/36 | 1.56 | 1.90 | 0 | 0.0 | 14.0 |
| v2_oneshot | 36/36 | 1.49 | 1.85 | 0 | 0.0 | 14.0 |
| tool_agent | 36/36 | 1.64 | 1.84 | 0 | 12.0 | 18.9 |

| A | B | Role | Units | Mean difference (A-B) | 95% CI (papers bootstrap) | Papers A higher / B higher | Sign-test p | Holm p (primary family) |
|---|---|---|---:|---:|---|---:|---:|---:|
| tool_agent | text_oneshot | primary | 36 | +0.08 | [-0.07, +0.21] | 7 / 3 | 0.344 | 0.344 |
| tool_agent | v2_oneshot | primary | 36 | +0.15 | [+0.01, +0.30] | 9 / 3 | 0.146 | 0.328 |
| tool_agent | closed_book | primary | 35 | +0.14 | [-0.06, +0.33] | 8 / 2 | 0.109 | 0.328 |
| closed_book | text_oneshot | exploratory | 35 | -0.05 | [-0.21, +0.12] | 5 / 5 | 1.000 | n/a |
| closed_book | v2_oneshot | exploratory | 35 | +0.04 | [-0.11, +0.19] | 6 / 5 | 1.000 | n/a |
| text_oneshot | v2_oneshot | exploratory | 36 | +0.08 | [-0.05, +0.19] | 7 / 3 | 0.344 | n/a |

| A | B | Judged units | A wins | B wins | Ties | Position-inconsistent | A win rate (no ties) |
|---|---|---:|---:|---:|---:|---:|---:|
| tool_agent | text_oneshot | 36 | 16 | 12 | 8 | 8 | 0.57 |
| tool_agent | v2_oneshot | 36 | 20 | 10 | 6 | 6 | 0.67 |
| tool_agent | closed_book | 35 | 17 | 12 | 6 | 6 | 0.59 |
