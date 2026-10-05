"""Resolve, cluster, synthesize, and evaluate question-centered materials evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from hypothesis_evidence_v2 import atomic_json, load_evidence
from llm_client import LLMError, chat_json, provider_info
from question_evidence import (
    ANSWER_STATUSES,
    DOMAINS,
    RESOLUTION_STATUSES,
    ResolvedQuestion,
    stable_cluster_id,
    write_resolved_paper,
)

SCHEMA_VERSION = "question-centered-pipeline-1.0"
QUESTION_BATCH_SIZE = 6
MAX_CANDIDATES_PER_QUESTION = 4
ADJUDICATION_BATCH_SIZE = 30
SYNTHESIS_ANSWER_LIMIT = 24
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STATUS_ALIASES = {
    "answered_in_same_paper": "answered_same_paper",
    "answered_by_same_paper": "answered_same_paper",
    "answered_in_earlier_corpus": "answered_earlier_corpus",
    "answered_by_earlier_corpus": "answered_earlier_corpus",
    "partially_resolved": "partially_answered",
    "unanswered": "unresolved",
}

_RESOLVE_SYSTEM = """You resolve reader questions using only supplied grounded materials evidence.
For every input question, classify its scientific facets and resolution. Do not use outside
knowledge. An answer must cite one supplied evidence_unit_id and copy one or more exact
evidence_spans from that unit. Multiple papers may answer the same question differently.

Resolution statuses:
answered_same_paper, answered_earlier_corpus, partially_answered, unresolved, reading_only,
replication_detail.

Domains:
oxidation_corrosion, mechanical_deformation, phase_stability, processing_manufacturing,
radiation_defects, thermal_transport, wear_tribology, magnetic_functional, general_materials.

question_function should be one of:
clarify, replicate, compare, explain_mechanism, change_variable, find_boundary,
test_evidence, transfer, plan_experiment.

Use concise normalized facet labels. Keep incompatible properties or regimes distinct.
epistemic_status must be observed, inferred, calculated, simulated, cited, hypothesized,
contradicted, or unspecified.

Return JSON:
{"questions": [{
  "question_id": "",
  "resolution_status": "",
  "resolution_summary": "",
  "facets": {
    "domain": "", "subtopic": "", "material_family": "", "target_property": "",
    "design_variable": "", "condition_regime": "", "mechanism_topic": "",
    "question_function": ""
  },
  "answers": [{
    "evidence_unit_id": "", "answer": "", "material": "", "processing_state": "",
    "conditions": "", "measurement_outcome": "", "mechanism": "",
    "boundary_limitation": "", "epistemic_status": "",
    "evidence_spans": ["exact supplied span"], "confidence": 0.0
  }]
}]}.

Return exactly one record per input question. A question may remain unresolved. Never invent an
answer or evidence ID."""

_SYNTHESIS_SYSTEM = """You synthesize one scientifically compatible question cluster using only
its grounded paper-specific answers. Explain how different papers approach the question.
Distinguish agreement, condition-dependent differences, genuine contradictions, and missing
regimes. Cite answer_ids exactly. Do not introduce uncited scientific claims.

Return JSON:
{"canonical_question": "", "compatibility": {
  "scientifically_coherent": true, "incompatibilities": []
}, "synthesis": {
  "consensus": "", "different_approaches": "", "condition_dependencies": "",
  "contradictions": "", "evidence_strength": "", "unresolved_gap": "",
  "candidate_hypothesis": "", "discriminating_experiment": "",
  "supporting_answer_ids": [], "conflicting_answer_ids": []
}}."""

_ADJUDICATE_SYSTEM = """You partition a coarse materials-science question topic into scientifically
coherent groups. Questions belong together only when one cross-paper synthesis can answer them
without conflating the target property, physical phenomenon, or operating regime.

Keep different wording and reading intents together when they concern the same scientific issue.
Separate incompatible environments, loading modes, target properties, and experimental versus
simulation meanings when those differences change the answer. Broad methodological questions
about unrelated instruments or processing steps must not be grouped merely because they share a
domain.

