# One real run, end to end: `PMC11643467__problem_constrained__rx_r__s1`

Arm: focused retrieval + the conservative writer (WRITER_B), o3-mini. Paper (hidden from every query-facing model): **The Effect of Zirconium on the Microstructure and Properties of Cast AlCoCrFeNi2.1 Eutectic High-Entropy Alloy.** (PMC11643467, doi 10.3390/ma17235938, published 2024-12-01, split test4).

Everything below is verbatim from the run's records. Inputs that were not stored (the screener's and grader's batches, the writer's payload) were rebuilt offline and checked against what the run logged. Made by `make_example_trace.py`; the complete machine-readable version is `example_trace.json`.

## 0. The user input and how the benchmark made it

**The question given to the agent** (problem_constrained; knowledge cutoff 2024-12-01):

> For an AlCoCrFeNi2.1 eutectic high-entropy alloy in its uniform, fine lamellar state, whose strength and plasticity remain below industrial application requirements, what single intervention could improve performance for fasteners exposed to extreme temperature fluctuations, long-term mechanical loading, room-temperature creep, and corrosive conditions? State the proposed intervention, mechanism, predicted outcome relative to the starting alloy, applicable operating and test boundaries, supporting prior evidence, and a controlled experiment with explicit falsification criteria.

The other two levels of the same question:

- **broad**: For high-entropy alloys intended for aerospace fasteners, what single intervention could improve the combination of mechanical durability, room-temperature creep resistance, and corrosion resistance? Formulate one hypothesis specifying the intervention, its mechanism, the predicted improvement relative to an untreated baseline, the conditions under which it should hold, prior evidence that supports it, and an experiment with clear results that would falsify it.
- **expert_context**: Single-phase high-entropy alloys have difficulty achieving a satisfactory strength–ductility balance. Earlier work introduced the AlCoCrFeNi2.1 eutectic high-entropy alloy with a uniform, fine lamellar structure to enable large-sized production and obtain good strength and plasticity, but its performance still falls short of industrial requirements. Its use in aircraft and spacecraft fasteners further requires stability under extreme temperature fluctuations, long-term mechanical loading, room-temperature creep, and corrosion, while relevant creep and corrosion studies remain limited by sample-size and experimental-environment constraints. Given these limitations and design requirements, what single intervention could improve the alloy’s practical performance? Present one hypothesis that specifies the intervention, causal mechanism, predicted improvement over the starting material, boundary conditions, supporting prior evidence, and a feasible experiment whose outcome could falsify the hypothesis.

**Paper selection screen** (prompt):

```text
You screen papers for a materials-science corpus. Inclusion rule: the paper directly studies elevated-temperature, refractory/extreme-environment, creep, oxidation, hot-corrosion, melting, thermal/phase-stability or temperature-dependent behaviour of a high-entropy alloy (multi-principal-element alloy), and it is primary research, not a review. Use only the title and abstract. Return JSON {"include": true|false, "reason": str}.
```

