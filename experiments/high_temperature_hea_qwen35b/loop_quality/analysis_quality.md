# Experiment 46: strong research proposals as the only objective (phases 0-1)

Pre-registered in loop.md 27.1. SP = mean of plausibility, testability, usefulness (RQ judge, three DeepSeek calls) and grounding (one DeepSeek call) minus 1, on 0-4; RQ alone while grounding is not validated. Pairwise: net preference over the closed-book writer, both orders (a win needs both), paired by paper; DeepSeek decides, GPT-5.6 confirms, o1 alongside.

**Grounding validation** (G1-G4): valid = True; {"G1_swap_lowers": true, "G2_no_citation_mean_le_1.5": true, "G3_retest_rho_ge_0.70": true, "G4_evidence_writer_above_closed_book": true}. Swap: {"pairs": 134, "original_mean": 1.858, "control_mean": 1.022, "control_higher_share": 0.0, "drop_by_paper": {"papers": 45, "a_mean": 1.852, "b_mean": 1.022, "diff": 0.83, "ci95": [0.652, 1.022], "up": 39, "down": 0, "p": 0.0}}. Removal: {"pairs": 135, "original_mean": 1.867, "control_mean": 1.0, "control_higher_share": 0.0, "drop_by_paper": {"papers": 45, "a_mean": 1.867, "b_mean": 1.0, "diff": 0.867, "ci95": [0.681, 1.067], "up": 40, "down": 0, "p": 0.0}}. Re-test: {"pairs": 135, "rho": 0.82, "mean_abs_diff": 0.311}. Known groups (evidence writer minus closed-book writer): +0.87 [+0.68, +1.07] 40/0.

**RQ controls this session** (one call): passed = False (216 items); gaps {"usefulness_positive_minus_random": 1.389, "rq_positive_minus_generic": 0.954, "plausibility_positive_minus_intervention_swap": 0.861, "plausibility_positive_minus_mechanism_swap": 1.445}.

**RQ controls this session** (three calls): passed = True (216 items); gaps {"usefulness_positive_minus_random": 1.547, "rq_positive_minus_generic": 1.099, "plausibility_positive_minus_intervention_swap": 0.75, "plausibility_positive_minus_mechanism_swap": 1.435}.

**Writer RQ drift** (this session minus experiment 43): +0.05 [+0.00, +0.10] 29/16.

**Incumbent** (rule in loop.md 27.1): {"incumbent": "rx_r", "deepseek_lower_bound": 0.415, "gpt56": "confirmed", "eligible": ["rx_r", "rx_ru", "edit_rx_r", "rx_base", "web64k_v2_b_o3mini", "rx_u", "web64k_r2_b_o3mini", "agent_draft_ground_b_o3mini", "pcd_nocritic_PCD_o3mini", "edit_rx_base", "web_text_64k_b_o3mini", "web_text_chunks_b_o3mini", "rx_ruc", "writer_study_b_o3mini", "rx_ruc_select", "agent_choose_ground_b_o3mini", "rx_c"]}

## Leaderboard (configurations with complete RQ)

