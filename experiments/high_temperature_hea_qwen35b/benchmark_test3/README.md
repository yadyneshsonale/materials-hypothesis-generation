# Experiment 27: fresh held-out test set (test3)

**Date.** 2026-10-25.
**Code.** [benchmark_test2.py](../../../benchmark_test2.py) `--set test3`, which is the test2 procedure with the
test3 window.
**Rules.** [must_obey.md](../../../must_obey.md).
**Pre-registered rule.** [loop.md](../../../loop.md) section 11.1, written before any search.

## Why

test and test2 are spent: each was used once for its pre-registered finals and is now round-3 development data
(dev3). Any claim that round 3 improves results needs papers that no round-3 decision has seen.

## Construction (unchanged after seeing any output)

1. **Search.** The corpus query with `FIRST_PDATE` from 2024-02-01 to 2025-07-16, the window just before test2,
   ranked by Europe PMC `citedByCount` and never extended. 49 results.
2. **Screening.** 37 candidates screened, 12 eligible:
   - 14 excluded by the topic rule;
   - 9 already in the corpus or in test2;
   - 1 failed the primary-research check;
   - 1 had an Introduction too short after redaction (435 characters).
3. **Targets and queries.** The same as test2: GPT-5.6 extracted the target from the non-Introduction sections; the
   v3 writer, checker and gate wrote the queries, followed by the v3.1 gap templates.
   - The query stage was resumed twice after GPT-5.6 rate limits. Only finished cases are saved, so a resumed case
     restarts from scratch with the same procedure.

## Result

| Property | Value |
|---|---|
| Papers | 12, dated 2024-01-01 to 2025-06-01 (earliest of online, first and print dates). All precede GPT-5.6's cutoff, so the query writer could know them; they are flagged, the same residual risk as the original 12. PMC11302478 (2024-01-01 issue date) is 1 day after Llama-3.3's cutoff and inside the one-month margin |
| Citations | 38, 12, 2, then 1 for each of the rest |
| Gap types | understanding 8, design 4 |
| Gate | 35/36 levels pass; one expert level fails and is flagged and kept |
| Answer-word overlap (mean) | broad 1.7%, problem 2.2%, expert 4.1% |
| Venues | Materials 3, Science Advances 2, Heliyon 2, Scientific Reports, Small Methods, RSC Advances, Entropy, Science and Technology of Advanced Materials |
| Evidence pools | 226–279 text chunks and 40–51 cards per case; 0 late or self records; all 120 target fields filled |

## Use

test3 is run once, for the configurations fixed by loop.md 11.1 rule 4; results are in loop.md section 11. The raw
XML (`papers/`) is not committed.

## Limits

- All 12 papers precede GPT-5.6's cutoff (unlike test2's 5 post-cutoff papers).
- The topic screen and target extractor are GPT-5.6 calls, not validated by an expert.
- Targets come from the same extractor as test2 but differ from the original 12 (experiment 3).
