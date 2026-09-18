"""Build typed entities and relations from role-extraction outputs.

The builder is deliberately a post-extraction stage: each paper is normalized
independently and written atomically, so failures can retry without repeating
role extraction. Final JSONL files are deterministic aggregates of per-paper files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from evidence_model import ENTITY_TYPES, RELATION_TYPES, EvidenceEntity, EvidenceRelation
from llm_client import provider_info, resilient_chat_json

BATCH_SIZE = 15
SEMANTIC_TYPES = {
    "method", "material_system", "property", "experimental_condition",
    "measurement", "dataset",
}
SEMANTIC_RELATIONS = {
    "supports", "contradicts", "uses_method", "compares_with", "outperforms",
    "underperforms", "applies_under", "measures", "analogous_to",
}
_MATERIAL_TERMS = re.compile(
    r"\b(graphene|alloy|oxide|electrolyte|electrode|interface|semiconductor|polymer|"
    r"perovskite|catalyst|membrane|film|crystal|nanoparticle|composite|ceramic|metal|"
    r"battery|photovoltaic|solar cell|quantum dot|hydrogel|coating)\b",
    re.I,
)
_CONDITION_RE = re.compile(
    r"\b(?:under|at|above|below|between|within)\s+[^.;]{0,60}?(?:\d+(?:\.\d+)?\s*"
    r"(?:K|°C|C|Pa|MPa|GPa|V|mV|A|mA|μA|Hz|nm|μm|mm|cm|h|s|%|mol|M)\b)",
    re.I,
)

_NORMALIZE_SYSTEM = """You normalize extracted materials-science claims into typed entities and
evidence relations. Use only information explicit in the supplied claims. Do not add background
knowledge. Entity types: method, material_system, property, experimental_condition, measurement,
dataset. Relation types: supports, contradicts, uses_method, compares_with, outperforms,
underperforms, applies_under, measures, analogous_to.

Return JSON with:
{"annotations": [{"claim_id": "...", "entities": [{"local_id": "E1", "type": "method",
"name": "...", "description": "...", "evidence_span": "verbatim supplied evidence",
"attributes": {}, "confidence": 0.0}], "relations": [{"type": "uses_method",
"source": "claim_id or local_id", "target": "claim_id or local_id", "evidence_span":
"verbatim supplied evidence", "source_element": "", "metric": "", "subject_value": null,
"reference_value": null, "unit": "", "conditions": {}, "confidence": 0.0}]}]}.

