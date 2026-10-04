"""Build and run leakage-audited temporal hypothesis reconstruction experiments."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from hypothesis_evidence_v2 import HypothesisEvidenceUnit, atomic_json, load_evidence
from llm_client import chat_json, provider_info
from materials_evidence import MaterialsEvidenceUnit, load_materials_evidence

SCHEMA_VERSION = "temporal-hypothesis-benchmark-1.0"
QUERY_LEVELS = ("broad", "problem_constrained", "expert_context")
VARIANTS = ("roles_only", "v1_evidence", "v2_evidence", "v2_roles_questions")
ACTIONABLE_QUESTION_TYPES = {
    "counterfactual",
    "boundary",
    "mechanism",
    "evidence",
    "limitation",
    "transfer",
    "follow_up",
}
QUERY_ROLE_TYPES = {"problem_motivation", "prior_limitation", "constraint"}
TARGET_ROLE_TYPES = {
    "hypothesis_statement",
    "causal_claim",
    "mechanism_principle",
    "evidence_result",
    "contradiction",
}
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_SPACE_RE = re.compile(r"\s+")

_CASE_SYSTEM = """You build a leakage-audited temporal hypothesis-reconstruction benchmark case.
You receive selected role claims and normalized evidence from ONE held-out paper.

Construct three user queries:
- broad: material/application family and desired property only;
- problem_constrained: add operating regime, known failure, and design constraints;
- expert_context: add all scientifically useful pre-solution context.

Queries must describe the scientific problem without revealing the held-out paper's exact
successful composition, intervention, processing recipe, resulting structure, mechanism,
quantitative result, conclusion, title, DOI, authors, or distinctive wording. Do not copy
result-revealing evidence. A query must request a hypothesis, supporting prior evidence, boundary,
and falsification experiment.

Also construct the hidden structured target from current-paper evidence. The hidden target is not
part of any query. Preserve uncertainty rather than filling absent details.

Return JSON:
{
  "queries": {
    "broad": {"text": "", "source_role_refs": []},
    "problem_constrained": {"text": "", "source_role_refs": []},
    "expert_context": {"text": "", "source_role_refs": []}
  },
  "hidden_target": {
    "material_initial_state": "",
    "intervention": "",
    "conditions": "",
    "structural_mediator": "",
    "mechanism": "",
    "predicted_outcome": "",
    "baseline": "",
    "boundary": "",
    "discriminating_measurement": "",
    "actual_result": ""
  },
  "leakage_audit": {
    "excluded_result_information": [],
    "remaining_risks": []
  }
}."""

_GENERATE_SYSTEM = """You are a materials-science hypothesis agent in a chronological benchmark.
Use ONLY the supplied temporally eligible evidence. Do not claim knowledge of the held-out paper.
If evidence is insufficient, state the uncertainty instead of inventing support.

Return one falsifiable hypothesis as JSON:
{
  "hypothesis": "",
  "material_initial_state": "",
  "intervention": "",
  "conditions": "",
  "structural_mediator": "",
  "mechanism": "",
  "predicted_outcome": "",
  "baseline": "",
  "boundary": "",
  "uncertainty": "",
  "supporting_evidence_ids": [],
  "conflicting_evidence_ids": [],
  "falsification_experiment": {
    "design": "", "measurements": [], "falsification_rule": ""
  }
}.
Evidence IDs must be copied from the supplied records."""

_SCORE_SYSTEM = """You evaluate a generated materials hypothesis against a hidden paper target.
Do not reward wording overlap. Score scientific agreement and evidence discipline. A different but
well-supported hypothesis may be plausible without being an exact reconstruction.

