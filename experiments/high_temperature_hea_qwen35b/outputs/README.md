# Output data, extraction rules, and provenance

This directory contains the machine-generated outputs for the 50-paper open-access
high-temperature high-entropy-alloy experiment. It documents what the inputs are, which model and
prompts were used, how papers were chunked, which rules controlled role and question generation,
how outputs were validated, and how the files should be interpreted.

**In brief:** each paper folder contains the original JATS XML, a visual-reference PDF, citation
metadata, reconciled argumentative roles, high-recall reader questions, and rejection audits. The
Qwen3.5-35B-A3B pipeline converted the XML into section-preserving text, processed it in
overlapping chunks, extracted 11 role types, generated questions that mimic a scientist's reading
process, and retained linked material–process–structure–mechanism–property evidence. Every accepted
role and question was checked against an exact quotation from the XML-derived paper text; the
consolidated files and corpus-level evaluations are stored in the adjacent `results/` directory.

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

## Start here: what this experiment is doing

The project starts with 50 research papers about high-temperature high-entropy alloys. A long-term
goal is to use the literature to support new, testable materials hypotheses. Raw papers cannot be
given safely to a hypothesis generator without preserving where each statement came from and what
kind of statement it is.

This experiment therefore creates three different views of every paper:

1. **Argumentative roles:** What job does a passage perform in the paper's argument? For example,
   does it state a problem, report evidence, propose a mechanism, or describe a limitation?
2. **Reader questions:** What might a scientist naturally ask while reading that passage? For
   example, why was a temperature selected, what evidence supports a mechanism, or would the
   result transfer to another alloy?
3. **Linked materials evidence:** What material, treatment, structure, mechanism, condition, and
   outcome belong together in one evidence chain? These records are stored beside this directory
   at [`../materials_evidence/`](../materials_evidence/).

These are complementary outputs:

- roles help explain the paper's argument;
- questions expose uncertainty and possible next reasoning steps; and
- linked evidence is the safest representation for later hypothesis generation.

None of these outputs is treated as automatically true merely because the model produced it.
Every accepted item must point back to exact text in the paper, and domain experts must still judge
scientific correctness and usefulness.

## The complete journey of one paper

The following steps happen for each paper.

### Step 1: store the source article

The original open-access JATS XML is stored as:

```text
papers/<PMCID>/input/article.xml
```

A checksum-verified PDF is stored beside it for a human to view:

```text
papers/<PMCID>/input/article.pdf
```

The PDF is not the extraction source. It may format citations, formulas, and columns differently
from the XML.

### Step 2: convert XML into readable extraction text

The XML is converted into structure-preserving plain text under
[`../data/corpus/text/`](../data/corpus/text/). The text retains section order and section labels
such as Abstract, Introduction, Methods, Results, Discussion, and Conclusion.

This text is the authoritative source for:

- model input;
- exact evidence checks;
- section names in outputs; and
- context displayed in the review interface.

### Step 3: divide the paper into manageable passages

The paper is too long to process as one undifferentiated prompt. It is divided into passages:

- the role pass primarily follows article sections, with a 900-word/100-word-overlap fallback;
- the reader-question pass uses smaller approximately 450-word passages with 50-word overlap; and
- reference, acknowledgment, and supporting-information end matter is excluded from reader
  questions.

Overlap prevents a statement at a chunk boundary from losing its context.

### Step 4: ask Qwen to extract role candidates

For each role passage, Qwen receives:

```text
SYSTEM INSTRUCTIONS
  - definitions of all 11 roles
  - distinctions between easily confused roles
  - exact evidence-copying rules
  - required JSON shape

SECTION GUIDANCE
  - current article section and likely role emphasis

CURRENT PAPER PASSAGE
  - XML-derived text from this paper only
```

The prompt asks the model to return zero or more candidates:

```json
{
  "role": "evidence_result",
  "content": "A concise interpretation of what the passage reports.",
  "evidence_span": "An exact contiguous quotation from the supplied passage."
}
```

The prompt does **not** ask the model to fill every role. An empty role is preferable to inventing
unsupported content.

### Step 5: validate and reconcile roles

Code checks each candidate before it can continue:

- the role key must be one of the 11 allowed roles;
- `content` cannot be empty; and
- `evidence_span` must be an exact substring of the supplied passage.

Valid chunk candidates are then sent to a paper-level reconciliation prompt. That prompt merges
only genuine duplicates, keeps different materials and operating regimes separate, selects the
single best role, and preserves exact evidence.

The final roles are written to:

```text
papers/<PMCID>/output/roles.json
```

### Step 6: read the paper again to generate questions

Question generation is a separate high-recall pass. It does not ask for only a few polished
hypothesis questions. Instead, it imitates the ongoing thoughts of a scientist reading the paper.

For each 450-word passage, Qwen receives:

```text
SYSTEM INSTRUCTIONS
  - examples of scientific reading questions
  - 14 allowed question types
  - 10 allowed reading steps
  - intent and relevance labels
  - exact evidence and JSON rules

READING STATE
  - paper title
  - current section
  - progress through the paper, for example 8/21
  - final 100 words of the preceding passage
  - 12 most recent accepted questions

CURRENT PAPER PASSAGE
  - the only text permitted to supply evidence
```

The reading state helps the model maintain continuity and avoid asking exactly the same question
again. It is **not** allowed to serve as evidence.

The model returns records such as:

