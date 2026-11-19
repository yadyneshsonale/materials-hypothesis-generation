# Experiment 49 pilot: per-paper generate → critique → narrow

Pre-registered in loop.md 28.1. 8 dev papers × 3 levels × 2 samples. o3-mini agents; DeepSeek RQ (3 calls), non-copying and pairwise v2; o1 pairwise v2.

**Decision rule: go: run all 45 papers**

| Method | RQ | Plaus. | Test. | Useful. | Non-copying |
|---|---:|---:|---:|---:|---:|
| `perpaper_dated` | 3.15 | 3.67 | 4.17 | 4.62 | 3.85 |
| `agent_draft_ground_b_o3mini` | 2.94 | 3.40 | 4.17 | 4.25 | 2.81 |
| `writer_only_b_o3mini` | 3.05 | 3.69 | 4.01 | 4.45 | 2.88 |
| `rx_r` | 2.73 | 3.11 | 4.19 | 3.89 | 1.85 |

Non-copying of the rank-1 hypothesis against its own source paper (diagnostic): 4.10

## perpaper vs `writer_only_b_o3mini` (paired by paper)

- RQ: +0.10 [-0.14, +0.41], 4 vs 4 papers; plausibility -0.02 [-0.28, +0.26], 3 vs 5 papers; testability +0.16 [-0.10, +0.52], 4 vs 4 papers; usefulness +0.17 [-0.12, +0.51], 5 vs 2 papers
- Non-copying: +0.98 [+0.19, +1.81], 7 vs 1 papers
- Pairwise v2: DeepSeek +0.44 [+0.31, +0.62], 8 vs 0 papers; o1 +0.50 [+0.21, +0.73], 7 vs 1 papers

## perpaper vs `agent_draft_ground_b_o3mini` (paired by paper)

- RQ: +0.21 [+0.02, +0.38], 7 vs 1 papers; plausibility +0.27 [+0.08, +0.45], 6 vs 1 papers; testability -0.01 [-0.19, +0.14], 3 vs 3 papers; usefulness +0.38 [+0.12, +0.62], 7 vs 1 papers
- Non-copying: +1.04 [+0.40, +1.65], 7 vs 1 papers
- Pairwise v2: DeepSeek +0.02 [-0.15, +0.23], 2 vs 3 papers; o1 +0.42 [+0.25, +0.56], 7 vs 0 papers

## Diagnostics

- runs_ok: 48
- runs_failed: 0
- calls_mean: 132.5
- calls_max: 176
- minutes_mean: 21.9
- papers_per_run: 9.88
- papers_with_accepted: 9.83
- papers_dropped_share: 0.004
- paper_errors: 0
- pool_after_dedupe_mean: 14.3
- rounds_to_accept: {1: 254, 2: 99, 3: 54, 4: 22, 5: 16, 6: 6, 7: 6, 8: 7, 9: 2, 10: 2, 12: 1, 14: 2, 16: 1}
- rounds_mean: 2.22
- accepted_in_round_1_share: 0.536
- criterion_pass_rate_round_1: {'sound': 0.302, 'testable': 0.976, 'beyond_paper': 0.856}
- criterion_pass_rate_all_rounds: {'sound': 0.247, 'testable': 0.982, 'beyond_paper': 0.875}
- rank1_source_paper_grade: {3: 31, 2: 17}
- distinct_rank1_sources: 40
- rank1_tied_share: 0.5
- tournament_formats: {'swiss+round_robin': 48}
- rubber_stamp_flag: False

## Leakage

{'counters': {'temporal_violations': 0, 'test_paper_leaks': 0, 'family_leaks': 0, 'target_doi_or_title_leaks': 0, 'invalid_citations': 0}, 'records_rechecked': 10442, 'date_violations': 0, 'background': {'kg_facts_seen': 2464, 'text_passages_seen': 1074, 'text_unknown_ids': 0, 'text_hea_mentions': 0, 'text_undated': 0, 'text_date_violations': 0}}