Return JSON:
{
  "scores": {
    "problem_alignment": 0,
    "intervention_reconstruction": 0,
    "condition_agreement": 0,
    "mechanism_agreement": 0,
    "outcome_agreement": 0,
    "baseline_quality": 0,
    "boundary_quality": 0,
    "experiment_discriminability": 0,
    "evidence_validity": 0,
    "novelty": 0
  },
  "classification": "exact_reconstruction|partial_reconstruction|plausible_alternative|unsupported",
  "fatal_errors": [],
  "explanation": ""
}.
Every score is an integer from 0 to 4."""


@dataclass(frozen=True)
class RetrievalRecord:
    record_id: str
    paper_id: str
    publication_date: str
    kind: str
    text: str
    structured: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "paper_id": self.paper_id,
            "publication_date": self.publication_date,
            "kind": self.kind,
            "text": self.text,
            "structured": self.structured,
        }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _normalize(text: str) -> str:
    return _SPACE_RE.sub(" ", text).strip()


def _tokens(text: str) -> list[str]:
    return [token for token in _TOKEN_RE.findall(text.casefold()) if len(token) > 2]


def _date_map(metadata_path: Path) -> dict[str, dict[str, Any]]:
    payload = _read_json(metadata_path)
    rows = payload.get("papers", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("temporal metadata must contain a papers list")
    return {str(row["paper_id"]): row for row in rows}


def chronological_split(
    metadata: dict[str, dict[str, Any]],
    *,
    train_through: int,
    validation_year: int,
) -> dict[str, str]:
    split: dict[str, str] = {}
    for paper_id, row in metadata.items():
        public_date = str(row.get("earliest_public_date") or "")
        if not public_date:
            split[paper_id] = "excluded_missing_date"
            continue
        year = int(public_date[:4])
        if year <= train_through:
            split[paper_id] = "train"
        elif year == validation_year:
            split[paper_id] = "validation"
        else:
            split[paper_id] = "test"
    return split


def triage_questions(papers_dir: Path, metadata_path: Path, output: Path) -> dict[str, Any]:
    metadata = _date_map(metadata_path)
    records: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for paper_id in sorted(metadata):
        path = papers_dir / paper_id / "output" / "questions.json"
        if not path.exists():
            continue
        payload = _read_json(path)
        for question in payload.get("questions", []):
            question_type = str(question.get("question_type", "")).strip().lower()
            section = str(question.get("source_section", "")).casefold()
            actionable = question_type in ACTIONABLE_QUESTION_TYPES
            likely_background = section.startswith(("abstract", "introduction", "background"))
            if not actionable:
                use = "reading_ui"
                category = (
                    "replication_detail"
                    if question_type in {"method", "replication"}
                    else "reading_clarification"
                )
            elif question_type == "counterfactual":
                use, category = "hypothesis_candidate", "design_variable"
            elif question_type == "boundary":
                use, category = "hypothesis_candidate", "boundary_failure"
            elif question_type in {"evidence", "follow_up"}:
                use, category = "experiment_candidate", "discriminating_experiment"
            elif question_type == "mechanism":
                use, category = "hypothesis_candidate", "mechanism_gap"
            else:
                use, category = "gap_candidate", "unresolved_gap"
            record = {
                "question_id": question.get("question_id"),
                "paper_id": paper_id,
                "publication_date": metadata[paper_id].get("earliest_public_date"),
                "question": question.get("question"),
                "question_type": question_type,
                "category": category,
                "recommended_use": use,
                "likely_background_trigger": likely_background,
                "resolution_status": "requires_evidence_search" if actionable else "not_required",
                "evidence_spans": question.get("evidence_spans", []),
            }
            records.append(record)
            counts[category] += 1
    result = {
        "schema_version": SCHEMA_VERSION,
        "method": "conservative deterministic triage; resolution requires temporal evidence search",
        "counts": dict(sorted(counts.items())),
        "questions": records,
    }
    atomic_json(output, result)
    return result


def _role_items(papers_dir: Path, paper_id: str, allowed: set[str]) -> list[dict[str, Any]]:
    path = papers_dir / paper_id / "output" / "roles.json"
    if not path.exists():
        return []
    roles = _read_json(path).get("reconciled_by_role", {})
    return [
        {
            "ref": f"{paper_id}:{role}:{index}",
            "role": role,
            "content": item.get("content", ""),
            "evidence_spans": item.get("evidence_spans", []),
        }
        for role in sorted(allowed)
        for index, item in enumerate(roles.get(role, []))
    ]


def _validate_case_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("benchmark case response must be an object")
    queries = payload.get("queries")
    target = payload.get("hidden_target")
    if not isinstance(queries, dict) or not isinstance(target, dict):
        raise ValueError("benchmark case requires queries and hidden_target objects")
    for level in QUERY_LEVELS:
        query = queries.get(level)
        if not isinstance(query, dict) or not str(query.get("text", "")).strip():
            raise ValueError(f"benchmark case query {level} is missing")
    required_target = {
        "material_initial_state",
        "intervention",
        "conditions",
        "structural_mediator",
        "mechanism",
        "predicted_outcome",
        "baseline",
        "boundary",
        "discriminating_measurement",
        "actual_result",
    }
    missing = required_target - set(target)
    if missing:
        raise ValueError(f"hidden target missing fields: {sorted(missing)}")
    return payload


def build_cases(
    metadata_path: Path,
    papers_dir: Path,
    v2_dir: Path,
    output_dir: Path,
    *,
    train_through: int,
    validation_year: int,
    include_validation: bool,
    resume: bool,
) -> dict[str, Any]:
    metadata = _date_map(metadata_path)
    split = chronological_split(
        metadata,
        train_through=train_through,
        validation_year=validation_year,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    selected = {
        paper_id
        for paper_id, label in split.items()
        if label == "test" or (include_validation and label == "validation")
    }
    completed = 0
    excluded: list[dict[str, str]] = []
    for paper_id in sorted(selected, key=lambda item: metadata[item]["earliest_public_date"]):
        destination = output_dir / f"{paper_id}.json"
        if resume and destination.exists():
            completed += 1
            continue
        evidence_path = v2_dir / f"{paper_id}.json"
        if not evidence_path.exists():
            raise FileNotFoundError(f"v2 evidence missing for benchmark paper {paper_id}")
        units = load_evidence(evidence_path)
        current_units = [
            unit.to_dict() for unit in units if unit.claim_ownership == "current_paper"
        ]
        target_roles = _role_items(papers_dir, paper_id, TARGET_ROLE_TYPES)
        if not current_units and not target_roles:
            excluded.append({
                "paper_id": paper_id,
                "reason": "no current-paper v2 evidence or reconciled target roles",
            })
            print(
                f"[temporal-cases] {paper_id} excluded: no hidden-target evidence",
                file=sys.stderr,
            )
            continue
        target_source = (
            "v2_current_paper_evidence"
            if current_units
            else "reconciled_target_roles_fallback"
        )
        prompt = {
            "safe_role_candidates": _role_items(papers_dir, paper_id, QUERY_ROLE_TYPES),
            "target_role_candidates": target_roles,
            "normalized_current_paper_evidence_for_hidden_target_only": current_units,
        }
        payload = _validate_case_payload(chat_json(
            _CASE_SYSTEM,
            json.dumps(prompt, ensure_ascii=False),
            max_tokens=7000,
        ))
        forbidden = [
            str(metadata[paper_id].get("title", "")).casefold(),
            str(metadata[paper_id].get("doi", "")).casefold(),
        ]
        detected: list[str] = []
        for level in QUERY_LEVELS:
            text = payload["queries"][level]["text"].casefold()
            for phrase in forbidden:
                if phrase and phrase in text:
                    detected.append(f"{level}:{phrase}")
        case = {
            "schema_version": SCHEMA_VERSION,
            "paper_id": paper_id,
            "publication_date": metadata[paper_id]["earliest_public_date"],
            "split": split[paper_id],
            "benchmark_claim": metadata[paper_id].get(
                "benchmark_claim",
                "retrospective_temporal_reconstruction",
            ),
            "model_cutoff_status": metadata[paper_id].get("model_cutoff_status", "unknown"),
            "hidden_target_source": target_source,
            **payload,
            "deterministic_leakage_flags": detected,
        }
        if detected:
            raise ValueError(f"identifying metadata leaked into {paper_id} query: {detected}")
        atomic_json(destination, case)
        completed += 1
        print(f"[temporal-cases] {paper_id} complete", file=sys.stderr)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "train_through": train_through,
        "validation_year": validation_year,
        "split_counts": dict(Counter(split.values())),
        "case_count": completed,
        "excluded_case_count": len(excluded),
        "excluded_cases": excluded,
        "cases": sorted(selected),
    }
    atomic_json(output_dir / "summary.json", summary)
    return summary


def _flatten(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten(item) for item in value)
    return "" if value is None else str(value)


def _eligible(
    paper_id: str,
    test_paper_id: str,
    cutoff: str,
    metadata: dict[str, dict[str, Any]],
) -> bool:
    if paper_id == test_paper_id or paper_id not in metadata:
        return False
    source_date = str(metadata[paper_id].get("earliest_public_date") or "")
    if not source_date or source_date >= cutoff:
        return False
    test_family = str(metadata[test_paper_id].get("work_family_id") or "")
    source_family = str(metadata[paper_id].get("work_family_id") or "")
    return not test_family or not source_family or source_family != test_family


def _load_records(
    variant: str,
    metadata: dict[str, dict[str, Any]],
    papers_dir: Path,
    v1_dir: Path,
    v2_dir: Path,
    triage_path: Path,
    test_paper_id: str,
    cutoff: str,
) -> list[RetrievalRecord]:
    records: list[RetrievalRecord] = []
    eligible_ids = {
        paper_id
        for paper_id in metadata
        if _eligible(paper_id, test_paper_id, cutoff, metadata)
    }
    if variant in {"roles_only", "v2_roles_questions"}:
        for paper_id in eligible_ids:
            for item in _role_items(papers_dir, paper_id, TARGET_ROLE_TYPES | QUERY_ROLE_TYPES):
                records.append(RetrievalRecord(
                    item["ref"],
                    paper_id,
                    metadata[paper_id]["earliest_public_date"],
                    f"role:{item['role']}",
                    _flatten(item),
                    item,
                ))
    if variant == "v1_evidence":
        for unit in load_materials_evidence(v1_dir):
            if unit.paper_id in eligible_ids:
                records.append(RetrievalRecord(
                    unit.unit_id,
                    unit.paper_id,
                    metadata[unit.paper_id]["earliest_public_date"],
                    "v1_evidence",
                    unit.summary(),
                    unit.to_dict(),
                ))
    if variant in {"v2_evidence", "v2_roles_questions"}:
        for unit in load_evidence(v2_dir):
            if unit.paper_id in eligible_ids:
                records.append(RetrievalRecord(
                    unit.unit_id,
                    unit.paper_id,
                    metadata[unit.paper_id]["earliest_public_date"],
                    "v2_evidence",
                    _flatten(unit.to_dict()),
                    unit.to_dict(),
                ))
    if variant == "v2_roles_questions":
        triage = _read_json(triage_path)
        for item in triage.get("questions", []):
            paper_id = str(item.get("paper_id", ""))
            if (
                paper_id in eligible_ids
                and item.get("recommended_use") != "reading_ui"
                and not item.get("likely_background_trigger")
            ):
                records.append(RetrievalRecord(
                    str(item["question_id"]),
                    paper_id,
                    metadata[paper_id]["earliest_public_date"],
                    f"question:{item['category']}",
                    str(item.get("question", "")),
                    item,
                ))
    return records


def retrieve(query: str, records: Iterable[RetrievalRecord], limit: int = 14) -> list[RetrievalRecord]:
    query_counts = Counter(_tokens(query))
    if not query_counts:
        return []
    scored: list[tuple[float, RetrievalRecord]] = []
    for record in records:
        document_counts = Counter(_tokens(record.text))
        overlap = sum(
            min(count, document_counts[token])
            for token, count in query_counts.items()
        )
        if not overlap:
            continue
        coverage = overlap / sum(query_counts.values())
        density = overlap / math.sqrt(max(sum(document_counts.values()), 1))
        score = 2 * coverage + density
        scored.append((score, record))
    scored.sort(key=lambda item: (-item[0], item[1].publication_date, item[1].record_id))
    return [record for _, record in scored[:limit]]


def _validate_generation(payload: Any, allowed_ids: set[str]) -> dict[str, Any]:
    if not isinstance(payload, dict) or not str(payload.get("hypothesis", "")).strip():
        raise ValueError("hypothesis generation response is invalid")
    cited = {
        str(item)
        for key in ("supporting_evidence_ids", "conflicting_evidence_ids")
        for item in payload.get(key, [])
    }
    unknown = cited - allowed_ids
    if unknown:
        raise ValueError(f"generated hypothesis cites unavailable evidence: {sorted(unknown)}")
    return payload


def _validate_score(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or not isinstance(payload.get("scores"), dict):
        raise ValueError("score response must contain scores")
    for name, value in payload["scores"].items():
        if not isinstance(value, int) or not 0 <= value <= 4:
            raise ValueError(f"invalid score {name}={value!r}")
    return payload


def run_experiments(
    metadata_path: Path,
    papers_dir: Path,
    v1_dir: Path,
    v2_dir: Path,
    triage_path: Path,
    cases_dir: Path,
    output_dir: Path,
    *,
    resume: bool,
    variants: tuple[str, ...] = VARIANTS,
    query_levels: tuple[str, ...] = QUERY_LEVELS,
) -> dict[str, Any]:
    metadata = _date_map(metadata_path)
    case_paths = sorted(
        path for path in cases_dir.glob("*.json") if path.name != "summary.json"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    completed: list[dict[str, Any]] = []
    for case_path in case_paths:
        case = _read_json(case_path)
        paper_id = case["paper_id"]
        cutoff = case["publication_date"]
        for variant in variants:
            records = _load_records(
                variant,
                metadata,
                papers_dir,
                v1_dir,
                v2_dir,
                triage_path,
                paper_id,
                cutoff,
            )
            for level in query_levels:
                run_id = f"{paper_id}__{level}__{variant}"
                destination = output_dir / f"{run_id}.json"
                if resume and destination.exists():
                    completed.append(_read_json(destination))
                    continue
                query = case["queries"][level]["text"]
                selected = retrieve(query, records)
                evidence_payload = [item.to_dict() for item in selected]
                generation = _validate_generation(
                    chat_json(
                        _GENERATE_SYSTEM,
                        json.dumps({
                            "query": query,
                            "knowledge_cutoff": cutoff,
                            "eligible_evidence": evidence_payload,
                        }, ensure_ascii=False),
                        max_tokens=5000,
                    ),
                    {item.record_id for item in selected},
                )
                score = _validate_score(chat_json(
                    _SCORE_SYSTEM,
                    json.dumps({
                        "query": query,
                        "hidden_target": case["hidden_target"],
                        "generated_hypothesis": generation,
                        "evidence_ids": [item.record_id for item in selected],
                    }, ensure_ascii=False),
                    max_tokens=3000,
                ))
                result = {
                    "schema_version": SCHEMA_VERSION,
                    "run_id": run_id,
                    "paper_id": paper_id,
                    "query_level": level,
                    "variant": variant,
                    "knowledge_cutoff": cutoff,
                    "benchmark_claim": case["benchmark_claim"],
                    "query": query,
                    "retrieved_evidence": evidence_payload,
                    "generation": generation,
                    "evaluation": score,
                }
                atomic_json(destination, result)
                completed.append(result)
                print(f"[temporal-experiment] {run_id} complete", file=sys.stderr)
    score_totals: dict[str, Counter[str]] = {}
    classifications: dict[str, Counter[str]] = {}
    run_counts: Counter[str] = Counter()
    for result in completed:
        variant = result["variant"]
        run_counts[variant] += 1
        score_totals.setdefault(variant, Counter()).update(result["evaluation"]["scores"])
        classifications.setdefault(variant, Counter()).update(
            [result["evaluation"]["classification"]]
        )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "provider": provider_info(),
        "runs": len(completed),
        "by_variant": {
            variant: {
                "runs": run_counts[variant],
                "mean_scores": {
                    score: round(total / run_counts[variant], 4)
                    for score, total in sorted(score_totals.get(variant, {}).items())
                } if run_counts[variant] else {},
                "classifications": dict(classifications.get(variant, {})),
            }
            for variant in variants
        },
        "limitations": [
            "Model-based scores require blinded materials-expert validation.",
            "Cases predating an undocumented model cutoff are retrospective temporal reconstructions.",
            "Question triage is conservative and does not claim that every gap is unresolved.",
        ],
    }
    atomic_json(output_dir / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    triage_parser = subparsers.add_parser("triage-questions")
    triage_parser.add_argument("--papers-dir", type=Path, required=True)
    triage_parser.add_argument("--metadata", type=Path, required=True)
    triage_parser.add_argument("--output", type=Path, required=True)

    cases_parser = subparsers.add_parser("build-cases")
    cases_parser.add_argument("--metadata", type=Path, required=True)
    cases_parser.add_argument("--papers-dir", type=Path, required=True)
    cases_parser.add_argument("--v2-dir", type=Path, required=True)
    cases_parser.add_argument("--output-dir", type=Path, required=True)
    cases_parser.add_argument("--train-through", type=int, default=2023)
    cases_parser.add_argument("--validation-year", type=int, default=2024)
    cases_parser.add_argument("--include-validation", action="store_true")
    cases_parser.add_argument("--resume", action="store_true")

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--metadata", type=Path, required=True)
    run_parser.add_argument("--papers-dir", type=Path, required=True)
    run_parser.add_argument("--v1-dir", type=Path, required=True)
    run_parser.add_argument("--v2-dir", type=Path, required=True)
    run_parser.add_argument("--triage", type=Path, required=True)
    run_parser.add_argument("--cases-dir", type=Path, required=True)
    run_parser.add_argument("--output-dir", type=Path, required=True)
    run_parser.add_argument("--resume", action="store_true")
    run_parser.add_argument("--variant", action="append", choices=VARIANTS)
    run_parser.add_argument("--query-level", action="append", choices=QUERY_LEVELS)

    args = parser.parse_args()
    if args.command == "triage-questions":
        triage_questions(args.papers_dir, args.metadata, args.output)
    elif args.command == "build-cases":
        build_cases(
            args.metadata,
            args.papers_dir,
            args.v2_dir,
            args.output_dir,
            train_through=args.train_through,
            validation_year=args.validation_year,
            include_validation=args.include_validation,
            resume=args.resume,
        )
    else:
        run_experiments(
            args.metadata,
            args.papers_dir,
            args.v1_dir,
            args.v2_dir,
            args.triage,
            args.cases_dir,
            args.output_dir,
            resume=args.resume,
            variants=tuple(args.variant or VARIANTS),
            query_levels=tuple(args.query_level or QUERY_LEVELS),
        )


if __name__ == "__main__":
    main()
