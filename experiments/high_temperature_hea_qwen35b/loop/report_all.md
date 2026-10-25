# Loop results (all)

| method | runs | failed | GPT-5.6 | DeepSeek | core GPT | core DS | broad / problem / expert | intervention | mechanism | outcome | problem align | lever>=2 | same class | specificity | hedges | novelty | calls/run |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| closed_book | 72 | 0 | 0.51 | 0.33 | 0.48 | 0.22 | 0.48 / 0.54 / 0.52 | 0.38 | 0.58 | 0.69 | 2.36 | 0.19 | 0.26 | 0.26 | 0.01 | 0.93 | 1.00 |
| closed_book_o3mini | 72 | 0 | 0.58 | 0.53 | 0.47 | 0.47 | 0.58 / 0.56 / 0.58 | 0.36 | 0.57 | 0.82 | 2.82 | 0.14 | 0.29 | 0.30 | 0.07 | 1.57 | 1.01 |
| scaffold_ensemble | 72 | 0 | 0.55 | 0.35 | 0.55 | 0.27 | 0.48 / 0.67 / 0.51 | 0.36 | 0.74 | 0.72 | 2.28 | 0.24 | 0.28 | 0.27 | 0.03 | 0.90 | 16.01 |
| text_chunks | 72 | 0 | 0.41 | 0.26 | 0.36 | 0.20 | 0.38 / 0.49 / 0.35 | 0.19 | 0.53 | 0.53 | 2.01 | 0.17 | 0.28 | 0.18 | 0.03 | 0.90 | 1.00 |
| trend_ground_b_o3mini | 72 | 0 | 0.70 | 0.71 | 0.60 | 0.65 | 0.65 / 0.71 / 0.75 | 0.38 | 0.82 | 0.92 | 2.83 | 0.18 | 0.31 | 0.34 | 0.11 | 1.99 | 3.11 |
| writer_only_b_o3mini | 72 | 0 | 0.62 | 0.62 | 0.54 | 0.55 | 0.52 / 0.64 / 0.70 | 0.38 | 0.71 | 0.85 | 2.88 | 0.14 | 0.26 | 0.32 | 0.12 | 1.58 | 1.00 |

## vs closed_book (GPT-5.6)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|
| closed_book_o3mini | 36 | 0.06 | [-0.031, 0.156] | 7 | 3 | 0.34 | 0.69 |
| scaffold_ensemble | 36 | 0.04 | [-0.052, 0.135] | 6 | 5 | 1.00 | 1.00 |
| text_chunks | 36 | -0.11 | [-0.278, 0.052] | 3 | 8 | 0.23 | 0.68 |
| trend_ground_b_o3mini | 36 | 0.19 | [0.108, 0.267] | 11 | 1 | 0.01 | 0.03 |
| writer_only_b_o3mini | 36 | 0.10 | [0.01, 0.191] | 9 | 2 | 0.07 | 0.26 |

## vs text_chunks (GPT-5.6)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|
| closed_book | 36 | 0.11 | [-0.052, 0.278] | 8 | 3 | 0.23 | 0.45 |
| closed_book_o3mini | 36 | 0.17 | [0.031, 0.337] | 10 | 2 | 0.04 | 0.15 |
| scaffold_ensemble | 36 | 0.15 | [-0.003, 0.309] | 7 | 4 | 0.55 | 0.55 |
| trend_ground_b_o3mini | 36 | 0.29 | [0.156, 0.462] | 10 | 1 | 0.01 | 0.06 |
| writer_only_b_o3mini | 36 | 0.21 | [0.08, 0.347] | 9 | 3 | 0.15 | 0.44 |

## vs closed_book (DeepSeek)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|
| closed_book_o3mini | 36 | 0.20 | [0.062, 0.344] | 9 | 3 | 0.15 | 0.44 |
| scaffold_ensemble | 36 | 0.02 | [-0.031, 0.073] | 6 | 3 | 0.51 | 0.51 |
| text_chunks | 36 | -0.07 | [-0.194, 0.049] | 2 | 7 | 0.18 | 0.44 |
| trend_ground_b_o3mini | 36 | 0.39 | [0.219, 0.549] | 11 | 1 | 0.01 | 0.03 |
| writer_only_b_o3mini | 36 | 0.29 | [0.163, 0.441] | 11 | 1 | 0.01 | 0.03 |

