# Experiment 45: a lever-preserving editor (E) and the programme's domain (D)

Pre-registered in loop.md 26.1. GPT-5.6 reconstruction decides (CI above 0 and DeepSeek above 0); DeepSeek, research quality (RQ, mean of three DeepSeek calls) and target-free pairwise quality alongside. Questions naming the alloy class: 91; not naming it: 44. D and D+E are composed: the base (or E) where the question names the class, the new arm elsewhere.

## Runs

| arm | ok | failed | failed attempts | DeepSeek judged | GPT-5.6 judged | audits | calls incl. stage 1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| domain_rx_base | 88 | 0 | 0 | 88 | 17 | 0 | 1.00 |
| domain_rx_r | 88 | 0 | 0 | 88 | 8 | 0 | 1.00 |
| edit_rx_base | 270 | 0 | 0 | 270 | 45 | 0 | 2.04 |
| edit_rx_r | 270 | 0 | 0 | 270 | 50 | 0 | 2.04 |
| domain_edit_rx_base | 88 | 0 | 0 | 88 | 16 | 0 | 2.09 |
| domain_edit_rx_r | 88 | 0 | 0 | 88 | 14 | 0 | 2.01 |

## Base `rx_base` (primary)

| variant | GPT-5.6 mean | DeepSeek mean | RQ (3 calls) | GPT-5.6 vs base | DeepSeek vs base | RQ vs base | decision |
|---|---:|---:|---:|---|---|---|---|
| base | 0.629 | 0.630 | 3.051 | – | – | – | – |
| E | 0.610 | 0.645 | 3.043 | -0.132 [-0.24, -0.03], 3/9 papers, p 0.146, Holm 0.438 | +0.016 [-0.03, +0.06], 19/18 papers, p 1.0, Holm 1.0 | -0.008 [-0.06, +0.05], 17/27 papers, p 0.1742, Holm 0.3484 | no detectable difference |
| D | 0.701 | 0.645 | 3.051 | -0.001 [-0.04, +0.04], 2/3 papers, p 1.0, Holm 1.0 | +0.016 [-0.02, +0.05], 11/7 papers, p 0.4807, Holm 0.9614 | +0.000 [-0.03, +0.03], 11/12 papers, p 1.0, Holm 1.0 | no detectable difference |
| DE | 0.620 | 0.697 | 3.016 | -0.086 [-0.20, +0.04], 3/8 papers, p 0.2266, Holm 0.4532 | +0.068 [+0.01, +0.12], 24/14 papers, p 0.1433, Holm 0.4299 | -0.035 [-0.10, +0.03], 15/29 papers, p 0.0488, Holm 0.1464 | no detectable difference |

On the questions that do not name the alloy class:

| contrast | GPT-5.6 | DeepSeek |
|---|---|---|
| D_vs_base | -0.089 [-0.38, +0.20], 2/3 papers, p 1.0 | +0.022 [-0.10, +0.14], 11/7 papers, p 0.4807 |
| DE_vs_base | +0.000 [-0.38, +0.38], 1/1 papers, p 1.0 | +0.113 [-0.01, +0.24], 13/6 papers, p 0.1671 |
| DE_vs_E | +0.000 [-0.25, +0.25], 1/1 papers, p 1.0 | +0.103 [-0.02, +0.22], 14/5 papers, p 0.0636 |

Dimensions (GPT-5.6 / DeepSeek):

| variant | intervention | conditions | mechanism | outcome |
|---|---|---|---|---|
| base | 0.25 / 0.48 | 0.63 / 0.73 | 0.67 / 0.60 | 0.95 / 0.70 |
| E | 0.36 / 0.53 | 0.56 / 0.72 | 0.78 / 0.61 | 0.98 / 0.73 |
| D | 0.30 / 0.51 | 0.69 / 0.74 | 0.72 / 0.62 | 0.95 / 0.71 |
| DE | 0.33 / 0.58 | 0.57 / 0.76 | 0.76 / 0.66 | 0.96 / 0.79 |

Edit diagnostics:

