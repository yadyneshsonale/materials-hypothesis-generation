# Experiment 36: web search for every baseline (harness runs)

**Plan.** [loop.md](../../../loop.md) section 17: 17.1 pre-registration; 17.2 Crossref replaces OpenAlex; 17.3
evaluation order and the suite tool agent.
**Runner.** [loop/run_web.sh](../loop/run_web.sh). **Analysis.** [web_analysis.py](../../../web_analysis.py) writes
`analysis_web.json` and `analysis_web.md` here. **Progress.** [web_status.py](../../../web_status.py).
**Corpora.** [websearch/](../websearch/README.md).

## What runs

Every harness configuration that uses evidence (the 30 analysed in experiments 23–35) is re-run as
`web_<name>`. In each, the question's web-search corpus replaces the fixed 50-paper corpus. Retrieval, budgets and
prompts are unchanged, and so are the models (all pre-cutoff).

The corpus is the first 50 papers of a live Europe PMC search for the question, strictly date-filtered, plus their
co-cited references. Passages and cards come verbatim from the papers' JATS XML.

Three agents search the web themselves, with up to 10 tool calls (`web_search`, `read_paper`, `references`) and up
to 6 pages read. Their writer cites only the pages they read.

| Agent | Searcher | Writer prompt | Compared with |
|---|---|---|---|
| `web_agent` | Llama-3.3 | the Llama baseline's | `closed_book` |
| `web_agent_o3mini` | o3-mini | the o3-mini baseline's | `closed_book_o3mini` |
| `web_agent_b_o3mini` | o3-mini | the best method's (`writer_only_b_o3mini`) | `writer_only_b_o3mini` |

**Tiers.**
- Tier 1: the three agents, `web_text_chunks` and `web_text_chunks_b_o3mini`, on all 45 papers (all36 + test4).
- Tier 2: the other 28 configurations, on all36.

Every run has 3 question levels × 2 samples. All papers are spent, so these are development runs, not finals.

**Evaluation.**
- Every run gets both judges (GPT-5.6, DeepSeek-V4-Pro), the target-free audit and the lever label.
- Under GPT-5.6 rate limits these run in priority order: the primary comparison's configurations first.

## Leakage controls

- **Before any run.** The corpus gate re-checked every corpus paper against every rule: dates from Europe PMC and
  Crossref (and OpenAlex where cached), not the case or a version of it, not a held-out paper, does not cite the
  case.
- **Every run.** The audit re-checks every record the run saw: all dates, case identity and held-out identity. The
  agents' search results, which pass the same filters, are audited too.
- **After the runs.** `web_analysis.py` W5 re-verifies every evidence record's dates, and runs the evidence-leak test
  (answer words in the evidence, own case vs other cases, web vs fixed corpus).

## Results

Full tables: [analysis_web.md](./analysis_web.md); discussion: [loop.md](../../../loop.md) 17.4.

**W1 (primary): each baseline with web search vs the same baseline without evidence** (GPT-5.6; 45 papers unless
stated).

| With web search | Without evidence | Difference [95% CI] | Holm p | DeepSeek |
|---|---|---|---|---|
| `web_text_chunks` | `closed_book` (Llama) | −0.00 [−0.06, +0.06] | 1.0 | +0.02 |
| `web_agent` | `closed_book` (Llama) | −0.08 [−0.15, −0.01] | 0.70 | −0.08 |
| `web_agent_o3mini` (24 papers) | `closed_book_o3mini` | +0.00 [−0.07, +0.07] | 1.0 | +0.13 |
| `web_text_chunks_b_o3mini` | `writer_only_b_o3mini` | −0.02 [−0.07, +0.04] | 1.0 | +0.04 |
| `web_agent_b_o3mini` | `writer_only_b_o3mini` | −0.07 [−0.11, −0.02] | 0.16 | −0.05 |

- **Web search helps no baseline** (pre-registered rule).
- **Web vs fixed corpus (W2).** No difference survives Holm with GPT-5.6. DeepSeek prefers the web versions of the
  card-based configurations (+0.15 to +0.28); GPT-5.6 does not.
- **Rankings (W3).** The best web configuration ties the no-evidence incumbent (0.622 vs 0.623). Configuration ranks
  agree across evidence sources (ρ = 0.79 / 0.72).
- **Leakage (W5).**
  - Counters are zero in all 7,398 runs, and every evidence record's dates were re-checked with no violation.
  - No evidence paper contains more than 1.5% of a held-out paper's text.
  - The answer-word test rises modestly for evidence-heavy configurations, as targeted search should, and their
    scores did not rise.
- **Evaluations.**
  - Both judges are complete for every run.
  - Target-free audits are complete for every run (see `must_obey_check.py` in loop.md 17.4).
  - Lever labels exist for the five primary configurations only (loop.md 17.3).
