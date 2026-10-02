# High-temperature HEA evidence extraction with Qwen3.5-35B-A3B

This folder is the reproducible record of a linked-evidence extraction and hypothesis-generation
experiment over 50 open-access primary-research papers about high-temperature high-entropy alloys
(HEAs). It contains the screened source corpus, all accepted and rejected model outputs, aggregate
evaluation, a complete adaptive-agent trace, and the manually grounded pilot used before the full
run.

The experiment addresses a materials-expert review of the original flat 11-role representation:
isolated argumentative labels did not preserve the composition/process -> structure -> mechanism ->
property relationships needed for defensible hypothesis generation. The replacement pipeline
extracts condition-specific linked evidence units with verbatim provenance and uses five
deterministic, decision-oriented research tasks.

## Results at a glance

| Metric | Result |
| --- | ---: |
| Source papers | 50 |
| Papers with completed output | 50 |
| Valid linked evidence units | 493 |
| Invalid persisted units | 0 |
| Model candidates rejected during extraction | 125 |
| Verbatim grounding rate | 100% |
| Mean valid units per paper | 9.86 |
| Complete core-chain rate | 56.19% |
| Mean model confidence | 0.8951 |
| Experimental / simulation / theory / mixed units | 365 / 85 / 26 / 17 |

Facet coverage among the 493 valid units was 100% for material, intervention, outcome, and
provenance; 97.97% for structure; 95.13% for mechanism; 83.37% for operating conditions; 69.17%
for comparisons; and 12.37% for explicit limitations.

The adaptive workflow retrieved from all 493 units, accumulated 15 relevant unique units, and
generated one candidate hypothesis. Its critics scored plausibility 3/5, novelty 4/5, and
feasibility 4/5. The plausibility critic identified a substantive weakness: relying on a
Cr2O3-dominant protective scale in a W-rich alloy above 1000 C may be chemically unstable because
volatile chromium oxides can form. The generated candidate is therefore a testable research lead,
not a validated recommendation; an alumina-forming alternative should be evaluated.

### Eleven-role and question extraction

A second pass retained the original 11-role representation while applying stricter role semantics,
exact source grounding, and a new definition of a useful question.

| Metric | Result |
| --- | ---: |
| Papers with role/question output | 50/50 |
| Reconciled role claims | 1,271 |
| Valid decision questions | 81 |
| Invalid persisted items | 0 |
| Mean questions per paper | 1.62 |
| Mean question confidence | 0.8074 |
| Papers with no sufficiently grounded question | 10 |
| Rejected model candidates | 191 |

A **decision question** is a specific, answerable, and falsifiable information need whose answer
changes a materials-design choice, causal-mechanism choice, boundary condition, or experiment.
Every accepted question records its rationale, decision use, required measurements, grounded role
references, exact source passages, and confidence.

The 81 questions comprise 26 boundary, 19 discrimination, 18 causal, 16 intervention, and two
baseline questions. The pipeline emits zero questions rather than manufacture one when the paper's
role evidence does not support a decision-useful uncertainty.

## Folder contents

```text
high_temperature_hea_qwen35b/
├── README.md
├── METHODS.md
├── experiment_config.json
├── data/
│   └── corpus/
│       ├── README.md
│       ├── manifest.json
│       ├── metadata.json
│       ├── screening_audit.json
│       ├── text/                 # 50 structure-preserving text files
│       └── xml/                  # 50 open-access JATS XML articles
├── outputs/
│   ├── materials_evidence/       # linked evidence, one JSON record per paper
│   └── role_questions/           # 11 roles and decision questions per paper
├── results/
│   ├── corpus_evaluation.json
│   ├── adaptive_trace.json
│   ├── role_question_evaluation.json
│   ├── roles.jsonl               # 1,271 consolidated grounded role claims
│   └── questions.jsonl           # 81 consolidated decision questions
└── pilot/
    ├── materials_evidence/       # six manually curated grounded units
    ├── evaluation.json
    └── adaptive_trace.json
```

Article licenses vary. Consult `data/corpus/manifest.json` and `data/corpus/metadata.json` before
redistributing or reusing individual articles.

## Reproduce the extraction

Create the repository environment as described in the top-level README and start an
OpenAI-compatible server for `Qwen3.5-35B-A3B` Q4_K_M. The successful run used llama.cpp with
thinking disabled:

```bash
export MATHG_PROVIDER=openai
export OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export OPENAI_API_KEY=local
export OPENAI_MODEL=Qwen3.5-35B-A3B-Q4_K_M.gguf
export OPENAI_CHAT_TEMPLATE_KWARGS='{"enable_thinking":false}'
export MATHG_CONTEXT_WINDOW=32768

.venv/bin/python materials_extract.py \
  --input-dir experiments/high_temperature_hea_qwen35b/data/corpus/text \
  --out-dir experiments/high_temperature_hea_qwen35b/outputs/materials_evidence \
  --workers 4 --resume
```

The four-worker run completed 48 papers. Two requests exceeded the 120-second HTTP timeout under
contention and were completed with the same command using `--workers 1 --resume`.

Evaluate the persisted outputs:

```bash
.venv/bin/python evaluate_materials_corpus.py \
  --evidence-dir experiments/high_temperature_hea_qwen35b/outputs/materials_evidence \
  --source-dir experiments/high_temperature_hea_qwen35b/data/corpus/text \
  --output experiments/high_temperature_hea_qwen35b/results/corpus_evaluation.json
```

Extract the 11 roles and decision questions:

```bash
.venv/bin/python role_question_extract.py \
  --input-dir experiments/high_temperature_hea_qwen35b/data/corpus/text \
  --out-dir experiments/high_temperature_hea_qwen35b/outputs/role_questions \
  --workers 4 --resume
```

Validate and consolidate the role/question outputs:

```bash
.venv/bin/python evaluate_role_questions.py \
  --evidence-dir experiments/high_temperature_hea_qwen35b/outputs/role_questions \
  --source-dir experiments/high_temperature_hea_qwen35b/data/corpus/text \
  --output experiments/high_temperature_hea_qwen35b/results/role_question_evaluation.json \
  --roles-jsonl experiments/high_temperature_hea_qwen35b/results/roles.jsonl \
  --questions-jsonl experiments/high_temperature_hea_qwen35b/results/questions.jsonl
```

Run the deterministic five-task agent:

```bash
mkdir -p /tmp/empty-legacy-outputs

.venv/bin/python adaptive_agent.py \
  "Develop a testable alloy-design hypothesis that improves high-temperature oxidation resistance and creep strength in high-entropy alloys above 1000 C while preserving phase stability." \
  /tmp/empty-legacy-outputs \
  experiments/high_temperature_hea_qwen35b/results/adaptive_trace.json \
  --max-depth 0 \
  --materials-evidence experiments/high_temperature_hea_qwen35b/outputs/materials_evidence
```

See [METHODS.md](METHODS.md) for selection rules, extraction safeguards, runtime details, metric
definitions, and limitations.
