"""Decision diagnostics for loop methods (loop.md failure analyses). Target-aware, analysis only.

For every method whose notebook records a chosen family, compare that family with the target's type (from the
experiment-22 labels, a property of the target, not of the query) and report:
  family_hit   = the decision step picked the target's kind of answer;
  lever_ge2    = the final hypothesis hit the target's lever (GPT-5.6 label);
  recon        = GPT-5.6 reconstruction;
per method and per case, plus the reconstruction conditional on a family hit.
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from typing import Any

import hypo_loop as H
from hypothesis_evidence_v2 import atomic_json
from temporal_eval_v3 import EXPERIMENT_DIR
from temporal_hypothesis_benchmark import _read_json

TARGET_TYPES = EXPERIMENT_DIR / "rerun_v3" / "failure" / "analysis.json"
FAMILY_TO_TYPE = {
    "composition_change": "composition_change",
    "processing_or_synthesis_route": "processing_route",
    "thermal_or_thermomechanical_treatment": "heat_or_thermomechanical_treatment",
    "microstructure_architecture": "microstructure_architecture",
    "surface_or_interface_engineering": "surface_or_coating",
    "controlled_variable_experiment": "experimental_characterization_study",
    "in_situ_or_advanced_characterization": "experimental_characterization_study",
    "atomistic_or_mesoscale_simulation": "simulation_study",
    "combined_experiment_and_simulation": "simulation_study",
    "new_computational_method_or_potential": "computational_method_development",
    "new_sampling_or_free_energy_scheme": "computational_method_development",
    "data_driven_or_machine_learning_model": "computational_method_development",
    "new_measurement_method": "experimental_characterization_study",
}


def mean(values: list[Any]) -> float | None:
    values = [v for v in values if v is not None]
    return round(statistics.fmean(values), 3) if values else None


def chosen_family(notes: dict[str, Any]) -> str | None:
    for key in ("decision",):  # the decision that produced the final hypothesis
        if isinstance(notes.get(key), dict) and notes[key].get("chosen_family"):
            return str(notes[key]["chosen_family"])
    if notes.get("tournament"):
        return str(notes["tournament"][0]["family"])
    if notes.get("selection") and "family" in notes["selection"][0]:
        return str(notes["selection"][0]["family"])
    return None


def report(split: str = "dev") -> dict[str, Any]:
    target_type = {pid: c["target_type"] for pid, c in _read_json(TARGET_TYPES)["per_case"].items()}
    rows = H.load_scored()
    out: dict[str, Any] = {}
    per_case: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for method in sorted({r["run"]["method"] for r in rows}):
        rs = [r for r in rows if r["run"]["method"] == method and r["gpt"] and r["run"]["split"] == split]
        fam_rows = [r for r in rs if chosen_family(r["run"].get("notes") or {})]
        hits = [FAMILY_TO_TYPE.get(chosen_family(r["run"]["notes"]), "?") == target_type[r["run"]["paper_id"]]
                for r in fam_rows]
        out[method] = {
            "runs": len(rs), "with_decision": len(fam_rows),
            "family_hit": mean([1.0 if h else 0.0 for h in hits]),
            "recon_given_family_hit": mean([H.recon(r["gpt"]["scores"]) for r, h in zip(fam_rows, hits) if h]),
            "recon_given_family_miss": mean([H.recon(r["gpt"]["scores"]) for r, h in zip(fam_rows, hits) if not h]),
            "lever_ge2": mean([1.0 if r["label"]["lever_match"] >= 2 else 0.0 for r in rs if r["label"]]),
            "same_class": mean([1.0 if r["label"]["lever_match"] >= 1 else 0.0 for r in rs if r["label"]]),
            "recon": mean([H.recon(r["gpt"]["scores"]) for r in rs]),
        }
        for r in rs:
            per_case[r["run"]["paper_id"]][method].append(H.recon(r["gpt"]["scores"]))
    cases = {pid: {"target_type": target_type[pid], **{m: round(statistics.fmean(v), 2) for m, v in ms.items()}}
             for pid, ms in sorted(per_case.items())}
    result = {"split": split, "methods": out, "per_case": cases}
    atomic_json(H.OUT / f"decision_diagnostics_{split}.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(report()["methods"], indent=1))
