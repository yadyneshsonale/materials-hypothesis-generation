# Citation-graph variant: results

Graph: 12 cases, 264 unique full-text papers, 14907 references (resolution {'doi': 0.728, 'title': 0.196, 'unresolved': 0.076, 'pmid': 0.001}).

| per case (mean) | nodes | full_text_nodes | seeds | expansion | edges | nodes_with_statements | statements | nodes_with_2plus_citers | contradicting_statements |
|---|---|---|---|---|---|---|---|---|---|
| | 1298 | 29.833 | 10 | 19.833 | 1621 | 673 | 1096 | 70.833 | 10.75 |

## Scores by arm

| arm | runs | failed | GPT-5.6 | DeepSeek | non-broad | broad | problem | expert | intervention | mechanism | outcome | evidence validity | novelty | own mechanism | unjustified transfer | specificity | packed papers | with citer statements |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| closed_book | 72 | 2 | 1.654 | 2.2 | 2.057 | 0.773 | 1.677 | 2.438 | 1.829 | 1.586 | 1.729 | 1.143 | 1.9 | 1 | 0 | 0.467 | 0 | - |
| text_chunks | 72 | 0 | 1.556 | 1.997 | 2 | 0.667 | 1.5 | 2.5 | 1.667 | 1.528 | 1.681 | 1.097 | 2.111 | 0.306 | 0.583 | 0.602 | 11.222 | - |
| card | 72 | 0 | 1.524 | 1.979 | 1.917 | 0.74 | 1.427 | 2.406 | 1.583 | 1.5 | 1.667 | 0.861 | 2.181 | 0.458 | 0.472 | 0.63 | 5.667 | - |
| card_systemmatch | 72 | 0 | 1.618 | 2.017 | 2.021 | 0.812 | 1.417 | 2.625 | 1.722 | 1.639 | 1.597 | 1.25 | 2.111 | 0.306 | 0.569 | 0.741 | 5.667 | - |
| graph_selection | 72 | 0 | 1.524 | 1.906 | 1.974 | 0.625 | 1.469 | 2.479 | 1.583 | 1.472 | 1.681 | 1.042 | 2.208 | 0.333 | 0.514 | 0.662 | 5.056 | 0 |
| graph_profiles | 72 | 0 | 1.524 | 1.965 | 1.948 | 0.677 | 1.51 | 2.385 | 1.625 | 1.472 | 1.708 | 1.056 | 2.014 | 0.292 | 0.542 | 0.634 | 13.583 | 11.333 |
| graph_profiles_systemmatch | 72 | 1 | 1.493 | 2.056 | 1.906 | 0.667 | 1.365 | 2.448 | 1.662 | 1.549 | 1.507 | 1.282 | 2 | 0.282 | 0.507 | 0.812 | 13.535 | 11.296 |
| corroboration_weighted | 72 | 0 | 1.486 | 1.969 | 1.932 | 0.594 | 1.469 | 2.396 | 1.514 | 1.431 | 1.639 | 0.847 | 2.278 | 0.472 | 0.472 | 0.593 | 8.972 | 8.972 |
| graph_tool_agent | 72 | 0 | 1.521 | 1.979 | 1.922 | 0.719 | 1.469 | 2.375 | 1.569 | 1.625 | 1.569 | 0.875 | 2.111 | 0.472 | 0.472 | 0.759 | 6.139 | 5.042 |

## Paired comparisons (GPT-5.6)

