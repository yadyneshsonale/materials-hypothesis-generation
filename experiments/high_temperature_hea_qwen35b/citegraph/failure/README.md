# Experiment 18: failure analysis of the citation-graph variants

> **Caveat (added 2026-10-23, experiment 19).** The benchmark queries used here leak the held-out answer: 8% of the answer's words appear in broad queries, 20% in problem_constrained and 47% in expert_context, and per-unit overlap correlates 0.77–0.86 with judge scores. Paired comparisons between methods on the same query remain fair. Absolute scores, differences between query levels and conclusions about query inferability or evidence use are confounded. See [query_leakage/README.md](../../query_leakage/README.md). All evaluations were rerun on leak-free queries with a pre-cutoff generator: scores fell from about 1.5 to about 0.5 and the level gradient disappeared. See [rerun_v3/README.md](../../rerun_v3/README.md).


Run 2026-10-23. Code: [failure_citegraph.py](../../../../failure_citegraph.py). Tables: `tables.md`,
`analysis.json`. It follows the pipeline in order: graph, extracted statements, what the graph contains, what
reached the model, and how it reasoned.

**Checks run.**

- 90 citer statements, 15 per relation (stratified), checked by GPT-5.6 against their source sentences.
- Evidence ceiling: the top 20 records by target text, rated by GPT-5.6. Same procedure as experiment 14, run on
  graph profiles and on the graph-selected papers' cards.
- Error coding of the fatal errors in 408 runs (same coder as experiment 15). The experiment-15 codes are
  reused for the baselines.
- Target-free audit of the mechanism source.
- Tool traces.

## 1. Statements are mostly faithful; "method" and "compares" are not

| Relation | n | Claim supported | Distorted | Unsupported | Relation correct | System supported (when stated) |
|---|---:|---:|---:|---:|---:|---:|
| supports | 15 | 1.00 | 0 | 0 | 1.00 | 0.77 |
| contradicts | 15 | 0.80 | 0.07 | 0.13 | 0.80 | 0.92 |
| extends | 15 | 0.80 | 0.13 | 0.07 | 1.00 | 1.00 |
| finding | 15 | 0.67 | 0.20 | 0.13 | 0.80 | 0.69 |
| compares | 15 | 0.60 | 0.27 | 0.13 | 1.00 | 0.40 |
| method | 15 | 0.47 | 0.13 | 0.40 | 0.80 | 0.13 |
| all | 90 | 0.72 | 0.13 | 0.14 | 0.90 | 0.68 |

The errors follow a pattern:

- *Method* statements often restate the cited title instead of what the sentence says ("calculations used VASP"
  became "developed ab initio molecular dynamics").
- *Compares* statements attribute the citing paper's own comparison to the cited work.
- The cited *system* is often filled from the cited title or from the citing paper, not from the sentence.
- Some "contradicts" labels are really supports. Contradicting statements are rare anyway (11 per graph), so
  that signal is both small and noisy.

The word-overlap grounding filter removed only 34 statements. It cannot catch a correct claim attributed to the
wrong work.

## 2. The graph does not contain more anticipating evidence than the 50-paper corpus

| Pool | Reconstructibility (0–2) | Cases at 2 | Supportive records in top 20 | Strongly supportive | Supportive that are reference-only nodes |
|---|---:|---:|---:|---:|---:|
| Graph profiles | 1.25 | 3 | 15.3 | 2.0 | 52% |
| Graph-selected cards | 1.33 | 4 | 14.8 | 2.2 | 0% |
| Corpus raw text (exp 14) | 1.25 | 3 | 14.1 | 2.0 | — |
| Corpus cards (exp 14) | 1.42 | 5 | 14.3 | 1.8 | — |

- Per case, the graph is better than the corpus in 2 cases (PMC11355469; PMC11775865 for selection) and worse in
  3 (PMC10759803, PMC11087546, PMC12941549).
- About half of the supportive profiles are reference-only nodes, so citer statements do add evidence that
  full-text cards alone would miss. But the total amount of strongly anticipating evidence (2 records per case)
  does not change.
- The limiting factor is the same as in experiment 15: what came before the target paper anticipates it only
  partly. Building a broader, better-cited neighbourhood does not add the missing ideas.
- PMC12941549 (only 8 expansion papers, the thinnest graph) shows that a relevance-thin graph is worse than
  the curated corpus.

## 3. What reaches the model: more papers, less relevant support per citation

| Arm | Failure rate | Supportive records in context | Share of citations that are supportive | Citations to reference-only nodes |
|---|---:|---:|---:|---:|
| text_chunks | 0.36 | 4.0 | 0.55 | — |
| card | 0.39 | 3.7 | 0.81 | — |
| card_systemmatch | 0.31 | 3.7 | 0.85 | — |
| graph_selection | 0.36 | 3.9 | 0.85 | 0 |
| graph_profiles | 0.38 | 3.8 | 0.46 | 0.57 |
| graph_profiles_systemmatch | 0.39 | 3.9 | 0.46 | 0.57 |
| corroboration_weighted | 0.36 | **1.3** | 0.22 | 0.90 |
| graph_tool_agent | 0.40 | 1.6 | 0.32 | 0.53 |

