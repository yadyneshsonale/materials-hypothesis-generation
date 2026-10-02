# High-temperature high-entropy alloy primary-research corpus

This corpus contains the 50 most-cited eligible open-access primary studies returned by a
reproducible Europe PMC search for high-temperature high-entropy alloys. Citation counts and
availability were checked on 2026-10-02.

## Selection

Candidates were ranked by Europe PMC `citedByCount` using:

```text
TITLE_ABS:("high entropy alloy" OR "high-entropy alloy") AND
TITLE_ABS:("high temperature" OR "high-temperature" OR "elevated temperature" OR
refractory OR creep OR oxidation OR "thermal stability" OR "hot corrosion" OR
"temperature-dependent" OR superalloy OR "extreme temperature" OR "phase stability") AND
OPEN_ACCESS:Y AND HAS_FT:Y sort_cited:y
```

Starting from the most-cited result, a paper was retained only if it:

- directly studies elevated-temperature, refractory/extreme-environment, creep, oxidation,
  hot-corrosion, melting, thermal/phase-stability, or temperature-dependent behavior of a
  high-entropy alloy;
- is indexed as a research article and contains methods/results-style sections;
- is not a review, correction, supporting-data record, or retracted article;
- has open-access JATS full-text XML available from Europe PMC; and
- appears in a peer-reviewed journal indexed by Europe PMC/NLM.

The process stopped when 50 papers passed all criteria. `screening_audit.json` records every
higher-ranked result that was excluded and its reason. Citation counts are source- and
date-dependent, so this is a reproducible Europe PMC ranking rather than a claim across every
scholarly index. Europe PMC did not return an eligible conference paper with comparable
full-text JATS XML availability before the selection cutoff.

## Contents

- `text/`: structure-preserving text generated from the JATS files for this repository's
  extraction pipeline.
- `manifest.json`: rank, citation count, DOI, venue, license, source URL, and screening evidence.
- `metadata.json`: compact title, DOI, license, venue, and publication-year lookup.
- `screening_audit.json`: query, selection rules, cutoff, and higher-ranked exclusions.

The canonical XML for each paper is stored with its paper-specific outputs under
`../../outputs/papers/<PMCID>/input/article.xml`. The adjacent PDF is for visual inspection only
and is not used by the pipeline.

Licenses vary by article and are retained in `manifest.json` and `metadata.json`. Reuse must
follow each article's license.
