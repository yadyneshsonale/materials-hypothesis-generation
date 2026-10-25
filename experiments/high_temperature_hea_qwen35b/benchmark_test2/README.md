# Experiment 25: fresh held-out test set (test2)

**Date.** 2026-10-25.
**Code.**
- [benchmark_test2.py](../../../benchmark_test2.py)
- [test_benchmark_test2.py](../../../test_benchmark_test2.py)

**Rules.** [must_obey.md](../../../must_obey.md).
**Pre-registered rule.** [loop.md](../../../loop.md) section 10.1, written before any search.

## Why

The 4-paper test split was used once (loop.md section 7). Since then its titles were printed during a probe
analysis and one target was quoted in experiment 22. A second look would therefore not be blind to rules that
favour study-type answers. test2 is a new set of held-out papers whose titles, queries and targets the method
designer does not read; only automated summaries are inspected.

## Construction (unchanged after seeing any output)

1. **Search.** The corpus query of `data/corpus/README.md` with `FIRST_PDATE` from 2026-02-17 (after GPT-5.6's
   cutoff) to 2026-10-15. Only 5 eligible papers fell in that window, so the rule extended it back month by month
   to 2025-07-17.
2. **Screening.** 41 candidates screened, 12 eligible:
   - 24 excluded by the topic rule (GPT-5.6, title and abstract only);
   - 2 already in the corpus;
   - 2 without an Introduction section;
   - 1 failed the primary-research check.

   Citation counts are 0 for all candidates, so the order is Europe PMC's.
3. **Hidden targets.** GPT-5.6 extracted the experiment-3 10-field schema from the abstract and the
   non-Introduction sections. All 120 fields are non-empty.
4. **Queries.** The v3 writer wrote from the redacted Introduction (1,687–6,426 characters kept), with the v3
   checker, lexical gate and up to 4 rounds. The v3.1 gap classifier then labelled the gap, and non-design gaps were
   rewritten with the v3.1 templates.
5. **Metadata.** Rows in the corpus format (`metadata.json`), with work family = DOI. The harness adds them at load
   time; test2 papers contribute no evidence records.

## Result

| Property | Value |
|---|---|
| Papers | 12, dated 2025-07-01 to 2026-07-01 (earliest of online, first and print dates). 5 are after 2026-02-16, so no model used to build or judge the set can know them. 7 are flagged: the query writer could know them, the same residual risk as the original 12 |
| Gap types | understanding 6, design 5, method 1 |
| Gate | 34/36 levels pass. Two expert levels fail and are flagged and kept |
| Answer-word overlap (mean) | broad 2.0%, problem 3.3%, expert 4.9% |
| Venues | Materials (MDPI) 8, Entropy 2, Nanomaterials 1, ACS Applied Nano Materials 1 |
| Evidence pools | 279–299 text chunks and 51–55 cards per case; 0 records dated on or after the case date; 0 self-records |

## Use

test2 is run once, for the configurations fixed in loop.md section 10.5. Results are in loop.md section 10.6 and
in `loop/final2_test2*.json`. The raw XML (`papers/`) is not committed.

## Limits

- Recent papers have no citations yet, so "most cited" cannot rank them, and the open-access JATS set is dominated
  by MDPI journals. This differs from the corpus, which was ranked by citations.
- The topic screen and the target extractor are GPT-5.6 calls, not validated by an expert.
- The targets were extracted by a different model and prompt from the original 12 (Qwen, experiment 3), so test2
  scores are comparable within test2, not directly with the original 12.
