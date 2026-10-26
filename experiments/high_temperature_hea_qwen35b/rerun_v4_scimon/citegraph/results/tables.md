# Citation-graph variant: results

Graph: 12 cases, 213 unique full-text papers, 13790 references (resolution {'doi': 0.752, 'title': 0.152, 'unresolved': 0.096, 'pmid': 0.001}).

| per case (mean) | nodes | full_text_nodes | seeds | expansion | edges | nodes_with_statements | statements | nodes_with_2plus_citers | contradicting_statements |
|---|---|---|---|---|---|---|---|---|---|
| | 1336 | 24.333 | 10 | 14.333 | 1613 | 562 | 857 | 52.833 | 5.417 |

## Scores by arm

| arm | runs | failed | GPT-5.6 | DeepSeek | non-broad | broad | problem | expert | intervention | mechanism | outcome | evidence validity | novelty | own mechanism | unjustified transfer | specificity | packed papers | with citer statements |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| closed_book | 24 | 0 | 0.427 | 0.198 | - | - | - | - | 0.292 | 0.292 | 0.708 | 0.375 | 0.083 | 1 | 0 | 0 | 0 | - |
| text_chunks | 24 | 0 | 0.438 | 0.281 | - | - | - | - | 0.25 | 0.5 | 0.667 | 1.292 | 0.792 | 0.542 | 0.208 | 0.097 | 9.75 | - |
| card | 24 | 0 | 0.458 | 0.125 | - | - | - | - | 0.583 | 0.375 | 0.625 | 1.417 | 1.167 | 0.542 | 0.292 | 0.347 | 5.583 | - |
| card_systemmatch | 24 | 0 | 0.521 | 0.156 | - | - | - | - | 0.417 | 0.583 | 0.792 | 1.417 | 0.375 | 0.625 | 0.333 | 0.014 | 5.583 | - |
| graph_selection | 24 | 0 | 0.375 | 0.146 | - | - | - | - | 0.167 | 0.375 | 0.708 | 1.25 | 1.125 | 0.417 | 0.25 | 0.375 | 7 | 0 |
| graph_profiles | 24 | 0 | 0.427 | 0.146 | - | - | - | - | 0.292 | 0.292 | 0.875 | 1.333 | 0.708 | 0.375 | 0.292 | 0.125 | 18.25 | 15.917 |
| graph_profiles_systemmatch | 24 | 0 | 0.385 | 0.156 | - | - | - | - | 0.292 | 0.333 | 0.708 | 1.417 | 0.667 | 0.375 | 0.417 | 0.125 | 18.25 | 15.917 |
| corroboration_weighted | 24 | 0 | 0.458 | 0.156 | - | - | - | - | 0.458 | 0.25 | 0.875 | 0.917 | 0.458 | 0.458 | 0.25 | 0.083 | 13.25 | 13.25 |
| graph_tool_agent | 24 | 0 | 0.281 | 0.115 | - | - | - | - | 0.25 | 0.208 | 0.667 | 0.917 | 0.875 | 0.583 | 0.208 | 0.194 | 0.958 | 0.75 |

## Paired comparisons (GPT-5.6)

| a | b | role | units | diff | 95% CI | a higher | b higher | p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| graph_selection | text_chunks | primary | 12 | -0.062 | [-0.24, 0.094] | 5 | 5 | 1 | 1 |
| graph_profiles | text_chunks | primary | 12 | -0.01 | [-0.156, 0.135] | 7 | 5 | 0.774 | 1 |
| graph_profiles_systemmatch | text_chunks | primary | 12 | -0.052 | [-0.208, 0.094] | 4 | 6 | 0.754 | 1 |
| corroboration_weighted | text_chunks | primary | 12 | 0.021 | [-0.229, 0.281] | 5 | 5 | 1 | 1 |
| graph_tool_agent | text_chunks | primary | 12 | -0.156 | [-0.354, 0.0] | 2 | 6 | 0.289 | 1 |
| graph_selection | card | secondary | 12 | -0.083 | [-0.323, 0.104] | 4 | 6 | 0.754 | - |
| graph_selection | card_systemmatch | secondary | 12 | -0.146 | [-0.344, 0.031] | 5 | 6 | 1 | - |
| graph_selection | closed_book | secondary | 12 | -0.052 | [-0.25, 0.146] | 5 | 5 | 1 | - |
| graph_profiles | card | secondary | 12 | -0.031 | [-0.312, 0.198] | 5 | 3 | 0.727 | - |
| graph_profiles | card_systemmatch | secondary | 12 | -0.094 | [-0.323, 0.104] | 4 | 4 | 1 | - |
| graph_profiles | closed_book | secondary | 12 | 0 | [-0.188, 0.198] | 4 | 5 | 1 | - |
| graph_profiles_systemmatch | card | secondary | 12 | -0.073 | [-0.292, 0.115] | 6 | 6 | 1 | - |
| graph_profiles_systemmatch | card_systemmatch | secondary | 12 | -0.135 | [-0.302, 0.021] | 3 | 5 | 0.727 | - |
| graph_profiles_systemmatch | closed_book | secondary | 12 | -0.042 | [-0.177, 0.094] | 5 | 6 | 1 | - |
| corroboration_weighted | card | secondary | 12 | 0 | [-0.292, 0.281] | 4 | 5 | 1 | - |
| corroboration_weighted | card_systemmatch | secondary | 12 | -0.062 | [-0.292, 0.167] | 3 | 6 | 0.508 | - |
| corroboration_weighted | closed_book | secondary | 12 | 0.031 | [-0.115, 0.188] | 4 | 3 | 1 | - |
| graph_tool_agent | card | secondary | 12 | -0.177 | [-0.417, 0.052] | 3 | 7 | 0.344 | - |
| graph_tool_agent | card_systemmatch | secondary | 12 | -0.24 | [-0.417, -0.073] | 2 | 9 | 0.065 | - |
| graph_tool_agent | closed_book | secondary | 12 | -0.146 | [-0.375, 0.094] | 4 | 8 | 0.388 | - |
| graph_profiles | graph_selection | secondary | 12 | 0.052 | [-0.104, 0.188] | 6 | 2 | 0.289 | - |
| graph_profiles_systemmatch | graph_profiles | secondary | 12 | -0.042 | [-0.156, 0.073] | 5 | 5 | 1 | - |
| corroboration_weighted | graph_profiles | secondary | 12 | 0.031 | [-0.115, 0.188] | 4 | 5 | 1 | - |
| graph_tool_agent | graph_profiles | secondary | 12 | -0.146 | [-0.281, 0.0] | 2 | 9 | 0.065 | - |

