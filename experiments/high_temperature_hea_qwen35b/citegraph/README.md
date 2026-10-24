# Experiment 17: citation-graph evidence variants

> **Caveat (added 2026-10-23, experiment 19).** The benchmark queries used here leak the held-out answer: 8% of the answer's words appear in broad queries, 20% in problem_constrained and 47% in expert_context, and per-unit overlap correlates 0.77–0.86 with judge scores. Paired comparisons between methods on the same query remain fair. Absolute scores, differences between query levels and conclusions about query inferability or evidence use are confounded. See [query_leakage/README.md](../query_leakage/README.md).


Run 2026-10-23. Code: [citegraph.py](../../../citegraph.py), tests: [test_citegraph.py](../../../test_citegraph.py),
runner: [run_citegraph.sh](../../../run_citegraph.sh). Failure analysis (experiment 18): [failure/README.md](./failure/README.md).

**Question.** If evidence comes from a per-query citation graph instead of the fixed 50-paper corpus, does the
hypothesis improve? The graph combines best-cited relevant papers, their most co-cited references, and what citing
papers say about each work. And how should the graph be used?

## Design (the user's choices)

For each held-out case, the cutoff t is the case's publication date and the query q is its problem_constrained
query. One graph is built per case and shared by all three query levels.

1. **Search phrases.** Qwen turns q into three 2–6 word phrases. It sees only the query, never the target.
2. **Seeds S0 (N = 10).**
   - Europe PMC search per phrase: open access, full text, first published before t. The phrase words are
     ORed in the abstract, and the search is anchored to the HEA domain (high/medium entropy, multi-principal,
     complex concentrated); 100 hits per phrase.
   - The pool is re-ranked by BM25 of title + abstract against q and the phrases. The 40 most relevant are kept.
   - Those 40 are ordered by citations received before the cutoff year (OpenAlex `cited_by_count` minus
     `counts_by_year` for years ≥ t).
   - The first 10 with parseable JATS are kept. Reviews are allowed.
3. **Expansion S1 (k = 3 per seed, backward only).**
   - Candidates are each seed's references that resolve to OpenAlex, were published before t, are not the target
     or its family, and have title relevance ≥ 0.4.
   - Ranked by co-citation count among seeds, then relevance to q, then pre-cutoff citations.
   - References without Europe PMC open full text are skipped in favour of the next one.
4. **Parsing.**
   - JATS body text, citing sentences with their preceding sentence, and numeric citation ranges expanded.
   - References are resolved to OpenAlex works by DOI or PMID, or by title match against the citer's OpenAlex
     `referenced_works`.
5. **Extraction (local Qwen).**
   - A paper card (experiment-14 rubric, quote-verified) for every full-text paper.
   - For every citing sentence with at most 4 references (at most 60 per paper), one statement per cited work:
     relation (finding, method, supports, contradicts, extends, compares, background), the attributed claim,
     cited system, applied-to system and numbers.
   - Background mentions are dropped, as are statements whose content words are under 50% present in the sentence.
6. **Graph.**
   - Nodes = S0 ∪ S1 ∪ all their pre-cutoff references.
   - A node holds its own card (full-text papers only) and every statement made about it by any full-text paper
     in the graph. If paper A cites C, A's statement is attached to node C.
   - Edges are citations. Each node's date is the latest of its own date and its citers' dates, which are all
     before t.

## Variants (all five run, as requested)

| Variant | What the model sees |
|---|---|
| graph_selection | Cards of the graph's full-text papers; the graph only chooses the papers (control) |
| graph_profiles | Node profiles: own card (when present) + up to 8 citer statements, contradictions first |
| graph_profiles_systemmatch | Profiles with the experiment-16 system-match appraisal before the hypothesis |
| corroboration_weighted | Profiles ranked by relevance × (1 + log(1 + independent citers)), with a corroboration line (supporting, contradicting, extending counts) |
| graph_tool_agent | Tools search_nodes, read_node, who_cites, references, path, submit_hypothesis; 12-call budget; a node can be cited only after it is read |

