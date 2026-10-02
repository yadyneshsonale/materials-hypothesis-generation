"""Validated, linked materials evidence for hypothesis generation."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
EVIDENCE_TYPES = {"experiment", "simulation", "theory", "mixed"}
_EMPTY_MARKERS = {
    "", "n/a", "na", "none", "null", "not applicable", "not available",
    "not explicitly stated", "not reported", "not specified", "unknown",
}


def _mapping(value: Any, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    return dict(value)


def _strings(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} must be a list of strings")
    return [item.strip() for item in value if item.strip()]


def _has_content(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in _EMPTY_MARKERS
    if isinstance(value, dict):
        return any(_has_content(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_has_content(item) for item in value)
    return True


def _stable_id(paper_id: str, evidence_spans: list[str], material: dict[str, Any], outcome: dict[str, Any]) -> str:
    payload = json.dumps(
        [paper_id, evidence_spans, material, outcome],
        sort_keys=True,
        ensure_ascii=False,
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return f"{paper_id}::materials_evidence::{digest}"


@dataclass(frozen=True)
class MaterialsEvidenceUnit:
    unit_id: str
    paper_id: str
    evidence_type: str
    material: dict[str, Any]
    intervention: dict[str, Any]
    structure: dict[str, Any]
    mechanism: str
    outcome: dict[str, Any]
    conditions: dict[str, Any]
    comparison: dict[str, Any]
    evidence_spans: list[str]
    source_section: str = ""
    limitations: list[str] = field(default_factory=list)
    confidence: float = 1.0

    @classmethod
    def from_dict(
        cls,
        row: dict[str, Any],
        *,
        paper_id: str | None = None,
        source_text: str | None = None,
    ) -> "MaterialsEvidenceUnit":
        if not isinstance(row, dict):
            raise ValueError("evidence unit must be an object")
        resolved_paper_id = str(row.get("paper_id") or paper_id or "").strip()
        if not resolved_paper_id:
            raise ValueError("paper_id is required")

        evidence_type = str(row.get("evidence_type", "")).lower()
        if evidence_type not in EVIDENCE_TYPES:
            raise ValueError(f"evidence_type must be one of {sorted(EVIDENCE_TYPES)}")

        material = _mapping(row.get("material"), "material")
        intervention = _mapping(row.get("intervention"), "intervention")
        structure = _mapping(row.get("structure"), "structure")
        outcome = _mapping(row.get("outcome"), "outcome")
        conditions = _mapping(row.get("conditions"), "conditions")
        comparison = _mapping(row.get("comparison"), "comparison")
        evidence_spans = _strings(row.get("evidence_spans"), "evidence_spans")
        limitations = _strings(row.get("limitations"), "limitations")

        if not str(material.get("name", "")).strip() and not str(material.get("composition", "")).strip():
            raise ValueError("material.name or material.composition is required")
        if not evidence_spans:
            raise ValueError("at least one verbatim evidence span is required")
        if source_text is not None:
            missing = [span for span in evidence_spans if span not in source_text]
            if missing:
                raise ValueError(f"non-verbatim evidence span: {missing[0][:120]!r}")

        mechanism = str(row.get("mechanism", "")).strip()
        has_intervention_or_structure = bool(
            _has_content(intervention.get("action"))
            or _has_content(intervention.get("description"))
            or _has_content(structure)
        )
        has_explanatory_outcome = bool(
            _has_content(mechanism) or _has_content(outcome.get("property"))
        )
        if not has_intervention_or_structure or not has_explanatory_outcome:
            raise ValueError(
                "unit must link an intervention or structure to a mechanism or property outcome"
            )

        confidence = float(row.get("confidence", 1.0))
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")

        unit_id = str(row.get("unit_id", "")).strip() or _stable_id(
            resolved_paper_id, evidence_spans, material, outcome
        )
        return cls(
            unit_id=unit_id,
            paper_id=resolved_paper_id,
            evidence_type=evidence_type,
            material=material,
            intervention=intervention,
            structure=structure,
            mechanism=mechanism,
            outcome=outcome,
            conditions=conditions,
            comparison=comparison,
            evidence_spans=evidence_spans,
            source_section=str(row.get("source_section", "")).strip(),
            limitations=limitations,
            confidence=confidence,
        )

    def facets(self) -> set[str]:
        present = {"material", "provenance"}
        if _has_content(self.intervention):
            present.add("intervention")
        if _has_content(self.structure):
            present.add("structure")
        if _has_content(self.mechanism):
            present.add("mechanism")
        if _has_content(self.outcome):
            present.add("outcome")
        if _has_content(self.conditions):
            present.add("conditions")
        if _has_content(self.comparison):
            present.add("comparison")
        if self.limitations:
            present.add("limitations")
        return present

    def summary(self) -> str:
        parts = [
            str(self.material.get("name") or self.material.get("composition") or "material"),
            str(self.intervention.get("description") or self.intervention.get("action") or ""),
            str(self.structure.get("description") or self.structure.get("phases") or ""),
            self.mechanism,
            str(self.outcome.get("property") or ""),
            str(self.outcome.get("value") or ""),
            str(self.outcome.get("unit") or ""),
            json.dumps(self.conditions, ensure_ascii=False),
            json.dumps(self.comparison, ensure_ascii=False),
        ]
        return " | ".join(part for part in parts if part and part != "{}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_materials_evidence(path: Path | None) -> list[MaterialsEvidenceUnit]:
    if path is None:
        return []
    if not path.exists():
        raise FileNotFoundError(f"materials evidence path not found: {path}")
    paths = sorted(path.glob("*.json")) if path.is_dir() else [path]
    units: list[MaterialsEvidenceUnit] = []
    seen: set[str] = set()
    for file_path in paths:
        payload = json.loads(file_path.read_text())
        paper_id = str(payload.get("paper_id", ""))
        rows = payload.get("evidence_units", [])
        if not isinstance(rows, list):
            raise ValueError(f"evidence_units must be a list: {file_path}")
        for index, row in enumerate(rows):
            try:
                unit = MaterialsEvidenceUnit.from_dict(row, paper_id=paper_id)
            except ValueError as error:
                raise ValueError(f"invalid materials evidence at {file_path}:{index + 1}: {error}") from error
            if unit.unit_id in seen:
                raise ValueError(f"duplicate materials evidence unit_id={unit.unit_id}")
            seen.add(unit.unit_id)
            units.append(unit)
    return units


def write_materials_record(
    path: Path,
    paper_id: str,
    units: list[MaterialsEvidenceUnit],
    rejected_units: list[dict[str, Any]] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "paper_id": paper_id,
        "evidence_units": [unit.to_dict() for unit in units],
        "rejected_units": rejected_units or [],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