| # | Configuration | Exp. | SP | RQ | Plaus. | Test. | Useful. | Grounding | Words | SP vs writer | Pairwise vs writer: DeepSeek | o1 | GPT-5.6 |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| 1 | `rx_r` | 44-45 | 2.65 | 3.03 | 3.56 | 4.19 | 4.35 | 2.52 | 548.10 | +0.33 [+0.23, +0.42] 39/6 | +0.50 [+0.41, +0.58] 41/2, Holm 0.0 | +0.59 [+0.51, +0.66] 44/1, Holm 0.0 | +0.54 [+0.43, +0.65] 40/3, Holm 0.0 |
| 2 | `edit_rx_r` | 44-45 | 2.62 | 2.98 | 3.50 | 4.18 | 4.25 | 2.54 | 548.80 | +0.29 [+0.20, +0.39] 38/7 | +0.42 [+0.33, +0.50] 40/1, Holm 0.0 | +0.56 [+0.48, +0.64] 42/1, Holm 0.0 | +0.54 [+0.42, +0.65] 40/3, Holm 0.0 |
| 3 | `rx_ru` | 44-45 | 2.59 | 3.00 | 3.43 | 4.22 | 4.34 | 2.38 | 579.10 | +0.27 [+0.17, +0.36] 35/10 | +0.43 [+0.35, +0.52] 39/0, Holm 0.0 | +0.53 [+0.46, +0.59] 44/0, Holm 0.0 | +0.43 [+0.33, +0.52] 38/2, Holm 0.0 |
| 4 | `rx_ruc` | 44-45 | 2.59 | 2.98 | 3.48 | 4.18 | 4.27 | 2.42 | 413.60 | +0.26 [+0.15, +0.36] 33/12 | +0.24 [+0.16, +0.32] 31/4, Holm 0.0 | +0.34 [+0.24, +0.43] 36/5, Holm 0.0 | – |
| 5 | `agent_draft_ground_b_o3mini` | 40 | 2.57 | 3.16 | 3.72 | 4.26 | 4.49 | 1.80 | 509.40 | +0.20 [+0.14, +0.27] 38/7 | +0.27 [+0.22, +0.32] 39/1, Holm 0.0 | +0.33 [+0.25, +0.42] 35/2, Holm 0.0 | – |
| 6 | `agent_choose_ground_b_o3mini` | 40 | 2.56 | 2.93 | 3.48 | 4.15 | 4.18 | 2.43 | 510.30 | +0.20 [+0.10, +0.29] 34/11 | +0.16 [+0.07, +0.25] 28/8, Holm 0.0024 | +0.25 [+0.16, +0.35] 33/8, Holm 0.0003 | – |
| 7 | `rx_base` | 44-45 | 2.54 | 3.05 | 3.59 | 4.17 | 4.39 | 2.00 | 535.00 | +0.21 [+0.11, +0.31] 35/9 | +0.40 [+0.32, +0.49] 39/1, Holm 0.0 | +0.47 [+0.38, +0.57] 38/3, Holm 0.0 | – |
| 8 | `web64k_v2_b_o3mini` | 42 | 2.53 | 3.06 | 3.62 | 4.27 | 4.30 | 1.94 | 530.40 | +0.21 [+0.13, +0.28] 36/9 | +0.32 [+0.24, +0.40] 35/2, Holm 0.0 | +0.41 [+0.30, +0.51] 38/3, Holm 0.0 | – |
| 9 | `web_text_chunks_b_o3mini` | 36 | 2.53 | 3.04 | 3.58 | 4.20 | 4.35 | 1.98 | 514.00 | +0.17 [+0.08, +0.25] 33/11 | +0.26 [+0.19, +0.34] 33/6, Holm 0.0 | +0.45 [+0.38, +0.53] 41/1, Holm 0.0 | – |
| 10 | `edit_rx_base` | 44-45 | 2.52 | 3.04 | 3.55 | 4.20 | 4.39 | 1.97 | 535.40 | +0.20 [+0.11, +0.29] 32/13 | +0.30 [+0.20, +0.40] 34/8, Holm 0.0005 | +0.43 [+0.34, +0.52] 38/3, Holm 0.0 | – |
| 11 | `web64k_r2_b_o3mini` | 42 | 2.51 | 3.03 | 3.57 | 4.16 | 4.35 | 1.94 | 536.00 | +0.14 [+0.05, +0.24] 30/15 | +0.31 [+0.23, +0.40] 33/2, Holm 0.0 | +0.46 [+0.36, +0.54] 37/3, Holm 0.0 | – |
| 12 | `rx_ruc_select` | 44-45 | 2.50 | 2.86 | 3.38 | 4.16 | 4.04 | 2.42 | 371.00 | +0.17 [+0.05, +0.30] 29/16 | +0.18 [+0.09, +0.27] 28/5, Holm 0.0005 | +0.14 [+0.04, +0.25] 24/15, Holm 0.1996 | – |
| 13 | `pcd_nocritic_PCD_o3mini` | 37 | 2.50 | 3.06 | 3.55 | 4.27 | 4.37 | 1.81 | 512.30 | +0.14 [+0.07, +0.21] 27/17 | +0.28 [+0.21, +0.36] 35/2, Holm 0.0 | +0.43 [+0.35, +0.51] 38/0, Holm 0.0 | – |
| 14 | `rx_c` | 44-45 | 2.50 | 3.06 | 3.66 | 4.15 | 4.36 | 1.83 | 411.70 | +0.17 [+0.10, +0.25] 35/10 | +0.11 [+0.03, +0.20] 24/11, Holm 0.041 | +0.30 [+0.22, +0.38] 35/5, Holm 0.0 | – |
| 15 | `web_study_64k_b_o3mini` | 41 | 2.49 | 3.06 | 3.63 | 4.16 | 4.39 | 1.79 | 559.50 | +0.13 [+0.05, +0.21] 27/15 | – | – | – |
| 16 | `rx_u` | 44-45 | 2.48 | 2.97 | 3.41 | 4.22 | 4.29 | 2.01 | 571.50 | +0.16 [+0.05, +0.26] 34/11 | +0.33 [+0.24, +0.41] 34/1, Holm 0.0 | +0.50 [+0.40, +0.58] 40/1, Holm 0.0 | – |
| 17 | `web_text_64k_b_o3mini` | 36 | 2.48 | 3.03 | 3.56 | 4.15 | 4.37 | 1.85 | 525.10 | +0.16 [+0.06, +0.25] 32/13 | +0.29 [+0.20, +0.38] 35/5, Holm 0.0 | +0.41 [+0.32, +0.51] 38/4, Holm 0.0 | – |
| 18 | `synth_mixed_b_o3mini` | 38 | 2.47 | 3.08 | 3.64 | 4.24 | 4.34 | 1.66 | 479.80 | +0.11 [+0.04, +0.18] 28/16 | – | – | – |
| 19 | `pcd_PCD_o3mini` | 37 | 2.46 | 3.05 | 3.56 | 4.19 | 4.41 | 1.70 | 520.90 | +0.10 [+0.03, +0.18] 29/15 | – | – | – |
| 20 | `web_agent_b_o3mini` | 36 | 2.46 | 2.94 | 3.47 | 4.18 | 4.16 | 2.03 | 507.30 | +0.10 [+0.02, +0.18] 31/14 | – | – | – |
| 21 | `web_agent_o3mini` | 36 | 2.46 | 2.88 | 3.37 | 4.13 | 4.14 | 2.20 | 494.60 | +0.10 [+0.00, +0.20] 26/18 | – | – | – |
| 22 | `pcd_CD_o3mini` | 37 | 2.43 | 3.13 | 3.64 | 4.27 | 4.47 | 1.33 | 516.80 | +0.07 [-0.00, +0.13] 29/15 | – | – | – |
| 23 | `pcd_D_o3mini` | 37 | 2.41 | 3.09 | 3.60 | 4.24 | 4.44 | 1.34 | 524.70 | +0.04 [-0.02, +0.11] 24/17 | – | – | – |
| 24 | `pcd_nodecider_PCD_o3mini` | 37 | 2.40 | 2.97 | 3.45 | 4.21 | 4.24 | 1.70 | 479.90 | +0.04 [-0.04, +0.12] 27/18 | – | – | – |
| 25 | `pcd_k1_PCD_o3mini` | 37 | 2.39 | 2.94 | 3.40 | 4.10 | 4.30 | 1.77 | 568.10 | +0.03 [-0.05, +0.12] 24/21 | – | – | – |
| 26 | `pcd_PD_o3mini` | 37 | 2.39 | 2.96 | 3.46 | 4.14 | 4.30 | 1.66 | 525.80 | +0.03 [-0.06, +0.12] 22/22 | – | – | – |
| 27 | `read_web_chunks_b_o3mini` | 39 | 2.37 | 2.85 | 3.35 | 4.15 | 4.03 | 1.95 | 476.80 | +0.01 [-0.08, +0.10] 24/20 | – | – | – |
| 28 | `synth_k4_b_o3mini` | 38 | 2.37 | 3.16 | 3.82 | 4.24 | 4.41 | 1.01 | 460.10 | +0.01 [-0.04, +0.06] 22/21 | – | – | – |
| 29 | `writer_types_b_o3mini` | 41 | 2.35 | 3.14 | 3.74 | 4.23 | 4.44 | 1.00 | 492.50 | -0.01 [-0.06, +0.04] 20/24 | – | – | – |
| 30 | `writer_only_b_o3mini_r5` | 38 | 2.35 | 3.14 | 3.75 | 4.23 | 4.44 | 1.00 | 486.80 | -0.01 [-0.07, +0.05] 19/26 | – | – | – |
| 31 | `writer_study_b_o3mini` | 41 | 2.35 | 3.13 | 3.71 | 4.25 | 4.43 | 1.00 | 529.20 | +0.02 [-0.04, +0.08] 20/24 | +0.22 [+0.14, +0.30] 30/7, Holm 0.0006 | +0.21 [+0.14, +0.29] 31/8, Holm 0.0006 | – |
| 32 | `writer_v2_b_o3mini` | 42 | 2.35 | 3.13 | 3.77 | 4.29 | 4.33 | 1.00 | 477.00 | -0.02 [-0.08, +0.04] 19/24 | – | – | – |
| 33 | `writer_only_b_o3mini` | 21-35 | 2.33 | 3.10 | 3.71 | 4.16 | 4.43 | 1.00 | 487.70 | – | – | – | – |
| 34 | `pcd_nocritic_none_o3mini` | 37 | 2.33 | 3.10 | 3.63 | 4.22 | 4.45 | 1.00 | 493.40 | -0.04 [-0.10, +0.03] 16/28 | – | – | – |
| 35 | `pcd_P_o3mini` | 37 | 2.31 | 3.08 | 3.58 | 4.22 | 4.46 | 1.00 | 511.90 | -0.05 [-0.11, +0.02] 13/32 | – | – | – |
| 36 | `pcd_nodecider_none_o3mini` | 37 | 2.31 | 3.08 | 3.62 | 4.26 | 4.37 | 1.00 | 464.30 | -0.05 [-0.11, +0.01] 18/27 | – | – | – |
| 37 | `pcd_C_o3mini` | 37 | 2.31 | 3.08 | 3.65 | 4.17 | 4.42 | 1.00 | 485.60 | -0.05 [-0.13, +0.01] 17/26 | – | – | – |
| 38 | `pcd_none_o3mini` | 37 | 2.31 | 3.07 | 3.59 | 4.23 | 4.40 | 1.00 | 507.70 | -0.06 [-0.13, +0.01] 17/27 | – | – | – |
| 39 | `pcd_k1_none_o3mini` | 37 | 2.30 | 3.06 | 3.60 | 4.09 | 4.50 | 1.00 | 557.10 | -0.06 [-0.12, -0.01] 18/27 | – | – | – |
| 40 | `synth_k1_b_o3mini` | 38 | 2.30 | 3.06 | 3.67 | 4.21 | 4.32 | 1.00 | 433.30 | -0.07 [-0.12, -0.01] 16/27 | – | – | – |
| 41 | `writer_design_b_o3mini` | 41 | 2.29 | 3.05 | 3.63 | 4.21 | 4.30 | 1.00 | 541.30 | -0.08 [-0.15, -0.01] 16/28 | – | – | – |
| 42 | `synth_crowd_b_o3mini` | 38 | 2.27 | 3.03 | 3.69 | 4.20 | 4.18 | 1.00 | 419.70 | -0.09 [-0.16, -0.03] 14/30 | – | – | – |
| 43 | `closed_book_o3mini` | 21-35 | 2.23 | 2.97 | 3.52 | 4.18 | 4.21 | 1.00 | 473.10 | -0.10 [-0.16, -0.04] 14/31 | -0.34 [-0.41, -0.27] 2/41, Holm 0.0 | -0.21 [-0.28, -0.13] 6/33, Holm 0.0 | – |
| 44 | `pcd_PC_o3mini` | 37 | 2.19 | 2.92 | 3.39 | 4.20 | 4.18 | 1.00 | 484.80 | -0.17 [-0.26, -0.09] 15/30 | – | – | – |
| 45 | `agent_choose_only_b_o3mini` | 40 | 2.10 | 2.81 | 3.44 | 4.13 | 3.85 | 1.00 | 454.60 | -0.26 [-0.33, -0.18] 8/37 | – | – | – |
| 46 | `web_agent` | 36 | 1.34 | 1.30 | 2.20 | 2.60 | 2.10 | 2.45 | 237.90 | -1.03 [-1.15, -0.90] 0/45 | – | – | – |
| 47 | `pcd_none_llama` | 37 | 1.23 | 1.64 | 2.54 | 2.80 | 2.57 | 1.00 | 282.50 | -1.14 [-1.22, -1.05] 0/45 | – | – | – |
| 48 | `web_text_chunks` | 36 | 1.14 | 1.11 | 2.12 | 2.28 | 1.93 | 2.22 | 234.60 | -1.22 [-1.31, -1.14] 0/45 | – | – | – |
| 49 | `pcd_PCD_llama` | 37 | 1.10 | 1.01 | 1.96 | 2.24 | 1.83 | 2.36 | 222.60 | -1.27 [-1.36, -1.18] 0/45 | – | – | – |
| 50 | `closed_book` | 21-35 | 1.05 | 1.40 | 2.35 | 2.64 | 2.21 | 1.00 | 226.20 | -1.28 [-1.37, -1.19] 0/45 | -1.00 [-1.00, -1.00] 0/45, Holm 0.0 | -0.98 [-1.00, -0.97] 0/45, Holm 0.0 | – |

Incomplete (still being judged): none.

## References (never methods; must_obey.md 5.4)

- `oracle_hint_full_b_o3mini`: SP 2.04, RQ 2.71, grounding 1.00; pairwise vs the writer (DeepSeek) -0.17 [-0.30, -0.05] 12/22
- `oracle_hint_lever_b_o3mini`: SP –, RQ 2.59, grounding –; pairwise vs the writer (DeepSeek) –
- `oracle_hint_class_b_o3mini`: SP –, RQ 2.95, grounding –; pairwise vs the writer (DeepSeek) –

Length: Spearman of SP with words across configurations 0.558.
