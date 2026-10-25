# Rerun on leak-free queries with a pre-cutoff generator

| query level | original overlap | rerun overlap |
|---|---:|---:|
| broad | 0.08 | 0.02 |
| problem_constrained | 0.20 | 0.06 |
| expert_context | 0.47 | 0.05 |

## Factorial (experiment-7 settings): generator x queries

| cell | runs | all | closed_book | text_oneshot | v2_oneshot | tool_agent | broad | problem | expert |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen3.5 (post-cutoff), original leaky queries | 143 | 1.56 | 1.56 | 1.56 | 1.49 | 1.64 | 0.77 | 1.52 | 2.38 |
| llama-3.3 (pre-cutoff), original leaky queries | 144 | 1.40 | 1.57 | 1.43 | 1.38 | 1.21 | 0.65 | 1.36 | 2.18 |
| qwen3.5 (post-cutoff), clean v3 queries | 144 | 0.50 | 0.45 | 0.55 | 0.46 | 0.53 | 0.42 | 0.52 | 0.56 |
| llama-3.3 (pre-cutoff), clean v3 queries | 144 | 0.45 | 0.57 | 0.43 | 0.41 | 0.40 | 0.45 | 0.45 | 0.46 |

| effect | diff | 95% CI | sign-test p |
|---|---:|---|---:|
| query_effect_qwen (clean - leaky) | -1.07 | [-1.366, -0.769] | 0.00 |
| query_effect_llama (clean - leaky) | -0.94 | [-1.182, -0.694] | 0.00 |
| generator_effect_leaky (llama - qwen) | -0.16 | [-0.322, -0.005] | 0.39 |
| generator_effect_clean (llama - qwen) | -0.04 | [-0.125, 0.031] | 0.77 |

## Agent tool use

| agent | runs | tool calls | runs with 0 calls | records cited |
|---|---:|---:|---:|---:|
| exp7 tool_agent original | 36 | 12.00 | 0 | 2.44 |
| exp7 tool_agent rerun | 36 | 2.11 | 9 | 0.94 |
| exp9 tool_agent_kg original | 36 | 12.00 | 0 | 3.11 |
| exp9 tool_agent_kg rerun | 36 | 0.08 | 35 | 0.03 |
| exp7 tool_agent, Qwen on clean queries (factorial) | 36 | 11.94 | 0 | 2.14 |

## Reconstruction score (GPT-5.6; DeepSeek where judged)

