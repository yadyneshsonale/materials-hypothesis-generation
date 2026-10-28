# Experiment 37: propose, critique, decide

## Q1 (primary): full system (web at every role) vs the baselines

| comparison | GPT-5.6 difference [CI] | DeepSeek difference [CI] | decision |
|---|---|---|---|
| pcd_PCD_o3mini vs writer_only_b_o3mini | -0.12 [-0.17, -0.07] (45 papers, Holm p 0.003) | -0.21 [-0.31, -0.12] (45 papers, Holm p 0.0345) | worse |
| pcd_PCD_o3mini vs closed_book_o3mini | -0.09 [-0.14, -0.04] (45 papers, Holm p 0.0136) | -0.14 [-0.23, -0.05] (45 papers, Holm p 0.132) | worse |
| pcd_PCD_o3mini vs closed_book | -0.00 [-0.05, +0.05] (45 papers, Holm p 0.8679) | +0.06 [-0.01, +0.12] (45 papers, Holm p 0.1641) | no detectable difference |
| pcd_PCD_o3mini vs web_text_chunks_b_o3mini | -0.11 [-0.17, -0.06] (45 papers, Holm p 0.0136) | -0.25 [-0.34, -0.15] (45 papers, Holm p 0.0) | worse |
| pcd_PCD_o3mini vs web_agent_o3mini | -0.06 [-0.10, -0.02] (45 papers, Holm p 0.1066) | -0.19 [-0.27, -0.11] (45 papers, Holm p 0.0012) | worse |
| pcd_PCD_o3mini vs web_text_64k_b_o3mini | -0.14 [-0.20, -0.08] (45 papers, Holm p 0.0012) | -0.29 [-0.38, -0.20] (45 papers, Holm p 0.0) | worse |

## Q2: the framework without web

| comparison | GPT-5.6 difference [CI] | DeepSeek difference [CI] | decision |
|---|---|---|---|
| pcd_none_o3mini vs writer_only_b_o3mini | -0.15 [-0.21, -0.10] (45 papers, Holm p 0.0) | -0.23 [-0.31, -0.15] (45 papers, Holm p 0.0) | worse |
| pcd_none_o3mini vs closed_book_o3mini | -0.12 [-0.17, -0.07] (45 papers, Holm p 0.0025) | -0.16 [-0.23, -0.08] (45 papers, Holm p 0.0004) | worse |

## Q3: web evidence at each role (main effects over the 8-cell grid)

| role | GPT-5.6 with − without [CI] | DeepSeek [CI] |
|---|---|---|
| web at P | +0.01 [-0.02, +0.04] (45 papers, Holm p 0.8804) | -0.02 [-0.06, +0.02] (45 papers, Holm p 1.0) |
| web at C | -0.01 [-0.04, +0.01] (45 papers, Holm p 0.56) | -0.02 [-0.05, +0.01] (45 papers, Holm p 1.0) |
| web at D | +0.03 [+0.01, +0.05] (45 papers, Holm p 0.3789) | +0.04 [+0.01, +0.08] (45 papers, Holm p 1.0) |

Cell means (GPT-5.6): {"none": 0.469, "P": 0.498, "C": 0.48, "D": 0.5, "PC": 0.46, "PD": 0.524, "CD": 0.503, "PCD": 0.5}
Cell means (DeepSeek): {"none": 0.346, "P": 0.352, "C": 0.356, "D": 0.388, "PC": 0.295, "PD": 0.383, "CD": 0.386, "PCD": 0.363}

## Q3: each grid cell vs no web

