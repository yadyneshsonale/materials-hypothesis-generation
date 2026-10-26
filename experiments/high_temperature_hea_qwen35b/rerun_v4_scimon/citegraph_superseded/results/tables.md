# Citation-graph variant: results

Graph: 12 cases, 213 unique full-text papers, 13790 references (resolution {'doi': 0.752, 'title': 0.152, 'unresolved': 0.096, 'pmid': 0.001}).

| per case (mean) | nodes | full_text_nodes | seeds | expansion | edges | nodes_with_statements | statements | nodes_with_2plus_citers | contradicting_statements |
|---|---|---|---|---|---|---|---|---|---|
| | 1336 | 24.333 | 10 | 14.333 | 1613 | 379 | 591 | 34.667 | 4.25 |

## Scores by arm

| arm | runs | failed | GPT-5.6 | DeepSeek | non-broad | broad | problem | expert | intervention | mechanism | outcome | evidence validity | novelty | own mechanism | unjustified transfer | specificity | packed papers | with citer statements |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| closed_book | 24 | 0 | 0.427 | 0.198 | - | - | - | - | 0.292 | 0.292 | 0.708 | 0.375 | 0.083 | 1 | 0 | 0 | 0 | - |
| text_chunks | 24 | 0 | 0.438 | 0.281 | - | - | - | - | 0.25 | 0.5 | 0.667 | 1.292 | 0.792 | 0.542 | 0.208 | 0.097 | 9.75 | - |
| card | 24 | 0 | 0.458 | 0.125 | - | - | - | - | 0.583 | 0.375 | 0.625 | 1.417 | 1.167 | 0.542 | 0.292 | 0.347 | 5.583 | - |
| card_systemmatch | 24 | 0 | 0.521 | 0.156 | - | - | - | - | 0.417 | 0.583 | 0.792 | 1.417 | 0.375 | 0.625 | 0.333 | 0.014 | 5.583 | - |
| graph_selection | 24 | 0 | 0.354 | 0.125 | - | - | - | - | 0.25 | 0.25 | 0.625 | 1.292 | 1.208 | 0.417 | 0.292 | 0.306 | 7 | 0 |
| graph_profiles | 24 | 0 | 0.448 | 0.156 | - | - | - | - | 0.25 | 0.375 | 1 | 1.417 | 0.667 | 0.542 | 0.25 | 0.153 | 17.25 | 13.917 |
| graph_profiles_systemmatch | 24 | 0 | 0.375 | 0.156 | - | - | - | - | 0.25 | 0.375 | 0.542 | 1.125 | 0.667 | 0.458 | 0.417 | 0.153 | 17.25 | 13.917 |
| corroboration_weighted | 24 | 0 | 0.396 | 0.271 | - | - | - | - | 0.417 | 0.292 | 0.708 | 0.917 | 0.583 | 0.417 | 0.292 | 0.069 | 14.083 | 14 |
| graph_tool_agent | 24 | 0 | 0.333 | 0.073 | - | - | - | - | 0.208 | 0.292 | 0.792 | 0.917 | 0.75 | 0.583 | 0.292 | 0.139 | 0.917 | 0.75 |

## Paired comparisons (GPT-5.6)

| a | b | role | units | diff | 95% CI | a higher | b higher | p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| graph_selection | text_chunks | primary | 12 | -0.083 | [-0.26, 0.083] | 3 | 4 | 1 | 1 |
| graph_profiles | text_chunks | primary | 12 | 0.01 | [-0.146, 0.146] | 7 | 4 | 0.549 | 1 |
| graph_profiles_systemmatch | text_chunks | primary | 12 | -0.062 | [-0.24, 0.094] | 4 | 6 | 0.754 | 1 |
| corroboration_weighted | text_chunks | primary | 12 | -0.042 | [-0.26, 0.146] | 3 | 5 | 0.727 | 1 |
| graph_tool_agent | text_chunks | primary | 12 | -0.104 | [-0.323, 0.073] | 3 | 5 | 0.727 | 1 |
| graph_selection | card | secondary | 12 | -0.104 | [-0.365, 0.104] | 4 | 7 | 0.549 | - |
| graph_selection | card_systemmatch | secondary | 12 | -0.167 | [-0.365, 0.01] | 3 | 7 | 0.344 | - |
| graph_selection | closed_book | secondary | 12 | -0.073 | [-0.292, 0.156] | 4 | 7 | 0.549 | - |
| graph_profiles | card | secondary | 12 | -0.01 | [-0.24, 0.167] | 7 | 3 | 0.344 | - |
| graph_profiles | card_systemmatch | secondary | 12 | -0.073 | [-0.24, 0.073] | 4 | 6 | 0.754 | - |
| graph_profiles | closed_book | secondary | 12 | 0.021 | [-0.156, 0.188] | 6 | 4 | 0.754 | - |
| graph_profiles_systemmatch | card | secondary | 12 | -0.083 | [-0.292, 0.083] | 5 | 6 | 1 | - |
| graph_profiles_systemmatch | card_systemmatch | secondary | 12 | -0.146 | [-0.302, -0.01] | 2 | 5 | 0.453 | - |
| graph_profiles_systemmatch | closed_book | secondary | 12 | -0.052 | [-0.24, 0.125] | 5 | 6 | 1 | - |
| corroboration_weighted | card | secondary | 12 | -0.062 | [-0.292, 0.146] | 6 | 5 | 1 | - |
| corroboration_weighted | card_systemmatch | secondary | 12 | -0.125 | [-0.292, 0.042] | 3 | 6 | 0.508 | - |
| corroboration_weighted | closed_book | secondary | 12 | -0.031 | [-0.208, 0.146] | 5 | 7 | 0.774 | - |
| graph_tool_agent | card | secondary | 12 | -0.125 | [-0.375, 0.115] | 5 | 5 | 1 | - |
| graph_tool_agent | card_systemmatch | secondary | 12 | -0.188 | [-0.385, 0.0] | 3 | 8 | 0.227 | - |
| graph_tool_agent | closed_book | secondary | 12 | -0.094 | [-0.323, 0.146] | 5 | 7 | 0.774 | - |
| graph_profiles | graph_selection | secondary | 12 | 0.094 | [-0.062, 0.208] | 9 | 2 | 0.065 | - |
| graph_profiles_systemmatch | graph_profiles | secondary | 12 | -0.073 | [-0.146, -0.01] | 1 | 5 | 0.219 | - |
| corroboration_weighted | graph_profiles | secondary | 12 | -0.052 | [-0.198, 0.083] | 4 | 5 | 1 | - |
| graph_tool_agent | graph_profiles | secondary | 12 | -0.115 | [-0.26, 0.042] | 3 | 6 | 0.508 | - |