| arm | orig GPT | orig DS | orig broad / problem / expert | orig ρ(overlap, score) | rerun GPT | rerun DS | rerun broad / problem / expert | rerun ρ | rerun ρ within expert | rerun, gate-passed units |
|---|---:|---:|---|---:|---:|---:|---|---:|---:|---:|
| exp11_critique:critique | 1.49 | - | 0.96 / 1.40 / 2.10 | 0.72 | 0.35 | - | 0.40 / 0.31 / 0.35 | 0.12 | 0.06 | 0.35 |
| exp11_critique:self_revise | 1.60 | - | 0.75 / 1.69 / 2.35 | 0.73 | 0.38 | - | 0.40 / 0.33 / 0.42 | 0.26 | 0.34 | 0.38 |
| exp11_critique:tool_agent_resample | 1.55 | - | 0.79 / 1.48 / 2.38 | 0.77 | 0.36 | - | 0.25 / 0.44 / 0.39 | 0.50 | 0.37 | 0.36 |
| exp14_rubrics:card | 1.52 | 1.98 | 0.74 / 1.43 / 2.41 | 0.80 | 0.48 | 0.20 | 0.39 / 0.51 / 0.53 | 0.44 | 0.20 | 0.45 |
| exp14_rubrics:closed_book | 1.65 | 2.20 | 0.77 / 1.68 / 2.44 | 0.86 | 0.60 | 0.28 | 0.62 / 0.55 / 0.62 | 0.19 | 0.33 | 0.58 |
| exp14_rubrics:effects | 1.51 | 1.95 | 0.59 / 1.53 / 2.42 | 0.79 | 0.46 | 0.23 | 0.33 / 0.55 / 0.49 | 0.45 | 0.44 | 0.47 |
| exp14_rubrics:gaps | 1.48 | 1.89 | 0.58 / 1.47 / 2.38 | 0.82 | 0.45 | 0.15 | 0.45 / 0.47 / 0.44 | 0.22 | 0.06 | 0.45 |
| exp14_rubrics:mechanisms | 1.46 | 1.90 | 0.55 / 1.45 / 2.37 | 0.84 | 0.42 | 0.24 | 0.47 / 0.38 / 0.43 | 0.01 | -0.14 | 0.43 |
| exp14_rubrics:mixed | 1.39 | 1.86 | 0.54 / 1.38 / 2.25 | 0.82 | 0.40 | 0.19 | 0.40 / 0.39 / 0.42 | 0.23 | 0.25 | 0.40 |
| exp14_rubrics:text_chunks | 1.56 | 2.00 | 0.67 / 1.50 / 2.50 | 0.84 | 0.47 | 0.26 | 0.51 / 0.46 / 0.44 | 0.22 | 0.15 | 0.48 |
| exp14_rubrics:v2_units | 1.52 | 1.96 | 0.58 / 1.54 / 2.44 | 0.88 | 0.38 | 0.16 | 0.31 / 0.45 / 0.39 | 0.37 | 0.15 | 0.38 |
| exp16_improvements:card_systemmatch | 1.62 | 2.02 | 0.81 / 1.42 / 2.62 | 0.83 | 0.49 | 0.20 | 0.48 / 0.55 / 0.45 | 0.25 | -0.21 | 0.47 |
| exp16_improvements:closed_book_fixed | 1.49 | 1.97 | 0.79 / 1.34 / 2.33 | 0.79 | 0.53 | 0.27 | 0.51 / 0.52 / 0.56 | 0.21 | 0.01 | 0.52 |
| exp16_improvements:ensemble_select | 1.59 | 2.12 | 0.75 / 1.46 / 2.55 | 0.83 | 0.54 | 0.27 | 0.50 / 0.56 / 0.56 | 0.31 | 0.15 | 0.52 |
| exp16_improvements:knowledge_first | 1.42 | 1.99 | 0.72 / 1.25 / 2.28 | 0.79 | 0.53 | 0.23 | 0.50 / 0.53 / 0.56 | 0.29 | 0.12 | 0.51 |
| exp16_improvements:text_systemmatch | 1.57 | 2.13 | 0.78 / 1.45 / 2.48 | 0.82 | 0.48 | 0.32 | 0.49 / 0.47 / 0.49 | 0.25 | -0.14 | 0.48 |
| exp17_citegraph:corroboration_weighted | 1.49 | 1.97 | 0.59 / 1.47 / 2.40 | 0.84 | 0.47 | 0.28 | 0.47 / 0.50 / 0.44 | -0.05 | -0.27 | 0.46 |
| exp17_citegraph:graph_profiles | 1.52 | 1.97 | 0.68 / 1.51 / 2.38 | 0.77 | 0.55 | 0.27 | 0.51 / 0.60 / 0.54 | 0.23 | -0.08 | 0.56 |
| exp17_citegraph:graph_profiles_systemmatch | 1.49 | 2.06 | 0.67 / 1.36 / 2.45 | 0.84 | 0.48 | 0.27 | 0.50 / 0.49 / 0.45 | 0.13 | -0.08 | 0.48 |
| exp17_citegraph:graph_selection | 1.52 | 1.91 | 0.62 / 1.47 / 2.48 | 0.86 | 0.54 | 0.22 | 0.46 / 0.60 / 0.54 | 0.25 | -0.18 | 0.54 |
| exp17_citegraph:graph_tool_agent | 1.52 | 1.98 | 0.72 / 1.47 / 2.38 | 0.84 | 0.46 | 0.12 | 0.41 / 0.44 / 0.54 | 0.20 | 0.07 | 0.45 |
| exp7_eval_v3:closed_book | 1.56 | - | 0.75 / 1.46 / 2.40 | 0.81 | 0.57 | - | 0.56 / 0.50 / 0.65 | 0.24 | 0.22 | 0.57 |
| exp7_eval_v3:text_oneshot | 1.56 | - | 0.79 / 1.52 / 2.38 | 0.79 | 0.43 | - | 0.42 / 0.48 / 0.40 | 0.29 | 0.20 | 0.44 |
| exp7_eval_v3:tool_agent | 1.64 | - | 0.79 / 1.65 / 2.48 | 0.77 | 0.40 | - | 0.44 / 0.38 / 0.40 | 0.14 | 0.37 | 0.40 |
| exp7_eval_v3:v2_oneshot | 1.49 | - | 0.73 / 1.44 / 2.29 | 0.78 | 0.41 | - | 0.38 / 0.44 / 0.42 | 0.35 | 0.06 | 0.42 |
| exp9_matkg:tool_agent_kg | 1.63 | - | 0.69 / 1.60 / 2.60 | 0.83 | 0.35 | - | 0.29 / 0.38 / 0.40 | 0.21 | -0.49 | 0.35 |

