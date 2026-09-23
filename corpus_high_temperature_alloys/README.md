# High-temperature alloy primary-research corpus

This corpus contains ten citation-ranked, open-access primary studies on high-temperature alloys. Citation counts came from Europe PMC on 2026-09-23. Every selected record exposes JATS full-text XML and is indexed as `research-article`.

## Screening

Selection required all of the following:

- direct relevance to high-temperature, refractory, or superalloy behavior;
- open-access full-text JATS XML in Europe PMC;
- a primary-research publication type;
- methods/results-style sections and original experimental or computational work;
- no review, survey, perspective, roadmap, or bibliometric framing.

Publication type alone was not treated as sufficient. Four research-article-indexed papers (`PMC5978221`, `PMC5793567`, `PMC5872974`, and `PMC5951476`) were excluded because full-text inspection showed literature-data synthesis or reanalysis rather than new primary experiments or simulations.

The ranked selection and provenance are in `manifest.json`. Citation counts are source- and date-dependent, so this is a reproducible Europe PMC ranking rather than a claim about all scholarly indexes.

## Contents

- `xml/`: downloaded Europe PMC JATS source.
- `text/`: structure-preserving extraction text with normalized numeric citations.
- `agent_claims/`: compact claims selected by Copilot subagents or the main agent.
- `outputs/`: validated 11-role `PaperRecord` outputs.
- `evidence_graph/`: deterministic typed entities and relations.
- `source_context/`: passages, references, citation mentions, tables, and claim anchors.
- `metadata.json`: title, DOI, and license mapping for downstream tools.

The extraction assembler rejects any evidence span that is not a verbatim substring of the converted source and computes `chunks_processed` with the repository chunker.

## Licenses

Nine papers are distributed under CC BY. `PMC11206460` is CC BY-NC. Per-paper license and source URL are retained in `manifest.json` and `metadata.json`; reuse must follow those terms.

## Reproduce

```bash
python import_jats_corpus.py --corpus-dir corpus_high_temperature_alloys \
  PMC11206460 PMC10154406 PMC5995863 PMC5627260 PMC7532182 \
  PMC6427779 PMC5458593 PMC10213035 PMC5978046 PMC6265909

python assemble_agent_extraction.py \
  --text-dir corpus_high_temperature_alloys/text \
  --claims-dir corpus_high_temperature_alloys/agent_claims \
  --out-dir corpus_high_temperature_alloys/outputs

python build_evidence_graph.py \
  --outputs-dir corpus_high_temperature_alloys/outputs \
  --graph-dir corpus_high_temperature_alloys/evidence_graph \
  --source-dir corpus_high_temperature_alloys/text \
  --metadata corpus_high_temperature_alloys/metadata.json \
  --normalizer deterministic

python source_context.py \
  --source-dir corpus_high_temperature_alloys/text \
  --outputs-dir corpus_high_temperature_alloys/outputs \
  --context-dir corpus_high_temperature_alloys/source_context \
  --metadata corpus_high_temperature_alloys/metadata.json
```
