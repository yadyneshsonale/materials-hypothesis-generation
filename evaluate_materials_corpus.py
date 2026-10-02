"""Evaluate linked materials evidence outputs against their source papers."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from materials_evidence import MaterialsEvidenceUnit

CORE_FACETS = {
    "material", "intervention", "structure", "mechanism",
    "outcome", "conditions", "comparison", "provenance",
}


def evaluate(evidence_dir: Path, source_dir: Path) -> dict[str, Any]:
    output_paths = sorted(evidence_dir.glob("*.json"))
    source_ids = {path.stem for path in source_dir.glob("*.txt")}
    output_ids = {path.stem for path in output_paths}
    facet_counts: Counter[str] = Counter()
    evidence_types: Counter[str] = Counter()
    per_paper = []
    invalid_units = []
    total_units = 0
    total_rejected = 0
    complete_units = 0
    grounded_spans = 0
    total_spans = 0
    confidences = []

    for path in output_paths:
        payload = json.loads(path.read_text())
        paper_id = str(payload.get("paper_id") or path.stem)
        source_path = source_dir / f"{paper_id}.txt"
        if not source_path.exists():
            invalid_units.append({"paper_id": paper_id, "reason": "source text is missing"})
            continue
        source_text = source_path.read_text(encoding="utf-8", errors="ignore")
        rows = payload.get("evidence_units", [])
        rejected = payload.get("rejected_units", [])
        paper_valid = 0
        paper_invalid = 0
        for index, row in enumerate(rows):
            total_units += 1
            try:
                unit = MaterialsEvidenceUnit.from_dict(
                    row,
                    paper_id=paper_id,
                    source_text=source_text,
                )
            except (TypeError, ValueError) as error:
                paper_invalid += 1
                invalid_units.append({
                    "paper_id": paper_id,
                    "unit_index": index,
                    "reason": str(error),
                })
                continue
            paper_valid += 1
            facets = unit.facets()
            facet_counts.update(facets)
            evidence_types[unit.evidence_type] += 1
            complete_units += CORE_FACETS <= facets
            confidences.append(unit.confidence)
            total_spans += len(unit.evidence_spans)
            grounded_spans += sum(span in source_text for span in unit.evidence_spans)
        total_rejected += len(rejected)
        per_paper.append({
            "paper_id": paper_id,
            "valid_units": paper_valid,
            "invalid_units": paper_invalid,
            "rejected_units": len(rejected),
        })

    valid_units = total_units - len([
        row for row in invalid_units if "unit_index" in row
    ])
    return {
        "source_papers": len(source_ids),
        "output_papers": len(output_ids),
        "missing_output_papers": sorted(source_ids - output_ids),
        "unexpected_output_papers": sorted(output_ids - source_ids),
        "total_units": total_units,
        "valid_units": valid_units,
        "invalid_unit_count": len(invalid_units),
        "invalid_units": invalid_units,
        "rejected_model_units": total_rejected,
        "papers_without_valid_units": sorted(
            row["paper_id"] for row in per_paper if row["valid_units"] == 0
        ),
        "mean_valid_units_per_output_paper": (
            round(mean(row["valid_units"] for row in per_paper), 2) if per_paper else 0
        ),
        "verbatim_grounding_rate": round(grounded_spans / total_spans, 4) if total_spans else 0,
        "complete_core_chain_rate": round(complete_units / valid_units, 4) if valid_units else 0,
        "mean_confidence": round(mean(confidences), 4) if confidences else 0,
        "facet_coverage": {
            facet: {
                "units": facet_counts[facet],
                "rate": round(facet_counts[facet] / valid_units, 4) if valid_units else 0,
            }
            for facet in sorted(CORE_FACETS | {"limitations"})
        },
        "evidence_types": dict(sorted(evidence_types.items())),
        "per_paper": per_paper,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = evaluate(args.evidence_dir, args.source_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        f"[evaluate-materials] papers={result['output_papers']}/{result['source_papers']} "
        f"valid_units={result['valid_units']} invalid={result['invalid_unit_count']} "
        f"grounding={result['verbatim_grounding_rate']:.1%} "
        f"complete_chains={result['complete_core_chain_rate']:.1%}"
    )
    if result["invalid_unit_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
