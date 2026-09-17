# Prompt Catalog

This directory documents the prompts used by the pipeline. Braced fields such as `{goal}` and `{text}` are populated at runtime.

| File | Purpose | Runtime owner |
| --- | --- | --- |
| `extraction.md` | Extract typed argumentative items from paper sections | `extract.py` |
| `reconciliation.md` | Reconcile role items across a paper | `extract.py` |
| `role-taxonomy.md` | Define extraction roles, triggers, and examples | `roles.py` |
| `hypothesis-composition.md` | Compose cross-paper hypotheses | `hypothesis_agent.py` |
| `hypothesis-critics.md` | Score plausibility, novelty, and feasibility | `hypothesis_agent.py` |
| `hypothesis-refinement.md` | Revise a candidate from critic feedback | `hypothesis_agent.py` |
| `hypothesis-merge.md` | Synthesize two surviving branches | `hypothesis_agent.py` |
| `gold-comparison-judge.md` | Compare extracted claims with gold abstracts | `compare_with_gold.py` |
| `masked-recovery-judge.md` | Score recovery of a withheld paper | `validate_masked.py` |

The Python constants remain the executable source of truth; these files expose the complete templates for review and experiment reporting.
