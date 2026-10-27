# Web-search corpora (experiment 36)

**Plan.** [loop.md](../../../loop.md) sections 17.1 (pre-registration) and 17.2 (amendment: Crossref replaces
OpenAlex).
**Code.** [websearch.py](../../../websearch.py), tested in [test_websearch.py](../../../test_websearch.py).

For every held-out paper and question, a web search of the literature builds the paper's evidence corpus. Nothing
published on or after the paper's date can enter it, and the paper itself, its versions and the other held-out
papers can never enter it.

## How a corpus is built

1. **Search phrases.** Llama-3.3-70B (knowledge cutoff 2023-12, before every held-out paper) writes three search
   phrases from the question alone, with the prompt of experiment 17.
2. **Web search.** Each phrase becomes one Europe PMC query: any of the phrase's words in the abstract, within the
   high-entropy-alloy domain, open access with full text, not a preprint, first published before the paper's date.
   Every hit is fetched (up to 2,000 per phrase), so the engine's own ordering does not decide what is seen.
3. **Strict filter** (code, before any model sees a paper). A paper is kept only if:
   - **(a)** every date is before the paper's date: Europe PMC's first and electronic publication dates and
     Crossref's publication date. A partial date counts as the end of its month or year. A paper without a Crossref
     date is not kept.
   - **(b)** it is not the paper itself or a version of it: same DOI or PMCID, title Jaccard ≥ 0.8, or ≥ 0.5 with the
     same first author;
   - **(c)** it is none of the 45 held-out papers;
   - **(d)** it is not a preprint, review, editorial, erratum, correction, retraction, comment or data paper (types from
     Europe PMC and Crossref; titles announcing a review also count);
   - **(e)** it does not cite the paper (DOI, title or raw citation string in its JATS reference list);
   - **(f)** it contains fewer than 5% of the paper's 12-word passages (non-introduction text);
   - **(g)** its XML has at least 3,000 characters of text.
4. **Ranking.** BM25 on title (counted twice) and abstract against the question and the phrases. Citation counts and
   other present-day signals are never used.
5. **Seeds.** The first 50 papers that pass every filter.
6. **Citation-graph expansion.** References (by DOI, from the seeds' JATS reference lists) cited by at least two
   seeds, passing the same filters, ranked by co-citation then title relevance; up to 50 with open-access XML.

## Corpus statistics ([stats.json](./stats.json), [gate.json](./gate.json))

| | |
|---|---|
| Corpora | 159: 135 for the harness's v3.1 questions (45 papers × 3 levels), 24 for the suite's differently worded v3 questions |
| Unique papers | 1,315 (1,198 ever a seed, 324 ever an expansion paper) |
| Per corpus | seeds: median 50 (min 25); expansion: median 16 (5–35); search hits: median 625 (30–1,301) |
| Newest evidence | median 15 days before the paper's date (minimum 1 day) |
| Gate | 10,556 corpus-paper entries re-checked, 10,249 also against cached OpenAlex dates: no violation |
| Version check (web_analysis.py W5) | largest share of a held-out paper's 12-word passages in any corpus paper: 1.5% (median 0; 2 entries ≥ 1%) |

**Removed by the filters** (counts summed over all corpora; one paper can be counted in several corpora):

| Reason | Count |
|---|---:|
| Excluded type (reviews and other non-research types, from Europe PMC types) | 9,429 |
| Another held-out paper | 2,017 |
| Crossref date on or after the cutoff | 581 |
| Review announced in the title | 171 |
| Cites the case paper | 33 |
| No Crossref date | 23 |
| Europe PMC electronic date on or after the cutoff | 9 |
| A version of the case paper (title rule) | 6 |
| Expansion candidates without open-access XML | 19,144 |

## Evidence records

- **Passages** (`text_chunks` pool): section-aligned, at most 1,600 characters, verbatim from the XML. The abstract
  and body are used; references, tables, figures and back matter (acknowledgements, funding, data availability,
  author contributions, conflicts of interest) are not.
- **Cards** (`card` pool): title, abstract and conclusions, verbatim, at most 3,200 characters. No LLM extraction is
  used on the web corpus.
- Every record carries the paper's DOI, title and all its dates. Its `publication_date` is the latest of them, so the
  standard temporal audit checks the strictest date.

## The live search tool for agents

`WebTools` gives an agent `web_search(query)`, `read_paper(paper_id, page)` and `references(paper_id)`.

- **Same filters.** Every result passes the same filters as the corpora. Results are parsed before they are shown,
  so rules (e)–(g) also cover titles and snippets.
- **Plain keywords only.** Field syntax, ranges and boolean operators are removed, so an agent cannot widen the date
  filter.
- **Reading limits.** Only papers a tool returned can be read, up to 6 pages of 2,400 characters each.
- **Logging.** Every call is logged with the IDs and dates of what it returned.

## Files

| Path | Content |
|---|---|
| `heldout.json` | The 45 held-out papers: PMCID, DOIs, title, first author, date |
| `corpora/<paper>/<level>.json` | One corpus per paper and v3.1 question (harness): phrases, searches, hit counts, filter-reason counts, every seed and expansion paper with IDs, dates, role and rank |
| `corpora/<paper>/<level>.q<hash>.json` | Corpora of the suite's v3 questions where they are worded differently from v3.1 |
| `corpora/<paper>/<level>*.phrases.json` | The search phrases and their writer |
| `gate.json` | The pre-run gate: every corpus paper re-checked against every rule (and against cached OpenAlex dates) |
| `stats.json` | Corpus statistics |
| `superseded_openalex/` | The 89 corpora built with OpenAlex dates before OpenAlex ran out of budget (not used) |

The caches (`search/`, `records/`, `papers/`, `crossref_by_doi.json`, `openalex_by_doi.json`) can be rebuilt from the
APIs and are not committed. Raw XML is cached in `../citegraph/papers/`.