## Paired comparisons (DeepSeek-V4-Pro)

| a | b | role | units | diff | 95% CI | a higher | b higher | p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| graph_selection | text_chunks | primary | 12 | -0.135 | [-0.292, 0.01] | 2 | 5 | 0.453 | 1 |
| graph_profiles | text_chunks | primary | 12 | -0.135 | [-0.292, 0.0] | 3 | 5 | 0.727 | 1 |
| graph_profiles_systemmatch | text_chunks | primary | 12 | -0.125 | [-0.271, 0.0] | 2 | 5 | 0.453 | 1 |
| corroboration_weighted | text_chunks | primary | 12 | -0.125 | [-0.302, 0.042] | 2 | 4 | 0.688 | 1 |
| graph_tool_agent | text_chunks | primary | 12 | -0.167 | [-0.354, 0.021] | 2 | 8 | 0.109 | 0.547 |
| graph_selection | card | secondary | 12 | 0.021 | [-0.115, 0.125] | 4 | 1 | 0.375 | - |
| graph_selection | card_systemmatch | secondary | 12 | -0.01 | [-0.146, 0.125] | 3 | 4 | 1 | - |
| graph_selection | closed_book | secondary | 12 | -0.052 | [-0.177, 0.062] | 3 | 5 | 0.727 | - |
| graph_profiles | card | secondary | 12 | 0.021 | [-0.125, 0.135] | 5 | 2 | 0.453 | - |
| graph_profiles | card_systemmatch | secondary | 12 | -0.01 | [-0.146, 0.125] | 4 | 5 | 1 | - |
| graph_profiles | closed_book | secondary | 12 | -0.052 | [-0.156, 0.052] | 2 | 5 | 0.453 | - |
| graph_profiles_systemmatch | card | secondary | 12 | 0.031 | [-0.115, 0.135] | 5 | 1 | 0.219 | - |
| graph_profiles_systemmatch | card_systemmatch | secondary | 12 | 0 | [-0.125, 0.125] | 2 | 3 | 1 | - |
| graph_profiles_systemmatch | closed_book | secondary | 12 | -0.042 | [-0.167, 0.073] | 3 | 4 | 1 | - |
| corroboration_weighted | card | secondary | 12 | 0.031 | [-0.135, 0.208] | 3 | 2 | 1 | - |
| corroboration_weighted | card_systemmatch | secondary | 12 | 0 | [-0.167, 0.219] | 3 | 5 | 0.727 | - |
| corroboration_weighted | closed_book | secondary | 12 | -0.042 | [-0.188, 0.135] | 2 | 6 | 0.289 | - |
| graph_tool_agent | card | secondary | 12 | -0.01 | [-0.083, 0.073] | 2 | 4 | 0.688 | - |
| graph_tool_agent | card_systemmatch | secondary | 12 | -0.042 | [-0.156, 0.094] | 2 | 6 | 0.289 | - |
| graph_tool_agent | closed_book | secondary | 12 | -0.083 | [-0.219, 0.073] | 2 | 6 | 0.289 | - |
| graph_profiles | graph_selection | secondary | 12 | 0 | [-0.062, 0.052] | 3 | 2 | 1 | - |
| graph_profiles_systemmatch | graph_profiles | secondary | 12 | 0.01 | [-0.031, 0.052] | 3 | 2 | 1 | - |
| corroboration_weighted | graph_profiles | secondary | 12 | 0.01 | [-0.062, 0.115] | 1 | 3 | 0.625 | - |
| graph_tool_agent | graph_profiles | secondary | 12 | -0.031 | [-0.135, 0.094] | 2 | 5 | 0.453 | - |

## Tool agent

```
{
 "runs": 24,
 "tool_calls_mean": 1.917,
 "tool_use_share": {
  "submit_hypothesis": 0.343,
  "search_nodes": 0.329,
  "read_node": 0.329
 },
 "nodes_read_mean": 0.958,
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
