# Experiment 46: strong research proposals as the only objective (phases 0-1)

Pre-registered in loop.md 27.1. SP = mean of plausibility, testability, usefulness (RQ judge, three DeepSeek calls) and grounding (one DeepSeek call) minus 1, on 0-4; RQ alone while grounding is not validated. Pairwise: net preference over the closed-book writer, both orders (a win needs both), paired by paper; DeepSeek decides, GPT-5.6 confirms, o1 alongside.

**Grounding validation** (G1-G4): valid = True; {"G1_swap_lowers": true, "G2_no_citation_mean_le_1.5": true, "G3_retest_rho_ge_0.70": true, "G4_evidence_writer_above_closed_book": true}. Swap: {"pairs": 134, "original_mean": 1.858, "control_mean": 1.022, "control_higher_share": 0.0, "drop_by_paper": {"papers": 45, "a_mean": 1.852, "b_mean": 1.022, "diff": 0.83, "ci95": [0.652, 1.022], "up": 39, "down": 0, "p": 0.0}}. Removal: {"pairs": 135, "original_mean": 1.867, "control_mean": 1.0, "control_higher_share": 0.0, "drop_by_paper": {"papers": 45, "a_mean": 1.867, "b_mean": 1.0, "diff": 0.867, "ci95": [0.681, 1.067], "up": 40, "down": 0, "p": 0.0}}. Re-test: {"pairs": 135, "rho": 0.82, "mean_abs_diff": 0.311}. Known groups (evidence writer minus closed-book writer): +0.87 [+0.68, +1.07] 40/0.

**RQ controls this session** (one call): passed = False (216 items); gaps {"usefulness_positive_minus_random": 1.389, "rq_positive_minus_generic": 0.954, "plausibility_positive_minus_intervention_swap": 0.861, "plausibility_positive_minus_mechanism_swap": 1.445}.

**RQ controls this session** (three calls): passed = True (216 items); gaps {"usefulness_positive_minus_random": 1.547, "rq_positive_minus_generic": 1.099, "plausibility_positive_minus_intervention_swap": 0.75, "plausibility_positive_minus_mechanism_swap": 1.435}.

**Writer RQ drift** (this session minus experiment 43): +0.05 [+0.00, +0.10] 29/16.

**Incumbent** (rule in loop.md 27.1): {"incumbent": "rx_r", "deepseek_lower_bound": 0.415, "gpt56": "confirmed", "eligible": ["rx_r", "rx_ru", "edit_rx_r", "rx_base", "web64k_v2_b_o3mini", "rx_u", "edit_rx_base", "web_text_64k_b_o3mini", "rx_ruc", "writer_study_b_o3mini", "rx_ruc_select", "rx_c"]}

## Leaderboard (configurations with complete RQ)

