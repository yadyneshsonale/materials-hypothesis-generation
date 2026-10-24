# Citation-graph failure analysis

## Statement fidelity

| | n | attributed_supported | attributed_distorted | attributed_unsupported | relation_correct | system_supported_when_stated |
|---|---|---|---|---|---|---|
| compares | 15 | 0.6 | 0.267 | 0.133 | 1 | 0.4 |
| contradicts | 15 | 0.8 | 0.067 | 0.133 | 0.8 | 0.923 |
| extends | 15 | 0.8 | 0.133 | 0.067 | 1 | 1 |
| finding | 15 | 0.667 | 0.2 | 0.133 | 0.8 | 0.692 |
| method | 15 | 0.467 | 0.133 | 0.4 | 0.8 | 0.125 |
| supports | 15 | 1 | 0 | 0 | 1 | 0.769 |
| all | 90 | 0.722 | 0.133 | 0.144 | 0.9 | 0.676 |

## Evidence ceiling (top 20 by target text)

| | cases | reconstructibility | cases_reconstructible_2 | supportive_in_top20 | strong_in_top20 | supportive_that_are_reference_only |
|---|---|---|---|---|---|---|
| graph_profiles | 12 | 1.25 | 3 | 15.333 | 2 | 0.521 |
| graph_selection | 12 | 1.333 | 4 | 14.75 | 2.167 | 0 |
| corpus_text_chunks | 12 | 1.25 | 3 | 14.083 | 2 | - |
| corpus_card | 12 | 1.417 | 5 | 14.333 | 1.75 | - |

## Retrieval and use

| | runs | failure_rate | mean_supportive_packed | share_cited_supportive | cited_reference_only_share | cited_with_citer_statements_share | recon_by_stage |
|---|---|---|---|---|---|---|---|
| text_chunks | 72 | 0.361 | 4.028 | 0.548 | - | - | {"supportive_cited": 1.543, "no_supportive_in_context": 0.25, "supportive_in_context_not_cited": 2.125} |
| card | 72 | 0.389 | 3.667 | 0.814 | - | - | {"supportive_cited": 1.561, "no_supportive_in_context": 0.25} |
| card_systemmatch | 72 | 0.306 | 3.667 | 0.849 | - | - | {"supportive_cited": 1.65, "no_supportive_in_context": 0.5} |
| graph_selection | 72 | 0.361 | 3.861 | 0.854 | 0 | 0 | {"supportive_cited": 1.524} |
| graph_profiles | 72 | 0.375 | 3.833 | 0.46 | 0.573 | 0.573 | {"supportive_cited": 1.617, "supportive_in_context_not_cited": 0.625, "no_supportive_in_context": 0.438} |
| graph_profiles_systemmatch | 71 | 0.394 | 3.859 | 0.464 | 0.568 | 0.568 | {"supportive_cited": 1.553, "no_supportive_in_context": 0.25, "supportive_in_context_not_cited": 3.5} |
| corroboration_weighted | 72 | 0.361 | 1.25 | 0.221 | 0.899 | 0.899 | {"no_supportive_in_context": 1.227, "supportive_cited": 1.633, "supportive_in_context_not_cited": 1.3} |
| graph_tool_agent | 72 | 0.403 | 1.569 | 0.321 | 0.53 | 0.53 | {"no_supportive_in_context": 0.893, "supportive_cited": 1.703, "supportive_in_context_not_cited": 1.35} |

## Errors per run and category shares

