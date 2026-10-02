"""Evaluate grounded 11-role and decision-question extraction outputs."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from role_question_extract import QUESTION_TYPES, _validate_questions, _validate_reconciled
from roles import ROLE_KEYS


def _rejection_category(reason: str) -> str:
    for prefix in (
        "non-verbatim role evidence_span",
        "non-verbatim reconciled span",
        "unknown role",
    ):
        if reason.startswith(prefix):
            return prefix
    return reason


def evaluate(
    evidence_dir: Path,
    source_dir: Path,
    roles_output: Path | None = None,
    questions_output: Path | None = None,
) -> dict[str, Any]:
    output_paths = sorted(evidence_dir.glob("*.json"))
    source_ids = {path.stem for path in source_dir.glob("*.txt")}
    output_ids = {path.stem for path in output_paths}
    role_counts: Counter[str] = Counter()
    role_papers: Counter[str] = Counter()
    question_types: Counter[str] = Counter()
    reference_roles: Counter[str] = Counter()
    rejection_stages: Counter[str] = Counter()
    rejection_reasons: Counter[str] = Counter()
    per_paper: list[dict[str, Any]] = []
    invalid_items: list[dict[str, Any]] = []
    exported_roles: list[dict[str, Any]] = []
    exported_questions: list[dict[str, Any]] = []
    question_confidences: list[float] = []
    total_rejected = 0

    for path in output_paths:
        payload = json.loads(path.read_text())
        paper_id = str(payload.get("paper_id") or path.stem)
        source_path = source_dir / f"{paper_id}.txt"
        if not source_path.exists():
            invalid_items.append({"paper_id": paper_id, "reason": "source text is missing"})
            continue
        full_text = source_path.read_text(encoding="utf-8", errors="ignore")
        reconciled, role_rejected = _validate_reconciled(
            payload.get("reconciled_by_role"),
            full_text,
        )
        questions, question_rejected = _validate_questions(
            payload.get("questions"),
            paper_id,
            full_text,
            reconciled,
        )
        for rejected in role_rejected + question_rejected:
            invalid_items.append({"paper_id": paper_id, **rejected})
        present_roles = {role for role, items in reconciled.items() if items}
        for role, items in reconciled.items():
            role_counts[role] += len(items)
            role_papers[role] += bool(items)
            for index, item in enumerate(items):
                exported_roles.append({
                    "role_id": f"{paper_id}::{role}::{index}",
                    "paper_id": paper_id,
                    "role": role,
                    **item,
                })
        for question in questions:
            question_types[question["question_type"]] += 1
            question_confidences.append(question["confidence"])
            exported_questions.append({"paper_id": paper_id, **question})
            for reference in question["grounded_role_refs"]:
                reference_roles[reference.split(":", 1)[0]] += 1
        rejected = payload.get("rejected_items", [])
        total_rejected += len(rejected) if isinstance(rejected, list) else 0
        if isinstance(rejected, list):
            for item in rejected:
                if isinstance(item, dict):
                    rejection_stages[str(item.get("stage", "unknown"))] += 1
                    reason = str(item.get("reason", "unknown"))
                    rejection_reasons[_rejection_category(reason)] += 1
        per_paper.append({
            "paper_id": paper_id,
            "role_items": sum(len(items) for items in reconciled.values()),
            "roles_present": len(present_roles),
            "questions": len(questions),
            "invalid_items": len(role_rejected) + len(question_rejected),
            "model_rejected_items": len(rejected) if isinstance(rejected, list) else 0,
        })

    total_roles = sum(role_counts.values())
    total_questions = sum(question_types.values())
    result = {
        "source_papers": len(source_ids),
        "output_papers": len(output_ids),
        "missing_output_papers": sorted(source_ids - output_ids),
        "unexpected_output_papers": sorted(output_ids - source_ids),
        "total_role_items": total_roles,
        "role_counts": {role: role_counts[role] for role in ROLE_KEYS},
        "role_paper_coverage": {
            role: {
                "papers": role_papers[role],
                "rate": round(role_papers[role] / len(output_paths), 4) if output_paths else 0,
            }
            for role in ROLE_KEYS
        },
        "total_questions": total_questions,
        "question_type_counts": {
            question_type: question_types[question_type]
            for question_type in sorted(QUESTION_TYPES)
        },
        "question_reference_roles": dict(sorted(reference_roles.items())),
        "mean_questions_per_output_paper": (
            round(mean(row["questions"] for row in per_paper), 2) if per_paper else 0
        ),
        "mean_question_confidence": (
            round(mean(question_confidences), 4) if question_confidences else 0
        ),
        "papers_without_questions": sorted(
            row["paper_id"] for row in per_paper if row["questions"] == 0
        ),
        "invalid_item_count": len(invalid_items),
        "invalid_items": invalid_items,
        "model_rejected_items": total_rejected,
        "rejection_stage_counts": dict(sorted(rejection_stages.items())),
        "rejection_reason_counts": dict(sorted(rejection_reasons.items())),
        "per_paper": per_paper,
    }
    for output_path, rows in (
        (roles_output, exported_roles),
        (questions_output, exported_questions),
    ):
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
            )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--roles-jsonl", type=Path)
    parser.add_argument("--questions-jsonl", type=Path)
    args = parser.parse_args()
    result = evaluate(
        args.evidence_dir,
        args.source_dir,
        args.roles_jsonl,
        args.questions_jsonl,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        f"[evaluate-role-questions] papers={result['output_papers']}/{result['source_papers']} "
        f"roles={result['total_role_items']} questions={result['total_questions']} "
        f"invalid={result['invalid_item_count']}"
    )
    if result["invalid_item_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
