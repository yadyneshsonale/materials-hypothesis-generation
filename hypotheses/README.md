# Hypotheses for the 45 test papers

Outputs of the per-paper generate → critique → narrow method (loop.md sections 28.1–28.3) for every paper in [`test/`](../test/), with the same numbering. One run (sample 1) per research question; each paper has three questions (levels `broad`, `problem_constrained`, `expert_context`). No agent ever saw the target paper: all evidence was published before the knowledge cutoff, and every run's leakage audit is stored.

## Files in each folder

| File | Content |
|---|---|
| `paper.pdf` | The target paper (for reading; never shown to any agent). |
| `question.json` | The three research questions and the knowledge cutoff (keys explained in [test/README.md](../test/README.md)). |
| `internal_reasoning.json` | Every step, per question level: the 10 retrieved papers; for each paper its background passages (teaching texts and MatKG facts), every round's hypotheses and the critic's notes on the paper (what it did, reported, proposed) and critique (pass/fail with reasons for `sound`, `testable` and `beyond_paper`, a quote and a fix); the outcome (accepted in round k, or dropped); the tournament's matches with both orders' reasons; cost and leakage audit. These are the agents' written outputs; o3-mini's hidden reasoning tokens are not available. |
| `hypotheses.json` | Every accepted hypothesis (near-duplicates merged), in tournament order (ranks 1–5 from the final round robin, the rest by Swiss-round points), each with its source paper, the round it was accepted in, what it builds on and what is new. |
| `final_hypothesis.json` | The method's answer per level: `final_hypothesis` (rank 1), the ranked `top3`, whether rank 1 was tied, and the text of the passages it cites. |

Each hypothesis has the shared fields: `hypothesis`, `material_initial_state`, `intervention`, `conditions`, `structural_mediator`, `mechanism`, `predicted_outcome`, `baseline`, `boundary`, `uncertainty`, `supporting_evidence_ids`, `conflicting_evidence_ids` and `falsification_experiment` (`design`, `measurements`, `falsification_rule`). Evidence IDs: `PMC…::web::…` = a passage of a retrieved paper, `TXT::…` = a teaching-text passage, `KG::…` = a MatKG fact.

Status: 5 of 135 question runs complete, 130 pending. These runs are not scored; the method's pilot evaluation is in loop.md 28.2. Built by `build_hypothesis_folder.py`.

