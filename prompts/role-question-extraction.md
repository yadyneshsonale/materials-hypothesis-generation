# Eleven-role and decision-question extraction

`role_question_extract.py` uses two model stages.

## Stage 1: section-level role extraction

Every paper section is checked against all 11 roles defined in `roles.py`. Claims retain an exact,
contiguous source span. The extractor rejects unknown roles, empty claims, and non-verbatim spans.

The prompt explicitly distinguishes:

- results from mechanisms;
- objectives from hypotheses;
- unusual observations from contradictions;
- test conditions from constraints; and
- cited prior work from the current paper's evidence.

## Stage 2: reconciliation and decision questions

Role candidates are reconciled without combining different materials, treatments, temperatures,
environments, or loading regimes.

A **decision question** is:

> A specific, answerable, and falsifiable information need whose answer changes a
> materials-design choice, causal-mechanism choice, boundary condition, or experiment.

It is not a topic label, paper-summary request, vague future-work prompt, unsupported speculation,
yes/no question without a discriminator, or restatement of an observed result.

Allowed types are:

- `baseline`: requests a quantitative reference under a named regime;
- `causal`: asks which linked mechanism explains an outcome and how to test it;
- `intervention`: asks which controllable change improves a named outcome;
- `boundary`: asks where a mechanism or benefit weakens, reverses, or fails; and
- `discrimination`: asks which measurement distinguishes competing explanations.

Every accepted question has a rationale, explicit decision use, required measurements or
comparisons, references to reconciled role items, exact source evidence, confidence, and a stable
question ID. Questions are limited to one primary uncertainty and at most 50 words by validation.
