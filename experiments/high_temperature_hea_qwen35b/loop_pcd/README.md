# Experiment 37: propose, critique, decide

**Plan.** [loop.md](../../../loop.md) section 18: 18.1 pre-registration, 18.2 amendment before any run.
**Code.** `m_pcd` and its helpers at the end of [loop_methods.py](../../../loop_methods.py), tested in
[test_pcd.py](../../../test_pcd.py).
**Runner.** [loop/run_pcd.sh](../loop/run_pcd.sh), with extra evaluation loops in
[run_pcd_judges.sh](../loop/run_pcd_judges.sh), [run_pcd_audits.sh](../loop/run_pcd_audits.sh) and
[run_pcd_labels.sh](../loop/run_pcd_labels.sh). **Analysis.** [pcd_analysis.py](../../../pcd_analysis.py) writes
[analysis_pcd.json](./analysis_pcd.json) and [analysis_pcd.md](./analysis_pcd.md) here. **Progress.**
`python web_status.py loop_pcd`.

## The method

Three agent roles answer each research question:

1. **Proposer.** Four candidate directions, each using a different lever or mechanism. Each gives the material
   system, intervention with parameters, conditions, structural change, mechanism, predicted outcome, and why it
   addresses the question's limitation.
2. **Critic.** Reviews every direction against six fixed criteria:
   - does it address the stated limitation;
   - does it respect the constraints;
   - is the mechanism physically sound;
   - is it feasible;
   - what does the evidence say;
   - what is the main risk.

   Each direction gets a verdict (strong, viable with changes, weak) and one fix.
3. **Decider.** Sees the directions and critiques in a shuffled order with neutral labels. It adopts one direction,
   adopts it with a fix, or merges compatible ones, then writes the final hypothesis with the incumbent's
   conservative-writer instruction.

**Web evidence (optional per role).** It comes from the question's experiment-36 web corpus
([websearch/](../websearch/README.md)); every record is dated before the paper.
- **Proposer:** the 10 most relevant paper cards (title, abstract, conclusions), ≤ 16,000 characters.
- **Critic and decider:** passages retrieved with each proposed idea's own text (HyDE-style), an equal share of
  16,000 characters per idea. The decider may cite only these.

## Configurations (270 runs each: 45 papers × 3 levels × 2 samples)

| Group | Configurations | Question |
|---|---|---|
| Web grid | `pcd_{none,P,C,D,PC,PD,CD,PCD}_o3mini` | Which roles benefit from web evidence (P proposer, C critic, D decider) |
| No critic | `pcd_nocritic_{none,PCD}_o3mini` | Does critique help the decision |
| No decider | `pcd_nodecider_{none,PCD}_o3mini` | Does an agent decide better than a rule (the best verdict wins) |
| One idea | `pcd_k1_{none,PCD}_o3mini` | Does breadth (4 ideas) help |
| Llama-3.3 | `pcd_{none,PCD}_llama` | Does the framework help the weaker baseline model |

The baselines are the existing runs of `closed_book`, `closed_book_o3mini`, `writer_only_b_o3mini`,
`web_text_chunks(_b_o3mini)`, `web_agent(_o3mini)` and `web_text_64k_b_o3mini`, all on the same 45 papers.

## Results

Full tables: [analysis_pcd.md](./analysis_pcd.md). Statistics and interpretation: [loop.md](../../../loop.md) 18.3.
Exploratory, because all 45 papers are spent.

| Configuration | GPT-5.6 | DeepSeek | vs `writer_only_b_o3mini` (0.62 / 0.58), GPT-5.6 [CI] |
|---|---:|---:|---|
| Full system, web at every role (`pcd_PCD_o3mini`) | 0.50 | 0.36 | −0.12 [−0.17, −0.07], Holm p 0.003 (DeepSeek −0.21) |
| No web (`pcd_none_o3mini`) | 0.47 | 0.35 | −0.15 [−0.21, −0.10], Holm p < 0.001 (DeepSeek −0.23) |
| Best of the 16: one idea, no web (`pcd_k1_none_o3mini`) | 0.53 | 0.43 | – |
| Llama-3.3 in every role, no web / full web | 0.42 / 0.40 | 0.20 / 0.24 | Llama closed-book: 0.50 / 0.31 |

- **Worse than one call.** The three-role system is worse than one o3-mini call, with or without web evidence, with
  both judges. It is no better than the Llama-3.3 closed-book baseline.
- **Web evidence.** It helps only the decider: +0.03 [+0.01, +0.05], not significant after Holm.
- **Each agent.** The critic adds nothing, the decider is no better than "the best verdict wins", and four ideas are
  no better than one.
- **Coverage and selection.**
  - At least one of the four ideas matches the paper's lever in 37–40% of runs, but the final hypothesis matches in
    only 15%.
  - When an idea matches, the decider picks one at chance level, and the critic rates matching ideas like the others.
- **Where the score is lost.** Mostly the intervention: 0.08–0.12 vs 0.32 with GPT-5.6. The hypotheses are more novel
  and more specific, not more hedged.
- **Leakage: none detected.** All counters are zero, and 60,141 web-record reads were re-checked against each paper's
  date.
