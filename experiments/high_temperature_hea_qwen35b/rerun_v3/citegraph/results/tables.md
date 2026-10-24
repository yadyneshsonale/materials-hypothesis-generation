# Citation-graph variant: results

Graph: 12 cases, 248 unique full-text papers, 13308 references (resolution {'doi': 0.729, 'title': 0.212, 'unresolved': 0.058, 'pmid': 0.001}).

| per case (mean) | nodes | full_text_nodes | seeds | expansion | edges | nodes_with_statements | statements | nodes_with_2plus_citers | contradicting_statements |
|---|---|---|---|---|---|---|---|---|---|
| | 1259 | 29.583 | 10 | 19.583 | 1565 | 649 | 1053 | 67.25 | 9.167 |

## Scores by arm

| arm | runs | failed | GPT-5.6 | DeepSeek | non-broad | broad | problem | expert | intervention | mechanism | outcome | evidence validity | novelty | own mechanism | unjustified transfer | specificity | packed papers | with citer statements |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| closed_book | 72 | 0 | 0.601 | 0.278 | 0.589 | 0.625 | 0.552 | 0.625 | 0.278 | 0.653 | 0.931 | 0.028 | 1.208 | 1 | 0 | 0.171 | 0 | - |
| text_chunks | 72 | 0 | 0.469 | 0.257 | 0.448 | 0.51 | 0.458 | 0.438 | 0.111 | 0.556 | 0.708 | 1.083 | 1.125 | 0.292 | 0.611 | 0.116 | 11.306 | - |
| card | 72 | 0 | 0.476 | 0.198 | 0.521 | 0.385 | 0.51 | 0.531 | 0.208 | 0.472 | 0.764 | 0.75 | 1.444 | 0.792 | 0.181 | 0.148 | 5.472 | - |
| card_systemmatch | 72 | 0 | 0.493 | 0.205 | 0.5 | 0.479 | 0.552 | 0.448 | 0.194 | 0.528 | 0.806 | 0.75 | 1.25 | 0.736 | 0.264 | 0.171 | 5.472 | - |
| graph_selection | 72 | 0 | 0.535 | 0.222 | 0.573 | 0.458 | 0.604 | 0.542 | 0.181 | 0.472 | 0.861 | 1.111 | 1.389 | 0.569 | 0.347 | 0.227 | 5.278 | 0 |
| graph_profiles | 72 | 0 | 0.552 | 0.271 | 0.573 | 0.51 | 0.604 | 0.542 | 0.167 | 0.528 | 0.917 | 1.069 | 1.222 | 0.403 | 0.514 | 0.134 | 15.528 | 13.917 |
| graph_profiles_systemmatch | 72 | 0 | 0.479 | 0.271 | 0.469 | 0.5 | 0.49 | 0.448 | 0.194 | 0.361 | 0.764 | 1.042 | 1.167 | 0.514 | 0.403 | 0.194 | 15.528 | 13.917 |
| corroboration_weighted | 72 | 0 | 0.469 | 0.278 | 0.469 | 0.469 | 0.5 | 0.438 | 0.181 | 0.403 | 0.806 | 0.681 | 1.236 | 0.361 | 0.569 | 0.116 | 9.667 | 9.667 |
| graph_tool_agent | 72 | 0 | 0.462 | 0.125 | 0.49 | 0.406 | 0.438 | 0.542 | 0.194 | 0.361 | 0.847 | 0.139 | 0.903 | 0.889 | 0.111 | 0.12 | 1.236 | 1.014 |

## Paired comparisons (GPT-5.6)

