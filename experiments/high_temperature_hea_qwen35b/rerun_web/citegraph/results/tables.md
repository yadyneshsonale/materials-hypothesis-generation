# Citation-graph variant: results

Graph: 12 cases, 0 unique full-text papers, 0 references (resolution {}).

| per case (mean) | nodes | full_text_nodes | seeds | expansion | edges | nodes_with_statements | statements | nodes_with_2plus_citers | contradicting_statements |
|---|---|---|---|---|---|---|---|---|---|
| | 1804 | 66.917 | 50 | 16.917 | 2315 | 1322 | 2486 | 151 | 0 |

## Scores by arm

| arm | runs | failed | GPT-5.6 | DeepSeek | non-broad | broad | problem | expert | intervention | mechanism | outcome | evidence validity | novelty | own mechanism | unjustified transfer | specificity | packed papers | with citer statements |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| closed_book | 72 | 0 | 0.601 | 0.278 | 0.589 | 0.625 | 0.552 | 0.625 | 0.278 | 0.653 | 0.931 | 0.028 | 1.208 | 1 | 0 | 0.171 | 0 | - |
| text_chunks | 72 | 0 | 0.476 | 0.285 | 0.547 | 0.333 | 0.635 | 0.458 | 0.153 | 0.431 | 0.806 | 1.306 | 1.236 | 0.194 | 0.597 | 0.167 | 11.139 | - |
| card | 72 | 0 | 0.448 | 0.274 | 0.5 | 0.344 | 0.531 | 0.469 | 0.181 | 0.431 | 0.736 | 1.028 | 1.319 | 0.208 | 0.694 | 0.204 | 7.889 | - |
| card_systemmatch | 72 | 0 | 0.438 | 0.309 | 0.458 | 0.396 | 0.49 | 0.427 | 0.125 | 0.458 | 0.722 | 1.25 | 1.403 | 0.194 | 0.625 | 0.185 | 7.889 | - |
| graph_selection | 72 | 0 | 0.49 | 0.281 | 0.521 | 0.427 | 0.552 | 0.49 | 0.25 | 0.458 | 0.764 | 1.111 | 1.389 | 0.208 | 0.611 | 0.143 | 7.75 | 0 |
| graph_profiles | 72 | 0 | 0.434 | 0.25 | 0.458 | 0.385 | 0.448 | 0.469 | 0.139 | 0.361 | 0.736 | 0.903 | 1.167 | 0.375 | 0.472 | 0.157 | 16.417 | 15.361 |
| graph_profiles_systemmatch | 72 | 0 | 0.469 | 0.292 | 0.458 | 0.49 | 0.438 | 0.479 | 0.194 | 0.444 | 0.764 | 0.958 | 1.139 | 0.431 | 0.486 | 0.194 | 16.417 | 15.361 |
| corroboration_weighted | 72 | 0 | 0.448 | 0.198 | 0.484 | 0.375 | 0.51 | 0.458 | 0.208 | 0.417 | 0.75 | 0.722 | 0.861 | 0.431 | 0.486 | 0.093 | 6.806 | 6.806 |
| graph_tool_agent | 72 | 0 | 0.424 | 0.167 | 0.443 | 0.385 | 0.323 | 0.562 | 0.153 | 0.319 | 0.792 | 0.208 | 0.986 | 0.819 | 0.167 | 0.116 | 1.764 | 1.597 |

## Paired comparisons (GPT-5.6)

| a | b | role | units | diff | 95% CI | a higher | b higher | p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| graph_selection | text_chunks | primary | 36 | 0.014 | [-0.069, 0.111] | 5 | 5 | 1 | 1 |
| graph_profiles | text_chunks | primary | 36 | -0.042 | [-0.108, 0.021] | 4 | 6 | 0.754 | 1 |
| graph_profiles_systemmatch | text_chunks | primary | 36 | -0.007 | [-0.049, 0.042] | 3 | 6 | 0.508 | 1 |
| corroboration_weighted | text_chunks | primary | 36 | -0.028 | [-0.125, 0.073] | 4 | 7 | 0.549 | 1 |
| graph_tool_agent | text_chunks | primary | 36 | -0.052 | [-0.132, 0.017] | 4 | 6 | 0.754 | 1 |
| graph_selection | card | secondary | 36 | 0.042 | [-0.01, 0.094] | 8 | 3 | 0.227 | - |
| graph_selection | card_systemmatch | secondary | 36 | 0.052 | [0.01, 0.101] | 7 | 2 | 0.18 | - |
| graph_selection | closed_book | secondary | 36 | -0.111 | [-0.229, 0.003] | 4 | 8 | 0.388 | - |
| graph_profiles | card | secondary | 36 | -0.014 | [-0.111, 0.066] | 4 | 7 | 0.549 | - |
| graph_profiles | card_systemmatch | secondary | 36 | -0.003 | [-0.09, 0.069] | 7 | 4 | 0.549 | - |
| graph_profiles | closed_book | secondary | 36 | -0.167 | [-0.302, -0.035] | 3 | 9 | 0.146 | - |
| graph_profiles_systemmatch | card | secondary | 36 | 0.021 | [-0.049, 0.094] | 5 | 5 | 1 | - |
| graph_profiles_systemmatch | card_systemmatch | secondary | 36 | 0.031 | [-0.031, 0.094] | 7 | 3 | 0.344 | - |
| graph_profiles_systemmatch | closed_book | secondary | 36 | -0.132 | [-0.26, 0.0] | 2 | 10 | 0.039 | - |
| corroboration_weighted | card | secondary | 36 | 0 | [-0.066, 0.08] | 3 | 7 | 0.344 | - |
| corroboration_weighted | card_systemmatch | secondary | 36 | 0.01 | [-0.073, 0.101] | 6 | 5 | 1 | - |
| corroboration_weighted | closed_book | secondary | 36 | -0.153 | [-0.271, -0.052] | 2 | 10 | 0.039 | - |
| graph_tool_agent | card | secondary | 36 | -0.024 | [-0.108, 0.059] | 5 | 6 | 1 | - |
| graph_tool_agent | card_systemmatch | secondary | 36 | -0.014 | [-0.111, 0.083] | 6 | 6 | 1 | - |
| graph_tool_agent | closed_book | secondary | 36 | -0.177 | [-0.288, -0.087] | 1 | 10 | 0.012 | - |
| graph_profiles | graph_selection | secondary | 36 | -0.056 | [-0.184, 0.042] | 4 | 6 | 0.754 | - |
| graph_profiles_systemmatch | graph_profiles | secondary | 36 | 0.035 | [-0.028, 0.104] | 6 | 5 | 1 | - |
| corroboration_weighted | graph_profiles | secondary | 36 | 0.014 | [-0.08, 0.132] | 4 | 8 | 0.388 | - |
| graph_tool_agent | graph_profiles | secondary | 36 | -0.01 | [-0.097, 0.076] | 5 | 5 | 1 | - |

