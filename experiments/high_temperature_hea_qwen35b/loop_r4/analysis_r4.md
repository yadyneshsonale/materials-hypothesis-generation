# Experiment 38: synthesis (round 4)

## Q1 (primary): each synthesis configuration vs the incumbent (original + fresh replicate)

| comparison | GPT-5.6 difference [CI] | DeepSeek difference [CI] | decision |
|---|---|---|---|
| synth_k4_b_o3mini vs incumbent (original + replicate) | -0.01 [-0.04, +0.02] (45 papers, 17/24, Holm p 1.0) | +0.02 [-0.02, +0.07] (45 papers, 25/15, Holm p 0.5052) | no detectable difference |
| synth_crowd_b_o3mini vs incumbent (original + replicate) | +0.01 [-0.02, +0.05] (45 papers, 22/20, Holm p 1.0) | -0.03 [-0.08, +0.02] (45 papers, 21/21, Holm p 1.0) | no detectable difference |
| synth_mixed_b_o3mini vs incumbent (original + replicate) | -0.00 [-0.05, +0.04] (45 papers, 18/24, Holm p 1.0) | +0.07 [-0.01, +0.14] (45 papers, 27/16, Holm p 0.5052) | no detectable difference |
| synth_k1_b_o3mini vs incumbent (original + replicate) | -0.04 [-0.07, -0.01] (45 papers, 14/28, Holm p 0.1744) | -0.00 [-0.05, +0.04] (45 papers, 25/19, Holm p 0.9028) | worse |

## Q2: ablations

| comparison | GPT-5.6 difference [CI] | DeepSeek difference [CI] | decision |
|---|---|---|---|
| synth_k4_b_o3mini vs synth_k1_b_o3mini | +0.03 [-0.01, +0.07] (45 papers, 26/14, Holm p 0.2421) | +0.03 [-0.02, +0.07] (45 papers, 20/19, Holm p 1.0) | no detectable difference |
| synth_crowd_b_o3mini vs synth_k4_b_o3mini | +0.02 [-0.02, +0.07] (45 papers, 22/16, Holm p 0.8354) | -0.05 [-0.11, +0.01] (45 papers, 12/27, Holm p 0.0948) | no detectable difference |
| synth_mixed_b_o3mini vs synth_k4_b_o3mini | +0.01 [-0.04, +0.06] (45 papers, 20/20, Holm p 1.0) | +0.04 [-0.04, +0.12] (45 papers, 23/19, Holm p 1.0) | no detectable difference |
| synth_k1_b_o3mini vs incumbent (original + replicate) | -0.04 [-0.07, -0.01] (45 papers, 14/28, Holm p 0.1744) | -0.00 [-0.05, +0.04] (45 papers, 25/19, Holm p 1.0) | worse |

## Noise floor: fresh replicate vs the original incumbent

| comparison | GPT-5.6 difference [CI] | DeepSeek difference [CI] | decision |
|---|---|---|---|
| writer_only_b_o3mini_r5 vs writer_only_b_o3mini | +0.02 [-0.02, +0.06] (45 papers, 21/18, Holm p 0.7493) | -0.01 [-0.07, +0.04] (45 papers, 16/22, Holm p 0.4177) | no detectable difference |

## Leaderboard (mean over papers)

| configuration | runs | failed | papers | GPT-5.6 | DeepSeek | lever ≥ 2 | class hit | complete chain | specificity | audited runs | hedges | unsupported | output chars | calls | input chars | seconds | draft failures |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| synth_crowd_b_o3mini | 270 | 0 | 45 | 0.645 | 0.542 | 0.207 | 0.419 | 0.761 | 0.265 | 142 | 0.074 | 0.77 | 2852.726 | 6.326 | 28158.844 | 64.545 | 0 |
| writer_only_b_o3mini_r5 | 270 | 0 | 45 | 0.639 | 0.561 | 0.178 | 0.4 | 0.841 | 0.325 | 270 | 0.107 | 0.774 | 3330.356 | 1.015 | 1861.133 | 10.216 | 0 |
| synth_mixed_b_o3mini | 270 | 0 | 45 | 0.629 | 0.633 | 0.226 | 0.381 | 0.653 | 0.299 | 147 | 0.141 | 0.567 | 3300.611 | 5.541 | 280907.548 | 66.061 | 3 |
| writer_only_b_o3mini | 270 | 0 | 45 | 0.623 | 0.575 | 0.189 | 0.404 | 0.837 | 0.306 | 270 | 0.115 | 0.726 | 3347.619 | 1.03 | 1899.959 | 10.459 | 0 |
| synth_k4_b_o3mini | 270 | 0 | 45 | 0.621 | 0.592 | 0.185 | 0.411 | 0.766 | 0.25 | 175 | 0.074 | 0.785 | 3172.333 | 5.267 | 26290.2 | 53.826 | 0 |
| synth_k1_b_o3mini | 270 | 0 | 45 | 0.591 | 0.566 | 0.189 | 0.374 | 0.772 | 0.242 | 267 | 0.07 | 0.778 | 2959.663 | 2.1 | 8045.689 | 18.682 | 0 |

## GPT-5.6 judge dimensions (0–4, mean over runs)

