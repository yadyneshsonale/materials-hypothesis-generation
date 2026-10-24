Integrity verified: True. Runs judged 180/180; pairs judged 144/144; failed runs 0; judge errors 0; generator trapi:Llama-3.3-70B-Instruct_5; judge trapi:gpt-5.6-sol_2026-07-09.

| Setting | Runs judged | Reconstruction (0-4) | Overall (0-4) | Failed | Tool calls | Records accessed | KG facts surfaced per run | Runs citing a KG fact | KG facts cited |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| tool_agent_kg | 36/36 | 0.35 | 0.74 | 0 | 0.1 | 0.1 | 0.0 | 0 | 0 |
| closed_book | 36/36 | 0.57 | 1.09 | 0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| text_oneshot | 36/36 | 0.43 | 1.02 | 0 | 0.0 | 14.0 | 0.0 | 0 | 0 |
| v2_oneshot | 36/36 | 0.41 | 0.97 | 0 | 0.0 | 14.0 | 0.0 | 0 | 0 |
| tool_agent | 36/36 | 0.40 | 0.76 | 0 | 2.1 | 3.9 | 0.0 | 0 | 0 |

| A | B | Units | Mean difference (A-B) | 95% CI (papers bootstrap) | Papers A higher / B higher | Sign-test p | Holm p |
|---|---|---:|---:|---|---:|---:|---:|
| tool_agent_kg | closed_book | 36 | -0.22 | [-0.31, -0.12] | 1 / 9 | 0.021 | 0.086 |
| tool_agent_kg | text_oneshot | 36 | -0.08 | [-0.23, +0.06] | 5 / 5 | 1.000 | 1.000 |
| tool_agent_kg | v2_oneshot | 36 | -0.06 | [-0.15, +0.06] | 3 / 8 | 0.227 | 0.680 |
| tool_agent_kg | tool_agent | 36 | -0.05 | [-0.15, +0.04] | 4 / 6 | 0.754 | 1.000 |

| A | B | Judged units | A wins | B wins | Ties | Position-inconsistent | A win rate (no ties) |
|---|---|---:|---:|---:|---:|---:|---:|
| tool_agent_kg | closed_book | 36 | 4 | 22 | 10 | 8 | 0.15 |
| tool_agent_kg | text_oneshot | 36 | 10 | 23 | 3 | 3 | 0.30 |
| tool_agent_kg | v2_oneshot | 36 | 8 | 18 | 10 | 10 | 0.31 |
| tool_agent_kg | tool_agent | 36 | 12 | 13 | 11 | 10 | 0.48 |