```
{
 "E": {
  "runs": 270,
  "calls": {
   "1 call(s), applied=True": 258,
   "2 call(s), applied=True": 7,
   "2 call(s), applied=False": 5
  },
  "fields_changed": {
   "hypothesis": 0.948,
   "intervention": 0.596,
   "conditions": 0.719,
   "mechanism": 0.77,
   "structural_mediator": 0.381
  },
  "invented_numbers_share": {
   "before": {
    "intervention": 0.263,
    "conditions": 0.4,
    "structural_mediator": 0.033
   },
   "after": {
    "intervention": 0.022,
    "conditions": 0.026,
    "structural_mediator": 0.019
   }
  },
  "mechanism_names_mpea_effect": {
   "before": 0.189,
   "after": 0.407
  },
  "hypothesis_states_causal_link": {
   "before": 0.552,
   "after": 0.9
  },
  "words": {
   "hypothesis": [
    50.2,
    57.1
   ],
   "intervention": [
    28.2,
    27.7
   ],
   "conditions": [
    31.0,
    29.1
   ],
   "structural_mediator": [
    23.5,
    23.3
   ],
   "mechanism": [
    51.6,
    47.8
   ],
   "predicted_outcome": [
    42.8,
    42.8
   ]
  },
  "words_total": [
   227.4,
   227.8
  ]
 },
 "DE": {
  "runs": 88,
  "calls": {
   "1 call(s), applied=True": 80,
   "2 call(s), applied=True": 6,
   "2 call(s), applied=False": 2
  },
  "fields_changed": {
   "hypothesis": 0.875,
   "mechanism": 0.795,
   "conditions": 0.648,
   "intervention": 0.545,
   "structural_mediator": 0.523
  },
  "invented_numbers_share": {
   "before": {
    "intervention": 0.205,
    "conditions": 0.364,
    "structural_mediator": 0.045
   },
   "after": {
    "intervention": 0.023,
    "conditions": 0.023,
    "structural_mediator": 0.023
   }
  },
  "mechanism_names_mpea_effect": {
   "before": 0.136,
   "after": 0.364
  },
  "hypothesis_states_causal_link": {
   "before": 0.534,
   "after": 0.909
  },
  "words": {
   "hypothesis": [
    47.3,
    54.9
   ],
   "intervention": [
    28.0,
    27.5
   ],
   "conditions": [
    30.7,
    29.2
   ],
   "structural_mediator": [
    24.1,
    23.8
   ],
   "mechanism": [
    49.6,
    47.6
   ],
   "predicted_outcome": [
    40.5,
    40.5
   ]
  },
  "words_total": [
   220.2,
   223.4
  ]
 }
}
```
Domain diagnostics:

```
{
 "base": {
  "runs": 88,
  "brings_in_alloy_class": 0.307
 },
 "D": {
  "runs": 88,
  "brings_in_alloy_class": 0.341
 }
}
```

## Base `rx_r` (secondary)

| variant | GPT-5.6 mean | DeepSeek mean | RQ (3 calls) | GPT-5.6 vs base | DeepSeek vs base | RQ vs base | decision |
|---|---:|---:|---:|---|---|---|---|
| base | 0.620 | 0.662 | 3.034 | – | – | – | – |
| E | 0.538 | 0.645 | 2.976 | +0.016 [-0.10, +0.10], 7/3 papers, p 0.3438, Holm 1.0 | -0.017 [-0.07, +0.03], 17/19 papers, p 0.8679, Holm 1.0 | -0.058 [-0.11, -0.00], 18/27 papers, p 0.2327, Holm 0.4654 | no detectable difference |
| D | 0.632 | 0.673 | 3.039 | -0.011 [-0.03, +0.00], 1/3 papers, p 0.625, Holm 1.0 | +0.011 [-0.03, +0.05], 9/10 papers, p 1.0, Holm 1.0 | +0.005 [-0.04, +0.05], 12/11 papers, p 1.0, Holm 1.0 | no detectable difference |
| DE | 0.525 | 0.656 | 2.960 | +0.039 [-0.04, +0.11], 8/4 papers, p 0.3877, Holm 1.0 | -0.006 [-0.07, +0.05], 18/20 papers, p 0.8714, Holm 1.0 | -0.074 [-0.14, -0.01], 17/28 papers, p 0.1352, Holm 0.4056 | no detectable difference |

On the questions that do not name the alloy class:

| contrast | GPT-5.6 | DeepSeek |
|---|---|---|
| D_vs_base | -0.250 [-0.62, +0.12], 1/3 papers, p 0.625 | +0.057 [-0.06, +0.18], 9/10 papers, p 1.0 |
| DE_vs_base | +0.042 [-0.12, +0.21], 3/2 papers, p 1.0 | +0.065 [-0.04, +0.17], 10/6 papers, p 0.4545 |
| DE_vs_E | +0.000 [-0.19, +0.19], 1/1 papers, p 1.0 | -0.005 [-0.09, +0.09], 8/8 papers, p 1.0 |

Dimensions (GPT-5.6 / DeepSeek):

| variant | intervention | conditions | mechanism | outcome |
|---|---|---|---|---|
| base | 0.26 / 0.51 | 0.68 / 0.78 | 0.68 / 0.64 | 0.92 / 0.72 |
| E | 0.14 / 0.50 | 0.66 / 0.79 | 0.64 / 0.57 | 0.80 / 0.72 |
| D | 0.31 / 0.54 | 0.70 / 0.79 | 0.68 / 0.65 | 0.89 / 0.72 |
| DE | 0.17 / 0.53 | 0.65 / 0.77 | 0.62 / 0.60 | 0.75 / 0.72 |

Edit diagnostics:

