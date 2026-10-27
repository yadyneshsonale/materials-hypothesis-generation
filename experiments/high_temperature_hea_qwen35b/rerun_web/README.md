# Experiment 36 (suite): the experiment-21 evaluations with web search

**Plan.** [loop.md](../../../loop.md) section 17. **Runner.** [run_web_suite.sh](../../../run_web_suite.sh).
**Baselines copied in.** [web_suite_prepare.py](../../../web_suite_prepare.py). **Analysis.**
[web_analysis.py](../../../web_analysis.py) W4 writes `comparison/analysis.json` and `comparison/tables.md`.

## What changed relative to experiment 21 ([rerun_v3](../rerun_v3/README.md))

| | Experiment 21 (`rerun_v3/`) | This rerun (`rerun_web/`) |
|---|---|---|
| Papers and questions | 12 papers, benchmark v3, 3 levels | same |
| Generator, judges | Llama-3.3-70B; GPT-5.6 and DeepSeek-V4-Pro | same (GPT-5.6 served by a second instance of the same deployment, loop.md 17.3) |
| Evidence | the fixed 50-paper corpus (temporally filtered) | each question's web-search corpus ([websearch/](../websearch/README.md)): the first 50 papers of a live Europe PMC search, strictly date-filtered, plus co-cited references; passages and cards verbatim from the XML |
| Tool agent (experiments 7, 11) | `search_corpus` over the fixed corpus | `search_corpus` returns the web corpus's passages and a live web search's top 3 papers, alternately (loop.md 17.3) |
| KG agent (experiment 9) | MatKG tool + fixed corpus | MatKG tool + the web tool agent's corpus and search |
| Citation graphs (experiment 17) | built from Europe PMC searches, LLM-extracted cards and citer statements | built from the problem-level web corpus: XML cards and the verbatim sentences that cite each node |
| Closed-book arms | run | copied from `rerun_v3/` (their input does not change), with their judgments |
| LLM-extracted arms (effects, mechanisms, gaps, mixed, v2 units, v2 one-shot) | run | not re-run (loop.md 17.1) |

## Superseded

[superseded_tool_agent_no_tool_calls/](./superseded_tool_agent_no_tool_calls/README.md) holds 36 tool-agent runs made
with a separate `web_search` tool, which broke Llama's tool-call format: no run made a tool call. They are not
analysed.

## Results

Full table: [comparison/tables.md](./comparison/tables.md); discussion: [loop.md](../../../loop.md) 17.4.

- **Runs.** 1,152 runs and 72 critique revisions, all judged by GPT-5.6 and DeepSeek and audited.
  `must_obey_check.py --bench v3` passes every run directory.
- **No web arm beats closed-book** with either judge. The 17 web arms score 0.29–0.51 against 0.60 (GPT-5.6, the
  experiment-14 closed book).
- **Web vs experiment 21** (same arm, fixed corpus): no difference survives Holm. The largest is graph profiles,
  −0.12 [−0.20, −0.04].
- **Tool use.**
  - 24 of the 36 web tool-agent runs were shown live web-search papers, and 9 read and cited one.
  - The KG agent made no tool call in 34 of 36 runs, as in experiment 21 (35 of 36), so its result says nothing about
    MatKG.
- **Citation graphs** (from the web corpora): 1,804 nodes, 67 full-text papers and 2,486 verbatim citing sentences
  per paper on average.
