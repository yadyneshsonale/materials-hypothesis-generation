# test4: fresh held-out set for experiment 35 (spent)

**Rule.** Pre-registered in [loop.md](../../../loop.md) section 16.1 C1 before any search. Built by
[benchmark_test2.py](../../../benchmark_test2.py) `--set test4`, the same procedure as test2 and test3.
- Europe PMC TOPIC query, FIRST_PDATE from 2024-11-01 to 2026-10-26, sorted by citations, never extended.
- Excludes the 50 corpus papers (which include the original 12), test2, test3, and near-duplicate titles.
- The same primary-research, introduction (at least 1,000 characters after redaction) and GPT-5.6 topic screens.
- The first 24 that qualify.
- Answer keys from the abstract and non-introduction sections. Queries from the v3 writer, checker and gate, then the
  v3.1 gap templates.

The window starts after every candidate generator's cutoff plus 31 days.

**Result.** 9 papers qualified, not 24.

| Screened | Topic rule | Already used | Structure checks | Eligible |
|---:|---:|---:|---:|---:|
| 66 | 29 failed | 23 | 5 failed | **9** |

The rule was not changed afterwards. Addendum 2 (loop.md 16.1) recorded this before any case was read.

| | |
|---|---|
| Dates | 2024-11-01 to 2026-03-16 (8 in 2024-11 to 2025-06, 1 in 2026) |
| Journals | Materials (Basel) 6; Advanced Science, Nanoscale Advances, Micromachines 1 each |
| Citations at build time | 0–3 (recent papers) |
| Gap type | 9 design (the v3 queries are kept, as for every design case) |
| Gate | broad 9 / 9, problem-constrained 9 / 9, expert-context 6 / 9 pass. The 3 failures keep the best of 4 attempts, as in earlier sets |
| Answer-word overlap | 1.2% / 1.9% / 3.8% (broad / problem / expert) |
| Answer-key audit (after the finals) | GPT-5.6: 5 ok, 4 minor. DeepSeek: 7 ok, 2 minor. None flagged |

**Blindness.** No title, query or answer key was read before the finals. Scripts printed counts only.

**Use.** Run once on 2026-10-26 for the experiment-35 replication: the incumbent writer and the Llama baseline, 54
runs each, marked final. Results are in loop.md 16.4. test4 is now **spent** (must_obey.md section 1).

**Files.**
- `cases/`: frozen cases;
- `targets/`: answer keys;
- `build_log/`: the query writer's history;
- `screening.json`, `selected.json`, `metadata.json`.

Downloaded XML (`papers/`) and the build log are not committed.
