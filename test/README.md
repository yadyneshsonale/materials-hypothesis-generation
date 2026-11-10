# Test set: 45 papers

The papers whose questions all methods were evaluated on (loop.md section 27). Each folder `N/` holds:

- `paper.pdf`: the published article (for reading; the pipeline never uses it).
- `paper.xml`: the open-access JATS XML.
- `question.json`: the three research questions written from the paper's introduction with its own contribution removed (levels `broad`, `problem_constrained`, `expert_context`), the knowledge cutoff (the paper's publication date: methods may only use evidence published before it), the gap the introduction states, and how the questions were written and leak-checked. The answer key is not included.

Note: paper 25 (PMC10920630, Scientific Reports 2024) has since been retracted; it is kept so that the set matches every reported result (`retracted: true` in its question.json).

Built by `build_test_folder.py`; source cases in `experiments/high_temperature_hea_qwen35b/benchmark_*`.

| # | Split | Paper | Published | Title |
|---:|---|---|---|---|
| [1](1/) | dev | PMC10759803 | 2024-01-02 | Synergy of strength–ductility in HfMoTaTiZr refractory high entropy alloy through Cr addition |
| [2](2/) | dev | PMC11077685 | 2024-02-28 | Ink‐Extrusion 3D Printing and Silicide Coating of HfNbTaTiZr Refractory High‐Entropy Alloy for Extreme Temperature Applications |
| [3](3/) | dev | PMC11087546 | 2024-05-10 | Overcoming strength-ductility tradeoff with high pressure thermal treatment |
| [4](4/) | dev | PMC11355469 | 2024-08-07 | Molecular Dynamics Study on Wear Resistance of High Entropy Alloy Coatings Considering the Effect of Temperature |
| [5](5/) | dev | PMC11375216 | 2024-09-04 | Chemical short-range order increases the phonon heat conductivity in a refractory high-entropy alloy |
| [6](6/) | dev | PMC11375712 | 2024-08-22 | Magnetic Properties of High-Entropy Alloy FeCoNiTi |
| [7](7/) | dev | PMC11606917 | 2024-11-29 | Accelerating ab initio melting property calculations with machine learning: application to the high entropy alloy TaVCrW |
| [8](8/) | dev | PMC11775865 | 2024-11-21 | Atomic‐Scale Insights Into the Thermal Stability of High‐Entropy Nanoalloys |
| [9](9/) | test | PMC12029629 | 2025-04-19 | Molecular Dynamics Simulation of the Dynamic Mechanical Behavior of FeNiCrMn High-Entropy Alloy |
| [10](10/) | test | PMC12298864 | 2025-07-09 | The Growth Kinetic and Ultra High Hardness of CoCrFeNiTi High–Entropy Alloy by Mechanical Alloying and Spark Plasma Sintering |
| [11](11/) | test | PMC12806431 | 2025-10-27 | Aging‐Induced Ductile‐Brittle‐Ductile Transition in High‐Entropy Alloys and its Implications |
| [12](12/) | test | PMC12941549 | 2026-02-16 | Effect of Sintering Temperature on the Microstructure and Integrated Properties of MgAlTiVFeCo Lightweight High-Entropy Alloy |
| [13](13/) | test2 | PMC12385913 | 2025-07-01 | High Strength and Fracture Resistance of Reduced-Activity W-Ta-Ti-V-Zr High-Entropy Alloy for Fusion Energy Applications |
| [14](14/) | test2 | PMC12525334 | 2025-09-01 | A Composition Design Strategy for Refractory High-Entropy Alloys |
| [15](15/) | test2 | PMC12566232 | 2025-10-01 | Influence of Increased TaNbV on the Microstructure, Mechanical Properties, and Energy Release Characteristics of High-Entropy Alloy HfZrTi(TaNbV)x |
| [16](16/) | test2 | PMC12693294 | 2025-11-01 | Sequential Spinodal Decompositions and Ordering Reactions in an As-Quenched Cr39Co18Fe18Ni18Al7 High-Entropy Alloy |
| [17](17/) | test2 | PMC12693311 | 2025-11-01 | Thermal Stability and Phase Evolution in the Phosphorus-Containing High-Entropy Alloy Fe22Ni16Co19Mn12Cr16P15 |
| [18](18/) | test2 | PMC12734844 | 2025-12-01 | Role of Heat Treatment Atmosphere on the Microstructure and Surface Morphology of DLP-Fabricated High-Entropy Alloy Components |
| [19](19/) | test2 | PMC12941970 | 2026-02-01 | Synthesis and Tribological Characteristics of High-Performance Self-Lubricating CoCrFeNiMox-Ni/MoS2-Ag-Cr2O3 Composites |
| [20](20/) | test2 | PMC12985727 | 2026-03-01 | CrFeVWX (X = Ta or Ti) High-Entropy Alloy: A Theoretical and Experimental Comparative Investigation on Phase Stability |
| [21](21/) | test2 | PMC12986532 | 2026-03-01 | Role of Interfacial Coherency on Creep Behavior of FCC/BCC High-Entropy Alloy Multilayers |
| [22](22/) | test2 | PMC13114876 | 2026-04-01 | Elevated-Temperature Tribo-Corrosion Response of Eutectic High-Entropy Alloy |
| [23](23/) | test2 | PMC13270461 | 2026-06-01 | Delineating Oxidation Aspects of an Additively Manufactured Nanoprecipitation-Strengthened Al0.2Co1.5CrFeNi1.5Ti0.3 High-Entropy Alloy |
| [24](24/) | test2 | PMC13415097 | 2026-07-01 | Impact of Annealing and Strain on Magnetic and Magnetocaloric Properties of FeNiMnSiGe High-Entropy Alloy Nanoribbons Prepared by Magnetron Co-Sputtering |
| [25](25/) | test3 | PMC10920630 | 2024-03-01 | RETRACTED ARTICLE: Electrochemical and hot corrosion behaviour of annealed AlCoCrFeNi HEA coating over steel |
| [26](26/) | test3 | PMC11277269 | 2024-07-01 | A catalyst family of high-entropy alloy atomic layers with square atomic arrangements comprising iron- and platinum-group metals |
| [27](27/) | test3 | PMC11279088 | 2024-07-01 | High-Temperature Oxidation and Phase Stability of AlCrCoFeNi High Entropy Alloy: Insights from In Situ HT-XRD and Thermodynamic Calculations |
| [28](28/) | test3 | PMC11302478 | 2024-01-01 | Analysis of the temperature-dependent plastic deformation of single crystals of quinary, quaternary and ternary equiatomic high- and medium-entropy alloys of the Cr-Mn-Fe-Co-Ni system |
| [29](29/) | test3 | PMC11431282 | 2024-09-01 | Enhanced Magnetocaloric Properties of the (MnNi)0.6Si0.62(FeCo)0.4Ge0.38 High-Entropy Alloy Obtained by Co Substitution |
| [30](30/) | test3 | PMC11433250 | 2024-09-01 | Molten Aluminum-Induced Corrosion and Wear-Resistance Properties of ZrB2-Based Cermets Improved by Sintering-Temperature Manipulation |
| [31](31/) | test3 | PMC11470405 | 2024-09-24 | The effect of changing constituents on tensile mechanical properties of HfNbTaTiZr high entropy alloy: A molecular dynamics study |
| [32](32/) | test3 | PMC11625148 | 2024-11-19 | Enhanced irradiation-resistance in NbMoTaW refractory high-entropy alloy via rhenium addition |
| [33](33/) | test3 | PMC12057660 | 2025-05-01 | Precise synthesis of targeted noble metal–based high-entropy alloy nanomaterials |
| [34](34/) | test3 | PMC12118456 | 2025-05-01 | Thermal behavior in FeCuCrCoNi high entropy alloy nanoparticles: an atomistic approach† |
| [35](35/) | test3 | PMC12194958 | 2025-06-01 | Superconductivity in High-Entropy Alloy System Containing Tb |
| [36](36/) | test3 | PMC12716175 | 2025-05-30 | Bi‐Continuous W‐Rich Refractory High Entropy Alloy‐Cu Composite: Toward Material Innovation of Nuclear Reactor Coolant System |
| [37](37/) | test4 | PMC11643467 | 2024-12-01 | The Effect of Zirconium on the Microstructure and Properties of Cast AlCoCrFeNi2.1 Eutectic High-Entropy Alloy |
| [38](38/) | test4 | PMC11676997 | 2024-11-01 | Impact of Conventional and Laser-Assisted Machining on the Microstructure and Mechanical Properties of Ti-Nb-Cr-V-Ni High-Entropy Alloy Fabricated with Directed Energy Deposition |
| [39](39/) | test4 | PMC11990796 | 2025-04-01 | Microstructure and Mechanical Properties of Nb35Zr26Ti19Hf15Mo5 Refractory High-Entropy Alloy Under Rolling and Heat Treatment |
| [40](40/) | test4 | PMC11990881 | 2025-03-01 | Effect of Microstructure on Oxidation Resistance and TGO Formation in FeCoNiCrAl HEA Coatings Deposited by Low-Temperature HVAF Spraying |
| [41](41/) | test4 | PMC12028842 | 2025-04-01 | Microstructure and Wear Behavior of WMoTaNbV Refractory High-Entropy Alloy Coating on Ti6Al4V Alloy Surface Prepared by Laser Cladding |
| [42](42/) | test4 | PMC12072472 | 2025-04-01 | Effect of Al on the Oxidation Behavior of TiCrZrNbTa High-Entropy Coatings on Zr Alloy |
| [43](43/) | test4 | PMC12120728 | 2025-03-07 | High Radiation Resistance in the Binary W‐Ta System Through Small V Additions: A New Paradigm for Nuclear Fusion Materials |
| [44](44/) | test4 | PMC12195094 | 2025-06-01 | Spark Plasma Sintering and Electrospark Deposition of High Entropy Alloys with Elemental Variation |
| [45](45/) | test4 | PMC12991304 | 2026-03-16 | Post-ageing guided closed-loop discovery of multi-element alloy catalysts for automotive exhaust purification |
