"""Role taxonomy for per-chunk argumentative extraction (MatHG Stage 1)."""

ROLES = [
    {
        "key": "problem_motivation",
        "definition": "The gap or need being addressed by the paper.",
        "triggers": ["remains challenging", "has not been achieved", "there is a need for"],
        "example": "\"A description of this process under bulk solvation conditions is missing.\" -> problem_motivation",
    },
    {
        "key": "prior_approach",
        "definition": "An existing method or approach mentioned as prior work.",
        "triggers": ["previous studies used", "X et al. reported", "prior work has"],
        "example": "\"Ullah et al. computed the registry-dependent stacking energy of encapsulated CuI/graphene.\" -> prior_approach",
    },
    {
        "key": "prior_limitation",
        "definition": "The stated weakness of a prior approach.",
        "triggers": ["however, this suffers from", "limited by", "fails to"],
        "example": "\"Their analysis stops at empirical per-element power-law fits, with no shared physical parameter set.\" -> prior_limitation",
    },
    {
        "key": "rejected_alternative",
        "definition": (
            "An approach the authors explicitly considered but did not use, together with the reason. "
            "A comparison, an observed performance difference, or a general weakness of prior work is not "
            "a rejected alternative unless the text establishes the authors' decision not to use it."
        ),
        "triggers": ["we did not use", "we avoided", "was rejected because"],
        "example": (
            "\"We did not use the Voigt approximation because it cannot represent grain-level stress variation.\" "
            "-> rejected_alternative"
        ),
    },
    {
        "key": "inspiration_source",
        "definition": "An analogy, prior finding, or borrowed method that shaped the new approach.",
        "triggers": ["inspired by", "drawing on", "analogous to"],
        "example": "\"The compression method was analogous to the Langmuir-Blodgett process.\" -> inspiration_source",
    },
    {
        "key": "causal_claim",
        "definition": "A claim that X caused/increased/decreased Y, with condition/magnitude if stated.",
        "triggers": ["resulted in", "led to a", "as a result of", "increased by"],
        "example": "\"Thermal annealing at 180C promotes growth of extended, well-defined domains.\" -> causal_claim",
    },
    {
        "key": "mechanism_principle",
        "definition": "The underlying physical/chemical reasoning offered for a causal claim.",
        "triggers": ["this is attributed to", "due to the strain induced by", "because of"],
        "example": "\"The 30 degree offset reflects the energetically preferred registry where iodine occupies hexagon centers.\" -> mechanism_principle",
    },
    {
        "key": "hypothesis_statement",
        "definition": (
            "A testable proposal or expectation about what should happen and why. A statement of study purpose, "
            "a method that was used, or a result already observed is not a hypothesis."
        ),
        "triggers": ["we hypothesize", "we propose that", "our approach should"],
        "example": "\"Oxo-G retains sufficient lattice periodicity to serve as a robust template for van der Waals epitaxy.\" -> hypothesis_statement",
    },
    {
        "key": "evidence_result",
        "definition": "A measured outcome supporting or refuting a claim.",
        "triggers": ["confirmed by", "measured value of", "as shown in Figure"],
        "example": "\"Control synthesis on a gold TEM grid yields no h-CuI under otherwise identical conditions.\" -> evidence_result",
    },
    {
        "key": "constraint",
        "definition": (
            "A stated design requirement, validity boundary, experimental limitation, or operating condition. "
            "An observed value, performance tradeoff, or stability result is not a constraint unless the paper "
            "states it as a requirement or limit."
        ),
        "triggers": ["must remain below", "constrained to", "under ambient conditions"],
        "example": "\"These trajectories cannot access dynamics on time scales longer than the ~1.5 ps restart segments.\" -> constraint",
    },
    {
        "key": "contradiction",
        "definition": (
            "The paper's own result explicitly conflicts with a specific prior claim or accepted expectation. "
            "An unusual observation, a comparison between materials, or the absence of a feature is not enough "
            "without identifying the conflicting expectation."
        ),
        "triggers": ["in contrast to prior reports", "unexpectedly, we found"],
        "example": "\"Contrary to what analytical potential molecular dynamics simulations predicted, we predominantly observe boron single vacancies.\" -> contradiction",
    },
]

ROLE_KEYS = [r["key"] for r in ROLES]


def role_table_prompt() -> str:
    """Render the role taxonomy (definition + triggers + one worked example) for the extraction prompt."""
    lines = []
    for r in ROLES:
        trig = ", ".join(f'"{t}"' for t in r["triggers"])
        lines.append(f"- {r['key']}: {r['definition']} (e.g. triggers: {trig})\n  Example: {r['example']}")
    return "\n".join(lines)
