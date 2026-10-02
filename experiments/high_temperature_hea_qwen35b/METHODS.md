# Methods

## 1. Corpus construction

Europe PMC was searched for open-access, full-text work combining high-entropy alloys with
high-temperature, elevated-temperature, refractory, creep, oxidation, thermal-stability,
hot-corrosion, melting, or phase-stability concepts. Results were ranked by the Europe PMC
`citedByCount` value available on 2026-10-02.

A record was retained only when it:

1. directly studied temperature-dependent or extreme-environment behavior of an HEA;
2. was indexed as primary research and contained methods/results-style sections;
3. was not a review, correction, supporting-data record, or retracted article;
4. provided open-access JATS full-text XML; and
5. appeared in a peer-reviewed venue indexed by Europe PMC/NLM.

Screening stopped after 50 eligible papers. `data/corpus/screening_audit.json` records the search,
cutoff, and exclusion reason for every higher-ranked rejected result. The resulting rank is
reproducible within Europe PMC at the recorded date; it is not a claim of universal citation rank
across all scholarly databases.

## 2. Source preparation

The retained JATS XML files were parsed into structure-preserving plain text. Both representations
are retained:

- XML is the archival open-access source representation.
- Text is the model input and the source used for character-exact grounding validation.

Titles, DOI values, venues, years, citation counts, licenses, and source URLs are recorded in the
manifest. Article-level reuse remains subject to each recorded license.

## 3. Model and inference runtime

| Setting | Value |
| --- | --- |
| Backbone | Qwen3.5-35B-A3B |
| Quantization | GGUF Q4_K_M |
| Serving engine | llama.cpp |
| llama.cpp revision | `a8c9a4e7ccba890d6a2644a235492f836a7371c3` |
| GPUs | 4 x NVIDIA Tesla V100-DGXS, 32 GB each |
| CUDA runtime | CUDA 12 libraries, compute capability 7.0 build |
| Context per request slot | 32,768 tokens |
| Concurrent slots | 4 |
| Extraction workers | 4, then 1 for two timed-out papers |
| Thinking mode | disabled through `chat_template_kwargs.enable_thinking=false` |

CUDA 13 libraries could load the model but could not execute generation on Volta. The successful
llama.cpp build explicitly targeted architecture 70 and linked CUDA 12 `libcudart`, `libcublas`,
and `libcublasLt`.

## 4. Linked evidence representation

Each unit represents one material state and operating regime:

```text
material/composition + intervention or initial structure
  -> resulting structure/defect state
  -> mechanism
  -> measured or calculated property outcome
  + conditions + comparison + limitations + verbatim provenance
```

The model was instructed to:

- separate records when compositions, treatments, temperatures, environments, or loads differ;
- avoid transferring a mechanism or outcome between material systems;
- leave unstated fields empty rather than infer values;
- exclude results attributed only to cited papers or generic literature background;
- copy complete, contiguous evidence passages exactly; and
- avoid paraphrasing, ellipses, notation normalization, or joining separated source text.

The deterministic validator rejects units lacking a material, a linked intervention/structure and
mechanism/outcome, an allowed evidence type, confidence in `[0, 1]`, or source-exact evidence spans.
Empty nested structures and placeholder values such as `null`, `unknown`, and `not explicitly
stated` do not count as populated facets.

## 5. Pilot and extraction acceptance gate

Before the full run, six units were manually curated from three papers covering creep, in-situ
oxidation, and computational dislocation behavior. All six were checked for schema validity,
complete core facets, and exact grounding.

The automated one-paper benchmark was iterated to remove cited-background claims and reduce
non-verbatim spans. The accepted configuration produced nine valid units, three rejected
candidates, 100% grounding, and 66.7% complete core chains on the representative oxidation paper.

## 6. Full extraction procedure

Papers were processed concurrently, but each paper was written only after all its chunks completed.
The run was resumable and skipped existing output records. Forty-eight papers completed during the
four-worker run. `PMC5995863` and `PMC9026100` exceeded the per-request timeout under concurrent
load; both completed successfully during a serial resumable pass.