**Shared settings.**

- Generator: Qwen3.5-35B-A3B Q4_K_M, temperature 0.2, thinking off. Two samples per unit, 12 cases × 3 levels.
- Evidence: 16,000-character budget, at most 24 records, 3,200 characters per record.
- Judges: GPT-5.6 (primary) and DeepSeek-V4-Pro (cross-family). Target-free audit by GPT-5.6.
- Baselines (unchanged runs from experiments 14 and 16): closed_book, text_chunks, card, card_systemmatch.
- Primary comparison: each variant against text_chunks, with Holm correction over 5. Units are the mean of the
  two samples, with a paper-clustered bootstrap and sign test.

## Graph that was built

- 264 unique full-text papers (seeds and expansion over 12 cases). Of the 120 seeds, 9% are reviews; median
  pre-cutoff citations 7.5 (range 0–622).
- Expansion reached 8–25 papers per case (target 30). On average 526 eligible references, 42 with open full text;
  221 were skipped because they had no full text.
- 14,907 references: resolved by DOI 72.8%, by title 19.6%, by PMID 0.1%; unresolved 7.6%.
- 7,793 citing sentences were used (903 wider than 4 references were skipped). 12,533 statements were proposed and
  9,899 kept; 2,549 were background and 85 were ungrounded or malformed.
- Per case, on average: 1,298 nodes, 30 full-text nodes, 1,621 edges, 673 nodes with statements, 1,096
  statements, 71 nodes with ≥ 2 independent citers, 11 contradicting statements.

## Results (reconstruction score 0–4, mean of units)

| Arm | Runs (failed) | GPT-5.6 | DeepSeek | Non-broad | Broad | Mechanism | Evidence validity | Specificity | Papers in context |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| closed_book | 72 (2) | **1.65** | **2.20** | **2.06** | 0.77 | 1.59 | 1.14 | 0.47 | 0 |
| card_systemmatch | 72 | 1.62 | 2.02 | 2.02 | **0.81** | **1.64** | 1.25 | 0.74 | 5.7 |
| text_chunks | 72 | 1.56 | 2.00 | 2.00 | 0.67 | 1.53 | 1.10 | 0.60 | 11.2 |
| graph_selection | 72 | 1.52 | 1.91 | 1.97 | 0.63 | 1.47 | 1.04 | 0.66 | 5.1 |
| graph_profiles | 72 | 1.52 | 1.97 | 1.95 | 0.68 | 1.47 | 1.06 | 0.63 | 13.6 |
| card | 72 | 1.52 | 1.98 | 1.92 | 0.74 | 1.50 | 0.86 | 0.63 | 5.7 |
| graph_tool_agent | 72 | 1.52 | 1.98 | 1.92 | 0.72 | 1.63 | 0.88 | 0.76 | 6.1 |
| graph_profiles_systemmatch | 72 (1) | 1.49 | 2.06 | 1.91 | 0.67 | 1.55 | **1.28** | **0.81** | 13.5 |
| corroboration_weighted | 72 | 1.49 | 1.97 | 1.93 | 0.59 | 1.43 | 0.85 | 0.59 | 9.0 |

**Paired against text_chunks** (difference, 95% CI, Holm p):

| Variant | GPT-5.6 | DeepSeek |
|---|---|---|
| graph_selection | −0.03 [−0.13, 0.06], 1 | −0.09 [−0.17, 0.00], 0.73 |
| graph_profiles | −0.03 [−0.12, 0.05], 1 | −0.03 [−0.19, 0.11], 1 |
| graph_profiles_systemmatch | −0.06 [−0.17, 0.03], 1 | +0.06 [−0.13, 0.23], 1 |
| corroboration_weighted | −0.07 [−0.17, 0.03], 1 | −0.03 [−0.14, 0.08], 1 |
| graph_tool_agent | −0.04 [−0.18, 0.12], 1 | −0.02 [−0.19, 0.17], 1 |

