# Critique-augmented hypothesis revision (eval_critique)

> **Caveat (added 2026-10-23, experiment 19).** The benchmark queries used here leak the held-out answer: 8% of the answer's words appear in broad queries, 20% in problem_constrained and 47% in expert_context, and per-unit overlap correlates 0.77–0.86 with judge scores. Paired comparisons between methods on the same query remain fair. Absolute scores, differences between query levels and conclusions about query inferability or evidence use are confounded. See [query_leakage/README.md](../query_leakage/README.md). All evaluations were rerun on leak-free queries with a pre-cutoff generator: scores fell from about 1.5 to about 0.5 and the level gradient disappeared. See [rerun_v3/README.md](../rerun_v3/README.md).


**Question.** Does a panel of critic LLMs, each checking one aspect of a tool-agent hypothesis against the
evidence the agent read, improve the hypothesis when a reviser rewrites it? The comparison is against the
unrevised baseline, against a self-revise control (same reviser, no critiques), and against a fresh baseline
sample that measures run-to-run noise.

**Status (2026-10-22):** complete and verified. All four arms have 36 judged units. The result is negative:
critique lowered the reconstruction score (1.64 → 1.49), and the drop is not statistically significant after
correction.

## Design

```
eval_v3 tool-agent run (generation, cited evidence, trace)        ← baseline "original"
  ├─ trace analyser (deterministic)
  ├─ critique arm:  3 critics in sequence → reviser (review_mode=critique) → revised hypothesis
  └─ self_revise:   reviser (review_mode=self, no critics)         → revised hypothesis
Both revised arms → blinded GPT-5.6 absolute judge (same as v3)
Fresh tool-agent sample (baseline_resample) → same judge            ← run-to-run noise
```

The critique and self-revise arms revise the **same** baseline generation, so each comparison is paired
on the same paper-by-query unit.

### Critics (roles run in sequence)

| Role | Model (TRAPI deployment) | Checks |
|---|---|---|
| evidence | Llama 3.3 70B Instruct (`Llama-3.3-70B-Instruct_5`) | Each supporting claim is backed by the text of the record it cites |
| consistency | OpenAI o1 (`o1_2024-12-17`) | Arithmetic, composition, direction of property changes, phase plausibility |
| falsifiability | GPT-4o (`gpt-4o_2024-11-20`) | Whether the experiment is concrete and testable, and whether the boundary and uncertainty are specific |

Critics output findings with a type (unsupported, miscited, inconsistent, implausible, untestable, other),
a severity from 1 to 3, the evidence labels they relied on, and a suggested fix. They do not write a
hypothesis. At most 8 findings per critic.

### Reviser

Llama 3.3 70B Instruct (`Llama-3.3-70B-Instruct_5`) rewrites the hypothesis with the same 14 fields. Citations
must be record IDs the agent read (validated as in v3). One repair attempt follows any invalid citation.
If the repair also fails, the original hypothesis is kept, and this is recorded as `fallback_original`.
In this run no unit needed a fallback.

## Model choice and knowledge cutoffs

The held-out papers were published between **2024-01-02 and 2026-02-16**. A critic or reviser whose
training data includes those papers could recognise them and steer the revision toward the true answer.
So every critic and the reviser must have a knowledge cutoff **before 2024-01-02**. This is checked at
run time, and the check is also tested.

| Model | Deployment (TRAPI) | Knowledge cutoff | Source | Used |
|---|---|---|---|---|
| Llama 3.3 70B Instruct | `Llama-3.3-70B-Instruct_5` | December 2023 | Meta model card (github.com/meta-llama/llama-models, llama3_3) | Evidence critic, reviser |
| OpenAI o1 | `o1_2024-12-17` | Oct 1, 2023 | developers.openai.com/api/docs/models/o1 | Consistency critic |
| GPT-4o | `gpt-4o_2024-11-20` | Oct 1, 2023 | developers.openai.com/api/docs/models/gpt-4o | Falsifiability critic |
| GPT-OSS-120B | `gpt-oss-120b_1` | June 2024 | Web search summary; official page not fetched | Excluded (after cutoff) |
| Mistral Large 3 | `Mistral-Large-3_1` | October 2024 | third-party listing | Excluded (after cutoff) |
| DeepSeek-V3.2 | `DeepSeek-V3.2_1` | May 2025 | third-party listing | Excluded (after cutoff) |

