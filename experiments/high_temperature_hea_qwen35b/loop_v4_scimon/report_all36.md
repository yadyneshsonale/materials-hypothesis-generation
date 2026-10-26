# Loop results (all36)

| method | runs | failed | GPT-5.6 | DeepSeek | core GPT | core DS | broad / problem / expert | intervention | mechanism | outcome | problem align | lever>=2 | same class | specificity | hedges | novelty | calls/run |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| closed_book | 72 | 0 | 0.47 | 0.19 | 0.46 | 0.16 | 0.47 | 0.43 | 0.49 | 0.75 | 1.78 | 0.21 | 0.49 | 0.07 | 0.01 | 0.29 | 1.00 |
| closed_book_o3mini | 72 | 0 | 0.66 | 0.31 | 0.58 | 0.24 | 0.66 | 0.43 | 0.72 | 0.97 | 2.38 | 0.25 | 0.54 | 0.11 | 0.08 | 1.28 | 1.01 |
| text_chunks_b_o3mini | 72 | 0 | 0.59 | 0.44 | 0.54 | 0.40 | 0.59 | 0.43 | 0.65 | 0.86 | 2.33 | 0.21 | 0.46 | 0.21 | 0.12 | 1.47 | 1.06 |
| writer_only_b_o3mini | 72 | 0 | 0.69 | 0.42 | 0.65 | 0.39 | 0.69 | 0.53 | 0.76 | 0.99 | 2.44 | 0.26 | 0.60 | 0.12 | 0.03 | 1.07 | 1.00 |

## vs closed_book (GPT-5.6)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|
| closed_book_o3mini | 36 | 0.18 | [0.052, 0.326] | 17 | 9 | 0.17 | 0.22 |
| text_chunks_b_o3mini | 36 | 0.12 | [-0.031, 0.274] | 21 | 11 | 0.11 | 0.22 |
| writer_only_b_o3mini | 36 | 0.22 | [0.08, 0.382] | 19 | 8 | 0.05 | 0.16 |

## vs text_chunks (GPT-5.6)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|

## vs closed_book (DeepSeek)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|
| closed_book_o3mini | 36 | 0.12 | [-0.01, 0.257] | 14 | 10 | 0.54 | 0.54 |
| text_chunks_b_o3mini | 36 | 0.25 | [0.101, 0.396] | 22 | 6 | 0.00 | 0.01 |
| writer_only_b_o3mini | 36 | 0.23 | [0.094, 0.385] | 19 | 6 | 0.01 | 0.03 |

## vs text_chunks (DeepSeek)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|

## vs closed_book (GPT-5.6, core)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|
| closed_book_o3mini | 36 | 0.12 | [-0.049, 0.306] | 14 | 10 | 0.54 | 0.54 |
| text_chunks_b_o3mini | 36 | 0.08 | [-0.097, 0.271] | 17 | 10 | 0.25 | 0.50 |
| writer_only_b_o3mini | 36 | 0.19 | [-0.007, 0.41] | 16 | 8 | 0.15 | 0.45 |

## vs text_chunks (GPT-5.6, core)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|

## vs closed_book (DeepSeek, core)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|
| closed_book_o3mini | 36 | 0.08 | [-0.042, 0.215] | 11 | 6 | 0.33 | 0.33 |
| text_chunks_b_o3mini | 36 | 0.24 | [0.076, 0.417] | 17 | 4 | 0.01 | 0.02 |
| writer_only_b_o3mini | 36 | 0.23 | [0.076, 0.41] | 15 | 3 | 0.01 | 0.02 |

## vs text_chunks (DeepSeek, core)

| method | units | diff | 95% CI | up | down | p | Holm p |
|---|---:|---:|---|---:|---:|---:|---:|
