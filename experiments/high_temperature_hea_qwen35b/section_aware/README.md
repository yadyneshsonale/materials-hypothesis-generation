# Section-aware extraction experiment

This experiment uses validated v2 evidence as scientific triggers, retrieves relevant Methods,
Results, Discussion, figure-caption, and table context from elsewhere in the same paper, and asks
Qwen to generate grounded cross-section questions and research threads.

The factual substrate remains the normalized v2 evidence. Questions are a reasoning and retrieval
interface, not facts.

## Pipeline

```text
paper text
  -> deterministic section-aware paper map
  -> one validated v2 evidence unit as a scientific trigger
  -> hybrid retrieval from other sections of the same paper
  -> Qwen compatibility check for sample/state/experiment identity
  -> cross-section links with exact spans
  -> decision-relevant questions
  -> research thread with a deterministic provenance bundle
```

Retrieval combines explicit figure/table references, sample and material identifiers, structured
terms from the v2 evidence unit, lexical overlap, and section priority. Up to four passages are
retrieved for each trigger. Passages are excerpted before prompting so large sections cannot exceed
the model context window.

Qwen must reject passages that do not concern the same sample, state, experiment, or relevant
comparison. It may generate mechanism, evidence-testing, comparison, boundary, replication,
variable-change, transfer, or experiment-planning questions. Questions without both a scientific
rationale and a clearly stated unresolved issue are rejected.

## Completed run

| Measure | Result |
|---|---:|
| Papers | 50 |
| Validated v2 evidence triggers | 276 |
| Retained questions | 482 |
| Validated cross-section links | 588 |
| Questions spanning more than one section | 317 |
| Cross-section question rate | 65.77% |
| Triggers with at least one question | 274 |
| Exact validated spans | 3,307 / 3,307 |
| Unknown evidence IDs | 0 |
| Unknown chunk IDs | 0 |
| Invalid research-thread provenance | 0 |

The most common question functions were:

- mechanism explanation: 135;
- comparison: 112;
- evidence testing: 109;
- boundary finding: 90;
- experiment planning: 16.

The agent linked 86 Method passages, 76 sample-lineage passages, 97 figure-caption or figure-reference
passages, 152 comparisons, and 125 mechanism passages. Results and Discussion were the most common
source sections, followed by Methods/Materials and Introduction.

Four generated questions were removed because they did not state both why the question matters and
what remains unresolved. Eighty-four proposed links were removed because their model-supplied span
was not an exact substring of the linked chunk. This rejection is intentional: an unsupported link
is not converted into valid evidence.

## Output layout

```text
section_aware/
├── paper_maps/          # deterministic chunks, sections, content types, and hashes
├── papers/              # validated links, questions, and research threads per paper
├── results/
│   ├── evaluation.json  # grounding and identifier integrity audit
│   └── quality_review.json
├── status.json
└── COMPLETE
```

Every research thread includes:

- its triggering v2 evidence-unit ID;
- all supporting chunk IDs;
- exact evidence spans from the trigger and validated cross-section links.

This provenance makes the synthesis auditable, but does not prove that every phrase in the
model-written research thread is entailed by every cited span.

## Scientific assessment

The outputs address the principal weakness of local question generation. Representative questions
now connect a reported property to processing details, test parameters, microstructure, alternative
mechanisms, or condition boundaries found elsewhere in the paper. Mechanism, evidence-testing,
comparison, and boundary questions dominate, rather than superficial clarification questions.

These questions should be used together with v2 evidence. They are not a replacement for the
sample-process-structure-condition-measurement records.

Current limitations:

- figure support uses captions and textual figure references; image pixels, curves, and plotted
  values are not yet interpreted by a vision model;
- research-thread prose is Qwen synthesis over grounded context and still needs expert review;
- hybrid retrieval can miss implicit links that share no sample identifier or terminology;
- scientific novelty and experimental feasibility require materials-expert ranking;
- this experiment validates extraction quality, not yet a new temporal hypothesis benchmark
  comparison.

Run in detached tmux:

```bash
tmux new-session -d -s mathg-section-aware \
  "cd $(pwd) && bash run_section_aware_experiments.sh"
```

Monitor:

```bash
cat experiments/high_temperature_hea_qwen35b/section_aware/status.json
tail -f experiments/high_temperature_hea_qwen35b/section_aware/logs/pipeline.log
```

Canonical outputs:

- `paper_maps/`: deterministic searchable chunk maps;
- `papers/`: validated links, questions, and research threads per paper;
- `results/evaluation.json`: exact-grounding and identifier integrity audit;
- `results/quality_review.json`: distributions and scientific strengths/limitations.