| comparison | GPT-5.6 difference [CI] | DeepSeek difference [CI] | decision |
|---|---|---|---|
| pcd_P_o3mini vs pcd_none_o3mini | +0.03 [-0.02, +0.08] (45 papers, Holm p 1.0) | +0.01 [-0.06, +0.07] (45 papers, Holm p 1.0) | no detectable difference |
| pcd_C_o3mini vs pcd_none_o3mini | +0.01 [-0.03, +0.06] (45 papers, Holm p 1.0) | +0.01 [-0.05, +0.06] (45 papers, Holm p 1.0) | no detectable difference |
| pcd_D_o3mini vs pcd_none_o3mini | +0.03 [-0.01, +0.07] (45 papers, Holm p 1.0) | +0.04 [-0.02, +0.11] (45 papers, Holm p 1.0) | no detectable difference |
| pcd_PC_o3mini vs pcd_none_o3mini | -0.01 [-0.06, +0.04] (45 papers, Holm p 1.0) | -0.05 [-0.12, +0.01] (45 papers, Holm p 0.2016) | no detectable difference |
| pcd_PD_o3mini vs pcd_none_o3mini | +0.06 [+0.00, +0.11] (45 papers, Holm p 1.0) | +0.04 [-0.03, +0.11] (45 papers, Holm p 0.8598) | no detectable difference |
| pcd_CD_o3mini vs pcd_none_o3mini | +0.03 [-0.01, +0.07] (45 papers, Holm p 0.2352) | +0.04 [-0.02, +0.10] (45 papers, Holm p 1.0) | no detectable difference |
| pcd_PCD_o3mini vs pcd_none_o3mini | +0.03 [-0.02, +0.08] (45 papers, Holm p 1.0) | +0.02 [-0.05, +0.08] (45 papers, Holm p 1.0) | no detectable difference |

## Q4: each agent's contribution (full minus ablation)

| comparison | GPT-5.6 difference [CI] | DeepSeek difference [CI] | decision |
|---|---|---|---|
| pcd_none_o3mini vs pcd_nocritic_none_o3mini | -0.01 [-0.05, +0.03] (45 papers, Holm p 1.0) | +0.02 [-0.05, +0.08] (45 papers, Holm p 1.0) | no detectable difference |
| pcd_none_o3mini vs pcd_nodecider_none_o3mini | -0.04 [-0.09, +0.01] (45 papers, Holm p 1.0) | -0.03 [-0.10, +0.04] (45 papers, Holm p 1.0) | no detectable difference |
| pcd_none_o3mini vs pcd_k1_none_o3mini | -0.06 [-0.12, -0.01] (45 papers, Holm p 0.8598) | -0.08 [-0.16, +0.00] (45 papers, Holm p 1.0) | worse |
| pcd_PCD_o3mini vs pcd_nocritic_PCD_o3mini | +0.02 [-0.02, +0.06] (45 papers, Holm p 1.0) | -0.02 [-0.09, +0.05] (45 papers, Holm p 1.0) | no detectable difference |
| pcd_PCD_o3mini vs pcd_nodecider_PCD_o3mini | -0.02 [-0.06, +0.02] (45 papers, Holm p 1.0) | -0.10 [-0.17, -0.04] (45 papers, Holm p 0.069) | no detectable difference |
| pcd_PCD_o3mini vs pcd_k1_PCD_o3mini | -0.00 [-0.03, +0.03] (45 papers, Holm p 1.0) | -0.12 [-0.18, -0.06] (45 papers, Holm p 0.0975) | no detectable difference |

## Q5: Llama-3.3 in every role

| comparison | GPT-5.6 difference [CI] | DeepSeek difference [CI] | decision |
|---|---|---|---|
| pcd_none_llama vs closed_book | -0.08 [-0.13, -0.03] (45 papers, Holm p 0.0498) | -0.11 [-0.16, -0.06] (45 papers, Holm p 0.0172) | worse |
| pcd_PCD_llama vs closed_book | -0.11 [-0.16, -0.04] (45 papers, Holm p 0.0116) | -0.06 [-0.13, +0.00] (45 papers, Holm p 0.0172) | worse |
| pcd_PCD_llama vs web_text_chunks | -0.10 [-0.17, -0.05] (45 papers, Holm p 0.1922) | -0.08 [-0.15, -0.02] (45 papers, Holm p 0.0332) | worse |
| pcd_PCD_llama vs web_agent | -0.02 [-0.07, +0.03] (45 papers, Holm p 1.0) | +0.01 [-0.06, +0.09] (45 papers, Holm p 1.0) | no detectable difference |

## Q6: coverage and selection (idea labels: every proposed idea and the final hypothesis)

