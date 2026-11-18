# Experiment 48: writers that combine or extend several papers

Pre-registered in loop.md 27.7. Same evidence pack as rx_r (focused retrieval); only the writer changes. Non-copying (1–5, unvalidated) and RQ (three DeepSeek calls); pairwise against rx_r in both orders.

| Arm | Runs ok | Calls | Words | Papers cited | Non-copying | Scores 1/2/3/4/5 | RQ | Plaus. | Test. | Useful. | SP2 |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| `synth_a` | 270 | 1.00 | 615.10 | 1.93 | 2.60 | 73/71/20/104/2 | 2.99 | 3.43 | 4.18 | 4.37 | 2.64 |
| `synth_b` | 270 | 2.00 | 619.00 | 2.40 | 3.47 | 22/43/18/160/27 | 2.97 | 3.33 | 4.24 | 4.35 | 2.85 |
| `agent_draft_ground_b_o3mini` | 270 | 2.16 | 509.40 | 2.20 | 3.03 | 82/26/22/82/58 | 3.16 | 3.72 | 4.26 | 4.49 | 2.87 |
| `rx_r` | 270 | 1.00 | 548.10 | 1.76 | 1.89 | 150/57/12/45/6 | 3.03 | 3.56 | 4.19 | 4.35 | 2.50 |
| `writer_only_b_o3mini` | 270 | 1.03 | 487.70 | 0.00 | 3.12 | 93/10/8/91/68 | 3.10 | 3.71 | 4.16 | 4.43 | 2.85 |

## Against rx_r (paired by paper)

**`synth_a`: improves on rx_r**

- Non-copying: +0.71 [+0.53, +0.89], 37 vs 2 papers, Holm 0.0 (vs the closed-book writer: -0.52 [-0.79, -0.25], 13 vs 31 papers)
- RQ: -0.04 [-0.13, +0.04], 18 vs 27 papers, Holm 0.4654; plausibility -0.14 [-0.25, -0.03], 14 vs 30 papers; testability -0.01 [-0.08, +0.07], 20 vs 24 papers; usefulness +0.02 [-0.12, +0.15], 22 vs 20 papers
- SP2: +0.14 [+0.06, +0.23], 29 vs 16 papers
- Pairwise v2 (goes beyond the earlier work): DeepSeek +0.17 [+0.12, +0.22], 28 vs 2 papers; GPT-5.6 +0.27 [+0.17, +0.37], 31 vs 7 papers
- Pairwise v1 (experiment-46 prompt): DeepSeek +0.05 [+0.00, +0.10], 17 vs 9 papers

**`synth_b`: improves on rx_r**

- Non-copying: +1.58 [+1.35, +1.80], 43 vs 0 papers, Holm 0.0 (vs the closed-book writer: +0.36 [+0.05, +0.66], 25 vs 16 papers)
- RQ: -0.06 [-0.16, +0.04], 19 vs 26 papers, Holm 0.4654; plausibility -0.24 [-0.36, -0.11], 12 vs 33 papers; testability +0.05 [-0.04, +0.14], 26 vs 15 papers; usefulness -0.00 [-0.14, +0.14], 18 vs 25 papers
- SP2: +0.35 [+0.24, +0.45], 40 vs 5 papers
- Pairwise v2 (goes beyond the earlier work): DeepSeek +0.18 [+0.10, +0.26], 30 vs 7 papers; GPT-5.6 +0.41 [+0.29, +0.53], 35 vs 8 papers
- Pairwise v1 (experiment-46 prompt): DeepSeek -0.01 [-0.07, +0.04], 13 vs 14 papers

**`agent_draft_ground_b_o3mini`: more original, but worse on quality** (evaluation-only addition; outside the Holm family)

- Non-copying: +1.14 [+0.92, +1.37], 42 vs 2 papers (vs the closed-book writer: -0.09 [-0.33, +0.16], 16 vs 24 papers)
- RQ: +0.12 [+0.02, +0.23], 27 vs 18 papers; plausibility +0.15 [+0.02, +0.29], 25 vs 18 papers; testability +0.07 [-0.00, +0.15], 25 vs 17 papers; usefulness +0.14 [-0.00, +0.29], 22 vs 18 papers
- SP2: +0.38 [+0.27, +0.48], 36 vs 9 papers
- Pairwise v2 (goes beyond the earlier work): DeepSeek -0.32 [-0.41, -0.24], 3 vs 35 papers; GPT-5.6 -0.03 [-0.15, +0.08], 19 vs 20 papers
- Pairwise v1 (experiment-46 prompt): DeepSeek –

## Leakage

{'counters': {'temporal_violations': 0, 'test_paper_leaks': 0, 'family_leaks': 0, 'target_doi_or_title_leaks': 0, 'invalid_citations': 0}, 'records_rechecked': 24496, 'date_violations': 0}
