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

### Eleven-role and high-recall reader-question extraction

A second pass retained the original 11-role representation while applying stricter role semantics,
exact source grounding, and a new definition of a useful question.

| Metric | Result |
| --- | ---: |
| Papers with role/question output | 50/50 |
| Reconciled role claims | 1,271 |
| Grounded reader questions | 8,848 |
| Invalid persisted items | 0 |
| Mean questions per paper | 176.96 |
| Median questions per paper | 168.5 |
| Questions per paper, minimum–maximum | 79–314 |
| Mean question confidence | 0.8440 |
| Exact grounding rate | 100% |
| Papers with no grounded question | 0 |
| Rejected model candidates | 1,914 |

A **reader question** captures a useful thought that may arise while reading: what a term means,
what method or material is being used, why a choice was made, how a mechanism works, whether the
evidence is sufficient, whether the result is relevant elsewhere, what would happen if a variable
changed, where the result fails, or what experiment should follow. Every accepted question records
its type, reading step, intent, relevance tier, rationale, exact source passage, and confidence.

The high-recall pass generated 1,858 clarification, 1,493 method, 1,411 mechanism, 890 rationale,
669 counterfactual, 625 comparison, 602 assumption, 527 evidence, 315 boundary, 134 follow-up,
130 limitation, 112 relevance, 63 replication, and 19 transfer questions. The earlier set of 81
strict decision questions is preserved in `results/decision_questions.jsonl`.

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
│       └── text/                 # 50 structure-preserving pipeline inputs
├── materials_evidence/           # linked evidence, one JSON record per paper
├── outputs/
│   └── papers/                   # one organized folder per research paper
│       └── <PMCID>/
│           ├── input/            # JATS XML and visual-only PDF
│           └── output/           # roles, questions, and rejected candidates
├── results/
│   ├── corpus_evaluation.json
│   ├── adaptive_trace.json
│   ├── role_question_evaluation.json
│   ├── reader_question_evaluation.json
│   ├── roles.jsonl               # 1,271 consolidated grounded role claims
│   ├── decision_questions.jsonl  # original 81 strict decision questions
│   └── questions.jsonl           # 8,848 grounded reader questions
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
  --out-dir experiments/high_temperature_hea_qwen35b/materials_evidence \
  --workers 4 --resume
```

The four-worker run completed 48 papers. Two requests exceeded the 120-second HTTP timeout under
contention and were completed with the same command using `--workers 1 --resume`.

Evaluate the persisted outputs:

```bash
.venv/bin/python evaluate_materials_corpus.py \
  --evidence-dir experiments/high_temperature_hea_qwen35b/materials_evidence \
  --source-dir experiments/high_temperature_hea_qwen35b/data/corpus/text \
  --output experiments/high_temperature_hea_qwen35b/results/corpus_evaluation.json
```

Extract the 11 roles and strict decision questions:

```bash
.venv/bin/python role_question_extract.py \
  --input-dir experiments/high_temperature_hea_qwen35b/data/corpus/text \
  --out-dir /tmp/role_questions \
  --workers 4 --resume
```

Arrange the output, retrieve checksum-verified PMC OA PDFs, and split roles from questions:

```bash
.venv/bin/python arrange_paper_outputs.py \
  --corpus-dir experiments/high_temperature_hea_qwen35b/data/corpus \
  --role-dir /tmp/role_questions \
  --papers-dir experiments/high_temperature_hea_qwen35b/outputs/papers \
  --workers 6
```

Generate high-recall reader questions using the existing reconciled roles:

```bash
.venv/bin/python reader_question_generate.py \
  --input-dir experiments/high_temperature_hea_qwen35b/data/corpus/text \
  --papers-dir experiments/high_temperature_hea_qwen35b/outputs/papers \
  --out-dir /tmp/reader-questions \
  --checkpoint-dir /tmp/reader-question-checkpoints \
  --workers 4 --resume --install
```

The PDF in each paper's `input/` directory is **only for visual inspection**. The pipeline does
not parse or use it. The JATS XML is the machine-readable source.

Review the PDF and generated evidence side by side:

```bash
.venv/bin/python review_interface_server.py --host 0.0.0.0
```

Then open `http://127.0.0.1:8765` in a local browser. For the VS Code integrated browser, use
`http://<machine-ip>:8765` because its loopback interface is isolated. The interface provides:

## Temporal hypothesis-reconstruction v2

The v2 experiment preserves all existing outputs and writes new artifacts under
`temporal_v2/`. It tests whether an agent can reconstruct a held-out paper's hypothesis using
only papers available before the held-out paper's earliest public date.

