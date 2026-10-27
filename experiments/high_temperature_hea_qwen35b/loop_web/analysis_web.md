# Experiment 36: web search for every baseline (harness)

## W1: each baseline with web search vs the same baseline without evidence (primary)

| web configuration | baseline | GPT-5.6 diff [CI] | DeepSeek diff [CI] | decision |
|---|---|---|---|---|
| web_text_chunks | closed_book | -0.00 [-0.06, +0.06] (45 papers, Holm p 1.0) | +0.02 [-0.05, +0.10] (45 papers, Holm p 1.0) | no detectable effect |
| web_agent | closed_book | -0.08 [-0.15, -0.01] (45 papers, Holm p 0.6968) | -0.08 [-0.15, +0.00] (45 papers, Holm p 1.0) | hurts |
| web_agent_o3mini | closed_book_o3mini | +0.00 [-0.07, +0.07] (24 papers, Holm p 1.0) | +0.13 [+0.02, +0.25] (24 papers, Holm p 0.4655) | no detectable effect |
| web_text_chunks_b_o3mini | writer_only_b_o3mini | -0.02 [-0.07, +0.04] (45 papers, Holm p 1.0) | +0.04 [-0.05, +0.12] (45 papers, Holm p 1.0) | no detectable effect |
| web_agent_b_o3mini | writer_only_b_o3mini | -0.07 [-0.11, -0.02] (45 papers, Holm p 0.1575) | -0.05 [-0.13, +0.04] (45 papers, Holm p 1.0) | hurts |

## W2: web corpus vs fixed corpus, same configuration