| measure | `pcd_none_o3mini` | `pcd_PCD_o3mini` |
|---|---|---|
| runs | 270 | 270 |
| proposal_recall_any_idea_lever_ge2 | 0.367 | 0.4 |
| final_lever_ge2 | 0.148 | 0.148 |
| selection_given_recall_final_ge2 | 0.394 | 0.352 |
| selection_given_recall_chosen_idea_ge2 | 0.394 | 0.37 |
| decider_chose_proposers_first_idea | 0.474 | 0.441 |
| decision_modes | {"adopt_with_fix": 258, "merge": 9, "adopt": 3} | {"adopt_with_fix": 246, "adopt": 16, "merge": 8} |
| distinct_intervention_classes_per_run | 2.522 | 2.641 |
| critic_verdicts_on_matching_ideas | {"viable_with_changes": 111, "strong": 6, "weak": 8} | {"viable_with_changes": 105, "weak": 16, "strong": 15} |
| critic_verdicts_on_other_ideas | {"weak": 132, "viable_with_changes": 732, "strong": 37} | {"viable_with_changes": 752, "strong": 61, "weak": 125} |

## Leaderboard (mean over papers)

| configuration | runs | failed | papers | GPT-5.6 | DeepSeek | complete chain | specificity | hedges | calls | input chars | seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| web_text_64k_b_o3mini | 270 | 0 | 45 | 0.636 | 0.656 | 0.693 | 0.405 | 0.104 | 1.256 | 94561.144 | 17.857 |
| writer_only_b_o3mini | 270 | 0 | 45 | 0.623 | 0.575 | 0.837 | 0.306 | 0.115 | 1.03 | 1899.959 | 10.459 |
| web_text_chunks_b_o3mini | 270 | 0 | 45 | 0.607 | 0.61 | 0.678 | 0.37 | 0.185 | 1.193 | 24202.937 | 15.024 |
| closed_book_o3mini | 270 | 0 | 45 | 0.591 | 0.503 | 0.83 | 0.273 | 0.059 | 1.011 | 1564.548 | 10.92 |
| web_agent_o3mini | 270 | 0 | 45 | 0.559 | 0.555 | 0.659 | 0.381 | 0.056 | 6.222 | 64200.796 | 74.511 |
| pcd_k1_none_o3mini | 270 | 0 | 45 | 0.532 | 0.425 | 0.822 | 0.577 | 0.126 | 3.015 | 13026.204 | 30.378 |
| pcd_PD_o3mini | 270 | 0 | 45 | 0.524 | 0.383 | 0.674 | 0.526 | 0.1 | 3.13 | 63869.826 | 50.026 |
| pcd_nodecider_PCD_o3mini | 270 | 0 | 45 | 0.52 | 0.464 | 0.648 | 0.533 | 0.093 | 3.211 | 73466.611 | 49.492 |
| pcd_nodecider_none_o3mini | 270 | 0 | 45 | 0.509 | 0.378 | 0.774 | 0.523 | 0.044 | 3.085 | 15026.607 | 39.175 |
| pcd_k1_PCD_o3mini | 270 | 0 | 45 | 0.504 | 0.486 | 0.707 | 0.591 | 0.141 | 3.193 | 71441.785 | 39.463 |
| pcd_CD_o3mini | 270 | 0 | 45 | 0.503 | 0.386 | 0.696 | 0.509 | 0.085 | 3.174 | 66366.53 | 49.418 |
| closed_book | 270 | 0 | 45 | 0.502 | 0.306 | 0.289 | 0.268 | 0.033 | 1.0 | 792.511 | 9.328 |
| web_text_chunks | 270 | 0 | 45 | 0.501 | 0.326 | 0.104 | 0.169 | 0.03 | 1.0 | 19263.193 | 29.98 |
| pcd_D_o3mini | 270 | 0 | 45 | 0.5 | 0.388 | 0.774 | 0.535 | 0.115 | 3.122 | 46090.178 | 47.658 |
| pcd_PCD_o3mini | 270 | 0 | 45 | 0.5 | 0.363 | 0.667 | 0.506 | 0.133 | 3.115 | 82125.252 | 50.994 |
| pcd_P_o3mini | 270 | 0 | 45 | 0.498 | 0.352 | 0.8 | 0.52 | 0.133 | 3.041 | 41975.644 | 47.073 |
| pcd_nocritic_PCD_o3mini | 270 | 0 | 45 | 0.481 | 0.385 | 0.656 | 0.527 | 0.104 | 2.215 | 51500.644 | 39.937 |
| pcd_C_o3mini | 270 | 0 | 45 | 0.48 | 0.356 | 0.83 | 0.506 | 0.085 | 3.907 | 54827.585 | 57.426 |
| pcd_nocritic_none_o3mini | 270 | 0 | 45 | 0.477 | 0.33 | 0.789 | 0.509 | 0.07 | 2.007 | 10240.233 | 30.509 |
| pcd_none_o3mini | 270 | 0 | 45 | 0.469 | 0.346 | 0.785 | 0.5 | 0.081 | 3.037 | 23820.911 | 42.521 |
| pcd_PC_o3mini | 270 | 0 | 45 | 0.46 | 0.295 | 0.752 | 0.464 | 0.089 | 3.941 | 73539.941 | 61.409 |
| pcd_none_llama | 270 | 0 | 45 | 0.42 | 0.197 | 0.33 | 0.54 | 0.03 | 3.052 | 19797.244 | 42.662 |
| web_agent | 270 | 0 | 45 | 0.419 | 0.231 | 0.152 | 0.27 | 0.022 | 10.156 | 177063.485 | 116.285 |
| pcd_PCD_llama | 270 | 0 | 45 | 0.396 | 0.244 | 0.07 | 0.258 | 0.03 | 3.063 | 72818.893 | 42.68 |