| a | b | role | units | diff | 95% CI | a higher | b higher | p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| graph_selection | text_chunks | primary | 36 | -0.031 | [-0.125, 0.056] | 4 | 6 | 0.754 | 1 |
| graph_profiles | text_chunks | primary | 36 | -0.031 | [-0.122, 0.052] | 5 | 6 | 1 | 1 |
| graph_profiles_systemmatch | text_chunks | primary | 36 | -0.062 | [-0.17, 0.031] | 5 | 7 | 0.774 | 1 |
| corroboration_weighted | text_chunks | primary | 36 | -0.069 | [-0.174, 0.028] | 5 | 6 | 1 | 1 |
| graph_tool_agent | text_chunks | primary | 36 | -0.035 | [-0.181, 0.122] | 5 | 6 | 1 | 1 |
| graph_selection | card | secondary | 36 | -0 | [-0.108, 0.097] | 6 | 5 | 1 | - |
| graph_selection | card_systemmatch | secondary | 36 | -0.094 | [-0.257, 0.056] | 4 | 7 | 0.549 | - |
| graph_selection | closed_book | secondary | 35 | -0.095 | [-0.191, -0.002] | 3 | 6 | 0.508 | - |
| graph_profiles | card | secondary | 36 | -0 | [-0.08, 0.09] | 5 | 5 | 1 | - |
| graph_profiles | card_systemmatch | secondary | 36 | -0.094 | [-0.253, 0.038] | 4 | 7 | 0.549 | - |
| graph_profiles | closed_book | secondary | 35 | -0.09 | [-0.222, 0.052] | 2 | 9 | 0.065 | - |
| graph_profiles_systemmatch | card | secondary | 36 | -0.031 | [-0.163, 0.111] | 4 | 7 | 0.549 | - |
| graph_profiles_systemmatch | card_systemmatch | secondary | 36 | -0.125 | [-0.285, 0.0] | 3 | 9 | 0.146 | - |
| graph_profiles_systemmatch | closed_book | secondary | 35 | -0.125 | [-0.247, 0.003] | 3 | 9 | 0.146 | - |
| corroboration_weighted | card | secondary | 36 | -0.038 | [-0.122, 0.052] | 3 | 8 | 0.227 | - |
| corroboration_weighted | card_systemmatch | secondary | 36 | -0.132 | [-0.26, -0.01] | 3 | 8 | 0.227 | - |
| corroboration_weighted | closed_book | secondary | 35 | -0.132 | [-0.229, -0.021] | 2 | 9 | 0.065 | - |
| graph_tool_agent | card | secondary | 36 | -0.003 | [-0.167, 0.167] | 5 | 6 | 1 | - |
| graph_tool_agent | card_systemmatch | secondary | 36 | -0.097 | [-0.271, 0.09] | 4 | 8 | 0.388 | - |
| graph_tool_agent | closed_book | secondary | 35 | -0.097 | [-0.219, 0.017] | 4 | 8 | 0.388 | - |
| graph_profiles | graph_selection | secondary | 36 | 0 | [-0.101, 0.108] | 5 | 6 | 1 | - |
| graph_profiles_systemmatch | graph_profiles | secondary | 36 | -0.031 | [-0.122, 0.08] | 2 | 9 | 0.065 | - |
| corroboration_weighted | graph_profiles | secondary | 36 | -0.038 | [-0.139, 0.052] | 6 | 6 | 1 | - |
| graph_tool_agent | graph_profiles | secondary | 36 | -0.003 | [-0.181, 0.174] | 7 | 5 | 0.774 | - |

## Paired comparisons (DeepSeek-V4-Pro)