## Paired comparisons (DeepSeek-V4-Pro)

| a | b | role | units | diff | 95% CI | a higher | b higher | p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| graph_selection | text_chunks | primary | 36 | -0.003 | [-0.083, 0.073] | 6 | 5 | 1 | 1 |
| graph_profiles | text_chunks | primary | 36 | -0.035 | [-0.156, 0.097] | 5 | 7 | 0.774 | 1 |
| graph_profiles_systemmatch | text_chunks | primary | 36 | 0.007 | [-0.104, 0.16] | 3 | 6 | 0.508 | 1 |
| corroboration_weighted | text_chunks | primary | 36 | -0.087 | [-0.149, -0.021] | 2 | 9 | 0.065 | 0.327 |
| graph_tool_agent | text_chunks | primary | 36 | -0.118 | [-0.215, -0.031] | 2 | 7 | 0.18 | 0.719 |
| graph_selection | card | secondary | 36 | 0.007 | [-0.083, 0.094] | 7 | 4 | 0.549 | - |
| graph_selection | card_systemmatch | secondary | 36 | -0.028 | [-0.132, 0.076] | 5 | 5 | 1 | - |
| graph_selection | closed_book | secondary | 36 | 0.003 | [-0.122, 0.122] | 4 | 5 | 1 | - |
| graph_profiles | card | secondary | 36 | -0.024 | [-0.16, 0.115] | 5 | 5 | 1 | - |
| graph_profiles | card_systemmatch | secondary | 36 | -0.059 | [-0.229, 0.118] | 5 | 6 | 1 | - |
| graph_profiles | closed_book | secondary | 36 | -0.028 | [-0.167, 0.118] | 4 | 6 | 0.754 | - |
| graph_profiles_systemmatch | card | secondary | 36 | 0.017 | [-0.122, 0.16] | 5 | 5 | 1 | - |
| graph_profiles_systemmatch | card_systemmatch | secondary | 36 | -0.017 | [-0.177, 0.174] | 5 | 6 | 1 | - |
| graph_profiles_systemmatch | closed_book | secondary | 36 | 0.014 | [-0.146, 0.191] | 5 | 3 | 0.727 | - |
| corroboration_weighted | card | secondary | 36 | -0.076 | [-0.212, 0.066] | 3 | 8 | 0.227 | - |
| corroboration_weighted | card_systemmatch | secondary | 36 | -0.111 | [-0.222, 0.014] | 2 | 9 | 0.065 | - |
| corroboration_weighted | closed_book | secondary | 36 | -0.08 | [-0.191, 0.017] | 4 | 8 | 0.388 | - |
| graph_tool_agent | card | secondary | 36 | -0.108 | [-0.26, 0.024] | 4 | 7 | 0.549 | - |
| graph_tool_agent | card_systemmatch | secondary | 36 | -0.142 | [-0.274, -0.014] | 4 | 7 | 0.549 | - |
| graph_tool_agent | closed_book | secondary | 36 | -0.111 | [-0.236, -0.014] | 2 | 7 | 0.18 | - |
| graph_profiles | graph_selection | secondary | 36 | -0.031 | [-0.149, 0.104] | 4 | 6 | 0.754 | - |
| graph_profiles_systemmatch | graph_profiles | secondary | 36 | 0.042 | [-0.014, 0.104] | 4 | 5 | 1 | - |
| corroboration_weighted | graph_profiles | secondary | 36 | -0.052 | [-0.198, 0.062] | 5 | 6 | 1 | - |
| graph_tool_agent | graph_profiles | secondary | 36 | -0.083 | [-0.191, 0.01] | 4 | 6 | 0.754 | - |

## Tool agent

```
{
 "runs": 72,
 "tool_calls_mean": 2.681,
 "tool_use_share": {
  "submit_hypothesis": 0.419,
  "read_node": 0.389,
  "search_nodes": 0.193
 },
 "nodes_read_mean": 1.764,
 "rejected_submissions": 67
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
