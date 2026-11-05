# Experiment 46: strong research proposals as the only objective (phases 0-1)

Pre-registered in loop.md 27.1. SP = mean of plausibility, testability, usefulness (RQ judge, three DeepSeek calls) and grounding (one DeepSeek call) minus 1, on 0-4; RQ alone while grounding is not validated. Pairwise: net preference over the closed-book writer, both orders (a win needs both), paired by paper; DeepSeek decides, GPT-5.6 confirms, o1 alongside.

**Grounding validation** (G1-G4): valid = True; {"G1_swap_lowers": true, "G2_no_citation_mean_le_1.5": true, "G3_retest_rho_ge_0.70": true, "G4_evidence_writer_above_closed_book": true}. Swap: {"pairs": 134, "original_mean": 1.858, "control_mean": 1.022, "control_higher_share": 0.0, "drop_by_paper": {"papers": 45, "a_mean": 1.852, "b_mean": 1.022, "diff": 0.83, "ci95": [0.652, 1.022], "up": 39, "down": 0, "p": 0.0}}. Removal: {"pairs": 135, "original_mean": 1.867, "control_mean": 1.0, "control_higher_share": 0.0, "drop_by_paper": {"papers": 45, "a_mean": 1.867, "b_mean": 1.0, "diff": 0.867, "ci95": [0.681, 1.067], "up": 40, "down": 0, "p": 0.0}}. Re-test: {"pairs": 135, "rho": 0.82, "mean_abs_diff": 0.311}. Known groups (evidence writer minus closed-book writer): +0.87 [+0.68, +1.07] 40/0.

**RQ controls this session** (one call): passed = False (216 items); gaps {"usefulness_positive_minus_random": 1.389, "rq_positive_minus_generic": 0.954, "plausibility_positive_minus_intervention_swap": 0.861, "plausibility_positive_minus_mechanism_swap": 1.445}.
**RQ controls this session** (three calls): passed = True (216 items); gaps {"usefulness_positive_minus_random": 1.547, "rq_positive_minus_generic": 1.099, "plausibility_positive_minus_intervention_swap": 0.75, "plausibility_positive_minus_mechanism_swap": 1.435}.

**Writer RQ drift** (this session minus experiment 43): –.

**Incumbent** (rule in loop.md 27.1): {"incumbent": "writer_only_b_o3mini", "rule": "no method passed; the writer stays"}

## Leaderboard (configurations with complete RQ)

| # | Configuration | Exp. | SP | RQ | Plaus. | Test. | Useful. | Grounding | Words | SP vs writer | Pairwise vs writer: DeepSeek | o1 | GPT-5.6 |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| 1 | `web_text_64k_b_o3mini` | 36 | 2.48 | 3.03 | 3.56 | 4.15 | 4.37 | 1.87 | 525.10 | +0.15 [+0.04, +0.26] 30/15 | – | – | – |
| 2 | `writer_only_b_o3mini` | 21-35 | 2.33 | 3.10 | 3.71 | 4.16 | 4.43 | 1.00 | 487.70 | – | – | – | – |
| 3 | `closed_book_o3mini` | 21-35 | 2.21 | 2.97 | 3.52 | 4.18 | 4.21 | 1.00 | 473.10 | -0.12 [-0.19, -0.05] 6/19 | – | – | – |
| 4 | `closed_book` | 21-35 | 1.05 | 1.40 | 2.35 | 2.64 | 2.21 | 1.00 | 226.20 | -1.28 [-1.37, -1.19] 0/45 | – | -0.98 [-0.99, -0.96] 0/32, Holm 0.0 | – |
| 5 | `writer_study_b_o3mini` | 41 | – | 3.13 | 3.71 | 4.25 | 4.43 | – | 529.20 | – | – | – | – |
| 6 | `web64k_v2_b_o3mini` | 42 | – | 3.06 | 3.62 | 4.27 | 4.30 | – | 530.40 | – | – | – | – |
| 7 | `rx_base` | 44-45 | – | 3.05 | 3.59 | 4.17 | 4.39 | – | 535.00 | – | – | – | – |
| 8 | `rx_r` | 44-45 | – | 3.03 | 3.56 | 4.19 | 4.35 | – | 548.10 | – | – | – | – |
| 9 | `rx_u` | 44-45 | – | 2.97 | 3.41 | 4.22 | 4.29 | – | 571.50 | – | – | – | – |
| 10 | `rx_ru` | 44-45 | – | 3.00 | 3.43 | 4.22 | 4.34 | – | 579.10 | – | – | – | – |
| 11 | `rx_c` | 44-45 | – | 3.06 | 3.66 | 4.15 | 4.36 | – | 411.70 | – | – | – | – |
| 12 | `rx_ruc_select` | 44-45 | – | 2.86 | 3.38 | 4.16 | 4.04 | – | 371.00 | – | – | – | – |
| 13 | `rx_ruc` | 44-45 | – | 2.98 | 3.48 | 4.18 | 4.27 | – | 413.60 | – | – | – | – |
| 14 | `edit_rx_base` | 44-45 | – | 3.04 | 3.55 | 4.20 | 4.39 | – | 535.40 | – | – | – | – |
| 15 | `edit_rx_r` | 44-45 | – | 2.98 | 3.50 | 4.18 | 4.25 | – | 548.80 | – | – | – | – |

Incomplete (still being judged): none.

## References (never methods; must_obey.md 5.4)

- `oracle_hint_full_b_o3mini`: SP –, RQ 2.71, grounding –; pairwise vs the writer (DeepSeek) –

Length: Spearman of SP with words across configurations None.
