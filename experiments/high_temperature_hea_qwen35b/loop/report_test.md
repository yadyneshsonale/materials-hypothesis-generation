# Loop results (test)

| method | runs | failed | GPT-5.6 | DeepSeek | core GPT | core DS | broad / problem / expert | intervention | mechanism | outcome | problem align | lever>=2 | same class | specificity | hedges | novelty | calls/run |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| closed_book | 24 | 0 | 0.52 | 0.35 | 0.58 | 0.25 | 0.53 / 0.38 / 0.66 | 0.46 | 0.71 | 0.71 | 1.88 | 0.21 | 0.29 | 0.28 | 0.00 | 0.67 | 1.00 |
| closed_book_o3mini | 24 | 0 | 0.47 | 0.53 | 0.46 | 0.54 | 0.59 / 0.38 / 0.44 | 0.46 | 0.46 | 0.67 | 2.38 | 0.08 | 0.12 | 0.17 | 0.21 | 1.54 | 1.00 |
| scaffold_ensemble | 24 | 0 | 0.43 | 0.40 | 0.52 | 0.35 | 0.41 / 0.47 / 0.41 | 0.29 | 0.75 | 0.58 | 1.88 | 0.21 | 0.29 | 0.30 | 0.00 | 0.71 | 16.00 |
| text_chunks | 24 | 0 | 0.36 | 0.26 | 0.44 | 0.25 | 0.38 / 0.44 / 0.28 | 0.25 | 0.62 | 0.42 | 1.75 | 0.12 | 0.21 | 0.14 | 0.04 | 0.75 | 1.00 |
| trend_ground_b_o3mini | 24 | 0 | 0.65 | 0.88 | 0.60 | 0.85 | 0.69 / 0.50 / 0.75 | 0.38 | 0.83 | 0.88 | 2.58 | 0.17 | 0.17 | 0.24 | 0.08 | 2.08 | 3.08 |
| writer_only_b_o3mini | 24 | 0 | 0.52 | 0.69 | 0.58 | 0.65 | 0.59 / 0.25 / 0.72 | 0.46 | 0.71 | 0.71 | 2.42 | 0.12 | 0.17 | 0.19 | 0.21 | 1.79 | 1.00 |

## vs closed_book (GPT-5.6)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|
| closed_book_o3mini | 12 | -0.05 | [-0.188, 0.031] | 1 | 1 | 1.00 | 1.00 |
| scaffold_ensemble | 12 | -0.09 | [-0.177, -0.0] | 1 | 3 | 0.62 | 1.00 |
| text_chunks | 12 | -0.16 | [-0.25, -0.094] | 0 | 4 | 0.12 | 0.62 |
| trend_ground_b_o3mini | 12 | 0.12 | [0.042, 0.229] | 4 | 0 | 0.12 | 0.62 |
| writer_only_b_o3mini | 12 | -0.00 | [-0.177, 0.135] | 3 | 1 | 0.62 | 1.00 |

## vs text_chunks (GPT-5.6)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|
| closed_book | 12 | 0.16 | [0.094, 0.25] | 4 | 0 | 0.12 | 0.62 |
| closed_book_o3mini | 12 | 0.10 | [-0.052, 0.24] | 3 | 1 | 0.62 | 1.00 |
| scaffold_ensemble | 12 | 0.06 | [-0.042, 0.167] | 2 | 1 | 1.00 | 1.00 |
| trend_ground_b_o3mini | 12 | 0.28 | [0.208, 0.354] | 4 | 0 | 0.12 | 0.62 |
| writer_only_b_o3mini | 12 | 0.16 | [-0.021, 0.312] | 3 | 1 | 0.62 | 1.00 |