| a | b | role | units | diff | 95% CI | a higher | b higher | p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| graph_selection | text_chunks | primary | 36 | 0.066 | [-0.066, 0.198] | 5 | 4 | 1 | 1 |
| graph_profiles | text_chunks | primary | 36 | 0.083 | [-0.031, 0.181] | 10 | 2 | 0.039 | 0.193 |
| graph_profiles_systemmatch | text_chunks | primary | 36 | 0.01 | [-0.087, 0.097] | 5 | 5 | 1 | 1 |
| corroboration_weighted | text_chunks | primary | 36 | 0 | [-0.115, 0.097] | 7 | 5 | 0.774 | 1 |
| graph_tool_agent | text_chunks | primary | 36 | -0.007 | [-0.132, 0.097] | 8 | 4 | 0.388 | 1 |
| graph_selection | card | secondary | 36 | 0.059 | [-0.087, 0.201] | 7 | 5 | 0.774 | - |
| graph_selection | card_systemmatch | secondary | 36 | 0.042 | [-0.115, 0.188] | 8 | 4 | 0.388 | - |
| graph_selection | closed_book | secondary | 36 | -0.066 | [-0.236, 0.097] | 4 | 8 | 0.388 | - |
| graph_profiles | card | secondary | 36 | 0.076 | [-0.035, 0.188] | 8 | 3 | 0.227 | - |
| graph_profiles | card_systemmatch | secondary | 36 | 0.059 | [-0.049, 0.16] | 8 | 4 | 0.388 | - |
| graph_profiles | closed_book | secondary | 36 | -0.049 | [-0.194, 0.094] | 4 | 7 | 0.549 | - |
| graph_profiles_systemmatch | card | secondary | 36 | 0.003 | [-0.104, 0.09] | 7 | 4 | 0.549 | - |
| graph_profiles_systemmatch | card_systemmatch | secondary | 36 | -0.014 | [-0.135, 0.094] | 7 | 5 | 0.774 | - |
| graph_profiles_systemmatch | closed_book | secondary | 36 | -0.122 | [-0.257, 0.007] | 3 | 8 | 0.227 | - |
| corroboration_weighted | card | secondary | 36 | -0.007 | [-0.097, 0.076] | 7 | 5 | 0.774 | - |
| corroboration_weighted | card_systemmatch | secondary | 36 | -0.024 | [-0.135, 0.076] | 5 | 4 | 1 | - |
| corroboration_weighted | closed_book | secondary | 36 | -0.132 | [-0.25, -0.028] | 3 | 9 | 0.146 | - |
| graph_tool_agent | card | secondary | 36 | -0.014 | [-0.09, 0.073] | 4 | 8 | 0.388 | - |
| graph_tool_agent | card_systemmatch | secondary | 36 | -0.031 | [-0.139, 0.083] | 5 | 7 | 0.774 | - |
| graph_tool_agent | closed_book | secondary | 36 | -0.139 | [-0.253, -0.042] | 1 | 8 | 0.039 | - |
| graph_profiles | graph_selection | secondary | 36 | 0.017 | [-0.094, 0.104] | 7 | 3 | 0.344 | - |
| graph_profiles_systemmatch | graph_profiles | secondary | 36 | -0.073 | [-0.153, 0.007] | 2 | 8 | 0.109 | - |
| corroboration_weighted | graph_profiles | secondary | 36 | -0.083 | [-0.177, 0.003] | 4 | 7 | 0.549 | - |
| graph_tool_agent | graph_profiles | secondary | 36 | -0.09 | [-0.205, 0.017] | 3 | 7 | 0.344 | - |

## Paired comparisons (DeepSeek-V4-Pro)