| configuration | GPT-5.6 web − fixed [CI] | DeepSeek web − fixed [CI] |
|---|---|---|
| web_text_chunks | +0.07 [+0.03, +0.13] (24 papers, Holm p 1.0) | +0.05 [-0.04, +0.13] (24 papers, Holm p 1.0) |
| web_text_chunks_b_o3mini | -0.07 [-0.16, +0.01] (24 papers, Holm p 1.0) | -0.06 [-0.17, +0.06] (24 papers, Holm p 1.0) |
| web_text_chunks_mbr_b_o3mini | -0.06 [-0.12, -0.00] (36 papers, Holm p 1.0) | +0.01 [-0.10, +0.11] (36 papers, Holm p 1.0) |
| web_text_4k_b_o3mini | -0.09 [-0.18, -0.01] (24 papers, Holm p 1.0) | -0.07 [-0.20, +0.06] (24 papers, Holm p 1.0) |
| web_text_64k_b_o3mini | -0.01 [-0.12, +0.09] (24 papers, Holm p 1.0) | -0.04 [-0.15, +0.06] (24 papers, Holm p 1.0) |
| web_papers_n1_b_o3mini | -0.02 [-0.08, +0.04] (36 papers, Holm p 1.0) | +0.15 [+0.06, +0.24] (36 papers, Holm p 1.0) |
| web_papers_n3_b_o3mini | +0.01 [-0.05, +0.07] (36 papers, Holm p 1.0) | +0.20 [+0.09, +0.32] (36 papers, Holm p 0.1288) |
| web_papers_n10_b_o3mini | +0.03 [-0.04, +0.09] (24 papers, Holm p 1.0) | +0.28 [+0.17, +0.39] (24 papers, Holm p 0.078) |
| web_papers_n30_b_o3mini | -0.00 [-0.06, +0.05] (36 papers, Holm p 1.0) | +0.18 [+0.09, +0.27] (36 papers, Holm p 0.0841) |
| web_papers_random10_b_o3mini | -0.04 [-0.10, +0.02] (24 papers, Holm p 1.0) | +0.18 [+0.07, +0.30] (24 papers, Holm p 0.7182) |
| web_precedent_decide | -0.04 [-0.12, +0.02] (8 papers, Holm p 1.0) | -0.02 [-0.16, +0.14] (8 papers, Holm p 1.0) |
| web_decide_then_ground | -0.12 [-0.21, -0.03] (8 papers, Holm p 1.0) | -0.02 [-0.12, +0.07] (8 papers, Holm p 1.0) |
| web_decide_then_ground_b | +0.01 [-0.07, +0.08] (8 papers, Holm p 1.0) | +0.03 [-0.06, +0.13] (8 papers, Holm p 1.0) |
| web_decide_then_ground_b_o3mini | -0.04 [-0.12, +0.02] (8 papers, Holm p 1.0) | +0.06 [-0.12, +0.24] (8 papers, Holm p 1.0) |
| web_decide_then_ground_v2_o3mini | -0.02 [-0.12, +0.07] (8 papers, Holm p 1.0) | +0.10 [+0.05, +0.16] (8 papers, Holm p 1.0) |
| web_multi_decision_ground_o3mini | -0.01 [-0.12, +0.08] (8 papers, Holm p 1.0) | +0.12 [-0.04, +0.27] (8 papers, Holm p 1.0) |
| web_trend_chain | -0.08 [-0.18, +0.02] (8 papers, Holm p 1.0) | +0.01 [-0.11, +0.12] (8 papers, Holm p 1.0) |
| web_trend_chain_o3mini | +0.09 [-0.02, +0.20] (8 papers, Holm p 1.0) | -0.01 [-0.18, +0.20] (8 papers, Holm p 1.0) |
| web_trend_ground_b | +0.05 [-0.04, +0.15] (8 papers, Holm p 1.0) | +0.02 [-0.06, +0.12] (8 papers, Holm p 1.0) |
| web_trend_ground_b_o1 | +0.03 [-0.05, +0.10] (8 papers, Holm p 1.0) | +0.10 [-0.06, +0.26] (8 papers, Holm p 1.0) |
| web_trend_ground_b_o3mini | +0.01 [-0.04, +0.06] (36 papers, Holm p 1.0) | +0.07 [-0.02, +0.17] (36 papers, Holm p 1.0) |
| web_trend_ground_bm25_b_o3mini | -0.02 [-0.09, +0.06] (8 papers, Holm p 1.0) | +0.18 [-0.04, +0.41] (8 papers, Holm p 1.0) |
| web_trend_ground_iter_b_o3mini | -0.03 [-0.20, +0.13] (8 papers, Holm p 1.0) | +0.08 [-0.09, +0.28] (8 papers, Holm p 1.0) |
| web_trend_focus_ground_b_o3mini | +0.05 [-0.10, +0.20] (8 papers, Holm p 1.0) | -0.03 [-0.34, +0.21] (8 papers, Holm p 1.0) |
| web_trend_niche_ground_b_o3mini | +0.05 [-0.04, +0.17] (8 papers, Holm p 1.0) | +0.11 [-0.09, +0.35] (8 papers, Holm p 1.0) |
| web_trend_o1_ground_b_o3mini | -0.03 [-0.14, +0.06] (8 papers, Holm p 1.0) | +0.13 [+0.02, +0.28] (8 papers, Holm p 1.0) |
| web_niche_ground_b_o1 | +0.04 [-0.02, +0.09] (8 papers, Holm p 1.0) | +0.03 [-0.16, +0.24] (8 papers, Holm p 1.0) |
| web_niche_ground_b_o3mini | +0.05 [-0.03, +0.14] (8 papers, Holm p 1.0) | -0.07 [-0.17, +0.05] (8 papers, Holm p 1.0) |
| web_scaffold_ensemble | +0.01 [-0.08, +0.08] (12 papers, Holm p 1.0) | +0.01 [-0.05, +0.06] (12 papers, Holm p 1.0) |
| web_scaffold_ensemble_o3mini | +0.06 [-0.02, +0.14] (8 papers, Holm p 1.0) | +0.03 [-0.07, +0.11] (8 papers, Holm p 1.0) |

## W3: leaderboard (mean over papers)