Outputs retain both:

- `evidence_units`: candidates accepted by deterministic validation; and
- `rejected_units`: rejected candidate payloads and explicit rejection reasons.

## 7. Evaluation metrics

`evaluate_materials_corpus.py` reloads every persisted unit against its complete source text and
reports:

- output completeness and missing/unexpected paper IDs;
- schema-valid and invalid unit counts;
- exact verbatim grounding rate;
- mean valid units per paper;
- evidence-type distribution;
- confidence mean;
- meaningful facet coverage, excluding empty/placeholder values; and
- complete core-chain rate, requiring material, intervention, structure, mechanism, outcome,
  conditions, comparison, and provenance.

The final results were 493 valid units, zero invalid persisted units, 125 rejected model
candidates, 100% exact grounding, and a 56.19% complete core-chain rate.

## 8. Adaptive hypothesis workflow

The adaptive agent used five deterministic tasks:

1. establish quantitative baselines and operating regimes;
2. identify intact causal chains;
3. identify actionable composition or processing interventions;
4. identify boundary and failure regimes; and
5. identify measurements that discriminate competing mechanisms.

Each task records its decision use and required facets. Retrieval was limited to two units per
paper and eight direct hits per task. Final synthesis prioritized task-cited evidence and was
bounded to at most 20 units to prevent context overflow. In this run, 15 unique units were
available after retrieval and all 15 were supplied to synthesis.

The workflow explicitly reported that the corpus did not contain a direct, quantitative study
combining oxidation resistance, creep strength, and phase stability above 1000 C. The generated
hypothesis therefore contains documented extrapolations and uncertainties rather than presenting
the evidence gap as resolved.

## 9. Limitations

- Europe PMC citation counts are database- and date-dependent.
- JATS availability biases the corpus toward venues deposited in PubMed Central.
- Model confidence is self-reported and is not calibrated probability.
- The 125 rejected candidates indicate that useful claims may remain unextracted when the model
  fails exact-span requirements.
- Only 56.19% of accepted units populate every core facet; missing comparisons and operating
  conditions are the largest gaps.
- The agent's final candidate combines evidence from different alloy systems and temperature
  regimes. These transfers are stated as proposed inferences and require experiments.
- The plausibility critic warned that Cr2O3 may not remain protective in a W-rich alloy above
  1000 C because volatile chromium oxides can form. The candidate must not be treated as a
  validated alloy prescription.
- No independent materials expert has yet scored the 493 extracted units or final candidate.

## 10. Eleven-role and decision-question extraction

The corpus was also processed with the original 11-role taxonomy: problem motivation, prior
approach, prior limitation, rejected alternative, inspiration source, causal claim,
mechanism/principle, hypothesis statement, evidence/result, constraint, and contradiction.

Role definitions were tightened to prevent common category errors. A hypothesis must predict
material behavior or an intervention-to-outcome relationship; method utility and study objectives
do not qualify. A contradiction must identify both the current result and the conflicting prior
claim or expectation. A rejected alternative requires an explicit decision not to use an option
and a reason. An inspiration source requires a borrowed method, analogy, or prior finding that
shaped the approach.

After section-level extraction, all roles were reconciled in one paper-level call. Claims from
different material systems or operating regimes were prohibited from merging. Exact source
grounding was validated both before and after reconciliation.

The same paper-level stage generated zero to five decision questions. A decision question was
defined as a specific, answerable, falsifiable information need that changes a material-design,
mechanism, boundary, or experiment decision. Accepted questions had to:

- ask one primary uncertainty in at most 50 words;
- use one of five types: baseline, causal, intervention, boundary, or discrimination;
- cite at least one valid reconciled role;
- state rationale and decision use;
- name the measurements or comparisons required to answer it; and
- retain exact source evidence.

The run produced 1,271 role claims and 81 questions. Ten papers produced no accepted question;
this is an intentional no-quota behavior. Across the corpus, 191 model candidates were rejected
for non-verbatim spans, invalid role references, malformed question syntax, or other schema
violations. All persisted items passed deterministic revalidation.
