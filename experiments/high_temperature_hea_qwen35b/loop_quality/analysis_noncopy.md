# Experiment 47: non-copying replaces grounding

Pre-registered in loop.md 27.5. Non-copying (1-5, DeepSeek, one call) judges whether a hypothesis goes beyond the earlier literature (every passage the focused-retrieval writer was given for the question) or copies it. SP2 = mean(plausibility, testability, usefulness, non-copying) - 1, on 0-4. **The metric is not validated** (the user chose no validation controls).

| | Non-copying (1–5) | Distribution 1/2/3/4/5 | Overall idea from: passages / general knowledge / new | SP2 | SP with grounding (exp. 46) | RQ |
|---|---:|---|---|---:|---:|---:|
| `rx_r` (270 of 270) | 1.89 | 150/57/12/45/6 | 237 / 7 / 26 | 2.50 | 2.65 | 3.03 |
| `writer_only_b_o3mini` (270 of 270) | 3.12 | 93/10/8/91/68 | 73 / 40 / 157 | 2.85 | 2.33 | 3.10 |

- Non-copying, `rx_r` minus the writer (paired by paper): -1.23 [-1.49, -0.96], 3 vs 41 papers, p 0.0
- SP2, `rx_r` minus the writer: -0.36 [-0.47, -0.25], 8 vs 37 papers, p 0.0

## Pairwise v2: `rx_r` vs the closed-book writer (both orders; a win needs both)

- deepseek: +0.56 [+0.48, +0.64], 42 vs 1 papers, p 0.0; pairs 270, rx_r wins 0.574, writer wins 0.011
- gpt56: +0.34 [+0.20, +0.47], 35 vs 8 papers, p 0.0; pairs 270, rx_r wins 0.578, writer wins 0.241

For comparison, the experiment-46 prompt (criterion 4 = well grounded):
- deepseek: +0.50 [+0.41, +0.58], 41 vs 2 papers, p 0.0
- gpt56: +0.54 [+0.43, +0.65], 40 vs 3 papers, p 0.0
- o1: +0.59 [+0.51, +0.66], 44 vs 1 papers, p 0.0

## Examples (lowest and highest scores)

- `rx_r` PMC10759803__broad__rx_r__s1 — **1**: Incorporate a trace level (on the order of 0.1–0.5 atomic %) of boron into the alloy composition. *Judge:* The hypothesis directly restates the finding reported in P1, which explicitly states that Wang et al. strengthened the grain boundary of MoNbTaW by doping with trace B or C, increasing room-temperature strength and toughness. The proposed intervention, mechanism, and material are identical to this p
- `rx_r` PMC10759803__broad__rx_r__s2 — **1**: Introduce a modest (~15 vol%) addition of Al2O3 ceramic particles during powder metallurgy processing (e.g., mechanical alloying followed by spark plasma sintering). *Judge:* The hypothesis directly restates the exact material, intervention, mechanism, and quantitative results already reported in P4, P16, and P17, presenting a prior experimental finding as a prediction without adding any new alloy, regime, mechanism, or integrative insight.
- `rx_r` PMC10920630__expert_context__rx_r__s1 — **5**: Expose identical samples to controlled salt spray or aggressive salt environments at room temperature versus high-temperature regimes (700–900 °C) under otherwise identical cyclic conditions. *Judge:* The hypothesis proposes a novel mechanistic contrast between room-temperature and high-temperature (700–900 °C) behavior of the same pre-passivated Q235 steel, linking thermal stress and chloride mobility to film embrittlement and a protective-to-porous oxide transition. None of the passages study t
- `rx_r` PMC11375216__problem_constrained__rx_r__s1 — **5**: Implement a predictive approach (e.g., integrating ab initio–informed machine-learning interatomic potentials with defect scattering models) that includes the effects of dislocations, oxygen-induced l *Judge:* The hypothesis proposes a new predictive framework that integrates defect-inclusive modeling (oxygen impurities, dislocations, lattice distortions) with machine-learning potentials to predict electrical conductivity of HfNbTaTiZr, a property and material combination not addressed in any passage. Whi
- `writer_only_b_o3mini` PMC10759803__expert_context__writer_only_b_o3mini__s2 — **1**: Replace a portion of the heavy Hf by increasing the Zr content (i.e., forming a (Hf_xZr_1-x)MoTaTiZr alloy) to lower the overall density while retaining similar phase stability and solid solution stre *Judge:* The hypothesis directly restates the known effect from P5 that adding Zr decreases density and elevated-temperature strength, and applies the well-known chemical similarity of Hf and Zr (P14) to propose a partial substitution in the same alloy system already studied, without combining findings from 
- `writer_only_b_o3mini` PMC10759803__problem_constrained__writer_only_b_o3mini__s1 — **1**: Replace Ta with an equivalent atomic fraction of Nb so that the alloy becomes HfMoNbTiZr. *Judge:* The hypothesis directly restates the known result from P6 and P21 that removing Ta (i.e., forming HfMoNbTiZr) reduces density while retaining strength, and it proposes exactly the alloy that P8 and P19 already studied, without adding any new mechanistic insight, combination of sources, or transfer t
- `writer_only_b_o3mini` PMC10759803__broad__writer_only_b_o3mini__s2 — **5**: Introduce a controlled, minor hafnium addition (0.5–1 at%) during alloy synthesis followed by a heat-treatment schedule optimized to foster in-situ HfC nanoprecipitation. *Judge:* The hypothesis proposes a specific, non-trivial intervention—minor Hf addition to a MoNbTaW-based RHEA to form HfC nanoprecipitates—that is not reported, suggested as future work, or directly implied by any single passage or combination of passages. While precipitation strengthening is a general con
- `writer_only_b_o3mini` PMC11087546__expert_context__writer_only_b_o3mini__s1 — **5**: Addition of a small amount of a microalloying element (e.g., Nb) during alloy preparation followed by a controlled post-casting heat-treatment to promote interfacial segregation. *Judge:* The hypothesis proposes a specific, non-trivial intervention—microalloying to segregate at and reinforce lamellar interfaces—to solve the documented problem of microcrack initiation in EHEAs. No passage suggests this exact approach; P9 observes a natural Cr segregation zone but does not propose engi