**Other comparisons.**

- profiles − selection: 0.00 (GPT-5.6), +0.06 (DeepSeek). Adding citer statements to the same graph is neutral.
- profiles_systemmatch − profiles: −0.03 and +0.09.
- corroboration − profiles: −0.04 and 0.00.
- tool_agent − profiles: 0.00 and +0.01.
- Against closed_book every variant is lower on both judges. The intervals exclude zero for graph_selection
  (both judges), corroboration_weighted (both) and graph_tool_agent (DeepSeek).
- Best arm per unit, counting ties: card_systemmatch 12, closed_book 7, text_chunks 7, graph_tool_agent 7,
  graph_profiles 6, card 5, graph_profiles_systemmatch 4, corroboration_weighted 4, graph_selection 3.

**Tool agent.** Every run used the full 12-call budget: 52% read_node, 35% search_nodes, 5% who_cites, under 1%
references, path never. It read 6.1 distinct nodes on average, and 6 submissions were rejected for citing unread
nodes.

## Which variant is best

None of the graph variants beats the corpus baselines, and none is clearly best among themselves.

- Every primary comparison has Holm p = 1 except graph_selection on DeepSeek (Holm p 0.73). The five variants are
  within 0.04 of each other on GPT-5.6.
- **graph_profiles_systemmatch** is the best graph variant on DeepSeek (2.06, higher than every evidence
  baseline) and on evidence validity and specificity. It is the lowest on GPT-5.6 problem_constrained queries.
- **graph_tool_agent** wins the most units among graph variants and has the best mechanism score. It also has
  the widest intervals.
- **corroboration_weighted** is the worst: it pushes relevant nodes out in favour of heavily cited general ones
  (experiment 18).

If one graph variant is kept, it should be graph_profiles_systemmatch: it matches card_systemmatch on DeepSeek,
and its failures have identifiable fixes. But it is not better than card_systemmatch, which needs no graph. Why
the graph does not help is analysed in [failure/README.md](./failure/README.md).

## Integrity

- 360 of 360 runs written, 359 ok. Each ok run was judged by GPT-5.6 and DeepSeek and audited.
- PMC11775865 broad graph_profiles_systemmatch sample 1 hit the 7,000-token output cap on both its first attempt
  and its single retry, so it is recorded as failed. Two other system-match runs failed first and succeeded on
  retry; the first attempts are kept in `failed_attempts/`.
- Zero temporal violations, test-paper leaks, family leaks, target DOI or near-duplicate-title leaks, and invalid
  citations.
- Each graph node record is dated by its latest citer, so the temporal audit also covers citer statements.
- One generator identity throughout.
- `paper.xml` and `parsed.json` are not committed; they are re-downloaded from Europe PMC and parsed
  deterministically.

## Files

- `cases/<case>/`: `keywords.json`, `seed_candidates.json`, `seeds.json`, `expansion.json`, `graph.json`.
- `papers/<pmcid>/`: `card.json` and `contexts.json` (citer statements with the source sentence).
- `runs/`, `judgments/{gpt56,deepseek}/`, `audit/`, `failed_attempts/`.
- `results/analysis.json`, `results/tables.md`.

## Limits

- Twelve papers. Every interval is wide, and no comparison survives correction.
- Only open-access Europe PMC full text can be expanded. Highly cited paywalled classics enter only as
  reference-only nodes, described by what citers say about them.
- Seed relevance is lexical (BM25 + domain anchor). For some cases the seed set drifts to adjacent HEA topics
  (for example functional or catalytic HEAs).
- Citation counts come from OpenAlex now, minus later years. Counts from the cutoff year onward are removed, so
  citations in the months before a mid-year cutoff are also removed.
