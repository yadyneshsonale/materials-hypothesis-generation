# Experiment 49 pilot: per-paper generate → critique → narrow

Pre-registered in loop.md 28.1. 8 dev papers × 3 levels × 2 samples. o3-mini agents; DeepSeek RQ (3 calls), non-copying and pairwise v2; o1 pairwise v2.

**Decision rule: no-go**

| Method | RQ | Plaus. | Test. | Useful. | Non-copying |
|---|---:|---:|---:|---:|---:|
| `perpaper` | 3.15 | 3.65 | 4.17 | 4.64 | 3.81 |
| `agent_draft_ground_b_o3mini` | 2.94 | 3.40 | 4.17 | 4.25 | 2.81 |
| `writer_only_b_o3mini` | 3.05 | 3.69 | 4.01 | 4.45 | 2.88 |
| `rx_r` | 2.73 | 3.11 | 4.19 | 3.89 | 1.85 |

Non-copying of the rank-1 hypothesis against its own source paper (diagnostic): 4.15

## perpaper vs `writer_only_b_o3mini` (paired by paper)

- RQ: +0.11 [-0.13, +0.37], 5 vs 3 papers; plausibility -0.04 [-0.38, +0.27], 4 vs 3 papers; testability +0.17 [-0.05, +0.42], 5 vs 3 papers; usefulness +0.19 [-0.13, +0.51], 6 vs 2 papers
- Non-copying: +0.94 [+0.29, +1.62], 6 vs 2 papers
- Pairwise v2: DeepSeek +0.35 [+0.19, +0.52], 7 vs 0 papers; o1 +0.58 [+0.38, +0.77], 7 vs 0 papers

## perpaper vs `agent_draft_ground_b_o3mini` (paired by paper)

- RQ: +0.21 [+0.07, +0.35], 6 vs 2 papers; plausibility +0.26 [+0.01, +0.44], 7 vs 1 papers; testability +0.00 [-0.18, +0.17], 3 vs 3 papers; usefulness +0.39 [+0.18, +0.57], 7 vs 1 papers
- Non-copying: +1.00 [+0.42, +1.58], 7 vs 1 papers
- Pairwise v2: DeepSeek -0.04 [-0.19, +0.08], 3 vs 3 papers; o1 +0.40 [+0.23, +0.56], 7 vs 0 papers

## Diagnostics

- runs_ok: 48
- runs_failed: 0
- calls_mean: 135.2
- calls_max: 226
- minutes_mean: 22.1
- papers_per_run: 9.88
- papers_with_accepted: 9.79
- papers_dropped_share: 0.008
- paper_errors: 0
- pool_after_dedupe_mean: 14.0
- rounds_to_accept: {1: 249, 2: 100, 3: 33, 4: 31, 5: 26, 6: 10, 7: 6, 8: 5, 9: 1, 10: 2, 11: 1, 12: 4, 15: 1, 18: 1}
- rounds_mean: 2.42
- accepted_in_round_1_share: 0.525
- criterion_pass_rate_round_1: {'sound': 0.292, 'testable': 0.982, 'beyond_paper': 0.838}
- criterion_pass_rate_all_rounds: {'sound': 0.223, 'testable': 0.986, 'beyond_paper': 0.851}
- rank1_source_paper_grade: {3: 31, 2: 17}
- distinct_rank1_sources: 38
- rank1_tied_share: 0.375
- tournament_formats: {'swiss+round_robin': 48}
- rubber_stamp_flag: False

## Leakage

{'counters': {'temporal_violations': 0, 'test_paper_leaks': 0, 'family_leaks': 0, 'target_doi_or_title_leaks': 0, 'invalid_citations': 0}, 'records_rechecked': 10442, 'date_violations': 0, 'background': {'kg_facts_seen': 2464, 'text_passages_seen': 1066, 'text_unknown_ids': 0, 'text_hea_mentions': 0, 'text_date_violations': 0}}