## Secondary: GPT-5.6 judge dimensions (0–4, mean over runs)

| configuration | problem | interv. | cond. | mech. | outcome | baseline | boundary | experiment | evidence | novelty |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| web_text_64k_b_o3mini | 2.637 | 0.319 | 0.67 | 0.696 | 0.859 | 1.504 | 1.47 | 2.448 | 1.096 | 1.796 |
| writer_only_b_o3mini | 2.641 | 0.315 | 0.578 | 0.748 | 0.852 | 1.419 | 1.348 | 2.356 | 0.056 | 1.556 |
| web_text_chunks_b_o3mini | 2.607 | 0.285 | 0.626 | 0.67 | 0.848 | 1.581 | 1.43 | 2.5 | 1.193 | 1.781 |
| closed_book_o3mini | 2.578 | 0.296 | 0.567 | 0.641 | 0.859 | 1.47 | 1.37 | 2.344 | 0.189 | 1.593 |
| web_agent_o3mini | 2.626 | 0.211 | 0.526 | 0.644 | 0.856 | 1.652 | 1.552 | 2.478 | 1.211 | 1.863 |
| pcd_k1_none_o3mini | 2.652 | 0.156 | 0.533 | 0.644 | 0.796 | 1.604 | 1.593 | 2.4 | 0.056 | 2.07 |
| pcd_PD_o3mini | 2.593 | 0.137 | 0.515 | 0.663 | 0.781 | 1.604 | 1.607 | 2.507 | 0.952 | 2.107 |
| pcd_nodecider_PCD_o3mini | 2.507 | 0.17 | 0.5 | 0.615 | 0.796 | 1.652 | 1.485 | 2.47 | 0.963 | 2.044 |
| pcd_nodecider_none_o3mini | 2.607 | 0.167 | 0.463 | 0.611 | 0.796 | 1.663 | 1.556 | 2.4 | 0.037 | 1.863 |
| pcd_k1_PCD_o3mini | 2.674 | 0.13 | 0.522 | 0.604 | 0.759 | 1.607 | 1.556 | 2.496 | 0.993 | 2.241 |
| pcd_CD_o3mini | 2.537 | 0.122 | 0.5 | 0.619 | 0.77 | 1.63 | 1.544 | 2.459 | 0.785 | 2.048 |
| closed_book | 2.163 | 0.267 | 0.396 | 0.604 | 0.741 | 1.167 | 0.763 | 1.456 | 0.011 | 0.9 |
| web_text_chunks | 2.0 | 0.267 | 0.419 | 0.559 | 0.759 | 1.081 | 0.63 | 1.374 | 1.207 | 0.911 |
| pcd_D_o3mini | 2.548 | 0.111 | 0.467 | 0.648 | 0.774 | 1.633 | 1.537 | 2.541 | 0.767 | 2.085 |
| pcd_PCD_o3mini | 2.467 | 0.119 | 0.47 | 0.589 | 0.822 | 1.563 | 1.526 | 2.526 | 0.941 | 2.048 |
| pcd_P_o3mini | 2.544 | 0.137 | 0.493 | 0.607 | 0.756 | 1.511 | 1.53 | 2.422 | 0.041 | 2.111 |
| pcd_nocritic_PCD_o3mini | 2.507 | 0.096 | 0.507 | 0.593 | 0.73 | 1.73 | 1.581 | 2.544 | 1.015 | 2.126 |
| pcd_C_o3mini | 2.541 | 0.119 | 0.463 | 0.589 | 0.748 | 1.578 | 1.507 | 2.385 | 0.026 | 1.963 |
| pcd_nocritic_none_o3mini | 2.57 | 0.067 | 0.467 | 0.581 | 0.793 | 1.596 | 1.474 | 2.4 | 0.052 | 1.974 |
| pcd_none_o3mini | 2.489 | 0.078 | 0.463 | 0.581 | 0.756 | 1.581 | 1.526 | 2.389 | 0.044 | 1.993 |
| pcd_PC_o3mini | 2.448 | 0.115 | 0.448 | 0.522 | 0.756 | 1.585 | 1.47 | 2.37 | 0.041 | 2.122 |
| pcd_none_llama | 2.115 | 0.122 | 0.333 | 0.567 | 0.659 | 1.381 | 0.867 | 1.544 | 0.0 | 1.415 |
| web_agent | 1.9 | 0.152 | 0.374 | 0.437 | 0.715 | 1.207 | 0.756 | 1.467 | 1.289 | 1.181 |
| pcd_PCD_llama | 1.848 | 0.185 | 0.326 | 0.43 | 0.644 | 1.141 | 0.619 | 1.278 | 1.107 | 1.096 |