The public Qwen3.5-35B-A3B documentation does not state a precise training-data cutoff. Therefore,
the experiment does not call pre-cutoff papers unseen. It records those cases as retrospective
temporal reconstructions and permits a strict unseen claim only if a documented model cutoff is
later supplied and the test paper postdates it.

The automatic workflow performs:

1. exact JATS publication-date and work-family audit;
2. conservative triage of the 8,848 reader questions;
3. resumable normalized v2 evidence extraction;
4. exact-grounding and schema evaluation;
5. leakage-safe broad, constrained, and expert-context query construction;
6. chronological train/validation/test case construction;
7. roles-only, v1-evidence, v2-evidence, and v2-plus-role/question ablations;
8. structured reconstruction, evidence, boundary, and falsification scoring.

Run it in a detached tmux session:

```bash
tmux new-session -d -s mathg-temporal-v2 \
  "cd $(pwd) && bash run_temporal_v2_experiments.sh"
```

The runner starts and health-checks the local Qwen server itself. It is restart-safe: completed
papers, cases, and experiment runs are skipped. Monitor it with:

```bash
cat experiments/high_temperature_hea_qwen35b/temporal_v2/status.json
tail -f experiments/high_temperature_hea_qwen35b/temporal_v2/logs/pipeline.log
tmux attach -t mathg-temporal-v2
```

Closing VS Code does not stop a detached tmux session. The run is complete only when
`temporal_v2/COMPLETE` exists and `status.json` reports `state: complete`.

## Question-centered evidence experiment

The next experiment uses questions as the only agent-facing knowledge representation. It resolves
each question into separately grounded paper answers, forms condition-aware scientific topic
clusters, and shows how different papers approach the same question. Normalized v2 evidence is
retained behind the interface for provenance and answer validation.

The five temporal ablations compare:

1. raw questions;
2. grouped questions without answers;
3. grouped questions with paper-specific grounded answers;
4. grouped questions with temporally filtered cross-paper synthesis; and
5. grouped answers plus exposed v2 evidence.

Run the complete workflow in tmux:

```bash
tmux new-session -d -s mathg-question-centered \
  "cd $(pwd) && bash run_question_centered_experiments.sh"
```

See `question_centered/README.md` for output contracts, monitoring, and the browser review command.

- a ranked 50-paper selector;
- a visual-only rendered PDF pane with page and zoom controls;
- count-labelled multi-select role filters and reader-question cards;
- question search plus type, intent, and relevance filters;
- exact XML-derived evidence chunks with the selected span highlighted; and
- navigation to the corresponding PDF page with coordinate-level passage highlights.

Chunk highlighting is exact because it uses the XML-derived pipeline source. The review server
reads the PDF text layer only to align visual highlight rectangles; pipeline extraction and exact
grounding continue to use JATS XML-derived text exclusively. PDF matching remains best-effort
because publisher text layers can differ in spacing, formulas, and reading order. Guarded
ordered-token alignment handles citation-format differences and evidence spanning two PDF pages.

For temporary international sharing, expose the running server through an HTTPS Quick Tunnel:

```bash
cloudflared tunnel --url http://127.0.0.1:8765 --no-autoupdate
```

The generated `https://*.trycloudflare.com` URL works while both processes remain running and has
no uptime guarantee. A permanent deployment requires a named tunnel or another managed host.

Validate and consolidate the organized role/question outputs:

```bash
.venv/bin/python evaluate_role_questions.py \
  --evidence-dir experiments/high_temperature_hea_qwen35b/outputs/papers \
  --source-dir experiments/high_temperature_hea_qwen35b/data/corpus/text \
  --output experiments/high_temperature_hea_qwen35b/results/role_question_evaluation.json \
  --roles-jsonl experiments/high_temperature_hea_qwen35b/results/roles.jsonl \
  --questions-jsonl experiments/high_temperature_hea_qwen35b/results/decision_questions.jsonl
```

Validate and consolidate the high-recall questions:

```bash
.venv/bin/python evaluate_reader_questions.py \
  --question-dir experiments/high_temperature_hea_qwen35b/outputs/papers \
  --source-dir experiments/high_temperature_hea_qwen35b/data/corpus/text \
  --output experiments/high_temperature_hea_qwen35b/results/reader_question_evaluation.json \
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
  --materials-evidence experiments/high_temperature_hea_qwen35b/materials_evidence
```

See [METHODS.md](METHODS.md) for selection rules, extraction safeguards, runtime details, metric
definitions, and limitations.