Measurements must have a value, qualitative outcome, or explicit comparison in attributes.
Use outperforms/underperforms only when the direction, metric, and conditions are stated. Preserve
conflicting claims rather than selecting a winner. Every entity and relation needs evidence from
the supplied claim. Local IDs only need to be unique inside one annotation."""


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:16]
    return f"{prefix}:{digest}"


def _normalize_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def _title_from_source(paper_id: str, source_text: str, metadata: dict[str, Any]) -> str:
    row = metadata.get(paper_id, {})
    if isinstance(row, dict) and row.get("title"):
        return str(row["title"])
    return next((line.strip() for line in source_text.splitlines() if line.strip()), paper_id)


def _claim_entities(record: dict[str, Any], title: str) -> tuple[list[EvidenceEntity], list[EvidenceRelation], list[dict[str, str]]]:
    paper_id = str(record["paper_id"])
    paper_entity_id = f"paper:{paper_id}"
    entities = [EvidenceEntity(
        entity_id=paper_entity_id,
        entity_type="paper",
        name=title,
        description=f"Materials-science paper {paper_id}",
        source_paper_id=paper_id,
        attributes={"paper_id": paper_id},
    )]
    relations: list[EvidenceRelation] = []
    prompts: list[dict[str, str]] = []
    for role, items in record.get("reconciled_by_role", {}).items():
        for index, item in enumerate(items):
            content = str(item.get("content", "")).strip()
            if not content:
                continue
            claim_id = f"{paper_id}::{role}::{index}"
            spans = [str(value) for value in item.get("evidence_spans", []) if value]
            evidence = spans[0] if spans else content
            entities.append(EvidenceEntity(
                entity_id=claim_id,
                entity_type="atomic_claim",
                name=content[:160],
                description=content,
                source_paper_id=paper_id,
                evidence_span=evidence,
                attributes={"role": role, "evidence_spans": spans, "conflicting": bool(item.get("conflicting"))},
            ))
            relations.append(EvidenceRelation(
                relation_id=_stable_id("relation", "derived_from", claim_id, paper_entity_id),
                relation_type="derived_from",
                source_entity_id=claim_id,
                target_entity_ids=[paper_entity_id],
                source_paper_id=paper_id,
                evidence_span=evidence,
            ))
            if role == "hypothesis_statement":
                hypothesis_id = _stable_id("hypothesis", paper_id, claim_id)
                entities.append(EvidenceEntity(
                    entity_id=hypothesis_id,
                    entity_type="hypothesis",
                    name=content[:160],
                    description=content,
                    source_paper_id=paper_id,
                    evidence_span=evidence,
                    attributes={"claim_id": claim_id, "origin": "paper_hypothesis"},
                ))
                relations.append(EvidenceRelation(
                    relation_id=_stable_id("relation", "derived_from", hypothesis_id, claim_id),
                    relation_type="derived_from",
                    source_entity_id=hypothesis_id,
                    target_entity_ids=[claim_id],
                    source_paper_id=paper_id,
                    evidence_span=evidence,
                ))
            prompts.append({"claim_id": claim_id, "role": role, "content": content, "evidence": evidence})
    return entities, relations, prompts


_ELEMENT_RE = re.compile(r"^\s*(?P<kind>Figure|Fig\.?|Table)\s*(?P<label>[A-Z]?\d+[A-Za-z]?)\s*[:.\-]?\s*(?P<caption>.*)$", re.I | re.M)


def _source_elements(paper_id: str, source_text: str) -> tuple[list[EvidenceEntity], list[EvidenceRelation]]:
    entities: list[EvidenceEntity] = []
    relations: list[EvidenceRelation] = []
    seen: set[tuple[str, str]] = set()
    for match in _ELEMENT_RE.finditer(source_text):
        kind = "table" if match.group("kind").lower().startswith("table") else "figure"
        label = match.group("label")
        key = (kind, label.lower())
        if key in seen:
            continue
        seen.add(key)
        caption = match.group("caption").strip()
        source_element = f"{kind.title()} {label}"
        entity_id = _stable_id("figure_table", paper_id, kind, label.lower())
        evidence = match.group(0).strip()
        entities.append(EvidenceEntity(
            entity_id=entity_id,
            entity_type="figure_table",
            name=f"{source_element}: {caption}".rstrip(": "),
            description=caption,
            source_paper_id=paper_id,
            evidence_span=evidence,
            source_element=source_element,
            attributes={"kind": kind, "label": label},
            confidence=0.9 if caption else 0.7,
        ))
        relations.append(EvidenceRelation(
            relation_id=_stable_id("relation", "derived_from", entity_id, f"paper:{paper_id}"),
            relation_type="derived_from",
            source_entity_id=entity_id,
            target_entity_ids=[f"paper:{paper_id}"],
            source_paper_id=paper_id,
            evidence_span=evidence,
            source_element=source_element,
        ))
    return entities, relations


def _citation_relations(paper_id: str, source_text: str, titles: dict[str, str]) -> list[EvidenceRelation]:
    normalized_source = _normalize_text(source_text)
    relations = []
    for target_id, title in titles.items():
        if target_id == paper_id:
            continue
        normalized_title = _normalize_text(title)
        if len(normalized_title) < 24 or normalized_title not in normalized_source:
            continue
        relations.append(EvidenceRelation(
            relation_id=_stable_id("relation", "cites", paper_id, target_id),
            relation_type="cites",
            source_entity_id=f"paper:{paper_id}",
            target_entity_ids=[f"paper:{target_id}"],
            source_paper_id=paper_id,
            evidence_span=title,
            source_element="References",
            confidence=0.9,
        ))
    return relations


_ARXIV_RE = re.compile(r"(?:arXiv\s*:\s*|arxiv\.org/(?:abs|pdf)/)(\d{4}\.\d{4,5})", re.I)
_DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)


def _external_citations(paper_id: str, source_text: str) -> tuple[list[EvidenceEntity], list[EvidenceRelation]]:
    reference_match = re.search(r"^\s*(?:References|Bibliography)\s*$", source_text, re.I | re.M)
    if not reference_match:
        return [], []
    references = source_text[reference_match.end():]
    citations: dict[str, tuple[str, str]] = {}
    for match in _ARXIV_RE.finditer(references):
        identifier = match.group(1)
        if identifier != paper_id:
            citations[f"paper:arxiv:{identifier}"] = (f"arXiv:{identifier}", match.group(0))
    for match in _DOI_RE.finditer(references):
        doi = match.group(0).rstrip(".,;)")
        citations[f"paper:doi:{doi.lower()}"] = (doi, match.group(0))

    entities = []
    relations = []
    for entity_id, (name, evidence) in sorted(citations.items()):
        entities.append(EvidenceEntity(
            entity_id=entity_id,
            entity_type="paper",
            name=name,
            description="External paper cited in the source paper's references",
            source_paper_id=paper_id,
            evidence_span=evidence,
            source_element="References",
            attributes={"external": True},
            confidence=0.95,
        ))
        relations.append(EvidenceRelation(
            relation_id=_stable_id("relation", "cites", paper_id, entity_id),
            relation_type="cites",
            source_entity_id=f"paper:{paper_id}",
            target_entity_ids=[entity_id],
            source_paper_id=paper_id,
            evidence_span=evidence,
            source_element="References",
            confidence=0.95,
        ))
    return entities, relations


def _semantic_annotations(paper_id: str, claims: list[dict[str, str]]) -> tuple[list[EvidenceEntity], list[EvidenceRelation]]:
    entities: list[EvidenceEntity] = []
    relations: list[EvidenceRelation] = []
    for start in range(0, len(claims), BATCH_SIZE):
        batch = claims[start:start + BATCH_SIZE]
        result = resilient_chat_json(_NORMALIZE_SYSTEM, json.dumps({"claims": batch}), max_tokens=8000)
        if not isinstance(result, dict) or not isinstance(result.get("annotations"), list):
            raise RuntimeError(f"semantic normalization failed for {paper_id} batch {start // BATCH_SIZE + 1}")
        claim_ids = {row["claim_id"] for row in batch}
        for annotation in result["annotations"]:
            if not isinstance(annotation, dict) or annotation.get("claim_id") not in claim_ids:
                continue
            claim_id = str(annotation["claim_id"])
            evidence_by_local_id: dict[str, str] = {}
            for row in annotation.get("entities", []):
                if not isinstance(row, dict) or str(row.get("type", "")).lower() not in SEMANTIC_TYPES or not row.get("name"):
                    continue
                entity_type = str(row["type"]).lower()
                local_id = str(row.get("local_id", row["name"]))
                entity_id = _stable_id(entity_type, paper_id, claim_id, local_id, str(row["name"]))
                evidence_by_local_id[local_id] = entity_id
                confidence = max(0.0, min(float(row.get("confidence", 0.7)), 1.0))
                entities.append(EvidenceEntity(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    name=str(row["name"]),
                    description=str(row.get("description", "")),
                    source_paper_id=paper_id,
                    evidence_span=str(row.get("evidence_span", "")),
                    attributes=dict(row.get("attributes", {})),
                    confidence=confidence,
                ))
                relations.append(EvidenceRelation(
                    relation_id=_stable_id("relation", "derived_from", entity_id, claim_id),
                    relation_type="derived_from",
                    source_entity_id=entity_id,
                    target_entity_ids=[claim_id],
                    source_paper_id=paper_id,
                    evidence_span=str(row.get("evidence_span", "")),
                    confidence=confidence,
                ))
            for row in annotation.get("relations", []):
                if not isinstance(row, dict) or str(row.get("type", "")).lower() not in SEMANTIC_RELATIONS:
                    continue
                source = evidence_by_local_id.get(str(row.get("source")), str(row.get("source", "")))
                target = evidence_by_local_id.get(str(row.get("target")), str(row.get("target", "")))
                if source not in claim_ids | set(evidence_by_local_id.values()) or target not in claim_ids | set(evidence_by_local_id.values()):
                    continue
                relation_type = str(row["type"]).lower()
                confidence = max(0.0, min(float(row.get("confidence", 0.7)), 1.0))
                relations.append(EvidenceRelation(
                    relation_id=_stable_id("relation", relation_type, source, target, str(start)),
                    relation_type=relation_type,
                    source_entity_id=source,
                    target_entity_ids=[target],
                    source_paper_id=paper_id,
                    evidence_span=str(row.get("evidence_span", "")),
                    source_element=str(row.get("source_element", "")),
                    metric=str(row.get("metric", "")),
                    subject_value=row.get("subject_value"),
                    reference_value=row.get("reference_value"),
                    unit=str(row.get("unit", "")),
                    conditions=dict(row.get("conditions", {})),
                    confidence=confidence,
                ))
    return entities, relations


def _deterministic_annotations(paper_id: str, claims: list[dict[str, str]]) -> tuple[list[EvidenceEntity], list[EvidenceRelation]]:
    entities: list[EvidenceEntity] = []
    relations: list[EvidenceRelation] = []
    claims_by_role: dict[str, list[dict[str, str]]] = {}
    for claim in claims:
        claims_by_role.setdefault(claim["role"], []).append(claim)

    def add_entity(claim: dict[str, str], entity_type: str, name: str, attributes: dict[str, Any] | None = None) -> str:
        entity_id = _stable_id(entity_type, paper_id, claim["claim_id"], name)
        entities.append(EvidenceEntity(
            entity_id=entity_id,
            entity_type=entity_type,
            name=name[:200],
            description=claim["content"],
            source_paper_id=paper_id,
            evidence_span=claim["evidence"],
            attributes=attributes or {},
            confidence=0.7,
        ))
        relations.append(EvidenceRelation(
            relation_id=_stable_id("relation", "derived_from", entity_id, claim["claim_id"]),
            relation_type="derived_from",
            source_entity_id=entity_id,
            target_entity_ids=[claim["claim_id"]],
            source_paper_id=paper_id,
            evidence_span=claim["evidence"],
            confidence=0.7,
        ))
        return entity_id

    property_by_claim: dict[str, str] = {}
    method_by_claim: dict[str, str] = {}
    for claim in claims:
        role = claim["role"]
        content = claim["content"]
        evidence = claim["evidence"]
        if role in {"prior_approach", "rejected_alternative", "inspiration_source"}:
            method_id = add_entity(claim, "method", content)
            method_by_claim[claim["claim_id"]] = method_id
            relations.append(EvidenceRelation(
                relation_id=_stable_id("relation", "uses_method", claim["claim_id"], method_id),
                relation_type="uses_method",
                source_entity_id=claim["claim_id"],
                target_entity_ids=[method_id],
                source_paper_id=paper_id,
                evidence_span=evidence,
                confidence=0.7,
            ))
        if _MATERIAL_TERMS.search(f"{content} {evidence}"):
            add_entity(claim, "material_system", content)
        if role in {"causal_claim", "mechanism_principle", "hypothesis_statement", "evidence_result"}:
            property_by_claim[claim["claim_id"]] = add_entity(claim, "property", content)
        condition_match = _CONDITION_RE.search(evidence)
        if condition_match:
            condition = condition_match.group(0)
            condition_id = add_entity(claim, "experimental_condition", condition, {"text": condition})
            relations.append(EvidenceRelation(
                relation_id=_stable_id("relation", "applies_under", claim["claim_id"], condition_id),
                relation_type="applies_under",
                source_entity_id=claim["claim_id"],
                target_entity_ids=[condition_id],
                source_paper_id=paper_id,
                evidence_span=evidence,
                conditions={"text": condition},
                confidence=0.8,
            ))
        if role == "evidence_result":
            measurement_id = add_entity(claim, "measurement", content, {"qualitative_result": content})
            property_id = property_by_claim[claim["claim_id"]]
            relations.append(EvidenceRelation(
                relation_id=_stable_id("relation", "measures", measurement_id, property_id),
                relation_type="measures",
                source_entity_id=measurement_id,
                target_entity_ids=[property_id],
                source_paper_id=paper_id,
                evidence_span=evidence,
                confidence=0.75,
            ))
        if re.search(r"\b(dataset|data set|database|corpus|training data|experimental data)\b", f"{content} {evidence}", re.I):
            add_entity(claim, "dataset", content)

    def best_target(source: dict[str, str], roles: set[str]) -> dict[str, str] | None:
        source_terms = set(_normalize_text(source["content"]).split())
        candidates = [item for role in roles for item in claims_by_role.get(role, []) if item["claim_id"] != source["claim_id"]]
        return max(candidates, key=lambda item: len(source_terms & set(_normalize_text(item["content"]).split())), default=None)

    for claim in claims:
        relation_type = None
        target_roles: set[str] = set()
        if claim["role"] == "evidence_result":
            relation_type, target_roles = "supports", {"hypothesis_statement", "causal_claim", "mechanism_principle"}
        elif claim["role"] == "contradiction":
            relation_type, target_roles = "contradicts", {"prior_approach", "hypothesis_statement", "causal_claim"}
        elif claim["role"] == "inspiration_source":
            relation_type, target_roles = "analogous_to", {"hypothesis_statement", "mechanism_principle"}
        target = best_target(claim, target_roles) if relation_type else None
        if target:
            relations.append(EvidenceRelation(
                relation_id=_stable_id("relation", relation_type, claim["claim_id"], target["claim_id"]),
                relation_type=relation_type,
                source_entity_id=claim["claim_id"],
                target_entity_ids=[target["claim_id"]],
                source_paper_id=paper_id,
                evidence_span=claim["evidence"],
                confidence=0.6,
            ))
        comparison = re.search(r"\b(outperform\w*|underperform\w*|compared with|compared to|versus|higher than|lower than)\b", claim["evidence"], re.I)
        if comparison:
            target = best_target(claim, {"prior_approach", "evidence_result"})
            if target:
                phrase = comparison.group(1).lower()
                negated_outperformance = bool(re.search(r"\b(?:not|does not|did not)\s+outperform", claim["evidence"], re.I))
                relation_type = "outperforms" if phrase.startswith("outperform") and not negated_outperformance else (
                    "underperforms" if phrase.startswith("underperform") else "compares_with"
                )
                relations.append(EvidenceRelation(
                    relation_id=_stable_id("relation", relation_type, claim["claim_id"], target["claim_id"]),
                    relation_type=relation_type,
                    source_entity_id=claim["claim_id"],
                    target_entity_ids=[target["claim_id"]],
                    source_paper_id=paper_id,
                    evidence_span=claim["evidence"],
                    confidence=0.55,
                ))
    return entities, relations


def build_paper(record_path: Path, source_path: Path | None, title: str, normalizer: str = "llm") -> dict[str, Any]:
    record = json.loads(record_path.read_text())
    paper_id = str(record["paper_id"])
    source_text = source_path.read_text(errors="ignore") if source_path and source_path.exists() else ""
    entities, relations, claims = _claim_entities(record, title)
    source_entities, source_relations = _source_elements(paper_id, source_text)
    citation_entities, citation_relations = _external_citations(paper_id, source_text)
    if normalizer == "llm":
        semantic_entities, semantic_relations = _semantic_annotations(paper_id, claims)
    elif normalizer == "deterministic":
        semantic_entities, semantic_relations = _deterministic_annotations(paper_id, claims)
    else:
        raise ValueError(f"unknown normalizer={normalizer!r}")
    entities.extend(source_entities)
    entities.extend(citation_entities)
    entities.extend(semantic_entities)
    relations.extend(source_relations)
    relations.extend(citation_relations)
    relations.extend(semantic_relations)
    return {"paper_id": paper_id, "entities": [asdict(value) for value in entities], "relations": [asdict(value) for value in relations]}


def _validate_bundle(bundle: dict[str, Any]) -> None:
    entity_ids = set()
    for row in bundle["entities"]:
        entity = EvidenceEntity.from_dict(row)
        if entity.entity_id in entity_ids:
            raise ValueError(f"duplicate entity_id={entity.entity_id}")
        entity_ids.add(entity.entity_id)
    relation_ids = set()
    for row in bundle["relations"]:
        relation = EvidenceRelation.from_dict(row)
        if relation.relation_id in relation_ids:
            raise ValueError(f"duplicate relation_id={relation.relation_id}")
        relation_ids.add(relation.relation_id)
        missing = {relation.source_entity_id, *relation.target_entity_ids} - entity_ids
        if missing:
            raise ValueError(f"relation {relation.relation_id} references missing entities: {sorted(missing)}")


def aggregate(output_dir: Path, titles: dict[str, str], source_dir: Path | None, normalizer: str = "unknown") -> tuple[int, int]:
    bundles = [json.loads(path.read_text()) for path in sorted((output_dir / "papers").glob("*.json"))]
    all_entities = [row for bundle in bundles for row in bundle["entities"]]
    all_relations = [row for bundle in bundles for row in bundle["relations"]]
    if source_dir:
        for bundle in bundles:
            paper_id = bundle["paper_id"]
            source_path = source_dir / f"{paper_id}.txt"
            if source_path.exists():
                all_relations.extend(asdict(value) for value in _citation_relations(paper_id, source_path.read_text(errors="ignore"), titles))
    all_entities = list({row["entity_id"]: row for row in all_entities}.values())
    entity_ids = {row["entity_id"] for row in all_entities}
    all_relations = [row for row in all_relations if row["source_entity_id"] in entity_ids and all(target in entity_ids for target in row["target_entity_ids"])]
    unique_relations = {row["relation_id"]: row for row in all_relations}
    (output_dir / "entities.jsonl").write_text("".join(json.dumps(row) + "\n" for row in all_entities))
    (output_dir / "relations.jsonl").write_text("".join(json.dumps(row) + "\n" for row in unique_relations.values()))
    summary = {
        "papers": len(bundles),
        "entities": len(all_entities),
        "relations": len(unique_relations),
        "entity_types": {kind: sum(row["entity_type"] == kind for row in all_entities) for kind in sorted(ENTITY_TYPES)},
        "relation_types": {kind: sum(row["relation_type"] == kind for row in unique_relations.values()) for kind in sorted(RELATION_TYPES)},
        "provider": provider_info(),
        "normalizer": normalizer,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    return len(all_entities), len(unique_relations)


def validate_corpus(output_dir: Path, expected_papers: int | None = None) -> dict[str, Any]:
    entity_path = output_dir / "entities.jsonl"
    relation_path = output_dir / "relations.jsonl"
    entities = [EvidenceEntity.from_dict(json.loads(line)) for line in entity_path.read_text().splitlines() if line.strip()]
    relations = [EvidenceRelation.from_dict(json.loads(line)) for line in relation_path.read_text().splitlines() if line.strip()]
    entity_ids = {entity.entity_id for entity in entities}
    if len(entity_ids) != len(entities):
        raise ValueError("aggregate contains duplicate entity IDs")
    missing = {
        entity_id
        for relation in relations
        for entity_id in [relation.source_entity_id, *relation.target_entity_ids]
        if entity_id not in entity_ids
    }
    if missing:
        raise ValueError(f"aggregate relations reference {len(missing)} missing entities")
    paper_count = sum(
        entity.entity_type == "paper" and not entity.attributes.get("external")
        for entity in entities
    )
    if expected_papers is not None and paper_count != expected_papers:
        raise ValueError(f"expected {expected_papers} papers, found {paper_count}")
    return {
        "papers": paper_count,
        "entities": len(entities),
        "relations": len(relations),
        "entity_types": {kind: sum(entity.entity_type == kind for entity in entities) for kind in sorted(ENTITY_TYPES)},
        "relation_types": {kind: sum(relation.relation_type == kind for relation in relations) for kind in sorted(RELATION_TYPES)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outputs-dir", required=True, type=Path)
    parser.add_argument("--graph-dir", required=True, type=Path)
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--normalizer", choices=("deterministic", "llm"), default="deterministic")
    parser.add_argument("--max-passes", type=int, default=1, help="0 retries until all papers succeed")
    parser.add_argument("--retry-delay", type=int, default=120)
    args = parser.parse_args()

    metadata = json.loads(args.metadata.read_text()) if args.metadata else {}
    args.graph_dir.mkdir(parents=True, exist_ok=True)
    paper_dir = args.graph_dir / "papers"
    paper_dir.mkdir(exist_ok=True)
    records = sorted(args.outputs_dir.glob("*.json"))
    source_texts = {path.stem: path.read_text(errors="ignore") for path in args.source_dir.glob("*.txt")} if args.source_dir else {}
    titles = {
        record.stem: _title_from_source(record.stem, source_texts.get(record.stem, ""), metadata)
        for record in records
    }

    pass_number = 0
    while True:
        pass_number += 1
        pending = [record for record in records if not (paper_dir / record.name).exists()]
        if not pending:
            break
        print(f"[evidence] pass={pass_number} pending={len(pending)}", file=sys.stderr)
        for record_path in pending:
            paper_id = record_path.stem
            source_path = args.source_dir / f"{paper_id}.txt" if args.source_dir else None
            try:
                bundle = build_paper(record_path, source_path, titles[paper_id], args.normalizer)
                _validate_bundle(bundle)
                destination = paper_dir / record_path.name
                temporary = destination.with_suffix(".json.tmp")
                temporary.write_text(json.dumps(bundle, indent=2))
                temporary.replace(destination)
                print(f"[evidence] {paper_id}: entities={len(bundle['entities'])} relations={len(bundle['relations'])}", file=sys.stderr)
            except Exception as error:  # noqa: BLE001 - retry this paper next pass
                print(f"[evidence] ERROR {paper_id}: {error}", file=sys.stderr)
        remaining = sum(not (paper_dir / record.name).exists() for record in records)
        if not remaining:
            break
        if args.max_passes and pass_number >= args.max_passes:
            raise SystemExit(f"{remaining} papers remain after {pass_number} passes")
        print(f"[evidence] {remaining} remain; retrying in {args.retry_delay}s", file=sys.stderr)
        time.sleep(args.retry_delay)

    entity_count, relation_count = aggregate(args.graph_dir, titles, args.source_dir, args.normalizer)
    validate_corpus(args.graph_dir, expected_papers=len(records))
    print(f"[evidence] complete papers={len(records)} entities={entity_count} relations={relation_count}")


if __name__ == "__main__":
    main()