# Question-centered evidence experiment

This experiment makes scientific question clusters the agent-facing knowledge representation.
Normalized v2 evidence remains behind the interface to ground and validate paper-specific answers.

## Why this experiment exists

The original roles and isolated reader questions did not reliably preserve the scientific links
needed for hypothesis generation: material and state, intervention, test condition, measured
outcome, proposed mechanism, and limitation. This experiment tests a different interface:

```text
canonical scientific question
  -> equivalent question variants from the literature
  -> paper-specific grounded answers
  -> condition-aware cross-paper synthesis
  -> candidate hypothesis and discriminating experiment
```

Questions organize retrieval, but they do not replace evidence. Every answer points to a normalized
v2 evidence unit and carries exact XML spans. Unsupported questions remain explicitly unresolved
instead of being converted into facts.

## Inputs

- `../temporal_v2/question_triage.json`: 8,848 reader questions generated from 50 papers.
- `../temporal_v2/materials_evidence_v2/`: 276 normalized, XML-grounded evidence units.
- `../temporal_v2/temporal_metadata.json`: exact publication dates and work-family identifiers.
- `../temporal_v2/benchmark_cases/`: 12 held-out temporal reconstruction cases.

## Pipeline

The automatic workflow:

1. resolves all 8,848 reader questions against temporally eligible grounded evidence;
2. attaches paper-specific answers with exact source spans;
3. extracts controlled scientific facets;
4. forms coarse domain/topic/property/regime groups;
5. splits coarse groups using scientific-compatibility adjudication;
6. synthesizes agreements, different approaches, condition dependencies, contradictions, gaps,
   hypotheses, and discriminating experiments;
7. builds browser-review data;
8. runs five question-centered temporal ablations over the existing 12 held-out cases; and
9. audits temporal eligibility, test-paper exclusion, work-family exclusion, and citations.

Qwen3.5-35B-A3B Q4_K_M performs resolution, compatibility adjudication, synthesis, hypothesis
generation, and model-based scoring. Hidden thinking is disabled. Resolution is processed in
six-question batches; compatibility adjudication is bounded to 30 questions per model call; and
synthesis sees a diverse sample of at most 24 answers while the persisted cluster retains every
answer.

## Final corpus results

| Measure | Result |
|---|---:|
| Papers | 50 |
| Reader questions | 8,848 |
| Grounded answers | 7,664 |
| Rejected question records | 3 |
| Coarse facet groups | 402 |
| Final compatibility clusters | 3,529 |
| Multi-paper clusters | 708 |
| Scientifically coherent clusters | 3,526 |
| Mean questions per cluster | 2.5072 |
| Mean answers per cluster | 2.1717 |

Resolution status counts are:

- 1,455 answered in the same paper;
- 1 answered from the eligible earlier corpus;
- 2,385 partially answered;
- 4,764 unresolved;
- 183 reading-only; and
- 60 replication-detail questions.

The answer count is larger than the number of answered questions because a question can have more
than one grounded paper-specific answer. The 4,764 unresolved questions are useful as candidate
knowledge gaps, but must not be presented to the hypothesis agent as established evidence.

Structural validation found zero missing, duplicate, or unknown question assignments; zero invalid
cluster-answer references; zero invalid synthesis-answer references; and zero cluster count
mismatches. All 7,664 answers reference one of the 276 validated v2 evidence units and use exact
stored evidence spans.

## Temporal benchmark

Each of the 12 held-out papers is evaluated with three query-specificity levels and five knowledge
representations, giving 180 runs:

1. `raw_questions`: eligible ungrouped question text only;
2. `grouped_questions`: canonical clusters and question variants, without answers;
3. `grouped_answers`: clusters plus grounded paper-specific answers;
4. `grouped_synthesis`: grouped answers plus synthesis regenerated after temporal filtering; and
5. `grouped_answers_v2`: grouped answers plus normalized v2 evidence.

Mean model-based scores use a five-point scale:

| Variant | Intervention | Mechanism | Outcome | Conditions | Evidence validity | Novelty | Unsupported |
|---|---:|---:|---:|---:|---:|---:|---:|
| Raw questions | 1.9444 | 1.8333 | 1.7778 | 1.9722 | 2.5278 | 2.5833 | 9 |
| Grouped questions | 1.6667 | 1.8056 | 1.8889 | 1.8611 | 2.6667 | 2.4722 | 9 |
| Grouped answers | 1.7500 | 1.7222 | 1.7222 | 1.9167 | 2.2778 | 2.4444 | 8 |
| Grouped synthesis | 1.6667 | 1.6111 | 1.6111 | 1.6944 | 2.5556 | 2.3611 | 7 |
| Grouped answers + v2 | 1.8611 | 1.6667 | 1.8333 | 1.8611 | **2.7500** | **2.5833** | 11 |

Raw questions achieved the strongest mean intervention, mechanism, and condition reconstruction.
Grouping alone did not improve reconstruction. Synthesis produced the fewest unsupported outputs,
but also reduced several reconstruction scores. Adding v2 evidence gave the strongest evidence
validity and tied the best novelty score, while producing more unsupported classifications.

Therefore, this experiment does **not** support using questions as the agent's only scientific
evidence. Questions are useful as a retrieval and comparison index. The most defensible next
architecture keeps grounded v2 evidence as the factual substrate and uses question clusters to
organize cross-paper contrasts, expose unresolved gaps, and select evidence relevant to the query.

The integrity audit verified all 180 expected runs with zero future-evidence violations, zero
held-out-paper leaks, zero same-work-family leaks, and zero invalid generated citations.

## Output layout

```text
question_centered/
├── resolved_questions/    # one file per paper plus summary.json
├── clusters/              # one file per final cluster plus summary.json
├── benchmark_runs/        # 180 run files plus aggregate summary.json
├── results/
│   ├── question_evaluation.json
│   └── integrity_audit.json
├── review_manifest.json   # lightweight index used by the review UI
├── status.json
└── COMPLETE
```

Runtime logs, resolver checkpoints, adjudication caches, temporal synthesis caches, PID files, and
server-health files are intentionally excluded from version control.

## Reproduce the workflow

Run detached:

```bash
tmux new-session -d -s mathg-question-centered \
  "cd $(pwd) && bash run_question_centered_experiments.sh"
```

Monitor:

```bash
cat experiments/high_temperature_hea_qwen35b/question_centered/status.json
tail -f experiments/high_temperature_hea_qwen35b/question_centered/logs/pipeline.log
tmux attach -t mathg-question-centered
```

After clusters exist, launch the review interface:

```bash
.venv/bin/python question_review_server.py --host 0.0.0.0 --port 8875
```

The experiment is complete only when `COMPLETE` exists and `status.json` reports
`"state": "complete"`.

## Review the clusters

The review interface shows the canonical question, variants, scientific facets, paper-specific
answers, conditions, exact source spans, and cross-paper synthesis:

```bash
.venv/bin/python question_review_server.py --host 0.0.0.0 --port 8875
```

Then open `http://localhost:8875`.

## Limitations

- Qwen3.5-35B-A3B has no documented public knowledge-cutoff date. These results are retrospective
  temporal reconstruction, not a strict demonstration of unseen-future prediction.
- Hypothesis quality scores are model-based and require materials-expert review.
- Citation validity proves that an identifier was retrieved, not that every generated inference is
  scientifically entailed by the cited evidence.
- Question resolution and compatibility adjudication are model decisions, although evidence spans
  and identifier containment are validated deterministically.
- The corpus contains only 50 open-access primary papers, so unresolved status can mean either a
  genuine research gap or missing coverage in this corpus.
