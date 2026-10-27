# review_eval: experiments 33–35 (changes suggested by two model reviews)

**Plan.** [loop.md](../../../loop.md) section 16.1, pre-registered. Results are in sections 16.2–16.5.

**Scripts.**
- [review_measurement.py](../../../review_measurement.py): measurement checks;
- [checklist_judge.py](../../../checklist_judge.py): checklist judge;
- [review_probe.py](../../../review_probe.py): memorisation probe;
- [review_analysis.py](../../../review_analysis.py): Phase B and test4 analysis;
- [answer_render.py](../../../answer_render.py): renders an answer key into the hypothesis schema;
- tests in [test_review.py](../../../test_review.py).

| Path | What |
|---|---|
| `output_audit.json` | A1: format failures, abstentions, repairs and truncations per run directory (10,896 runs) |
| `controls/items/`, `controls/judgments/{gpt56,deepseek}/` | A3: 216 sanity controls built by code from the answer keys, and both judges' scores |
| `checklist/facts/` | A4: frozen atomic facts per answer key (45 papers: the 36 held-out ones, then test4 after its finals) |
| `checklist/scores/{controls,runs,retest,phaseb,test4}/{gpt56,deepseek}/` | A4: checklist verdicts with verified quotes |
| `checklist/analysis.json` | A4: reliability and the adoption decision (not adopted) |
| `triage/` | A5: 60 stratified runs triaged by both judges (`sample.json` lists them) |
| `key_audit/`, `key_audit_test4/` | A6: field-by-field answer-key audits by both judges |
| `measurement.json` | A1, A2, A3, A5 and A6 summary |
| `probe/` | B1: memorisation probe of gpt-4o, o3, o4-mini, gpt-4.1 and gpt-5 against Llama-3.3 (`summary.json`) |
| `phase_b.json` | Experiment 34: each configuration vs the replicate, finalist rule, router agreement, few-shot leakage check |
| `test4.json` | Experiment 35: test4 replication, and the pooled 37-paper estimate |
| `run_phase_a.sh`, `logs/` | Runner (logs not committed) |

**Headline.**
- The judges pass every sanity control, the checklist judge is not adopted, and no answer key is flagged.
- No method change beats the o3-mini conservative writer.
- The writer's lead over the Llama baseline replicates on test4, and over 37 fresh papers it is +0.11 (GPT-5.6,
  p = 0.003) and +0.27 (DeepSeek, p = 0.0001).