## vs text_chunks (DeepSeek)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|
| closed_book | 36 | 0.07 | [-0.049, 0.194] | 7 | 2 | 0.18 | 0.29 |
| closed_book_o3mini | 36 | 0.27 | [0.083, 0.479] | 9 | 3 | 0.15 | 0.29 |
| scaffold_ensemble | 36 | 0.09 | [-0.052, 0.229] | 8 | 1 | 0.04 | 0.19 |
| trend_ground_b_o3mini | 36 | 0.46 | [0.226, 0.694] | 10 | 2 | 0.04 | 0.19 |
| writer_only_b_o3mini | 36 | 0.36 | [0.135, 0.615] | 10 | 2 | 0.04 | 0.19 |

## vs closed_book (GPT-5.6, core)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|
| closed_book_o3mini | 36 | -0.01 | [-0.139, 0.104] | 6 | 5 | 1.00 | 1.00 |
| scaffold_ensemble | 36 | 0.07 | [-0.035, 0.181] | 6 | 4 | 0.75 | 1.00 |
| text_chunks | 36 | -0.12 | [-0.333, 0.111] | 3 | 7 | 0.34 | 1.00 |
| trend_ground_b_o3mini | 36 | 0.12 | [-0.007, 0.236] | 9 | 3 | 0.15 | 0.73 |
| writer_only_b_o3mini | 36 | 0.06 | [-0.021, 0.139] | 9 | 3 | 0.15 | 0.73 |

## vs text_chunks (GPT-5.6, core)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|
| closed_book | 36 | 0.12 | [-0.111, 0.333] | 7 | 3 | 0.34 | 0.69 |
| closed_book_o3mini | 36 | 0.10 | [-0.083, 0.312] | 6 | 3 | 0.51 | 0.69 |
| scaffold_ensemble | 36 | 0.19 | [-0.007, 0.396] | 7 | 2 | 0.18 | 0.54 |
| trend_ground_b_o3mini | 36 | 0.24 | [0.049, 0.458] | 9 | 2 | 0.07 | 0.33 |
| writer_only_b_o3mini | 36 | 0.18 | [-0.021, 0.375] | 9 | 2 | 0.07 | 0.33 |

## vs closed_book (DeepSeek, core)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|
| closed_book_o3mini | 36 | 0.25 | [0.104, 0.41] | 10 | 2 | 0.04 | 0.12 |
| scaffold_ensemble | 36 | 0.05 | [-0.007, 0.097] | 6 | 1 | 0.12 | 0.25 |
| text_chunks | 36 | -0.02 | [-0.167, 0.146] | 1 | 3 | 0.62 | 0.62 |
| trend_ground_b_o3mini | 36 | 0.42 | [0.215, 0.618] | 11 | 1 | 0.01 | 0.03 |
| writer_only_b_o3mini | 36 | 0.33 | [0.181, 0.493] | 11 | 1 | 0.01 | 0.03 |

## vs text_chunks (DeepSeek, core)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|
| closed_book | 36 | 0.02 | [-0.146, 0.167] | 3 | 1 | 0.62 | 0.62 |
| closed_book_o3mini | 36 | 0.27 | [0.049, 0.5] | 9 | 2 | 0.07 | 0.15 |
| scaffold_ensemble | 36 | 0.07 | [-0.139, 0.229] | 8 | 1 | 0.04 | 0.15 |
| trend_ground_b_o3mini | 36 | 0.44 | [0.181, 0.708] | 10 | 2 | 0.04 | 0.15 |
| writer_only_b_o3mini | 36 | 0.35 | [0.083, 0.625] | 10 | 1 | 0.01 | 0.06 |
