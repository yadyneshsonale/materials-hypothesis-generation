# Extraction Role Taxonomy

The extraction system injects these 11 roles through `roles.role_table_prompt()`.

| Role | Definition | Example triggers | Worked example |
| --- | --- | --- | --- |
| `problem_motivation` | The gap or need being addressed by the paper. | "remains challenging"; "has not been achieved"; "there is a need for" | "A description of this process under bulk solvation conditions is missing." |
| `prior_approach` | An existing method or approach mentioned as prior work. | "previous studies used"; "X et al. reported"; "prior work has" | "Ullah et al. computed the registry-dependent stacking energy of encapsulated CuI/graphene." |
| `prior_limitation` | The stated weakness of a prior approach. | "however, this suffers from"; "limited by"; "fails to" | "Their analysis stops at empirical per-element power-law fits, with no shared physical parameter set." |
| `rejected_alternative` | An explicitly rejected method or contrastive motivation positioning this work against prior work. | "unlike X"; "we avoided Y since"; "rather than"; "unlike previous reports" | "Unlike previous reports, this study systematically examines the coupled influence of absorber, ETL, and HTL properties together with bulk and interface defects." |
| `inspiration_source` | An analogy, prior finding, or borrowed method that shaped the new approach. | "inspired by"; "drawing on"; "analogous to" | "The compression method was analogous to the Langmuir-Blodgett process." |
| `causal_claim` | A claim that X caused, increased, or decreased Y, including conditions or magnitude when stated. | "resulted in"; "led to a"; "as a result of"; "increased by" | "Thermal annealing at 180C promotes growth of extended, well-defined domains." |
| `mechanism_principle` | The underlying physical or chemical reasoning offered for a causal claim. | "this is attributed to"; "due to the strain induced by"; "because of" | "The 30 degree offset reflects the energetically preferred registry where iodine occupies hexagon centers." |
| `hypothesis_statement` | An explicit or implicit statement of the paper's core proposal or expectation. | "we hypothesize"; "we propose that"; "our approach should" | "Oxo-G retains sufficient lattice periodicity to serve as a robust template for van der Waals epitaxy." |
| `evidence_result` | A measured outcome supporting or refuting a claim. | "confirmed by"; "measured value of"; "as shown in Figure" | "Control synthesis on a gold TEM grid yields no h-CuI under otherwise identical conditions." |
| `constraint` | A stated limitation or boundary condition the solution must satisfy. | "must remain below"; "constrained to"; "under ambient conditions" | "These trajectories cannot access dynamics on time scales longer than the ~1.5 ps restart segments." |
| `contradiction` | The paper's own result conflicts with a prior claim in the literature. | "in contrast to prior reports"; "unexpectedly, we found" | "Contrary to what analytical potential molecular dynamics simulations predicted, we predominantly observe boron single vacancies." |
