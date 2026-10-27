Integrity verified: False. Runs judged 144/180; pairs judged 108/144; failed runs 0; judge errors 0; generator trapi:Llama-3.3-70B-Instruct_5; judge trapi:gpt-5.6-sol_2026-07-09.

| Setting | Runs judged | Reconstruction (0-4) | Overall (0-4) | Failed | Tool calls | Records accessed | KG facts surfaced per run | Runs citing a KG fact | KG facts cited |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| tool_agent_kg | 36/36 | 0.42 | 0.77 | 0 | 0.1 | 0.4 | 0.0 | 0 | 0 |
| closed_book | 36/36 | 0.57 | 1.09 | 0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| text_oneshot | 36/36 | 0.44 | 1.09 | 0 | 0.0 | 14.0 | 0.0 | 0 | 0 |
| v2_oneshot | 0/36 | nan | nan | 0 | nan | nan | nan | 0 | 0 |
| tool_agent | 36/36 | 0.35 | 0.67 | 0 | 1.7 | 5.5 | 0.0 | 0 | 0 |

| A | B | Units | Mean difference (A-B) | 95% CI (papers bootstrap) | Papers A higher / B higher | Sign-test p | Holm p |
|---|---|---:|---:|---|---:|---:|---:|
| tool_agent_kg | closed_book | 36 | -0.15 | [-0.28, -0.03] | 3 / 6 | 0.508 | 1.000 |
| tool_agent_kg | text_oneshot | 36 | -0.03 | [-0.16, +0.09] | 5 / 4 | 1.000 | 1.000 |
| tool_agent_kg | tool_agent | 36 | +0.06 | [-0.06, +0.17] | 8 / 3 | 0.227 | 0.680 |

| A | B | Judged units | A wins | B wins | Ties | Position-inconsistent | A win rate (no ties) |
|---|---|---:|---:|---:|---:|---:|---:|
| tool_agent_kg | closed_book | 36 | 8 | 22 | 6 | 4 | 0.27 |
| tool_agent_kg | text_oneshot | 36 | 8 | 26 | 2 | 2 | 0.24 |
| tool_agent_kg | v2_oneshot | 0 | 0 | 0 | 0 | 0 | n/a |
| tool_agent_kg | tool_agent | 36 | 12 | 16 | 8 | 6 | 0.43 |