| | errors_per_run | wrong_intervention | wrong_mechanism | wrong_outcome | wrong_baseline | wrong_conditions | physical_error | evidence_unsupported | evidence_contradicted | internal_inconsistency | untestable_or_vague | other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| closed_book | 3.53 | 0.134 | 0.251 | 0.097 | 0.053 | 0.17 | 0.053 | 0.134 | 0 | 0.012 | 0.093 | 0.004 |
| text_chunks | 3.81 | 0.128 | 0.204 | 0.091 | 0.044 | 0.15 | 0.04 | 0.215 | 0.026 | 0.018 | 0.08 | 0.004 |
| card | 4.18 | 0.13 | 0.183 | 0.086 | 0.05 | 0.159 | 0.066 | 0.209 | 0.013 | 0.02 | 0.083 | 0 |
| card_systemmatch | 3.86 | 0.126 | 0.216 | 0.129 | 0.061 | 0.169 | 0.036 | 0.169 | 0.004 | 0.011 | 0.079 | 0 |
| graph_selection | 3.97 | 0.098 | 0.224 | 0.073 | 0.063 | 0.171 | 0.056 | 0.217 | 0.007 | 0.024 | 0.066 | 0 |
| graph_profiles | 3.85 | 0.116 | 0.202 | 0.09 | 0.072 | 0.166 | 0.036 | 0.191 | 0.011 | 0.025 | 0.09 | 0 |
| graph_profiles_systemmatch | 4.03 | 0.112 | 0.227 | 0.091 | 0.066 | 0.206 | 0.063 | 0.133 | 0.01 | 0.017 | 0.073 | 0 |
| corroboration_weighted | 4.12 | 0.128 | 0.219 | 0.074 | 0.054 | 0.172 | 0.047 | 0.199 | 0.007 | 0.017 | 0.081 | 0.003 |
| graph_tool_agent | 3.92 | 0.128 | 0.199 | 0.103 | 0.053 | 0.16 | 0.046 | 0.184 | 0.011 | 0.035 | 0.082 | 0 |

## Share of failures with each error

| | failures | wrong_intervention | wrong_mechanism | wrong_outcome | wrong_baseline | wrong_conditions | physical_error | evidence_unsupported | evidence_contradicted | internal_inconsistency | untestable_or_vague | other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| closed_book | 23 | 0.739 | 0.696 | 0.391 | 0.261 | 0.478 | 0.13 | 0.652 | 0 | 0.043 | 0.348 | 0.043 |
| text_chunks | 26 | 0.769 | 0.692 | 0.538 | 0.269 | 0.538 | 0.115 | 0.808 | 0.115 | 0.115 | 0.154 | 0.038 |
| card | 28 | 0.607 | 0.714 | 0.393 | 0.286 | 0.464 | 0.143 | 0.786 | 0.036 | 0.071 | 0.357 | 0 |
| card_systemmatch | 22 | 0.636 | 0.727 | 0.5 | 0.318 | 0.5 | 0.136 | 0.727 | 0 | 0.045 | 0.273 | 0 |
| graph_selection | 26 | 0.615 | 0.654 | 0.308 | 0.385 | 0.615 | 0.192 | 0.962 | 0.038 | 0.115 | 0.308 | 0 |
| graph_profiles | 27 | 0.519 | 0.667 | 0.37 | 0.407 | 0.593 | 0.185 | 0.704 | 0.074 | 0.111 | 0.222 | 0 |
| graph_profiles_systemmatch | 28 | 0.643 | 0.821 | 0.357 | 0.393 | 0.607 | 0.286 | 0.607 | 0.071 | 0.107 | 0.25 | 0 |
| corroboration_weighted | 26 | 0.731 | 0.808 | 0.308 | 0.462 | 0.462 | 0.192 | 0.962 | 0.077 | 0.077 | 0.231 | 0.038 |
| graph_tool_agent | 29 | 0.552 | 0.655 | 0.379 | 0.31 | 0.483 | 0.172 | 0.828 | 0.069 | 0.138 | 0.379 | 0 |

## Tool agent

```
{
 "runs": 72,
 "tool_use": {
  "search_nodes": 334,
  "read_node": 501,
  "submit_hypothesis": 78,
  "who_cites": 51,
  "references": 4
 },
 "runs_using_graph_navigation": 20,
 "reads_mean": 6.958,
 "budget_exhausted": 72,
 "spearman_reads_vs_recon": -0.041,
 "recon_with_navigation": 1.525,
 "recon_without_navigation": 1.519
}
```

## Best arm per unit (ties count for each)

```
{"card_systemmatch": 12, "closed_book": 7, "text_chunks": 7, "graph_tool_agent": 7, "graph_profiles": 6, "card": 5, "graph_profiles_systemmatch": 4, "corroboration_weighted": 4, "graph_selection": 3}
```
