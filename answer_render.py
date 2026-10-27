"""Render a frozen answer key (hidden target) into the generator's hypothesis schema, by code and without an LLM.

Used by the judge sanity controls (review_measurement.py, loop.md 16.1 A3) and by the few-shot worked examples
(loop_methods.py, B2). A worked example only ever uses the key of an earlier, different paper.
"""

from __future__ import annotations

from typing import Any

TARGET_FIELDS = ("material_initial_state", "intervention", "conditions", "structural_mediator", "mechanism",
                 "predicted_outcome", "baseline", "boundary", "discriminating_measurement", "actual_result")


def render(target: dict[str, Any]) -> dict[str, Any]:
    t = {k: str(target.get(k, "") or "").strip() for k in TARGET_FIELDS}
    hypothesis = (f"{t['intervention']} applied to {t['material_initial_state']} will act through "
                  f"{t['structural_mediator']} and {t['mechanism']}, giving {t['predicted_outcome']} relative to "
                  f"{t['baseline']}.")
    measurement = t["discriminating_measurement"]
    return {"hypothesis": hypothesis, "material_initial_state": t["material_initial_state"],
            "intervention": t["intervention"], "conditions": t["conditions"],
            "structural_mediator": t["structural_mediator"], "mechanism": t["mechanism"],
            "predicted_outcome": t["predicted_outcome"], "baseline": t["baseline"], "boundary": t["boundary"],
            "uncertainty": "", "supporting_evidence_ids": [], "conflicting_evidence_ids": [],
            "falsification_experiment": {"design": measurement, "measurements": [measurement] if measurement else [],
                                         "falsification_rule": "If the predicted outcome is not observed relative "
                                                               "to the baseline, the hypothesis is rejected."}}
