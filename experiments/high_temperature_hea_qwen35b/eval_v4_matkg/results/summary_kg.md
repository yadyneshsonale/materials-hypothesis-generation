Integrity verified: False. Runs judged 179/180; pairs judged 143/144; failed runs 1; judge errors 0; generator openai:Qwen3.5-35B-A3B-Q4_K_M.gguf; judge trapi:gpt-5.6-sol_2026-07-09.

| Setting | Runs judged | Reconstruction (0-4) | Overall (0-4) | Failed | Tool calls | Records accessed | KG facts surfaced per run | Runs citing a KG fact | KG facts cited |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| tool_agent_kg | 36/36 | 1.63 | 1.85 | 0 | 12.0 | 29.1 | 14.4 | 5 | 11 |
| closed_book | 35/36 | 1.56 | 1.89 | 1 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| text_oneshot | 36/36 | 1.56 | 1.90 | 0 | 0.0 | 14.0 | 0.0 | 0 | 0 |
| v2_oneshot | 36/36 | 1.49 | 1.85 | 0 | 0.0 | 14.0 | 0.0 | 0 | 0 |
| tool_agent | 36/36 | 1.64 | 1.84 | 0 | 12.0 | 18.9 | 0.0 | 0 | 0 |

| A | B | Units | Mean difference (A-B) | 95% CI (papers bootstrap) | Papers A higher / B higher | Sign-test p | Holm p |
|---|---|---:|---:|---|---:|---:|---:|
| tool_agent_kg | closed_book | 35 | +0.12 | [-0.01, +0.24] | 7 / 3 | 0.344 | 1.000 |
| tool_agent_kg | text_oneshot | 36 | +0.07 | [-0.05, +0.19] | 6 / 4 | 0.754 | 1.000 |
| tool_agent_kg | v2_oneshot | 36 | +0.15 | [+0.06, +0.24] | 8 / 2 | 0.109 | 0.438 |
| tool_agent_kg | tool_agent | 36 | -0.01 | [-0.12, +0.11] | 5 / 5 | 1.000 | 1.000 |

| A | B | Judged units | A wins | B wins | Ties | Position-inconsistent | A win rate (no ties) |
|---|---|---:|---:|---:|---:|---:|---:|
| tool_agent_kg | closed_book | 35 | 14 | 12 | 9 | 9 | 0.54 |
| tool_agent_kg | text_oneshot | 36 | 15 | 19 | 2 | 2 | 0.44 |
| tool_agent_kg | v2_oneshot | 36 | 15 | 11 | 10 | 10 | 0.58 |
| tool_agent_kg | tool_agent | 36 | 10 | 18 | 8 | 8 | 0.36 |
