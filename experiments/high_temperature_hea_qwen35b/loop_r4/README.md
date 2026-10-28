# Experiment 38: round 4, new signals for the decision and consensus synthesis

**Plan.** [loop.md](../../../loop.md) section 19 (19.1 failure analysis, offline checks and pre-registered plan).
**Code.**
- `m_synth` and its helpers at the end of [loop_methods.py](../../../loop_methods.py), tested in
  [test_synth.py](../../../test_synth.py).
- Offline checks: [round4_offline.py](../../../round4_offline.py), plus the local likelihood scorer
  [round4_pmi.py](../../../round4_pmi.py), which needs a V100-compatible PyTorch environment.

**Runner.** [loop/run_r4.sh](../loop/run_r4.sh). **Analysis.** [round4_analysis.py](../../../round4_analysis.py)
writes `analysis_r4.json` and `analysis_r4.md` here. **Progress.** `python web_status.py loop_r4`.

## 1. Thinking first: where the score is lost, and which ideas survive an offline check

All checks use existing runs, judgments and labels on the 45 spent papers ([offline/](./offline/)).

**Where the incumbent loses** (`decompose.json`).
- 60% of its hypotheses propose a different kind of intervention from the paper's.
- Only the right lever pays: 0.84 with the same lever, against 0.55 with a different kind.
- Its study types are miscalibrated: processing routes 7% (papers 22%), simulation studies 0% (11%).

**Ideas tested offline before anything was built.**

| Idea | Offline result | Built? |
|---|---|---|
| Base rates of study types in the earlier literature | The modal type of the most similar earlier papers matches the paper's in 28–29% of units; o3-mini's own choice in 38% | No |
| Likelihood selection with a local pre-cutoff model (Llama-3.2-3B): forward and backward (noisy-channel) PMI | Picks better candidates only between weak and strong configurations; among the strongest configurations' candidates it is worse than a random pick | No |
| State concrete test conditions | No effect within the same question (−0.06 [−0.19, +0.09]) | No |
| Mechanisms at the level of the problem | Mechanism credit when the lever is wrong is rare (15 of 163 runs) | No |
| A model fine-tuned on how earlier papers followed their introductions | Only 724 usable pre-2024 pairs, and the earlier literature predicts the study type worse than o3-mini | No (future work) |
| **Synthesis of several drafts** | Not testable offline | **Yes** |

## 2. The method: synthesis

Several independent drafts come from the incumbent's writer (WRITER_B). The drafts are shown in a shuffled order
with neutral labels and without model names. An o3-mini synthesis then writes one final hypothesis:
- it uses the intervention most drafts share, and never combines interventions;
- it keeps the conditions, mechanism, outcome, baseline and boundary that two or more drafts state;
- it drops specifics that only one draft states.

Sources: Mixture-of-Agents (https://arxiv.org/abs/2406.04692), the wisdom of the silicon crowd
(https://arxiv.org/abs/2402.19379) and universal self-consistency (https://arxiv.org/abs/2311.17311).

| Configuration | Drafts | Calls |
|---|---|---:|
| `synth_k4_b_o3mini` | 4 o3-mini drafts, closed-book | 5 |
| `synth_crowd_b_o3mini` | 5 drafts: o3-mini, o1, gpt-4o, gpt-4o-mini, Llama-3.3 (all 2023 cutoffs) | 6 |
| `synth_mixed_b_o3mini` | 2 closed-book and 2 with the best web method's evidence (64,000 characters of the question's date-filtered web corpus); the synthesis sees the same evidence | 5 |
| `synth_k1_b_o3mini` | 1 o3-mini draft (ablation: the rewrite alone) | 2 |
| `writer_only_b_o3mini_r5` | the incumbent with fresh samples (reference) | 1 |

Each runs on the 45 papers × 3 levels × 2 samples = 270 runs.

## 3. Results

Full tables: [analysis_r4.md](./analysis_r4.md). Statistics and interpretation: [loop.md](../../../loop.md) 19.2.
Exploratory, because all 45 papers are spent.

| Configuration | GPT-5.6 | DeepSeek | vs the incumbent (original + replicate: 0.631 / 0.568), GPT-5.6 [CI] |
|---|---:|---:|---|
| `synth_crowd_b_o3mini` | 0.645 | 0.542 | +0.01 [−0.02, +0.05] (DeepSeek −0.03) |
| `writer_only_b_o3mini_r5` (replicate) | 0.639 | 0.561 | – |
| `synth_mixed_b_o3mini` | 0.629 | 0.633 | −0.00 [−0.05, +0.04] (DeepSeek +0.07) |
| `writer_only_b_o3mini` (incumbent) | 0.623 | 0.575 | – |
| `synth_k4_b_o3mini` | 0.621 | 0.592 | −0.01 [−0.04, +0.02] (DeepSeek +0.02) |
| `synth_k1_b_o3mini` | 0.591 | 0.566 | −0.04 [−0.07, −0.01], Holm p 0.17 (DeepSeek −0.00) |

- **No synthesis beats the incumbent** with either judge.
- **The decision does not change.** The synthesis keeps the drafts' majority study type in 88–96% of runs, and the
  majority carries the drafts' shared bias, even across five different models. The lever matches in 18–23% of runs,
  against 19% for the incumbent.
- **Leakage: none detected.** All counters are zero, and 14,658 web-record reads were re-checked against each paper's
  date.

## Reproducing the offline checks

```bash
python round4_offline.py decompose
python round4_offline.py classify && python round4_offline.py baserate
python round4_offline.py pools && python round4_offline.py simpool
<v100-env>/bin/python round4_pmi.py offline/pmi_pool.jsonl offline/pmi_scores.jsonl      # GPU, Llama-3.2-3B
<v100-env>/bin/python round4_pmi.py offline/pmi_pool_sim.jsonl offline/pmi_scores.jsonl
python round4_offline.py pmi
```

The candidate pools (`offline/pmi_pool*.jsonl`) are regenerated deterministically by `pools` and `simpool` and are
not committed.