| # | Configuration | Exp. | SP | RQ | Plaus. | Test. | Useful. | Grounding | Words | SP vs writer | Pairwise vs writer: DeepSeek | o1 | GPT-5.6 |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| 1 | `rx_r` | 44-45 | 2.65 | 3.03 | 3.56 | 4.19 | 4.35 | 2.52 | 548.10 | +0.33 [+0.23, +0.42] 39/6 | +0.50 [+0.41, +0.58] 41/2, Holm 0.0 | – | +0.53 [+0.41, +0.64] 40/3, Holm 0.0 |
| 2 | `edit_rx_r` | 44-45 | 2.62 | 2.98 | 3.50 | 4.18 | 4.25 | 2.54 | 548.80 | +0.29 [+0.20, +0.39] 38/7 | +0.42 [+0.33, +0.50] 40/1, Holm 0.0 | – | +0.53 [+0.41, +0.64] 40/3, Holm 0.0 |
| 3 | `rx_ru` | 44-45 | 2.59 | 3.00 | 3.43 | 4.22 | 4.34 | 2.38 | 579.10 | +0.27 [+0.17, +0.36] 35/10 | +0.43 [+0.35, +0.52] 39/0, Holm 0.0 | – | +0.43 [+0.33, +0.53] 39/4, Holm 0.0 |
| 4 | `rx_ruc` | 44-45 | 2.59 | 2.98 | 3.48 | 4.18 | 4.27 | 2.42 | 413.60 | +0.26 [+0.15, +0.36] 33/12 | +0.24 [+0.16, +0.32] 31/4, Holm 0.0 | – | – |
| 5 | `agent_choose_ground_b_o3mini` | 40 | 2.56 | 2.93 | 3.48 | 4.15 | 4.18 | 2.43 | 510.30 | +0.20 [+0.10, +0.29] 34/11 | – | – | – |
| 6 | `rx_base` | 44-45 | 2.54 | 3.05 | 3.59 | 4.17 | 4.39 | 2.00 | 535.00 | +0.21 [+0.11, +0.31] 35/9 | +0.40 [+0.32, +0.49] 39/1, Holm 0.0 | – | – |
| 7 | `web64k_v2_b_o3mini` | 42 | 2.53 | 3.06 | 3.62 | 4.27 | 4.30 | 1.94 | 530.40 | +0.21 [+0.13, +0.28] 36/9 | +0.32 [+0.24, +0.40] 35/2, Holm 0.0 | +0.40 [+0.30, +0.51] 38/3, Holm 0.0 | – |
| 8 | `edit_rx_base` | 44-45 | 2.52 | 3.04 | 3.55 | 4.20 | 4.39 | 1.97 | 535.40 | +0.20 [+0.11, +0.29] 32/13 | +0.30 [+0.20, +0.40] 34/8, Holm 0.0004 | – | – |
| 9 | `web64k_r2_b_o3mini` | 42 | 2.51 | 3.03 | 3.57 | 4.16 | 4.35 | 1.94 | 536.00 | +0.14 [+0.05, +0.24] 30/15 | – | – | – |
| 10 | `rx_ruc_select` | 44-45 | 2.50 | 2.86 | 3.38 | 4.16 | 4.04 | 2.42 | 371.00 | +0.17 [+0.05, +0.30] 29/16 | +0.18 [+0.09, +0.27] 28/5, Holm 0.0004 | – | – |
| 11 | `rx_c` | 44-45 | 2.50 | 3.06 | 3.66 | 4.15 | 4.36 | 1.83 | 411.70 | +0.17 [+0.10, +0.25] 35/10 | +0.11 [+0.03, +0.20] 24/11, Holm 0.041 | – | – |
| 12 | `web_study_64k_b_o3mini` | 41 | 2.49 | 3.06 | 3.63 | 4.16 | 4.39 | 1.79 | 559.50 | +0.13 [+0.05, +0.21] 27/15 | – | – | – |
| 13 | `rx_u` | 44-45 | 2.48 | 2.97 | 3.41 | 4.22 | 4.29 | 2.01 | 571.50 | +0.16 [+0.05, +0.26] 34/11 | +0.33 [+0.24, +0.41] 34/1, Holm 0.0 | – | – |
| 14 | `web_text_64k_b_o3mini` | 36 | 2.48 | 3.03 | 3.56 | 4.15 | 4.37 | 1.85 | 525.10 | +0.16 [+0.06, +0.25] 32/13 | +0.29 [+0.20, +0.38] 35/5, Holm 0.0 | +0.41 [+0.32, +0.51] 38/4, Holm 0.0 | – |
| 15 | `pcd_PCD_o3mini` | 37 | 2.46 | 3.05 | 3.56 | 4.19 | 4.41 | 1.70 | 520.90 | +0.10 [+0.03, +0.18] 29/15 | – | – | – |
| 16 | `writer_study_b_o3mini` | 41 | 2.35 | 3.13 | 3.71 | 4.25 | 4.43 | 1.00 | 529.20 | +0.02 [-0.04, +0.08] 20/24 | +0.22 [+0.14, +0.30] 30/7, Holm 0.0004 | +0.21 [+0.14, +0.29] 31/8, Holm 0.0003 | – |
| 17 | `writer_v2_b_o3mini` | 42 | 2.35 | 3.13 | 3.77 | 4.29 | 4.33 | 1.00 | 477.00 | -0.02 [-0.08, +0.04] 19/24 | – | – | – |
| 18 | `writer_only_b_o3mini` | 21-35 | 2.33 | 3.10 | 3.71 | 4.16 | 4.43 | 1.00 | 487.70 | – | – | – | – |
| 19 | `closed_book_o3mini` | 21-35 | 2.23 | 2.97 | 3.52 | 4.18 | 4.21 | 1.00 | 473.10 | -0.10 [-0.16, -0.04] 14/31 | -0.34 [-0.41, -0.27] 2/41, Holm 0.0 | -0.21 [-0.28, -0.13] 6/33, Holm 0.0 | – |
| 20 | `closed_book` | 21-35 | 1.05 | 1.40 | 2.35 | 2.64 | 2.21 | 1.00 | 226.20 | -1.28 [-1.37, -1.19] 0/45 | -1.00 [-1.00, -1.00] 0/45, Holm 0.0 | -0.98 [-1.00, -0.97] 0/45, Holm 0.0 | – |

Incomplete (still being judged): none.

## References (never methods; must_obey.md 5.4)

- `oracle_hint_full_b_o3mini`: SP 2.04, RQ 2.71, grounding 1.00; pairwise vs the writer (DeepSeek) -0.17 [-0.30, -0.05] 12/22

Length: Spearman of SP with words across configurations 0.481.
