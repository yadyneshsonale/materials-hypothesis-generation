# Experiment 36: the experiment-21 suite with web search (12 papers, v3 questions)

| arm | web GPT | web DeepSeek | exp 21 GPT | exp 21 DeepSeek | vs closed-book GPT | vs closed-book DeepSeek | web − exp 21 GPT | web − exp 21 DeepSeek |
|---|---:|---:|---:|---:|---|---|---|---|
| exp14_rubrics:closed_book (copied) | 0.601 | 0.278 | 0.601 | 0.278 | - | - | - | - |
| exp7_eval_v3:closed_book (copied) | 0.569 | 0.243 | 0.569 | None | - | - | - | - |
| exp16_improvements:closed_book_fixed (copied) | 0.531 | 0.274 | 0.531 | 0.274 | - | - | - | - |
| exp16_improvements:ensemble_select | 0.51 | 0.264 | 0.542 | 0.267 | -0.09 [-0.16, -0.02] (12 papers, Holm p 0.4632) | -0.01 [-0.12, +0.09] (12 papers, Holm p 1.0) | -0.03 [-0.10, +0.03] (12 papers, Holm p 1.0) | -0.00 [-0.12, +0.12] (12 papers, Holm p 1.0) |
| exp17_citegraph:graph_selection | 0.49 | 0.281 | 0.535 | 0.222 | -0.11 [-0.23, +0.00] (12 papers, Holm p 0.7658) | +0.00 [-0.12, +0.12] (12 papers, Holm p 1.0) | -0.04 [-0.14, +0.05] (12 papers, Holm p 1.0) | +0.06 [-0.06, +0.18] (12 papers, Holm p 1.0) |
| exp16_improvements:knowledge_first | 0.483 | 0.26 | 0.531 | 0.229 | -0.12 [-0.18, -0.05] (12 papers, Holm p 0.1755) | -0.02 [-0.11, +0.08] (12 papers, Holm p 1.0) | -0.05 [-0.11, +0.01] (12 papers, Holm p 1.0) | +0.03 [-0.03, +0.10] (12 papers, Holm p 1.0) |
| exp16_improvements:text_systemmatch | 0.483 | 0.326 | 0.483 | 0.319 | -0.12 [-0.23, -0.01] (12 papers, Holm p 0.7658) | +0.05 [-0.10, +0.19] (12 papers, Holm p 1.0) | -0.00 [-0.09, +0.09] (12 papers, Holm p 1.0) | +0.01 [-0.17, +0.18] (12 papers, Holm p 1.0) |
| exp14_rubrics:text_chunks | 0.476 | 0.285 | 0.469 | 0.257 | -0.12 [-0.24, -0.01] (12 papers, Holm p 0.7658) | +0.01 [-0.09, +0.10] (12 papers, Holm p 1.0) | +0.01 [-0.07, +0.08] (12 papers, Holm p 1.0) | +0.03 [-0.09, +0.11] (12 papers, Holm p 1.0) |
| exp17_citegraph:graph_profiles_systemmatch | 0.469 | 0.292 | 0.479 | 0.271 | -0.13 [-0.25, +0.00] (12 papers, Holm p 0.4632) | +0.01 [-0.14, +0.18] (12 papers, Holm p 1.0) | -0.01 [-0.08, +0.08] (12 papers, Holm p 1.0) | +0.02 [-0.12, +0.20] (12 papers, Holm p 1.0) |
| exp14_rubrics:card | 0.448 | 0.274 | 0.476 | 0.198 | -0.15 [-0.28, -0.04] (12 papers, Holm p 0.7658) | -0.00 [-0.18, +0.17] (12 papers, Holm p 1.0) | -0.03 [-0.10, +0.04] (12 papers, Holm p 1.0) | +0.08 [+0.01, +0.15] (12 papers, Holm p 1.0) |
| exp17_citegraph:corroboration_weighted | 0.448 | 0.198 | 0.469 | 0.278 | -0.15 [-0.27, -0.05] (12 papers, Holm p 0.4632) | -0.08 [-0.19, +0.02] (12 papers, Holm p 1.0) | -0.02 [-0.10, +0.07] (12 papers, Holm p 1.0) | -0.08 [-0.16, -0.01] (12 papers, Holm p 1.0) |
| exp7_eval_v3:text_oneshot | 0.444 | 0.264 | 0.431 | None | -0.16 [-0.27, -0.05] (12 papers, Holm p 0.5232) | -0.01 [-0.16, +0.12] (12 papers, Holm p 1.0) | +0.01 [-0.12, +0.13] (12 papers, Holm p 1.0) | - |
| exp16_improvements:card_systemmatch | 0.438 | 0.309 | 0.493 | 0.205 | -0.16 [-0.28, -0.05] (12 papers, Holm p 0.7658) | +0.03 [-0.15, +0.19] (12 papers, Holm p 1.0) | -0.06 [-0.14, +0.04] (12 papers, Holm p 1.0) | +0.10 [+0.00, +0.20] (12 papers, Holm p 1.0) |
| exp17_citegraph:graph_profiles | 0.434 | 0.25 | 0.552 | 0.271 | -0.17 [-0.30, -0.04] (12 papers, Holm p 0.7658) | -0.03 [-0.17, +0.12] (12 papers, Holm p 1.0) | -0.12 [-0.20, -0.04] (12 papers, Holm p 0.6647) | -0.02 [-0.12, +0.07] (12 papers, Holm p 1.0) |
| exp11_critique:critique | 0.431 | 0.174 | 0.354 | None | -0.17 [-0.36, -0.00] (12 papers, Holm p 0.7658) | -0.10 [-0.27, +0.08] (12 papers, Holm p 1.0) | +0.08 [-0.03, +0.17] (12 papers, Holm p 1.0) | - |
| exp17_citegraph:graph_tool_agent | 0.424 | 0.167 | 0.462 | 0.125 | -0.18 [-0.29, -0.09] (12 papers, Holm p 0.1755) | -0.11 [-0.23, -0.01] (12 papers, Holm p 1.0) | -0.04 [-0.09, +0.01] (12 papers, Holm p 1.0) | +0.04 [+0.01, +0.08] (12 papers, Holm p 1.0) |
| exp9_matkg:tool_agent_kg | 0.417 | 0.167 | 0.354 | None | -0.18 [-0.29, -0.09] (12 papers, Holm p 0.2795) | -0.11 [-0.19, -0.02] (12 papers, Holm p 1.0) | +0.06 [-0.04, +0.16] (12 papers, Holm p 1.0) | - |
| exp11_critique:self_revise | 0.375 | 0.188 | 0.382 | None | -0.23 [-0.40, -0.09] (12 papers, Holm p 0.4632) | -0.09 [-0.24, +0.06] (12 papers, Holm p 1.0) | -0.01 [-0.14, +0.12] (12 papers, Holm p 1.0) | - |
| exp7_eval_v3:tool_agent | 0.354 | 0.132 | 0.403 | None | -0.25 [-0.38, -0.13] (12 papers, Holm p 0.1008) | -0.15 [-0.27, -0.03] (12 papers, Holm p 1.0) | -0.05 [-0.15, +0.04] (12 papers, Holm p 1.0) | - |
| exp11_critique:tool_agent_resample | 0.285 | 0.118 | 0.368 | None | -0.32 [-0.45, -0.21] (12 papers, Holm p 0.0085) | -0.16 [-0.26, -0.08] (12 papers, Holm p 0.1989) | -0.08 [-0.17, -0.01] (12 papers, Holm p 1.0) | - |

Beats closed-book: {"gpt": [], "deep": []}

Tool use: {"tool_agent": {"runs": 36, "tool_calls": 1.667, "runs_with_no_tool_call": 11, "runs_shown_live_web_papers": 24, "runs_reading_a_live_web_paper": 9, "live_web_papers_cited": 9}, "tool_agent_kg": {"runs": 36, "tool_calls": 0.139, "runs_with_no_tool_call": 34, "runs_shown_live_web_papers": 2, "runs_reading_a_live_web_paper": 1, "live_web_papers_cited": 0}}

Web citation graphs (mean): {"nodes": 1804.0, "full_text_nodes": 66.917, "edges": 2315.417, "statements": 2486.167, "nodes_with_2plus_citers": 151.0}