## Rerun paired comparisons, vs_text_chunks (GPT-5.6)

| a | b | units | diff | 95% CI | a higher | b higher | p | Holm p |
|---|---|---:|---:|---|---:|---:|---:|---:|
| exp14_rubrics:card | exp14_rubrics:text_chunks | 36 | 0.01 | [-0.08, 0.097] | 7 | 5 | 0.77 | 1.00 |
| exp14_rubrics:closed_book | exp14_rubrics:text_chunks | 36 | 0.13 | [0.024, 0.243] | 10 | 2 | 0.04 | 0.66 |
| exp14_rubrics:effects | exp14_rubrics:text_chunks | 36 | -0.01 | [-0.135, 0.146] | 4 | 7 | 0.55 | 1.00 |
| exp14_rubrics:gaps | exp14_rubrics:text_chunks | 36 | -0.02 | [-0.122, 0.069] | 5 | 5 | 1.00 | 1.00 |
| exp14_rubrics:mechanisms | exp14_rubrics:text_chunks | 36 | -0.04 | [-0.16, 0.035] | 5 | 3 | 0.73 | 1.00 |
| exp14_rubrics:mixed | exp14_rubrics:text_chunks | 36 | -0.07 | [-0.188, 0.031] | 4 | 4 | 1.00 | 1.00 |
| exp14_rubrics:v2_units | exp14_rubrics:text_chunks | 36 | -0.09 | [-0.17, -0.007] | 3 | 8 | 0.23 | 1.00 |
| exp16_improvements:card_systemmatch | exp14_rubrics:text_chunks | 36 | 0.02 | [-0.073, 0.128] | 6 | 5 | 1.00 | 1.00 |
| exp16_improvements:closed_book_fixed | exp14_rubrics:text_chunks | 36 | 0.06 | [-0.024, 0.149] | 8 | 3 | 0.23 | 1.00 |
| exp16_improvements:ensemble_select | exp14_rubrics:text_chunks | 36 | 0.07 | [0.0, 0.149] | 7 | 3 | 0.34 | 1.00 |
| exp16_improvements:knowledge_first | exp14_rubrics:text_chunks | 36 | 0.06 | [-0.035, 0.163] | 8 | 3 | 0.23 | 1.00 |
| exp16_improvements:text_systemmatch | exp14_rubrics:text_chunks | 36 | 0.01 | [-0.059, 0.094] | 7 | 4 | 0.55 | 1.00 |
| exp17_citegraph:corroboration_weighted | exp14_rubrics:text_chunks | 36 | 0.00 | [-0.115, 0.097] | 7 | 5 | 0.77 | 1.00 |
| exp17_citegraph:graph_profiles | exp14_rubrics:text_chunks | 36 | 0.08 | [-0.031, 0.181] | 10 | 2 | 0.04 | 0.66 |
| exp17_citegraph:graph_profiles_systemmatch | exp14_rubrics:text_chunks | 36 | 0.01 | [-0.087, 0.097] | 5 | 5 | 1.00 | 1.00 |
| exp17_citegraph:graph_selection | exp14_rubrics:text_chunks | 36 | 0.07 | [-0.066, 0.198] | 5 | 4 | 1.00 | 1.00 |
| exp17_citegraph:graph_tool_agent | exp14_rubrics:text_chunks | 36 | -0.01 | [-0.132, 0.097] | 8 | 4 | 0.39 | 1.00 |

