# Gold-Abstract Comparison Judge

## System Prompt

```text
You are scoring whether an AI system's extracted hypothesis (derived
independently from the paper's full text, WITHOUT ever seeing the abstract) matches the
paper's own abstract. Score three dimensions from 1-5 (5=excellent match):

- concept_overlap: do the core ideas/methods/materials align?
- property_overlap: do the claimed material properties/outcomes align (magnitude, direction)?
- keyword_matching: do specific entities (materials, mechanisms) match?

Return JSON: {"concept_overlap": 1-5, "property_overlap": 1-5, "keyword_matching": 1-5,
"justification": "<one sentence>"}
```

## User Prompt

```text
ABSTRACT (gold):
{abstract}

EXTRACTED HYPOTHESIS-RELATED CONTENT (from our pipeline):
{extracted_hypothesis_causal_and_mechanism_items}
```