| # | Split | Paper | Title | Levels done | Final hypothesis (problem-constrained question) |
|---:|---|---|---|---|---|
| [1](1/) | dev | PMC10759803 | Synergy of strength–ductility in HfMoTaTiZr refractory high entropy alloy through Cr addit | 2/3 | Partially substitute Ta with Nb (50 at.% replacement) in HfMoTaTiZr to reduce the alloy’s density while retaining its high-temperature BCC-strengthened framework. |
| [2](2/) | dev | PMC11077685 | Ink‐Extrusion 3D Printing and Silicide Coating of HfNbTaTiZr Refractory High‐Entropy Alloy | 3/3 | Apply a pack aluminizing surface treatment to the as‐cast HfNbTaTiZr alloy to form an external, thin Al-rich layer that oxidizes preferentially at high temperature to form a protective, adherent Al2O3 scale. |
| [3](3/) | dev | PMC11087546 | Overcoming strength-ductility tradeoff with high pressure thermal treatment | 0/3 |  |
| [4](4/) | dev | PMC11355469 | Molecular Dynamics Study on Wear Resistance of High Entropy Alloy Coatings Considering the | 0/3 |  |
| [5](5/) | dev | PMC11375216 | Chemical short-range order increases the phonon heat conductivity in a refractory high-ent | 0/3 |  |
| [6](6/) | dev | PMC11375712 | Magnetic Properties of High-Entropy Alloy FeCoNiTi | 0/3 |  |
| [7](7/) | dev | PMC11606917 | Accelerating ab initio melting property calculations with machine learning: application to | 0/3 |  |
| [8](8/) | dev | PMC11775865 | Atomic‐Scale Insights Into the Thermal Stability of High‐Entropy Nanoalloys | 0/3 |  |
| [9](9/) | test | PMC12029629 | Molecular Dynamics Simulation of the Dynamic Mechanical Behavior of FeNiCrMn High-Entropy  | 0/3 |  |
| [10](10/) | test | PMC12298864 | The Growth Kinetic and Ultra High Hardness of CoCrFeNiTi High–Entropy Alloy by Mechanical  | 0/3 |  |
| [11](11/) | test | PMC12806431 | Aging‐Induced Ductile‐Brittle‐Ductile Transition in High‐Entropy Alloys and its Implicatio | 0/3 |  |
| [12](12/) | test | PMC12941549 | Effect of Sintering Temperature on the Microstructure and Integrated Properties of MgAlTiV | 0/3 |  |
| [13](13/) | test2 | PMC12385913 | High Strength and Fracture Resistance of Reduced-Activity W-Ta-Ti-V-Zr High-Entropy Alloy  | 0/3 |  |
| [14](14/) | test2 | PMC12525334 | A Composition Design Strategy for Refractory High-Entropy Alloys | 0/3 |  |
| [15](15/) | test2 | PMC12566232 | Influence of Increased TaNbV on the Microstructure, Mechanical Properties, and Energy Rele | 0/3 |  |
| [16](16/) | test2 | PMC12693294 | Sequential Spinodal Decompositions and Ordering Reactions in an As-Quenched Cr39Co18Fe18Ni | 0/3 |  |
| [17](17/) | test2 | PMC12693311 | Thermal Stability and Phase Evolution in the Phosphorus-Containing High-Entropy Alloy Fe22 | 0/3 |  |
| [18](18/) | test2 | PMC12734844 | Role of Heat Treatment Atmosphere on the Microstructure and Surface Morphology of DLP-Fabr | 0/3 |  |
| [19](19/) | test2 | PMC12941970 | Synthesis and Tribological Characteristics of High-Performance Self-Lubricating CoCrFeNiMo | 0/3 |  |
| [20](20/) | test2 | PMC12985727 | CrFeVWX (X = Ta or Ti) High-Entropy Alloy: A Theoretical and Experimental Comparative Inve | 0/3 |  |
| [21](21/) | test2 | PMC12986532 | Role of Interfacial Coherency on Creep Behavior of FCC/BCC High-Entropy Alloy Multilayers | 0/3 |  |
| [22](22/) | test2 | PMC13114876 | Elevated-Temperature Tribo-Corrosion Response of Eutectic High-Entropy Alloy | 0/3 |  |
| [23](23/) | test2 | PMC13270461 | Delineating Oxidation Aspects of an Additively Manufactured Nanoprecipitation-Strengthened | 0/3 |  |
| [24](24/) | test2 | PMC13415097 | Impact of Annealing and Strain on Magnetic and Magnetocaloric Properties of FeNiMnSiGe Hig | 0/3 |  |
| [25](25/) | test3 | PMC10920630 | RETRACTED ARTICLE: Electrochemical and hot corrosion behaviour of annealed AlCoCrFeNi HEA  | 0/3 |  |
| [26](26/) | test3 | PMC11277269 | A catalyst family of high-entropy alloy atomic layers with square atomic arrangements comp | 0/3 |  |
| [27](27/) | test3 | PMC11279088 | High-Temperature Oxidation and Phase Stability of AlCrCoFeNi High Entropy Alloy: Insights  | 0/3 |  |
| [28](28/) | test3 | PMC11302478 | Analysis of the temperature-dependent plastic deformation of single crystals of quinary, q | 0/3 |  |
| [29](29/) | test3 | PMC11431282 | Enhanced Magnetocaloric Properties of the (MnNi)0.6Si0.62(FeCo)0.4Ge0.38 High-Entropy Allo | 0/3 |  |
| [30](30/) | test3 | PMC11433250 | Molten Aluminum-Induced Corrosion and Wear-Resistance Properties of ZrB2-Based Cermets Imp | 0/3 |  |
| [31](31/) | test3 | PMC11470405 | The effect of changing constituents on tensile mechanical properties of HfNbTaTiZr high en | 0/3 |  |
| [32](32/) | test3 | PMC11625148 | Enhanced irradiation-resistance in NbMoTaW refractory high-entropy alloy via rhenium addit | 0/3 |  |
| [33](33/) | test3 | PMC12057660 | Precise synthesis of targeted noble metal–based high-entropy alloy nanomaterials | 0/3 |  |
| [34](34/) | test3 | PMC12118456 | Thermal behavior in FeCuCrCoNi high entropy alloy nanoparticles: an atomistic approach† | 0/3 |  |
| [35](35/) | test3 | PMC12194958 | Superconductivity in High-Entropy Alloy System Containing Tb | 0/3 |  |
| [36](36/) | test3 | PMC12716175 | Bi‐Continuous W‐Rich Refractory High Entropy Alloy‐Cu Composite: Toward Material Innovatio | 0/3 |  |
| [37](37/) | test4 | PMC11643467 | The Effect of Zirconium on the Microstructure and Properties of Cast AlCoCrFeNi2.1 Eutecti | 0/3 |  |
| [38](38/) | test4 | PMC11676997 | Impact of Conventional and Laser-Assisted Machining on the Microstructure and Mechanical P | 0/3 |  |
| [39](39/) | test4 | PMC11990796 | Microstructure and Mechanical Properties of Nb35Zr26Ti19Hf15Mo5 Refractory High-Entropy Al | 0/3 |  |
| [40](40/) | test4 | PMC11990881 | Effect of Microstructure on Oxidation Resistance and TGO Formation in FeCoNiCrAl HEA Coati | 0/3 |  |
| [41](41/) | test4 | PMC12028842 | Microstructure and Wear Behavior of WMoTaNbV Refractory High-Entropy Alloy Coating on Ti6A | 0/3 |  |
| [42](42/) | test4 | PMC12072472 | Effect of Al on the Oxidation Behavior of TiCrZrNbTa High-Entropy Coatings on Zr Alloy | 0/3 |  |
| [43](43/) | test4 | PMC12120728 | High Radiation Resistance in the Binary W‐Ta System Through Small V Additions: A New Parad | 0/3 |  |
| [44](44/) | test4 | PMC12195094 | Spark Plasma Sintering and Electrospark Deposition of High Entropy Alloys with Elemental V | 0/3 |  |
| [45](45/) | test4 | PMC12991304 | Post-ageing guided closed-loop discovery of multi-element alloy catalysts for automotive e | 0/3 |  |