| a | b | role | units | diff | 95% CI | a higher | b higher | p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| graph_selection | text_chunks | primary | 36 | -0.035 | [-0.135, 0.059] | 5 | 4 | 1 | 1 |
| graph_profiles | text_chunks | primary | 36 | 0.014 | [-0.125, 0.153] | 7 | 5 | 0.774 | 1 |
| graph_profiles_systemmatch | text_chunks | primary | 36 | 0.014 | [-0.097, 0.122] | 5 | 3 | 0.727 | 1 |
| corroboration_weighted | text_chunks | primary | 36 | 0.021 | [-0.056, 0.097] | 5 | 5 | 1 | 1 |
| graph_tool_agent | text_chunks | primary | 36 | -0.132 | [-0.26, -0.014] | 4 | 7 | 0.549 | 1 |
| graph_selection | card | secondary | 36 | 0.024 | [-0.066, 0.118] | 6 | 4 | 0.754 | - |
| graph_selection | card_systemmatch | secondary | 36 | 0.017 | [-0.08, 0.108] | 7 | 5 | 0.774 | - |
| graph_selection | closed_book | secondary | 36 | -0.056 | [-0.208, 0.094] | 4 | 8 | 0.388 | - |
| graph_profiles | card | secondary | 36 | 0.073 | [-0.042, 0.191] | 7 | 4 | 0.549 | - |
| graph_profiles | card_systemmatch | secondary | 36 | 0.066 | [-0.059, 0.194] | 7 | 5 | 0.774 | - |
| graph_profiles | closed_book | secondary | 36 | -0.007 | [-0.149, 0.132] | 6 | 5 | 1 | - |
| graph_profiles_systemmatch | card | secondary | 36 | 0.073 | [-0.017, 0.156] | 8 | 4 | 0.388 | - |
| graph_profiles_systemmatch | card_systemmatch | secondary | 36 | 0.066 | [-0.024, 0.16] | 7 | 3 | 0.344 | - |
| graph_profiles_systemmatch | closed_book | secondary | 36 | -0.007 | [-0.177, 0.163] | 6 | 5 | 1 | - |
| corroboration_weighted | card | secondary | 36 | 0.08 | [-0.035, 0.194] | 7 | 5 | 0.774 | - |
| corroboration_weighted | card_systemmatch | secondary | 36 | 0.073 | [-0.052, 0.188] | 8 | 3 | 0.227 | - |
| corroboration_weighted | closed_book | secondary | 36 | 0 | [-0.108, 0.104] | 7 | 5 | 0.774 | - |
| graph_tool_agent | card | secondary | 36 | -0.073 | [-0.194, 0.035] | 6 | 5 | 1 | - |
| graph_tool_agent | card_systemmatch | secondary | 36 | -0.08 | [-0.208, 0.031] | 5 | 6 | 1 | - |
| graph_tool_agent | closed_book | secondary | 36 | -0.153 | [-0.278, -0.049] | 1 | 9 | 0.021 | - |
| graph_profiles | graph_selection | secondary | 36 | 0.049 | [-0.052, 0.16] | 6 | 6 | 1 | - |
| graph_profiles_systemmatch | graph_profiles | secondary | 36 | 0 | [-0.108, 0.108] | 5 | 6 | 1 | - |
| corroboration_weighted | graph_profiles | secondary | 36 | 0.007 | [-0.104, 0.108] | 7 | 5 | 0.774 | - |
| graph_tool_agent | graph_profiles | secondary | 36 | -0.146 | [-0.24, -0.062] | 2 | 10 | 0.039 | - |

## Tool agent

```
{
 "runs": 72,
 "tool_calls_mean": 2.167,
 "tool_use_share": {
  "submit_hypothesis": 0.469,
  "read_node": 0.31,
  "search_nodes": 0.221
 },
 "nodes_read_mean": 1.236,
 "rejected_submissions": 66
}
```

## Integrity

```
{
 "expected_runs": 360,
 "runs": 360,
 "ok": 360,
 "judged_gpt56": 360,
 "judged_deepseek": 360,
 "audited": 360,
 "temporal_violations": 0,
 "test_paper_leaks": 0,
 "family_leaks": 0,
 "target_doi_or_title_leaks": 0,
 "invalid_citations": 0,
 "stage_errors": {
  "audit": 0,
  "cross_judge": 0,
  "extract": 0,
  "generate": 0,
  "judge": 0
 },
 "generators": [
  "trapi:Llama-3.3-70B-Instruct_5"
 ],
 "failed_after_retry": [],
 "verified": true
}
```
