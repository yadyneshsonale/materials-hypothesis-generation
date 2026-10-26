# Superseded: first citation-graph attempt of experiment 32 (not analysed)

These are the first experiment-17 runs on the v4 input: 120 runs with both judges and audits, made 2026-10-26 before
a parser fix. They are kept for the record and are excluded from every analysis.

**What was wrong.** New papers in the v4 graphs were extracted by Llama-3.3 (loop.md 15.1). In most citer statements
Llama wrote the cited paper's title where the extraction prompt asks for the marker label (R1, R2, ...). The parser
then rejected 4,437 of 4,535 statements as malformed: 0.9 statements per new paper, against 37 for the cached Qwen
extractions. The graphs therefore had few citer statements for the 94 newly extracted papers.

**Fix.** `citegraph.marker_label` maps a copied marker text back to its label (unit-tested). The 91 affected
statement files were re-extracted, then the graphs, runs and judgments were rebuilt in `../citegraph/`. Seeds and
expansions are the same, copied from this attempt, so retrieval is unchanged.

The selection files (`cases/`) are not committed here; they are identical to `../citegraph/cases/`.
