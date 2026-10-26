Integrity verified: True. Runs judged 60/60; pairs judged 48/48; failed runs 0; judge errors 0; generator trapi:Llama-3.3-70B-Instruct_5; judge trapi:gpt-5.6-sol_2026-07-09.

| Setting | Runs judged | Reconstruction (0-4) | Overall (0-4) | Failed | Tool calls | Records accessed | KG facts surfaced per run | Runs citing a KG fact | KG facts cited |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| tool_agent_kg | 12/12 | 0.29 | 0.53 | 0 | 0.9 | 2.3 | 0.7 | 0 | 0 |
| closed_book | 12/12 | 0.46 | 0.64 | 0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| text_oneshot | 12/12 | 0.50 | 0.81 | 0 | 0.0 | 14.0 | 0.0 | 0 | 0 |
| v2_oneshot | 12/12 | 0.33 | 0.64 | 0 | 0.0 | 14.0 | 0.0 | 0 | 0 |
| tool_agent | 12/12 | 0.33 | 0.57 | 0 | 2.1 | 5.0 | 0.0 | 0 | 0 |

| A | B | Units | Mean difference (A-B) | 95% CI (papers bootstrap) | Papers A higher / B higher | Sign-test p | Holm p |
|---|---|---:|---:|---|---:|---:|---:|
| tool_agent_kg | closed_book | 12 | -0.17 | [-0.33, -0.02] | 2 / 7 | 0.180 | 0.719 |
| tool_agent_kg | text_oneshot | 12 | -0.21 | [-0.42, +0.00] | 2 / 7 | 0.180 | 0.719 |
| tool_agent_kg | v2_oneshot | 12 | -0.04 | [-0.29, +0.17] | 4 / 4 | 1.000 | 1.000 |
| tool_agent_kg | tool_agent | 12 | -0.04 | [-0.23, +0.17] | 3 / 6 | 0.508 | 1.000 |

| A | B | Judged units | A wins | B wins | Ties | Position-inconsistent | A win rate (no ties) |
|---|---|---:|---:|---:|---:|---:|---:|
| tool_agent_kg | closed_book | 12 | 5 | 3 | 4 | 3 | 0.62 |
| tool_agent_kg | text_oneshot | 12 | 5 | 6 | 1 | 1 | 0.45 |
| tool_agent_kg | v2_oneshot | 12 | 5 | 5 | 2 | 2 | 0.50 |
| tool_agent_kg | tool_agent | 12 | 5 | 6 | 1 | 1 | 0.45 |
