# Output data, extraction rules, and provenance

This directory contains the machine-generated outputs for the 50-paper open-access
high-temperature high-entropy-alloy experiment. It documents what the inputs are, which model and
prompts were used, how papers were chunked, which rules controlled role and question generation,
how outputs were validated, and how the files should be interpreted.

## Summary

| Output | Papers | Accepted records | Exact grounding |
| --- | ---: | ---: | ---: |
| Linked materials-evidence units | 50 | 493 | 100% |
| Reconciled argumentative-role claims | 50 | 1,271 | 100% |
| High-recall reader questions | 50 | 8,848 | 100% |
| Original strict decision questions, archived separately | 50 | 81 | 100% |

The current per-paper `questions.json` files contain the **8,848 high-recall reader questions**.
The earlier set of 81 strict decision questions is preserved in
[`../results/decision_questions.jsonl`](../results/decision_questions.jsonl).

## Directory layout

```text
outputs/
├── README.md
├── materials_evidence/
│   └── <PMCID>.json
└── papers/
    ├── README.md
    └── <PMCID>/
        ├── metadata.json
        ├── input/
        │   ├── README.md
        │   ├── article.xml
        │   └── article.pdf
        └── output/
            ├── roles.json
            ├── questions.json
            ├── rejected_items.json
            └── reader_question_rejections.json
```

Consolidated datasets and evaluations are stored in [`../results/`](../results/):

- [`questions.jsonl`](../results/questions.jsonl): 8,848 high-recall reader questions;
- [`roles.jsonl`](../results/roles.jsonl): 1,271 reconciled role claims;
- [`decision_questions.jsonl`](../results/decision_questions.jsonl): the original 81 strict
  decision questions;
- [`reader_question_evaluation.json`](../results/reader_question_evaluation.json): question
  counts, distributions, grounding, and per-paper metrics;
- [`role_question_evaluation.json`](../results/role_question_evaluation.json): original
  role/decision-question evaluation; and
- [`corpus_evaluation.json`](../results/corpus_evaluation.json): linked materials-evidence
  evaluation.

## Source corpus and selection

The corpus contains 50 open-access primary-research papers selected from Europe PMC and ranked by
`citedByCount`. Reviews, corrections, supporting-data records, retracted papers, papers without
open-access JATS full text, and papers outside elevated-temperature HEA behavior were excluded.

The query covered high-entropy alloys together with terms such as high temperature, elevated
temperature, refractory, creep, oxidation, thermal stability, hot corrosion, superalloy, extreme
temperature, and phase stability. Full selection rules, exclusions, metadata, and the
date-dependent citation ranking are documented in
[`../data/corpus/README.md`](../data/corpus/README.md),
[`../data/corpus/manifest.json`](../data/corpus/manifest.json), and
[`../data/corpus/screening_audit.json`](../data/corpus/screening_audit.json).

## Authoritative inputs

### JATS XML

`papers/<PMCID>/input/article.xml` is the canonical machine-readable article. It is the original
open-access JATS XML retrieved for that paper.

### Structure-preserving text

The actual extraction input is the XML-derived text in
[`../data/corpus/text/`](../data/corpus/text/). Section names and article order are retained so
extracted records can refer to their source section.

All deterministic grounding checks use this text. An accepted evidence span must occur as an
exact character substring of the paper text.

### PDF

`papers/<PMCID>/input/article.pdf` is included **only for human visual review**. Each PDF was
downloaded from the official PMC Open Access object store, checked for a PDF signature, and
verified against the MD5 checksum in PMC metadata.

The PDF was not used to generate roles, questions, or materials-evidence records. The review
interface reads the PDF text layer only after extraction to locate visual highlight rectangles.
PDF page matching is therefore a presentation aid, not evidence provenance.

## Model and inference environment

| Setting | Value |
| --- | --- |
| Model | Qwen3.5-35B-A3B |
| Quantization | GGUF Q4_K_M |
| Inference server | llama.cpp |
| llama.cpp revision | `a8c9a4e7ccba890d6a2644a235492f836a7371c3` |
| Hardware | 4 × NVIDIA Tesla V100-DGXS, 32 GB each |
| CUDA | CUDA 12 libraries, compute capability 7.0 build |
| Context | 32,768 tokens per request slot |
| Parallel slots | 4 |
| Thinking mode | disabled with `{"enable_thinking": false}` |
| Request timeout | 300 seconds for the role/question runs |

CUDA 13 could load the model but could not generate on Volta GPUs. The successful llama.cpp build
targeted architecture 70 and linked CUDA 12 `libcudart`, `libcublas`, and `libcublasLt`.

## Shared evidence-grounding rules

The role, question, and linked-evidence prompts used the following common rules:

