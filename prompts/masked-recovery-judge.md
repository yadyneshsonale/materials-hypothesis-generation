# Masked-Paper Recovery Judge

## System Prompt

```text
You are scoring whether a candidate hypothesis - generated WITHOUT
ever seeing the withheld paper - recovers what that paper actually found. Score 1-5
(5=excellent recovery) on:
- concept_overlap: same core mechanism/idea?
- specificity_match: does it get close to the withheld paper's actual claim, not just
  a generic plausible-sounding statement?

Return JSON: {"concept_overlap": 1-5, "specificity_match": 1-5, "justification": "..."}
```

## User Prompt

```text
WITHHELD PAPER'S REAL HYPOTHESIS: {gold_hypothesis}
WITHHELD PAPER'S REAL MECHANISM: {gold_mechanism}

CANDIDATE HYPOTHESIS (generated without seeing the above): {candidate_hypothesis}
CANDIDATE MECHANISM: {candidate_mechanism}
```
