# Hypothesis Branch Merge

## System Prompt

```text
You are given TWO surviving hypotheses from independent branches of a search.
Propose ONE new hypothesis that combines the strongest, most complementary elements of both -
not a superficial concatenation, but a genuine synthesis where the mechanisms reinforce each other.

You may re-cite ids already used by either parent; do not invent new ids you were not given.

Return a single JSON object (not a list): {"hypothesis": "...", "mechanism": "...",
"cited_ids": ["..."], "crosses_boundary": "..."}
```

## User Prompt

```text
GOAL: {goal}

BRANCH A:
Hypothesis: {hypothesis_a}
Mechanism: {mechanism_a}
Cited items:
{cited_items_a}

BRANCH B:
Hypothesis: {hypothesis_b}
Mechanism: {mechanism_b}
Cited items:
{cited_items_b}
```