## Secondary: DeepSeek judge dimensions (0–4, mean over runs)

| configuration | problem | interv. | cond. | mech. | outcome | baseline | boundary | experiment | evidence | novelty |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| web_text_64k_b_o3mini | 1.641 | 0.53 | 0.774 | 0.589 | 0.73 | 1.637 | 1.43 | 1.519 | 1.285 | 1.496 |
| writer_only_b_o3mini | 1.604 | 0.448 | 0.656 | 0.548 | 0.648 | 1.522 | 1.267 | 1.4 | 0.193 | 1.207 |
| web_text_chunks_b_o3mini | 1.633 | 0.489 | 0.719 | 0.559 | 0.674 | 1.578 | 1.344 | 1.385 | 1.259 | 1.463 |
| closed_book_o3mini | 1.563 | 0.367 | 0.615 | 0.481 | 0.548 | 1.5 | 1.296 | 1.352 | 0.178 | 1.267 |
| web_agent_o3mini | 1.593 | 0.437 | 0.633 | 0.522 | 0.626 | 1.578 | 1.33 | 1.419 | 1.274 | 1.385 |
| pcd_k1_none_o3mini | 1.485 | 0.319 | 0.467 | 0.441 | 0.474 | 1.519 | 1.341 | 1.467 | 0.285 | 1.444 |
| pcd_PD_o3mini | 1.359 | 0.263 | 0.415 | 0.381 | 0.474 | 1.537 | 1.326 | 1.315 | 1.174 | 1.53 |
| pcd_nodecider_PCD_o3mini | 1.411 | 0.348 | 0.493 | 0.481 | 0.533 | 1.526 | 1.311 | 1.378 | 1.211 | 1.419 |
| pcd_nodecider_none_o3mini | 1.415 | 0.267 | 0.426 | 0.381 | 0.437 | 1.444 | 1.3 | 1.433 | 0.163 | 1.241 |
| pcd_k1_PCD_o3mini | 1.519 | 0.367 | 0.541 | 0.507 | 0.53 | 1.648 | 1.4 | 1.515 | 1.374 | 1.656 |
| pcd_CD_o3mini | 1.359 | 0.285 | 0.444 | 0.381 | 0.433 | 1.522 | 1.304 | 1.348 | 0.952 | 1.441 |
| closed_book | 1.052 | 0.148 | 0.337 | 0.274 | 0.467 | 0.911 | 0.667 | 0.537 | 0.004 | 0.459 |
| web_text_chunks | 1.089 | 0.156 | 0.359 | 0.296 | 0.493 | 0.963 | 0.685 | 0.393 | 0.978 | 0.444 |
| pcd_D_o3mini | 1.374 | 0.281 | 0.433 | 0.381 | 0.456 | 1.544 | 1.311 | 1.33 | 0.922 | 1.441 |
| pcd_PCD_o3mini | 1.319 | 0.267 | 0.393 | 0.381 | 0.411 | 1.474 | 1.278 | 1.326 | 1.211 | 1.363 |
| pcd_P_o3mini | 1.381 | 0.237 | 0.396 | 0.359 | 0.415 | 1.459 | 1.274 | 1.381 | 0.222 | 1.341 |
| pcd_nocritic_PCD_o3mini | 1.352 | 0.27 | 0.396 | 0.393 | 0.481 | 1.493 | 1.3 | 1.341 | 1.256 | 1.437 |
| pcd_C_o3mini | 1.419 | 0.252 | 0.404 | 0.356 | 0.411 | 1.448 | 1.296 | 1.359 | 0.211 | 1.359 |
| pcd_nocritic_none_o3mini | 1.389 | 0.215 | 0.374 | 0.319 | 0.411 | 1.419 | 1.241 | 1.322 | 0.174 | 1.389 |
| pcd_none_o3mini | 1.381 | 0.23 | 0.389 | 0.359 | 0.407 | 1.467 | 1.307 | 1.378 | 0.207 | 1.307 |
| pcd_PC_o3mini | 1.344 | 0.207 | 0.319 | 0.278 | 0.378 | 1.411 | 1.259 | 1.307 | 0.144 | 1.385 |
| pcd_none_llama | 1.056 | 0.081 | 0.233 | 0.207 | 0.267 | 0.952 | 0.778 | 0.552 | 0.004 | 0.674 |
| web_agent | 1.011 | 0.141 | 0.233 | 0.207 | 0.341 | 0.963 | 0.715 | 0.5 | 0.915 | 0.526 |
| pcd_PCD_llama | 0.93 | 0.152 | 0.252 | 0.219 | 0.352 | 0.889 | 0.596 | 0.326 | 0.863 | 0.407 |