- **Profiles dilute the context.** They spread the same budget over 13.6 papers instead of 5. More than half of
  what the model cites is a reference-only node, described by 1–8 one-sentence citer statements without system
  details.
- Runs citing such nodes score no higher than runs citing only full-text cards (1.52 against 1.54 for profiles).
  For profiles + system-match the gap reverses: 1.43 against 2.13 (8 runs).
- **Corroboration ranking removes relevant evidence.** Multiplying relevance by the number of citers promotes
  heavily cited general works (classic HEA papers, generic methods). Supportive records in context fall from 3.8
  to 1.3, and the share of failures with an evidence_unsupported error rises to 96%.
- Citation count measures how central a work is to the field, not how relevant it is to the query.
- **The tool agent reads too little and never navigates.**
  - It exhausts the 12-call budget in every run, mostly on search and read. It reads 7 nodes on average, so it
    sees fewer supportive records (1.6) than one-shot packing (3.8).
  - It used who_cites, references or path in only 20 of 72 runs, scoring 1.53 with navigation and 1.52 without.
    Path was never called.
  - The number of nodes read is unrelated to the score (Spearman −0.04).
  - The 4 runs that cited nothing scored 0.69.

## 4. Reasoning: the same failures as before

Share of failing runs with each error:

| Arm | Failures | Wrong intervention | Wrong mechanism | Wrong conditions | Wrong baseline | Evidence unsupported | Physical error |
|---|---:|---:|---:|---:|---:|---:|---:|
| closed_book | 23 | 0.74 | 0.70 | 0.48 | 0.26 | 0.65 | 0.13 |
| text_chunks | 26 | 0.77 | 0.69 | 0.54 | 0.27 | 0.81 | 0.12 |
| card_systemmatch | 22 | 0.64 | 0.73 | 0.50 | 0.32 | 0.73 | 0.14 |
| graph_selection | 26 | 0.62 | 0.65 | 0.62 | 0.38 | 0.96 | 0.19 |
| graph_profiles | 27 | 0.52 | 0.67 | 0.59 | 0.41 | 0.70 | 0.19 |
| graph_profiles_systemmatch | 28 | 0.64 | **0.82** | 0.61 | 0.39 | 0.61 | **0.29** |
| corroboration_weighted | 26 | 0.73 | 0.81 | 0.46 | **0.46** | **0.96** | 0.19 |
| graph_tool_agent | 29 | 0.55 | 0.66 | 0.48 | 0.31 | 0.83 | 0.17 |

- **Wrong baseline and wrong conditions rise in every graph arm** (baseline 0.31–0.46 against 0.26–0.32;
  conditions up to 0.62). The graph brings in papers on other alloy classes and test regimes, and the model takes
  their starting materials and temperatures.
- **System-match on profiles appraises statements, not systems.** A citer statement rarely states the cited
  system (system supported for only 68% even when stated), so the appraisal has little to go on. Mechanism errors
  in failures rise to 82%, and physical errors to 29%. Long appraisals of 11+ records also caused the one
  truncation failure.
- **Mechanism source** (target-free audit):
  - Own reasoning is the strongest source in every profile arm: 1.84 for graph_profiles, 1.84 for profiles +
    system-match and 1.80 for corroboration.
  - Same-system evidence is rare (0–7%) and scores low (0.25–0.75).
  - The graph almost never provides a same-system mechanism.
- **Broad queries still fail** in all arms (graph arms 0.59–0.72 at the broad level).

## 5. Conclusions

Why the graph variants do not beat the baselines, in order of impact:

1. **The ceiling does not rise** (section 2). Graph and corpus anticipate the target equally (1.25–1.42 of 2). The
   bottleneck is what earlier literature contains about these specific results, not which papers are chosen.
2. **Citation-based ranking is not query relevance** (sections 3 and 4). Seed citation counts and corroboration
   reward centrality. That brings general and cross-system papers into the context, which raises
   wrong-baseline, wrong-conditions and wrong-mechanism errors.
3. **Reference-only nodes are thin** (sections 1 and 3). One-sentence citer statements, 28% unfaithful (method 53%),
   with a missing or unreliable system field, give the model claims without the scope it needs to judge transfer.
4. **The agent does not use the graph structure** (section 3). With 12 calls it searches and reads like a flat
   retriever. The citation edges are almost unused, and it sees less evidence than one-shot packing.

**Best variant and why.** graph_profiles_systemmatch is the most promising graph variant. It has the highest
DeepSeek score of any evidence arm (2.06), the highest evidence validity and specificity, and it is the only one
whose losses come from fixable causes: missing system fields and long appraisals. graph_profiles and
graph_selection are equal to the corpus card baseline. corroboration_weighted should be dropped.

**Fixes if the graph is pursued.**

- Rank by query relevance first. Use citations only as a tie-breaker.
- Drop or down-weight reference-only nodes unless they have at least 2 independent citers with consistent
  statements and an explicit system.
- Extract the cited system from the reference list entry and title, not the sentence. Drop method and compares
  statements.
- Give the agent a graph-first protocol (read seed, then who_cites / references on the best node) and a larger
  read budget, or precompute 2-hop neighbourhoods.
- The largest gain still lies outside the evidence: broad-query repair and a better candidate selector
  (experiment 16 oracle 1.93).