**Answer key** (trapi:gpt-5.6-sol_2026-07-09; input: the paper's abstract and every section except the Introduction (not reproduced here)). Prompt:

```text
You build the hidden answer key of a temporal hypothesis-reconstruction benchmark case. You receive one paper's abstract and its sections other than the Introduction. Construct the hidden structured target from the paper's own results (current-paper evidence): what the paper did and found. Preserve uncertainty rather than filling absent details. Fields: material_initial_state (the starting material and its state), intervention (the intervention or study the paper made, with its key parameters), conditions (processing, test or simulation conditions), structural_mediator (the structure or state through which the effect acts), mechanism, predicted_outcome (the outcome the paper reports, stated as a prediction relative to the baseline), baseline, boundary (where the result holds), discriminating_measurement (the measurement that tests it), actual_result (the main quantitative or qualitative result). Return JSON {"hidden_target": {"material_initial_state": str, "intervention": str, "conditions": str, "structural_mediator": str, "mechanism": str, "predicted_outcome": str, "baseline": str, "boundary": str, "discriminating_measurement": str, "actual_result": str}}.
```

Output (the hidden target the judges compare against):

```json
{
 "material_initial_state": "As-cast AlCoCrFeNi2.1 eutectic high-entropy alloy (x = 0), produced from high-purity elements, with an approximately 70% FCC-dominant FCC + ordered B2 dual-phase lamellar microstructure.",
 "intervention": "Zr was alloyed into AlCoCrFeNi2.1 at nominal x = 0.01, 0.05, and 0.1 (with x = 0 as the control), and the as-cast alloys were examined for phase/microstructure evolution, hardness, room-temperature compression, nanoindentation creep, and electrochemical corrosion.",
 "conditions": "Button ingots were made under Ar by cold-crucible/vacuum melting and remelted at least five times. Microhardness used a 0.981 N load for 15 s; room-temperature compression used 3 mm × 6 mm cylinders at 1 × 10^-3 s^-1 to strain 0.3. Nanoindentation creep used a 10 mN peak load, 100 s hold, and loading rates of 0.1, 1, and 5 mN/s. Corrosion testing was conducted after 30 min immersion in 3.5 wt% NaCl using polarization from -0.8 to 1.5 V at 1 mV/s and EIS from 10^-2 to 10^4 Hz.",
 "structural_mediator": "Zr initially enters the FCC/B2 matrix and causes lattice distortion; at x >= 0.05, Ni- and Zr-rich Ni7Zr2 precipitates emerge at phase boundaries and bridge the FCC and B2 regions. Their morphology evolves from dispersed particles at low Zr to a discontinuous network at x = 0.05 and a coarse continuous network at x = 0.1, while the B2 fraction decreases. TEM of x = 0.1 also showed L12 precipitates in the FCC phase and nanoprecipitates in B2.",
 "mechanism": "Moderate Zr provides solid-solution strengthening through lattice distortion and dispersion/precipitation strengthening through fine, coherent or semi-coherent Ni7Zr2-related precipitates, impeding dislocations and grain-boundary sliding. Excess Zr coarsens and connects the Zr-rich phase, promotes Ni depletion from B2, reduces the B2 fraction, increases segregation and embrittlement, and therefore diminishes mechanical strengthening. For corrosion, the more continuous Zr-rich structure at x = 0.1 favors a stable, protective passive layer, plausibly including ZrO2, that blocks Cl- ingress; uneven intermediate precipitates can instead promote microgalvanic attack.",
 "predicted_outcome": "Relative to Zr-free AlCoCrFeNi2.1, moderate Zr addition—especially x = 0.05—should reduce creep deformation and increase hardness, yield strength, and compressive strength, whereas excessive Zr (x = 0.1) should lower room-temperature mechanical properties from the x = 0.05 optimum. In contrast, x = 0.1 should provide the best corrosion resistance through a more stable passive film.",
 "baseline": "The x = 0 as-cast AlCoCrFeNi2.1 alloy had an FCC + B2 lamellar structure, yield strength 705.1 ± 31.53 MPa, compressive strength 1182.7 ± 24.68 MPa, corrosion current density 0.09993 μA/cm2, pitting potential 320.27 mV, corrosion rate 0.0011621 mm/year, and charge-transfer resistance 2600 Ω·cm2.",
 "boundary": "The reported trends apply to the as-cast ZrxAlCoCrFeNi2.1 compositions x = 0, 0.01, 0.05, and 0.1 under the stated room-temperature mechanical/nanoindentation conditions and in 3.5 wt% NaCl. The mechanical optimum occurred at x = 0.05; increasing Zr to x = 0.1 reversed part of the strengthening benefit, while corrosion resistance was best at x = 0.1. Dislocation-dominated creep was most persistent at x = 0.05, whereas loading-rate changes altered the inferred mechanisms in the other alloys.",
 "discriminating_measurement": "XRD, SEM/EDS, and TEM/SAED identified phase and morphology changes; microhardness and room-temperature compression distinguished the mechanical optimum; nanoindentation creep displacement and the fitted stress exponent n distinguished creep resistance and mechanism; potentiodynamic polarization (Icorr, Ecorr, and Epit), EIS/Rct, and post-corrosion SEM/EDS distinguished corrosion resistance and passive-film stability.",
 "actual_result": "At x = 0.05, hardness peaked at 368.1 HV (about 18.7% above the Zr-free alloy), yield strength at 1048.7 ± 23.84 MPa (about 48.7% higher), and compressive strength at 1801.1 ± 28.70 MPa (about 52.2% higher). At x = 0.1 these fell to 865.9 ± 14.85 MPa and 1382.4 ± 13.56 MPa, respectively. At a 5 mN/s indentation loading rate, creep depth changed from 22.16 nm at x = 0 to 13.47 nm at x = 0.05, then rose to 18.36 nm at x = 0.1. The creep exponent exceeded 3 at 0.1 mN/s, and x = 0.05 retained n > 3 even at 5 mN/s, indicating dislocation creep and robust creep resistance. Corrosion resistance ranked x = 0.1 > x = 0.01 > x = 0.05 > x = 0; x = 0.1 had the lowest Icorr, 0.034197 μA/cm2, the highest Epit, 323.06 mV, a corrosion rate of 0.00039737 mm/year, and the highest Rct, 700,000 Ω·cm2."
}
```

**Gap type** (prompt, output):

```text
You read the introduction of a materials-science paper, with the paper's own contribution removed. Classify the research gap that the introduction motivates. design: a property or performance limitation of a material that needs to be overcome. understanding: a behaviour, mechanism, stability or structure-property question that the introduction says is unknown, unclear or insufficiently understood. method: a limitation of existing methods, models, simulations or measurement tools for obtaining some quantity. Use only the text. Return JSON {"gap_type": "design"|"understanding"|"method", "evidence": short quote from the text, "reason": str}.
```

```json
{
 "gap_type": "design",
 "evidence": "the AlCoCrFeNi2.1 eutectic high-entropy alloy still falls short of the industrial application requirements, making it crucial to further enhance its performance",
 "reason": "The introduction emphasizes that the alloy's current strength, ductility, creep, and corrosion performance is inadequate for industrial and aerospace applications, motivating material performance improvement.",
 "classifier": "gpt-5.6-sol_2026-07-09"
}
```

**Question writer** (trapi:gpt-5.6-sol_2026-07-09). Prompt:

```text
You write evaluation questions for a materials-science hypothesis-generation benchmark. You receive the introduction of a research paper with the paper's own contribution removed. Write three research questions for a scientist who has not read the paper, at three levels of context: broad, problem_constrained and expert_context. Each level adds context to the previous one.
Rules (from the MOOSE-Chem benchmark guideline):
- Use only information in the supplied introduction text. Do not add anything you may know about this or any other paper.
- The question and background must not contain any information or method that could be the paper's answer: no proposed material change, added element, processing route, treatment, microstructure, phase, defect structure, mechanism or predicted value. Methods that the introduction describes as earlier work on this problem may be mentioned as background, with their limitations.
- The question must stay general about the solution: ask what intervention could solve the problem, never hint at its direction or class (for example do not say 'via alloying', 'by heat treatment', 'by introducing a second phase').
- Each question asks for one hypothesis with: the proposed intervention, the mechanism, the predicted outcome relative to a baseline, its boundary conditions, supporting prior evidence and a falsification experiment.
Level rules: broad: State only the material family or application and the property goal. Do not name a specific starting composition. problem_constrained: Add the specific starting material and its state, the failure or limitation to overcome, and the operating or test regime. expert_context: Add a short background survey from the introduction: what earlier work tried for this problem and why it fell short, and any stated design constraints.
If revision_requests are supplied, rewrite the listed levels so that none of the listed phrases or ideas remains, in any wording; keep the other levels unchanged.
Return JSON {"broad": str, "problem_constrained": str, "expert_context": str}.
```

Input (the paper's introduction with its own contribution removed):

```json
{
 "introduction_without_own_contribution": "In recent years, high entropy alloys (HEAs), also referred to as multicomponent alloys (MCAs), have increasingly been explored as potential materials for various applications due to their outstanding properties, such as high strength, excellent plasticity, resistance to oxidation, and superior corrosion resistance. HEAs generally comprise at least five principal elements, creating a homogeneous solid solution within a high-entropy state through the combination of multiple elements. This complex composition and structure result in numerous dislocation defects and grain boundaries in the material, which effectively restrict dislocation movement and enhance the material’s strength and ductility. However, balancing strength and ductility in single-phase HEAs remains a challenge. To address this issue, Lu et al.. from Dalian University of Technology introduced an AlCoCrFeNi2.1 eutectic high entropy alloy in 2014, featuring a uniform, fine lamellar eutectic structure similar to pearlite. This alloy offers a novel approach for producing large-sized high-entropy alloys. Despite having good strength and plasticity, the AlCoCrFeNi2.1 eutectic high-entropy alloy still does not fully meet industrial application standards, underscoring the need for further performance enhancements to expand its practical utility. Nevertheless, the performance of the AlCoCrFeNi2.1 eutectic high-entropy alloy still falls short of the industrial application requirements, making it crucial to further enhance its performance to broaden its practical application potential. Zirconium (Zr) is often added as a solute atom in high-entropy alloy systems. Research has shown that Zr can induce the formation of hard Laves phases, thereby improving the compressive performance of Al2NbTi3V2Zrx alloys. Additionally, adding Zr to CoCrFeNiNb entropy alloys can significantly refine the grain structure and increase the grain boundary density, which contributes to enhancing the yield strength and hardness of the alloy.\n\nIn aircrafts and spacecraft, fasteners are critical components that ensure the safe connection of various parts. These fasteners must withstand extreme temperature fluctuations and endure long-term mechanical loading. In such environments, room-temperature creep and corrosion resistance are significant factors that affect the long-term stability and lifespan of fasteners. Currently, research on the creep and corrosion resistance of eutectic high-entropy alloys is limited owing to the sample size and experimental environment constraints, hindering their widespread application in the field."
}
```

Output:

```json
{
 "broad": "For high-entropy alloys intended for aerospace fasteners, what single intervention could improve the combination of mechanical durability, room-temperature creep resistance, and corrosion resistance? Formulate one hypothesis specifying the intervention, its mechanism, the predicted improvement relative to an untreated baseline, the conditions under which it should hold, prior evidence that supports it, and an experiment with clear results that would falsify it.",
 "problem_constrained": "For an AlCoCrFeNi2.1 eutectic high-entropy alloy in its uniform, fine lamellar state, whose strength and plasticity remain below industrial application requirements, what single intervention could improve performance for fasteners exposed to extreme temperature fluctuations, long-term mechanical loading, room-temperature creep, and corrosive conditions? State the proposed intervention, mechanism, predicted outcome relative to the starting alloy, applicable operating and test boundaries, supporting prior evidence, and a controlled experiment with explicit falsification criteria.",
 "expert_context": "Single-phase high-entropy alloys have difficulty achieving a satisfactory strength–ductility balance. Earlier work introduced the AlCoCrFeNi2.1 eutectic high-entropy alloy with a uniform, fine lamellar structure to enable large-sized production and obtain good strength and plasticity, but its performance still falls short of industrial requirements. Its use in aircraft and spacecraft fasteners further requires stability under extreme temperature fluctuations, long-term mechanical loading, room-temperature creep, and corrosion, while relevant creep and corrosion studies remain limited by sample-size and experimental-environment constraints. Given these limitations and design requirements, what single intervention could improve the alloy’s practical performance? Present one hypothesis that specifies the intervention, causal mechanism, predicted improvement over the starting material, boundary conditions, supporting prior evidence, and a feasible experiment whose outcome could falsify the hypothesis."
}
```

**Leakage checker** (trapi:gpt-5.6-sol_2026-07-09) and lexical gate (answer-word overlap at most 10%). Prompt:

```text
You audit a benchmark question for answer leakage. The input has the question and the hidden answer (the paper's intervention, structural mediator, mechanism and outcome). Stating the starting material, its problem, the property goal, the test conditions and earlier work that the answer does not use is allowed. Report every phrase in the question that reveals or points to: the intervention or its class (for example 'alloying addition', 'thermomechanical treatment', 'second phase'), the structural mediator, the mechanism, or a quantified outcome of the answer. Also judge whether a materials scientist reading only the question would be steered toward the answer's intervention class. Return JSON {"leaks": [{"phrase": exact text from the question, "reveals": one of intervention|structural_mediator|mechanism|outcome, "why": str}], "steers_to_answer": true|false}.
```

Results (round 1):

```json
{
 "broad": {
  "passed": true,
  "leaks": [],
  "steers_to_answer": false,
  "overlap": 0.023,
  "shared_words": [
   "alloys",
   "mechanical"
  ]
 },
 "problem_constrained": {
  "passed": true,
  "leaks": [],
  "steers_to_answer": false,
  "overlap": 0.034,
  "shared_words": [
   "boundaries",
   "fine",
   "mechanical"
  ]
 },
 "expert_context": {
  "passed": true,
  "leaks": [],
  "steers_to_answer": false,
  "overlap": 0.034,
  "shared_words": [
   "alloys",
   "fine",
   "mechanical"
  ]
 }
}
```

## 1. Search plan (trapi:o3-mini_2025-01-31)

Prompt:

```text
You plan a literature search for a materials-science research question, before anyone answers it. Use only the question and materials-science knowledge from before the knowledge cutoff. Write the concepts a researcher would search for, as groups of short search phrases (1 to 4 words each, as they would appear in titles or abstracts, with common synonyms and abbreviations):
- "material": the specific material systems the question names (alloy names or compositions);
- "material_class": the class of material as researchers name it (for example "refractory high-entropy alloy");
- "property": the property, behaviour or limitation at stake;
- "regime": the operating or test conditions, if the question states them;
- "approach_1" ... "approach_6": approaches, mechanisms, phenomena or methods a researcher would look up to answer the question (compositions, processing routes, microstructures, mechanisms, characterisation or simulation methods), one per group.
Omit a group the question gives no basis for. Each group has 1 to 6 phrases. Then write 6 to 8 searches; each is an AND of 2 or 3 group names, from specific (material AND property) to broader (material_class AND an approach). Return JSON {"groups": {group name: [phrases]}, "searches": [[group names], ...]}, where each search is a plain list of group names, for example ["material", "property"].
```

Input:

```json
{
 "question": "For an AlCoCrFeNi2.1 eutectic high-entropy alloy in its uniform, fine lamellar state, whose strength and plasticity remain below industrial application requirements, what single intervention could improve performance for fasteners exposed to extreme temperature fluctuations, long-term mechanical loading, room-temperature creep, and corrosive conditions? State the proposed intervention, mechanism, predicted outcome relative to the starting alloy, applicable operating and test boundaries, supporting prior evidence, and a controlled experiment with explicit falsification criteria.",
 "knowledge_cutoff": "2024-12-01"
}
```

Output (as parsed and stored):

```json
{
 "groups": {
  "material": [
   "AlCoCrFeNi2.1",
   "AlCoCrFeNi HEA"
  ],
  "material_class": [
   "eutectic high-entropy alloy",
   "EHEA"
  ],
  "property": [
   "strength",
   "plasticity",
   "creep resistance",
   "corrosion resistance"
  ],
  "regime": [
   "extreme temperature cycling",
   "long-term loading",
   "room-temperature creep",
   "corrosive environment"
  ],
  "approach_1": [
   "precipitation hardening",
   "secondary phase"
  ],
  "approach_2": [
   "annealing treatment",
   "heat treatment"
  ],
  "approach_3": [
   "micro-alloying",
   "minor alloying addition"
  ],
  "approach_4": [
   "grain boundary engineering",
   "grain refinement"
  ],
  "approach_5": [
   "surface modification",
   "coating application"
  ],
  "approach_6": [
   "phase transformation",
   "dual-phase formation"
  ]
 },
 "searches": [
  [
   "material",
   "property"
  ],
  [
   "material_class",
   "regime",
   "approach_1"
  ],
  [
   "material",
   "approach_2"
  ],
  [
   "material_class",
   "approach_3"
  ],
  [
   "material",
   "approach_4"
  ],
  [
   "material_class",
   "property",
   "regime"
  ],
  [
   "approach_2",
   "property"
  ],
  [
   "approach_1",
   "regime"
  ]
 ]
}
```

## 2. Searches (Europe PMC: open access, full text, dated before the paper)

Filter added to every query: `OPEN_ACCESS:y AND HAS_FT:y AND NOT SRC:PPR AND FIRST_PDATE:[1900-01-01 TO 2024-11-30]`

| Search (AND of groups) | Hits | Fetched |
|---|---:|---:|
| material AND property | 8 | 8 |
| material_class AND regime | 0 | 0 |
| material AND approach_2 | 3 | 3 |
| material_class AND approach_3 | 0 | 0 |
| material AND approach_4 | 0 | 0 |
| material_class AND property | 16 | 16 |
| approach_2 AND property | 891 | 200 |
| approach_1 AND regime | 1 | 1 |

Unique hits: 222. The query of the first search:

```text
(TITLE_ABS:"AlCoCrFeNi2.1" OR TITLE_ABS:"AlCoCrFeNi HEA") AND (TITLE_ABS:"strength" OR TITLE_ABS:"plasticity" OR TITLE_ABS:"creep resistance" OR TITLE_ABS:"corrosion resistance") AND OPEN_ACCESS:y AND HAS_FT:y AND NOT SRC:PPR AND FIRST_PDATE:[1900-01-01 TO 2024-11-30]
```

**Second channel: the experiment-36 web corpus** (70 papers). Its search phrases were written by trapi:Llama-3.3-70B-Instruct_5. Prompt:

```text
You turn a materials-science research question into literature-search phrases. Return JSON {"phrases": [three phrases]}. Each phrase has 2 to 6 words and names the material system or alloy family, and the property, process or mechanism the question is about. Use only terms from or directly implied by the question. No boolean operators or quotes.
```

Input:

```json
{
 "question": "For an AlCoCrFeNi2.1 eutectic high-entropy alloy in its uniform, fine lamellar state, whose strength and plasticity remain below industrial application requirements, what single intervention could improve performance for fasteners exposed to extreme temperature fluctuations, long-term mechanical loading, room-temperature creep, and corrosive conditions? State the proposed intervention, mechanism, predicted outcome relative to the starting alloy, applicable operating and test boundaries, supporting prior evidence, and a controlled experiment with explicit falsification criteria."
}
```

Output:

```json
{
 "phrases": [
  "AlCoCrFeNi high entropy strength",
  "eutectic alloy plasticity improvement",
  "high entropy alloy creep resistance"
 ]
}
```

Its searches:

```json
[
 {
  "phrase": "AlCoCrFeNi high entropy strength",
  "query": "(ABSTRACT:alcocrfeni OR ABSTRACT:strength) AND (ABSTRACT:\"high entropy\" OR ABSTRACT:\"high-entropy\" OR ABSTRACT:\"multi-principal\" OR ABSTRACT:\"multi-principal-element\" OR ABSTRACT:\"complex concentrated\" OR ABSTRACT:\"medium entropy\" OR ABSTRACT:\"medium-entropy\" OR TITLE:\"high entropy\" OR TITLE:\"high-entropy\") AND OPEN_ACCESS:y AND HAS_FT:y AND NOT SRC:PPR AND FIRST_PDATE:[1900-01-01 TO 2024-11-30]",
  "hit_count": 350,
  "fetched": 350,
  "searched_at": "2026-10-27"
 },
 {
  "phrase": "eutectic alloy plasticity improvement",
  "query": "(ABSTRACT:eutectic OR ABSTRACT:plasticity OR ABSTRACT:improvement) AND (ABSTRACT:\"high entropy\" OR ABSTRACT:\"high-entropy\" OR ABSTRACT:\"multi-principal\" OR ABSTRACT:\"multi-principal-element\" OR ABSTRACT:\"complex concentrated\" OR ABSTRACT:\"medium entropy\" OR ABSTRACT:\"medium-entropy\" OR TITLE:\"high entropy\" OR TITLE:\"high-entropy\") AND OPEN_ACCESS:y AND HAS_FT:y AND NOT SRC:PPR AND FIRST_PDATE:[1900-01-01 TO 2024-11-30]",
  "hit_count": 123,
  "fetched": 123,
  "searched_at": "2026-10-27"
 },
 {
  "phrase": "high entropy alloy creep resistance",
  "query": "(ABSTRACT:creep OR ABSTRACT:resistance) AND (ABSTRACT:\"high entropy\" OR ABSTRACT:\"high-entropy\" OR ABSTRACT:\"multi-principal\" OR ABSTRACT:\"multi-principal-element\" OR ABSTRACT:\"complex concentrated\" OR ABSTRACT:\"medium entropy\" OR ABSTRACT:\"medium-entropy\" OR TITLE:\"high entropy\" OR TITLE:\"high-entropy\") AND OPEN_ACCESS:y AND HAS_FT:y AND NOT SRC:PPR AND FIRST_PDATE:[1900-01-01 TO 2024-11-30]",
  "hit_count": 234,
  "fetched": 234,
  "searched_at": "2026-10-27"
 }
]
```

Admitted after the date, type and held-out checks: 270 papers (channels {'search': 200, 'both': 11, 'old_corpus': 59}; rejected {'excluded_type': 11, 'held_out': 1}).

## 3. Relevance screening (trapi:gpt-4o_2024-11-20), 20 papers per call in a seeded random order

Prompt:

```text
You screen search results for a materials-science research question. For each paper (title and abstract), grade how useful it is for answering the question:
3 = directly on point: the same or a closely related material system AND the same property or limitation, or it reports an approach that directly addresses the question's limitation;
2 = relevant: the same property or limitation in a related material class, the same material system with a related property, or a mechanism, approach or method the question could use;
1 = tangential: the same broad field, but a different property and a different material system;
0 = unrelated.
Judge from the title and abstract only. If a search purpose is given, also count usefulness for that purpose. Return JSON {"grades": [{"id": int, "grade": 0-3, "why": "at most 12 words"}]} with one entry per paper.
```

Batch 1, input:

```json
{
 "question": "For an AlCoCrFeNi2.1 eutectic high-entropy alloy in its uniform, fine lamellar state, whose strength and plasticity remain below industrial application requirements, what single intervention could improve performance for fasteners exposed to extreme temperature fluctuations, long-term mechanical loading, room-temperature creep, and corrosive conditions? State the proposed intervention, mechanism, predicted outcome relative to the starting alloy, applicable operating and test boundaries, supporting prior evidence, and a controlled experiment with explicit falsification criteria.",
 "papers": [
  {
   "id": 1,
   "title": "Tuning Corrosion Resistance and AC Soft Magnetic Properties of Fe-Co-Ni-Al Medium-Entropy Alloy via Ni Content.",
   "abstract": "Corrosion of soft magnetic materials during service can significantly impact their performance and service life, therefore it is important to improve their corrosion resistance. In this paper, the corrosion resistance, alternating current soft magnetic properties (AC SMPs) and microstructure of FeCoNi x Al ( x = 1.0-2.0) medium-entropy alloys (MEAs) were studied. Corrosion resistance is greatly improved with an increase in Ni content. The x = 2.0 alloy has the lowest corrosion current density ( I corr = 2.67 × 10 -7 A/cm 2 ), which is reduced by 71% compared to the x = 1.0 alloy. Increasing the Ni content can improve the AC SMPs of the alloy. When x = 1.75, the total loss ( P s ) is improved by 6% compared to the x = 1.0 alloy. X-ray diffraction (XRD) and scanning electron microscopy (SEM) show that the increase in Ni content is beneficial for promoting the formation of the face-centered-cubic (FCC) phase, and the body-centered-cubic (BCC) phase is gradually divided by the FCC phase. Electron backscatter diffraction (EBSD) shows that, with the increase in Ni content, the number of grain boundaries in the alloy is greatly reduced and numerous phase boundaries appear in the alloys. The degree of strain concentration is significantly reduced with the increasing Ni content. The corrosion mechanism of alloys is also discussed in this paper. Our study provides a method to balance the soft magnetic properties and corrosion resistance, paving the way for potential applications of Fe-"
  },
  {
   "id": 2,
   "title": "Effect of BASC and BASCA Heat Treatment on Microstructure and Mechanical Properties of TC10 Titanium Alloy.",
   "abstract": "The purpose of this study is to investigate two new heat treatment processes on the mechanical properties of TC10 titanium alloy. By changing the β annealing temperature, the variation in microstructure and mechanical properties of TC10 titanium alloy were investigated. The results showed that with the increase in β annealing temperature the microstructure type changes from an equiaxed structure to a lamellar structure. The strength of the alloy then increases firstly, followed by a decrease, while the plasticity decreases all the time. Microstructure observation revealed that the alloy is uniformly composed of α phase and β phase after the two processes. In addition, it was found that the fracture morphology of the equiaxed structure is mainly dimples, showing ductile fracture characteristics, while the fracture morphology of lamellar microstructure is mainly crystalline, showing brittle fracture characteristics. These results indicated that reasonable β annealing temperature can be set according to different requirements to obtain different types of microstructure and mechanical properties, which expands the application field of TC10 titanium alloy."
  },
  {
   "id": 3,
   "title": "Influence of Sintering Atmosphere, Temperature and the Solution-Annealing Treatment on the Properties of Precipitation-Hardening Sintered 17-4 PH Stainless Steel.",
   "abstract": "So far, unlike metal injection molding (MIM), conventional powder metallurgy technology (PM) has not been regarded as a method for producing structural elements from 17-4 PH powders, due to the problems of obtaining almost fully compacted shapes after sintering. Nevertheless, recent research demonstrates that it is possible to manufacture sintered parts with high strength by pressing and sintering. The purpose of the study was to determine the degree of densification of 17-4 PH sintered stainless steel during sintering at different temperatures and atmospheres. As a result of the study, it was pointed out that both the temperature and the sintering atmosphere play an essential role in the process of densification of the studied powders during sintering. The formation of delta ferrite and a more pronounced degree of spheroidization of the pores is activated by a higher sintering temperature. Furthermore, after solution-annealed and age-hardened treatment, sintered 17-4 PH stainless steel exhibits high strength with moderate ductility at a level that is difficult to achieve for other sintered stainless-steel grades, such as austenitic, ferritic and martensitic. In turn, the largest improvement in the pitting corrosion resistance in 0.5 M NaCl solution is reached by sintering at 1340 °C in hydrogen and after solid solution treatment."
  },
  {
   "id": 4,
   "title": "Effect of Ultrasonic-Assisted Modification Treatment on the Microstructure and Properties of A356 Alloy.",
   "abstract": "Ultrasonic treatment was applied to an A356 aluminum melt with different modifiers, and the effects of ultrasonic treatment on the structure and properties of the A356 alloy were studied. The results showed that α-Al was effectively refined with different ultrasonic modification treatments. In particular, ultrasonic treatment showed the most obvious refinement with macroscopic grains of unmodified alloy and optimized the refinement of secondary dendrite arm spacings in the Sr/Ce synergistic alloys. The eutectic Si of the unmodified A356 alloy had no obvious change after the ultrasonic treatment, but the branch diameter of the eutectic Si reduced in the Sr and Sr/Ce modification alloys after the ultrasonic treatment. The ultrasonic treatment significantly improved the ultimate tensile strength and elongation of the as-cast A356 alloy with the unmodified material, which was due to refinement of the α-Al grains by the ultrasonic treatment. After the T6 heat treatment, the ultimate tensile strength values of the alloys showed no obvious change due to the ultrasonic treatment, but the plasticity of the alloy was significantly improved. Mg 2 Si precipitation was the dominant strengthening mechanism during the T6 heat treatment, while the plasticity was determined by the size and distribution of the eutectic Si. Acoustic cavitation caused by the ultrasound-activated impurities and the induced heterogeneous nucleation and supercooled nucleation in the groove melt was the main cause o"
  },
  {
   "id": 5,
   "title": "Micromechanical Modeling of AlSi10Mg Processed by Laser-Based Additive Manufacturing: From as-Built to Heat-Treated Microstructures.",
   "abstract": "The unique microstructure of the alloy AlSi10Mg produced by the laser-based powder bed fusion of metals (PBF-LB/M) provides high-strength and high-strain-hardening capabilities of the material. The microstructure and mechanical properties of 3D-printed, i.e., additively manufactured, AlSi10Mg are significantly altered by post-building heat-treatment processes applied in order to tailor the final properties of the parts. Using an accurate computational model to predict and improve the mechanical performance of 3D-printed samples considering their microstructural features can accelerate their employment in envisaged applications. The present study aims to investigate the correlation between microstructural features and the mechanical behavior of as-built, direct-aged, and T6 heat-treated samples of PBF-LB/M AlSi10Mg under tensile loading using experiment and microstructure-sensitive modeling approaches. Nanoindentation tests are used to calibrate the parameters of the constitutive models for the Al and Si-rich phases. The experimental investigations revealed that heat treatment significantly changes the sub-grain morphology of the Si-rich phase, and this can have a considerable effect on the mechanical behavior of the components. The effect of the modeling of the Si-rich phase in the representative volume elements on the prediction of mechanical behavior is investigated using the J2 plasticity model. The combination of the crystal plasticity model for Al and the J2 plasticity m"
  },
  {
   "id": 6,
   "title": "Relationship between Texture, Hydrogen Content, Residual Stress and Corrosion Resistance of Electrodeposited Chromium Coating: Influence of Heat Treatment.",
   "abstract": "Electrodeposited chromium plating continues to be widely used in a number of specialized areas, such as weapons, transport, aerospace, etc. However, the formation of texture, hydrogen content and residual stress can degrade the serviceability and lead to material failure. The effect of post heat treatment processes on the relationship of texture, hydrogen content, residual stress and corrosion resistance of hexavalent [Cr(VI)] chromium coatings deposited on Cr-Ni-Mo-V steel substrates was investigated. Macrotexture was measured by XRD. Microtexture, dislocation density and grain size were studied by EBSD. With the increase of the heat treatment temperature, it was found that the fiber texture strength of the (222) plane tended to increase and subsequently decrease. Below 600 °C, the increase in the (222) plane texture carried a decrease in the hydrogen content, residual stress, microhardness and an increase in the corrosion resistance. In addition, crack density and texture strength were less affected by the heat treatment time. Notably, relatively fewer crack densities of 219/cm 2 , a lower corrosion current density of 1.798 × 10 -6 A/dm 2 and a higher microhardness of 865 HV were found under the preferred heat treatment temperature and time of 380 °C and 4 h, respectively. The hydrogen content and residual stress were 7.63 ppm and 61 MPa, with 86% and 75% reduction rates compared to the as-plated state, respectively. In conclusion, in our future judgement of the influence o"
  },
  {
   "id": 7,
   "title": "Simultaneous Strength-Ductility Enhancement of a Nano-Lamellar AlCoCrFeNi2.1 Eutectic High Entropy Alloy by Cryo-Rolling and Annealing.",
   "abstract": "Nano-lamellar (L1 2 + B2) AlCoCrFeNi 2.1 eutectic high entropy alloy (EHEA) was processed by cryo-rolling and annealing. The EHEA developed a novel hierarchical microstructure featured by fine lamellar regions consisting of FCC lamellae filled with ultrafine FCC grains (average size ~200-250 nm) and B2 lamellae, and coarse non-lamellar regions consisting of ultrafine FCC (average size ~200-250 nm), few coarse recrystallized FCC grains and rather coarse unrecrystallized B2 phase (~2.5 µm). This complex and hierarchical microstructure originated from differences in strain-partitioning amongst the constituent phases, affecting the driving force for recrystallization. The hierarchical microstructure of the cryo-rolled and annealed material resulted in simultaneous enhancement in strength (Yield Strength/YS: 1437 ± 26 MPa, Ultimate Tensile Strength/UTS: 1562 ± 33 MPa) and ductility (elongation to failure/e f ~ 14 ± 1%) as compared to the as-cast as well as cold-rolled and annealed materials. The present study for the first time demonstrated that cryo-deformation and annealing could be a novel microstructural design strategy for overcoming strength-ductility trade off in multiphase high entropy alloys."
  },
  {
   "id": 8,
   "title": "Dynamic Shear Deformation of a Precipitation Hardened Al0.7CoCrFeNi Eutectic High-Entropy Alloy Using Hat-Shaped Specimen Geometry.",
   "abstract": "Lamellar eutectic structure in Al 0.7 CoCrFeNi high-entropy alloy (HEA) is emerging as a promising candidate for structural applications because of its high strength-ductility combination. The alloy consists of a fine-scale lamellar fcc + B2 microstructure with high flow stresses > 1300 MPa under quasi-static tensile deformation and >10% ductility. The response to shear loading was not investigated so far. This is the first report on the shear deformation of a eutectic structured HEA and effect of precipitation on shear deformation. A split-Hopkinson pressure bar (SHPB) was used to compress the hat-shaped specimens to study the local dynamic shear response of the alloy. The change in the width of shear bands with respect to precipitation and deformation rates was studied. The precipitation of L1 2 phase did not delay the formation of adiabatic shear bands (ASB) or affect the ASB width significantly, however, the deformed region around ASB, consisting of high density of twins in fcc phase, was reduced from 80 µm to 20 µm in the stronger precipitation strengthened condition. We observe dynamic recrystallization of grains within ASBs and local mechanical response of individual eutectic lamellae before and after shear deformation and within the shear bands was examined using nano-indentation."
  },
  {
   "id": 9,
   "title": "Tuning Microstructure and Mechanical Performance of a Co-Rich Transformation-Induced Plasticity High Entropy Alloy.",
   "abstract": "Multi-principal element alloys and high-entropy alloys (HEAs) are emerging metallic materials with unprecedented structures and properties for various applications. In this study, we tuned the microstructure and mechanical performance of a recently designed high-performance Co-rich TRIP-HEA via thermomechanical processing (TMP). The microstructures of the HEA after various TMP routines were characterized, and their correlation with room-temperature tensile performance was clarified. The results showed that grain refinement is an effective strategy for enhancing strength while retaining satisfactory ductility. The formation of incoherent precipitates slightly improves the strength but inevitably sacrifices the ductility, which needs to be considered for optimizing the TMPs. The room temperature tensile yield strength and ultimate tensile strength were increased from 254.6 to 641.3 MPa and from 702.5 to 968.4 MPa, respectively, but the tensile elongation retains a satisfactory value of 68.8%. We herein provide important insights into the regulation of the microstructure and mechanical properties of TRIP-HEAs."
  },
  {
   "id": 10,
   "title": "Research on the Mechanism of Oxygen-Induced Embrittlement Fracturing in Industrial Electrolytic Nickel.",
   "abstract": "In this study, severe cracking occurred during an investigation of the direct hot rolling of industrial electrolytic nickel plates. To determine the cause of hot-rolling cracking, the microstructure phase composition was analyzed through the utilization of various techniques, including optical microscopy, scanning electron microscopy, electron backscattering diffraction, transmission electron microscopy (TEM), energy-dispersive X-ray spectroscopy (EDS) and electron probe micro-analysis. The comparative microstructural analysis took place between specimens heat treated in atmospheric and vacuum environments. The characterization and analysis of the hot-rolled plates considered the crack microstructure and fracture morphology. It was shown that holes appeared along the large angular grain boundaries after annealing at 1100 °C for 8 h. Possible reason: In a high-temperature environment, the decomposition of residual additives in the electrolytic nickel releases oxidizing gases, which oxidizes the grain boundaries. The reaction with carbon diffused into the grain boundaries and produced carbon monoxide gas, which induced holes and severely reduced the grain boundary plasticity. The heat treatment time did not need to be very long for severe grain boundary degradation to occur. After severe cavitation, the electrolytic nickel was severely cracked at grain boundaries cracks due to a shear force, and brittle fractures occurred along grains with very low plasticity."
  },
  {
   "id": 11,
   "title": "Microstructures and Mechanical Properties of an AlCoCrNiFe HEA/WC Reinforcing Particle Composite Coating Prepared by Laser Cladding.",
   "abstract": "In this study, an AlCoCrFeNi HEA coating with a 10% mass fraction of WC particles was fabricated on the surface of 316L stainless steel by laser cladding technology. WC powders were formed by the partial or total dissolution of the initial WC particles with different sizes in the AlCoCrFeNi HEA coating. Micron WC particles were dispersed in the coating homogeneously, and millimeter WC particles were deposited on the bottom of coating because of their high density. The addition of the WC powers prompted Columnar dendritic and cellular grains, observed in the bottom and top regions of the coating, respectively. Additionally, this led to a higher micro-hardness and better corrosion resistance than that of the pure HEA coating."
  },
  {
   "id": 12,
   "title": "Factors Affecting the Microstructure, Tensile Properties and Corrosion Resistance of AA7075 Forgings.",
   "abstract": "AA7075 alloys are high strength alloys and are used as an important material for making engineering parts. Forged AA7075 alloys showed significantly decreased toughness when the material was hot deformed at a high temperature. This study investigated the effects of forging parameters on the tensile properties and the microstructure of AA7075 forgings. The tensile properties and corrosion resistance of different forgings were determined to be correlated with their microstructures. The experiment annealed and hot-deformed sample bars at 633 K, cold-deformed them at room temperature (RF), and at sub-zero temperatures (CF). After T73 heat treatment, the microstructures depended on the deformation temperature. This varied significantly, from elongated grains for hot-forged samples to equiaxial grains for cold-deformed samples. The hot-deformed samples had a tensile strength of 592 MPa for UTS, 538 MPa for YS, and 13.4% for elongation. These were stronger but less elongated than the cold-deformed samples. All hot-deformed (HF), RF, and CF samples exhibited mechanical properties that exceeded UTS > 505 MPa, YS > 435 MPa, and an elongation > 13%, and showed moderate corrosion resistance if samples were in contact with a 3.5 wt.% NaCl solution. The toughness of the forgings could be significantly improved by decreasing the forging temperatures. The corrosion resistance of AA7075-T73 forgings was affected by the total grain boundary (GB) lengths per unit area and the 2nd phase particle"
  },
  {
   "id": 13,
   "title": "Cryogenic strength improvement by utilizing room-temperature deformation twinning in a partially recrystallized VCrMnFeCoNi high-entropy alloy.",
   "abstract": "The excellent cryogenic tensile properties of the CrMnFeCoNi alloy are generally caused by deformation twinning, which is difficult to achieve at room temperature because of insufficient stress for twinning. Here, we induced twinning at room temperature to improve the cryogenic tensile properties of the CrMnFeCoNi alloy. Considering grain size effects on the critical stress for twinning, twins were readily formed in the coarse microstructure by cold rolling without grain refinement by hot rolling. These twins were retained by partial recrystallization and played an important role in improving strength, allowing yield strengths approaching 1 GPa. The persistent elongation up to 46% as well as the tensile strength of 1.3 GPa are attributed to additional twinning in both recrystallized and non-recrystallization regions. Our results demonstrate that non-recrystallized grains, which are generally avoided in conventional alloys because of their deleterious effect on ductility, can be useful in achieving high-strength high-entropy alloys."
  },
  {
   "id": 14,
   "title": "Effect of oxidation at an elevated temperature on the evolution of phases, microstructure, and properties of the oxide films formed on the surface of TiZr.",
   "abstract": "This study examined the evolution of the microstructure, microhardness, corrosion resistance, and selective leaching properties of oxide films formed on the surface of a Ti-50Zr (%) alloy during heat treatment at 600 °C for various time intervals. According to our experimental results, the growth and evolution of oxide films can be divided into three stages. In stage I (heat treatment for less than 2 min), ZrO 2 was first formed on the surface of the TiZr alloy, which slightly improved its corrosion resistance. In stage II (heat treatment for 2-10 min), the initially generated ZrO 2 is gradually transformed into ZrTiO 4 from the top to the bottom of the surface layer. The formation of ZrTiO 4 significantly improves the microhardness and corrosion resistance of the alloy. In stage III (heat treatment for more than 10 min), microcracks appeared and propagated on the surface of the ZrTiO 4 film, deteriorating the surface properties of the alloy. The ZrTiO 4 began to peel off after heat treatment for more than 60 min. The untreated and heat-treated TiZr alloys exhibited excellent selective leaching properties in Ringer's solution, whereas a trace amount of suspended ZrTiO 4 oxide particles formed in the solution after soaking the 60 min heat-treated TiZr alloy for 120 days. Surface modification of the TiZr alloy by generating an intact ZrTiO 4 oxide film effectively improved its microhardness and corrosion resistance; however, oxidation should be performed appropriately to obtain"
  },
  {
   "id": 15,
   "title": "Microstructure and Properties of Mg-Gd-Y-Zn-Mn High-Strength Alloy Welded by Friction Stir Welding.",
   "abstract": "Mg-Gd-Y-Zn-Mn (MVWZ842) is a kind of high rare earth magnesium alloy with high strength, high toughness and multi-scale strengthening mechanisms. After heat treatment, the maximum tensile strength of MVWZ842 alloy is more than 550 MPa, and the elongation is more than 5%. Because of its great mechanical properties, MVWZ842 has broad application potential in aerospace and rail transit. However, the addition of high rare earth elements makes the deformation resistance of MVWZ842 alloy increase to some extent. This leads to the difficulty of direct plastic processing forming and large structural part shaping. Friction stir welding (FSW) is a convenient fast solid-state joining technology. When FSW is used to weld MVWZ842 alloy, small workpieces can be joined into a large one to avoid the problem that large workpieces are difficult to form. In this work, a high-quality joint of MVWZ842 alloy was achieved by FSW. The microstructure and properties of this high-strength magnesium alloy after friction stir welding were studied. There was a prominent onion ring characteristic in the nugget zone. After the base was welded, the stacking fault structure precipitated in the grain. There were a lot of broken long period stacking order (LPSO) phases on the retreating side of the nugget zone, which brought the effect of precipitation strengthening. Nano-α-Mn and the broken second phase dispersed in the matrix in the nugget zone, which made the grains refine. A relatively complete dynamic recr"
  },
  {
   "id": 16,
   "title": "Ultrastrong ductile and stable high-entropy alloys at small scales.",
   "abstract": "Refractory high-entropy alloys (HEAs) are a class of emerging multi-component alloys, showing superior mechanical properties at elevated temperatures and being technologically interesting. However, they are generally brittle at room temperature, fail by cracking at low compressive strains and suffer from limited formability. Here we report a strategy for the fabrication of refractory HEA thin films and small-sized pillars that consist of strongly textured, columnar and nanometre-sized grains. Such HEA pillars exhibit extraordinarily high yield strengths of ∼ 10 GPa--among the highest reported strengths in micro-/nano-pillar compression and one order of magnitude higher than that of its bulk form--and their ductility is considerably improved (compressive plastic strains over 30%). Additionally, we demonstrate that such HEA films show substantially enhanced stability for high-temperature, long-duration conditions (at 1,100 °C for 3 days). Small-scale HEAs combining these properties represent a new class of materials in small-dimension devices potentially for high-stress and high-temperature applications."
  },
  {
   "id": 17,
   "title": "Effect of Sm + Er and Heat Treatment on As-Cast Microstructure and Mechanical Properties of 7055 Aluminum Alloy.",
   "abstract": "The 7055 aluminum alloy is an ultra-high strength aluminum alloy, which is widely used in the aerospace field and new energy automobile manufacturing industry. As it retains high strength, its plastic deformation ability needs to be improved, which limits its application in plastic processing. In this study, the cast grains of the 7055 aluminum alloy were refined by adding Sm + Er, and the proper heat treatment procedure was utilized to further precipitate the rare earth phase in order to increase the alloy's strength and toughness. The grain size, microstructure and phase were characterized by optical microscopes (OMs), scanning electron microscopy-energy spectrum (SEM-EDS) and a XRD diffractometer (XRD). The macroscopic hardness, yield strength and tensile strength of alloy materials were measured by a hardness meter and universal electronic tensile machine. The results showed that the as-cast sample and the heat treatment sample all contained Al 10 Cu 7 Sm 2 and Al 8 Cu 4 Er rare earth phases. But, after heat treatment, the volume percentage of the rare earth phase dramatically increased and the dispersion was more unified. When 0.3 wt.%Sm and 0.1 wt.%Er were added, the grain size could be refined to 53 μm. With the increase in the total content of rare earth elements, the refining effect first increased and then decreased. Under 410 °C solid solution for 2 h + 150 °C and aging for 12 h, the macroscopic hardness, yield strength, tensile strength and elongation of 0.3 wt.%S"
  },
  {
   "id": 18,
   "title": "Corrosion Resistance of Laser Powder Bed Fused AISI 316L Stainless Steel and Effect of Direct Annealing.",
   "abstract": "Alloy parts produced by an additive manufacturing method with rapid heat transfer from fast melting and solidification have different microstructures, characteristics, and performances compared with materials made by the conventional process. In this study, the corrosion and oxidation resistance of SS316L, which was prepared by the powder bed fusion process, was compared with those of cold-rolled SS316L. Additionally, the surface oxide film on stainless steel was thoroughly assessed since the film has the greatest influence on the corrosion and oxidation resistance. The effect of heat treatment on corrosion and oxidation resistance of SS316L fabricated by additive manufacturing was investigated. The SS316L has a microstructure formed by sub-grain cells, in which locally concentrated alloying elements form a stable passive film. As a result, it has a higher level of corrosion resistance and oxidation resistance than conventional cold-rolled materials. However, it was confirmed that the sub-grain cell was removed by heat treatment, which resulted in the degradation of corrosion and oxidation resistance."
  },
  {
   "id": 19,
   "title": "Microstructural Assessment, Mechanical and Corrosion Properties of a Mg-Sr Alloy Processed by Combined Severe Plastic Deformation.",
   "abstract": "The development of high-performance biodegradable alloys with controllable corrosion rates to be used for manufacturing advanced implants is a hot topic of modern materials science and biomedicine. This work features the changes in microstructure, corrosion behavior and mechanical properties of the Mg-2 wt.%Sr alloy progressively induced by equal-channel angular pressing, high-pressure torsion and annealing. We show that such processing leads to significant microstructure refinement including diminishing grain size, defect accumulation and fragmentation of the initial eutectics. We demonstrate that the application of severe plastic deformation and heat treatment is capable of considerably enhancing the mechanical and corrosion performance of a biodegradable alloy of the Mg-Sr system. The best trade-off between strength, plasticity and the corrosion resistance has been achieved by annealing of the Mg-Sr alloy subjected to combined severe plastic deformation processing."
  },
  {
   "id": 20,
   "title": "High-Temperature Mechanical Properties of NbTaHfTiZrV0.5 Refractory High-Entropy Alloys.",
   "abstract": "The NbTaHfTiZrV 0.5 is a refractory multi-principal-element alloy with high strength and good ductility at room temperature. It is important for possible high-temperature applications to investigate the deformation mechanism of the NbTaHfTiZrV 0.5 alloy at different temperatures using tensile tests. In this investigation, the tensile tests were conducted at room temperature to 1273 K on sheet materials fabricated by cold rolling combined with annealing treatments. At 473 K, the NbTaHfTiZrV 0.5 alloy exhibited a high tensile ductility (12%). At a testing temperature range of 673~873 K, the ductility was reduced, but the yield strength remained above 800 MPa, which is rare in most other alloys. The TEM investigations revealed that a dislocation slip controlled the plastic deformation, and the degree of deformation was closely related to the dislocation density. The true stress-strain curves of the alloy under different deformation conditions were obtained by tensile deformation at different deformation temperatures (673~873 K) and strain rates (0.001~0.0005 s -1 ). Experimental results were utilized to construct the parameters of a constitutive model based on a traditional mathematical model to predict the flow behavior at high temperatures. The excellent high-temperature mechanical properties of the NbTaHfTiZrV 0.5 alloy will enable it to be used in several engineering applications."
  }
 ]
}
```

Batch 1, output (parsed):

```json
{
 "grades": [
  {
   "id": 1,
   "grade": 1,
   "why": "Different material system and property focus."
  },
  {
   "id": 2,
   "grade": 1,
   "why": "Different material system and property focus."
  },
  {
   "id": 3,
   "grade": 1,
   "why": "Different material system and property focus."
  },
  {
   "id": 4,
   "grade": 1,
   "why": "Different material system and property focus."
  },
  {
   "id": 5,
   "grade": 1,
   "why": "Different material system and property focus."
  },
  {
   "id": 6,
   "grade": 1,
   "why": "Different material system and property focus."
  },
  {
   "id": 7,
   "grade": 3,
   "why": "Directly addresses strength and plasticity in AlCoCrFeNi2.1 EHEA."
  },
  {
   "id": 8,
   "grade": 2,
   "why": "Related material system but different composition and focus."
  },
  {
   "id": 9,
   "grade": 1,
   "why": "Different material system and property focus."
  },
  {
   "id": 10,
   "grade": 1,
   "why": "Different material system and property focus."
  },
  {
   "id": 11,
   "grade": 1,
   "why": "Different material system and property focus."
  },
  {
   "id": 12,
   "grade": 1,
   "why": "Different material system and property focus."
  },
  {
   "id": 13,
   "grade": 1,
   "why": "Different material system and property focus."
  },
  {
   "id": 14,
   "grade": 1,
   "why": "Different material system and property focus."
  },
  {
   "id": 15,
   "grade": 1,
   "why": "Different material system and property focus."
  },
  {
   "id": 16,
   "grade": 1,
   "why": "Different material system and property focus."
  },
  {
   "id": 17,
   "grade": 1,
   "why": "Different material system and property focus."
  },
  {
   "id": 18,
   "grade": 1,
   "why": "Different material system and property focus."
  },
  {
   "id": 19,
   "grade": 1,
   "why": "Different material system and property focus."
  },
  {
   "id": 20,
   "grade": 1,
   "why": "Different material system and property focus."
  }
 ]
}
```

All batches (title and grade; the full inputs are in example_trace.json):

| Batch | Id | Grade | Why | Title |
|---:|---:|---:|---|---|
| 1 | 1 | 1 | Different material system and property focus. | Tuning Corrosion Resistance and AC Soft Magnetic Properties of Fe-Co-Ni-Al Medium-Entropy Alloy via Ni Content |
| 1 | 2 | 1 | Different material system and property focus. | Effect of BASC and BASCA Heat Treatment on Microstructure and Mechanical Properties of TC10 Titanium Alloy. |
| 1 | 3 | 1 | Different material system and property focus. | Influence of Sintering Atmosphere, Temperature and the Solution-Annealing Treatment on the Properties of Preci |
| 1 | 4 | 1 | Different material system and property focus. | Effect of Ultrasonic-Assisted Modification Treatment on the Microstructure and Properties of A356 Alloy. |
| 1 | 5 | 1 | Different material system and property focus. | Micromechanical Modeling of AlSi10Mg Processed by Laser-Based Additive Manufacturing: From as-Built to Heat-Tr |
| 1 | 6 | 1 | Different material system and property focus. | Relationship between Texture, Hydrogen Content, Residual Stress and Corrosion Resistance of Electrodeposited C |
| 1 | 7 | 3 | Directly addresses strength and plasticity in AlCoCrFeNi2.1 EHEA. | Simultaneous Strength-Ductility Enhancement of a Nano-Lamellar AlCoCrFeNi2.1 Eutectic High Entropy Alloy by Cr |
| 1 | 8 | 2 | Related material system but different composition and focus. | Dynamic Shear Deformation of a Precipitation Hardened Al0.7CoCrFeNi Eutectic High-Entropy Alloy Using Hat-Shap |
| 1 | 9 | 1 | Different material system and property focus. | Tuning Microstructure and Mechanical Performance of a Co-Rich Transformation-Induced Plasticity High Entropy A |
| 1 | 10 | 1 | Different material system and property focus. | Research on the Mechanism of Oxygen-Induced Embrittlement Fracturing in Industrial Electrolytic Nickel. |
| 1 | 11 | 1 | Different material system and property focus. | Microstructures and Mechanical Properties of an AlCoCrNiFe HEA/WC Reinforcing Particle Composite Coating Prepa |
| 1 | 12 | 1 | Different material system and property focus. | Factors Affecting the Microstructure, Tensile Properties and Corrosion Resistance of AA7075 Forgings. |
| 1 | 13 | 1 | Different material system and property focus. | Cryogenic strength improvement by utilizing room-temperature deformation twinning in a partially recrystallize |
| 1 | 14 | 1 | Different material system and property focus. | Effect of oxidation at an elevated temperature on the evolution of phases, microstructure, and properties of t |
| 1 | 15 | 1 | Different material system and property focus. | Microstructure and Properties of Mg-Gd-Y-Zn-Mn High-Strength Alloy Welded by Friction Stir Welding. |
| 1 | 16 | 1 | Different material system and property focus. | Ultrastrong ductile and stable high-entropy alloys at small scales. |
| 1 | 17 | 1 | Different material system and property focus. | Effect of Sm + Er and Heat Treatment on As-Cast Microstructure and Mechanical Properties of 7055 Aluminum Allo |
| 1 | 18 | 1 | Different material system and property focus. | Corrosion Resistance of Laser Powder Bed Fused AISI 316L Stainless Steel and Effect of Direct Annealing. |
| 1 | 19 | 1 | Different material system and property focus. | Microstructural Assessment, Mechanical and Corrosion Properties of a Mg-Sr Alloy Processed by Combined Severe  |
| 1 | 20 | 1 | Different material system and property focus. | High-Temperature Mechanical Properties of NbTaHfTiZrV0.5 Refractory High-Entropy Alloys. |
| 2 | 1 | 2 | Discusses strengthening mechanisms relevant to HEAs. | Interstitial atoms enable joint twinning and transformation induced plasticity in strong and ductile high-entr |
| 2 | 2 | 3 | Directly studies AlCoCrFeNi2.1 with focus on mechanical properties. | Small-scale mechanical behavior of a eutectic high entropy alloy. |
| 2 | 3 | 3 | Directly evaluates corrosion behavior of AlCoCrFeNi2.1. | Molten Salt Corrosion Behavior of Dual-Phase High Entropy Alloy for Concentrating Solar Power Systems. |
| 2 | 4 | 2 | Discusses heterogeneous grain structures for strength and ductility. | Dynamically reinforced heterogeneous grain structure prolongs ductility in a medium-entropy alloy with gigapas |
| 2 | 5 | 1 | Focuses on Fe-Mn-Ti steel, not directly relevant to HEAs. | Heterogeneous Multi-Phase Grains Improving the Strength-Ductility Balance in Warm-Rolled Fe-18Mn-3Ti Steel. |
| 2 | 6 | 3 | Directly studies damage tolerance in AlCoCrFeNi2.1. | Phase-Specific Damage Tolerance of a Eutectic High Entropy Alloy. |
| 2 | 7 | 1 | Focuses on a different HEA and unrelated processing method. | Effects of Heat Treatment on the Microstructure and Mechanical Properties of a Dual-Phase High-Entropy Alloy F |
| 2 | 8 | 1 | Focuses on dual-phase steel, not relevant to HEAs. | Influence of Annealing and Aging Parameters on the Microstructure and Properties of 1200 MPa Grade Cold-Rolled |
| 2 | 9 | 0 | Focuses on stainless steel, unrelated to the question. | Ion Implantation Combined with Heat Treatment Enables Excellent Conductivity and Corrosion Resistance of Stain |
| 2 | 10 | 2 | Discusses precipitation strengthening in a related HEA. | Influence of ordered L12 precipitation on strain-rate dependent mechanical behavior in a eutectic high entropy |
| 2 | 11 | 1 | Focuses on Al alloy composites, not directly relevant. | Effects of Heat Treatment on the Interface Microstructure and Mechanical Properties of Friction-Stir-Processed |
| 2 | 12 | 1 | Focuses on AlCrCuFeNi, a different HEA system. | Non-Aqueous Electrodeposition and Characterization of AlCrCuFeNi High Entropy Alloy Thin Films. |
| 2 | 13 | 0 | Focuses on aluminum alloy, unrelated to HEAs. | The Influence of Heat Treatment on the Mechanical Properties and Corrosion Resistance of the Ultrafine-Grained |
| 2 | 14 | 1 | Focuses on a different HEA system and high-temperature properties. | Effects of Cr Content on Microstructure and Mechanical Properties of Co-Free FeCryNiAl0.8 High-Entropy Alloys. |
| 2 | 15 | 0 | Focuses on low-carbon steel, unrelated to HEAs. | The corrosion behavior of low carbon steel (AISI 1010) influenced by grain size through microstructural mechan |
| 2 | 16 | 0 | Focuses on stainless steel, unrelated to HEAs. | Deformation-Induced Martensitic Transformation in Laser Cladded 304 Stainless Steel Coatings. |
| 2 | 17 | 1 | Focuses on CoCrFeMnNi HEA, not AlCoCrFeNi2.1. | Plane-Stress Deformation Behavior of CoCrFeMnNi High-Entropy Alloy Sheet under Low Temperatures. |
| 2 | 18 | 0 | Focuses on biomedical HEA, unrelated to the question. | Solid-State Processing of CoCrMoNbTi High-Entropy Alloy for Biomedical Applications. |
| 2 | 19 | 0 | Focuses on Al-Sc foams, unrelated to HEAs. | Homogeneous Age-hardening of Large-sized Al-Sc Foams via Micro-alloying with Zr and Ti. |
| 2 | 20 | 0 | Focuses on Inconel superalloy, unrelated to HEAs. | Achieving High Strength and Creep Resistance in Inconel 740H Superalloy through Wire-Arc Additive Manufacturin |
| 3 | 1 | 0 | Focuses on stainless steel, not high-entropy alloys or related properties. | Effect of Heat Treatment on Crevice Corrosion Behavior of 304 Stainless Steel Clad Plate in Seawater Environme |
| 3 | 2 | 3 | Directly studies AlCoCrFeNi2.1 EHEA and effects of alloying on strength and plasticity. | Effect of Alloying on Microstructure and Mechanical Properties of AlCoCrFeNi2.1 Eutectic High-Entropy Alloy. |
| 3 | 3 | 2 | Discusses corrosion resistance in related HEAs, but not AlCoCrFeNi2.1. | Effect of Ti Content on the Microstructure and Corrosion Resistance of CoCrFeNiTix High Entropy Alloys Prepare |
| 3 | 4 | 1 | Focuses on aluminum alloys, unrelated to high-entropy alloys. | Application of New Al-Si Welding Filler with High Concentration of Copper and Magnesium: High-Temperature Stre |
| 3 | 5 | 0 | Focuses on aluminum alloys, unrelated to high-entropy alloys or properties. | Effect of Heat Treatment States of Feedstock on the Microstructure and Mechanical Properties of AA2219 Layers  |
| 3 | 6 | 2 | Discusses high-temperature creep in refractory HEAs, relevant to the question. | Effect of Al Content on Microstructure and Properties of Al&lt;sub&gt;x&lt;/sub&gt;Cr&lt;sub&gt;0.2&lt;/sub&gt |
| 3 | 7 | 0 | Focuses on Al-Si alloys, unrelated to high-entropy alloys or properties. | Effect of Semisolid and Heat Treatment Process on Microstructural Refinement of Al-7Si Alloy. |
| 3 | 8 | 0 | Focuses on aluminum alloys, unrelated to high-entropy alloys or properties. | The Effect of Extrusion and Heat Treatment on the Microstructure and Tensile Properties of 2024 Aluminum Alloy |
| 3 | 9 | 3 | Proposes phase-selective recrystallization to improve ductility in EHEAs. | Phase-selective recrystallization makes eutectic high-entropy alloys ultra-ductile. |
| 3 | 10 | 2 | Discusses creep and high-temperature behavior in HEAs, relevant but not AlCoCrFeNi2.1. | The High Temperature Tensile and Creep Behaviors of High Entropy Superalloy. |
| 3 | 11 | 1 | Focuses on FCC HEAs in cryogenic environments, tangentially relevant. | Local chemical order enables an ultrastrong and ductile high-entropy alloy in a cryogenic environment. |
| 3 | 12 | 0 | Focuses on medium carbon steel, unrelated to high-entropy alloys or properties. | The Effect of Multi-Step Tempering and Partition Heat Treatment on 25Cr2Ni3MoV Steel's Cryogenic Strength Prop |
| 3 | 13 | 2 | Discusses strengthening mechanisms in HEAs, relevant to the question. | Hierarchical microstructure strengthening in a single crystal high entropy superalloy. |
| 3 | 14 | 0 | Focuses on ferritic stainless steel, unrelated to high-entropy alloys or properties. | Effect of Cold-Rolling Reduction on Recrystallization Microstructure, Texture and Corrosion Properties of the  |
| 3 | 15 | 0 | Focuses on Ti-Zr-Mo alloy, unrelated to high-entropy alloys or properties. | Enhanced Mechanical and Corrosion Properties via Annealing Treatment on the Hot-Rolled Ti-Zr-Mo Alloy. |
| 3 | 16 | 3 | Directly studies AlCoCrFeNi2.1 EHEA and its thermal stability and corrosion. | Thermal Stability and Hot Corrosion Performance of the AlCoCrFeNi2.1 High-Entropy Alloy Coating by Laser Cladd |
| 3 | 17 | 0 | Focuses on Ni-P/Ni-B coatings, unrelated to high-entropy alloys or properties. | Synthesis, structure characterization, and corrosion properties of duplex electroless Ni-P/Ni-B and Ni-P/Ni-B- |
| 3 | 18 | 0 | Focuses on Cr coatings, unrelated to high-entropy alloys or properties. | Deformation and Annealing Behavior of Cr Coating Prepared by Pack-Cementation on the Surface of Austenitic Sta |
| 3 | 19 | 0 | Focuses on Inconel 718, unrelated to high-entropy alloys or properties. | Effect of heat treatment on microstructure and mechanical properties of selective laser melted Inconel 718 all |
| 3 | 20 | 0 | Focuses on biomedical coatings, unrelated to high-entropy alloys or properties. | Microstructure and Selected Properties of Advanced Biomedical n-HA/ZnS/Sulfonated PEEK Coatings Fabricated on  |
| 4 | 1 | 3 | Directly addresses AlCoCrFeNi2.1 EHEA with improved strength and plasticity. | From Small Data Modeling to Large Language Model Screening: A Dual-Strategy Framework for Materials Intelligen |
| 4 | 2 | 1 | Focuses on CoCrNi alloy, not AlCoCrFeNi2.1 or its limitations. | Effect of Annealing on Microstructure and Tensile Behavior of CoCrNi Medium Entropy Alloy Processed by High-Pr |
| 4 | 3 | 3 | Directly studies AlCoCrFeNi EHEA and strengthening mechanisms. | The Exceptional Strong Face-centered Cubic Phase and Semi-coherent Phase Boundary in a Eutectic Dual-phase Hig |
| 4 | 4 | 1 | Focuses on VCrFeTaW HEAs, not AlCoCrFeNi2.1 or its limitations. | A Novel Low-Activation VCrFeTaxWx (x = 0.1, 0.2, 0.3, 0.4, and 1) High-Entropy Alloys with Excellent Heat-Soft |
| 4 | 5 | 1 | Focuses on Fe-Mn-Co-Cr HEA, unrelated to AlCoCrFeNi2.1. | Improving Mechanical Properties of Fe-Mn-Co-Cr High-Entropy Alloy via Annealing after Cold Rolling. |
| 4 | 6 | 1 | Focuses on AlTiVNb HEA film, unrelated to AlCoCrFeNi2.1. | A Lightweight AlTiVNb High-Entropy Alloy Film with High Strength-Ductility Synergy and Corrosion Resistance. |
| 4 | 7 | 0 | Focuses on duplex stainless steel, unrelated to HEAs. | Effect of Sigma Phase Morphology on the Degradation of Properties in a Super Duplex Stainless Steel. |
| 4 | 8 | 0 | Focuses on low-alloy steel, unrelated to HEAs. | Effects of Heat Treatment on Microstructures and Mechanical Properties of a Low-Alloy Cylinder Liner. |
| 4 | 9 | 2 | Discusses SCC mechanisms in Fe/Ni/Cr alloy, relevant to corrosion. | Mechanisms of chemical-reaction-induced tensile deformation of an Fe/Ni/Cr alloy revealed by reactive atomisti |
| 4 | 10 | 0 | Focuses on titanium alloy, unrelated to HEAs. | The Influence of Heat Treatment on the Tensile Creep Life of the TC25 Titanium Alloy. |
| 4 | 11 | 0 | Focuses on titanium alloy, unrelated to HEAs. | Effect of Hydrothermal and Vapor Thermal Treatments on Apatite Inductivity of Titanate Nanotubes on Anodized T |
| 4 | 12 | 0 | Focuses on 12CrNi2 alloy steel, unrelated to HEAs. | Quenching and Tempering-Dependent Evolution on the Microstructure and Mechanical Performance Based on a Laser  |
| 4 | 13 | 2 | Discusses Si addition effects on CoCrFeMnNi HEAs, relevant to corrosion. | Study on the Microstructure, Mechanical Properties, and Corrosion Behavior of 900 °C-Annealed CoCrFeMnNiSix (X |
| 4 | 14 | 1 | Focuses on Al0.3CoCrFeNi HEA, not AlCoCrFeNi2.1. | High-velocity deformation of Al0.3CoCrFeNi high-entropy alloy: Remarkable resistance to shear failure. |
| 4 | 15 | 2 | Discusses Co-free AlCrFeNi EHEAs, related to AlCoCrFeNi2.1. | Rapid Design, Microstructures, and Properties of Low-Cost Co-Free Al-Cr-Fe-Ni Eutectic Medium Entropy Alloys. |
| 4 | 16 | 1 | Focuses on Fe-Co-Cr-Ni-Mo-C MEA, not AlCoCrFeNi2.1. | Unveiling the Stacking Fault-Driven Phase Transition Delaying Cryogenic Fracture in Fe-Co-Cr-Ni-Mo-C-Based Med |
| 4 | 17 | 1 | Focuses on stainless steel, unrelated to AlCoCrFeNi2.1. | Femtosecond Laser Treatment for Improving the Corrosion Resistance of Selective Laser Melted 17-4PH Stainless  |
| 4 | 18 | 2 | Discusses AlCoCrFeNiSi HEA, relevant to coatings and corrosion. | Microstructural Evolution of AlCoCrFeNiSi High-Entropy Alloy Powder during Mechanical Alloying and Its Coating |
| 4 | 19 | 2 | Discusses AlCoCrFeNiTi HEA, relevant to wear resistance. | Enhanced Wear Behaviour of Spark Plasma Sintered AlCoCrFeNiTi High-Entropy Alloy Composites. |
| 4 | 20 | 3 | Directly addresses AlCoCrFeNi2.1 EHEA with strength-ductility improvement. | Nanostructuring with Structural-Compositional Dual Heterogeneities Enhances Strength-Ductility Synergy in Eute |
| 5 | 1 | 1 | Different material system; focus on stainless steel and cryo-plastic deformation. | Development of Mechanical Properties of Stainless Steel 316LN-IG after Cryo-Plastic Deformation. |
| 5 | 2 | 1 | Different material system; focus on Al-Li alloys, not high-entropy alloys. | Homogenization heat treatment influence on microstructure evolution and mechanical properties of as-cast Al-Li |
| 5 | 3 | 1 | Different material system; focus on magnesium alloys, not high-entropy alloys. | Effect of Zinc and Severe Plastic Deformation on Mechanical Properties of AZ61 Magnesium Alloy. |
| 5 | 4 | 0 | Unrelated; focuses on machining parameters for titanium alloy. | Optimization of machining parameters for turning operation of heat-treated Ti-6Al-3Mo-2Nb-2Sn-2Zr-1.5Cr alloy  |
| 5 | 5 | 1 | Different material system; focus on Inconel 718, not high-entropy alloys. | Influence of Different Build Orientations and Heat Treatments on the Creep Properties of Inconel 718 Produced  |
| 5 | 6 | 1 | Different material system; focus on aluminum alloy 7075, not high-entropy alloys. | Increasing the Mechanical Strength and Corrosion Resistance of Aluminum Alloy 7075 via Hydrostatic Extrusion a |
| 5 | 7 | 2 | Relevant; discusses corrosion resistance in a related high-entropy alloy system. | Phase, Microstructure and Corrosion Behaviour of Al0.3FeCoNiCrx High-Entropy Alloys via Cr Addition. |
| 5 | 8 | 2 | Relevant; focuses on AlCoCrFeNi HEA coatings, related to the material system. | Process Parameters Optimization and Numerical Simulation of AlCoCrFeNi High-Entropy Alloy Coating via Laser Cl |
| 5 | 9 | 2 | Relevant; discusses strength improvement in a related medium entropy alloy. | Effect of Si on Microstructure and Mechanical Properties of FeCrNi Medium Entropy Alloys. |
| 5 | 10 | 3 | Directly on point; same material system and addresses strength-ductility improvement. | Enhanced strength-ductility synergy in ultrafine-grained eutectic high-entropy alloys by inheriting microstruc |
| 5 | 11 | 2 | Relevant; discusses microstructural changes and wear behavior in a related HEA. | Influence of Titanium on Microstructure, Phase Formation and Wear Behaviour of AlCoCrFeNiTix High-Entropy Allo |
| 5 | 12 | 0 | Unrelated; focuses on paints for corrosion protection, not high-entropy alloys. | Corrosion Protection and Heat Resistance of Paints for Outdoor Use. |
| 5 | 13 | 1 | Tangential; focuses on titanium alloys, not high-entropy alloys. | Optimization of the Post-Process Heat Treatment Strategy for a Near-α Titanium Base Alloy Produced by Laser Po |
| 5 | 14 | 1 | Tangential; focuses on Al2O3-TiO2 coatings, not high-entropy alloys. | Effect of Vacuum Heat Treatment on the Element Diffusion Behavior and Corrosion Resistance of Al2O3-3wt.%TiO2  |
| 5 | 15 | 1 | Tangential; focuses on duplex stainless steels, not high-entropy alloys. | Validation of the Powder Metallurgical Processing of Duplex Stainless Steels through Hot Isostatic Pressing wi |
| 5 | 16 | 1 | Tangential; focuses on 17-4PH stainless steel, not high-entropy alloys. | 17-4 Precipitation-Hardening Stainless Steel: Soft-Tough Heat Treatment Mechanism and Thermal Fatigue Characte |
| 5 | 17 | 2 | Relevant; discusses mechanical and corrosion properties of a refractory HEA. | Refractory CrMoNbWV High-Entropy Alloy Manufactured by Mechanical Alloying and Spark Plasma Sintering: Evoluti |
| 5 | 18 | 1 | Tangential; focuses on gear steel, not high-entropy alloys. | The Effect of Cyclic Heat Treatment on the Microstructure and Mechanical Properties of 18CrNiMo7-6 Gear Steel. |
| 5 | 19 | 2 | Relevant; discusses mechanical properties of refractory HEAs. | Ab initio-predicted micro-mechanical performance of refractory high-entropy alloys. |
| 5 | 20 | 2 | Relevant; discusses creep deformation in a related high-entropy alloy. | Intermediate-Temperature Creep Deformation and Microstructural Evolution of an Equiatomic FCC-Structured CoCrF |
| 6 | 1 | 1 | Different material system, focus on oxidation. | Modeling Oxidation of AlCoCrFeNi High-Entropy Alloy Using Stochastic Cellular Automata. |
| 6 | 2 | 1 | Different material class, focus on borides. | High-Entropy Borides under Extreme Environment of Pressures and Temperatures. |
| 6 | 3 | 1 | Different material system, focus on maraging steels. | Integrated Computing Accelerates Design and Performance Control of New Maraging Steels. |
| 6 | 4 | 1 | Different material system, focus on Mg alloys. | Effect of heat treatment on corrosion behavior of Mg-5Gd-3Y-0.5Zr alloy. |
| 6 | 5 | 2 | Relevant mechanism: nanoprecipitates for strength improvement. | High-content ductile coherent nanoprecipitates achieve ultrastrong high-entropy alloys. |
| 6 | 6 | 1 | Different material system, focus on RHEAs. | Origin of age softening in the refractory high-entropy alloys. |
| 6 | 7 | 2 | Relevant mechanism: deformation-induced amorphization. | Amorphization in extreme deformation of the CrMnFeCoNi high-entropy alloy. |
| 6 | 8 | 2 | Relevant mechanism: serrated grain boundaries for creep resistance. | Effect of serrated grain boundary on tensile and creep properties of a precipitation strengthened high entropy |
| 6 | 9 | 1 | Different material system, focus on Fe-based amorphous alloys. | The Effect of Heat Treatment on the Corrosion Resistance of Fe-Based Amorphous Alloy Coating Prepared by High  |
| 6 | 10 | 1 | Different material system, focus on Mg alloys. | Effect of Heat Treatments on the Corrosion Resistance of a High Strength Mg-Gd-Y-Zn-Zr Alloy. |
| 6 | 11 | 2 | Relevant mechanism: B2 precipitates for strength enhancement. | Microstructural Evolution and Tensile Properties of Al0.3CoCrFeNi High-Entropy Alloy Associated with B2 Precip |
| 6 | 12 | 3 | Directly on point: AlCoCrFeNi alloy, mechanical improvement. | Microstructure and composition dependence of mechanical characteristics of nanoimprinted AlCoCrFeNi high-entro |
| 6 | 13 | 1 | Different material system, focus on Al-Zn-Mg alloys. | Effect of Multistage Solution Aging Heat Treatment on Mechanical Properties and Precipitated Phase Characteris |
| 6 | 14 | 1 | Different material system, focus on TiVNb alloy. | Lightweight TiVNb medium-entropy alloy with weak strength dependence on temperature. |
| 6 | 15 | 3 | Directly on point: AlCoCrFeNi2.1 alloy, corrosion behavior. | Corrosion Behavior of the AlCoCrFeNi2.1 Eutectic High-Entropy Alloy in Chloride-Containing Sulfuric Acid Solut |
| 6 | 16 | 1 | Different material system, focus on CoCrFeNiMn alloy. | Mechanistic understanding of speciated oxide growth in high entropy alloys. |
| 6 | 17 | 1 | Different material system, focus on NiCoCrAlTi alloy. | Microstructure and Properties of NiCoCrAlTi High Entropy Alloy Prepared Using MA-SPS Technique. |
| 6 | 18 | 1 | Different material system, focus on ferritic stainless steel. | Microstructures and Properties of a Low-Carbon-Chromium Ferritic Stainless Steel Treated by a Quenching and Pa |
| 6 | 19 | 3 | Directly on point: AlCoCrFeNi2.1 alloy, mechanical properties. | A promising new class of high-temperature alloys: eutectic high-entropy alloys. |
| 6 | 20 | 1 | Different material system, focus on titanium implants. | Residual Stress Homogenization of Hybrid Implants. |

Citation expansion (papers co-cited by at least two selected papers), screened the same way:

```json
{
 "input": {
  "question": "For an AlCoCrFeNi2.1 eutectic high-entropy alloy in its uniform, fine lamellar state, whose strength and plasticity remain below industrial application requirements, what single intervention could improve performance for fasteners exposed to extreme temperature fluctuations, long-term mechanical loading, room-temperature creep, and corrosive conditions? State the proposed intervention, mechanism, predicted outcome relative to the starting alloy, applicable operating and test boundaries, supporting prior evidence, and a controlled experiment with explicit falsification criteria.",
  "papers": [
   {
    "id": 1,
    "title": "Database on the mechanical properties of high entropy alloys and complex concentrated alloys.",
    "abstract": "This data article presents the compilation of mechanical properties for 370 high entropy alloys (HEAs) and complex concentrated alloys (CCAs) reported in the period from 2004 to 2016. The data sheet includes alloy composition, type of microstructures, density, hardness, type of tests to measure the room temperature mechanical properties, yield strength, elongation, ultimate strength and Young׳s modulus. For 27 refractory HEAs (RHEAs), the yield stress and elongation are given as a function of the testing temperature. The data are stored in a database provided in Supplementary materials, and for practical use they are tabulated in the present paper. The database was used in recent publications by Miracle and Senkov [1], Gorsse et al. [2] and Senkov et al. [3]."
   }
  ]
 },
 "output_parsed": {
  "PMC6290247": {
   "grade": 1,
   "why": "Broad HEA data, but lacks focus on AlCoCrFeNi2.1 or specific interventions."
  }
 }
}
```

**Selected papers** (30):

| Grade | Channel | Date | Title | Why |
|---:|---|---|---|---|
| 3 | both | 2023-08-22 | Thermal Stability and Hot Corrosion Performance of the AlCoCrFeNi2.1 High-Entropy Alloy Coating by L | Directly studies AlCoCrFeNi2.1 EHEA and its thermal stability and corrosion. |
| 3 | search | 2023-02-04 | Molten Salt Corrosion Behavior of Dual-Phase High Entropy Alloy for Concentrating Solar Power System | Directly evaluates corrosion behavior of AlCoCrFeNi2.1. |
| 3 | both | 2020-02-14 | Small-scale mechanical behavior of a eutectic high entropy alloy. | Directly studies AlCoCrFeNi2.1 with focus on mechanical properties. |
| 3 | search | 2023-11-30 | Phase-Specific Damage Tolerance of a Eutectic High Entropy Alloy. | Directly studies damage tolerance in AlCoCrFeNi2.1. |
| 3 | both | 2018-10-08 | The Exceptional Strong Face-centered Cubic Phase and Semi-coherent Phase Boundary in a Eutectic Dual | Directly studies AlCoCrFeNi EHEA and strengthening mechanisms. |
| 3 | both | 2014-08-27 | A promising new class of high-temperature alloys: eutectic high-entropy alloys. | Directly on point: AlCoCrFeNi2.1 alloy, mechanical properties. |
| 3 | both | 2024-09-12 | Effect of Alloying on Microstructure and Mechanical Properties of AlCoCrFeNi2.1 Eutectic High-Entrop | Directly studies AlCoCrFeNi2.1 EHEA and effects of alloying on strength and plasticity. |
| 3 | both | 2018-02-19 | Simultaneous Strength-Ductility Enhancement of a Nano-Lamellar AlCoCrFeNi2.1 Eutectic High Entropy A | Directly addresses strength and plasticity in AlCoCrFeNi2.1 EHEA. |
| 3 | both | 2019-08-08 | Nanostructuring with Structural-Compositional Dual Heterogeneities Enhances Strength-Ductility Syner | Directly addresses AlCoCrFeNi2.1 EHEA with strength-ductility improvement. |
| 3 | both | 2022-07-11 | Corrosion Behavior of the AlCoCrFeNi2.1 Eutectic High-Entropy Alloy in Chloride-Containing Sulfuric  | Directly on point: AlCoCrFeNi2.1 alloy, corrosion behavior. |
| 3 | search | 2024-10-04 | From Small Data Modeling to Large Language Model Screening: A Dual-Strategy Framework for Materials  | Directly addresses AlCoCrFeNi2.1 EHEA with improved strength and plasticity. |
| 3 | search | 2022-08-10 | Phase-selective recrystallization makes eutectic high-entropy alloys ultra-ductile. | Proposes phase-selective recrystallization to improve ductility in EHEAs. |
| 3 | old_corpus | 2021-07-01 | Microstructure and composition dependence of mechanical characteristics of nanoimprinted AlCoCrFeNi  | Directly on point: AlCoCrFeNi alloy, mechanical improvement. |
| 3 | both | 2019-01-30 | Enhanced strength-ductility synergy in ultrafine-grained eutectic high-entropy alloys by inheriting  | Directly on point; same material system and addresses strength-ductility improvement. |
| 2 | old_corpus | 2018-02-23 | Microstructural Evolution of AlCoCrFeNiSi High-Entropy Alloy Powder during Mechanical Alloying and I | Discusses AlCoCrFeNiSi HEA, relevant to coatings and corrosion. |
| 2 | old_corpus | 2021-01-29 | Refractory CrMoNbWV High-Entropy Alloy Manufactured by Mechanical Alloying and Spark Plasma Sinterin | Relevant; discusses mechanical and corrosion properties of a refractory HEA. |
| 2 | old_corpus | 2017-10-04 | The High Temperature Tensile and Creep Behaviors of High Entropy Superalloy. | Discusses creep and high-temperature behavior in HEAs, relevant but not AlCoCrFeNi2.1. |
| 2 | both | 2019-04-23 | Influence of ordered L12 precipitation on strain-rate dependent mechanical behavior in a eutectic hi | Discusses precipitation strengthening in a related HEA. |
| 2 | old_corpus | 2017-01-12 | Interstitial atoms enable joint twinning and transformation induced plasticity in strong and ductile | Discusses strengthening mechanisms relevant to HEAs. |
| 2 | old_corpus | 2023-01-10 | Effect of serrated grain boundary on tensile and creep properties of a precipitation strengthened hi | Relevant mechanism: serrated grain boundaries for creep resistance. |
| 2 | old_corpus | 2024-10-29 | Phase, Microstructure and Corrosion Behaviour of Al0.3FeCoNiCrx High-Entropy Alloys via Cr Addition. | Relevant; discusses corrosion resistance in a related high-entropy alloy system. |
| 2 | old_corpus | 2023-02-27 | Mechanisms of chemical-reaction-induced tensile deformation of an Fe/Ni/Cr alloy revealed by reactiv | Discusses SCC mechanisms in Fe/Ni/Cr alloy, relevant to corrosion. |
| 2 | old_corpus | 2024-08-27 | Process Parameters Optimization and Numerical Simulation of AlCoCrFeNi High-Entropy Alloy Coating vi | Relevant; focuses on AlCoCrFeNi HEA coatings, related to the material system. |
| 2 | old_corpus | 2018-07-02 | Influence of Titanium on Microstructure, Phase Formation and Wear Behaviour of AlCoCrFeNiTix High-En | Relevant; discusses microstructural changes and wear behavior in a related HEA. |
| 2 | both | 2020-04-10 | Dynamic Shear Deformation of a Precipitation Hardened Al0.7CoCrFeNi Eutectic High-Entropy Alloy Usin | Related material system but different composition and focus. |
| 2 | old_corpus | 2021-01-29 | Amorphization in extreme deformation of the CrMnFeCoNi high-entropy alloy. | Relevant mechanism: deformation-induced amorphization. |
| 2 | search | 2024-10-23 | Study on the Microstructure, Mechanical Properties, and Corrosion Behavior of 900 °C-Annealed CoCrFe | Discusses Si addition effects on CoCrFeMnNi HEAs, relevant to corrosion. |
| 2 | old_corpus | 2024-05-21 | Effect of Al Content on Microstructure and Properties of Al&lt;sub&gt;x&lt;/sub&gt;Cr&lt;sub&gt;0.2& | Discusses high-temperature creep in refractory HEAs, relevant to the question. |
| 2 | old_corpus | 2018-11-08 | Enhanced Wear Behaviour of Spark Plasma Sintered AlCoCrFeNiTi High-Entropy Alloy Composites. | Discusses AlCoCrFeNiTi HEA, relevant to wear resistance. |
| 2 | old_corpus | 2018-06-26 | Dynamically reinforced heterogeneous grain structure prolongs ductility in a medium-entropy alloy wi | Discusses heterogeneous grain structures for strength and ductility. |

## 4. Passage grading (trapi:gpt-4o_2024-11-20), 20 passages per call in a seeded random order

Prompt:

```text
You select evidence passages for a materials-science research question. For each passage (with its paper's title and section), grade:
3 = reports a result, mechanism, condition or method that bears directly on the question;
2 = useful background for the question (for example properties of the same system, or a related approach and its outcome);
1 = generic or tangential;
0 = irrelevant (for example sample preparation unrelated to the question).
If a search purpose is given, also count usefulness for that purpose. Return JSON {"grades": [{"id": int, "grade": 0-3}]} with one entry per passage.
```

Batch 1, input:

```json
{
 "question": "For an AlCoCrFeNi2.1 eutectic high-entropy alloy in its uniform, fine lamellar state, whose strength and plasticity remain below industrial application requirements, what single intervention could improve performance for fasteners exposed to extreme temperature fluctuations, long-term mechanical loading, room-temperature creep, and corrosive conditions? State the proposed intervention, mechanism, predicted outcome relative to the starting alloy, applicable operating and test boundaries, supporting prior evidence, and a controlled experiment with explicit falsification criteria.",
 "passages": [
  {
   "id": 1,
   "paper_title": "Influence of Titanium on Microstructure, Phase Formation and Wear Behaviour of AlCoCrFeNiTix High-Entropy Alloy.",
   "section": "4. Summary and Conclusions",
   "text": "The influence of the alloying element titanium was studied in detail in the alloy system AlCoCrFeNiTix. For the alloy without titanium (x = 0.0), a single chemically ordered bcc phase with B2 structure is formed. In contrast, a multiphase microstructure was revealed for all titanium-containing alloys. With an increase of titanium content, an increase of heterogeneity of the microstructure is observed. Furthermore, the hardness can be distinctly increased, whereas the maximum hardness is achieved for the equimolar composition. Phase analyses prove the formation of two major bcc phases for all titanium-containing samples. One chemically ordered bcc phase with B2 structure and one chemically disordered bcc phase with A2 structure is formed. With an increase in titanium content, additional phases occur. For x ≥ 0.5 a minor fraction of an fcc phase was detected. A further increase in titanium content results in additional, more complex phases. This could also be proved by analysing the solidification behaviour. Analyses of the lattice parameters revealed a shift to bigger values with increasing titanium content, especially for the bcc (B2) and the fcc (A1) phase. The alloy system AlCoCr"
  },
  {
   "id": 2,
   "paper_title": "Effect of Al Content on Microstructure and Properties of Al&lt;sub&gt;x&lt;/sub&gt;Cr&lt;sub&gt;0.2&lt;/sub&gt;NbTiV Refractory High-Entropy Alloys.",
   "section": "1. Introduction",
   "text": "Structural components used in high-temperature environments often fail due to high-temperature creep. Traditional creep tests, such as uniaxial tensile or compression tests, often require large sample sizes and long testing periods, which has limited the research on the creep properties of RHEAs. To overcome these limitations, the use of nanoindentation techniques for studying creep behavior offers an effective alternative. Nanoindentation is applying a small indentation load on the surface of the material to measure its mechanical properties, allowing for the assessment of creep properties at a very small scale. The advantages of this technique include the small size of samples required and short experimental periods. Existing research indicates that adding Al to CoCrFeNiCu alloys results in a phase transformation from FCC to BCC structures. Although this addition reduces the ductility of the alloy, it effectively enhances its creep resistance at the nanoscale []. As the Al content increases, the creep resistance of AlxCoCrFeNi (x = 0.3, 0.5, 0.7, 1) alloys shows a trend of initially increasing and then decreasing, but the creep mechanism remains consistent and is characterized by"
  },
  {
   "id": 3,
   "paper_title": "Simultaneous Strength-Ductility Enhancement of a Nano-Lamellar AlCoCrFeNi2.1 Eutectic High Entropy Alloy by Cryo-Rolling and Annealing.",
   "section": "Materials and Methods",
   "text": "AlCoCrFeNi2.1 EHEA was prepared by arc melting in a Ti-gettered high-purity argon atmosphere using high purity elements (≥99.9%). The melt was suction-cast into a copper mold (15 mm (width) × 90 mm (length) × 3 mm (thickness)). Multi-pass cryo-rolling of the as-cast EHEA was carried out using a laboratory scale rolling mill (SPX Precision Instruments, Fenn Division, USA) up to ~90% reduction in thickness. Before and immediately after each pass, the samples were immersed in a liquid N2 bath for 45 minutes. The 90% cryo-rolled samples were annealed for 1 hour (h) at 800 °C and water quenched. In order to highlight the effect of cryo-rolling and annealing, comparisons were made with a 90% cold-rolled (at room temperature) specimen annealed at 800 °C for 1 h,. Nano-indentation tests were carried out using a TI950 Tribo-indenter (Hysitron, USA) equipped with a sharp cube-corner probe (apex radius of curvature of ~40 nm). During each indentation, the load was increased linearly from 1 μN to 500 μN over a period of 0.25 seconds (sec.), kept constant for 0.25 sec., and unloaded to 1 μN over a period of 0.25 sec. before moving to the next indent position. All nano-indentation data were anal"
  },
  {
   "id": 4,
   "paper_title": "Effect of Alloying on Microstructure and Mechanical Properties of AlCoCrFeNi2.1 Eutectic High-Entropy Alloy.",
   "section": "3.2. Mechanical Properties",
   "text": "On the one hand, this is because when B element is added, the microstructures of alloy change from typical lamellar eutectic morphologies to a petal-like structure (see Figure 1b), in which the petal-like dendrites with BCC structures are coarser, which is conducive to the improvement of the hardness of alloy. Meanwhile, with the increase in the B content, the proportion of BCC phase also increases, and the increase in the harder BCC phase leads to an increase in hardness. On the other hand, unlike the alloys with the addition of V and Mo, the grain refinement is obvious in the alloys with the increase in the content of B. The strengthening effect brought about by grain refinement is also the main reason for the increase in the hardness of these alloys. In conclusion, the addition of high-melting-point metal and nonmetallic elements has a direct impact on the hardness of the AlCoCrFeNi2.1 alloy, with nonmetallic elements having the greatest effect."
  },
  {
   "id": 5,
   "paper_title": "From Small Data Modeling to Large Language Model Screening: A Dual-Strategy Framework for Materials Intelligent Design.",
   "section": "The Overall Performance of AMSEP",
   "text": "The newly proposed EHEA Al14(CoCrFe)19Ni28 demonstrates significantly greater plasticity without strength loss compared to the typical as‐cast EHEA AlCoCrFeNi2.1.[ ] Alloys with high plasticity exhibit remarkable ductility and toughness, allowing for substantial deformation without fracturing, which enhances their suitability for critical applications across various applications, including automotive, aerospace, marine, and petroleum industries. Their superior formability and resistance to cracking not only extend the lifespan of components but also reduce manufacturing costs, positioning them as valuable materials in the advancement of industrial technologies."
  },
  {
   "id": 6,
   "paper_title": "Nanostructuring with Structural-Compositional Dual Heterogeneities Enhances Strength-Ductility Synergy in Eutectic High Entropy Alloy.",
   "section": "Discussion",
   "text": "As reviewed recently by Ovid’ko et al., various strategies for improving the ductility have been proposed including grain boundaries deformation phenomena, introduction of nanotwins, formation of second phase particles and more recently through the formation of heterogeneous micro/nano-structure. While the extreme strength in the hybrid-processed EHEA is contributed by various strengthening mechanisms including nanostructuring and presence of hard B2 phase and nano-precipitates. The outstanding strength-ductility combination of the hybrid-rolled EHEA originates from the extreme heterogeneities. It is perceived that in heterogeneous materials, mechanical incompatibility between the different domains results in the development of strain gradients near the interfaces or domain boundaries, which must be accommodated by geometrically necessary dislocations (GNDs),. The pile up of GNDs at the interfaces/domain boundaries leads to the development of long-range back stress which increases with the increasing strain, eventually leading to back-stress strengthening. The generation of such long-range back stress in the heterogeneous materials has been already experimentally verified,,. The st"
  },
  {
   "id": 7,
   "paper_title": "Dynamic Shear Deformation of a Precipitation Hardened Al0.7CoCrFeNi Eutectic High-Entropy Alloy Using Hat-Shaped Specimen Geometry.",
   "section": "2. Experimental Section",
   "text": "The Al0.7CoCrFeNi alloy (15 at.% Al and 21.25 at.% each of Co, Cr, Fe, Ni) was arc-melted. The ingot was remelted five times for homogenization of the alloy, inverting it after each melt. The as-cast alloy was homogenized at 1150 °C for 1 h to annihilate the dislocations and reduce micro-segregations from casting process to assist in cold deformation of the alloy. The alloy was then rolled at room temperature to 30% reduction in thickness. Subsequent annealing at 1100 for 5 min was done to homogenize and recrystallize the alloy at high temperature. The cold-rolled and homogenized condition is referred to as HTA (high temperature annealed) hereafter. Another low-temperature annealing treatment was done at 580 °C for 24 h on the HTA condition to precipitate a fine-scale distribution of L12 phase inside fcc lamellae, this is referred to as the HTA-580 condition. In all the heating steps, the samples were placed in the furnace after the set temperature was reached and cooled by water quenching after a specified treatment time. The microstructural examination was carried out using scanning electron microscopy (SEM) including electron backscatter diffraction (EBSD) and transmission elect"
  },
  {
   "id": 8,
   "paper_title": "Interstitial atoms enable joint twinning and transformation induced plasticity in strong and ductile high-entropy alloys.",
   "section": "Body",
   "text": "Exploring strong and yet ductile materials is paramount for reducing the weight and hence the energy consumption in all fields where mobile structures are used,. However, strength and ductility of current engineering materials are generally conflicting, limiting traditional alloy design strategies. Over the past years, high-entropy alloys (HEAs) have drawn great attention as it opens an entirely new realm of compositional opportunities for designing novel materials with exceptional properties,,,,,,,. HEAs were originally proposed to contain multiple principal elements in near-equimolar ratios to stabilize single-phase solid solutions through maximizing configurational entropy,. Recently, motivated by the fact that maximized configurational entropy is not the sole factor determining phase stability of HEAs,,,,, a novel metastable transformation-induced plasticity dual-phase (TRIP-DP) HEA with exceptional strength and ductility has been developed,. Based on this approach, we propose a new class of HEAs which is interstitially alloyed and unifies all known metallic strengthening mechanisms in one material. We use carbon as interstitial element in line with two main trends which can be"
  },
  {
   "id": 9,
   "paper_title": "Influence of Titanium on Microstructure, Phase Formation and Wear Behaviour of AlCoCrFeNiTix High-Entropy Alloy.",
   "section": "1. Introduction",
   "text": "High-entropy alloys (HEAs) are an emerging class of new materials. Their alloying concept differs from conventional alloys, which are composed of one main element, and an improvement of properties is achieved by adding minor amounts of other elements. In contrast, HEAs are multicomponent alloys comprising at least five elements with approximately equimolar composition []. Despite their complex composition, only simple solid solutions with fcc or bcc structure were formed for several alloy systems. The formation of brittle and intermetallic phases can be successfully suppressed. One of the first alloys with a single fcc phase is the equimolar alloy CoCrFeMnNi investigated by Cantor et al. []. Due to their unique structure, HEAs exhibit an interesting combination of properties e.g., high hardness and strength in combination with adequate ductility. Furthermore, a high wear and corrosion resistance can be obtained [,,,]. Two main groups can be distinguished: HEAs forming (i) cubic or (ii) hexagonal phases []. Detailed structural investigations of HEAs revealed that only a few alloys form a single phase microstructure comprising fcc or bcc phases. Most alloys are composed of more than "
  },
  {
   "id": 10,
   "paper_title": "Effect of serrated grain boundary on tensile and creep properties of a precipitation strengthened high entropy alloy.",
   "section": "Conclusions",
   "text": "The effect of serrated grain boundary on tensile and creep properties has been investigated for a high-entropy alloy (Al8Co35Cr18Ni34Ti3Nb2Zr0.005B0.01 (at.%)) fabricated by selective laser melting, the followings are findings of this work: Serrated grain boundary could render a significant increase in tensile fracture strain and creep rupture life by a factor of 3.5 and 400, respectively. The inferior ductility of straight grain boundary at 650°C was attributed to the grain boundary embrittlement caused by strain concentration at triple junctions and fast intergranular crack propagation. The slow cooling process of the post heat treatment could coarsen the γ′ particles and encourage interactions with mobile grain boundaries to from serrated grain boundaries. Analysis has indicated that serrated grain boundary could distribute strains more evenly than that of straight morphology. Serrated grain boundaries could reduce local strain concentration and provide resistance against intergranular cracking."
  },
  {
   "id": 11,
   "paper_title": "Small-scale mechanical behavior of a eutectic high entropy alloy.",
   "section": "Introduction",
   "text": "However, dynamic strengthening mechanisms and phase interactions during external loading is not well understood for these eutectic alloys. The large fraction of phase boundary significantly impacts plastic flow in these systems. Considering the effect of thermo-mechanical processing on tailoring the microstructure and mechanical properties of AlCoCrFeNi2.1 EHEA, understanding of phase-specific mechanical response is critical for fundamental insights as well as wider application of these alloys. Here, phase-specific mechanical behavior of AlCoCrFeNi2.1 eutectic high entropy alloy was evaluated for better understanding of phase boundary interactions during loading. Measurement of hardness, modulus, strain rate sensitivity, yielding and plastic deformation of micro-pillars, and friction analysis was done at the microstructural length-scale and compared with bulk mechanical response. This will pave the way for designing stronger and tougher complex phase HEAs."
  },
  {
   "id": 12,
   "paper_title": "Enhanced strength-ductility synergy in ultrafine-grained eutectic high-entropy alloys by inheriting microstructural lamellae.",
   "section": "Introduction",
   "text": "Moreover, the safety and advancement of modern technologies not only strongly relies on current mechanical properties of these eutectic alloys, but also calls for better ones. To date, many conventional routes to optimize eutectic alloys, such as processing to create line defects, usually result in reduced ductility. Previous studies showed that engineering an ultrafine-grained duplex microstructure by severe cold-rolling and annealing could dramatically strengthen eutectic alloys although degrading ductility. Recently, Wu et al. developed a heterogeneous structure of bimodal grains in Ti, which possesses < 30 vol.% soft, coarse-grained lamellae embedded in a hard, ultrafine-grained lamella matrix,. The resulting materials exhibited great ductility, as a high density of lamella interfaces could induce the building of large strain gradients across them during deformation. Meanwhile, the full deformation constraint imposed by the hard lamella matrix enables the soft lamellae to be almost as strong as the hard matrix, thus making materials with high strength,. So a remarkable strength–ductility enhancement is expected if we could inherit the heterogeneous lamellar nature via an approp"
  },
  {
   "id": 13,
   "paper_title": "The Exceptional Strong Face-centered Cubic Phase and Semi-coherent Phase Boundary in a Eutectic Dual-phase High Entropy Alloy AlCoCrFeNi.",
   "section": "Phase strengthening vs. boundary strengthening in dual-phase",
   "text": "Interestingly, the above results demonstrate that, in strong contrast to our traditional understanding, the FCC phase was capable of not only carrying large plastic deformation but also served as the source of strengthening. The high lattice friction in matrix and the strong semi-coherent phase boundaries which were decorated by disorderedly distributed multiple elements enabled high dislocation density in FCC phases. As a result, significant hardening of material would be expected. To confirm our hypothesis, we compared the mechanical properties of the as-casted and pre-strained AlCoCrFeNi alloys. The pre-straining was conducted to raise the dislocation density in the FCC phase. A comparison of the strain-stress curves of the as-casted and cold rolled dual-phase AlCoCrFeNi2.1 HEAs was shown in Fig. 4a. The strain-stress curve of the as-casted sample (black curve) exhibited a combination of high fracture strength (~0.94 GPa) and good ductility (~25%). Meanwhile, the mechanical property of the eutectic dual-phase HEA in cast can be further improved by reasonable pre-straining (shown by the red line in Fig. 4a), which remarkably increased the yield strength by a factor of ~5."
  },
  {
   "id": 14,
   "paper_title": "Interstitial atoms enable joint twinning and transformation induced plasticity in strong and ductile high-entropy alloys.",
   "section": "Deformation mechanisms",
   "text": "The improved mechanical properties (Fig. 3) and the associated multiple deformation mechanisms (Fig. 4) confirm the success of the new design approach, and its potential economic viability since interstitial alloying elements are much cheaper compared to substitutional alloying elements. The new interstitial TWIP-TRIP-HEAs unify all known metallurgical strengthening effects in one single bulk material: i) massive substitutional solid solution strengthening due to multiple principle elements (i.e., Fe, Mn, Co and Cr); ii) interstitial solid solution strengthening by carbon; iii) micro-composite effect from dual-phase structure; iv) nano-particle strengthening from nano-carbides (Figs 2b and 4c); v) nano-twinning induced plasticity effect (TWIP) (Fig. 4b); vi) displacive transformation induced plasticity effect (TRIP) (Fig. 4a); vii) formation of stacking faults (Fig. 4b); viii) grain size reduction (increased grain boundary density); and dislocation hardening (Fig. 4b)."
  },
  {
   "id": 15,
   "paper_title": "Process Parameters Optimization and Numerical Simulation of AlCoCrFeNi High-Entropy Alloy Coating via Laser Cladding.",
   "section": "1. Introduction",
   "text": "Among many high-entropy alloy systems, AlCoCrFeNi high-entropy alloy has excellent ductility and high-temperature strength and can be used as a protective coating in a special service environment with broad application prospects. Currently, research on AlCoCrFeNi high-entropy alloys is primarily focused on two areas. On the one hand, is the aim is to study the ratio of the five elements. For example, Vo et al. [] compared and analyzed the performance differences and causes of the two high-entropy alloys Al0.8CrFeNi2.2 and AlCoCrFeNi2.1; Izadi et al. [] studied the changes in the tissue structure of AlxCoCrFeNi high-entropy alloys and their influence on corrosion properties under different Al element content; Sim et al. [] discussed the influence of Ni element content on the characteristics of AlCoCrFeNix high-entropy alloys and compared it with AlCoCrFe medium entropy alloys. On the other hand, the research focuses on adding Cu, Mn, Ti [], Co [], carbon nanotubes (CNT) [], TiB2 [], nano TiC [], Bi2O3 [], WC [], and other trace components to regulate the microstructure, mechanical characteristics, tribological properties, and corrosion resistance of AlCoCrFeNi high-entropy alloys. H"
  },
  {
   "id": 16,
   "paper_title": "Influence of ordered L12 precipitation on strain-rate dependent mechanical behavior in a eutectic high entropy alloy.",
   "section": "Effect of microstructure on mechanical properties",
   "text": "The advantage of such a two-phase eutectic alloy is that it consists of a more easily deformable ductile (fcc or fcc + L12) phase, and a hard, difficult to deform, B2 + bcc phase. The hard B2 + bcc phase defines the inter-lamellar spacing of the softer fcc phase. To evaluate the mechanical performance of the Al0.7CoCrFeNi alloy, the CR-H and CR-H-580 conditions were tested under two different strain rates (10−3 s−1 and 2 × 103 s−1) and the corresponding stress-strain plots are shown in Fig. 6. Figure 6(a) shows the engineering (thick line) and true (thin line) stress-strain plots from quasi-static testing. The CR-H condition with fcc + B2 (with fine scale bcc precipitates) shows a yield strength (YS) of ~770 MPa, UTS ~1090 MPa with an elongation to failure (EF) of ~17% under the quasi-static deformation (10−3). The CR-H-580 condition with the fcc + L12 & B2 + bcc microstructure exhibited a YS ~1080 MPa, UTS ~1370 MPa and EF of ~15%. A precipitation strengthening of ~310 MPa is observed after the additional heat treatment with just ~2% reduction in the elongation."
  },
  {
   "id": 17,
   "paper_title": "Effect of serrated grain boundary on tensile and creep properties of a precipitation strengthened high entropy alloy.",
   "section": "Abstract",
   "text": "ABSTRACTIn this study, tensile and creep deformation of a high-entropy alloy processed by selective laser melting (SLM) has been investigated; hot ductility drop was identified at first, and the loss of ductility at elevated temperature was associated with intergranular fracture. By modifying the grain boundary morphology from straight to serration, the hot ductility drop issue has been resolved successfully. The serrated grain boundary could be achieved by reducing the cooling rate of solution heat treatment, which allowed the coarsening of L12 structured γ′ precipitates to interfere with mobile grain boundaries, resulting in undulation of the grain boundary morphology. Tensile and creep tests at 650°C were conducted, and serrated grain boundary could render a significant increase in tensile fracture strain and creep rupture life by a factor of 3.5 and 400, respectively. Detailed microstructure analysis has indicated that serrated grain boundary could distribute strains more evenly than that of straight morphology. The underlying mechanism of deformation with grain boundary serration was further demonstrated by molecular dynamic simulation, which has indicated that serrated grain "
  },
  {
   "id": 18,
   "paper_title": "Small-scale mechanical behavior of a eutectic high entropy alloy.",
   "section": "Micro-pillar compression",
   "text": "In contrast, the micro-pillars in L12 phase after deformation showed a high density of slip steps due to the activation of more slip systems and homogenous plastic flow as shown in Fig. 6(e). The deformation mechanism in conventional FCC alloys is mainly influenced by dislocation slip and twinning. The phase boundary in a dual phase alloy such as EHEA plays an important role in crack nucleation and failure mode. During compression of mixed pillars (Fig. 6(f)), initial slip steps formed near the top of L12 while B2 was still elastically deforming. Plastic deformation of B2 initiated at higher loads while there was continued work hardening of L12. Enhanced plasticity in this EHEA during bulk tensile testing has been explained by complex back-stresses from L12. A similar phenomenon was observed for the mixed micro-pillars. Once B2 plastic deformation initiated, it proceeded with the rapid formation of slip bands and majority of the plastic flow was concentrated on the B2 side since L12 was sufficiently work hardened. At higher loads, both L12 and B2 deformed simultaneously with the initiation and propagation of slip steps but the phase boundary was preserved without any sign of separa"
  },
  {
   "id": 19,
   "paper_title": "Microstructure and composition dependence of mechanical characteristics of nanoimprinted AlCoCrFeNi high-entropy alloys.",
   "section": "Influence of grain size",
   "text": "In this section, five polycrystalline samples with various grain sizes of 80.03, 71.61, 63.57, 56.88, and 51.43 Å are prepared to probe the effect of grain sizes on the mechanistic characteristics of the Al0.5 HEA during nanoimprinting. Figure 10 shows the force–time diagrams for polycrystalline Al0.5 HEA specimens during the nanoimprinting process with various grain sizes. Generally, the loading force increases with the increase of the imprinting depth. The results reveal that the highest loading forces are 879.45, 858.55, 830.20, 826.86, and 730.07 nN corresponding to grain sizes of 80.03, 71.61, 63.57, 56.88, and 51.43 Å, respectively. It shows a positive relationship between the grain size and the largest loading force. This phenomenon reveals that the GB clearly relates to the softening of the polycrystalline structure. The smaller grain size samples have more GBs, leading to the loading force is reduced with the decrease in the grain size. The reduction of grain size improves the strength of the material indicating a Hall–Petch relation. However, many previous studies demonstrate that grain refinement below a critical grain size induces a decrease in the material strength, wh"
  },
  {
   "id": 20,
   "paper_title": "Study on the Microstructure, Mechanical Properties, and Corrosion Behavior of 900 °C-Annealed CoCrFeMnNiSix (X = 0, 0.3, 0.6, 0.9) High-Entropy Alloys",
   "section": "3.2. CoCrFeMnNiSix HEAs Mechanical Properties After 900 °C H",
   "text": "The dispersed hard FCO phase and Fe rich HCP phase jointly strengthens the HEA, resulting in a continued increase in hardness to 974.8 ± 30.2 HV, which is 667% higher than that of the original HEA. Figure 8 shows the stress–strain curves of the CoCrFeMnNiSix HEAs after heat treatment. It can be observed that as the silicon content increases, the slope of the curve also increases. This indicates that the elastic strain modulus of the HEA increases continuously, leading to a continuous improvement in the compressive strength of the HEA for the same amount of deformation. However, the fracture strain of the HEA decreases to varying degrees with the addition of different silicon contents, indicating a reduction in the HEA ductility. According to the compression data in Table 3, the equiatomic CoCrFeMnNi HEA without silicon shows grain growth after heat treatment, the compressive strength is 1367 MPa. When x = 0.3, the addition of Si leads to significant grain refinement, along with the evident effects of solid solution strengthening and grain refinement, resulting in a substantial increase in HEA strength. When the silicon content reaches 0.6, the compressive strength of the HEA contin"
  }
 ]
}
```

Batch 1, output (parsed):

```json
{
 "grades": [
  {
   "id": 1,
   "grade": 2
  },
  {
   "id": 2,
   "grade": 2
  },
  {
   "id": 3,
   "grade": 3
  },
  {
   "id": 4,
   "grade": 3
  },
  {
   "id": 5,
   "grade": 2
  },
  {
   "id": 6,
   "grade": 3
  },
  {
   "id": 7,
   "grade": 2
  },
  {
   "id": 8,
   "grade": 2
  },
  {
   "id": 9,
   "grade": 1
  },
  {
   "id": 10,
   "grade": 3
  },
  {
   "id": 11,
   "grade": 2
  },
  {
   "id": 12,
   "grade": 3
  },
  {
   "id": 13,
   "grade": 3
  },
  {
   "id": 14,
   "grade": 2
  },
  {
   "id": 15,
   "grade": 1
  },
  {
   "id": 16,
   "grade": 3
  },
  {
   "id": 17,
   "grade": 3
  },
  {
   "id": 18,
   "grade": 3
  },
  {
   "id": 19,
   "grade": 1
  },
  {
   "id": 20,
   "grade": 2
  }
 ]
}
```

Grades over all 180 passages: {0: 3, 1: 49, 2: 68, 3: 60}. The pack: 46 passages, graded 3 and then 2 (58786 characters).

Target-aware check after the run (DeepSeek lever labels of the pack, 0-3): {0: 41, 1: 5}. No passage carries the paper's actual lever.

## 5. Writer (trapi:o3-mini_2025-01-31)

Prompt (WRITER_B with the output schema):

```text
You are a materials-science hypothesis agent in a chronological benchmark. Use the supplied analysis notes (your own earlier reasoning about this question) and any supplied temporally eligible evidence. Do not claim knowledge of the held-out paper. If the notes name a chosen family and lever, build the hypothesis on them. Predict the direction and approximate size of effects only as far as the notes and evidence support; if support is insufficient, state the uncertainty instead of inventing support or precise values.

Return one falsifiable hypothesis as JSON:
{
  "hypothesis": "",
  "material_initial_state": "",
  "intervention": "",
  "conditions": "",
  "structural_mediator": "",
  "mechanism": "",
  "predicted_outcome": "",
  "baseline": "",
  "boundary": "",
  "uncertainty": "",
  "supporting_evidence_ids": [],
  "conflicting_evidence_ids": [],
  "falsification_experiment": {"design": "", "measurements": [], "falsification_rule": ""}
}
Evidence IDs must be copied from the supplied records.
```

Input (72164 characters with the prompt):

```json
{
 "query": "For an AlCoCrFeNi2.1 eutectic high-entropy alloy in its uniform, fine lamellar state, whose strength and plasticity remain below industrial application requirements, what single intervention could improve performance for fasteners exposed to extreme temperature fluctuations, long-term mechanical loading, room-temperature creep, and corrosive conditions? State the proposed intervention, mechanism, predicted outcome relative to the starting alloy, applicable operating and test boundaries, supporting prior evidence, and a controlled experiment with explicit falsification criteria.",
 "knowledge_cutoff": "2024-12-01",
 "analysis_notes": {},
 "eligible_evidence": [
  {
   "record_id": "PMC6353877::web::018::discussion",
   "paper_title": "Enhanced strength-ductility synergy in ultrafine-grained eutectic high-entropy alloys by inheriting microstructural lamellae.",
   "section": "Discussion",
   "publication_date": "2019-01-30",
   "evidence": "In this work, we successfully achieve a superior strength–ductility combination in AlCoCrFeNi2.1 EHEAs by introducing two concurrent effects, the two-hierarchical constraint effect and the self-generated microcrack-arresting mechanisms. The underlying origin lying behind the observed mechanical response is the inherited lamellar geometry from the as-cast EHEA. It is known that grain refinement to the nano/ultrafine-grained regime can render material stronger, but this process is usually accompanied by a dramatic loss of ductility. However, with a composite lamellar architecture, the ultrafine-grained duplex microstructure in this study achieves an improved strength–ductility synergy. Phase decomposition is applied to optimize properties instead of just being a phase-instability phenomenon frequently observed in single-phase HEAs, which may encourage further research in this area. In addition, the AlCoCrFeNi2.1 EHEA could be simply processed to achieve properties that are an improvement over traditional TRIP (transformation-induced plasticity) and TWIP (twinning-induced plasticity) steels (Fig. 5). We believe that the simplicity in the present processing procedure is extremely attractive for industrial applications. Meanwhile, we anticipate that the investigated EHEA based on the present strengthening strategy can be further modified to satisfy more demanding application requirements, such as high-temperature and/or corrosion ..."
  },
  {
   "record_id": "PMC10488378::web::000::abstract",
   "paper_title": "Thermal Stability and Hot Corrosion Performance of the AlCoCrFeNi<sub>2.1</sub> High-Entropy Alloy Coating by Laser Cladding.",
   "section": "Abstract",
   "publication_date": "2023-08-22",
   "evidence": "AbstractBoth crack-free AlCoCrFeNi2.1 eutectic high-entropy alloy (EHEA) and Y and Hf co-doping AlCoCrFeNi2.1 EHEA (YHf-EHEA) coatings were prepared by laser cladding. The solidification microstructure, thermal stability, and hot corrosion performance of the coatings at 900 °C under 75% Na2SO4 + 25% NaCl molten salts were investigated. The experimental results showed that the structure of the as-deposited coatings consisted of FCC and BCC/B2 phases. After heat treatment, an Al-rich L12 phase was precipitated in the FCC phase of all coatings. The grain sizes of the EHEA and YHf-EHEA coatings after heat treatment at 900 °C for 10 h increased by 27.5% and 15.7%, respectively, compared to the as-deposited coatings. Meanwhile, after hot corrosion, the spallation areas of the YHf-EHEA and EHEA coatings accounted for 14.98% and 5.67% of the total surface area, respectively. In this study, the Y and Hf co-doping did not change the microstructure morphology and phase structure of the coatings but did improve the thermal stability and resistance of the hot corrosion oxide scale spallation, providing a certain amount of data and theoretical support for the application of EHEA coatings as high-temperature protective coatings.Keywords: high-entropy alloy, laser cladding, thermal stability, hot corrosion"
  },
  {
   "record_id": "PMC9955357::web::019::5_conclusions",
   "paper_title": "Molten Salt Corrosion Behavior of Dual-Phase High Entropy Alloy for Concentrating Solar Power Systems.",
   "section": "5. Conclusions",
   "publication_date": "2023-02-04",
   "evidence": "The corrosion behavior of dual-phase AlCoCrFeNi2.1 (EHEA) and duplex stainless steel 2205 (DS2205) was studied in NaCl-KCl-MgCl2 molten salt at 450 °C and 650 °C. AlCoCrFeNi2.1 EHEA showed superior molten salt corrosion resistance than DS2205, which was attributed to the following: (i)Higher Ni content in EHEA and sacrificial role of Al in reducing outward diffusion of Cr, Fe, and Ni in AlCoCrFeNi2.1 and the different reactivity of formation of chlorides, as well as enrichment of Co and Ni in the corrosion layer.(ii)Thermodynamically driven corrosion between alloying elements and molten salt constituents or impurities present within the melt. Metallic impurities such as Ni2+, Fe2+, and Co2+ enhance the corrosion resistance of AlCoCrFeNi2.1 via enrichment of impurity ions such as Ni, Co, and Fe (to lesser extent) in the corrosion layer as temperature increases.(iii)A lower volume fraction of the BCC phase, which makes it less prone to galvanic corrosion. The phase-specific work function for the as-cast AlCoCrFeNi2.1 and DS2205 suggested micro-galvanic corrosion, with nobler L12 and FCC phase in EHEA and DS 2205, respectively, compared to the B2 and BCC phases."
  },
  {
   "record_id": "PMC6687781::web::013::discussion",
   "paper_title": "Nanostructuring with Structural-Compositional Dual Heterogeneities Enhances Strength-Ductility Synergy in Eutectic High Entropy Alloy.",
   "section": "Discussion",
   "publication_date": "2019-08-08",
   "evidence": "As reviewed recently by Ovid’ko et al., various strategies for improving the ductility have been proposed including grain boundaries deformation phenomena, introduction of nanotwins, formation of second phase particles and more recently through the formation of heterogeneous micro/nano-structure. While the extreme strength in the hybrid-processed EHEA is contributed by various strengthening mechanisms including nanostructuring and presence of hard B2 phase and nano-precipitates. The outstanding strength-ductility combination of the hybrid-rolled EHEA originates from the extreme heterogeneities. It is perceived that in heterogeneous materials, mechanical incompatibility between the different domains results in the development of strain gradients near the interfaces or domain boundaries, which must be accommodated by geometrically necessary dislocations (GNDs),. The pile up of GNDs at the interfaces/domain boundaries leads to the development of long-range back stress which increases with the increasing strain, eventually leading to back-stress strengthening. The generation of such long-range back stress in the heterogeneous materials has been already experimentally verified,,. The strain hardening due to the back stress is perceived to prevent the early onset of necking, rendering high strength and appreciable ductility."
  },
  {
   "record_id": "PMC9955357::web::000::abstract",
   "paper_title": "Molten Salt Corrosion Behavior of Dual-Phase High Entropy Alloy for Concentrating Solar Power Systems.",
   "section": "Abstract",
   "publication_date": "2023-02-04",
   "evidence": "Dual-phase high entropy alloys have recently attracted widespread attention as advanced structural materials due to their unique microstructure, excellent mechanical properties, and corrosion resistance. However, their molten salt corrosion behavior has not been reported, which is critical in evaluating their application merit in the areas of concentrating solar power and nuclear energy. Here, the molten salt corrosion behavior of AlCoCrFeNi2.1 eutectic high-entropy alloy (EHEA) was evaluated in molten NaCl-KCl-MgCl2 salt at 450 °C and 650 °C in comparison to conventional duplex stainless steel 2205 (DS2205). The EHEA showed a significantly lower corrosion rate of ~1 mm/year at 450 °C compared to ~8 mm/year for DS2205. Similarly, EHEA showed a lower corrosion rate of ~9 mm/year at 650 °C compared to ~20 mm/year for DS2205. There was selective dissolution of the body-centered cubic phase in both the alloys, B2 in AlCoCrFeNi2.1 and α-Ferrite in DS2205. This was attributed to micro-galvanic coupling between the two phases in each alloy that was measured in terms of Volta potential difference using a scanning kelvin probe. Additionally, the work function increased with increasing temperature for AlCoCrFeNi2.1, indicating that the FCC-L12 phase acted as a barrier against further oxidation and protected the underlying BCC-B2 phase with enrichment of noble elements in the protective surface layer."
  },
  {
   "record_id": "PMC10488378::web::015::4_conclusions",
   "paper_title": "Thermal Stability and Hot Corrosion Performance of the AlCoCrFeNi<sub>2.1</sub> High-Entropy Alloy Coating by Laser Cladding.",
   "section": "4. Conclusions",
   "publication_date": "2023-08-22",
   "evidence": "In this work, AlCoCrFeNi2.1 EHEA and co-doping Y and Hf AlCoCrFeNi2.1 YHf-EHEA coatings were successfully prepared by laser cladding. The solidification microstructure, thermal stability, and hot corrosion of the coatings at 900 °C under 75% Na2SO4 + 25% NaCl molten salts were investigated. 1. The YHf co-doping did not alter the solidification microstructure and phase structure of the EHEA coating. The microstructure morphologies of the top and bottom portions of coatings were composed of cellular and columnar dendrites, respectively. And the phase structure consisted of FCC and BCC/B2. 2. After heat treatment at 900 °C for 10 h, the BCC/B2 structure was relatively stable in all coatings while the nanoscale Al-rich L12 phase was precipitated in the FCC. 3. The grain sizes of the HT-EHEA and HT-YHf coatings after heat treatment at 900 °C for 10 h increased by 27.5% and 15.7%, respectively, compared to the as-deposited coatings. Additionally, the volume fractions of the LAGBs decreased by 13.9% and 8.3% in the HT-EHEA and HT-YHf coatings, respectively. 4. Al2O3 was found to be formed when the surface oxide products of the coatings were hot corroded at 900 °C for 60 h under Na2SO4 + 25% NaCl molten salts. The YHf-EHEA coating showed better resistance to scale spallation compared to the EHEA coating."
  },
  {
   "record_id": "PMC10488378::web::011::3_2_thermal_stability_of_the_coatings",
   "paper_title": "Thermal Stability and Hot Corrosion Performance of the AlCoCrFeNi<sub>2.1</sub> High-Entropy Alloy Coating by Laser Cladding.",
   "section": "3.2. Thermal Stability of the Coatings",
   "publication_date": "2023-08-22",
   "evidence": "As shown in Figure 6, it can be observed that after heat treatment, both coatings still maintained an intact BCC structure. However, small rod-shaped precipitates with widths ranging from 110 to 340 nm were found in the FCC phase. Higher temperatures cause the precipitation of the Al-rich ordered phase L12 within the FCC phase of AlCoCrFeNi high-entropy alloys. Some reports have indicated that the transformation to the ordered phase occurs at temperatures of 778 ± 2 °C [,,]. Al has a more negative mixing enthalpy with other elements such as Ni and Co(Al-Ni, −22 KJ/mol, Al-Co −19 KJ/mol). At 900 °C, the diffusion of Al intensified, leading to the formation of precipitate phases with other elements. Therefore, the preliminary judgment is that the rod-shaped phase that was precipitated in the FCC is the L12 phase. L12 and FCC exhibited a high degree of coherency. XRD could not distinguish them. The elemental analysis results of the YHf-EHEA coating are shown in Figure 7. From Figure 7a, it can be observed that the BCC phase was AlNi-rich. Moreover, one can see that the Al, Co, Cr, Fe, Ni, Y, and Hf elements in the FCC phase were uniform. However, after heat treatment, rod-like precipitates formed in the FCC phase, which were found to be Al-rich after the EDS line scan (Figure 7b,c). In conclusion, both coating samples maintained the initial BCC/B2 morphology after heat treatment and the Al-rich rod-like L12 ..."
  },
  {
   "record_id": "PMC9955357::web::003::1_introduction",
   "paper_title": "Molten Salt Corrosion Behavior of Dual-Phase High Entropy Alloy for Concentrating Solar Power Systems.",
   "section": "1. Introduction",
   "publication_date": "2023-02-04",
   "evidence": "Here, the corrosion behavior of AlCoCrFeNI2.1 EHEA in molten NaCl-KCl-MgCl2 salt was investigated at 450 °C and 650 °C. The performance of EHEA was compared with one of the benchmark dual-phase structural alloys, namely duplex steel 2205 (DS2205). Dual-phase steels have been reported to have excellent corrosion resistance and a good combination of strength and ductility [,,,,,,]. To explain the effect of eutectic microstructure on the local electrochemical activity, Scanning Kelvin Probe (SKP) analysis was utilized to measure the relative electron work function [,,]. Our findings pave the way for further research on molten salt corrosion behavior of dual-phase alloys over a wide range of temperature for potential use in concentrating solar power systems."
  },
  {
   "record_id": "PMC11433366::web::004::1_introduction",
   "paper_title": "Effect of Alloying on Microstructure and Mechanical Properties of AlCoCrFeNi<sub>2.1</sub> Eutectic High-Entropy Alloy.",
   "section": "1. Introduction",
   "publication_date": "2024-09-12",
   "evidence": "Because AlCoCrFeNi2.1 EHEAs present excellent properties, far beyond those of single-phase high entropy-alloys, they have been widely studied by scholars as new types of HEA. However, the current treatment methods for improving strength and toughness are relatively complicated, and how to further improve the properties is the key to developing these alloys. Alloying is a simple method that can effectively improve the mechanical properties and expand the application range of alloys. The majority of the additional elements in previous studies were metals, while few studies were performed on how high-melting-point elements and non-metallic elements affect the mechanical characteristics. Therefore, the aim of this work is to improve the strength and ductility of AlCoCrFeNi2.1 EHEA alloys by the alloying method. The influence of alloying components and their content on the microstructures and mechanical properties of the alloy were investigated by adding the refractory metal elements V and Mo and the non-metallic element B to the AlCoCrFeNi2.1 alloy. The results will provide theoretical guidance for the development of new high-strength and high-toughness eutectic high-entropy alloys."
  },
  {
   "record_id": "PMC7021732::web::019::micro_pillar_compression",
   "paper_title": "Small-scale mechanical behavior of a eutectic high entropy alloy.",
   "section": "Micro-pillar compression",
   "publication_date": "2020-02-14",
   "evidence": "In contrast, the micro-pillars in L12 phase after deformation showed a high density of slip steps due to the activation of more slip systems and homogenous plastic flow as shown in Fig. 6(e). The deformation mechanism in conventional FCC alloys is mainly influenced by dislocation slip and twinning. The phase boundary in a dual phase alloy such as EHEA plays an important role in crack nucleation and failure mode. During compression of mixed pillars (Fig. 6(f)), initial slip steps formed near the top of L12 while B2 was still elastically deforming. Plastic deformation of B2 initiated at higher loads while there was continued work hardening of L12. Enhanced plasticity in this EHEA during bulk tensile testing has been explained by complex back-stresses from L12. A similar phenomenon was observed for the mixed micro-pillars. Once B2 plastic deformation initiated, it proceeded with the rapid formation of slip bands and majority of the plastic flow was concentrated on the B2 side since L12 was sufficiently work hardened. At higher loads, both L12 and B2 deformed simultaneously with the initiation and propagation of slip steps but the phase boundary was preserved without any sign of separation or cracking even after high compressive strains. This demonstrates that the semi-coherent phase boundary had a major contribution towards the high strength and ductility of this EHEA."
  },
  {
   "record_id": "PMC11433366::web::001::1_introduction",
   "paper_title": "Effect of Alloying on Microstructure and Mechanical Properties of AlCoCrFeNi<sub>2.1</sub> Eutectic High-Entropy Alloy.",
   "section": "1. Introduction",
   "publication_date": "2024-09-12",
   "evidence": "Due to their unique solid solution structures, high-entropy alloys (HEAs) typically exhibit various excellent properties, such as high strength/hardness [,,,], high wear resistance [], outstanding temperature strength [], strong structural stability [], good corrosion resistance [,], and oxidation resistance [] Generally speaking, HEAs can be divided into face-centered cubic (FCC) HEAs, body-centered cubic (BCC) HEAs, FCC + BCC two-phase HEAs, etc., from the perspective of phase structure. The high-entropy alloy (HEA) with a single FCC structure has high ductility but low hardness. For example, the CoCrFeMnNi alloy has a room temperature fracture elongation of 52%, but a tensile strength of only 563 MPa [], and the Fe40Mn40Co10Cr10 alloy has a tensile ductility of 58%, but a yield strength of only 240 MPa []. Although HEA with a single BCC structure has high strength and hardness, it also has low ductility. Therefore, an important challenge in the engineering application of high-entropy alloys is how to obtain high strength and high ductility at the same time. A potential solution to the problem lies in the development of eutectic high-entropy alloys (EHEAs), which are novel kinds of HEA, with significant advantages. Their composite structures, with FCC and BCC solid solutions, retain both the superior casting performance of eutectic alloys and the excellent mechanical qualities of HEAs."
  },
  {
   "record_id": "PMC7021732::web::000::abstract",
   "paper_title": "Small-scale mechanical behavior of a eutectic high entropy alloy.",
   "section": "Abstract",
   "publication_date": "2020-02-14",
   "evidence": "Eutectic high entropy alloys, with lamellar arrangement of solid solution phases, represent a new paradigm for simultaneously achieving high strength and ductility, thereby circumventing this well-known trade-off in conventional alloys. However, dynamic strengthening mechanisms and phase-boundary interactions during external loading remain unclear for these eutectic systems. In this study, small-scale mechanical behavior was evaluated for AlCoCrFeNi2.1 eutectic high entropy alloy, consisting of a lamellar arrangement of L12 and B2 solid-solution phases. The ultimate tensile strength was 1165 MPa with ductility of ~18% and ultimate compressive strength was 1863 MPa with a total compressive fracture strain of ~34%. Dual mode fracture was observed with ductile failure for L12 phase and brittle mode for B2 phase. Phase-specific mechanical tests using nano-indentation and micro-pillar compression showed higher hardness and strength and larger strain rate sensitivity for B2 compared with L12. Micro-pillars on B2 phase deformed by plastic barreling while L12 micro-pillars showed high density of slip steps due to activation of more slip systems and homogenous plastic flow. Mixed micro-pillars containing both the phases exhibited dual yielding behavior while the interface between L12 and B2 was well preserved without any sign of separation or cracking. Phase-specific friction analysis revealed higher coefficient of friction for B2 compared to L12."
  },
  {
   "record_id": "PMC7021732::web::023::conclusions",
   "paper_title": "Small-scale mechanical behavior of a eutectic high entropy alloy.",
   "section": "Conclusions",
   "publication_date": "2020-02-14",
   "evidence": "In this study, the mechanical behavior of AlCoCrFeNi2.1 eutectic high entropy alloy at small length scales was investigated for fundamental understanding of phase-specific contribution to the bulk mechanical response. The main conclusions are as follows:The as-cast microstructure consisted of eutectic lamellae of: (a) L12 phase rich in Fe, Co, Cr and (b) B2 phase rich in Ni and Al. The average grain size of the cast alloy was ~100 μm. The B2 phase consisted of Cr-rich precipitates with disordered BCC structure and average size of ~20 nm.The AlCoCrFeNi2.1 eutectic high entropy alloy showed excellent combination of strength and ductility in tensile and compression loading. In tensile loading, it showed a yield strength of 750 ± 24 MPa, ultimate tensile strength of 1165 ± 20 MPa and elongation of ~18%. In compressive loading, the yield strength was 517 ± 7 MPa, ultimate compressive strength was 1863 ± 12 MPa, and plasticity of ~34.3%. The fracture morphologies confirmed brittle mode for B2 phase and ductile mode for L12 phase.The B2 phase showed higher hardness and slightly lower modulus than L12 phase. Phase specific strain rate sensitivity (SRS) measurements demonstrated higher SRS value for B2 phase compared to L12. The overall SRS value for the alloy was close to that of the B2 phase, indicating B2 controlled deformation of the current EHEA.Uniaxial micro-pillar compression studies showed higher yield strength for B2 phase (~610 MPa) compared to L12 phase (~460 MPa). Mixed pillars containing ..."
  },
  {
   "record_id": "PMC10743261::web::001::1_introduction",
   "paper_title": "Phase-Specific Damage Tolerance of a Eutectic High Entropy Alloy.",
   "section": "1. Introduction",
   "publication_date": "2023-11-30",
   "evidence": "Multiphase alloys with heterogeneous microstructures demonstrate excellent combination of strength and ductility, making them attractive for myriad structural applications [,,]. Recently, eutectic high entropy alloys (HEAs) with multiple solid solution phases have been the subject of extensive research due to their promise of overcoming the strength-ductility tradeoff seen in metals and conventional alloys [,,,,,,,]. The AlCoCrFeNi2.1 alloy represents a canonical example of an eutectic HEA with the lamellar arrangement of CoCrFe-rich L12 and AlNi-rich B2 phases [], which exhibit an excellent combination of strength and ductility at room temperature as well as exceptional strain hardening behavior that is largely retained up to 700 °C. Different processing routes have been utilized for achieving a wide range of microstructural features, resulting in outstanding mechanical properties and excellent corrosion resistance in these alloys. The ease of attaining ultrafine microstructure in directly cast eutectic HEAs is uncommon in conventional alloys []. However, there is a limited understanding of the response of these alloys to complex loading states and the initiation of failure at microstructural length-scales [,,,,]. There are reports of brittle failure in eutectic HEAs subjected to loading at dynamic strain rates, such as during ballistic impact []."
  },
  {
   "record_id": "PMC7021732::web::009::bulk_tensile_and_compression",
   "paper_title": "Small-scale mechanical behavior of a eutectic high entropy alloy.",
   "section": "Bulk-tensile and compression",
   "publication_date": "2020-02-14",
   "evidence": "Tensile engineering stress-strain plot of the as-cast alloy is shown in Fig. 2(a). The EHEA showed a yield strength (σ0.2) of 750 ± 24 MPa, ultimate tensile strength (σUTS) of 1165 ± 20 MPa and elongation of ~18%. The AlCoCrFeNi2.1 EHEA showed a better combination of strength and ductility in tension when compared to several other reported EHEAs,. The fracture morphology of the sample after tensile test is shown in Fig. 2(b). The fracture surface showed two different fracture features. The B2 phase fractured in a brittle manner with the cracks initiating at one end and propagating to the other by leaving fish-bone shaped markings with radial stripes. In contrast, the L12 phase fractured in a ductile manner by necking into sharp lines without forming any dimples. The compressive engineering stress-strain curve of AlCoCrFeNi2.1 EHEA is shown in Fig. 2(c). The alloy showed a compressive yield strength (σ0.2) of 517 ± 7 MPa and compressive ultimate strength (σUTS) of 1863 ± 12 MPa, with a total compressive fracture strain of ~34%. These compressive properties are superior to the other eutectic compositions as well,. The compressive fracture surface is shown in Fig. 2(d) with cleavage steps and slip features that are clear in the higher magnification image (inset). These features suggest quasi-cleavage type of fracture for AlCoCrFeNi2.1 EHEA in the compression mode, with micro-cracks originating at the coarse B2 phase and deflecting from the interface to grow into large cracks."
  },
  {
   "record_id": "PMC10743261::web::000::abstract",
   "paper_title": "Phase-Specific Damage Tolerance of a Eutectic High Entropy Alloy.",
   "section": "Abstract",
   "publication_date": "2023-11-30",
   "evidence": "AbstractPhase-specific damage tolerance was investigated for the AlCoCrFeNi2.1 high entropy alloy with a lamellar microstructure of L12 and B2 phases. A microcantilever bending technique was utilized with notches milled in each of the two phases as well as at the phase boundary. The L12 phase exhibited superior bending strength, strain hardening, and plastic deformation, while the B2 phase showed limited damage tolerance during bending due to micro-crack formation. The dimensionalized stiffness (DS) of the L12 phase cantilevers were relatively constant, indicating strain hardening followed by increase in stiffness at the later stages and, therefore, indicating plastic failure. In contrast, the B2 phase cantilevers showed a continuous drop in stiffness, indicating crack propagation. Distinct differences in micro-scale deformation mechanisms were reflected in post-compression fractography, with L12-phase cantilevers showing typical characteristics of ductile failure, including the activation of multiple slip planes, shear lips at the notch edge, and tearing inside the notch versus quasi-cleavage fracture with cleavage facets and a river pattern on the fracture surface for the B2-phase cantilevers.Keywords: micro-cantilever bending, eutectic system, high entropy alloy"
  },
  {
   "record_id": "PMC9319277::web::003::1_introduction",
   "paper_title": "Corrosion Behavior of the AlCoCrFeNi<sub>2.1</sub> Eutectic High-Entropy Alloy in Chloride-Containing Sulfuric Acid Solutions at Different Temperature",
   "section": "1. Introduction",
   "publication_date": "2022-07-11",
   "evidence": "Scholars have conducted much research about the corrosion behavior of HEAs, but studies on EHEA corrosion are relatively rare. It has been reported that HEAs exhibit different corrosion resistance in various corrosive environments. Wang et al. [] discovered that the CoCrFeNiMo0.01 EHA displayed pseudo-passive behavior in an H2S-containing environment. Luo et al. [] found that the pitting corrosion resistance of the interstitial equiatomic CoCrFeMnNi HEA was influenced by carbon content in a Cl--containing solution. Most studies have focused on the corrosion behavior of HEAs at room temperature (~25 °C). However, HEAs would are often used in corrosive mediums at different temperatures. Until now, only a few studies have paid attention to the influence of temperature on the corrosion of HEAs in aqueous solutions. For instance, Chou et al. [] showed that the pitting potential of the Co1.5CrFeNi1.5Ti0.5Mo0.1 HEA changed linearly with the logarithm of chloride concentration at 70 °C and 80 °C. Moreover, studies on the corrosion behavior of HEAs are usually based on stainless steel. The relationship between corrosion behavior and environmental temperature is an essential topic in the study of stainless steel. Hou et al. [] considered that the passive film resistance of 316L SS in methyl diethanolamine solution dropped as the solution temperature rose. Cui et al. [] established that temperature caused a decrease ..."
  },
  {
   "record_id": "PMC6175879::web::006::dislocation_dominated_plastic_deformatio",
   "paper_title": "The Exceptional Strong Face-centered Cubic Phase and Semi-coherent Phase Boundary in a Eutectic Dual-phase High Entropy Alloy AlCoCrFeNi.",
   "section": "Dislocation dominated plastic deformation in FCC phases",
   "publication_date": "2018-10-08",
   "evidence": "Considering the much higher strength of BCC phase compared to that of FCC phase in the eutectic dual-phase AlCoCrFeNi HEA, the former served as the strengthening phase while the latter became the dominant carrier of deformation via dislocation plasticity, as evidenced by the in-situ deformation observations. At the early stage of deformation, plenty of dislocations were released from the phase boundary and glided along parallel slip bands, leading to the initial yielding. Despite of abundant dislocation sources, dislocation slips within the FCC phase became difficult due to the high lattice friction in HEAs, the intrinsic strengthening effect of multiple solution atoms, and therefore cross slip were activated by homogenous increase of strain accumulation. The interaction between primary slip arrays and cross-slip systems was to increase the rate of dislocation storage by forming dislocation substructures, and to further promote work hardening of the FCC phase. Meanwhile, the BCC phase was difficult to deform even at crack tips with high stress, as evidenced by the in situ deformation experiments shown in Fig. S3. When the loading direction was perpendicular to the thickness direction of BCC lamellar, dense dislocations were blocked by the phase boundary, leading to the stress concentration, which made a small number of dislocations penetrate through or emitted from the boundary. ..."
  },
  {
   "record_id": "PMC4145285::web::005::tensile_properties",
   "paper_title": "A promising new class of high-temperature alloys: eutectic high-entropy alloys.",
   "section": "Tensile properties",
   "publication_date": "2014-08-27",
   "evidence": "The eutectic AlCoCrFeNi2.1 alloy, with an fcc/B2 dual-phase constitution and a uniform and fine lamellar microstructure, exhibited the combination of both high fracture strength and high ductility, which has never been achieved in previously reported HEAs. The room temperature tensile test showed a fracture stress of 944 MPa and an elongation of 25.6%, from the engineering stress-strain curve given in Fig. 4a. These values converted to 1186 MPa and 22.8% in the true stress/strain condition. Noteworthily, this alloy exhibited an ultra-high strain hardening behavior, having the proof stress (the proof stress is determined by shifting the linear elastic curve to 0.2% strain. We choose to not to call it the yield stress, as the mechanism for such a low elastic limit is still unclear at this stage.) of 75 MPa but reaching the fracture stress close to 1.2 GPa. At elevated temperatures of 600 and 700°C (Fig. 4b), the proof stress, fracture stress and elongation were 95 MPa, 806 MPa, 33.7%, and 108 MPa, 538 MPa, 22.9%, respectively, both in the true stress/strain condition. The combination of high strength and high ductility for this EHEA could be maintained at least up to 700°C. The mechanical properties of the as-cast EHEA can be further tuned by thermomechanical treatments. Figure 5 shows that a simple cold rolling with a thick reduction of 8% can increase the engineering/true proof stress and fracture stress to 275 MPa and 1145 MPa/1265 MPa, respectively, while remaining a ..."
  },
  {
   "record_id": "PMC9319277::web::002::1_introduction",
   "paper_title": "Corrosion Behavior of the AlCoCrFeNi<sub>2.1</sub> Eutectic High-Entropy Alloy in Chloride-Containing Sulfuric Acid Solutions at Different Temperature",
   "section": "1. Introduction",
   "publication_date": "2022-07-11",
   "evidence": "The content of Al, Co, Cr, Fe, and Ni in the EHEA all affect its passivation behavior, which is essential to the corrosion resistance of the EHEA. Alloys with more than 12 at.% Cr content can form a passive film in some solutions []. Cr is the primary component of passive films [,]. Additionally, some research have reported that Ni, Al, Co, and Fe can also be the constituent elements in passive films [,,]. Shi et al. [] established that an increase in Al content reduced the protective ability of the passive film on the surface of the AlxCoCrFeNi HEA in 3.5% NaCl solutions. Chen et al. [] discovered that the Cu0.5NiAlCoCrFeSi HEA was more prone to pitting than 304 stainless steel in chloride solution. Xu et al. [] demonstrated that Ni was the central element of the passive film on CoCrFeMnNi HEA in sulfuric acid solution. In addition, Chai et al. [] revealed that the FeCoNiCr0.5 HEA possessed good local corrosion resistance, while the dissolution of the Cr-rich zone in the dendrites was accelerated. Lin et al. [] asserted that the Al-Ni-rich phase on FCC was the preferential corrosion area in chloride-containing sulfuric acid solutions. Additionally, unique microstructures alter the corrosion behavior of the AlCoCrFeNi2.1 EHEAs, compared to other HEAs. The eutectic structure may lead to the galvanic effect, which making the EHEA face local corrosion risks. Corrosion is a serious threat to the security of ..."
  },
  {
   "record_id": "PMC11433366::web::012::3_2_mechanical_properties",
   "paper_title": "Effect of Alloying on Microstructure and Mechanical Properties of AlCoCrFeNi<sub>2.1</sub> Eutectic High-Entropy Alloy.",
   "section": "3.2. Mechanical Properties",
   "publication_date": "2024-09-12",
   "evidence": "On the one hand, this is because when B element is added, the microstructures of alloy change from typical lamellar eutectic morphologies to a petal-like structure (see Figure 1b), in which the petal-like dendrites with BCC structures are coarser, which is conducive to the improvement of the hardness of alloy. Meanwhile, with the increase in the B content, the proportion of BCC phase also increases, and the increase in the harder BCC phase leads to an increase in hardness. On the other hand, unlike the alloys with the addition of V and Mo, the grain refinement is obvious in the alloys with the increase in the content of B. The strengthening effect brought about by grain refinement is also the main reason for the increase in the hardness of these alloys. In conclusion, the addition of high-melting-point metal and nonmetallic elements has a direct impact on the hardness of the AlCoCrFeNi2.1 alloy, with nonmetallic elements having the greatest effect."
  },
  {
   "record_id": "PMC9955357::web::009::3_2_electrochemical_and_corrosion_behavi",
   "paper_title": "Molten Salt Corrosion Behavior of Dual-Phase High Entropy Alloy for Concentrating Solar Power Systems.",
   "section": "3.2. Electrochemical and Corrosion Behavior",
   "publication_date": "2023-02-04",
   "evidence": "Corrosion rates (CR) based on Icorr and Mass loss for the two alloys was calculated from the following equations [,]: where K1 = 3.27 × 10−3 [mm/(μA·cm·year)] is a constant which is taken from ASTM G102; EW is equivalent weight in g/equivalent; ρ is density in g/cm3; and Icorr is corrosion current density in μA/cm2. where k is constant 8.76 × 104; CR is in (mm/y), which is taken from ASTM G31; mloss is the mass loss (g) of the metal in time t (h); A is the surface area of the material exposed (cm2); and ρ is the density of the material (g/cm3). The corrosion rate based on Equations (1) and (2) for the two alloys at 450 °C and 650 °C are shown in Table 3. AlCoCrFeNi2.1 showed a significantly lower corrosion rate compared to DS2205 at both the temperatures. Poor stability of Fe-based alloys at elevated temperatures in molten chloride media due to dissolution of Cr and Fe has been reported previously [,]. In contrast, AlCoCrFeNi2.1 high-entropy alloy showed a higher corrosion resistance compared to dual-phase DS2205 steel possibly, due to greater stability of its constituent elements in the molten chloride salt environment."
  },
  {
   "record_id": "PMC6175879::web::015::discussion",
   "paper_title": "The Exceptional Strong Face-centered Cubic Phase and Semi-coherent Phase Boundary in a Eutectic Dual-phase High Entropy Alloy AlCoCrFeNi.",
   "section": "Discussion",
   "publication_date": "2018-10-08",
   "evidence": "In conclusion, by conducting in situ deformation experiments in a eutectic dual-phase AlCoCrFeNi HEA, a unique mechanism of second phase strengthening was revealed. In contrast to the traditional thought, which considers hard BCC phases as the crucial strengthening component in dual-phase alloys, it is found that pre-strained FCC can also make significant contribution to the macroscopic strength of the eutectic dual-phase AlCoCrFeNi HEA. Consequently, increasing the proportion of pre-strained FCC phases can effectively enhance the strength of material. The strengthening effect of this eutectic dual-phase HEAs lies in several aspects. Firstly, given the large lattice resistance to dislocation gliding, BCC phases served as powerful barriers to prevent massive dislocations from moving inside, which intrinsically enhanced the overall strength. Moreover, the unexpected strong phase boundaries made great contribution in balancing strength-ductility while the abundant cross-slip activities can increase the rate of dislocation storage and made FCC phases exceptionally strong. Our results not only revealed the underlying strengthening mechanism of FCC/BCC dual-phase HEAs, but also shed light on new strategies for optimizing the mechanical properties of dual-phase HEAs."
  },
  {
   "record_id": "PMC11433366::web::003::1_introduction",
   "paper_title": "Effect of Alloying on Microstructure and Mechanical Properties of AlCoCrFeNi<sub>2.1</sub> Eutectic High-Entropy Alloy.",
   "section": "1. Introduction",
   "publication_date": "2024-09-12",
   "evidence": "These results showed that the yield strength (1437 ± 26 MPa), tensile strength (1562 ± 33 MPa), and elongation (14 ± 1%) of the AlCoCrFeNi2.1 alloy after annealing at low temperature were significantly improved compared with the as-cast alloy. Eutectic high-entropy alloys exhibit an excellent balance of toughness and strength at room temperature. However, there is still an immediate requirement to design structural components with more strength and ductility due to the increasing technical requirements and harsher operating environments in industrial applications. The demand for stronger and more ductile structural elements has increased as airplane components have become more demanding and technical standards have advanced. Therefore, it is of significance to develop a new eutectic high-entropy alloy with superior properties based on AlCoCrFeNi2.1."
  },
  {
   "record_id": "PMC10743261::web::017::4_conclusions",
   "paper_title": "Phase-Specific Damage Tolerance of a Eutectic High Entropy Alloy.",
   "section": "4. Conclusions",
   "publication_date": "2023-11-30",
   "evidence": "The phase-specific damage tolerance of AlCoCrFeNi2.1 EHEA was studied, with lamellar microstructures consisting of L12 and B2 phases. In situ microcantilever bending technique was used with notches milled in the two phases and at the phase boundary. The cantilever with the notch on the L12 phase demonstrated superior bending strength and ductility over the B2 phase notched cantilever, which yielded lower stress and deformed less. This divergence from phase-specific micropillar compression behavior may be due to micro-crack formation in the B2 phase under bending stress and the reduced effectiveness of nano-precipitate strengthening due to a smaller test volume and a lack of extrinsic mechanisms to hinder crack growth. The bending deformation process showed four distinct stages based on dimensionalized stiffness (DS) values. L12 and B2 phases showed significant stiffness variations, with L12 cantilevers showing constant DS values due to strain hardening during stage III and increases in DS values indicating plastic failure during stage IV. B2 cantilevers showed an initial drop in DS during stage III (micro-crack formation) and a sharp drop in DS during stage IV, indicating crack propagation. The energy absorbed during deformation in the presence of a notch in L12 phase was 44% higher than in B2 phase."
  },
  {
   "record_id": "PMC6353877::web::000::abstract",
   "paper_title": "Enhanced strength-ductility synergy in ultrafine-grained eutectic high-entropy alloys by inheriting microstructural lamellae.",
   "section": "Abstract",
   "publication_date": "2019-01-30",
   "evidence": "Realizing improved strength–ductility synergy in eutectic alloys acting as in situ composite materials remains a challenge in conventional eutectic systems, which is why eutectic high-entropy alloys (EHEAs), a newly-emerging multi-principal-element eutectic category, may offer wider in situ composite possibilities. Here, we use an AlCoCrFeNi2.1 EHEA to engineer an ultrafine-grained duplex microstructure that deliberately inherits its composite lamellar nature by tailored thermo-mechanical processing to achieve property combinations which are not accessible to previously-reported reinforcement methodologies. The as-prepared samples exhibit hierarchically-structural heterogeneity due to phase decomposition, and the improved mechanical response during deformation is attributed to both a two-hierarchical constraint effect and a self-generated microcrack-arresting mechanism. This work provides a pathway for strengthening eutectic alloys and widens the design toolbox for high-performance materials based upon EHEAs. Producing in situ composite materials with superior strength and ductility has long been a challenge. Here, the authors use lamellar microstructure inherited from casting, rolling, and annealing to produce an ultrafine duplex eutectic high entropy alloy with outstanding properties."
  },
  {
   "record_id": "PMC11433366::web::002::1_introduction",
   "paper_title": "Effect of Alloying on Microstructure and Mechanical Properties of AlCoCrFeNi<sub>2.1</sub> Eutectic High-Entropy Alloy.",
   "section": "1. Introduction",
   "publication_date": "2024-09-12",
   "evidence": "Lu [] combined the advantages of FCC and BCC high-entropy alloys, and designed a representative dual-phase eutectic high-entropy alloy AlCoCrFeNi2.1 based on the point ratio of eutectic components, which achieves an excellent match of high strength and good ductility. The X-ray diffraction (XRD) analysis showed that the alloy is composed of two phases, FCC and B2 structures, while the tensile strength is 944 MPa and the fracture elongation is 25.6%. Ting X et al. [] observed scattered nanocrystalline precipitates with BCC structures in the B2 phase and spherical or ellipsoidal L12 precipitates in the FCC phase in an AlCoCrFeNi2.1 alloy. The results showed a high level of consistency between the L12 precipitate and its FCC matrix, as well as between the BCC precipitate and its B2 matrix. In order to explore the excellent strength and toughness of AlCoCrFeNi2.1 alloy, Gao X et al. [] found that AlCoCrFeNi2.1 alloy has staggered microstructures, which include three-dimensional regular FCC (L12)/BCC (B2) composite structures and two-dimensional lamellar structures. Two different fracture mechanisms were identified in this alloy: ductile fracture in the FCC (L12) phase and brittle fracture in the BCC (B2) phase. The AlCoCrFeNi2.1 alloy was treated by low-temperature rolling and annealing processes, and new hierarchical microstructures formed []."
  },
  {
   "record_id": "PMC9319277::web::000::abstract",
   "paper_title": "Corrosion Behavior of the AlCoCrFeNi<sub>2.1</sub> Eutectic High-Entropy Alloy in Chloride-Containing Sulfuric Acid Solutions at Different Temperature",
   "section": "Abstract",
   "publication_date": "2022-07-11",
   "evidence": "In this work, the influence of temperature on the corrosion behavior of AlCoCrFeNi2.1 eutectic high-entropy alloy in a chloride-containing sulfuric acid solution was investigated using electrochemical measurement, X-ray photoelectron spectroscopy, and scanning electron microscopy. Results show that the passive film of AlCoCrFeNi2.1 is stable in chloride-containing sulfuric acid solutions at low temperatures, while an unstable film forms on the alloy at high temperatures. Furthermore, temperature changes the proportion of hydroxide and oxide in Fe and Cr, but it has no noticeable effect on Al and Ni, which is a significant factor on the passive behavior. L12 phase exhibits good corrosion resistance at different temperatures. Pitting occurred on B2 phase in the chloride-containing sulfuric acid solution at a low temperature of 5 °C, while pitting and dissolution take place on AlCoCrFeNi2.1 in the acid solution at room temperature and above."
  },
  {
   "record_id": "PMC6353877::web::002::introduction",
   "paper_title": "Enhanced strength-ductility synergy in ultrafine-grained eutectic high-entropy alloys by inheriting microstructural lamellae.",
   "section": "Introduction",
   "publication_date": "2019-01-30",
   "evidence": "Moreover, the safety and advancement of modern technologies not only strongly relies on current mechanical properties of these eutectic alloys, but also calls for better ones. To date, many conventional routes to optimize eutectic alloys, such as processing to create line defects, usually result in reduced ductility. Previous studies showed that engineering an ultrafine-grained duplex microstructure by severe cold-rolling and annealing could dramatically strengthen eutectic alloys although degrading ductility. Recently, Wu et al. developed a heterogeneous structure of bimodal grains in Ti, which possesses < 30 vol.% soft, coarse-grained lamellae embedded in a hard, ultrafine-grained lamella matrix,. The resulting materials exhibited great ductility, as a high density of lamella interfaces could induce the building of large strain gradients across them during deformation. Meanwhile, the full deformation constraint imposed by the hard lamella matrix enables the soft lamellae to be almost as strong as the hard matrix, thus making materials with high strength,. So a remarkable strength–ductility enhancement is expected if we could inherit the heterogeneous lamellar nature via an appropriate thermo-mechanical treatment, instead of just tailoring a dual-phase ultrafine-grained structure in eutectic alloys."
  },
  {
   "record_id": "PMC11433366::web::000::abstract",
   "paper_title": "Effect of Alloying on Microstructure and Mechanical Properties of AlCoCrFeNi<sub>2.1</sub> Eutectic High-Entropy Alloy.",
   "section": "Abstract",
   "publication_date": "2024-09-12",
   "evidence": "AbstractIn order to explore the effect of alloying on the microstructures and mechanical properties of AlCoCrFeNi2.1 eutectic high-entropy alloys (EHEAs), 0.1, 0.2, and 0.3 at.% V, Mo, and B were added to the AlCoCrFeNi2.1 alloy in this work. The effects of the elements and contents on the phase composition, microstructures, mechanical properties, and fracture mechanism were investigated. The results showed that the crystal structures of the AlCoCrFeNi2.1 EHEAs remained unchanged, and the alloys were still composed of FCC and BCC structures, whose content varied with the addition of alloying elements. After alloying, the aggregation of Co, Cr, Al, and Ni elements remained unchanged, and the V and Mo were distributed in both dendritic and interdendritic phases. The tensile strengths of the alloys all exceeded 1000 MPa when the V and Mo elements were added, and the Mo0.2 alloy had the highest tensile strength, of 1346.3 MPa, and fracture elongation, of 24.6%. The alloys with the addition of V and Mo elements showed a mixed ductile and brittle fracture, while the B-containing alloy presented a cleavage fracture. The fracture mechanism of Mo0.2 alloy is mainly crack propagation in the BCC lamellae, and the FCC dendritic lamellae exhibit the characteristics of plastic deformation.Keywords: eutectic high-entropy alloy, alloying, microstructures, mechanical properties, fracture mechanism"
  },
  {
   "record_id": "PMC6175879::web::010::the_role_of_phase_boundary_in_second_pha",
   "paper_title": "The Exceptional Strong Face-centered Cubic Phase and Semi-coherent Phase Boundary in a Eutectic Dual-phase High Entropy Alloy AlCoCrFeNi.",
   "section": "The role of phase boundary in second phase strengthening",
   "publication_date": "2018-10-08",
   "evidence": "It is a traditional method to strengthen alloys by introducing internal boundaries in order to impede the motion of dislocations. Unlike coherent twin boundaries with low excess energies, grain boundaries and phase boundaries are regarded as major strengthening agents for metallic materials because they are more effective in resisting dislocation penetration. In this study, the phase boundaries were produced through the eutectic reaction during the preparation of dual-phase AlCoCrFeNi2.1 HEA. Thereby plenty of phase boundaries contained in this HEA were semi-coherent due to the low energy features. Given that interfacial strength increases with the decrease of coherency, phase boundaries of semi-coherence prepared in eutectic dual-phase HEAs were observed to be strong enough to accommodate high stress due to their chemically disordered features, as proved by the HAADF-STEM observation (Fig. 3b) and in-situ straining experiments. Such strong phase boundaries were essential to achieving compatibility of interphase deformations through enhancing the strength of FCC phases by work hardening effects so as to commence dislocation glide in BCC phases."
  },
  {
   "record_id": "PMC6175879::web::011::phase_strengthening_vs_boundary_strength",
   "paper_title": "The Exceptional Strong Face-centered Cubic Phase and Semi-coherent Phase Boundary in a Eutectic Dual-phase High Entropy Alloy AlCoCrFeNi.",
   "section": "Phase strengthening vs. boundary strengthening in dual-phase",
   "publication_date": "2018-10-08",
   "evidence": "Interestingly, the above results demonstrate that, in strong contrast to our traditional understanding, the FCC phase was capable of not only carrying large plastic deformation but also served as the source of strengthening. The high lattice friction in matrix and the strong semi-coherent phase boundaries which were decorated by disorderedly distributed multiple elements enabled high dislocation density in FCC phases. As a result, significant hardening of material would be expected. To confirm our hypothesis, we compared the mechanical properties of the as-casted and pre-strained AlCoCrFeNi alloys. The pre-straining was conducted to raise the dislocation density in the FCC phase. A comparison of the strain-stress curves of the as-casted and cold rolled dual-phase AlCoCrFeNi2.1 HEAs was shown in Fig. 4a. The strain-stress curve of the as-casted sample (black curve) exhibited a combination of high fracture strength (~0.94 GPa) and good ductility (~25%). Meanwhile, the mechanical property of the eutectic dual-phase HEA in cast can be further improved by reasonable pre-straining (shown by the red line in Fig. 4a), which remarkably increased the yield strength by a factor of ~5."
  },
  {
   "record_id": "PMC10743261::web::003::2_materials_and_methods",
   "paper_title": "Phase-Specific Damage Tolerance of a Eutectic High Entropy Alloy.",
   "section": "2. Materials and Methods",
   "publication_date": "2023-11-30",
   "evidence": "The AlCoCrFeNi2.1 EHEA was synthesized via vacuum-arc melting, wherein a predetermined quantity of the constituent pure elements was melted and homogenized. Following that, the samples underwent metallographic preparation for characterization, which involved mechanical grinding using SiC papers, with grit sizes ranging from 400 to 1200 and cloth polishing to obtain scratch free surfaces, using a 1 µm and 0.25 µm diamond solution. The final step in the preparation process involved the use of 0.02 μm colloidal silica to achieve a mirror finish. Microstructural characterization was carried out using FEI Nova Nano SEM230. The electron backscatter diffraction (EBSD) inverse pole figure (IPF) in Figure 1a shows the grain of interest. The selection of this grain was based on its size, which allowed for the milling of multiple microcantilevers without the influence of grain orientation on the properties. The secondary electron image in Figure 1b shows the lamellar arrangement of the B2 and the L12 phases in the EHEA, each phase being 2–3 µm in width. The B2 phase shows lighter contrast and L12 shows a darker contrast. The location of a representative micro-cantilever is also depicted in Figure 1b. To fabricate the microcantilevers, elongated and parallel lamellae were chosen for the milling of notches. As illustrated in Figure 1c, these lamellae extended through the thickness of the micro-cantilever, thereby enabling the notches to be entirely within the same phase."
  },
  {
   "record_id": "PMC6353877::web::003::introduction",
   "paper_title": "Enhanced strength-ductility synergy in ultrafine-grained eutectic high-entropy alloys by inheriting microstructural lamellae.",
   "section": "Introduction",
   "publication_date": "2019-01-30",
   "evidence": "Inspired by the above idea, we architected a dual-phase heterogeneous lamella (DPHL) structure (Fig. 1) in a cold-rolled and annealed AlCoCrFeNi2.1 (at%) EHEA (detailed processing procedure shown in Methods). Compared to the aforementioned heterogeneous lamella structure, our current structure features the strength heterogeneity with soft/hard phases instead of bimodal grains, and simultaneously exhibits a higher lamella density arising from the full lamella nature of eutectic alloys. Furthermore, owning to phase decomposition, there are substantial hard intergranular B2 (ordered-body-centered-cubic) precipitates in the soft FCC (face-centered-cubic) lamella matrix, thereby imparting an additional rigid deformation constraint to FCC grains,. Unexpectedly, due to the introduction of the DPHL structure, the as-fabricated EHEAs can activate microcrack-arresting mechanisms (the extrinsically ductilizing effect) to further extend the strain-hardening ability (the intrinsically ductilizing effect) for great ductility at the late stage of deformation. In this study, we prepared three EHEAs with the DPHL structure, and denoted them as DPHL660, DPHL700, and DPHL740 as per their different annealing temperatures, to study their mechanical behavior and deformation mechanisms."
  },
  {
   "record_id": "PMC7021732::web::020::micro_pillar_compression",
   "paper_title": "Small-scale mechanical behavior of a eutectic high entropy alloy.",
   "section": "Micro-pillar compression",
   "publication_date": "2020-02-14",
   "evidence": "TEM analysis was performed on a deformed mixed micro-pillar containing the B2 and L12 phases in order to understand the effect of deformation on the interface after the compression test. Figure 7 shows bright-field TEM images of a mixed micropillar. The B2 and L12 regions are indicated within the bright-field image in Fig. 7(a). The superlattice diffraction spots within the TEM selected area diffraction (SAD) patterns (shown as insets) confirmed that both phases were still ordered after the compression and no disordering and phase transformation occurred after deformation. Significantly higher dislocation density was observed for the L12 phase compared to B2 near the interface supporting the greater extent of plastic deformation for the L12. Zoomed in view near the B2 phase (Fig. 7(b)) showed high density of nano-sized precipitates that were previously identified as Cr-rich with disordered BCC structure,. The average size of the precipitates was about 20 nm. The presence of these precipitates further enhanced the strength of B2 phase by acting as barriers for dislocation movement. Toughening in HEAs is influenced by the formation of stacking-fault parallelepipeds, arresting of undissociated dislocations at planar slip bands, and easy motion of Shockley partial dislocations. The micro-pillar compression tests revealed that the interphase boundary was preserved during deformation and led to exceptional strain hardening and strength-ductility combination."
  },
  {
   "record_id": "PMC9319277::web::022::3_4_corrosion_observation",
   "paper_title": "Corrosion Behavior of the AlCoCrFeNi<sub>2.1</sub> Eutectic High-Entropy Alloy in Chloride-Containing Sulfuric Acid Solutions at Different Temperature",
   "section": "3.4. Corrosion Observation",
   "publication_date": "2022-07-11",
   "evidence": "Based on the above conclusions, the corrosion process of the EHEA in the test solution is schematically described in Figure 14. The passive films of few Al-Ni-rich phases are attacked by Cl− at lower temperature (Figure 14a2), and then occurs localized corrosion (Figure 14a3); while the passive films of Al-Ni-rich phases are damaged (Figure 14b2), and more Al-Ni-rich phases are dissolved at higher temperature (Figure 14b3). Metastable pits are preferentially created on the grain boundary or B2 phase. Pitting is enhanced by the effect of polarization. Due to autocatalysis by the caustic ions, the metastable pits gradually grow in the pitting corrosion area or the selective dissolution region. Moreover, the size of the selective dissolution region increases with temperature, and pitting occurs on the surface at various temperatures."
  },
  {
   "record_id": "PMC5818523::web::002::introduction",
   "paper_title": "Simultaneous Strength-Ductility Enhancement of a Nano-Lamellar AlCoCrFeNi<sub>2.1</sub> Eutectic High Entropy Alloy by Cryo-Rolling and Annealing.",
   "section": "Introduction",
   "publication_date": "2018-02-19",
   "evidence": "Thus, significant heterogeneities (microstructural, crystal structure or compositional) are present in such materials which appear to be the key factors for overcoming the strength-ductility trade-off. Recently, high entropy alloys (HEAs) have emerged as a novel class of multicomponent alloys containing five or more elements in equi-atomic or nearly equi-atomic compositions. Despite having a large number of components, HEAs can show simple phases such as FCC, BCC and FCC + BCC,, presumably due to their high configurational entropy, which decreases the free energy sufficiently to stabilize simple solid solution phases. HEAs have triggered a remarkable research interest in recent years due to their unique and intriguing mechanical properties,,. In order to further enhance the properties of HEAs, dual and multi-phase HEAs having mixture of soft and hard phases are suggested. Non-equiatomic AlCoCrFeNi2.1 eutectic HEA is a noteworthy example of such multiphase HEAs. Wani et al., have recently demonstrated that thermo-mechanical processing can effectively tailor the microstructure and properties of the EHEAs. In the present work, an interesting effect of cryo-rolling and annealing on the microstructure and mechanical properties of AlCoCrFeNi2.1 EHEA is reported. Although cryo-rolling has been investigated in single phase HEAs,, we have found a remarkable effect of cryo-rolling on tensile properties of the EHEA for the ..."
  },
  {
   "record_id": "PMC4145285::web::000::abstract",
   "paper_title": "A promising new class of high-temperature alloys: eutectic high-entropy alloys.",
   "section": "Abstract",
   "publication_date": "2014-08-27",
   "evidence": "High-entropy alloys (HEAs) can have either high strength or high ductility, and a simultaneous achievement of both still constitutes a tough challenge. The inferior castability and compositional segregation of HEAs are also obstacles for their technological applications. To tackle these problems, here we proposed a novel strategy to design HEAs using the eutectic alloy concept, i.e. to achieve a microstructure composed of alternating soft fcc and hard bcc phases. As a manifestation of this concept, an AlCoCrFeNi2.1 (atomic portion) eutectic high-entropy alloy (EHEA) was designed. The as-cast EHEA possessed a fine lamellar fcc/B2 microstructure, and showed an unprecedented combination of high tensile ductility and high fracture strength at room temperature. The excellent mechanical properties could be kept up to 700°C. This new alloy design strategy can be readily adapted to large-scale industrial production of HEAs with simultaneous high fracture strength and high ductility."
  },
  {
   "record_id": "PMC6175879::web::013::discussion",
   "paper_title": "The Exceptional Strong Face-centered Cubic Phase and Semi-coherent Phase Boundary in a Eutectic Dual-phase High Entropy Alloy AlCoCrFeNi.",
   "section": "Discussion",
   "publication_date": "2018-10-08",
   "evidence": "The properties of many metallic alloys are essentially related to the structure, morphology and chemical distribution of boundaries. In terms of atomic structure, the phase boundaries contained in eutectic dual-phase HEAs were supposed to be insufficient in prohibiting dislocations due to their semi-coherent nature, which is similar to those widely reported in NiAl dual-phase intermetallic alloys,. However, in-situ deformation tests revealed that dense dislocation storage can be achieved within FCC phases and dislocation walls were formed along phase boundaries. The unexpected strong interfaces are thought to be highly related to the chemically disordered distribution of multiple solution atoms at phase boundaries as well as in the matrix of HEAs. Particularly, an ultra-thin segregation zone of randomly distributed Cr atoms, typically less than 2 nm in width (Fig. 3b and S4), was detected near the phase boundary without forming complex intermetallic compounds, which were intrinsically brittle and would lead to stress concentration. Additionally, the solute segregation may enhance the thermodynamic stability and suppress diffusional boundary migration by lowering phase boundary energy, such that improving the mechanical properties of eutectic dual-phase HEAs at elevated temperature, which is consistent with the previous ex-situ results,. Beyond the effect of unique chemical constitution discussed above, cross slip of ..."
  },
  {
   "record_id": "PMC9365806::web::014::psr_mechanisms",
   "paper_title": "Phase-selective recrystallization makes eutectic high-entropy alloys ultra-ductile.",
   "section": "PSR mechanisms",
   "publication_date": "2022-08-10",
   "evidence": "In conclusion, we proposed a universal routine of PSR to ductilize eutectic alloys. The PSR, i.e., individual recrystallization of the soft phase and recovery of the hard phase, was achieved by tailoring the strain partitioning behavior between the two phases of eutectics. Compared with traditional processing methods for eutectic alloys, the PSR prevents premature fracture by eliminating the weak boundaries and thus triggers the intrinsically superior strain hardening capacity of the two phases through dislocation multiplication and potential phase transformation. In a typical FCC/B2 EHEA, ∼35% uniform elongation and ∼2 GPa true stress were achieved. The strain partitioning-dominated PSR mechanism ensures its good adaptability in other duplex alloys, as proven in the A357 alloy. This strategy will open new frontiers of eutectic alloys as high-strength metallic materials in model civilization by combining their excellent castability and strengthening capacity."
  },
  {
   "record_id": "PMC5818523::web::000::abstract",
   "paper_title": "Simultaneous Strength-Ductility Enhancement of a Nano-Lamellar AlCoCrFeNi<sub>2.1</sub> Eutectic High Entropy Alloy by Cryo-Rolling and Annealing.",
   "section": "Abstract",
   "publication_date": "2018-02-19",
   "evidence": "Nano-lamellar (L12 + B2) AlCoCrFeNi2.1 eutectic high entropy alloy (EHEA) was processed by cryo-rolling and annealing. The EHEA developed a novel hierarchical microstructure featured by fine lamellar regions consisting of FCC lamellae filled with ultrafine FCC grains (average size ~200–250 nm) and B2 lamellae, and coarse non-lamellar regions consisting of ultrafine FCC (average size ~200–250 nm), few coarse recrystallized FCC grains and rather coarse unrecrystallized B2 phase (~2.5 µm). This complex and hierarchical microstructure originated from differences in strain-partitioning amongst the constituent phases, affecting the driving force for recrystallization. The hierarchical microstructure of the cryo-rolled and annealed material resulted in simultaneous enhancement in strength (Yield Strength/YS: 1437 ± 26 MPa, Ultimate Tensile Strength/UTS: 1562 ± 33 MPa) and ductility (elongation to failure/ef ~ 14 ± 1%) as compared to the as-cast as well as cold-rolled and annealed materials. The present study for the first time demonstrated that cryo-deformation and annealing could be a novel microstructural design strategy for overcoming strength-ductility trade off in multiphase high entropy alloys."
  },
  {
   "record_id": "PMC6687781::web::000::abstract",
   "paper_title": "Nanostructuring with Structural-Compositional Dual Heterogeneities Enhances Strength-Ductility Synergy in Eutectic High Entropy Alloy.",
   "section": "Abstract",
   "publication_date": "2019-08-08",
   "evidence": "AbstractA lamellar (L12 + B2) AlCoCrFeNi2.1 eutectic high entropy alloy (EHEA) was severely deformed by a novel hybrid-rolling process. During hybrid-rolling, the deformation was carried out in two stages, namely cryo-rolling followed by warm-rolling at 600 °C. The strain (ε) imparted in each of these steps was identical ~1.2, resulting in a total strain of ε~2.4 (corresponding to 90% reduction in thickness). The novel processing strategy resulted in an extremely heterogeneous microstructure consisting of retained lamellar and transformed nanocrystalline regions. Each of these regions consisted of different phases having different crystal structures and chemical compositions. The novel structure-composition dual heterogeneous microstructure originated from the stored energy of the cryo-rolling which accelerated transformations during subsequent low temperature warm-rolling. The dual heterogeneous microstructure yielded an unprecedented combination of strength (~2000 MPa) and ductility (~8%). The present study for the first time demonstrated that dual structure-composition heterogeneities can be a novel microstructural design strategy for achieving outstanding strength-ductility combination in multiphase high entropy alloys.Subject terms: Materials science, Metals and alloys"
  },
  {
   "record_id": "PMC9365806::web::000::abstract",
   "paper_title": "Phase-selective recrystallization makes eutectic high-entropy alloys ultra-ductile.",
   "section": "Abstract",
   "publication_date": "2022-08-10",
   "evidence": "Excellent ductility is crucial not only for shaping but also for strengthening metals and alloys. The ever most widely used eutectic alloys are suffering from the limited ductility and losing competitiveness among advanced structural materials. Here we report a distinctive concept of phase-selective recrystallization to overcome this challenge for eutectic alloys by triggering the strain hardening capacity of the duplex phases completely. We manipulate the strain partitioning behavior of the two phases in a eutectic high-entropy alloy (EHEA) to obtain the phase-selectively recrystallized microstructure with a fully recrystallized soft phase embedded in the skeleton of a hard phase. The resulting microstructure fully releases the strain hardening capacity in EHEA by eliminating the weak boundaries. Our phase-selectively recrystallized EHEA achieves a high ductility of ∼35% uniform elongation with true stress of ∼2 GPa. This concept is universal for various duplex alloys with soft and hard phases and opens new frontiers for traditional eutectic alloys as high-strength metallic materials. The ever most widely used eutectic alloys often suffer from limited ductility. Here the authors propose a distinctive concept of phase-selective recrystallization to significantly improve their ductility and strength and pave the way for new applications of the widespread eutectic alloys."
  },
  {
   "record_id": "PMC10743261::web::002::1_introduction",
   "paper_title": "Phase-Specific Damage Tolerance of a Eutectic High Entropy Alloy.",
   "section": "1. Introduction",
   "publication_date": "2023-11-30",
   "evidence": "Evaluating the response of these novel alloys to complex loading states and understanding their intrinsic fracture mechanisms will allow for the design of damage-tolerant microstructures for further pushing the envelope of applications. Fracture toughness measurements are primarily geared towards understanding two different responses of materials: (i) intrinsic mechanisms, which pertain to the initiation of cracks, and (ii) extrinsic mechanisms, which are related to the propagation of cracks. The latter involves various mechanisms such as crack deflection, trapping, and bridging that contribute to impeding crack growth until the point of crack arrest []. All prior studies on fracture behavior in eutectic HEAs are focused on macroscopic scale deformation and post mortem analysis, which provide limited insights into intrinsic versus extrinsic mechanisms [,,,,]. Focused ion beam (FIB) milling and micro-mechanical testing have proven to be valuable tools in investigating mechanical behavior and intrinsic mechanisms of fracture [,,,,]. Here, we report on the intrinsic fracture behavior and damage tolerance of the L12 and B2 phases in AlCoCrFeNi2.1 EHEA through the utilization of microcantilever beams with notches milled in each of the phases for the in-depth understanding of failure initiation in these alloys and facilitate the design of microstructures that lead to a superior strength–ductility combination."
  },
  {
   "record_id": "PMC6687781::web::019::impact_statement",
   "paper_title": "Nanostructuring with Structural-Compositional Dual Heterogeneities Enhances Strength-Ductility Synergy in Eutectic High Entropy Alloy.",
   "section": "Impact statement",
   "publication_date": "2019-08-08",
   "evidence": "A novel hybrid processing strategy achieves a unique structural-compositional dual heterogeneous microstructure in AlCoCrFeNi2.1 eutectic high entropy alloy resulting in unprecedented strength (>2000 MPa) and ductility (~8%) combination."
  },
  {
   "record_id": "PMC5818523::web::014::discussion",
   "paper_title": "Simultaneous Strength-Ductility Enhancement of a Nano-Lamellar AlCoCrFeNi<sub>2.1</sub> Eutectic High Entropy Alloy by Cryo-Rolling and Annealing.",
   "section": "Discussion",
   "publication_date": "2018-02-19",
   "evidence": "It is rather interesting to note that certain intermetallic phases such as Fe3Al also show simultaneous increase in strength and ductility in recovered or partially recrystallized conditions (having a few recrystallized grains),. While the mechanisms responsible for this rather interesting behavior of Fe3Al have not been investigated in-depth, the simultaneous increase in strength and ductility of the cryo-rolled and annealed material with hierarchical microstructure composed of ultrafine recrystallized, recovered and partially recrystallized phases is evidently in excellent agreement,. In summary, the effect of thermo-mechanical processing by cryo-rolling and annealing on microstructure and properties of nano-lamellar (L12 + B2) AlCoCrFeNi2.1 EHEA was investigated. The cryo-rolled and annealed EHEA developed a novel hierarchical microstructure after annealing. The synergistic effect exerted by the hierarchical microstructure resulted in outstanding increase in strength without loss of ductility when compared to the as-cast as well as cold-rolled and annealed materials. The present work demonstrates the potential of cryo-rolling for developing EHEAs with outstanding strength-ductility balance."
  }
 ]
}
```

Output:

```json
{
 "hypothesis": "Introducing a small amount of high‐temperature stabilizing rare earth elements (specifically Y and Hf) into the AlCoCrFeNi2.1 eutectic high‐entropy alloy will enhance its thermal stability, corrosion resistance, and mechanical performance (strength and ductility) under extreme temperature fluctuations, long‐term loading, room‐temperature creep, and corrosive environments.",
 "material_initial_state": "AlCoCrFeNi2.1 in a uniform, fine lamellar dual-phase (FCC/B2 or L12/B2) structure that shows lower than industrial requirements for strength and plasticity.",
 "intervention": "Co‐doping with small additions of Yttrium (Y) and Hafnium (Hf) into the alloy (as part of the alloy composition or as a surface modification) without altering the overall lamellar morphology.",
 "conditions": "Performance is targeted for fastener components operating under cyclic extreme temperature variations (up to ~700°C and rapid fluctuations), long-term mechanical loading that may induce creep at room temperature, and exposure to corrosive media (e.g., chloride-containing environments or molten salts).",
 "structural_mediator": "Retention of the fine lamellar architecture with phase boundaries that become slightly enriched with Y and Hf, reinforcing both the FCC/L12 and B2 phases and increasing their interfacial stability.",
 "mechanism": "The Y and Hf additions are expected to segregate to grain and phase boundaries, thereby inhibiting grain coarsening (improving thermal stability), retarding the nucleation and propagation of microcracks (enhancing ductility and damage tolerance), and promoting the formation of a more adherent, protective oxide layer under high temperature and corrosive conditions—thereby reducing oxide scale spallation and mitigating corrosion-induced degradation.",
 "predicted_outcome": "Compared to the baseline alloy, the Y/Hf-doped material will display higher yield and ultimate strength along with improved ductility and creep resistance at ambient and elevated temperatures, as well as improved corrosion resistance under severe conditions.",
 "baseline": "The original AlCoCrFeNi2.1 eutectic alloy in its fine lamellar state, which, while demonstrating an attractive composite microstructure, suffers from insufficient mechanical performance and stability under extreme operating environments.",
 "boundary": "The intervention is expected to be effective within operating temperatures up to about 700°C, under long-term static and cyclic mechanical load, in room-temperature creep conditions, and in corrosive environments similar to chloride or molten salt media. Its benefits may diminish if dopant levels are too high or if exposure significantly exceeds these conditions.",
 "uncertainty": "The optimum concentrations of Y and Hf that balance enhanced stability against possible embrittlement, and the long-term performance under cyclic thermo-mechanical fatigue remain to be precisely determined.",
 "supporting_evidence_ids": [
  "PMC10488378::web::000::abstract",
  "PMC10488378::web::015::4_conclusions"
 ],
 "conflicting_evidence_ids": [],
 "falsification_experiment": {
  "design": "Prepare two batches of AlCoCrFeNi2.1 alloys – one as the baseline and one doped with optimized small amounts of Y and Hf. Fabricate specimens with identical fine lamellar microstructures using the same casting and thermo-mechanical processing routes. Subject both sets of samples to accelerated aging and thermal cycling (simulating extreme temperature fluctuations), long-term mechanical loading (including creep tests at room temperature), and corrosive attack in chloride-containing or molten salt environments.",
  "measurements": [
   "Mechanical properties (yield strength, ultimate tensile/compressive strength, ductility, and creep rate) at room and elevated temperatures.",
   "Microstructural stability (grain size, phase boundary integrity) post thermal cycling and long-term load.",
   "Corrosion metrics (oxide scale adhesion, spallation area, weight loss or corrosion current density)."
  ],
  "falsification_rule": "If the Y/Hf-doped alloy does not show a statistically significant (e.g., >15%) improvement in the key performance metrics—mechanical strength, ductility, creep resistance, and corrosion resistance—over the baseline alloy under simulated service conditions, or if the doped alloy exhibits adverse effects (such as increased brittleness or early failure), then the hypothesis is falsified."
 },
 "citation_validation": {
  "status": "valid",
  "removed_unknown_ids": []
 }
}
```

## 6. Reconstruction judges (GPT-5.6 primary, DeepSeek-V4-Pro cross-judge)

Prompt (both judges):

```text
You evaluate a generated materials hypothesis against a hidden paper target.
Do not reward wording overlap. Score scientific agreement and evidence discipline. A different but
well-supported hypothesis may be plausible without being an exact reconstruction.

Return JSON:
{
  "scores": {
    "problem_alignment": 0,
    "intervention_reconstruction": 0,
    "condition_agreement": 0,
    "mechanism_agreement": 0,
    "outcome_agreement": 0,
    "baseline_quality": 0,
    "boundary_quality": 0,
    "experiment_discriminability": 0,
    "evidence_validity": 0,
    "novelty": 0
  },
  "classification": "exact_reconstruction|partial_reconstruction|plausible_alternative|unsupported",
  "fatal_errors": [],
  "explanation": ""
}.
Every score is an integer from 0 to 4.
```

Input (evidence IDs replaced by neutral labels; only the judge sees the answer key):

```json
{
 "query": "For an AlCoCrFeNi2.1 eutectic high-entropy alloy in its uniform, fine lamellar state, whose strength and plasticity remain below industrial application requirements, what single intervention could improve performance for fasteners exposed to extreme temperature fluctuations, long-term mechanical loading, room-temperature creep, and corrosive conditions? State the proposed intervention, mechanism, predicted outcome relative to the starting alloy, applicable operating and test boundaries, supporting prior evidence, and a controlled experiment with explicit falsification criteria.",
 "hidden_target": {
  "material_initial_state": "As-cast AlCoCrFeNi2.1 eutectic high-entropy alloy (x = 0), produced from high-purity elements, with an approximately 70% FCC-dominant FCC + ordered B2 dual-phase lamellar microstructure.",
  "intervention": "Zr was alloyed into AlCoCrFeNi2.1 at nominal x = 0.01, 0.05, and 0.1 (with x = 0 as the control), and the as-cast alloys were examined for phase/microstructure evolution, hardness, room-temperature compression, nanoindentation creep, and electrochemical corrosion.",
  "conditions": "Button ingots were made under Ar by cold-crucible/vacuum melting and remelted at least five times. Microhardness used a 0.981 N load for 15 s; room-temperature compression used 3 mm × 6 mm cylinders at 1 × 10^-3 s^-1 to strain 0.3. Nanoindentation creep used a 10 mN peak load, 100 s hold, and loading rates of 0.1, 1, and 5 mN/s. Corrosion testing was conducted after 30 min immersion in 3.5 wt% NaCl using polarization from -0.8 to 1.5 V at 1 mV/s and EIS from 10^-2 to 10^4 Hz.",
  "structural_mediator": "Zr initially enters the FCC/B2 matrix and causes lattice distortion; at x >= 0.05, Ni- and Zr-rich Ni7Zr2 precipitates emerge at phase boundaries and bridge the FCC and B2 regions. Their morphology evolves from dispersed particles at low Zr to a discontinuous network at x = 0.05 and a coarse continuous network at x = 0.1, while the B2 fraction decreases. TEM of x = 0.1 also showed L12 precipitates in the FCC phase and nanoprecipitates in B2.",
  "mechanism": "Moderate Zr provides solid-solution strengthening through lattice distortion and dispersion/precipitation strengthening through fine, coherent or semi-coherent Ni7Zr2-related precipitates, impeding dislocations and grain-boundary sliding. Excess Zr coarsens and connects the Zr-rich phase, promotes Ni depletion from B2, reduces the B2 fraction, increases segregation and embrittlement, and therefore diminishes mechanical strengthening. For corrosion, the more continuous Zr-rich structure at x = 0.1 favors a stable, protective passive layer, plausibly including ZrO2, that blocks Cl- ingress; uneven intermediate precipitates can instead promote microgalvanic attack.",
  "predicted_outcome": "Relative to Zr-free AlCoCrFeNi2.1, moderate Zr addition—especially x = 0.05—should reduce creep deformation and increase hardness, yield strength, and compressive strength, whereas excessive Zr (x = 0.1) should lower room-temperature mechanical properties from the x = 0.05 optimum. In contrast, x = 0.1 should provide the best corrosion resistance through a more stable passive film.",
  "baseline": "The x = 0 as-cast AlCoCrFeNi2.1 alloy had an FCC + B2 lamellar structure, yield strength 705.1 ± 31.53 MPa, compressive strength 1182.7 ± 24.68 MPa, corrosion current density 0.09993 μA/cm2, pitting potential 320.27 mV, corrosion rate 0.0011621 mm/year, and charge-transfer resistance 2600 Ω·cm2.",
  "boundary": "The reported trends apply to the as-cast ZrxAlCoCrFeNi2.1 compositions x = 0, 0.01, 0.05, and 0.1 under the stated room-temperature mechanical/nanoindentation conditions and in 3.5 wt% NaCl. The mechanical optimum occurred at x = 0.05; increasing Zr to x = 0.1 reversed part of the strengthening benefit, while corrosion resistance was best at x = 0.1. Dislocation-dominated creep was most persistent at x = 0.05, whereas loading-rate changes altered the inferred mechanisms in the other alloys.",
  "discriminating_measurement": "XRD, SEM/EDS, and TEM/SAED identified phase and morphology changes; microhardness and room-temperature compression distinguished the mechanical optimum; nanoindentation creep displacement and the fitted stress exponent n distinguished creep resistance and mechanism; potentiodynamic polarization (Icorr, Ecorr, and Epit), EIS/Rct, and post-corrosion SEM/EDS distinguished corrosion resistance and passive-film stability.",
  "actual_result": "At x = 0.05, hardness peaked at 368.1 HV (about 18.7% above the Zr-free alloy), yield strength at 1048.7 ± 23.84 MPa (about 48.7% higher), and compressive strength at 1801.1 ± 28.70 MPa (about 52.2% higher). At x = 0.1 these fell to 865.9 ± 14.85 MPa and 1382.4 ± 13.56 MPa, respectively. At a 5 mN/s indentation loading rate, creep depth changed from 22.16 nm at x = 0 to 13.47 nm at x = 0.05, then rose to 18.36 nm at x = 0.1. The creep exponent exceeded 3 at 0.1 mN/s, and x = 0.05 retained n > 3 even at 5 mN/s, indicating dislocation creep and robust creep resistance. Corrosion resistance ranked x = 0.1 > x = 0.01 > x = 0.05 > x = 0; x = 0.1 had the lowest Icorr, 0.034197 μA/cm2, the highest Epit, 323.06 mV, a corrosion rate of 0.00039737 mm/year, and the highest Rct, 700,000 Ω·cm2."
 },
 "generated_hypothesis": {
  "hypothesis": "Introducing a small amount of high‐temperature stabilizing rare earth elements (specifically Y and Hf) into the AlCoCrFeNi2.1 eutectic high‐entropy alloy will enhance its thermal stability, corrosion resistance, and mechanical performance (strength and ductility) under extreme temperature fluctuations, long‐term loading, room‐temperature creep, and corrosive environments.",
  "material_initial_state": "AlCoCrFeNi2.1 in a uniform, fine lamellar dual-phase (FCC/B2 or L12/B2) structure that shows lower than industrial requirements for strength and plasticity.",
  "intervention": "Co‐doping with small additions of Yttrium (Y) and Hafnium (Hf) into the alloy (as part of the alloy composition or as a surface modification) without altering the overall lamellar morphology.",
  "conditions": "Performance is targeted for fastener components operating under cyclic extreme temperature variations (up to ~700°C and rapid fluctuations), long-term mechanical loading that may induce creep at room temperature, and exposure to corrosive media (e.g., chloride-containing environments or molten salts).",
  "structural_mediator": "Retention of the fine lamellar architecture with phase boundaries that become slightly enriched with Y and Hf, reinforcing both the FCC/L12 and B2 phases and increasing their interfacial stability.",
  "mechanism": "The Y and Hf additions are expected to segregate to grain and phase boundaries, thereby inhibiting grain coarsening (improving thermal stability), retarding the nucleation and propagation of microcracks (enhancing ductility and damage tolerance), and promoting the formation of a more adherent, protective oxide layer under high temperature and corrosive conditions—thereby reducing oxide scale spallation and mitigating corrosion-induced degradation.",
  "predicted_outcome": "Compared to the baseline alloy, the Y/Hf-doped material will display higher yield and ultimate strength along with improved ductility and creep resistance at ambient and elevated temperatures, as well as improved corrosion resistance under severe conditions.",
  "baseline": "The original AlCoCrFeNi2.1 eutectic alloy in its fine lamellar state, which, while demonstrating an attractive composite microstructure, suffers from insufficient mechanical performance and stability under extreme operating environments.",
  "boundary": "The intervention is expected to be effective within operating temperatures up to about 700°C, under long-term static and cyclic mechanical load, in room-temperature creep conditions, and in corrosive environments similar to chloride or molten salt media. Its benefits may diminish if dopant levels are too high or if exposure significantly exceeds these conditions.",
  "uncertainty": "The optimum concentrations of Y and Hf that balance enhanced stability against possible embrittlement, and the long-term performance under cyclic thermo-mechanical fatigue remain to be precisely determined.",
  "supporting_evidence_ids": [
   "E1",
   "E2"
  ],
  "conflicting_evidence_ids": [],
  "falsification_experiment": {
   "design": "Prepare two batches of AlCoCrFeNi2.1 alloys – one as the baseline and one doped with optimized small amounts of Y and Hf. Fabricate specimens with identical fine lamellar microstructures using the same casting and thermo-mechanical processing routes. Subject both sets of samples to accelerated aging and thermal cycling (simulating extreme temperature fluctuations), long-term mechanical loading (including creep tests at room temperature), and corrosive attack in chloride-containing or molten salt environments.",
   "measurements": [
    "Mechanical properties (yield strength, ultimate tensile/compressive strength, ductility, and creep rate) at room and elevated temperatures.",
    "Microstructural stability (grain size, phase boundary integrity) post thermal cycling and long-term load.",
    "Corrosion metrics (oxide scale adhesion, spallation area, weight loss or corrosion current density)."
   ],
   "falsification_rule": "If the Y/Hf-doped alloy does not show a statistically significant (e.g., >15%) improvement in the key performance metrics—mechanical strength, ductility, creep resistance, and corrosion resistance—over the baseline alloy under simulated service conditions, or if the doped alloy exhibits adverse effects (such as increased brittleness or early failure), then the hypothesis is falsified."
  }
 },
 "cited_evidence": [
  {
   "evidence_id": "E1",
   "paper_id": "PMC10488378",
   "publication_date": "2023-08-22",
   "text": "AbstractBoth crack-free AlCoCrFeNi2.1 eutectic high-entropy alloy (EHEA) and Y and Hf co-doping AlCoCrFeNi2.1 EHEA (YHf-EHEA) coatings were prepared by laser cladding. The solidification microstructure, thermal stability, and hot corrosion performance of the coatings at 900 °C under 75% Na2SO4 + 25% NaCl molten salts were investigated. The experimental results showed that the structure of the as-deposited coatings consisted of FCC and BCC/B2 phases. After heat treatment, an Al-rich L12 phase was precipitated in the FCC phase of all coatings. The grain sizes of the EHEA and YHf-EHEA coatings after heat treatment at 900 °C for 10 h increased by 27.5% and 15.7%, respectively, compared to the as-deposited coatings. Meanwhile, after hot corrosion, the spallation areas of the YHf-EHEA and EHEA coatings accounted for 14.98% and 5.67% of the total surface area, respectively. In this study, the Y and Hf co-doping did not change the microstructure morphology and phase structure of the coatings but did improve the thermal stability and resistance of the hot corrosion oxide scale spallation, providing a certain amount of data and theoretical support for the application of EHEA coatings as high"
  },
  {
   "evidence_id": "E2",
   "paper_id": "PMC10488378",
   "publication_date": "2023-08-22",
   "text": "In this work, AlCoCrFeNi2.1 EHEA and co-doping Y and Hf AlCoCrFeNi2.1 YHf-EHEA coatings were successfully prepared by laser cladding. The solidification microstructure, thermal stability, and hot corrosion of the coatings at 900 °C under 75% Na2SO4 + 25% NaCl molten salts were investigated. 1. The YHf co-doping did not alter the solidification microstructure and phase structure of the EHEA coating. The microstructure morphologies of the top and bottom portions of coatings were composed of cellular and columnar dendrites, respectively. And the phase structure consisted of FCC and BCC/B2. 2. After heat treatment at 900 °C for 10 h, the BCC/B2 structure was relatively stable in all coatings while the nanoscale Al-rich L12 phase was precipitated in the FCC. 3. The grain sizes of the HT-EHEA and HT-YHf coatings after heat treatment at 900 °C for 10 h increased by 27.5% and 15.7%, respectively, compared to the as-deposited coatings. Additionally, the volume fractions of the LAGBs decreased by 13.9% and 8.3% in the HT-EHEA and HT-YHf coatings, respectively. 4. Al2O3 was found to be formed when the surface oxide products of the coatings were hot corroded at 900 °C for 60 h under Na2SO4 + 2"
  }
 ]
}
```

GPT-5.6 output:

```json
{
 "schema_version": "temporal-eval-v3-1.0",
 "run_id": "PMC11643467__problem_constrained__rx_r__s1",
 "judge": "trapi:gpt-5.6-sol_2026-07-09",
 "scores": {
  "problem_alignment": 3,
  "intervention_reconstruction": 0,
  "condition_agreement": 1,
  "mechanism_agreement": 1,
  "outcome_agreement": 1,
  "baseline_quality": 1,
  "boundary_quality": 2,
  "experiment_discriminability": 2,
  "evidence_validity": 1,
  "novelty": 2
 },
 "classification": "plausible_alternative",
 "fatal_errors": [
  "The proposed Y/Hf co-doping does not reconstruct the target intervention of controlled Zr alloying at x = 0.01, 0.05, and 0.1.",
  "The cited evidence concerns laser-clad coatings tested at 900 °C, not as-cast bulk fastener material with a fine eutectic lamellar microstructure under the target room-temperature compression, nanoindentation-creep, and 3.5 wt% NaCl conditions.",
  "Claims of improved strength, ductility, and room-temperature creep resistance are not supported by the cited evidence.",
  "The intervention is insufficiently specified: Y and Hf concentrations are absent, and bulk alloying and surface modification are treated as interchangeable.",
  "The proposed operating limit of approximately 700 °C is not established by the cited 900 °C coating study."
 ],
 "explanation": "The hypothesis addresses the intended combination of mechanical, creep, thermal, and corrosion performance and offers a broadly controlled comparison, so it is a scientifically plausible alternative. However, it misses the target Zr-addition study and its central composition-dependent tradeoff: x = 0.05 gives the mechanical and creep optimum, whereas x = 0.1 gives the best corrosion resistance but reduced mechanical performance. Its mechanism of Y/Hf boundary segregation and oxide-scale adhesion differs from the target lattice-distortion and Ni7Zr2 precipitation mechanism. The evidence supports improved thermal stability and provides some hot-corrosion observations for laser-clad Y/Hf coatings, but it does not validate the claimed bulk strength, ductility, or room-temperature creep improvements. The experiment includes a control and an explicit threshold, yet use of an undefined 'optimized' composition, unspecified replication/statistics, and a bundled requirement that every metric improve by more than 15% limit discriminability.",
 "trapi_instance": "redmond/interactive"
}
```

DeepSeek output:

```json
{
 "run_id": "PMC11643467__problem_constrained__rx_r__s1",
 "judge": "trapi:DeepSeek-V4-Pro_2026-04-23",
 "scores": {
  "problem_alignment": 1,
  "intervention_reconstruction": 0,
  "condition_agreement": 0,
  "mechanism_agreement": 0,
  "outcome_agreement": 0,
  "baseline_quality": 1,
  "boundary_quality": 1,
  "experiment_discriminability": 1,
  "evidence_validity": 1,
  "novelty": 1
 },
 "classification": "unsupported",
 "trapi_instance": "gcr/shared"
}
```

Reconstruction = mean of intervention, conditions, mechanism and outcome: GPT-5.6 0.75, DeepSeek 0.00.

## 7. Quality judges without the answer key

**Research quality (RQ)**, three DeepSeek calls. Prompt:

```text
You are an experienced materials scientist rating research hypotheses on high-temperature high-entropy alloys.

What the AI systems were asked to do: each system saw only the research question, not the paper. It had to propose one hypothesis that answers the question, in a fixed structure:
- Main hypothesis: the proposal in one or two sentences.
- Starting material: the alloy or material and its state before the change (as cast, annealed, coating, ...).
- What is changed or studied: the intervention: a composition change, a process, a heat treatment, a coating, or, for some questions, the study or simulation to be done.
- Conditions: processing, test or simulation conditions (temperature, time, atmosphere, loading, ...).
- Structure through which it acts: the microstructural or structural feature that mediates the effect (phases, precipitates, grain boundaries, defects, ordering, ...).
- Mechanism: why the change should produce the effect.
- Predicted outcome: what should happen to the property, compared with the baseline.
- Compared with (baseline): the reference condition the prediction is compared with.
- Where it should hold (boundary): the range of materials or conditions where the prediction should apply.
- Main uncertainty: what could make the hypothesis wrong.
- Test that would falsify it: an experiment or simulation, and the result that would prove the hypothesis wrong.
A field shown as "—" was left empty by its author. Rate the hypothesis on what is there.

Rate the hypothesis on three separate aspects. They are independent: a hypothesis can be plausible but hard to test, or testable but not useful.

Plausibility (1-5): is it scientifically sound for this material and these conditions?
1 = Physically wrong, or contradicts well-established knowledge
2 = Doubtful: major scientific problems
3 = Possible, but with notable gaps or questionable steps
4 = Sound, with minor issues
5 = Fully sound and convincing

Testability (1-5): could it be clearly tested, and would the proposed test decide it?
1 = Cannot be tested as written, or too vague to test
2 = A test is mentioned, but it would not really decide the question
3 = Testable, but the test is weak, incomplete or impractical
4 = Clear, feasible test with minor gaps
5 = Clear, feasible test with a decisive criterion for proving it wrong

Usefulness (1-5): would it help a researcher working on exactly this question?
1 = Not useful: off-topic, trivial or wrong
2 = Of little use
3 = Moderately useful
4 = Useful: worth testing
5 = Very useful: I would want to see it tested

Length or the number of details does not make a hypothesis better in itself.

Return JSON: {"plausibility_reason": "one sentence", "plausibility": integer 1-5, "testability_reason": "one sentence", "testability": integer 1-5, "usefulness_reason": "one sentence", "usefulness": integer 1-5}. Give each reason before its score.
```

Input:

```json
{
 "research_question": "For an AlCoCrFeNi2.1 eutectic high-entropy alloy in its uniform, fine lamellar state, whose strength and plasticity remain below industrial application requirements, what single intervention could improve performance for fasteners exposed to extreme temperature fluctuations, long-term mechanical loading, room-temperature creep, and corrosive conditions? State the proposed intervention, mechanism, predicted outcome relative to the starting alloy, applicable operating and test boundaries, supporting prior evidence, and a controlled experiment with explicit falsification criteria.",
 "hypothesis": "- **Main hypothesis:** Introducing a small amount of high‐temperature stabilizing rare earth elements (specifically Y and Hf) into the AlCoCrFeNi2.1 eutectic high‐entropy alloy will enhance its thermal stability, corrosion resistance, and mechanical performance (strength and ductility) under extreme temperature fluctuations, long‐term loading, room‐temperature creep, and corrosive environments.\n- **Starting material:** AlCoCrFeNi2.1 in a uniform, fine lamellar dual-phase (FCC/B2 or L12/B2) structure that shows lower than industrial requirements for strength and plasticity.\n- **What is changed or studied:** Co‐doping with small additions of Yttrium (Y) and Hafnium (Hf) into the alloy (as part of the alloy composition or as a surface modification) without altering the overall lamellar morphology.\n- **Conditions:** Performance is targeted for fastener components operating under cyclic extreme temperature variations (up to ~700°C and rapid fluctuations), long-term mechanical loading that may induce creep at room temperature, and exposure to corrosive media (e.g., chloride-containing environments or molten salts).\n- **Structure through which it acts:** Retention of the fine lamellar architecture with phase boundaries that become slightly enriched with Y and Hf, reinforcing both the FCC/L12 and B2 phases and increasing their interfacial stability.\n- **Mechanism:** The Y and Hf additions are expected to segregate to grain and phase boundaries, thereby inhibiting grain coarsening (improving thermal stability), retarding the nucleation and propagation of microcracks (enhancing ductility and damage tolerance), and promoting the formation of a more adherent, protective oxide layer under high temperature and corrosive conditions—thereby reducing oxide scale spallation and mitigating corrosion-induced degradation.\n- **Predicted outcome:** Compared to the baseline alloy, the Y/Hf-doped material will display higher yield and ultimate strength along with improved ductility and creep resistance at ambient and elevated temperatures, as well as improved corrosion resistance under severe conditions.\n- **Compared with (baseline):** The original AlCoCrFeNi2.1 eutectic alloy in its fine lamellar state, which, while demonstrating an attractive composite microstructure, suffers from insufficient mechanical performance and stability under extreme operating environments.\n- **Where it should hold (boundary):** The intervention is expected to be effective within operating temperatures up to about 700°C, under long-term static and cyclic mechanical load, in room-temperature creep conditions, and in corrosive environments similar to chloride or molten salt media. Its benefits may diminish if dopant levels are too high or if exposure significantly exceeds these conditions.\n- **Main uncertainty:** The optimum concentrations of Y and Hf that balance enhanced stability against possible embrittlement, and the long-term performance under cyclic thermo-mechanical fatigue remain to be precisely determined.\n- **Test that would falsify it:**\n  - *Design:* Prepare two batches of AlCoCrFeNi2.1 alloys – one as the baseline and one doped with optimized small amounts of Y and Hf. Fabricate specimens with identical fine lamellar microstructures using the same casting and thermo-mechanical processing routes. Subject both sets of samples to accelerated aging and thermal cycling (simulating extreme temperature fluctuations), long-term mechanical loading (including creep tests at room temperature), and corrosive attack in chloride-containing or molten salt environments.\n  - *Measurements:* Mechanical properties (yield strength, ultimate tensile/compressive strength, ductility, and creep rate) at room and elevated temperatures.; Microstructural stability (grain size, phase boundary integrity) post thermal cycling and long-term load.; Corrosion metrics (oxide scale adhesion, spallation area, weight loss or corrosion current density).\n  - *Falsified if:* If the Y/Hf-doped alloy does not show a statistically significant (e.g., &gt;15%) improvement in the key performance metrics—mechanical strength, ductility, creep resistance, and corrosion resistance—over the baseline alloy under simulated service conditions, or if the doped alloy exhibits adverse effects (such as increased brittleness or early failure), then the hypothesis is falsified."
}
```

Outputs:

```json
[
 {
  "item": "PMC11643467__problem_constrained__rx_r__s1",
  "judge": "deepseek",
  "scores": {
   "plausibility": 3,
   "testability": 4,
   "usefulness": 5
  },
  "reasons": {
   "plausibility": "The hypothesis is scientifically sound, as rare-earth additions are well-known to segregate to grain boundaries, improve oxidation resistance, and refine microstructure in high-temperature alloys, though the specific claim of simultaneously improving strength, ductility, and room-temperature creep resistance in this complex eutectic HEA without disrupting the lamellar structure is ambitious and carries notable risk of embrittlement.",
   "testability": "The proposed test is clear and comprehensive, with explicit falsification criteria (>15% improvement) and relevant measurements, but the requirement for 'optimized' dopant levels without specifying them introduces ambiguity, and the test does not isolate the mechanism of interfacial stability.",
   "usefulness": "The hypothesis directly addresses the industrial problem with a concrete, well-reasoned intervention and a detailed experimental plan, making it a valuable starting point for a researcher, despite the uncertainty around optimal composition."
  },
  "rq": 3.0,
  "attempts": 1
 },
 {
  "item": "PMC11643467__problem_constrained__rx_r__s1",
  "judge": "deepseek",
  "scores": {
   "plausibility": 4,
   "testability": 4,
   "usefulness": 5
  },
  "reasons": {
   "plausibility": "The hypothesis is scientifically sound, as Y and Hf are well-known for grain boundary segregation, thermal stabilization, and oxidation resistance in Ni/Co-based superalloys, and the proposed mechanisms are consistent with established metallurgical principles for this alloy system.",
   "testability": "The proposed test is clear and feasible, with explicit falsification criteria (>15% improvement), but it lacks specific dopant concentrations and processing details, which makes exact replication slightly ambiguous.",
   "usefulness": "The hypothesis directly addresses the research question with a specific, non-obvious intervention and a well-defined testing protocol, making it highly valuable for guiding experimental work on this alloy for fastener applications."
  },
  "rq": 3.3333,
  "attempts": 1
 },
 {
  "item": "PMC11643467__problem_constrained__rx_r__s1",
  "judge": "deepseek",
  "scores": {
   "plausibility": 4,
   "testability": 4,
   "usefulness": 5
  },
  "reasons": {
   "plausibility": "The hypothesis is scientifically sound, as Y and Hf are well-known for grain boundary segregation, oxide scale adhesion improvement, and thermal stability in high-temperature alloys, and the proposed mechanisms align with established metallurgical principles for this alloy system.",
   "testability": "The proposed test is clear and feasible, with explicit falsification criteria (>15% improvement) and relevant measurements, though the 'optimized' dopant levels are not specified, which adds a minor practical gap.",
   "usefulness": "The hypothesis directly addresses the research question with a specific, actionable intervention and a well-defined testing protocol, making it highly useful for guiding experimental work on this alloy for fastener applications."
  },
  "rq": 3.3333,
  "attempts": 1
 }
]
```

RQ = mean of the three scales minus 1, averaged over the calls: 3.22.

**Pairwise quality** against the base arm (the old web corpus), DeepSeek, both orders. Prompt:

```text
You are an experienced materials scientist reviewing two research hypotheses written, before the work is done, for the same research question on high-temperature high-entropy alloys. Decide which one is the better research proposal to pursue. Consider: (1) does it address the limitation the question states, within its constraints; (2) is the mechanism physically sound for this material and regime; (3) is it specific and testable: a clear intervention, conditions, a measurable predicted outcome against a baseline, and a decisive experiment; (4) is it well grounded: claims consistent with established knowledge and with any cited evidence, and no invented precise values presented as fact; (5) is it a substantive, non-trivial contribution. Do not prefer a hypothesis for being longer or for citing more evidence as such. Return JSON {"winner": "A" | "B" | "tie", "confidence": number from 0 to 1, "reason": "one or two sentences"}.
```

Input, base shown first:

```json
{
 "research_question": "For an AlCoCrFeNi2.1 eutectic high-entropy alloy in its uniform, fine lamellar state, whose strength and plasticity remain below industrial application requirements, what single intervention could improve performance for fasteners exposed to extreme temperature fluctuations, long-term mechanical loading, room-temperature creep, and corrosive conditions? State the proposed intervention, mechanism, predicted outcome relative to the starting alloy, applicable operating and test boundaries, supporting prior evidence, and a controlled experiment with explicit falsification criteria.",
 "candidate_A": {
  "hypothesis": {
   "hypothesis": "A severe thermomechanical processing intervention—specifically, heavy cryo‐rolling followed by an optimized annealing treatment—can refine and decompose the uniform lamellar microstructure of the as‐cast AlCoCrFeNi2.1 EHEA to generate ultrafine recrystallized grains and coherent nanoprecipitates, thereby simultaneously increasing strength, ductility, creep resistance, and corrosion performance for fastener applications under extreme service conditions.",
   "material_initial_state": "As‐cast, uniform, fine lamellar AlCoCrFeNi2.1 eutectic high‐entropy alloy with coupled fcc (L12) and B2 phases.",
   "intervention": "Implement a single processing step consisting of severe cryo‐rolling (e.g., ~90% reduction) followed by an optimized short-term annealing (~800°C for an appropriate time) to induce targeted microstructural refinement and controlled phase decomposition.",
   "conditions": "Designed for fasteners exposed to wide temperature fluctuations (up to ~700°C), long-term mechanical loads with room-temperature creep challenges, and corrosive environments (e.g., marine or chloride-containing conditions).",
   "structural_mediator": "A heterogeneously refined lamellar structure featuring ultrafine recrystallized domains and nanoscale, coherent precipitates at phase boundaries that enhance interphase interaction and dislocation blockage.",
   "mechanism": "The severe cryo-rolling introduces high dislocation densities while the subsequent annealing triggers controlled phase decomposition. This process refines the lamellae into thinner, more heterogeneous domains where geometrically necessary dislocations accumulate at new phase boundaries, increasing back-stress and strengthening. The formation of coherent nanoscale precipitates additionally contributes to precipitation strengthening, improves creep resistance by impeding dislocation movement, and provides more stable interfaces that also enhance corrosion resistance.",
   "predicted_outcome": "Relative to the starting, as-cast alloy, the treated material is expected to exhibit a 20–40% increase in yield and ultimate tensile strength, a multiplication (roughly 2×) of ductility (fracture elongation), significantly reduced creep rates at room temperature, and improved resistance against corrosive attack.",
   "baseline": "The performance metrics of the uniform as-cast fine lamellar AlCoCrFeNi2.1 alloy, which shows mechanical properties below industrial requirements for fasteners.",
   "boundary": "The improvements are anticipated under conditions typical for fastener applications: moderate to high temperatures (operational stability up to ~700°C), quasi-static and dynamic loading environments, room-temperature creep testing, and exposure to corrosive media (e.g., artificial seawater).",
   "uncertainty": "The precise quantitative gains in strength, ductility, and corrosion resistance depending on the exact processing parameters and scale-up effects remain to be fully determined. Optimizing the processing window will be critical to balance gains across the multiple performance aspects.",
   "supporting_evidence_ids": [
    "E3",
    "E2",
    "E1"
   ],
   "conflicting_evidence_ids": [],
   "falsification_experiment": {
    "design": "Prepare two batches of AlCoCrFeNi2.1 alloy specimens: one batch processed by the proposed cryo-rolling plus annealing route and one control batch in the as-cast state. Characterize their microstructures using TEM and EBSD to verify refinement, recrystallization, and nanoprecipitate formation. Conduct standardized tensile tests, long-term room-temperature creep tests, and corrosion tests in simulated marine (chloride-containing) conditions. The experiment should compare strength, ductility, creep rate, and corrosion performance between the two batches.",
    "measurements": [
     "Yield strength and ultimate tensile strength (via tensile tests)",
     "Fracture elongation/dductility",
     "Creep strain rate at room temperature",
     "Corrosion rate and passivation behavior (electrochemical tests)",
     "Microstructural analysis (grain size, precipitate distribution via EBSD/TEM)"
    ],
    "falsification_rule": "If the processed specimens fail to exhibit statistically significant improvements (for example, less than a 20% increase in yield/ultimate strength and less than a doubling of ductility, along with no measurable gains in creep and corrosion resistance) compared to the as-cast control, then the hypothesis that the proposed processing intervention enhances performance under the defined service conditions is falsified."
   }
  },
  "cited_evidence": [
   {
    "evidence_id": "E1",
    "paper_id": "PMC11433366",
    "publication_date": "2024-09-12",
    "text": "These results showed that the yield strength (1437 ± 26 MPa), tensile strength (1562 ± 33 MPa), and elongation (14 ± 1%) of the AlCoCrFeNi2.1 alloy after annealing at low temperature were significantly improved compared with the as-cast alloy. Eutectic high-entropy alloys exhibit an excellent balance of toughness and strength at room temperature. However, there is still an immediate requirement to design structural components with more strength and ductility due to the increasing technical requirements and harsher operating environments in industrial applications. The demand for stronger and more ductile structural elements has increased as airplane components have become more demanding and technical standards have advanced. Therefore, it is of significance to develop a new eutectic high-entropy alloy with superior properties based on AlCoCrFeNi2.1."
   },
   {
    "evidence_id": "E2",
    "paper_id": "PMC4145285",
    "publication_date": "2014-08-27",
    "text": "As such, our alloy design strategy resulted in the discovery of an EHEA with a fine lamellar fcc/B2 structure and balanced high fracture strength and high ductility. This novel strategy is promising to solve the problems inhibiting the engineering application of HEAs as high-temperature materials, including the inferior castability and compositional segregation, and the conflict between high fracture strength and high ductility. In addition, this novel strategy also brought breakthrough to NiAl-based alloys in significantly enhancing the ductility at room temperature while simultaneously achieving the high strength. The EHEA concept, combining the advantages of both HEAs and eutectic alloys, and at the same time eliminating the disadvantages of these two types of alloys, leads to a promising new class of high-temperature alloys. Using this new alloy design strategy, an industrial scale HEA with uniform organizations and compositions can be prepared by the conventional casting method in a low cost way, allowing for large-scale industrial applications. Further exploration of new EHEAs will be based on previous established physical metallurgy principles to design HEAs, utilizing physi"
   },
   {
    "evidence_id": "E3",
    "paper_id": "PMC6353877",
    "publication_date": "2019-01-30",
    "text": "In this work, we successfully achieve a superior strength–ductility combination in AlCoCrFeNi2.1 EHEAs by introducing two concurrent effects, the two-hierarchical constraint effect and the self-generated microcrack-arresting mechanisms. The underlying origin lying behind the observed mechanical response is the inherited lamellar geometry from the as-cast EHEA. It is known that grain refinement to the nano/ultrafine-grained regime can render material stronger, but this process is usually accompanied by a dramatic loss of ductility. However, with a composite lamellar architecture, the ultrafine-grained duplex microstructure in this study achieves an improved strength–ductility synergy. Phase decomposition is applied to optimize properties instead of just being a phase-instability phenomenon frequently observed in single-phase HEAs, which may encourage further research in this area. In addition, the AlCoCrFeNi2.1 EHEA could be simply processed to achieve properties that are an improvement over traditional TRIP (transformation-induced plasticity) and TWIP (twinning-induced plasticity) steels (Fig. 5). We believe that the simplicity in the present processing procedure is extremely attra"
   }
  ]
 },
 "candidate_B": {
  "hypothesis": {
   "hypothesis": "Introducing a small amount of high‐temperature stabilizing rare earth elements (specifically Y and Hf) into the AlCoCrFeNi2.1 eutectic high‐entropy alloy will enhance its thermal stability, corrosion resistance, and mechanical performance (strength and ductility) under extreme temperature fluctuations, long‐term loading, room‐temperature creep, and corrosive environments.",
   "material_initial_state": "AlCoCrFeNi2.1 in a uniform, fine lamellar dual-phase (FCC/B2 or L12/B2) structure that shows lower than industrial requirements for strength and plasticity.",
   "intervention": "Co‐doping with small additions of Yttrium (Y) and Hafnium (Hf) into the alloy (as part of the alloy composition or as a surface modification) without altering the overall lamellar morphology.",
   "conditions": "Performance is targeted for fastener components operating under cyclic extreme temperature variations (up to ~700°C and rapid fluctuations), long-term mechanical loading that may induce creep at room temperature, and exposure to corrosive media (e.g., chloride-containing environments or molten salts).",
   "structural_mediator": "Retention of the fine lamellar architecture with phase boundaries that become slightly enriched with Y and Hf, reinforcing both the FCC/L12 and B2 phases and increasing their interfacial stability.",
   "mechanism": "The Y and Hf additions are expected to segregate to grain and phase boundaries, thereby inhibiting grain coarsening (improving thermal stability), retarding the nucleation and propagation of microcracks (enhancing ductility and damage tolerance), and promoting the formation of a more adherent, protective oxide layer under high temperature and corrosive conditions—thereby reducing oxide scale spallation and mitigating corrosion-induced degradation.",
   "predicted_outcome": "Compared to the baseline alloy, the Y/Hf-doped material will display higher yield and ultimate strength along with improved ductility and creep resistance at ambient and elevated temperatures, as well as improved corrosion resistance under severe conditions.",
   "baseline": "The original AlCoCrFeNi2.1 eutectic alloy in its fine lamellar state, which, while demonstrating an attractive composite microstructure, suffers from insufficient mechanical performance and stability under extreme operating environments.",
   "boundary": "The intervention is expected to be effective within operating temperatures up to about 700°C, under long-term static and cyclic mechanical load, in room-temperature creep conditions, and in corrosive environments similar to chloride or molten salt media. Its benefits may diminish if dopant levels are too high or if exposure significantly exceeds these conditions.",
   "uncertainty": "The optimum concentrations of Y and Hf that balance enhanced stability against possible embrittlement, and the long-term performance under cyclic thermo-mechanical fatigue remain to be precisely determined.",
   "supporting_evidence_ids": [
    "E1",
    "E2"
   ],
   "conflicting_evidence_ids": [],
   "falsification_experiment": {
    "design": "Prepare two batches of AlCoCrFeNi2.1 alloys – one as the baseline and one doped with optimized small amounts of Y and Hf. Fabricate specimens with identical fine lamellar microstructures using the same casting and thermo-mechanical processing routes. Subject both sets of samples to accelerated aging and thermal cycling (simulating extreme temperature fluctuations), long-term mechanical loading (including creep tests at room temperature), and corrosive attack in chloride-containing or molten salt environments.",
    "measurements": [
     "Mechanical properties (yield strength, ultimate tensile/compressive strength, ductility, and creep rate) at room and elevated temperatures.",
     "Microstructural stability (grain size, phase boundary integrity) post thermal cycling and long-term load.",
     "Corrosion metrics (oxide scale adhesion, spallation area, weight loss or corrosion current density)."
    ],
    "falsification_rule": "If the Y/Hf-doped alloy does not show a statistically significant (e.g., >15%) improvement in the key performance metrics—mechanical strength, ductility, creep resistance, and corrosion resistance—over the baseline alloy under simulated service conditions, or if the doped alloy exhibits adverse effects (such as increased brittleness or early failure), then the hypothesis is falsified."
   }
  },
  "cited_evidence": [
   {
    "evidence_id": "E1",
    "paper_id": "PMC10488378",
    "publication_date": "2023-08-22",
    "text": "AbstractBoth crack-free AlCoCrFeNi2.1 eutectic high-entropy alloy (EHEA) and Y and Hf co-doping AlCoCrFeNi2.1 EHEA (YHf-EHEA) coatings were prepared by laser cladding. The solidification microstructure, thermal stability, and hot corrosion performance of the coatings at 900 °C under 75% Na2SO4 + 25% NaCl molten salts were investigated. The experimental results showed that the structure of the as-deposited coatings consisted of FCC and BCC/B2 phases. After heat treatment, an Al-rich L12 phase was precipitated in the FCC phase of all coatings. The grain sizes of the EHEA and YHf-EHEA coatings after heat treatment at 900 °C for 10 h increased by 27.5% and 15.7%, respectively, compared to the as-deposited coatings. Meanwhile, after hot corrosion, the spallation areas of the YHf-EHEA and EHEA coatings accounted for 14.98% and 5.67% of the total surface area, respectively. In this study, the Y and Hf co-doping did not change the microstructure morphology and phase structure of the coatings but did improve the thermal stability and resistance of the hot corrosion oxide scale spallation, providing a certain amount of data and theoretical support for the application of EHEA coatings as high"
   },
   {
    "evidence_id": "E2",
    "paper_id": "PMC10488378",
    "publication_date": "2023-08-22",
    "text": "In this work, AlCoCrFeNi2.1 EHEA and co-doping Y and Hf AlCoCrFeNi2.1 YHf-EHEA coatings were successfully prepared by laser cladding. The solidification microstructure, thermal stability, and hot corrosion of the coatings at 900 °C under 75% Na2SO4 + 25% NaCl molten salts were investigated. 1. The YHf co-doping did not alter the solidification microstructure and phase structure of the EHEA coating. The microstructure morphologies of the top and bottom portions of coatings were composed of cellular and columnar dendrites, respectively. And the phase structure consisted of FCC and BCC/B2. 2. After heat treatment at 900 °C for 10 h, the BCC/B2 structure was relatively stable in all coatings while the nanoscale Al-rich L12 phase was precipitated in the FCC. 3. The grain sizes of the HT-EHEA and HT-YHf coatings after heat treatment at 900 °C for 10 h increased by 27.5% and 15.7%, respectively, compared to the as-deposited coatings. Additionally, the volume fractions of the LAGBs decreased by 13.9% and 8.3% in the HT-EHEA and HT-YHf coatings, respectively. 4. Al2O3 was found to be formed when the surface oxide products of the coatings were hot corroded at 900 °C for 60 h under Na2SO4 + 2"
   }
  ]
 }
}
```

Outputs:

```json
{
 "baseline_first": {
  "judge": "deepseek",
  "order": "baseline_first",
  "winner": "A",
  "new_won": false,
  "baseline_won": true,
  "reason": "Hypothesis A proposes a specific, testable thermomechanical processing route with a clear microstructural mechanism (cryo-rolling + annealing to refine grains and form precipitates) that directly addresses the strength-ductility-creep-corrosion limitations, and its falsification experiment is well-defined with quantitative criteria. Hypothesis B relies on doping with Y and Hf, but the cited evidence shows only modest thermal stability improvement and worse hot corrosion spallation for the doped coating, undermining its mechanism for corrosion resistance, and the proposal lacks specificity on h"
 },
 "new_first": {
  "judge": "deepseek",
  "order": "new_first",
  "winner": "A",
  "new_won": true,
  "baseline_won": false,
  "reason": "Hypothesis A directly addresses the stated limitations (strength, plasticity, thermal stability, creep, corrosion) with a physically sound mechanism (boundary segregation and oxide scale improvement) supported by directly relevant evidence (E1, E2) on the same alloy system, and proposes a specific, testable experiment with clear falsification criteria. Hypothesis B relies on a thermomechanical processing route that is less directly tied to the alloy's inherent stability under the specified extreme environments, and its cited evidence does not clearly support the claimed simultaneous improvemen"
 }
}
```

Both orders must agree for a win; here each order picked candidate A, so the pair counts as a tie.

## Integrity

```json
{
 "leakage_counters": {
  "temporal_violations": 0,
  "test_paper_leaks": 0,
  "family_leaks": 0,
  "target_doi_or_title_leaks": 0,
  "invalid_citations": 0
 },
 "target_free_asserted": true,
 "evidence_records_seen": 46
}
```

