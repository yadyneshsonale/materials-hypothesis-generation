"""Validated question-centered evidence for cross-paper materials reasoning."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from hypothesis_evidence_v2 import atomic_json

SCHEMA_VERSION = "question-evidence-1.0"
RESOLUTION_STATUSES = {
    "answered_same_paper",
    "answered_earlier_corpus",
    "partially_answered",
    "unresolved",
    "reading_only",
    "replication_detail",
}
ANSWER_STATUSES = {
    "observed",
    "inferred",
    "calculated",
    "simulated",
    "cited",
    "hypothesized",
    "contradicted",
    "unspecified",
}
DOMAINS = {
    "oxidation_corrosion",
    "mechanical_deformation",
    "phase_stability",
    "processing_manufacturing",
    "radiation_defects",
    "thermal_transport",
    "wear_tribology",
    "magnetic_functional",
    "general_materials",
}
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _text(value: Any, name: str, required: bool = False) -> str:
    result = str(value or "").strip()
    if required and not result:
        raise ValueError(f"{name} is required")
    return result


def _strings(value: Any, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{name} must be a list of strings")
    return [item.strip() for item in value if item.strip()]


def _slug(value: str) -> str:
    return _SLUG_RE.sub("_", value.casefold()).strip("_") or "unspecified"


def stable_answer_id(question_id: str, evidence_id: str, answer: str) -> str:
    digest = hashlib.sha256(
        json.dumps([question_id, evidence_id, answer], ensure_ascii=False).encode()
    ).hexdigest()[:16]
    return f"{question_id}::answer::{digest}"


def stable_cluster_id(facets: dict[str, str]) -> str:
    keys = (
        "domain",
        "subtopic",
        "target_property",
        "condition_regime",
    )
    signature = "|".join(_slug(str(facets.get(key, ""))) for key in keys)
    digest = hashlib.sha256(signature.encode()).hexdigest()[:12]
    return f"question_cluster::{_slug(facets.get('domain', 'general'))}::{digest}"


@dataclass(frozen=True)
class GroundedAnswer:
    answer_id: str
    question_id: str
    paper_id: str
    publication_date: str
    evidence_unit_id: str
    answer: str
    material: str
    processing_state: str
    conditions: str
    measurement_outcome: str
    mechanism: str
    boundary_limitation: str
    epistemic_status: str
    evidence_spans: list[str]
    confidence: float

    @classmethod
    def from_dict(
        cls,
        row: dict[str, Any],
        *,
        question_id: str,
        evidence_lookup: dict[str, dict[str, Any]],
    ) -> "GroundedAnswer":
        if not isinstance(row, dict):
            raise ValueError("answer must be an object")
        evidence_id = _text(row.get("evidence_unit_id"), "evidence_unit_id", True)
        if evidence_id not in evidence_lookup:
            raise ValueError(f"unknown evidence_unit_id={evidence_id}")
        evidence = evidence_lookup[evidence_id]
        spans = _strings(row.get("evidence_spans"), "evidence_spans")
        allowed_spans = set(evidence.get("evidence_spans", []))
        if not spans or not set(spans) <= allowed_spans:
            raise ValueError("answer evidence_spans must be exact spans from its evidence unit")
        status = _text(row.get("epistemic_status"), "epistemic_status").lower()
        if status not in ANSWER_STATUSES:
            raise ValueError(f"epistemic_status must be one of {sorted(ANSWER_STATUSES)}")
        confidence = float(row.get("confidence", 1.0))
        if not 0 <= confidence <= 1:
            raise ValueError("answer confidence must be between 0 and 1")
        answer = _text(row.get("answer"), "answer", True)
        return cls(
            answer_id=_text(row.get("answer_id"), "answer_id") or stable_answer_id(
                question_id, evidence_id, answer
            ),
            question_id=question_id,
            paper_id=_text(evidence.get("paper_id"), "paper_id", True),
            publication_date=_text(evidence.get("publication_date"), "publication_date", True),
            evidence_unit_id=evidence_id,
            answer=answer,
            material=_text(row.get("material"), "material"),
            processing_state=_text(row.get("processing_state"), "processing_state"),
            conditions=_text(row.get("conditions"), "conditions"),
            measurement_outcome=_text(row.get("measurement_outcome"), "measurement_outcome"),
            mechanism=_text(row.get("mechanism"), "mechanism"),
            boundary_limitation=_text(row.get("boundary_limitation"), "boundary_limitation"),
            epistemic_status=status,
            evidence_spans=spans,
            confidence=confidence,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResolvedQuestion:
    question_id: str
    paper_id: str
    publication_date: str
    question: str
    question_type: str
    category: str
    resolution_status: str
    resolution_summary: str
    facets: dict[str, str]
    answers: list[GroundedAnswer]
    source_evidence_spans: list[str]

    @classmethod
    def from_dict(
        cls,
        row: dict[str, Any],
        *,
        evidence_lookup: dict[str, dict[str, Any]],
    ) -> "ResolvedQuestion":
        if not isinstance(row, dict):
            raise ValueError("resolved question must be an object")
        question_id = _text(row.get("question_id"), "question_id", True)
        status = _text(row.get("resolution_status"), "resolution_status").lower()
        if status not in RESOLUTION_STATUSES:
            raise ValueError(f"resolution_status must be one of {sorted(RESOLUTION_STATUSES)}")
        facets = row.get("facets")
        if not isinstance(facets, dict):
            raise ValueError("facets must be an object")
        normalized_facets = {
            key: _text(facets.get(key), f"facets.{key}", key in {"domain", "subtopic"})
            for key in (
                "domain",
                "subtopic",
                "material_family",
                "target_property",
                "design_variable",
                "condition_regime",
                "mechanism_topic",
                "question_function",
            )
        }
        if normalized_facets["domain"] not in DOMAINS:
            raise ValueError(f"domain must be one of {sorted(DOMAINS)}")
        answers = [
            GroundedAnswer.from_dict(
                answer,
                question_id=question_id,
                evidence_lookup=evidence_lookup,
            )
            for answer in row.get("answers", [])
        ]
        if status.startswith("answered") and not answers:
            raise ValueError(f"{status} requires at least one answer")
        return cls(
            question_id=question_id,
            paper_id=_text(row.get("paper_id"), "paper_id", True),
            publication_date=_text(row.get("publication_date"), "publication_date", True),
            question=_text(row.get("question"), "question", True),
            question_type=_text(row.get("question_type"), "question_type", True),
            category=_text(row.get("category"), "category", True),
            resolution_status=status,
            resolution_summary=_text(row.get("resolution_summary"), "resolution_summary"),
            facets=normalized_facets,
            answers=answers,
            source_evidence_spans=_strings(
                row.get("source_evidence_spans"),
                "source_evidence_spans",
            ),
        )

    def cluster_id(self) -> str:
        return stable_cluster_id(self.facets)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["cluster_id"] = self.cluster_id()
        return payload


def write_resolved_paper(
    path: Path,
    paper_id: str,
    questions: list[ResolvedQuestion],
    rejected: list[dict[str, Any]],
) -> None:
    atomic_json(path, {
        "schema_version": SCHEMA_VERSION,
        "paper_id": paper_id,
        "questions": [question.to_dict() for question in questions],
        "rejected": rejected,
    })


def load_resolved(path: Path) -> list[ResolvedQuestion]:
    files = sorted(path.glob("*.json")) if path.is_dir() else [path]
    rows: list[ResolvedQuestion] = []
    for file_path in files:
        payload = json.loads(file_path.read_text())
        evidence_lookup = {
            answer["evidence_unit_id"]: {
                "paper_id": answer["paper_id"],
                "publication_date": answer["publication_date"],
                "evidence_spans": answer["evidence_spans"],
            }
            for question in payload.get("questions", [])
            for answer in question.get("answers", [])
        }
        rows.extend(
            ResolvedQuestion.from_dict(row, evidence_lookup=evidence_lookup)
            for row in payload.get("questions", [])
        )
    return rows