## Rerun paired comparisons, agents_vs_closed_book_v3 (GPT-5.6)

| a | b | units | diff | 95% CI | a higher | b higher | p | Holm p |
|---|---|---:|---:|---|---:|---:|---:|---:|
| exp11_critique:critique | exp7_eval_v3:closed_book | 36 | -0.21 | [-0.326, -0.111] | 1 | 9 | 0.02 | - |
| exp11_critique:self_revise | exp7_eval_v3:closed_book | 36 | -0.19 | [-0.271, -0.097] | 1 | 10 | 0.01 | - |
| exp11_critique:tool_agent_resample | exp7_eval_v3:closed_book | 35 | -0.19 | [-0.306, -0.083] | 1 | 9 | 0.02 | - |
| exp7_eval_v3:text_oneshot | exp7_eval_v3:closed_book | 36 | -0.14 | [-0.278, 0.014] | 3 | 7 | 0.34 | - |
| exp7_eval_v3:tool_agent | exp7_eval_v3:closed_book | 36 | -0.17 | [-0.278, -0.056] | 2 | 9 | 0.07 | - |
| exp7_eval_v3:v2_oneshot | exp7_eval_v3:closed_book | 36 | -0.16 | [-0.271, -0.056] | 2 | 8 | 0.11 | - |
| exp9_matkg:tool_agent_kg | exp7_eval_v3:closed_book | 36 | -0.21 | [-0.312, -0.118] | 1 | 9 | 0.02 | - |

## Rerun paired comparisons, vs_closed_book_exp14 (GPT-5.6)

| a | b | units | diff | 95% CI | a higher | b higher | p | Holm p |
|---|---|---:|---:|---|---:|---:|---:|---:|
| exp14_rubrics:card | exp14_rubrics:closed_book | 36 | -0.12 | [-0.205, -0.049] | 2 | 9 | 0.07 | - |
| exp14_rubrics:effects | exp14_rubrics:closed_book | 36 | -0.14 | [-0.278, 0.014] | 2 | 10 | 0.04 | - |
| exp14_rubrics:gaps | exp14_rubrics:closed_book | 36 | -0.15 | [-0.257, -0.049] | 2 | 9 | 0.07 | - |
| exp14_rubrics:mechanisms | exp14_rubrics:closed_book | 36 | -0.18 | [-0.333, -0.045] | 2 | 10 | 0.04 | - |
| exp14_rubrics:mixed | exp14_rubrics:closed_book | 36 | -0.20 | [-0.333, -0.087] | 2 | 10 | 0.04 | - |
| exp14_rubrics:v2_units | exp14_rubrics:closed_book | 36 | -0.22 | [-0.34, -0.111] | 1 | 10 | 0.01 | - |
| exp16_improvements:card_systemmatch | exp14_rubrics:closed_book | 36 | -0.11 | [-0.212, 0.007] | 3 | 9 | 0.15 | - |
| exp16_improvements:closed_book_fixed | exp14_rubrics:closed_book | 36 | -0.07 | [-0.122, -0.024] | 1 | 8 | 0.04 | - |
| exp16_improvements:ensemble_select | exp14_rubrics:closed_book | 36 | -0.06 | [-0.128, 0.017] | 3 | 8 | 0.23 | - |
| exp16_improvements:knowledge_first | exp14_rubrics:closed_book | 36 | -0.07 | [-0.125, -0.014] | 2 | 8 | 0.11 | - |
| exp16_improvements:text_systemmatch | exp14_rubrics:closed_book | 36 | -0.12 | [-0.243, 0.01] | 3 | 9 | 0.15 | - |
| exp17_citegraph:corroboration_weighted | exp14_rubrics:closed_book | 36 | -0.13 | [-0.25, -0.028] | 3 | 9 | 0.15 | - |
| exp17_citegraph:graph_profiles | exp14_rubrics:closed_book | 36 | -0.05 | [-0.194, 0.094] | 4 | 7 | 0.55 | - |
| exp17_citegraph:graph_profiles_systemmatch | exp14_rubrics:closed_book | 36 | -0.12 | [-0.257, 0.007] | 3 | 8 | 0.23 | - |
| exp17_citegraph:graph_selection | exp14_rubrics:closed_book | 36 | -0.07 | [-0.236, 0.097] | 4 | 8 | 0.39 | - |
| exp17_citegraph:graph_tool_agent | exp14_rubrics:closed_book | 36 | -0.14 | [-0.253, -0.042] | 1 | 8 | 0.04 | - |