| a | b | role | units | diff | 95% CI | a higher | b higher | p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| graph_selection | text_chunks | primary | 36 | -0.09 | [-0.174, 0.003] | 3 | 9 | 0.146 | 0.73 |
| graph_profiles | text_chunks | primary | 36 | -0.031 | [-0.191, 0.111] | 5 | 6 | 1 | 1 |
| graph_profiles_systemmatch | text_chunks | primary | 36 | 0.059 | [-0.125, 0.233] | 7 | 5 | 0.774 | 1 |
| corroboration_weighted | text_chunks | primary | 36 | -0.028 | [-0.139, 0.083] | 5 | 7 | 0.774 | 1 |
| graph_tool_agent | text_chunks | primary | 36 | -0.017 | [-0.191, 0.167] | 5 | 7 | 0.774 | 1 |
| graph_selection | card | secondary | 36 | -0.073 | [-0.222, 0.059] | 4 | 7 | 0.549 | - |
| graph_selection | card_systemmatch | secondary | 36 | -0.111 | [-0.323, 0.142] | 3 | 9 | 0.146 | - |
| graph_selection | closed_book | secondary | 35 | -0.247 | [-0.375, -0.118] | 2 | 10 | 0.039 | - |
| graph_profiles | card | secondary | 36 | -0.014 | [-0.17, 0.142] | 7 | 5 | 0.774 | - |
| graph_profiles | card_systemmatch | secondary | 36 | -0.052 | [-0.247, 0.122] | 6 | 4 | 0.754 | - |
| graph_profiles | closed_book | secondary | 35 | -0.177 | [-0.413, 0.035] | 4 | 8 | 0.388 | - |
| graph_profiles_systemmatch | card | secondary | 36 | 0.076 | [-0.142, 0.271] | 7 | 3 | 0.344 | - |
| graph_profiles_systemmatch | card_systemmatch | secondary | 36 | 0.038 | [-0.149, 0.247] | 5 | 5 | 1 | - |
| graph_profiles_systemmatch | closed_book | secondary | 35 | -0.097 | [-0.274, 0.101] | 3 | 9 | 0.146 | - |
| corroboration_weighted | card | secondary | 36 | -0.01 | [-0.149, 0.125] | 6 | 6 | 1 | - |
| corroboration_weighted | card_systemmatch | secondary | 36 | -0.049 | [-0.184, 0.097] | 3 | 8 | 0.227 | - |
| corroboration_weighted | closed_book | secondary | 35 | -0.177 | [-0.351, -0.031] | 2 | 8 | 0.109 | - |
| graph_tool_agent | card | secondary | 36 | 0 | [-0.205, 0.201] | 6 | 6 | 1 | - |
| graph_tool_agent | card_systemmatch | secondary | 36 | -0.038 | [-0.274, 0.25] | 4 | 8 | 0.388 | - |
| graph_tool_agent | closed_book | secondary | 35 | -0.175 | [-0.302, -0.045] | 3 | 8 | 0.227 | - |
| graph_profiles | graph_selection | secondary | 36 | 0.059 | [-0.146, 0.233] | 8 | 3 | 0.227 | - |
| graph_profiles_systemmatch | graph_profiles | secondary | 36 | 0.09 | [-0.104, 0.302] | 5 | 6 | 1 | - |
| corroboration_weighted | graph_profiles | secondary | 36 | 0.003 | [-0.142, 0.17] | 5 | 6 | 1 | - |
| graph_tool_agent | graph_profiles | secondary | 36 | 0.014 | [-0.229, 0.274] | 5 | 7 | 0.774 | - |

## Tool agent

```
{
 "runs": 72,
 "tool_calls_mean": 12.361,
 "tool_use_share": {
  "read_node": 0.518,
  "search_nodes": 0.345,
  "submit_hypothesis": 0.081,
  "who_cites": 0.053,
  "references": 0.004
 },
 "nodes_read_mean": 6.139,
 "rejected_submissions": 6
}
```

## Integrity

```
{
 "expected_runs": 360,
 "runs": 360,
 "ok": 359,
 "judged_gpt56": 359,
 "judged_deepseek": 359,
 "audited": 359,
 "temporal_violations": 0,
 "test_paper_leaks": 0,
 "family_leaks": 0,
 "target_doi_or_title_leaks": 0,
 "invalid_citations": 0,
 "stage_errors": {
  "audit": 0,
  "cross_judge": 0,
  "extract": 0,
  "fa_ceiling": 0,
  "fa_fidelity": 0,
  "generate": 0,
  "judge": 0
 },
 "generators": [
  "openai:Qwen3.5-35B-A3B-Q4_K_M.gguf"
 ],
 "failed_after_retry": [
  "PMC11775865__broad__graph_profiles_systemmatch__s1"
 ],
 "verified": true
}
```
