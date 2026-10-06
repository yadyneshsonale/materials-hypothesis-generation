"""Run temporal hypothesis reconstruction using question-centered knowledge only."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from hypothesis_evidence_v2 import atomic_json, load_evidence
from llm_client import chat_json, provider_info
from question_centered_pipeline import _SYNTHESIS_SYSTEM
from temporal_hypothesis_benchmark import (
    QUERY_LEVELS,
    RetrievalRecord,
    _date_map,
    _flatten,
    _validate_score,
    compact_evidence_payload,
    generate_with_citation_repair,
    retrieve,
    _SCORE_SYSTEM,
)

SCHEMA_VERSION = "question-centered-benchmark-1.0"
VARIANTS = (
    "raw_questions",
    "grouped_questions",
    "grouped_answers",
    "grouped_synthesis",
    "grouped_answers_v2",
)


def _load_clusters(cluster_dir: Path) -> list[dict[str, Any]]:
    return [
        json.loads(path.read_text())
        for path in sorted(cluster_dir.glob("question_cluster*.json"))
    ]


def _eligible_source_ids(
    metadata: dict[str, dict[str, Any]],
    test_paper: str,
    cutoff: str,
) -> set[str]:
    test_family = str(metadata.get(test_paper, {}).get("work_family_id") or "")
    return {
        paper_id
        for paper_id, row in metadata.items()
        if paper_id != test_paper
        and row["earliest_public_date"] < cutoff
        and (
            not test_family
            or not row.get("work_family_id")
            or row.get("work_family_id") != test_family
        )
    }


def _eligible_question(row: dict[str, Any], eligible_ids: set[str], cutoff: str) -> bool:
    return row["paper_id"] in eligible_ids and row["publication_date"] < cutoff


def _eligible_answer(row: dict[str, Any], eligible_ids: set[str], cutoff: str) -> bool:
    return row["paper_id"] in eligible_ids and row["publication_date"] < cutoff


def _question_text(row: dict[str, Any]) -> str:
    return " | ".join([
        row.get("question", ""),
        row.get("category", ""),
        _flatten(row.get("facets", {})),
    ])


def build_records(
    variant: str,
    *,
    test_paper: str,
    cutoff: str,
    triage: dict[str, Any],
    clusters: list[dict[str, Any]],
    v2_dir: Path,
    metadata: dict[str, dict[str, Any]],
    synthesis_cache: Path,
) -> list[RetrievalRecord]:
    records: list[RetrievalRecord] = []
    eligible_ids = _eligible_source_ids(metadata, test_paper, cutoff)
    if variant == "raw_questions":
        for row in triage["questions"]:
            if _eligible_question(row, eligible_ids, cutoff):
                records.append(RetrievalRecord(
                    row["question_id"],
                    row["paper_id"],
                    row["publication_date"],
                    "raw_question",
                    row["question"],
                    {
                        "question": row["question"],
                        "question_type": row["question_type"],
                        "category": row["category"],
                    },
                ))
        return records

    for cluster in clusters:
        questions = [
            row for row in cluster["question_variants"]
            if _eligible_question(row, eligible_ids, cutoff)
        ]
        if not questions:
            continue
        answers = [
            row for row in cluster.get("answers", [])
            if _eligible_answer(row, eligible_ids, cutoff)
        ]
        base = {
            "cluster_id": cluster["cluster_id"],
            "canonical_question": cluster["canonical_question"],
            "facets": cluster["facets"],
            "question_variants": [
                {"question_id": row["question_id"], "question": row["question"]}
                for row in questions[:12]
            ],
        }
        if variant in {"grouped_answers", "grouped_synthesis", "grouped_answers_v2"}:
            base["answers"] = answers
        source_papers = sorted({row["paper_id"] for row in questions} | {
            row["paper_id"] for row in answers
        })
        records.append(RetrievalRecord(
            cluster["cluster_id"],
            source_papers[0],
            max(
                [row["publication_date"] for row in questions]
                + [row["publication_date"] for row in answers]
            ),
            variant,
            _flatten(base),
            base,
        ))

    if variant == "grouped_answers_v2":
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
    return records


def add_temporal_synthesis(
    records: list[RetrievalRecord],
    *,
    cutoff: str,
    test_paper: str,
    synthesis_cache: Path,
) -> list[RetrievalRecord]:
    enriched = []
    for record in records:
        structured = dict(record.structured)
        answers = structured.get("answers", [])
        if not answers:
            enriched.append(record)
            continue
        cache_path = (
            synthesis_cache
            / cutoff
            / test_paper
            / f"{record.record_id.replace('::', '__')}.json"
        )
        if cache_path.exists():
            synthesis = json.loads(cache_path.read_text())
        else:
            synthesis = chat_json(
                _SYNTHESIS_SYSTEM,
                json.dumps({
                    "facets": structured["facets"],
                    "question_variants": [
                        row["question"] for row in structured["question_variants"]
                    ],
                    "answers": answers,
                    "temporal_cutoff": cutoff,
                }, ensure_ascii=False),
                max_tokens=4000,
            )
            allowed = {answer["answer_id"] for answer in answers}
            for key in ("supporting_answer_ids", "conflicting_answer_ids"):
                cited = synthesis.get("synthesis", {}).get(key, [])
                synthesis.setdefault("synthesis", {})[key] = [
                    item for item in cited if item in allowed
                ]
            atomic_json(cache_path, synthesis)
        structured["eligible_cross_paper_synthesis"] = synthesis
        enriched.append(RetrievalRecord(
            record.record_id,
            record.paper_id,
            record.publication_date,
            record.kind,
            _flatten(structured),
            structured,
        ))
    return enriched


def run(
    *,
    metadata_path: Path,
    cases_dir: Path,
    triage_path: Path,
    cluster_dir: Path,
    v2_dir: Path,
    output_dir: Path,
    synthesis_cache: Path,
    resume: bool,
    variants: tuple[str, ...],
    query_levels: tuple[str, ...],
) -> dict[str, Any]:
    metadata = _date_map(metadata_path)
    triage = json.loads(triage_path.read_text())
    clusters = _load_clusters(cluster_dir)
    case_paths = sorted(
        path for path in cases_dir.glob("PMC*.json") if path.name != "summary.json"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    completed = []
    for case_path in case_paths:
        case = json.loads(case_path.read_text())
        test_paper = case["paper_id"]
        cutoff = case["publication_date"]
        for variant in variants:
            records = build_records(
                variant,
                test_paper=test_paper,
                cutoff=cutoff,
                triage=triage,
                clusters=clusters,
                v2_dir=v2_dir,
                metadata=metadata,
                synthesis_cache=synthesis_cache,
            )
            for level in query_levels:
                run_id = f"{test_paper}__{level}__{variant}"
                destination = output_dir / f"{run_id}.json"
                if resume and destination.exists():
                    completed.append(json.loads(destination.read_text()))
                    continue
                query = case["queries"][level]["text"]
                selected = retrieve(query, records, limit=14)
                if variant == "grouped_synthesis":
                    selected = add_temporal_synthesis(
                        selected,
                        cutoff=cutoff,
                        test_paper=test_paper,
                        synthesis_cache=synthesis_cache,
                    )
                compact = compact_evidence_payload(selected)
                generation = generate_with_citation_repair(
                    {
                        "query": query,
                        "knowledge_cutoff": cutoff,
                        "eligible_question_centered_knowledge": compact,
                    },
                    {row.record_id for row in selected},
                )
                evaluation = _validate_score(chat_json(
                    _SCORE_SYSTEM,
                    json.dumps({
                        "query": query,
                        "hidden_target": case["hidden_target"],
                        "generated_hypothesis": generation,
                        "evidence_ids": [row.record_id for row in selected],
                    }, ensure_ascii=False),
                    max_tokens=3000,
                ))
                result = {
                    "schema_version": SCHEMA_VERSION,
                    "run_id": run_id,
                    "paper_id": test_paper,
                    "query_level": level,
                    "variant": variant,
                    "knowledge_cutoff": cutoff,
                    "query": query,
                    "retrieved_records": [row.to_dict() for row in selected],
                    "generation": generation,
                    "evaluation": evaluation,
                }
                atomic_json(destination, result)
                completed.append(result)
                print(f"[question-benchmark] {run_id} complete", file=sys.stderr)
    totals: dict[str, Counter[str]] = {}
    classes: dict[str, Counter[str]] = {}
    counts = Counter()
    for row in completed:
        variant = row["variant"]
        counts[variant] += 1
        totals.setdefault(variant, Counter()).update(row["evaluation"]["scores"])
        classes.setdefault(variant, Counter()).update([row["evaluation"]["classification"]])
    summary = {
        "schema_version": SCHEMA_VERSION,
        "provider": provider_info(),
        "runs": len(completed),
        "by_variant": {
            variant: {
                "runs": counts[variant],
                "mean_scores": {
                    key: round(value / counts[variant], 4)
                    for key, value in sorted(totals.get(variant, {}).items())
                } if counts[variant] else {},
                "classifications": dict(classes.get(variant, {})),
            }
            for variant in variants
        },
    }
    atomic_json(output_dir / "summary.json", summary)
    return summary


def audit(
    metadata_path: Path,
    cases_dir: Path,
    runs_dir: Path,
    output: Path,
    *,
    variants: tuple[str, ...] = VARIANTS,
    query_levels: tuple[str, ...] = QUERY_LEVELS,
) -> dict[str, Any]:
    metadata = _date_map(metadata_path)
    cases = {
        path.stem: json.loads(path.read_text())
        for path in cases_dir.glob("PMC*.json")
    }
    runs = [json.loads(path.read_text()) for path in runs_dir.glob("PMC*.json")]
    temporal = 0
    test_leaks = 0
    work_family_leaks = 0
    citation_errors = 0
    for run_row in runs:
        ids = {row["record_id"] for row in run_row["retrieved_records"]}
        test_family = str(
            metadata.get(run_row["paper_id"], {}).get("work_family_id") or ""
        )
        for record in run_row["retrieved_records"]:
            temporal += record["publication_date"] >= run_row["knowledge_cutoff"]
            test_leaks += record["paper_id"] == run_row["paper_id"]
            record_family = str(
                metadata.get(record["paper_id"], {}).get("work_family_id") or ""
            )
            work_family_leaks += bool(
                test_family and record_family and record_family == test_family
            )
        cited = set(run_row["generation"].get("supporting_evidence_ids", []))
        cited.update(run_row["generation"].get("conflicting_evidence_ids", []))
        citation_errors += len(cited - ids)
    expected = len(cases) * len(query_levels) * len(variants)
    expected_matrix = {
        (paper_id, query_level, variant)
        for paper_id in cases
        for query_level in query_levels
        for variant in variants
    }
    actual_matrix = {
        (row["paper_id"], row["query_level"], row["variant"])
        for row in runs
        if row["query_level"] in query_levels and row["variant"] in variants
    }
    result = {
        "schema_version": SCHEMA_VERSION,
        "cases": len(cases),
        "runs": len(runs),
        "expected_runs": expected,
        "matrix_complete": actual_matrix == expected_matrix,
        "temporal_violations": temporal,
        "test_paper_leaks": test_leaks,
        "same_work_family_leaks": work_family_leaks,
        "invalid_citations": citation_errors,
        "verified": not any(
            (temporal, test_leaks, work_family_leaks, citation_errors)
        ),
    }
    atomic_json(output, result)
    if not result["verified"] or not result["matrix_complete"]:
        raise ValueError(f"question-centered benchmark integrity failed: {result}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--metadata", type=Path, required=True)
    run_parser.add_argument("--cases-dir", type=Path, required=True)
    run_parser.add_argument("--triage", type=Path, required=True)
    run_parser.add_argument("--cluster-dir", type=Path, required=True)
    run_parser.add_argument("--v2-dir", type=Path, required=True)
    run_parser.add_argument("--output-dir", type=Path, required=True)
    run_parser.add_argument("--synthesis-cache", type=Path, required=True)
    run_parser.add_argument("--resume", action="store_true")
    run_parser.add_argument("--variant", action="append", choices=VARIANTS)
    run_parser.add_argument("--query-level", action="append", choices=QUERY_LEVELS)
    audit_parser = sub.add_parser("audit")
    audit_parser.add_argument("--metadata", type=Path, required=True)
    audit_parser.add_argument("--cases-dir", type=Path, required=True)
    audit_parser.add_argument("--runs-dir", type=Path, required=True)
    audit_parser.add_argument("--output", type=Path, required=True)
    audit_parser.add_argument("--variant", action="append", choices=VARIANTS)
    audit_parser.add_argument("--query-level", action="append", choices=QUERY_LEVELS)
    args = parser.parse_args()
    if args.command == "run":
        run(
            metadata_path=args.metadata,
            cases_dir=args.cases_dir,
            triage_path=args.triage,
            cluster_dir=args.cluster_dir,
            v2_dir=args.v2_dir,
            output_dir=args.output_dir,
            synthesis_cache=args.synthesis_cache,
            resume=args.resume,
            variants=tuple(args.variant or VARIANTS),
            query_levels=tuple(args.query_level or QUERY_LEVELS),
        )
    else:
        audit(
            args.metadata,
            args.cases_dir,
            args.runs_dir,
            args.output,
            variants=tuple(args.variant or VARIANTS),
            query_levels=tuple(args.query_level or QUERY_LEVELS),
        )


if __name__ == "__main__":
    main()