The other deployments on the list (GPT-4.1, GPT-5 family, GPT-5.x, GPT-6 family, Qwen3.5, Kimi, Grok, DeepSeek-V4)
were not checked individually. They were not used, because they are later models whose cutoffs were not
confirmed from the sources consulted. Before any of them is used, its cutoff needs checking on the official page.
The GPT-OSS-120B, Mistral Large 3 and DeepSeek-V3.2 dates come from a web search summary and third-party listings,
not from official pages. Each is after 2024-01-02 according to those sources, so the exclusion stands unless an
official page shows otherwise.

**Family independence.** The reviser (Llama) is outside the OpenAI family used by the judge, and the evidence
critic is also non-OpenAI. Two critics (o1, GPT-4o) share a family with the GPT-5.6 judge. That could bias
judging toward their wording, so treat the judge's scores with that in mind.

**Knowledge cutoff caveat.** The cutoffs above are developers' stated training-data cutoffs. A cutoff
rules out training on post-cutoff papers, but it does not prove the model has no other knowledge of the
held-out papers. The judge (GPT-5.6) was not changed and is not subject to this rule, because it compares
against the hidden target by design.

## Leakage controls

1. **Hidden target is never sent.** Critic and reviser payloads have a fixed key set (query, knowledge
   cutoff, hypothesis, evidence, critiques, review mode). `assert_payload` rejects any other key and any
   payload containing the string `hidden_target`. Both checks run on every call, and tests cover them.
2. **No held-out or same-family records.** Before any critic runs, `assert_no_target_records` rejects a run
   whose read records include the held-out paper or a paper from its work family. The check found no such
   records (`payload_target_family_records: 0`).
3. **Blinding for critics.** Records are shown as E1, E2, … and their real IDs are not shown. Critic
   findings are mapped back to real record IDs for the reviser. The reviser sees real IDs, so its citations
   can be validated.
4. **Model cutoffs before the earliest held-out date.** Checked at run time (`check_model_cutoffs`) and in
   tests. The run would fail if any model's cutoff were not before 2024-01-02.
5. **Judge stays blinded and separate.** The judge sees the revised hypothesis under the same blinding as v3.

Integrity (see [results/integrity_critique.json](results/integrity_critique.json)): 36 judged units per arm,
0 judge errors, 0 incomplete critic sets, 0 invalid revised citations, 0 hidden-target sends, 0
target-family records in payloads.

## Results

Primary metric: reconstruction mean (intervention, condition, mechanism, outcome; 0 to 4). Units are 12
papers × 3 queries = 36. Intervals use a paper-clustered bootstrap (10,000 resamples, seed 20260421).
Holm correction spans the three primary comparisons.

| Arm | Units | Reconstruction | Overall (10 dims) |
|---|---:|---:|---:|
| original (eval_v3 tool agent) | 36 | **1.64** | 1.84 |
| resample (fresh tool-agent sample, noise check) | 36 | 1.55 | 1.82 |
| critique (3 critics + revision) | 36 | 1.49 | 1.64 |
| self_revise (revision only) | 36 | 1.60 | 1.79 |

| Comparison | Mean difference | 95% CI (papers bootstrap) | Papers A higher / B higher | Sign-test p | Holm p |
|---|---:|---|---:|---:|---:|
| critique − original | −0.15 | −0.36 to +0.03 | 2 / 8 | 0.11 | 0.33 |
| self_revise − original | −0.04 | −0.10 to +0.02 | 3 / 7 | 0.34 | 0.69 |
| critique − self_revise | −0.11 | −0.31 to +0.07 | 4 / 7 | 0.55 | 0.69 |
| resample − original (noise) | −0.09 | −0.19 to +0.01 | 2 / 8 | 0.11 | n/a |

Classifications (judge): original has 1 exact reconstruction, 20 partial, 6 plausible alternative, 9
unsupported. Critique has 0 exact, 16 partial, 7 plausible alternative, 13 unsupported.

### Where the drop comes from

Mean score by dimension, original vs critique revision (0 to 4):

