"""Typed evidence relations for citation and cross-paper comparison retrieval."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ENTITY_TYPES = {
    "paper",
    "atomic_claim",
    "method",
    "material_system",
    "property",
    "experimental_condition",
    "measurement",
    "dataset",
    "figure_table",
    "hypothesis",
}

RELATION_TYPES = {
    "cites",
    "supports",
    "contradicts",
    "uses_method",
    "compares_with",
    "outperforms",
    "underperforms",
    "applies_under",
    "measures",
    "derived_from",
    "analogous_to",
}


@dataclass(frozen=True)
class EvidenceEntity:
    entity_id: str
    entity_type: str
    name: str
    description: str
    source_paper_id: str
    evidence_span: str = ""
    source_element: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "EvidenceEntity":
        entity_type = str(row.get("entity_type", "")).lower()
        if entity_type not in ENTITY_TYPES:
            raise ValueError(f"unknown entity_type={entity_type!r}")
        if not row.get("entity_id") or not row.get("name"):
            raise ValueError("entity_id and name are required")
        confidence = float(row.get("confidence", 1.0))
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        return cls(
            entity_id=str(row["entity_id"]),
            entity_type=entity_type,
            name=str(row["name"]),
            description=str(row.get("description", "")),
            source_paper_id=str(row.get("source_paper_id", "")),
            evidence_span=str(row.get("evidence_span", "")),
            source_element=str(row.get("source_element", "")),
            attributes=dict(row.get("attributes", {})),
            confidence=confidence,
        )


@dataclass(frozen=True)
class EvidenceRelation:
    relation_id: str
    relation_type: str
    source_entity_id: str
    target_entity_ids: list[str]
    source_paper_id: str
    evidence_span: str
    source_element: str = ""
    metric: str = ""
    subject_value: Any = None
    reference_value: Any = None
    unit: str = ""
    conditions: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "EvidenceRelation":
        relation_type = str(row.get("relation_type", "")).lower()
        if relation_type not in RELATION_TYPES:
            raise ValueError(f"unknown relation_type={relation_type!r}")
        targets = [str(value) for value in row.get("target_entity_ids", [])]
        if not row.get("relation_id") or not row.get("source_entity_id") or not targets:
            raise ValueError("relation_id, source_entity_id, and target_entity_ids are required")
        confidence = float(row.get("confidence", 1.0))
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        return cls(
            relation_id=str(row["relation_id"]),
            relation_type=relation_type,
            source_entity_id=str(row["source_entity_id"]),
            target_entity_ids=targets,
            source_paper_id=str(row.get("source_paper_id", "")),
            evidence_span=str(row.get("evidence_span", "")),
            source_element=str(row.get("source_element", "")),
            metric=str(row.get("metric", "")),
            subject_value=row.get("subject_value"),
            reference_value=row.get("reference_value"),
            unit=str(row.get("unit", "")),
            conditions=dict(row.get("conditions", {})),
            confidence=confidence,
        )


def load_relations(path: Path | None) -> list[EvidenceRelation]:
    if path is None:
        return []
    if not path.exists():
        raise FileNotFoundError(f"relation file not found: {path}")
    relations = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            relations.append(EvidenceRelation.from_dict(json.loads(line)))
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise ValueError(f"invalid relation at {path}:{line_number}: {error}") from error
    return relations


def load_entities(path: Path) -> list[EvidenceEntity]:
    if not path.exists():
        raise FileNotFoundError(f"entity file not found: {path}")
    entities = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entities.append(EvidenceEntity.from_dict(json.loads(line)))
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise ValueError(f"invalid entity at {path}:{line_number}: {error}") from error
    return entities


def index_relations(relations: list[EvidenceRelation]) -> dict[str, list[EvidenceRelation]]:
    index: dict[str, list[EvidenceRelation]] = {}
    for relation in relations:
        index.setdefault(relation.source_entity_id, []).append(relation)
        for target_id in relation.target_entity_ids:
            index.setdefault(target_id, []).append(relation)
    return index