## Secondary: classification, length, lever labels

Unsupported: share of runs the GPT-5.6 judge classes as unsupported. Output: characters in the final hypothesis's text fields. Lever ≥ 2: share of labelled runs (standard labels) whose intervention matches the paper's lever.

| configuration | unsupported | output chars | lever ≥ 2 | labelled runs | audited runs |
|---|---:|---:|---:|---:|---:|
| web_text_64k_b_o3mini | 0.47 | 3601.63 | None | 0 | 270 |
| writer_only_b_o3mini | 0.726 | 3347.619 | 0.189 | 270 | 270 |
| web_text_chunks_b_o3mini | 0.459 | 3513.685 | 0.207 | 270 | 270 |
| closed_book_o3mini | 0.789 | 3246.726 | 0.229 | 144 | 270 |
| web_agent_o3mini | 0.452 | 3389.878 | 0.159 | 270 | 270 |
| pcd_k1_none_o3mini | 0.807 | 3870.056 | None | 0 | 270 |
| pcd_PD_o3mini | 0.619 | 3639.4 | None | 0 | 270 |
| pcd_nodecider_PCD_o3mini | 0.656 | 3254.041 | None | 0 | 270 |
| pcd_nodecider_none_o3mini | 0.83 | 3135.304 | None | 0 | 270 |
| pcd_k1_PCD_o3mini | 0.611 | 3947.83 | None | 0 | 270 |
| pcd_CD_o3mini | 0.67 | 3548.619 | None | 0 | 270 |
| closed_book | 0.915 | 1393.281 | 0.167 | 270 | 270 |
| web_text_chunks | 0.652 | 1445.7 | 0.193 | 270 | 270 |
| pcd_D_o3mini | 0.656 | 3608.637 | None | 0 | 270 |
| pcd_PCD_o3mini | 0.622 | 3591.752 | 0.115 | 270 | 270 |
| pcd_P_o3mini | 0.856 | 3531.593 | None | 0 | 270 |
| pcd_nocritic_PCD_o3mini | 0.633 | 3503.47 | None | 0 | 270 |
| pcd_C_o3mini | 0.848 | 3319.696 | None | 0 | 270 |
| pcd_nocritic_none_o3mini | 0.87 | 3367.348 | None | 0 | 270 |
| pcd_none_o3mini | 0.848 | 3492.57 | 0.13 | 270 | 270 |
| pcd_PC_o3mini | 0.848 | 3330.948 | None | 0 | 270 |
| pcd_none_llama | 0.937 | 1735.419 | None | 0 | 270 |
| web_agent | 0.626 | 1444.107 | 0.2 | 270 | 270 |
| pcd_PCD_llama | 0.752 | 1365.059 | None | 0 | 270 |

## Leakage

Counters over 4320 runs: {}; web records re-checked: 60141, date violations: 0, unresolved: 0.