## vs closed_book (DeepSeek)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|
| closed_book_o3mini | 12 | 0.18 | [-0.125, 0.521] | 2 | 2 | 1.00 | 1.00 |
| scaffold_ensemble | 12 | 0.04 | [-0.104, 0.167] | 3 | 1 | 0.62 | 1.00 |
| text_chunks | 12 | -0.09 | [-0.167, -0.021] | 0 | 3 | 0.25 | 0.75 |
| trend_ground_b_o3mini | 12 | 0.52 | [0.302, 0.844] | 4 | 0 | 0.12 | 0.62 |
| writer_only_b_o3mini | 12 | 0.33 | [0.125, 0.594] | 4 | 0 | 0.12 | 0.62 |

## vs text_chunks (DeepSeek)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|
| closed_book | 12 | 0.09 | [0.021, 0.167] | 3 | 0 | 0.25 | 0.75 |
| closed_book_o3mini | 12 | 0.27 | [-0.083, 0.688] | 3 | 1 | 0.62 | 0.75 |
| scaffold_ensemble | 12 | 0.14 | [0.021, 0.302] | 3 | 0 | 0.25 | 0.75 |
| trend_ground_b_o3mini | 12 | 0.61 | [0.333, 0.979] | 4 | 0 | 0.12 | 0.62 |
| writer_only_b_o3mini | 12 | 0.43 | [0.188, 0.76] | 4 | 0 | 0.12 | 0.62 |

## vs closed_book (GPT-5.6, core)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|
| closed_book_o3mini | 12 | -0.12 | [-0.271, 0.021] | 1 | 3 | 0.62 | 1.00 |
| scaffold_ensemble | 12 | -0.06 | [-0.188, 0.042] | 1 | 2 | 1.00 | 1.00 |
| text_chunks | 12 | -0.15 | [-0.271, -0.042] | 0 | 3 | 0.25 | 1.00 |
| trend_ground_b_o3mini | 12 | 0.02 | [-0.167, 0.208] | 2 | 2 | 1.00 | 1.00 |
| writer_only_b_o3mini | 12 | -0.00 | [-0.167, 0.083] | 3 | 1 | 0.62 | 1.00 |

## vs text_chunks (GPT-5.6, core)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|
| closed_book | 12 | 0.15 | [0.042, 0.271] | 3 | 0 | 0.25 | 1.00 |
| closed_book_o3mini | 12 | 0.02 | [-0.188, 0.292] | 1 | 2 | 1.00 | 1.00 |
| scaffold_ensemble | 12 | 0.08 | [0.0, 0.188] | 2 | 0 | 0.50 | 1.00 |
| trend_ground_b_o3mini | 12 | 0.17 | [0.0, 0.292] | 3 | 1 | 0.62 | 1.00 |
| writer_only_b_o3mini | 12 | 0.15 | [-0.062, 0.333] | 3 | 1 | 0.62 | 1.00 |

## vs closed_book (DeepSeek, core)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|
| closed_book_o3mini | 12 | 0.29 | [-0.042, 0.667] | 3 | 1 | 0.62 | 1.00 |
| scaffold_ensemble | 12 | 0.10 | [0.042, 0.167] | 3 | 0 | 0.25 | 0.75 |
| text_chunks | 12 | 0.00 | [0.0, 0.0] | 0 | 0 | 1.00 | 1.00 |
| trend_ground_b_o3mini | 12 | 0.60 | [0.333, 0.917] | 4 | 0 | 0.12 | 0.62 |
| writer_only_b_o3mini | 12 | 0.40 | [0.208, 0.646] | 4 | 0 | 0.12 | 0.62 |

## vs text_chunks (DeepSeek, core)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|
| closed_book | 12 | 0.00 | [0.0, 0.0] | 0 | 0 | 1.00 | 1.00 |
| closed_book_o3mini | 12 | 0.29 | [-0.042, 0.667] | 3 | 1 | 0.62 | 1.00 |
| scaffold_ensemble | 12 | 0.10 | [0.042, 0.167] | 3 | 0 | 0.25 | 0.75 |
| trend_ground_b_o3mini | 12 | 0.60 | [0.333, 0.917] | 4 | 0 | 0.12 | 0.62 |
| writer_only_b_o3mini | 12 | 0.40 | [0.208, 0.646] | 4 | 0 | 0.12 | 0.62 |
