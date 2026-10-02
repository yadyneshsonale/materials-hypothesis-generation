"""Evaluate high-recall reader questions for grounding, diversity, and paper coverage."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any

from reader_question_generate import (
    READING_STEPS,
    RELEVANCE_LEVELS,
    SCHEMA_VERSION,
)
from role_question_extract import READER_INTENTS, READER_QUESTION_TYPES


def _payload_paths(question_dir: Path) -> list[Path]:
    flat = sorted(question_dir.glob("*.json"))
    if flat:
        return flat
    return sorted(question_dir.glob("*/output/questions.json"))


def evaluate(
    question_dir: Path,
    source_dir: Path,
    questions_output: Path | None = None,
) -> dict[str, Any]:
    source_ids = {path.stem for path in source_dir.glob("*.txt")}
    output_ids = set()
    invalid_items = []
    per_paper = []
    type_counts: Counter[str] = Counter()
    intent_counts: Counter[str] = Counter()
    step_counts: Counter[str] = Counter()
    relevance_counts: Counter[str] = Counter()
    section_counts: Counter[str] = Counter()
    confidences = []
    all_ids = set()
    exported_questions = []

    for path in _payload_paths(question_dir):
        payload = json.loads(path.read_text())
        paper_id = str(payload.get("paper_id") or path.stem)
        output_ids.add(paper_id)
        source_path = source_dir / f"{paper_id}.txt"
        if not source_path.exists():
            invalid_items.append({"paper_id": paper_id, "reason": "source text is missing"})
            continue
        source = source_path.read_text(encoding="utf-8", errors="ignore")
        questions = payload.get("questions", [])
        if not isinstance(questions, list):
            invalid_items.append({"paper_id": paper_id, "reason": "questions is not a list"})
            continue
        valid_count = 0
        grounded_count = 0
        paper_sections = set()
        for index, item in enumerate(questions):
            reason = ""
            if not isinstance(item, dict):
                reason = "question is not an object"
            else:
                question_id = str(item.get("question_id", ""))
                question = str(item.get("question", "")).strip()
                question_type = str(item.get("question_type", "")).strip()
                reader_intent = str(item.get("reader_intent", "")).strip()
                reading_step = str(item.get("reading_step", "")).strip()
                relevance = str(item.get("relevance", "")).strip()
                rationale = str(item.get("rationale", "")).strip()
                section = str(item.get("source_section", "")).strip()
                spans = item.get("evidence_spans", [])
                try:
                    confidence = float(item.get("confidence", -1))
                except (TypeError, ValueError):
                    confidence = -1
                if not question_id or question_id in all_ids:
                    reason = "question_id is missing or duplicated"
                elif not question.endswith("?") or len(question.split()) > 60:
                    reason = "question syntax is invalid"
                elif question_type not in READER_QUESTION_TYPES:
                    reason = f"unknown question_type: {question_type!r}"
                elif reader_intent not in READER_INTENTS:
                    reason = f"unknown reader_intent: {reader_intent!r}"
                elif reading_step not in READING_STEPS:
                    reason = f"unknown reading_step: {reading_step!r}"
                elif relevance not in RELEVANCE_LEVELS:
                    reason = f"unknown relevance: {relevance!r}"
                elif not rationale:
                    reason = "rationale is empty"
                elif not isinstance(spans, list) or len(spans) != 1:
                    reason = "exactly one evidence span is required"
                elif not isinstance(spans[0], str) or spans[0] not in source:
                    reason = "evidence span is not verbatim paper text"
                elif not 0 <= confidence <= 1:
                    reason = "confidence must be between 0 and 1"
                else:
                    all_ids.add(question_id)
                    valid_count += 1
                    grounded_count += 1
                    type_counts[question_type] += 1
                    intent_counts[reader_intent] += 1
                    step_counts[reading_step] += 1
                    relevance_counts[relevance] += 1
                    section_counts[section] += 1
                    paper_sections.add(section)
                    confidences.append(confidence)
                    exported_questions.append({"paper_id": paper_id, **item})
            if reason:
                invalid_items.append({
                    "paper_id": paper_id,
                    "question_index": index,
                    "reason": reason,
                })
        per_paper.append({
            "paper_id": paper_id,
            "questions": valid_count,
            "grounded_questions": grounded_count,
            "sections_with_questions": len(paper_sections),
        })

    counts = [row["questions"] for row in per_paper]
    total = sum(counts)
    result = {
        "schema_version": SCHEMA_VERSION,
        "source_papers": len(source_ids),
        "output_papers": len(output_ids),
        "missing_output_papers": sorted(source_ids - output_ids),
        "unexpected_output_papers": sorted(output_ids - source_ids),
        "total_questions": total,
        "mean_questions_per_paper": round(mean(counts), 2) if counts else 0,
        "median_questions_per_paper": median(counts) if counts else 0,
        "minimum_questions_per_paper": min(counts) if counts else 0,
        "maximum_questions_per_paper": max(counts) if counts else 0,
        "mean_confidence": round(mean(confidences), 4) if confidences else 0,
        "exact_grounding_rate": round(
            sum(row["grounded_questions"] for row in per_paper) / total, 4
        ) if total else 0,
        "question_type_counts": dict(sorted(type_counts.items())),
        "reader_intent_counts": dict(sorted(intent_counts.items())),
        "reading_step_counts": dict(sorted(step_counts.items())),
        "relevance_counts": dict(sorted(relevance_counts.items())),
        "source_section_counts": dict(sorted(section_counts.items())),
        "papers_without_questions": sorted(
            row["paper_id"] for row in per_paper if row["questions"] == 0
        ),
        "invalid_item_count": len(invalid_items),
        "invalid_items": invalid_items,
        "per_paper": sorted(per_paper, key=lambda row: row["paper_id"]),
    }
    if questions_output is not None:
        questions_output.parent.mkdir(parents=True, exist_ok=True)
        questions_output.write_text(
            "".join(
                json.dumps(item, ensure_ascii=False) + "\n"
                for item in exported_questions
            )
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question-dir", required=True, type=Path)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--questions-jsonl", type=Path)
    args = parser.parse_args()
    result = evaluate(args.question_dir, args.source_dir, args.questions_jsonl)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        f"[evaluate-reader-questions] papers={result['output_papers']}/"
        f"{result['source_papers']} questions={result['total_questions']} "
        f"grounding={result['exact_grounding_rate']:.1%} "
        f"invalid={result['invalid_item_count']}"
    )
    if result["invalid_item_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
