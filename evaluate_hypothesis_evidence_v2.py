"""Evaluate validity, grounding, normalization, and completeness of v2 evidence."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from hypothesis_evidence_v2 import HypothesisEvidenceUnit, atomic_json


def evaluate(evidence_dir: Path, source_dir: Path) -> dict[str, Any]:
    files = sorted(evidence_dir.glob("*.json"))
    valid = 0
    invalid = 0
    grounded = 0
    rejected = 0
    ownership: Counter[str] = Counter()
    mechanism_status: Counter[str] = Counter()
    properties: Counter[str] = Counter()
    completeness: Counter[str] = Counter()
    per_paper: dict[str, dict[str, int]] = {}
    errors: list[dict[str, str]] = []
    for path in files:
        payload = json.loads(path.read_text())
        paper_id = str(payload.get("paper_id", path.stem))
        source_path = source_dir / f"{paper_id}.txt"
        source = source_path.read_text(encoding="utf-8", errors="ignore")
        paper_valid = 0
        paper_invalid = 0
        rejected += len(payload.get("rejected_units", []))
        for index, row in enumerate(payload.get("evidence_units", [])):
            try:
                unit = HypothesisEvidenceUnit.from_dict(
                    row,
                    paper_id=paper_id,
                    source_text=source,
                )
            except ValueError as error:
                invalid += 1
                paper_invalid += 1
                errors.append({
                    "paper_id": paper_id,
                    "unit_index": str(index),
                    "error": str(error),
                })
                continue
            valid += 1
            paper_valid += 1
            grounded += 1
            ownership[unit.claim_ownership] += 1
            if unit.sample.get("composition"):
                completeness["normalized_composition"] += 1
            if unit.process_steps:
                completeness["process_lineage"] += 1
            if unit.structure_observations:
                completeness["structure"] += 1
            if unit.test_conditions:
                completeness["conditions"] += 1
            if unit.measurements:
                completeness["measurements"] += 1
            if unit.comparison:
                completeness["comparison"] += 1
            if unit.boundaries:
                completeness["boundaries"] += 1
            if unit.limitations:
                completeness["limitations"] += 1
            for measurement in unit.measurements:
                properties[str(measurement.get("property", "")).strip().casefold()] += 1
                if measurement.get("value") is not None:
                    completeness["numeric_measurement"] += 1
                if measurement.get("uncertainty") is not None:
                    completeness["measurement_uncertainty"] += 1
            for mechanism in unit.mechanisms:
                mechanism_status[str(mechanism.get("status", ""))] += 1
        per_paper[paper_id] = {"valid_units": paper_valid, "invalid_units": paper_invalid}
    denominator = valid or 1
    return {
        "schema_version": "hypothesis-evidence-evaluation-2.0",
        "papers": len(files),
        "valid_units": valid,
        "invalid_units": invalid,
        "rejected_candidates": rejected,
        "exact_grounding_rate": grounded / denominator,
        "claim_ownership": dict(sorted(ownership.items())),
        "mechanism_status": dict(sorted(mechanism_status.items())),
        "completeness_rates": {
            key: round(value / denominator, 6)
            for key, value in sorted(completeness.items())
        },
        "unique_property_labels": len([key for key in properties if key]),
        "top_property_labels": properties.most_common(30),
        "per_paper": per_paper,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.evidence_dir, args.source_dir)
    atomic_json(args.output, result)
    if result["invalid_units"]:
        raise SystemExit(f"{result['invalid_units']} invalid v2 evidence units")


if __name__ == "__main__":
    main()