1. Evidence must be copied from the supplied XML-derived paper text.
2. An evidence span must be one exact, contiguous substring.
3. The model must not insert ellipses, normalize notation, or combine separated passages.
4. Missing information must remain missing; it must not be inferred from domain knowledge.
5. A statement attributed only to cited literature must not be presented as the current paper's
   result.
6. Different materials, compositions, treatments, temperatures, environments, and loading
   regimes must not be merged.
7. Model output is accepted only after deterministic schema and grounding validation.
8. Rejected candidates and their reasons are retained for audit rather than silently repaired.

## Eleven argumentative roles

Roles describe how a passage functions in the paper's argument. They are not, by themselves, a
complete material/process/structure/property representation.

| Role key | Acceptance meaning |
| --- | --- |
| `problem_motivation` | The gap, unresolved problem, or need addressed by the paper. |
| `prior_approach` | A method, result, or approach explicitly described as prior work. |
| `prior_limitation` | A stated weakness or insufficiency of a prior approach. |
| `rejected_alternative` | An option the authors explicitly chose not to use, together with the reason. |
| `inspiration_source` | An analogy, borrowed method, or prior finding that shaped the current approach. |
| `causal_claim` | A claim that one factor caused, increased, or decreased another. |
| `mechanism_principle` | Physical or chemical reasoning offered to explain a causal claim. |
| `hypothesis_statement` | A prospective, testable prediction about behavior or an intervention and outcome. |
| `evidence_result` | A measured or calculated result supporting or refuting a claim. |
| `constraint` | A design requirement, validity boundary, experimental limitation, or operating limit. |
| `contradiction` | The paper's result explicitly conflicts with a named prior claim or accepted expectation. |

### Role disambiguation rules

The extraction prompt explicitly stated that:

- a measured result is not automatically a causal mechanism;
- a study objective is not a hypothesis;
- an unusual result is not a contradiction unless the conflicting expectation is named;
- a test condition is not a constraint unless it limits design, validity, or operation;
- a performance comparison is not a rejected alternative unless the authors explicitly decided
  not to use an option and gave a reason;
- a methodological benefit is not an inspiration source without a borrowed method, analogy, or
  prior finding that shaped the work; and
- cited work normally belongs in `prior_approach`, `prior_limitation`, or `inspiration_source`
  unless the current paper directly tests or contradicts it.

### Role chunking and reconciliation

The structure-preserving text was first split by recognizable article headers. If reliable
headers were unavailable, the fallback used 900-word windows with 100-word overlap. Chunks were
also constrained to 60% of the configured model context, leaving space for instructions and
output.

Each chunk was checked against all 11 roles. Accepted chunk candidates required:

- a known role key;
- non-empty interpreted content; and
- one exact evidence span present in that chunk.

Paper-level reconciliation then:

- merged only genuine duplicates;
- kept different materials, treatments, temperatures, environments, and loads separate;
- assigned a claim to its single best role unless two functions were explicit;
- kept conflicting claims separate;
- retained exact evidence spans; and
- reapplied strict tests for hypotheses, contradictions, rejected alternatives, and inspiration.

At most 24 raw candidates per role were supplied to final reconciliation to bound the paper-level
context. The complete prompt and validators are implemented in
[`../../../role_question_extract.py`](../../../role_question_extract.py) and the taxonomy is
defined in [`../../../roles.py`](../../../roles.py).

## High-recall reader questions

The latest question pass was designed to model the natural thought process of a scientist reading
a paper. It deliberately generates many grounded questions first; relevance filtering occurs
later in the interface or downstream analysis.

The prompt asks questions such as:

- What exactly does this term, variable, or result mean?
- What material, composition, instrument, model, parameter, or procedure is being used?
- Why was this option chosen instead of an alternative?
- Why might the reported mechanism work?
- What evidence supports or challenges the explanation?
- How does the result compare with a baseline or prior work?
- Is the result relevant or transferable to another alloy, process, scale, or service regime?
- What would happen if composition, temperature, time, atmosphere, load, or processing changed?
- Where does the behavior stop working?
- Which failure mode, confounder, uncertainty, assumption, or missing control matters?
- What information is required for replication?
- What should be checked next in the paper or in a follow-up experiment?

### Question types

The allowed `question_type` values are:

`clarification`, `rationale`, `mechanism`, `method`, `evidence`, `comparison`, `relevance`,
`counterfactual`, `boundary`, `assumption`, `limitation`, `transfer`, `replication`, and
`follow_up`.

### Reading steps

Each question also records the thought operation that produced it:

`clarify`, `inspect_choice`, `trace_mechanism`, `test_evidence`, `compare`,
`assess_relevance`, `change_variable`, `find_boundary`, `identify_gap`, or `plan_follow_up`.

### Intent and relevance

