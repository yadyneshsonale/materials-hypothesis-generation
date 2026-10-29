# Experiment 40: an agent that chooses its approach from the evidence

**Plan.** [loop.md](../../../loop.md) section 21 (21.1 offline checks and pre-registered plan). **Code.**
- The agent (`m_agent`, `GROUP_SYSTEM`, `choose_group`, `focused_pack`) at the end of
  [loop_methods.py](../../../loop_methods.py), tested in [test_agent.py](../../../test_agent.py).
- Offline checks: [agent_offline.py](../../../agent_offline.py).
- Analysis: [agent_analysis.py](../../../agent_analysis.py).

**Runner.** [loop/run_agent.sh](../loop/run_agent.sh). **Report.** `analysis_agent.md` and `analysis_agent.json`.
**Progress.** `python web_status.py loop_agent`.

## Why this agent

Experiment 39 ([loop_diag/](../loop_diag/README.md)) found two things the agent can change:
- **The decision.** The model copies details from the evidence but keeps its own choice of approach, which matches
  the paper's lever in only 19% of hypotheses. When the paper's approach is given, it uses it 93% of the time, and
  the score doubles.
- **The selection.** The paper's approach is in most evidence packs, but diluted (16–18% of passages). Evidence
  concentrated on it raised the score by +0.13.

**Offline checks** ([offline/](./offline/); target-aware analysis of existing runs only):
- **Re-ranking the evidence:** small gain. The best re-ranking (the model's own draft as the query) raises the share
  of passages carrying the paper's lever from 17% to 21%.
- **Choosing the approach from the evidence:** large gain. o3-mini groups the 64,000-character pack's passages by
  approach and rates how directly each addresses the question's limitation. The most direct group matches the
  paper's lever in 35.6% of questions, against 24.8% for a random group and 18.9% for the model's own choice.

## The agent (`agent_choose_ground_b_o3mini`)

1. Retrieve the question's 64,000-character pack from its date-filtered web corpus.
2. **Choose.** o3-mini groups the passages by approach and rates each group's directness. Code takes the most
   direct group, then the one with more papers, then more passages.
3. **Focus.** Build a 16,000-character pack: the chosen group's passages, then the corpus passages most similar
   (BM25) to the chosen approach and the question.
4. **Write.** The best method's conservative writer writes the hypothesis on the chosen approach, with the focused
   evidence.

It is target-free, makes 2 calls, and every evidence record is dated before the paper.

## The 2 × 2 design (270 runs each: 45 papers × 3 levels × 2 samples)

| Approach chosen by | No evidence for writing | Focused evidence for writing |
|---|---|---|
| The model | `writer_only_b_o3mini` (existing) | `agent_draft_ground_b_o3mini` |
| The evidence | `agent_choose_only_b_o3mini` | `agent_choose_ground_b_o3mini` (the agent) |

**Baselines.** `writer_only_b_o3mini` and `web_text_64k_b_o3mini`. GPT-5.6 judges them again in the same session
(must_obey.md 6.10). Quality is also judged without the answer key (must_obey.md 6.11).

## Results

Full tables: [analysis_agent.md](./analysis_agent.md). Statistics and interpretation:
[loop.md](../../../loop.md) 21.2. Exploratory, because all 45 papers are spent.

| Configuration | GPT-5.6 | DeepSeek | Matches the paper's lever | Unsupported |
|---|---:|---:|---:|---:|
| `writer_only_b_o3mini` (closed-book, re-judged in the same session) | 0.621 | 0.575 | 19% | 73% |
| `web_text_64k_b_o3mini` (64,000 characters of web evidence, re-judged) | 0.620 | 0.656 | 21% | 47% |
| `agent_choose_ground_b_o3mini` (the new agent) | 0.584 | 0.569 | 19% | 41% |
| `agent_choose_only_b_o3mini` | 0.583 | 0.468 | 19% | 80% |
| `agent_draft_ground_b_o3mini` | 0.567 | 0.549 | 15% | 57% |

- **The pre-registered rule is not met.** The agent does not raise reconstruction: −0.04 [−0.10, +0.03] against the
  writer.
- **The approach still matches the paper in only 19% of runs.** The offline estimate of 35.6% used lenient passage
  labels, the chosen groups are often topics rather than levers, and the writer adopts them only partly.
- **Quality, without the answer key.** All three judges (GPT-5.6, DeepSeek, o1) prefer the agent's hypotheses to the
  closed-book writer's (+0.19 to +0.29). o1 and DeepSeek prefer the simpler 64,000-character writer to the agent.
- **The best agent overall is `web_text_64k_b_o3mini`.** It ties the closed-book writer on reconstruction and is
  clearly preferred on quality.
- **Leakage: none detected.**
