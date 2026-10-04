"""Normalized, grounded materials evidence for temporal hypothesis benchmarks."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "hypothesis-evidence-2.0"
STUDY_TYPES = {"experiment", "simulation", "theory", "mixed"}
CLAIM_OWNERSHIP = {"current_paper", "cited_work"}
MECHANISM_STATUS = {
    "observed",
    "inferred",
    "calculated",
    "simulated",
    "cited",
    "hypothesized",
    "contradicted",
}
EVIDENCE_STRENGTH = {
    "direct_measurement",
    "controlled_intervention",
    "correlation",
    "simulation",
    "thermodynamic_calculation",
    "author_interpretation",
    "cited_claim",
}
_EMPTY = {"", "none", "null", "unknown", "not reported", "not specified", "n/a"}


def _object(value: Any, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return dict(value)


def _objects(value: Any, name: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{name} must be a list of objects")
    return [dict(item) for item in value]


def _strings(value: Any, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{name} must be a list of strings")
    return [item.strip() for item in value if item.strip()]


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().casefold() not in _EMPTY
    if isinstance(value, dict):
        return any(_present(item) for item in value.values())
    if isinstance(value, list):
        return any(_present(item) for item in value)
    return True


def _stable_id(paper_id: str, sample_id: str, spans: list[str], measurements: list[dict[str, Any]]) -> str:
    encoded = json.dumps(
        [paper_id, sample_id, spans, measurements],
        ensure_ascii=False,
        sort_keys=True,
    ).encode()
    return f"{paper_id}::hypothesis_evidence_v2::{hashlib.sha256(encoded).hexdigest()[:16]}"


def _validate_composition(rows: list[dict[str, Any]]) -> None:
    for index, row in enumerate(rows):
        if not str(row.get("element", "")).strip():
            raise ValueError(f"sample.composition[{index}].element is required")
        value = row.get("fraction")
        if value is not None and not isinstance(value, (int, float)):
            raise ValueError(f"sample.composition[{index}].fraction must be numeric or null")
        if value is not None and value < 0:
            raise ValueError(f"sample.composition[{index}].fraction cannot be negative")
        unit = str(row.get("fraction_unit", "")).strip()
        if value is not None and unit not in {"at.%", "wt.%", "mole_fraction", "mass_fraction"}:
            raise ValueError(
                f"sample.composition[{index}].fraction_unit must identify the fraction basis"
            )


def _validate_measurements(rows: list[dict[str, Any]]) -> None:
    for index, row in enumerate(rows):
        if not str(row.get("property", "")).strip():
            raise ValueError(f"measurements[{index}].property is required")
        value = row.get("value")
        numeric_series = (
            isinstance(value, list)
            and bool(value)
            and all(isinstance(item, (int, float)) for item in value)
        )
        if value is not None and not isinstance(value, (int, float)) and not numeric_series:
            raise ValueError(
                f"measurements[{index}].value must be numeric, a numeric series, or null"
            )
        uncertainty = row.get("uncertainty")
        if uncertainty is not None and not isinstance(uncertainty, (int, float)):
            raise ValueError(f"measurements[{index}].uncertainty must be numeric or null")


def _limitations(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("limitations must be a list")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if isinstance(item, str) and item.strip():
            normalized.append({
                "type": "unspecified",
                "description": item.strip(),
                "impact": "",
            })
        elif isinstance(item, dict):
            row = dict(item)
            description = str(
                row.get("description") or row.get("failure_mode") or ""
            ).strip()
            if not description:
                raise ValueError(f"limitations[{index}] requires description or failure_mode")
            row.setdefault("type", "unspecified")
            row["description"] = description
            row.setdefault("impact", "")
            normalized.append(row)
        else:
            raise ValueError(f"limitations[{index}] must be a string or object")
    return normalized


def _validate_mechanisms(rows: list[dict[str, Any]], ownership: str) -> None:
    for index, row in enumerate(rows):
        if not str(row.get("assertion", "")).strip():
            raise ValueError(f"mechanisms[{index}].assertion is required")
        status = str(row.get("status", "")).strip().lower()
        if status not in MECHANISM_STATUS:
            raise ValueError(
                f"mechanisms[{index}].status must be one of {sorted(MECHANISM_STATUS)}"
            )
        strength = str(row.get("evidence_strength", "")).strip().lower()
        if strength not in EVIDENCE_STRENGTH:
            raise ValueError(
                f"mechanisms[{index}].evidence_strength must be one of "
                f"{sorted(EVIDENCE_STRENGTH)}"
            )
        source = str(row.get("source_ownership", ownership)).strip().lower()
        if source not in CLAIM_OWNERSHIP:
            raise ValueError(f"mechanisms[{index}].source_ownership is invalid")
        row["status"] = status
        row["evidence_strength"] = strength
        row["source_ownership"] = source


@dataclass(frozen=True)
class HypothesisEvidenceUnit:
    unit_id: str
    paper_id: str
    study_type: str
    claim_ownership: str
    sample: dict[str, Any]
    process_steps: list[dict[str, Any]]
    structure_observations: list[dict[str, Any]]
    test_conditions: dict[str, Any]
    measurements: list[dict[str, Any]]
    comparison: dict[str, Any]
    mechanisms: list[dict[str, Any]]
    boundaries: list[dict[str, Any]]
    limitations: list[dict[str, Any]]
    evidence_spans: list[str]
    source_section: str = ""
    extraction_confidence: float = 1.0
    result_revealing: bool = True

    @classmethod
    def from_dict(
        cls,
        row: dict[str, Any],
        *,
        paper_id: str | None = None,
        source_text: str | None = None,
    ) -> "HypothesisEvidenceUnit":
        if not isinstance(row, dict):
            raise ValueError("evidence unit must be an object")
        resolved_paper = str(row.get("paper_id") or paper_id or "").strip()
        if not resolved_paper:
            raise ValueError("paper_id is required")
        study_type = str(row.get("study_type", "")).strip().lower()
        if study_type not in STUDY_TYPES:
            raise ValueError(f"study_type must be one of {sorted(STUDY_TYPES)}")
        ownership = str(row.get("claim_ownership", "")).strip().lower()
        if ownership not in CLAIM_OWNERSHIP:
            raise ValueError(f"claim_ownership must be one of {sorted(CLAIM_OWNERSHIP)}")

        sample = _object(row.get("sample"), "sample")
        sample_id = str(sample.get("sample_id", "")).strip()
        if not sample_id:
            raise ValueError("sample.sample_id is required")
        if not (
            str(sample.get("material_name", "")).strip()
            or str(sample.get("nominal_composition", "")).strip()
        ):
            raise ValueError("sample.material_name or sample.nominal_composition is required")
        composition = _objects(sample.get("composition"), "sample.composition")
        _validate_composition(composition)
        sample["composition"] = composition

        process_steps = _objects(row.get("process_steps"), "process_steps")
        structure = _objects(row.get("structure_observations"), "structure_observations")
        conditions = _object(row.get("test_conditions"), "test_conditions")
        measurements = _objects(row.get("measurements"), "measurements")
        comparison = _object(row.get("comparison"), "comparison")
        mechanisms = _objects(row.get("mechanisms"), "mechanisms")
        boundaries = _objects(row.get("boundaries"), "boundaries")
        limitations = _limitations(row.get("limitations"))
        spans = _strings(row.get("evidence_spans"), "evidence_spans")
        _validate_measurements(measurements)
        _validate_mechanisms(mechanisms, ownership)
        if not spans:
            raise ValueError("at least one evidence span is required")
        if source_text is not None:
            missing = [span for span in spans if span not in source_text]
            if missing:
                raise ValueError(f"non-verbatim evidence span: {missing[0][:120]!r}")
        if not (_present(process_steps) or _present(structure)):
            raise ValueError("a process step or structure observation is required")
        process_lineage_only = (
            ownership == "current_paper"
            and bool(process_steps)
            and not bool(row.get("result_revealing", True))
        )
        if not (_present(measurements) or _present(mechanisms) or process_lineage_only):
            raise ValueError(
                "a measurement or mechanism assertion is required unless this is an "
                "explicit non-result process-lineage record"
            )

        confidence = float(row.get("extraction_confidence", 1.0))
        if not 0 <= confidence <= 1:
            raise ValueError("extraction_confidence must be between 0 and 1")
        unit_id = str(row.get("unit_id", "")).strip() or _stable_id(
            resolved_paper,
            sample_id,
            spans,
            measurements,
        )
        return cls(
            unit_id=unit_id,
            paper_id=resolved_paper,
            study_type=study_type,
            claim_ownership=ownership,
            sample=sample,
            process_steps=process_steps,
            structure_observations=structure,
            test_conditions=conditions,
            measurements=measurements,
            comparison=comparison,
            mechanisms=mechanisms,
            boundaries=boundaries,
            limitations=limitations,
            evidence_spans=spans,
            source_section=str(row.get("source_section", "")).strip(),
            extraction_confidence=confidence,
            result_revealing=bool(row.get("result_revealing", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def write_evidence_record(
    path: Path,
    paper_id: str,
    units: list[HypothesisEvidenceUnit],
    rejected_units: list[dict[str, Any]] | None = None,
    *,
    chunks_processed: int = 0,
    resumed_chunks: int = 0,
) -> None:
    atomic_json(path, {
        "schema_version": SCHEMA_VERSION,
        "paper_id": paper_id,
        "chunks_processed": chunks_processed,
        "resumed_chunks": resumed_chunks,
        "evidence_units": [unit.to_dict() for unit in units],
        "rejected_units": rejected_units or [],
    })


def load_evidence(path: Path) -> list[HypothesisEvidenceUnit]:
    paths = sorted(path.glob("*.json")) if path.is_dir() else [path]
    units: list[HypothesisEvidenceUnit] = []
    seen: set[str] = set()
    for item_path in paths:
        payload = json.loads(item_path.read_text())
        paper_id = str(payload.get("paper_id", "")).strip()
        for index, row in enumerate(payload.get("evidence_units", [])):
            try:
                unit = HypothesisEvidenceUnit.from_dict(row, paper_id=paper_id)
            except ValueError as error:
                raise ValueError(f"invalid v2 evidence at {item_path}:{index + 1}: {error}") from error
            if unit.unit_id in seen:
                raise ValueError(f"duplicate unit_id={unit.unit_id}")
            seen.add(unit.unit_id)
            units.append(unit)
    return units