```
{
 "E": {
  "runs": 270,
  "calls": {
   "1 call(s), applied=True": 260,
   "2 call(s), applied=True": 4,
   "2 call(s), applied=False": 6
  },
  "fields_changed": {
   "hypothesis": 0.937,
   "intervention": 0.552,
   "conditions": 0.748,
   "structural_mediator": 0.389,
   "mechanism": 0.741
  },
  "invented_numbers_share": {
   "before": {
    "intervention": 0.207,
    "conditions": 0.363,
    "structural_mediator": 0.026
   },
   "after": {
    "intervention": 0.056,
    "conditions": 0.019,
    "structural_mediator": 0.019
   }
  },
  "mechanism_names_mpea_effect": {
   "before": 0.174,
   "after": 0.359
  },
  "hypothesis_states_causal_link": {
   "before": 0.533,
   "after": 0.922
  },
  "words": {
   "hypothesis": [
    52.2,
    59.3
   ],
   "intervention": [
    27.4,
    26.9
   ],
   "conditions": [
    32.4,
    30.6
   ],
   "structural_mediator": [
    24.1,
    23.9
   ],
   "mechanism": [
    54.8,
    50.9
   ],
   "predicted_outcome": [
    43.5,
    43.5
   ]
  },
  "words_total": [
   234.4,
   235.2
  ]
 },
 "DE": {
  "runs": 88,
  "calls": {
   "1 call(s), applied=True": 87,
   "2 call(s), applied=True": 1
  },
  "fields_changed": {
   "hypothesis": 0.977,
   "intervention": 0.625,
   "conditions": 0.739,
   "mechanism": 0.784,
   "structural_mediator": 0.409
  },
  "invented_numbers_share": {
   "before": {
    "intervention": 0.193,
    "conditions": 0.375,
    "structural_mediator": 0.023
   },
   "after": {
    "intervention": 0.011,
    "conditions": 0.0,
    "structural_mediator": 0.011
   }
  },
  "mechanism_names_mpea_effect": {
   "before": 0.17,
   "after": 0.409
  },
  "hypothesis_states_causal_link": {
   "before": 0.477,
   "after": 0.92
  },
  "words": {
   "hypothesis": [
    48.3,
    57.0
   ],
   "intervention": [
    28.8,
    28.4
   ],
   "conditions": [
    32.0,
    30.4
   ],
   "structural_mediator": [
    24.1,
    23.8
   ],
   "mechanism": [
    51.6,
    48.0
   ],
   "predicted_outcome": [
    43.0,
    43.0
   ]
  },
  "words_total": [
   227.8,
   230.6
  ]
 }
}
```
Domain diagnostics:

```
{
 "base": {
  "runs": 88,
  "brings_in_alloy_class": 0.239
 },
 "D": {
  "runs": 88,
  "brings_in_alloy_class": 0.352
 }
}
```

## Target-free pairwise quality (net preference for the variant; both orders must agree)

- deepseek, E vs rx_base: -0.267 [-0.32, -0.21], 0/36 papers, p 0.0, Holm 0.0; pairs 270, variant wins 0.004, base wins 0.27
- deepseek, D vs rx_base: +0.007 [-0.12, +0.15], 5/8 papers, p 0.5811, Holm 0.5811; pairs 88, variant wins 0.114, base wins 0.17
- deepseek, DE vs rx_base: -0.259 [-0.32, -0.20], 1/38 papers, p 0.0, Holm 0.0; pairs 270, variant wins 0.03, base wins 0.289
- deepseek, E vs rx_r: -0.296 [-0.36, -0.24], 0/39 papers, p 0.0, Holm 0.0; pairs 270, variant wins 0.015, base wins 0.311
- deepseek, D vs rx_r: +0.062 [-0.04, +0.17], 6/6 papers, p 1.0, Holm 1.0; pairs 88, variant wins 0.114, base wins 0.091
- deepseek, DE vs rx_r: -0.248 [-0.31, -0.19], 1/35 papers, p 0.0, Holm 0.0; pairs 270, variant wins 0.03, base wins 0.278
- o1, E vs rx_base: -0.037 [-0.10, +0.02], 10/20 papers, p 0.0987, Holm 0.2961; pairs 270, variant wins 0.07, base wins 0.107
- o1, D vs rx_base: +0.036 [-0.14, +0.22], 7/8 papers, p 1.0, Holm 1.0; pairs 88, variant wins 0.205, base wins 0.227
- o1, DE vs rx_base: -0.053 [-0.12, +0.01], 10/20 papers, p 0.0987, Holm 0.2961; pairs 256, variant wins 0.102, base wins 0.148

## Leakage

{"counters": {"temporal_violations": 0, "test_paper_leaks": 0, "family_leaks": 0, "target_doi_or_title_leaks": 0, "invalid_citations": 0}, "records_rechecked": 40718, "date_violations": 0}
