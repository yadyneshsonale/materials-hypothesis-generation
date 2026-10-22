# Citation-graph paper selection

**Script:** [citation_graph.py](../../../citation_graph.py). **Outputs:** `summary.json`, `rows.json`, `selections.json` in this folder.
**Run date:** 2026-10-22 (OpenAlex and Europe PMC queries made that day; the counts will change over time).

## Question

Can a paper's citation graph and citation counts improve how papers are selected for the HEA
hypothesis corpus? The current 50-paper corpus was selected by a single signal: the Europe PMC
citation count at screening time (`citation_count` in `data/corpus/manifest.json`).

## Method

1. **Metadata.** OpenAlex works for the 50 corpus DOIs: citation count, publication year, and
   reference list. All 50 were found.
2. **In-corpus graph.** A directed edge A → B means corpus paper A cites corpus paper B, using
   OpenAlex reference lists. PageRank is computed by power iteration (100 iterations, damping 0.85;
   no scipy dependency).
3. **Candidate expansion.** The top 10 corpus papers by PageRank are seeds. For each seed, the
   script fetches up to 60 open-access journal articles from 2015 onward that cite it and match
   "high entropy alloy" in OpenAlex search. A candidate must have an alloy-related title
   (`alloy`, `superalloy`, `refractory`, `solid solution`, or `eutectic`), must mention a
   high-entropy term, and must not match catalysis, electro-, battery, ceramic, oxide, nitride,
   carbide, or magnetism terms, or a review-type title or type. 224 candidates remained.
4. **Full-text check.** The corpus uses PMC JATS XML. Each DOI is looked up in Europe PMC, and a
   candidate counts only if it has a PMC ID. OpenAlex does not give this reliably (its `ids` field
   had no `pmcid` for corpus papers that do have PMC records), so Europe PMC is the source. 37
   candidates pass.
5. **Scores.** Each paper is scored three ways, with z-scores taken over the pool:
   - `citation_only`: log(1 + citations per year of age), from OpenAlex.
   - `graph`: bibliographic coupling (share of a paper's references that are also references of
     the corpus) plus the number of corpus papers it directly cites.
   - `combined`: the mean of the three z-scores (citation impact, coupling, direct citations).
6. **Comparison.** For each score, the top 50 of the 87-paper pool (50 corpus + 37 PMC candidates)
   is compared with the current corpus.

## Results

| Measure | Value |
|---|---:|
| Corpus papers found in OpenAlex | 50 / 50 |
| Corpus papers with PMC full text (Europe PMC check) | 50 / 50 |
| Directed links within the corpus | 21 |
| Corpus papers with at least one link inside the corpus | 26 / 50 |
| Candidates after topic and review filters | 224 |
| Candidates with PMC full text | 37 |

Top-50 selections from the 87-paper pool:

| Score | Kept from current corpus | New papers | Share with high-temperature term in title |
|---|---:|---:|---:|
| current corpus (Europe PMC citations) | 50 | 0 | 30/50 (60%) |
| `graph` | 42 | 8 | 27/50 (54%) |
| `combined` | 32 | 18 | 24/50 (48%) |
| `citation_only` (OpenAlex citations) | 24 | 26 | 20/50 (40%) |

The high-temperature share is a crude title keyword check (`high temperature`, `elevated
temperature`, `oxidation`, `creep`, `refractory`, `thermal`, `heat`, `hot`, `fatigue`, `annealing`,
`aging`, `tensile`). It is included as a relevance signal, not a relevance judgment.

## Interpretation

- **Citation counts alone drift away from the topic.** Ranking by citations brings in highly cited
  but off-target papers, such as nuclear, ultralow-temperature, and electrochemical work. Its
  high-temperature share is the lowest of the four.
- **Graph coupling keeps the selection close to the current corpus.** It recovers 42 of the 50
  current papers and keeps the highest topic share after the current corpus. Its weakness is that
  it reinforces what is already selected, so it may miss new subfields.
- **Recommended next step:** use a combined rule with a high-temperature term requirement (title or
  abstract) as a hard filter, then rank by coupling and citations per year. The rule is not yet
  evaluated against held-out hypothesis quality, so it should not replace the current corpus until
  it has been tested.

## Caveats

- The current corpus was selected on Europe PMC counts, and the candidates are scored on OpenAlex
  counts. The two sources differ, so "kept from current corpus" is not a neutral test of
  agreement.
- Reference lists in OpenAlex are incomplete for some papers, which lowers coupling scores for
  them.
- The candidate pool is limited to papers that cite the top 10 seeds and match a title term. A
  paper that no seed cites cannot be reached by this method.
- No evaluation of selection quality against hypothesis performance was run. This analysis only
  compares selection rules and their topic fit.