| configuration | runs | failed | papers | GPT-5.6 | DeepSeek |
|---|---:|---:|---:|---:|---:|
| writer_only_b_o3mini (fixed, no evidence) | 270 | 0 | 45 | 0.623 | 0.575 |
| web_trend_ground_b_o1 | 216 | 0 | 36 | 0.622 | 0.617 |
| web_text_64k_b_o3mini | 216 | 0 | 36 | 0.617 | 0.661 |
| web_niche_ground_b_o1 | 216 | 0 | 36 | 0.608 | 0.618 |
| web_text_chunks_b_o3mini | 270 | 0 | 45 | 0.607 | 0.61 |
| web_trend_ground_b_o3mini | 216 | 0 | 36 | 0.602 | 0.619 |
| web_scaffold_ensemble_o3mini | 216 | 0 | 36 | 0.596 | 0.589 |
| web_papers_n30_b_o3mini | 216 | 0 | 36 | 0.59 | 0.662 |
| web_trend_chain_o3mini | 216 | 0 | 36 | 0.579 | 0.568 |
| web_text_chunks_mbr_b_o3mini | 216 | 0 | 36 | 0.575 | 0.583 |
| closed_book_o3mini (fixed, no evidence) | 144 | 0 | 24 | 0.575 | 0.542 |
| web_papers_n10_b_o3mini | 216 | 0 | 36 | 0.574 | 0.692 |
| web_trend_focus_ground_b_o3mini | 216 | 0 | 36 | 0.574 | 0.603 |
| web_niche_ground_b_o3mini | 216 | 0 | 36 | 0.573 | 0.524 |
| web_multi_decision_ground_o3mini | 216 | 0 | 36 | 0.568 | 0.581 |
| web_decide_then_ground_v2_o3mini | 216 | 0 | 36 | 0.567 | 0.61 |
| web_trend_niche_ground_b_o3mini | 216 | 0 | 36 | 0.567 | 0.561 |
| web_trend_o1_ground_b_o3mini | 216 | 0 | 36 | 0.566 | 0.611 |
| web_decide_then_ground_b_o3mini | 216 | 0 | 36 | 0.565 | 0.591 |
| web_trend_ground_iter_b_o3mini | 216 | 0 | 36 | 0.56 | 0.552 |
| web_agent_o3mini | 270 | 0 | 45 | 0.559 | 0.555 |
| web_agent_b_o3mini | 270 | 0 | 45 | 0.558 | 0.527 |
| web_papers_random10_b_o3mini | 216 | 0 | 36 | 0.549 | 0.58 |
| web_trend_ground_bm25_b_o3mini | 216 | 0 | 36 | 0.542 | 0.58 |
| web_papers_n3_b_o3mini | 216 | 0 | 36 | 0.525 | 0.564 |
| web_scaffold_ensemble | 216 | 0 | 36 | 0.523 | 0.319 |
| closed_book (fixed, no evidence) | 270 | 0 | 45 | 0.502 | 0.306 |
| web_text_chunks | 270 | 0 | 45 | 0.501 | 0.326 |
| web_text_4k_b_o3mini | 216 | 0 | 36 | 0.5 | 0.506 |
| web_papers_n1_b_o3mini | 216 | 0 | 36 | 0.495 | 0.493 |
| web_trend_chain | 216 | 0 | 36 | 0.449 | 0.275 |
| web_decide_then_ground_b | 216 | 0 | 36 | 0.432 | 0.247 |
| web_trend_ground_b | 216 | 0 | 36 | 0.427 | 0.236 |
| web_agent | 270 | 0 | 45 | 0.419 | 0.231 |
| web_decide_then_ground | 216 | 0 | 36 | 0.381 | 0.2 |
| web_precedent_decide | 216 | 0 | 36 | 0.326 | 0.206 |

Rank agreement web vs fixed: {"gpt": {"configs": 30, "spearman": 0.788}, "deep": {"configs": 30, "spearman": 0.721}}

Agent tool use: {"web_agent": {"runs": 270, "tool_calls": 8.419, "searches": 3.611, "reference_lookups": 0.004, "pages_read": 4.711, "papers_read": 1.548, "runs_reading_nothing": 5, "cited_records": 3.678}, "web_agent_o3mini": {"runs": 270, "tool_calls": 4.185, "searches": 2.304, "reference_lookups": 0.011, "pages_read": 1.837, "papers_read": 1.678, "runs_reading_nothing": 7, "cited_records": 1.478}, "web_agent_b_o3mini": {"runs": 270, "tool_calls": 4.222, "searches": 2.23, "reference_lookups": 0.007, "pages_read": 1.941, "papers_read": 1.715, "runs_reading_nothing": 3, "cited_records": 1.522}}

## W5: leakage

Counters: {} over 7398 runs; suite: {} over 1188 runs.

Evidence dates re-checked: {"violations": 0, "examples": [], "unresolved_records": 0}