## Rerun paired comparisons, vs_text_chunks (DeepSeek-V4-Pro)

| a | b | units | diff | 95% CI | a higher | b higher | p | Holm p |
|---|---|---:|---:|---|---:|---:|---:|---:|
| exp14_rubrics:card | exp14_rubrics:text_chunks | 36 | -0.06 | [-0.188, 0.059] | 5 | 6 | 1.00 | 1.00 |
| exp14_rubrics:closed_book | exp14_rubrics:text_chunks | 36 | 0.02 | [-0.128, 0.153] | 7 | 4 | 0.55 | 1.00 |
| exp14_rubrics:effects | exp14_rubrics:text_chunks | 36 | -0.03 | [-0.181, 0.125] | 7 | 4 | 0.55 | 1.00 |
| exp14_rubrics:gaps | exp14_rubrics:text_chunks | 36 | -0.11 | [-0.215, -0.024] | 2 | 7 | 0.18 | 1.00 |
| exp14_rubrics:mechanisms | exp14_rubrics:text_chunks | 36 | -0.01 | [-0.115, 0.08] | 4 | 5 | 1.00 | 1.00 |
| exp14_rubrics:mixed | exp14_rubrics:text_chunks | 36 | -0.07 | [-0.184, 0.038] | 5 | 5 | 1.00 | 1.00 |
| exp14_rubrics:v2_units | exp14_rubrics:text_chunks | 36 | -0.10 | [-0.208, 0.0] | 2 | 8 | 0.11 | 1.00 |
| exp16_improvements:card_systemmatch | exp14_rubrics:text_chunks | 36 | -0.05 | [-0.191, 0.073] | 3 | 5 | 0.73 | 1.00 |
| exp16_improvements:closed_book_fixed | exp14_rubrics:text_chunks | 36 | 0.02 | [-0.087, 0.128] | 5 | 6 | 1.00 | 1.00 |
| exp16_improvements:ensemble_select | exp14_rubrics:text_chunks | 36 | 0.01 | [-0.104, 0.128] | 6 | 4 | 0.75 | 1.00 |
| exp16_improvements:knowledge_first | exp14_rubrics:text_chunks | 36 | -0.03 | [-0.128, 0.09] | 3 | 7 | 0.34 | 1.00 |
| exp16_improvements:text_systemmatch | exp14_rubrics:text_chunks | 36 | 0.06 | [-0.059, 0.205] | 4 | 5 | 1.00 | 1.00 |
| exp17_citegraph:corroboration_weighted | exp14_rubrics:text_chunks | 36 | 0.02 | [-0.056, 0.097] | 5 | 5 | 1.00 | 1.00 |
| exp17_citegraph:graph_profiles | exp14_rubrics:text_chunks | 36 | 0.01 | [-0.125, 0.153] | 7 | 5 | 0.77 | 1.00 |
| exp17_citegraph:graph_profiles_systemmatch | exp14_rubrics:text_chunks | 36 | 0.01 | [-0.097, 0.122] | 5 | 3 | 0.73 | 1.00 |
| exp17_citegraph:graph_selection | exp14_rubrics:text_chunks | 36 | -0.04 | [-0.135, 0.059] | 5 | 4 | 1.00 | 1.00 |
| exp17_citegraph:graph_tool_agent | exp14_rubrics:text_chunks | 36 | -0.13 | [-0.26, -0.014] | 4 | 7 | 0.55 | 1.00 |