| Dimension | Original | Critique | Change |
|---|---:|---:|---:|
| problem alignment | 3.19 | 2.89 | −0.31 |
| intervention reconstruction | 1.83 | 1.83 | 0.00 |
| condition agreement | 1.36 | 1.36 | 0.00 |
| mechanism agreement | 1.67 | 1.39 | −0.28 |
| outcome agreement | 1.69 | 1.36 | −0.33 |
| baseline quality | 1.97 | 1.89 | −0.08 |
| boundary quality | 1.58 | 1.31 | −0.28 |
| experiment discriminability | 2.25 | 1.89 | −0.36 |
| evidence validity | 0.92 | 1.00 | +0.08 |
| novelty | 1.97 | 1.47 | −0.50 |

Hedging, counted in the hypothesis plus predicted outcome (words such as may, might, potentially,
uncertain, likely): **0.14 per hypothesis originally, 3.33 after critique**. Hypotheses also got longer
(728 → 807 characters on average). The critics mostly flagged untestable claims (93 findings) and
unsupported claims (111).

### Revision behaviour

| Arm | Records | Status | Findings | Citation set changed |
|---|---:|---|---|---:|
| critique | 36 | ok 36 | unsupported 111, untestable 93, miscited 42, inconsistent 26, implausible 24, other 10 | 14 |
| self_revise | 36 | ok 36 | not applicable | 7 |

The trace analyser found the same tool-use behaviour as in v3: the agent used its full 12-call budget
in every run.

## Interpretation

- **Critique as implemented hurts reconstruction.** The critique arm is the lowest in the comparison, and the
  drop is larger than the baseline run-to-run noise (0.15 against 0.09). It is still not significant after
  correction, because 36 units are few.
- **The mechanism is hedging.** Critics ask for quantitative boundaries and testable thresholds. The
  reviser answers by adding uncertainty language and softening claims. The judge then scores the hypothesis
  as less specific: novelty, experiment discriminability, outcome agreement and boundary quality all drop.
  The intervention and condition dimensions, which depend on the actual design choice, do not move at all.
- **Critique has no clear accuracy benefit.** Evidence validity rises slightly (+0.08), which is within noise.
  The critics raise real problems (miscited and unsupported claims), but the reviser fixes them by weakening
  the hypothesis rather than correcting it.
- **The self-revise control also loses a little**, but less than critique (−0.04 against −0.15), and its
  novelty loss is smaller (−0.19 against −0.50). So part of the drop is a general revision effect, and most of
  it is specific to the critique prompts.

### Suggested next steps (not run)

1. **Tell the reviser not to hedge.** Add an explicit rule: keep specific claims when the evidence supports
   them, and state uncertainty in the `uncertainty` field only, not in the hypothesis or outcome. Re-run
   this same design.
2. **Turn critiques into specific repairs.** Ask for a replacement value or condition for each flagged
   claim, not a general edit.
3. **Score for specificity separately.** Add a judge check for hedge density so that softening cannot pass as
   improvement.
4. **Rerun the noise check with more papers** before attributing any effect below about 0.1.

## Limitations

- 12 papers and 36 units. Confidence intervals are wide, and no comparison is significant after correction.
- The judge is GPT-5.6, which is uncalibrated against human experts and shares a family with two critics.
- The reviser is a 70B open model. A stronger reviser might behave differently; this design does not test that.
- The generator (Qwen3.5-35B-A3B) has an undocumented training cutoff, so the baseline cannot be guaranteed
  free of memorised held-out content. The closed-book baseline in eval_v3 is the probe for that.
- The evidence critic's output cap was raised from 3,000 to 6,000 tokens after one unit was truncated. That
  unit was rerun with the new cap. The other 71 units ran with 3,000, and their outputs were complete.
  The o1 consistency critic has a 12,000-token cap because reasoning tokens count against the output limit.

## Reproduce

```bash
# Baseline resample, critiques and self-revise, judging and analysis (tmux, resumable)
tmux new-session -d -s mathg-eval-critique -c "$PWD" 'bash run_eval_critique.sh; exec bash'

# Unit tests for the leakage guards, critic logic and TRAPI call
.venv/bin/python -m unittest test_temporal_eval_critique.py
```

Outputs: `baseline_resample/` (fresh tool-agent runs and judgments), `revisions/{critique,self_revise}/`
(critic findings, trace analysis, revised hypotheses, payload audit), `judgments/{critique,self_revise}/`,
`results/analysis_critique.json`, `results/integrity_critique.json`, `results/summary_critique.md`.
