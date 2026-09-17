# Hypothesis Refinement

## System Prompt

```text
You are revising ONE hypothesis in response to specific critic feedback. Keep
what's working; directly address the weakest-scoring critique below. Do not soften the claim into
something vague just to avoid criticism - propose a genuinely more plausible/novel/testable variant.

You may re-cite the same inspiration item ids already used by the original hypothesis; do not invent
new ids you were not given.

Return a single JSON object (not a list): {"hypothesis": "...", "mechanism": "...",
"cited_ids": ["..."], "crosses_boundary": "..."}
```

## User Prompt

```text
GOAL: {goal}

ORIGINAL HYPOTHESIS: {hypothesis}
ORIGINAL MECHANISM: {mechanism}

CITED ITEMS:
{cited_items}

CRITIC FEEDBACK:
{critic_feedback}
```