Version check (share of a held-out paper's 12-word passages in any corpus paper): {"corpus_papers": 10556, "max_share": 0.0154, "p99_share": 0.0019, "median_share": 0.0, "papers_at_or_above_1pct": 2}

| configuration | answer-word excess, web | fixed corpus | web − fixed [CI] |
|---|---:|---:|---|
| web_text_chunks | 0.048 | 0.037 | +0.01 [-0.01, +0.03] (24 papers, Holm p 1.0) |
| web_text_chunks_b_o3mini | 0.048 | 0.037 | +0.01 [-0.01, +0.03] (24 papers, Holm p 1.0) |
| web_text_chunks_mbr_b_o3mini | 0.048 | 0.029 | +0.02 [+0.00, +0.04] (36 papers, Holm p 1.0) |
| web_text_4k_b_o3mini | 0.015 | 0.019 | -0.01 [-0.02, +0.01] (24 papers, Holm p 1.0) |
| web_text_64k_b_o3mini | 0.063 | 0.007 | +0.06 [+0.04, +0.08] (24 papers, Holm p 0.0) |
| web_papers_n1_b_o3mini | 0.011 | 0.016 | -0.01 [-0.02, +0.01] (36 papers, Holm p 1.0) |
| web_papers_n3_b_o3mini | 0.027 | 0.02 | +0.01 [-0.01, +0.03] (36 papers, Holm p 1.0) |
| web_papers_n10_b_o3mini | 0.044 | 0.028 | +0.02 [-0.02, +0.05] (24 papers, Holm p 1.0) |
| web_papers_n30_b_o3mini | 0.063 | -0.004 | +0.07 [+0.04, +0.09] (36 papers, Holm p 0.0) |
| web_papers_random10_b_o3mini | 0.038 | 0.011 | +0.04 [-0.00, +0.07] (24 papers, Holm p 0.5902) |
| web_precedent_decide | 0.051 | 0.012 | +0.04 [-0.01, +0.10] (8 papers, Holm p 1.0) |
| web_decide_then_ground | 0.055 | 0.096 | -0.01 [-0.04, +0.03] (8 papers, Holm p 1.0) |
| web_decide_then_ground_b | 0.057 | 0.098 | -0.00 [-0.05, +0.04] (8 papers, Holm p 1.0) |
| web_decide_then_ground_b_o3mini | 0.065 | 0.089 | +0.01 [-0.02, +0.05] (8 papers, Holm p 1.0) |
| web_decide_then_ground_v2_o3mini | 0.06 | 0.094 | +0.00 [-0.04, +0.04] (8 papers, Holm p 1.0) |
| web_multi_decision_ground_o3mini | 0.076 | 0.053 | +0.04 [+0.01, +0.08] (8 papers, Holm p 1.0) |
| web_trend_chain | 0.049 | 0.015 | +0.04 [-0.02, +0.10] (8 papers, Holm p 1.0) |
| web_trend_chain_o3mini | 0.062 | 0.029 | +0.04 [-0.04, +0.10] (8 papers, Holm p 1.0) |
| web_trend_ground_b | 0.063 | 0.058 | +0.02 [-0.02, +0.06] (8 papers, Holm p 1.0) |
| web_trend_ground_b_o1 | 0.074 | 0.054 | +0.04 [+0.00, +0.08] (8 papers, Holm p 1.0) |
| web_trend_ground_b_o3mini | 0.078 | 0.024 | +0.05 [+0.03, +0.08] (36 papers, Holm p 0.0084) |
| web_trend_ground_bm25_b_o3mini | 0.079 | 0.024 | +0.07 [+0.04, +0.10] (8 papers, Holm p 0.2106) |
| web_trend_ground_iter_b_o3mini | 0.081 | 0.069 | +0.04 [+0.00, +0.07] (8 papers, Holm p 1.0) |
| web_trend_focus_ground_b_o3mini | 0.076 | 0.053 | +0.05 [-0.01, +0.10] (8 papers, Holm p 1.0) |
| web_trend_niche_ground_b_o3mini | 0.07 | 0.058 | +0.04 [-0.01, +0.07] (8 papers, Holm p 1.0) |
| web_trend_o1_ground_b_o3mini | 0.072 | 0.062 | +0.03 [-0.01, +0.07] (8 papers, Holm p 1.0) |
| web_niche_ground_b_o1 | 0.072 | 0.094 | +0.00 [-0.04, +0.04] (8 papers, Holm p 1.0) |
| web_niche_ground_b_o3mini | 0.069 | 0.091 | +0.01 [-0.02, +0.04] (8 papers, Holm p 1.0) |
| web_scaffold_ensemble | 0.051 | 0.042 | +0.02 [-0.04, +0.08] (12 papers, Holm p 1.0) |
| web_scaffold_ensemble_o3mini | 0.061 | 0.034 | +0.04 [-0.02, +0.10] (8 papers, Holm p 1.0) |