## Rerun paired comparisons, agents_vs_closed_book_v3 (DeepSeek-V4-Pro)

| a | b | units | diff | 95% CI | a higher | b higher | p | Holm p |
|---|---|---:|---:|---|---:|---:|---:|---:|

## Rerun paired comparisons, vs_closed_book_exp14 (DeepSeek-V4-Pro)

| a | b | units | diff | 95% CI | a higher | b higher | p | Holm p |
|---|---|---:|---:|---|---:|---:|---:|---:|
| exp14_rubrics:card | exp14_rubrics:closed_book | 36 | -0.08 | [-0.222, 0.062] | 4 | 8 | 0.39 | - |
| exp14_rubrics:effects | exp14_rubrics:closed_book | 36 | -0.05 | [-0.188, 0.118] | 3 | 8 | 0.23 | - |
| exp14_rubrics:gaps | exp14_rubrics:closed_book | 36 | -0.13 | [-0.24, -0.035] | 2 | 9 | 0.07 | - |
| exp14_rubrics:mechanisms | exp14_rubrics:closed_book | 36 | -0.04 | [-0.201, 0.132] | 4 | 6 | 0.75 | - |
| exp14_rubrics:mixed | exp14_rubrics:closed_book | 36 | -0.09 | [-0.191, 0.007] | 4 | 6 | 0.75 | - |
| exp14_rubrics:v2_units | exp14_rubrics:closed_book | 36 | -0.12 | [-0.212, -0.035] | 2 | 8 | 0.11 | - |
| exp16_improvements:card_systemmatch | exp14_rubrics:closed_book | 36 | -0.07 | [-0.215, 0.087] | 2 | 9 | 0.07 | - |
| exp16_improvements:closed_book_fixed | exp14_rubrics:closed_book | 36 | -0.00 | [-0.076, 0.073] | 6 | 5 | 1.00 | - |
| exp16_improvements:ensemble_select | exp14_rubrics:closed_book | 36 | -0.01 | [-0.149, 0.118] | 3 | 5 | 0.73 | - |
| exp16_improvements:knowledge_first | exp14_rubrics:closed_book | 36 | -0.05 | [-0.153, 0.042] | 5 | 6 | 1.00 | - |
| exp16_improvements:text_systemmatch | exp14_rubrics:closed_book | 36 | 0.04 | [-0.146, 0.243] | 4 | 7 | 0.55 | - |
| exp17_citegraph:corroboration_weighted | exp14_rubrics:closed_book | 36 | 0.00 | [-0.108, 0.104] | 7 | 5 | 0.77 | - |
| exp17_citegraph:graph_profiles | exp14_rubrics:closed_book | 36 | -0.01 | [-0.149, 0.132] | 6 | 5 | 1.00 | - |
| exp17_citegraph:graph_profiles_systemmatch | exp14_rubrics:closed_book | 36 | -0.01 | [-0.177, 0.163] | 6 | 5 | 1.00 | - |
| exp17_citegraph:graph_selection | exp14_rubrics:closed_book | 36 | -0.06 | [-0.208, 0.094] | 4 | 8 | 0.39 | - |
| exp17_citegraph:graph_tool_agent | exp14_rubrics:closed_book | 36 | -0.15 | [-0.278, -0.049] | 1 | 9 | 0.02 | - |