## Paired comparisons (DeepSeek-V4-Pro)

| a | b | role | units | diff | 95% CI | a higher | b higher | p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| graph_selection | text_chunks | primary | 12 | -0.156 | [-0.333, 0.021] | 1 | 5 | 0.219 | 0.875 |
| graph_profiles | text_chunks | primary | 12 | -0.125 | [-0.302, 0.042] | 3 | 5 | 0.727 | 1 |
| graph_profiles_systemmatch | text_chunks | primary | 12 | -0.125 | [-0.302, 0.031] | 3 | 5 | 0.727 | 1 |
| corroboration_weighted | text_chunks | primary | 12 | -0.01 | [-0.229, 0.24] | 3 | 4 | 1 | 1 |
| graph_tool_agent | text_chunks | primary | 12 | -0.208 | [-0.354, -0.062] | 1 | 8 | 0.039 | 0.196 |
| graph_selection | card | secondary | 12 | 0 | [-0.146, 0.135] | 3 | 2 | 1 | - |
| graph_selection | card_systemmatch | secondary | 12 | -0.031 | [-0.156, 0.094] | 3 | 4 | 1 | - |
| graph_selection | closed_book | secondary | 12 | -0.073 | [-0.198, 0.052] | 2 | 5 | 0.453 | - |
| graph_profiles | card | secondary | 12 | 0.031 | [-0.073, 0.135] | 3 | 2 | 1 | - |
| graph_profiles | card_systemmatch | secondary | 12 | 0 | [-0.115, 0.135] | 3 | 5 | 0.727 | - |
| graph_profiles | closed_book | secondary | 12 | -0.042 | [-0.177, 0.094] | 3 | 6 | 0.508 | - |
| graph_profiles_systemmatch | card | secondary | 12 | 0.031 | [-0.083, 0.135] | 4 | 3 | 1 | - |
| graph_profiles_systemmatch | card_systemmatch | secondary | 12 | 0 | [-0.104, 0.125] | 3 | 5 | 0.727 | - |
| graph_profiles_systemmatch | closed_book | secondary | 12 | -0.042 | [-0.177, 0.094] | 4 | 5 | 1 | - |
| corroboration_weighted | card | secondary | 12 | 0.146 | [-0.073, 0.396] | 6 | 2 | 0.289 | - |
| corroboration_weighted | card_systemmatch | secondary | 12 | 0.115 | [-0.083, 0.354] | 6 | 4 | 0.754 | - |
| corroboration_weighted | closed_book | secondary | 12 | 0.073 | [-0.094, 0.26] | 5 | 4 | 1 | - |
| graph_tool_agent | card | secondary | 12 | -0.052 | [-0.135, 0.01] | 1 | 3 | 0.625 | - |
| graph_tool_agent | card_systemmatch | secondary | 12 | -0.083 | [-0.177, 0.031] | 1 | 6 | 0.125 | - |
| graph_tool_agent | closed_book | secondary | 12 | -0.125 | [-0.25, 0.0] | 2 | 6 | 0.289 | - |
| graph_profiles | graph_selection | secondary | 12 | 0.031 | [-0.083, 0.125] | 4 | 1 | 0.375 | - |
| graph_profiles_systemmatch | graph_profiles | secondary | 12 | 0 | [-0.042, 0.052] | 1 | 2 | 1 | - |
| corroboration_weighted | graph_profiles | secondary | 12 | 0.115 | [-0.031, 0.312] | 4 | 2 | 0.688 | - |
| graph_tool_agent | graph_profiles | secondary | 12 | -0.083 | [-0.156, -0.021] | 0 | 4 | 0.125 | - |

## Tool agent

```
{
 "runs": 24,
 "tool_calls_mean": 1.833,
 "tool_use_share": {
  "submit_hypothesis": 0.353,
  "search_nodes": 0.324,
  "read_node": 0.324
 },
 "nodes_read_mean": 0.917,
 "rejected_submissions": 0
}
```

## Integrity

```
{
 "expected_runs": 120,
 "runs": 120,
 "ok": 120,
 "judged_gpt56": 120,
 "judged_deepseek": 120,
 "audited": 120,
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