`reader_intent` is one of `understand`, `evaluate`, `apply`, `replicate`, or `extend`.

`relevance` is:

- `direct`: directly about the paper's system, claim, method, or conclusion;
- `adjacent`: a comparison or transfer to a closely related system or condition; or
- `exploratory`: a farther extension that is still concretely triggered by the passage.

Relevance is metadata, not an acceptance gate. This preserves questions for later filtering.

### Question chunking and context state

Question generation used approximately 450-word windows with 50-word overlap. References,
acknowledgments, and supporting-information end matter were excluded.

Within each paper, chunks were processed in reading order. Every model call received:

- the paper title;
- the current section;
- reading progress such as `8/21`;
- the final 100 words of the preceding passage, for continuity only; and
- the 12 most recent accepted questions, to discourage exact repetition.

This state could guide continuity but was explicitly prohibited as evidence. Every question still
had to be triggered by, and quote evidence from, the current passage.

The target number of questions scaled with passage length:

```text
minimum = max(3, min(16, word_count // 35))
maximum = max(minimum + 4, min(30, word_count // 18))
```

For a typical 450-word passage, the target was 12–25 questions. Multiple questions could arise
from one sentence when they represented different scientific thoughts.

### Question acceptance rules

An accepted question had to:

1. end with a question mark;
2. contain one primary thought in at most 60 words;
3. use an allowed question type, reading step, intent, and relevance tier;
4. include a non-empty rationale;
5. contain exactly one evidence span copied from the current passage;
6. have confidence between 0 and 1; and
7. not be an exact duplicate of another accepted question.

Only exact duplicates were removed. Near-duplicates and exploratory questions were intentionally
preserved because this stage optimizes recall. Questions were linked to reconciled roles when
their evidence spans overlapped.

The generator, complete prompt, validators, checkpointing, and installation logic are in
[`../../../reader_question_generate.py`](../../../reader_question_generate.py). A concise prompt
contract is also available at
[`../../../prompts/reader-question-generation.md`](../../../prompts/reader-question-generation.md).

## Question execution and final results

The high-recall run processed 775 chunks across 50 papers:

- 730 new Qwen calls;
- 46 chunks reused from valid checkpoints;
- four concurrent paper workers, matching four llama.cpp slots;
- sequential chunk processing within each paper to preserve reading state;
- atomic per-chunk checkpoints keyed by paper and chunk SHA-256 hashes; and
- 1,914 rejected or deduplicated candidates retained for audit.

Final accepted results:

| Metric | Value |
| --- | ---: |
| Questions | 8,848 |
| Mean per paper | 176.96 |
| Median per paper | 168.5 |
| Minimum per paper | 79 |
| Maximum per paper | 314 |
| Mean confidence | 0.8440 |
| Exact grounding | 100% |
| Invalid persisted questions | 0 |
| Papers without questions | 0 |

Question-type counts:

| Type | Count | Type | Count |
| --- | ---: | --- | ---: |
| Clarification | 1,858 | Method | 1,493 |
| Mechanism | 1,411 | Rationale | 890 |
| Counterfactual | 669 | Comparison | 625 |
| Assumption | 602 | Evidence | 527 |
| Boundary | 315 | Follow-up | 134 |
| Limitation | 130 | Relevance | 112 |
| Replication | 63 | Transfer | 19 |

The exact evaluation is stored in
[`../results/reader_question_evaluation.json`](../results/reader_question_evaluation.json).

## Original strict decision questions

Before the high-recall reader pass, the pipeline generated 81 strict decision questions across
five types: `baseline`, `causal`, `intervention`, `boundary`, and `discrimination`.

Those questions had additional gates:

- at most 50 words;
- at least one valid reconciled-role reference;
- an explicit decision use;
- non-empty measurements or comparisons required to answer the question; and
- exact source evidence.

That pass optimized precision for hypothesis planning and produced only 1.62 questions per paper,
including ten papers with none. It is retained for comparison in
[`../results/decision_questions.jsonl`](../results/decision_questions.jsonl), but it is not the
current per-paper question output.

## Linked materials-evidence output

[`materials_evidence/`](materials_evidence/) contains records designed for hypothesis generation.
Unlike flat argumentative roles, each unit attempts to preserve a linked chain:

```text
material/composition
  + intervention or initial state
  -> structure, phase, or defect state
  -> mechanism
  -> measured or calculated property outcome
  + conditions + comparison + limitations + exact provenance
```

The prompt required separate records for different material states and operating regimes, no
mechanism or outcome transfer between systems, empty fields for unstated facts, exclusion of
cited-background results, and exact contiguous evidence. Deterministic validation checked schema,
evidence type, confidence, meaningful linked facets, and exact grounding.