| configuration | problem_alignment | intervention_reconstruction | condition_agreement | mechanism_agreement | outcome_agreement | baseline_quality | boundary_quality | experiment_discriminability | evidence_validity | novelty |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| synth_crowd_b_o3mini | 2.615 | 0.315 | 0.622 | 0.741 | 0.904 | 1.504 | 1.307 | 2.278 | 0.07 | 1.352 |
| writer_only_b_o3mini_r5 | 2.689 | 0.3 | 0.656 | 0.707 | 0.893 | 1.47 | 1.419 | 2.419 | 0.067 | 1.563 |
| synth_mixed_b_o3mini | 2.585 | 0.341 | 0.641 | 0.689 | 0.844 | 1.496 | 1.422 | 2.496 | 1.004 | 1.689 |
| writer_only_b_o3mini | 2.641 | 0.315 | 0.578 | 0.748 | 0.852 | 1.419 | 1.348 | 2.356 | 0.056 | 1.556 |
| synth_k4_b_o3mini | 2.648 | 0.3 | 0.6 | 0.737 | 0.848 | 1.448 | 1.4 | 2.333 | 0.078 | 1.493 |
| synth_k1_b_o3mini | 2.604 | 0.281 | 0.563 | 0.696 | 0.822 | 1.437 | 1.289 | 2.315 | 0.052 | 1.526 |

## DeepSeek judge dimensions (0–4, mean over runs)

| configuration | problem_alignment | intervention_reconstruction | condition_agreement | mechanism_agreement | outcome_agreement | baseline_quality | boundary_quality | experiment_discriminability | evidence_validity | novelty |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| synth_crowd_b_o3mini | 1.611 | 0.363 | 0.659 | 0.507 | 0.637 | 1.448 | 1.237 | 1.285 | 0.178 | 1.022 |
| writer_only_b_o3mini_r5 | 1.652 | 0.426 | 0.648 | 0.541 | 0.63 | 1.526 | 1.326 | 1.411 | 0.196 | 1.278 |
| synth_mixed_b_o3mini | 1.648 | 0.474 | 0.726 | 0.607 | 0.726 | 1.604 | 1.344 | 1.411 | 1.167 | 1.374 |
| writer_only_b_o3mini | 1.604 | 0.448 | 0.656 | 0.548 | 0.648 | 1.522 | 1.267 | 1.4 | 0.193 | 1.207 |
| synth_k4_b_o3mini | 1.644 | 0.426 | 0.7 | 0.556 | 0.685 | 1.481 | 1.278 | 1.37 | 0.222 | 1.144 |
| synth_k1_b_o3mini | 1.611 | 0.437 | 0.659 | 0.541 | 0.626 | 1.422 | 1.196 | 1.315 | 0.211 | 1.148 |

## Draft agreement (gpt-4o-mini study-type labels of drafts and final, target-free)

| measure | `synth_k4_b_o3mini` | `synth_crowd_b_o3mini` | `synth_mixed_b_o3mini` | `synth_k1_b_o3mini` |
|---|---|---|---|---|
| runs | 270 | 270 | 270 | 270 |
| drafts_per_run | 4.0 | 5.0 | 3.99 | 1.0 |
| final_class_shared_by_2plus_drafts | 0.948 | 0.93 | 0.907 | 0.0 |
| final_class_is_modal_draft_class | 0.956 | 0.881 | 0.926 | 1.0 |
| drafts_unanimous | 0.552 | 0.348 | 0.459 | 1.0 |
| final_class_among_drafts | 1.0 | 1.0 | 0.989 | 1.0 |
| final_classes | {"composition_change": 0.337, "heat_or_thermomechanical_treatment": 0.322, "surface_or_coating": 0.148, "computational_method_development": 0.059, "processing_route": 0.059, "experimental_characterization_study": 0.056, "microstructure_architecture": 0.019} | {"composition_change": 0.426, "heat_or_thermomechanical_treatment": 0.256, "surface_or_coating": 0.111, "experimental_characterization_study": 0.067, "processing_route": 0.063, "computational_method_development": 0.059, "microstructure_architecture": 0.019} | {"composition_change": 0.33, "heat_or_thermomechanical_treatment": 0.33, "surface_or_coating": 0.13, "processing_route": 0.078, "experimental_characterization_study": 0.052, "computational_method_development": 0.048, "microstructure_architecture": 0.026, "simulation_study": 0.004, "other": 0.004} | {"composition_change": 0.348, "heat_or_thermomechanical_treatment": 0.307, "surface_or_coating": 0.156, "experimental_characterization_study": 0.059, "computational_method_development": 0.059, "processing_route": 0.056, "microstructure_architecture": 0.015} |
| draft_classes | {"composition_change": 0.355, "heat_or_thermomechanical_treatment": 0.318, "surface_or_coating": 0.131, "processing_route": 0.071, "computational_method_development": 0.056, "experimental_characterization_study": 0.051, "microstructure_architecture": 0.017, "simulation_study": 0.002} | {"composition_change": 0.466, "heat_or_thermomechanical_treatment": 0.216, "surface_or_coating": 0.101, "processing_route": 0.067, "experimental_characterization_study": 0.064, "computational_method_development": 0.056, "microstructure_architecture": 0.027, "other": 0.002, "simulation_study": 0.001} | {"composition_change": 0.359, "heat_or_thermomechanical_treatment": 0.299, "surface_or_coating": 0.12, "processing_route": 0.088, "experimental_characterization_study": 0.057, "computational_method_development": 0.051, "microstructure_architecture": 0.019, "simulation_study": 0.006, "other": 0.001} | {"composition_change": 0.348, "heat_or_thermomechanical_treatment": 0.307, "surface_or_coating": 0.156, "experimental_characterization_study": 0.059, "computational_method_development": 0.059, "processing_route": 0.056, "microstructure_architecture": 0.015} |

## Leakage

Counters over 1350 runs: {}; web records re-checked: 14658, date violations: 0, unresolved: 0.