```json
{
  "question": "What specific vacuum pressure and air flow conditions defined the oxidation environments?",
  "question_type": "clarification",
  "reading_step": "clarify",
  "reader_intent": "understand",
  "relevance": "direct",
  "rationale": "Oxidation behavior is sensitive to atmosphere.",
  "evidence_span": "Mn is the major oxide-forming element in both vacuum and air environments",
  "confidence": 0.95
}
```

This example means:

- the scientist is trying to understand an underspecified condition;
- the question is directly about the paper;
- the rationale explains why the thought matters; and
- the exact quotation records what triggered the thought.

### Step 7: validate, deduplicate, and link questions

Code checks every question for allowed categories, length, syntax, rationale, confidence, and exact
grounding in the current passage. Only exact duplicate question text is removed. Similar questions
are retained intentionally because relevance and redundancy filtering happen later.

If a question's evidence overlaps a reconciled role, the question records that role reference.
The final questions are written to:

```text
papers/<PMCID>/output/questions.json
```

Rejected candidates are written to:

```text
papers/<PMCID>/output/reader_question_rejections.json
```

### Step 8: extract linked materials evidence

A separate prompt asks for evidence units that keep the scientific relationship intact:

```text
material + intervention -> structure -> mechanism -> outcome
                        + conditions + comparison + provenance
```

This prevents a later agent from accidentally combining, for example, the processing condition
from one alloy with the mechanism or measured property of another.

The output is written to:

```text
../materials_evidence/<PMCID>.json
```

### Step 9: review outputs beside the paper

The interface loads the roles and questions, displays their exact XML-derived context, finds the
best corresponding PDF page, and draws visual highlights. A reviewer can filter roles and search
or filter questions by type, intent, and relevance.

The highlighted PDF is a convenience for inspection. The exact XML-derived evidence remains the
authoritative provenance.

## Inputs, prompts, and outputs at a glance

| Stage | Input given to model | Main prompt request | Accepted output | Stored at |
| --- | --- | --- | --- | --- |
| Role extraction | One XML-derived section or passage | Identify only supported argumentative roles and quote exact evidence | Raw role candidates | `papers/<PMCID>/output/roles.json` under `raw_by_role` |
| Role reconciliation | Valid role candidates from one paper | Merge duplicates, separate regimes, enforce strict role definitions | Final role claims | `papers/<PMCID>/output/roles.json` under `reconciled_by_role` |
| Reader questions | One 450-word passage plus continuity state | Ask many natural scientific-reading questions triggered by the passage | Grounded questions with type, step, intent, relevance, rationale, and confidence | `papers/<PMCID>/output/questions.json` |
| Linked evidence | XML-derived paper chunks | Preserve linked material/process/structure/mechanism/property evidence | Structured evidence units | `../materials_evidence/<PMCID>.json` |
| Deterministic evaluation | Stored JSON plus complete XML-derived text | No model call; recheck schema and exact provenance | Corpus metrics and invalid-item report | `../results/*.json` and `*.jsonl` |

## A concrete role example

Suppose a passage says that mass gain decreased after adding an element.

- `evidence_result` is appropriate if the passage reports the measured decrease.
- `causal_claim` is appropriate only if the paper claims that the addition caused the decrease.
- `mechanism_principle` is appropriate only if the paper explains why, such as formation of a
  dense protective oxide.
- `hypothesis_statement` is not appropriate if the behavior has already been observed; a
  hypothesis must be a prospective testable expectation.

A final role record therefore separates interpretation from provenance:

```json
{
  "content": "Chromium addition reduced oxidation mass gain at 800 C.",
  "evidence_spans": [
    "Cr addition reduced mass gain from 10.4 to 5.1 mg/cm2 at 800 C."
  ],
  "conflicting": false
}
```

`content` is concise model interpretation. `evidence_spans` is the exact source needed to verify
that interpretation.

## Directory layout

```text
outputs/
├── README.md
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

| Question type | What the reader is asking |
| --- | --- |
| `clarification` | What does a term, value, material, condition, or statement mean? |
| `rationale` | Why did the authors make this choice? |
| `mechanism` | How or why could the reported behavior occur? |
| `method` | What procedure, instrument, model, parameter, or analysis was used? |
| `evidence` | What observation supports the claim, and is it sufficient? |
| `comparison` | How does this differ from a baseline, another material, or prior work? |
| `relevance` | Does this matter for the reader's problem or design goal? |
| `counterfactual` | What would happen if a variable or choice changed? |
| `boundary` | Under what condition does the behavior stop, reverse, or fail? |
| `assumption` | What unstated or stated assumption does the result depend on? |
| `limitation` | What uncertainty, confounder, missing control, or weakness restricts the conclusion? |
| `transfer` | Would the result carry to another alloy, process, scale, or environment? |
| `replication` | What information is needed to reproduce the work? |
| `follow_up` | What should be measured, tested, or read next? |

### Reading steps

Each question also records the thought operation that produced it:

| Reading step | Thought operation |
| --- | --- |
| `clarify` | Resolve what the passage means. |
| `inspect_choice` | Examine why a material, method, parameter, or design was selected. |
| `trace_mechanism` | Follow the proposed causal or physical explanation. |
| `test_evidence` | Judge whether the evidence supports the claim. |
| `compare` | Contrast against another condition, material, baseline, or report. |
| `assess_relevance` | Decide whether the finding matters for another goal or system. |
| `change_variable` | Consider the effect of changing a controllable variable. |
| `find_boundary` | Identify a validity or failure regime. |
| `identify_gap` | Notice missing information, assumptions, uncertainty, or controls. |
| `plan_follow_up` | Form the next reading, measurement, or experiment step. |

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

[`../materials_evidence/`](../materials_evidence/) contains records designed for hypothesis generation.
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