The final linked-evidence set contains 493 accepted units, 125 rejected candidates, 100% exact
grounding, and a 56.19% complete core-chain rate. See
[`../results/corpus_evaluation.json`](../results/corpus_evaluation.json) and
[`../../../materials_extract.py`](../../../materials_extract.py).

## Per-paper file contracts

### `metadata.json`

Contains paper rank, citation and bibliographic metadata, license, PMC version, checksum-qualified
PDF source, and an explicit statement that the PDF is visual-only.

### `input/article.xml`

Canonical JATS XML input. Use this, or its structure-preserving text derivative, for machine
analysis and provenance.

### `input/article.pdf`

Human visual reference only. Do not treat PDF page matching as extraction evidence.

### `output/roles.json`

Contains:

- `schema_version`;
- `paper_id`;
- `chunks_processed`;
- `raw_by_role`: accepted pre-reconciliation role candidates; and
- `reconciled_by_role`: final role claims with `content`, exact `evidence_spans`, and
  `conflicting`.

### `output/questions.json`

Contains:

- schema and paper identifiers;
- generation mode and processing steps;
- chunk, model-call, and resume counts; and
- high-recall `questions`.

Each question includes a deterministic `question_id`, text, type, reading step, intent, relevance,
rationale, source section, chunk index, overlapping role references, one exact evidence span, and
confidence.

### `output/rejected_items.json`

Audit from the original role and strict decision-question run. It contains rejected model payloads,
pipeline stage, and explicit rejection reason.

### `output/reader_question_rejections.json`

Audit from high-recall question generation. It records malformed values, unknown categories,
non-verbatim spans, invalid confidence, and exact duplicates removed across overlapping chunks.

## How outputs are used

- **Roles** support inspection of the paper's argumentative structure and provide optional links
  for questions.
- **Reader questions** support human-like paper reading, exploration, experiment ideation, and
  later relevance filtering.
- **Linked materials evidence** is the preferred input for the hypothesis-generation agent because
  it preserves material/process/structure/mechanism/property relationships.
- **Rejected-item files** support error analysis and prompt/validator improvement; they are not
  accepted evidence.
- **PDFs** support human review and visual highlighting only.

The review interface supports:

- paper selection;
- multi-select role filters;
- question text search;
- type, intent, and relevance filters;
- exact XML-derived evidence context;
- PDF page navigation; and
- best-effort coordinate-level PDF highlights.

## Reproduction

Start the configured Qwen OpenAI-compatible endpoint, then set:

```bash
export MATHG_PROVIDER=openai
export OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export OPENAI_API_KEY=local
export OPENAI_MODEL=Qwen3.5-35B-A3B-Q4_K_M.gguf
export OPENAI_CHAT_TEMPLATE_KWARGS='{"enable_thinking":false}'
export MATHG_REQUEST_TIMEOUT=300
export MATHG_CONTEXT_WINDOW=32768
```

Generate high-recall questions:

```bash
.venv/bin/python reader_question_generate.py \
  --input-dir experiments/high_temperature_hea_qwen35b/data/corpus/text \
  --papers-dir experiments/high_temperature_hea_qwen35b/outputs/papers \
  --out-dir /tmp/reader-questions \
  --checkpoint-dir /tmp/reader-question-checkpoints \
  --workers 4 \
  --resume \
  --install
```

Validate and consolidate them:

```bash
.venv/bin/python evaluate_reader_questions.py \
  --question-dir experiments/high_temperature_hea_qwen35b/outputs/papers \
  --source-dir experiments/high_temperature_hea_qwen35b/data/corpus/text \
  --output experiments/high_temperature_hea_qwen35b/results/reader_question_evaluation.json \
  --questions-jsonl experiments/high_temperature_hea_qwen35b/results/questions.jsonl
```

Serve the review interface:

```bash
.venv/bin/python review_interface_server.py --host 0.0.0.0 --port 8765
```

## Interpretation and limitations

- The corpus is ranked by Europe PMC citation counts as observed on the collection date, not by a
  universal citation index.
- JATS availability biases the corpus toward papers deposited in PubMed Central.
- Exact grounding proves that evidence text occurs in the paper; it does not prove that every
  model interpretation or question is scientifically valuable.
- Confidence is model-reported and is not a calibrated probability.
- The reader-question set intentionally contains near-duplicates and exploratory questions to
  maximize recall. Use the interface filters or downstream ranking before selecting questions for
  hypothesis generation.
- PDF text extraction can differ from XML in citation formatting, formulas, ligatures, and reading
  order. PDF highlights are best-effort visual alignment.
- Materials-expert review is still required before treating extracted mechanisms, causal claims,
  or generated questions as validated scientific conclusions.

For the full experimental narrative, see [`../METHODS.md`](../METHODS.md) and
[`../README.md`](../README.md).
