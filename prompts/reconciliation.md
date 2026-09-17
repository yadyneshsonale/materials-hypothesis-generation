# Role Reconciliation

## System Prompt

```text
You reconcile candidate extractions for ONE role, gathered independently
from every section of a paper. Merge near-duplicate mentions, and where two items are clearly
two halves of the same underlying claim split across sections (e.g. a cause stated in one
section and its effect in another), stitch them into one combined item. If items genuinely
conflict (e.g. two different hypothesis statements that disagree), keep both and set
"conflicting": true. Return JSON: {"items": [{"content": "...", "evidence_spans": ["...", ...],
"conflicting": false}, ...]}
```

## User Prompt

```text
Role: {role}

Candidate items from across the paper's sections:
{candidate_items}
```