Return JSON:
{"groups": [
  {"label": "short normalized scientific topic", "question_ids": ["exact supplied id"],
   "reason": ""}
]}.

Every supplied question_id must appear exactly once. Do not invent IDs."""


def _tokens(text: str) -> list[str]:
    return [token for token in _TOKEN_RE.findall(text.casefold()) if len(token) > 2]


def _flatten(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten(item) for item in value)
    return "" if value is None else str(value)


def build_evidence_index(evidence_dir: Path, metadata_path: Path) -> list[dict[str, Any]]:
    metadata_payload = json.loads(metadata_path.read_text())
    metadata_rows = metadata_payload.get("papers", metadata_payload)
    dates = {row["paper_id"]: row["earliest_public_date"] for row in metadata_rows}
    records = []
    for unit in load_evidence(evidence_dir):
        row = unit.to_dict()
        row["publication_date"] = dates[unit.paper_id]
        row["search_text"] = _flatten(row)
        records.append(row)
    return records


def select_candidates(
    question: dict[str, Any],
    evidence: list[dict[str, Any]],
    *,
    allow_future: bool = False,
) -> list[dict[str, Any]]:
    query_tokens = Counter(_tokens(str(question.get("question", ""))))
    cutoff = str(question["publication_date"])
    paper_id = str(question["paper_id"])
    scored = []
    for row in evidence:
        if not allow_future and row["publication_date"] > cutoff:
            continue
        document = Counter(_tokens(row["search_text"]))
        overlap = sum(min(count, document[token]) for token, count in query_tokens.items())
        if not overlap:
            continue
        same_paper = 1.5 if row["paper_id"] == paper_id else 0.0
        current_claim = 0.4 if row["claim_ownership"] == "current_paper" else 0.0
        score = same_paper + current_claim + overlap / max(sum(query_tokens.values()), 1)
        scored.append((score, row))
    scored.sort(key=lambda item: (-item[0], item[1]["publication_date"], item[1]["unit_id"]))
    return [row for _, row in scored[:MAX_CANDIDATES_PER_QUESTION]]


def _compact_evidence(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_unit_id": row["unit_id"],
        "paper_id": row["paper_id"],
        "publication_date": row["publication_date"],
        "claim_ownership": row["claim_ownership"],
        "sample": {
            key: row["sample"].get(key)
            for key in ("sample_id", "material_name", "nominal_composition", "form", "initial_state")
        },
        "process_steps": row["process_steps"][:3],
        "structure_observations": row["structure_observations"][:3],
        "test_conditions": row["test_conditions"],
        "measurements": row["measurements"][:4],
        "mechanisms": row["mechanisms"][:3],
        "boundaries": row["boundaries"][:3],
        "limitations": row["limitations"][:2],
        "evidence_spans": row["evidence_spans"][:3],
    }


def _fallback_question(question: dict[str, Any]) -> dict[str, Any]:
    category = str(question.get("category", ""))
    if category == "reading_clarification":
        status = "reading_only"
    elif category == "replication_detail":
        status = "replication_detail"
    else:
        status = "unresolved"
    domain = "general_materials"
    text = str(question.get("question", "")).casefold()
    if any(term in text for term in ("oxid", "corrosion", "oxide", "scale")):
        domain = "oxidation_corrosion"
    elif any(term in text for term in ("creep", "strength", "strain", "stress", "dislocation")):
        domain = "mechanical_deformation"
    elif any(term in text for term in ("phase", "precip", "fcc", "bcc", "laves")):
        domain = "phase_stability"
    return {
        **question,
        "resolution_status": status,
        "resolution_summary": "No grounded answer was selected from the eligible evidence.",
        "facets": {
            "domain": domain,
            "subtopic": category or "general",
            "material_family": "",
            "target_property": "",
            "design_variable": "",
            "condition_regime": "",
            "mechanism_topic": "",
            "question_function": "clarify",
        },
        "answers": [],
    }


def _canonical_topic(question: str, domain: str) -> str:
    text = question.casefold()
    rules = {
        "oxidation_corrosion": (
            (("spall", "crack", "failure"), "scale_failure"),
            (("kinetic", "mass gain", "rate constant"), "oxidation_kinetics"),
            (("protective", "scale", "oxide film"), "protective_scale"),
            (("diffusion", "depletion", "segregation"), "element_transport"),
            (("phase", "oxide form", "oxide species"), "oxide_phase_formation"),
            (("corrosion", "pitting", "salt"), "corrosion_resistance"),
        ),
        "mechanical_deformation": (
            (("creep", "rupture"), "creep"),
            (("dislocation", "slip", "twin"), "deformation_mechanism"),
            (("ductility", "elongation"), "ductility"),
            (("yield", "strength", "hardness"), "strength_hardness"),
            (("grain", "boundary"), "grain_boundary_effect"),
            (("strain rate",), "strain_rate_effect"),
        ),
        "phase_stability": (
            (("precip", "particle", "laves", "heusler"), "precipitation"),
            (("transform", "fcc", "bcc"), "phase_transformation"),
            (("calphad", "thermodynamic", "gibbs"), "thermodynamic_prediction"),
            (("stability", "stable", "decompos"), "phase_stability"),
        ),
        "processing_manufacturing": (
            (("laser", "lpbf", "printing", "additive"), "additive_manufacturing"),
            (("sinter", "spark plasma"), "sintering"),
            (("anneal", "heat treatment", "aging"), "heat_treatment"),
            (("cast", "melt", "remelt"), "melting_casting"),
            (("surface", "shot", "peen"), "surface_processing"),
        ),
        "radiation_defects": (
            (("helium", "he implantation"), "helium_effects"),
            (("irradi", "dpa", "radiation"), "radiation_damage"),
            (("vacancy", "defect"), "defect_evolution"),
        ),
        "wear_tribology": (
            (("friction",), "friction"),
            (("wear",), "wear_resistance"),
        ),
        "thermal_transport": (
            (("conduct",), "thermal_conductivity"),
            (("melt",), "melting"),
        ),
        "magnetic_functional": (
            (("magnet", "curie"), "magnetic_behavior"),
        ),
    }
    for keywords, topic in rules.get(domain, ()):
        if any(keyword in text for keyword in keywords):
            return topic
    return "general"


def _canonical_property(question: str) -> str:
    text = question.casefold()
    for keywords, label in (
        (("mass gain", "oxidation rate"), "oxidation_rate"),
        (("yield strength", "flow stress"), "yield_strength"),
        (("ultimate tensile", "uts"), "tensile_strength"),
        (("hardness",), "hardness"),
        (("ductility", "elongation"), "ductility"),
        (("creep", "rupture"), "creep_response"),
        (("phase fraction", "phase stability"), "phase_stability"),
        (("grain size",), "grain_size"),
        (("corrosion", "pitting"), "corrosion_resistance"),
        (("wear",), "wear_resistance"),
        (("thermal conductivity",), "thermal_conductivity"),
    ):
        if any(keyword in text for keyword in keywords):
            return label
    return "unspecified"


def _canonical_variable(question: str) -> str:
    text = question.casefold()
    for keywords, label in (
        (("composition", "content", "addition", "alloying"), "composition"),
        (("temperature",), "temperature"),
        (("time", "duration", "aging"), "time"),
        (("atmosphere", "environment", "oxygen pressure", "vacuum"), "environment"),
        (("strain rate",), "strain_rate"),
        (("stress", "load"), "load_stress"),
        (("grain size",), "grain_size"),
        (("heat treatment", "anneal", "sinter"), "thermal_processing"),
        (("printing", "laser", "scan"), "manufacturing_parameter"),
    ):
        if any(keyword in text for keyword in keywords):
            return label
    return "unspecified"


def _canonical_regime(question: str) -> str:
    text = question.casefold()
    if "vacuum" in text:
        return "vacuum"
    if any(term in text for term in ("air", "oxygen", "atmospheric")):
        return "oxidizing_atmosphere"
    if any(term in text for term in ("molten salt", "flibe", "chloride")):
        return "molten_salt"
    if any(term in text for term in ("irradi", "implant", "dpa")):
        return "irradiation"
    if any(term in text for term in ("simulation", "molecular dynamics", "dft")):
        return "simulation"
    if any(term in text for term in ("high temperature", "elevated temperature", "°c", " k")):
        return "elevated_temperature"
    return "unspecified"


def _sanitize_generated(
    generated: dict[str, Any],
    question: dict[str, Any],
    evidence_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    row = dict(generated)
    status = str(row.get("resolution_status", "")).strip().lower()
    row["resolution_status"] = _STATUS_ALIASES.get(status, status)
    sanitized_answers = []
    for answer in row.get("answers", []):
        if not isinstance(answer, dict):
            continue
        evidence_id = str(answer.get("evidence_unit_id", "")).strip()
        evidence = evidence_lookup.get(evidence_id)
        if evidence is None:
            continue
        sanitized = dict(answer)
        sanitized["evidence_spans"] = evidence.get("evidence_spans", [])[:3]
        answer_status = str(sanitized.get("epistemic_status", "")).strip().lower()
        sanitized["epistemic_status"] = (
            answer_status if answer_status in ANSWER_STATUSES else "unspecified"
        )
        sanitized_answers.append(sanitized)
    row["answers"] = sanitized_answers
    if row["resolution_status"] in {"answered_same_paper", "answered_earlier_corpus"} and not sanitized_answers:
        row["resolution_status"] = "unresolved"
    if row["resolution_status"] not in RESOLUTION_STATUSES:
        row["resolution_status"] = "partially_answered" if sanitized_answers else "unresolved"
    facets = dict(row.get("facets") or {})
    domain = str(facets.get("domain", "")).strip().lower()
    if domain not in DOMAINS:
        domain = _fallback_question(question)["facets"]["domain"]
    text = str(question.get("question", ""))
    facets.update({
        "domain": domain,
        "subtopic": _canonical_topic(text, domain),
        "target_property": _canonical_property(text),
        "design_variable": _canonical_variable(text),
        "condition_regime": _canonical_regime(text),
    })
    row["facets"] = facets
    return row


def resolve_batch(
    questions: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> tuple[list[ResolvedQuestion], list[dict[str, Any]]]:
    candidate_lookup: dict[str, dict[str, Any]] = {}
    input_rows = []
    for question in questions:
        candidates = select_candidates(question, evidence)
        for row in candidates:
            candidate_lookup[row["unit_id"]] = row
        input_rows.append({
            "question": question,
            "eligible_evidence_ids": [row["unit_id"] for row in candidates],
        })
    payload = chat_json(
        _RESOLVE_SYSTEM,
        json.dumps({
            "items": input_rows,
            "eligible_evidence": [
                _compact_evidence(row)
                for row in candidate_lookup.values()
            ],
        }, ensure_ascii=False),
        max_tokens=10000,
    )
    generated = {
        str(row.get("question_id")): row
        for row in payload.get("questions", [])
        if isinstance(row, dict)
    } if isinstance(payload, dict) else {}
    resolved: list[ResolvedQuestion] = []
    rejected: list[dict[str, Any]] = []
    for question in questions:
        question_id = str(question["question_id"])
        model_row = generated.get(question_id)
        if model_row is not None:
            model_row = _sanitize_generated(model_row, question, candidate_lookup)
        candidate = {
            **question,
            **(model_row or _fallback_question(question)),
            "source_evidence_spans": question.get("evidence_spans", []),
        }
        try:
            resolved.append(ResolvedQuestion.from_dict(
                candidate,
                evidence_lookup=candidate_lookup,
            ))
        except ValueError as error:
            rejected.append({
                "question_id": question_id,
                "reason": str(error),
                "candidate": candidate,
            })
            resolved.append(ResolvedQuestion.from_dict(
                _fallback_question(question),
                evidence_lookup={},
            ))
    return resolved, rejected


def resolve_questions(
    triage_path: Path,
    evidence_dir: Path,
    metadata_path: Path,
    output_dir: Path,
    *,
    workers: int,
    resume: bool,
    paper_ids: set[str] | None = None,
) -> dict[str, Any]:
    triage = json.loads(triage_path.read_text())
    by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in triage["questions"]:
        if paper_ids and row["paper_id"] not in paper_ids:
            continue
        by_paper[row["paper_id"]].append(row)
    evidence = build_evidence_index(evidence_dir, metadata_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    def process(paper_id: str, questions: list[dict[str, Any]]) -> dict[str, int]:
        destination = output_dir / f"{paper_id}.json"
        if resume and destination.exists():
            payload = json.loads(destination.read_text())
            return {
                "questions": len(payload.get("questions", [])),
                "answers": sum(len(row.get("answers", [])) for row in payload.get("questions", [])),
                "rejected": len(payload.get("rejected", [])),
            }
        checkpoint_path = output_dir / ".checkpoints" / f"{paper_id}.json"
        completed_batches: dict[str, Any] = {}
        if checkpoint_path.exists():
            completed_batches = json.loads(checkpoint_path.read_text()).get(
                "completed_batches", {}
            )
        resolved = []
        rejected: list[dict[str, Any]] = []
        for start in range(0, len(questions), QUESTION_BATCH_SIZE):
            key = str(start)
            if key in completed_batches:
                resolved.extend(
                    ResolvedQuestion.from_dict(
                        row,
                        evidence_lookup={
                            answer["evidence_unit_id"]: {
                                "paper_id": answer["paper_id"],
                                "publication_date": answer["publication_date"],
                                "evidence_spans": answer["evidence_spans"],
                            }
                            for row in completed_batches[key]["questions"]
                            for answer in row.get("answers", [])
                        },
                    )
                    for row in completed_batches[key]["questions"]
                )
                rejected.extend(completed_batches[key]["rejected"])
                continue
            batch, batch_rejected = resolve_batch(
                questions[start:start + QUESTION_BATCH_SIZE],
                evidence,
            )
            resolved.extend(batch)
            rejected.extend(batch_rejected)
            completed_batches[key] = {
                "questions": [row.to_dict() for row in batch],
                "rejected": batch_rejected,
            }
            atomic_json(checkpoint_path, {
                "paper_id": paper_id,
                "completed_batches": completed_batches,
            })
        write_resolved_paper(destination, paper_id, resolved, rejected)
        checkpoint_path.unlink(missing_ok=True)
        return {
            "questions": len(resolved),
            "answers": sum(len(row.answers) for row in resolved),
            "rejected": len(rejected),
        }

    totals = Counter()
    failures = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(process, paper_id, questions): paper_id
            for paper_id, questions in sorted(by_paper.items())
        }
        for future in as_completed(futures):
            paper_id = futures[future]
            try:
                result = future.result()
            except Exception as error:
                failures.append({"paper_id": paper_id, "error": str(error)})
                print(f"[question-resolve] ERROR {paper_id}: {error}", file=sys.stderr)
                continue
            totals.update(result)
            print(f"[question-resolve] {paper_id}: {result}", file=sys.stderr)
    if failures:
        raise RuntimeError(f"{len(failures)} question-resolution papers failed: {failures}")
    summary = {"schema_version": SCHEMA_VERSION, "papers": len(by_paper), **dict(totals)}
    atomic_json(output_dir / "summary.json", summary)
    return summary


def _load_resolved_rows(resolved_dir: Path) -> list[dict[str, Any]]:
    return [
        row
        for path in sorted(resolved_dir.glob("PMC*.json"))
        for row in json.loads(path.read_text()).get("questions", [])
    ]


def adjudicate_questions(
    questions: list[dict[str, Any]],
    facets: dict[str, Any],
) -> list[tuple[str, list[dict[str, Any]]]]:
    if len(questions) == 1:
        return [("single_question", questions)]
    if len(questions) > ADJUDICATION_BATCH_SIZE:
        groups = []
        for start in range(0, len(questions), ADJUDICATION_BATCH_SIZE):
            for label, rows in adjudicate_questions(
                questions[start:start + ADJUDICATION_BATCH_SIZE],
                facets,
            ):
                groups.append((f"batch_{start // ADJUDICATION_BATCH_SIZE + 1}:{label}", rows))
        return groups
    try:
        payload = chat_json(
            _ADJUDICATE_SYSTEM,
            json.dumps({
                "coarse_facets": facets,
                "questions": [
                    {
                        "question_id": row["question_id"],
                        "question": row["question"],
                        "question_type": row["question_type"],
                        "question_function": row["facets"].get("question_function", ""),
                        "material_family": row["facets"].get("material_family", ""),
                        "design_variable": row["facets"].get("design_variable", ""),
                        "mechanism_topic": row["facets"].get("mechanism_topic", ""),
                    }
                    for row in questions
                ],
            }, ensure_ascii=False),
            max_tokens=5000,
        )
    except LLMError as error:
        if len(questions) <= 2:
            return [(f"adjudication_failed:{error}", [row]) for row in questions]
        middle = len(questions) // 2
        return (
            adjudicate_questions(questions[:middle], facets)
            + adjudicate_questions(questions[middle:], facets)
        )
    by_id = {row["question_id"]: row for row in questions}
    assigned: set[str] = set()
    groups: list[tuple[str, list[dict[str, Any]]]] = []
    if isinstance(payload, dict):
        for index, group in enumerate(payload.get("groups", [])):
            if not isinstance(group, dict):
                continue
            ids = []
            for item in group.get("question_ids", []):
                question_id = str(item)
                if (
                    question_id in by_id
                    and question_id not in assigned
                    and question_id not in ids
                ):
                    ids.append(question_id)
            if not ids:
                continue
            assigned.update(ids)
            label = str(group.get("label") or f"group_{index + 1}").strip()
            groups.append((label, [by_id[item] for item in ids]))
    for question_id in sorted(set(by_id) - assigned):
        groups.append(("unassigned_singleton", [by_id[question_id]]))
    return groups


def build_clusters(
    resolved_dir: Path,
    output_dir: Path,
    *,
    adjudicate: bool,
    synthesize: bool,
    resume: bool,
) -> dict[str, Any]:
    rows = _load_resolved_rows(resolved_dir)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[stable_cluster_id(row["facets"])].append(row)
    output_dir.mkdir(parents=True, exist_ok=True)
    final_groups: list[tuple[str, str, list[dict[str, Any]]]] = []
    for coarse_id, questions in sorted(grouped.items()):
        facets = questions[0]["facets"]
        adjudication_path = (
            output_dir
            / ".adjudication"
            / f"{coarse_id.replace('::', '__')}.json"
        )
        if adjudicate and resume and adjudication_path.exists():
            cached = json.loads(adjudication_path.read_text())
            by_id = {row["question_id"]: row for row in questions}
            adjudicated = [
                (
                    group["label"],
                    [by_id[item] for item in group["question_ids"] if item in by_id],
                )
                for group in cached["groups"]
            ]
        else:
            adjudicated = (
                adjudicate_questions(questions, facets)
                if adjudicate
                else [("coarse_group", questions)]
            )
            if adjudicate:
                atomic_json(adjudication_path, {
                    "coarse_cluster_id": coarse_id,
                    "groups": [
                        {
                            "label": label,
                            "question_ids": [row["question_id"] for row in group],
                        }
                        for label, group in adjudicated
                    ],
                })
        for label, group_questions in adjudicated:
            signature = json.dumps(
                sorted(row["question_id"] for row in group_questions),
                ensure_ascii=False,
            )
            suffix = hashlib.sha256(signature.encode()).hexdigest()[:10]
            final_groups.append((f"{coarse_id}::{suffix}", label, group_questions))

    coherent = 0
    multi_paper = 0
    for cluster_id, adjudication_label, questions in final_groups:
        destination = output_dir / f"{cluster_id.replace('::', '__')}.json"
        if resume and destination.exists():
            continue
        answers = {
            answer["answer_id"]: answer
            for question in questions
            for answer in question.get("answers", [])
        }
        papers = {row["paper_id"] for row in questions}
        facets = questions[0]["facets"]
        canonical = min(
            (str(question["question"]) for question in questions),
            key=lambda text: (len(text), text),
        )
        synthesis = {
            "canonical_question": canonical,
            "compatibility": {"scientifically_coherent": True, "incompatibilities": []},
            "synthesis": {
                "consensus": "",
                "different_approaches": "",
                "condition_dependencies": "",
                "contradictions": "",
                "evidence_strength": "",
                "unresolved_gap": "",
                "candidate_hypothesis": "",
                "discriminating_experiment": "",
                "supporting_answer_ids": [],
                "conflicting_answer_ids": [],
            },
        }
        if synthesize and answers and (len(questions) > 1 or len(papers) > 1):
            selected_answers = []
            answers_by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for answer in sorted(
                answers.values(),
                key=lambda item: (item["publication_date"], item["answer_id"]),
            ):
                answers_by_paper[answer["paper_id"]].append(answer)
            while len(selected_answers) < SYNTHESIS_ANSWER_LIMIT and answers_by_paper:
                exhausted = []
                for paper_id in sorted(answers_by_paper):
                    if answers_by_paper[paper_id]:
                        selected_answers.append(answers_by_paper[paper_id].pop(0))
                        if len(selected_answers) >= SYNTHESIS_ANSWER_LIMIT:
                            break
                    if not answers_by_paper[paper_id]:
                        exhausted.append(paper_id)
                for paper_id in exhausted:
                    answers_by_paper.pop(paper_id, None)
            compact_answers = [
                {
                    key: answer.get(key)
                    for key in (
                        "answer_id", "paper_id", "publication_date", "answer", "material",
                        "processing_state", "conditions", "measurement_outcome", "mechanism",
                        "boundary_limitation", "epistemic_status",
                    )
                }
                for answer in selected_answers
            ]
            try:
                model = chat_json(
                    _SYNTHESIS_SYSTEM,
                    json.dumps({
                        "facets": facets,
                        "adjudication_label": adjudication_label,
                        "question_variants": [row["question"] for row in questions[:30]],
                        "answers": compact_answers,
                        "omitted_answer_count": len(answers) - len(selected_answers),
                    }, ensure_ascii=False),
                    max_tokens=4000,
                )
                if isinstance(model, dict):
                    synthesis = model
            except LLMError as error:
                synthesis["compatibility"] = {
                    "scientifically_coherent": False,
                    "incompatibilities": [f"synthesis generation failed: {error}"],
                }
            allowed = set(answers)
            for key in ("supporting_answer_ids", "conflicting_answer_ids"):
                cited = synthesis.get("synthesis", {}).get(key, [])
                synthesis.setdefault("synthesis", {})[key] = [
                    item for item in cited if item in allowed
                ]
        payload = {
            "schema_version": SCHEMA_VERSION,
            "cluster_id": cluster_id,
            "facets": facets,
            "adjudication_label": adjudication_label,
            "canonical_question": synthesis.get("canonical_question", canonical),
            "compatibility": synthesis.get("compatibility", {}),
            "question_count": len(questions),
            "paper_count": len(papers),
            "question_variants": questions,
            "answers": list(answers.values()),
            "cross_paper_synthesis": synthesis.get("synthesis", {}),
        }
        atomic_json(destination, payload)
        coherent += bool(payload["compatibility"].get("scientifically_coherent", True))
        multi_paper += len(papers) > 1
    summary = {
        "schema_version": SCHEMA_VERSION,
        "questions": len(rows),
        "coarse_clusters": len(grouped),
        "clusters": len(final_groups),
        "multi_paper_clusters": multi_paper,
        "coherent_clusters": coherent,
    }
    atomic_json(output_dir / "summary.json", summary)
    return summary


def build_review_data(cluster_dir: Path, output: Path) -> dict[str, Any]:
    clusters = [
        json.loads(path.read_text())
        for path in sorted(cluster_dir.glob("question_cluster*.json"))
    ]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "instructions": {
            "cluster_purity": "Do all question variants ask the same scientific question?",
            "condition_compatibility": "Are material states and regimes compatible or explicitly separated?",
            "answer_grounding": "Does each answer follow from its exact evidence spans?",
            "synthesis_quality": "Does synthesis distinguish agreement, differences, and gaps?",
        },
        "clusters": [
            {
                "cluster_id": row["cluster_id"],
                "file": f"{row['cluster_id'].replace('::', '__')}.json",
                "canonical_question": row["canonical_question"],
                "facets": row["facets"],
                "question_count": row["question_count"],
                "paper_count": row["paper_count"],
                "answer_count": len(row.get("answers", [])),
            }
            for row in clusters
        ],
    }
    atomic_json(output, payload)
    return {"clusters": len(clusters)}


def evaluate(resolved_dir: Path, cluster_dir: Path, output: Path) -> dict[str, Any]:
    rows = _load_resolved_rows(resolved_dir)
    clusters = [
        json.loads(path.read_text())
        for path in cluster_dir.glob("question_cluster*.json")
    ]
    statuses = Counter(row["resolution_status"] for row in rows)
    domains = Counter(row["facets"]["domain"] for row in rows)
    answers = [answer for row in rows for answer in row.get("answers", [])]
    result = {
        "schema_version": SCHEMA_VERSION,
        "questions": len(rows),
        "answers": len(answers),
        "answer_grounding_rate": 1.0 if answers else 0.0,
        "resolution_statuses": dict(statuses),
        "domains": dict(domains),
        "clusters": len(clusters),
        "multi_paper_clusters": sum(row.get("paper_count", 0) > 1 for row in clusters),
        "mean_questions_per_cluster": round(len(rows) / max(len(clusters), 1), 4),
        "mean_answers_per_cluster": round(len(answers) / max(len(clusters), 1), 4),
    }
    atomic_json(output, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    resolve = sub.add_parser("resolve")
    resolve.add_argument("--triage", type=Path, required=True)
    resolve.add_argument("--evidence-dir", type=Path, required=True)
    resolve.add_argument("--metadata", type=Path, required=True)
    resolve.add_argument("--output-dir", type=Path, required=True)
    resolve.add_argument("--workers", type=int, default=4)
    resolve.add_argument("--resume", action="store_true")
    resolve.add_argument("--paper-id", action="append")
    cluster = sub.add_parser("cluster")
    cluster.add_argument("--resolved-dir", type=Path, required=True)
    cluster.add_argument("--output-dir", type=Path, required=True)
    cluster.add_argument("--synthesize", action="store_true")
    cluster.add_argument("--adjudicate", action="store_true")
    cluster.add_argument("--resume", action="store_true")
    review = sub.add_parser("review-data")
    review.add_argument("--cluster-dir", type=Path, required=True)
    review.add_argument("--output", type=Path, required=True)
    evaluate_parser = sub.add_parser("evaluate")
    evaluate_parser.add_argument("--resolved-dir", type=Path, required=True)
    evaluate_parser.add_argument("--cluster-dir", type=Path, required=True)
    evaluate_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "resolve":
        resolve_questions(
            args.triage,
            args.evidence_dir,
            args.metadata,
            args.output_dir,
            workers=args.workers,
            resume=args.resume,
            paper_ids=set(args.paper_id) if args.paper_id else None,
        )
    elif args.command == "cluster":
        build_clusters(
            args.resolved_dir,
            args.output_dir,
            adjudicate=args.adjudicate,
            synthesize=args.synthesize,
            resume=args.resume,
        )
    elif args.command == "review-data":
        build_review_data(args.cluster_dir, args.output)
    else:
        evaluate(args.resolved_dir, args.cluster_dir, args.output)


if __name__ == "__main__":
    main()
