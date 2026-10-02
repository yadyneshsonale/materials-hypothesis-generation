"""Extract the 11 argumentative roles and grounded decision questions from papers."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from chunking import Chunk, split_into_chunks
from llm_client import TruncatedError, chat_json, provider_info
from roles import ROLE_KEYS, role_table_prompt

SCHEMA_VERSION = "role-question-1.0"
QUESTION_TYPES = {"baseline", "causal", "intervention", "boundary", "discrimination"}
MAX_SPLIT_DEPTH = 3
MAX_FINAL_ITEMS_PER_ROLE = 24

_EXTRACT_SYSTEM = """You extract argumentative roles from one section of a materials-science paper.

Use exactly these roles:
{roles}

Keep roles distinct. In particular:
- a measured result is not automatically a causal mechanism;
- a study objective is not a hypothesis;
- an unusual result is not a contradiction unless it conflicts with a named expectation;
- a test condition is not a constraint unless it limits design, validity, or operation;
- cited work belongs only in prior_approach, prior_limitation, or inspiration_source unless the
  current paper explicitly tests or contradicts it.

Each evidence_span must be one exact, contiguous substring copied from the supplied section.
Never paraphrase the evidence span, insert ellipses, normalize notation, or join separated text.
The content field should be a concise interpretation of that exact span.

Return JSON:
{{"items": [
  {{"role": "<role_key>", "content": "<concise claim>",
    "evidence_span": "<exact source substring>"}}
]}}

Return an empty items list when the section contains no high-signal role evidence. Do not fill
roles to meet a quota."""

_SECTION_GUIDANCE = """Section guidance:
- Introduction/background: emphasize problem, prior approach, prior limitation, and inspiration.
- Methods: emphasize explicitly rejected alternatives and genuine design/validity constraints.
- Results: emphasize measured evidence and causal claims directly supported by the paper.
- Discussion/conclusion: emphasize mechanisms, testable hypotheses, and explicit contradictions.
Claims about the current paper may occur in any section, so use definitions rather than location."""

_FINALIZE_SYSTEM = """You reconcile all 11 argumentative roles for one materials-science paper and
form grounded decision questions for hypothesis generation.

A DECISION QUESTION is a specific, answerable, and falsifiable information need whose answer would
change a materials-design choice, causal-mechanism choice, boundary condition, or experiment.
It is not a topic label, a request to summarize the paper, a vague invitation for future work, a
yes/no question without a discriminator, or a restatement of an already reported result.

Allowed question types:
- baseline: asks for a quantitative reference value under a named regime;
- causal: asks which linked mechanism explains an outcome and how it can be tested;
- intervention: asks which controllable composition/process change improves a named outcome;
- boundary: asks where a mechanism or benefit weakens, reverses, or fails;
- discrimination: asks which measurement distinguishes competing explanations.

Reconcile role candidates by merging only genuine duplicates. Never merge claims from different
materials, treatments, temperatures, environments, or loading regimes. Preserve exact source
spans. Keep conflicting claims separate and mark them conflicting. Assign each claim to its single
best role unless the source explicitly performs two different argumentative functions. Apply these
strict rare-role tests:
- inspiration_source requires an explicit analogy, borrowed method, or prior finding that shaped
  the approach; a methodological need or benefit is not inspiration;
- hypothesis_statement requires a prospective, testable prediction of material behavior or an
  intervention-to-outcome relationship; a study objective, expected measurement-method utility,
  or post-hoc attribution of an observed result is not a hypothesis;
- rejected_alternative requires an explicit choice not to use an option and the reason;
- contradiction requires source spans that identify both this paper's result and the conflicting
  prior claim or accepted expectation; absence or novelty alone is insufficient.

Generate zero to five decision questions. Every question must:
1. name the material/system, intervention or mechanism, property, and operating regime when known;
2. state why answering it changes a research decision;
3. specify the measurements, comparison, or observations required to answer it;
4. cite at least one reconciled role as '<role>:<zero-based-index>';
5. be supported by exact source evidence spans; and
6. ask one primary uncertainty in at most 45 words and end with a question mark.

Prefer questions grounded by at least two complementary roles, such as a limitation plus evidence,
or a mechanism plus contradiction. Do not invent an evidence gap that the role candidates do not
support. Do not introduce a material, mechanism, intervention, threshold, or comparison absent from
the cited roles. Phrase speculative alternatives as measurements to perform, not assumed facts.

Return JSON with every role key present:
{
  "reconciled_by_role": {
    "<role_key>": [
      {"content": "...", "evidence_spans": ["exact source text"],
       "conflicting": false}
    ]
  },
  "questions": [
    {
      "question": "...?",
      "question_type": "baseline|causal|intervention|boundary|discrimination",
      "rationale": "...",
      "decision_use": "...",
      "grounded_role_refs": ["<role>:<index>"],
      "answer_requirements": ["specific measurement or comparison"],
      "evidence_spans": ["exact source text"],
      "confidence": 0.0
    }
  ]
}"""


@dataclass
class RoleQuestionRecord:
    paper_id: str
    raw_by_role: dict[str, list[dict[str, Any]]] = field(
        default_factory=lambda: {role: [] for role in ROLE_KEYS}
    )
    reconciled_by_role: dict[str, list[dict[str, Any]]] = field(
        default_factory=lambda: {role: [] for role in ROLE_KEYS}
    )
    questions: list[dict[str, Any]] = field(default_factory=list)
    rejected_items: list[dict[str, Any]] = field(default_factory=list)
    chunks_processed: int = 0


def _question_id(paper_id: str, question: str) -> str:
    digest = hashlib.sha256(f"{paper_id}\0{question}".encode()).hexdigest()[:16]
    return f"{paper_id}::decision_question::{digest}"


def _extract_chunk(
    chunk: Chunk,
    paper_id: str,
    depth: int = 0,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    user = f"{_SECTION_GUIDANCE}\n\n--- SECTION: {chunk.section} ---\n{chunk.text}"
    try:
        result = chat_json(
            _EXTRACT_SYSTEM.format(roles=role_table_prompt()),
            user,
            max_tokens=8000,
        )
    except TruncatedError:
        lines = chunk.text.splitlines()
        if depth >= MAX_SPLIT_DEPTH or len(lines) < 4:
            raise
        midpoint = len(lines) // 2
        first = Chunk(f"{chunk.section}/a", "\n".join(lines[:midpoint]), chunk.index)
        second = Chunk(f"{chunk.section}/b", "\n".join(lines[midpoint:]), chunk.index)
        first_items, first_rejected = _extract_chunk(first, paper_id, depth + 1)
        second_items, second_rejected = _extract_chunk(second, paper_id, depth + 1)
        return first_items + second_items, first_rejected + second_rejected

    rows = result.get("items", []) if isinstance(result, dict) else []
    if not isinstance(rows, list):
        raise ValueError(f"model returned non-list items for section {chunk.section}")
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        reason = ""
        if not isinstance(row, dict):
            reason = "role item must be an object"
        else:
            role = str(row.get("role", ""))
            content = str(row.get("content", "")).strip()
            evidence_span = str(row.get("evidence_span", "")).strip()
            if role not in ROLE_KEYS:
                reason = f"unknown role: {role!r}"
            elif not content:
                reason = "role content is empty"
            elif not evidence_span:
                reason = "role evidence_span is empty"
            elif evidence_span not in chunk.text:
                reason = f"non-verbatim role evidence_span: {evidence_span[:120]!r}"
            else:
                accepted.append({
                    "role": role,
                    "content": content,
                    "evidence_span": evidence_span,
                    "source_section": chunk.section,
                })
        if reason:
            rejected.append({
                "stage": "chunk_extraction",
                "section": chunk.section,
                "model_item_index": index,
                "reason": reason,
                "candidate": row,
            })
    return accepted, rejected


def _validate_reconciled(
    payload: Any,
    full_text: str,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    reconciled, rejected, _ = _validate_reconciled_with_ref_map(payload, full_text)
    return reconciled, rejected


def _validate_reconciled_with_ref_map(
    payload: Any,
    full_text: str,
) -> tuple[
    dict[str, list[dict[str, Any]]],
    list[dict[str, Any]],
    dict[str, str],
]:
    source = payload if isinstance(payload, dict) else {}
    reconciled: dict[str, list[dict[str, Any]]] = {role: [] for role in ROLE_KEYS}
    rejected: list[dict[str, Any]] = []
    reference_map: dict[str, str] = {}
    for role in ROLE_KEYS:
        rows = source.get(role, [])
        if not isinstance(rows, list):
            rejected.append({
                "stage": "reconciliation",
                "role": role,
                "reason": "reconciled role value must be a list",
                "candidate": rows,
            })
            continue
        for index, row in enumerate(rows):
            reason = ""
            if not isinstance(row, dict):
                reason = "reconciled role item must be an object"
            else:
                content = str(row.get("content", "")).strip()
                spans = row.get("evidence_spans", [])
                if not content:
                    reason = "reconciled role content is empty"
                elif not isinstance(spans, list) or not spans or not all(
                    isinstance(span, str) and span.strip() for span in spans
                ):
                    reason = "reconciled evidence_spans must be a non-empty string list"
                else:
                    normalized_spans = [span.strip() for span in spans]
                    missing = [span for span in normalized_spans if span not in full_text]
                    if missing:
                        reason = f"non-verbatim reconciled span: {missing[0][:120]!r}"
                    else:
                        accepted_index = len(reconciled[role])
                        reconciled[role].append({
                            "content": content,
                            "evidence_spans": normalized_spans,
                            "conflicting": bool(row.get("conflicting", False)),
                        })
                        reference_map[f"{role}:{index}"] = f"{role}:{accepted_index}"
            if reason:
                rejected.append({
                    "stage": "reconciliation",
                    "role": role,
                    "model_item_index": index,
                    "reason": reason,
                    "candidate": row,
                })
    return reconciled, rejected, reference_map


def _validate_questions(
    rows: Any,
    paper_id: str,
    full_text: str,
    reconciled: dict[str, list[dict[str, Any]]],
    reference_map: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(rows, list):
        return [], [{
            "stage": "question_generation",
            "reason": "questions must be a list",
            "candidate": rows,
        }]
    valid_refs = {
        f"{role}:{index}"
        for role, items in reconciled.items()
        for index in range(len(items))
    }
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        reason = ""
        if not isinstance(row, dict):
            reason = "question must be an object"
        else:
            question = str(row.get("question", "")).strip()
            question_type = str(row.get("question_type", "")).strip().lower()
            rationale = str(row.get("rationale", "")).strip()
            decision_use = str(row.get("decision_use", "")).strip()
            raw_refs = row.get("grounded_role_refs", [])
            refs = (
                [reference_map.get(str(ref), str(ref)) for ref in raw_refs]
                if isinstance(raw_refs, list) and reference_map is not None
                else raw_refs
            )
            requirements = row.get("answer_requirements", [])
            spans = row.get("evidence_spans", [])
            try:
                confidence = float(row.get("confidence", 1.0))
            except (TypeError, ValueError):
                confidence = -1
            if not question.endswith("?"):
                reason = "decision question must end with a question mark"
            elif len(question.split()) > 50:
                reason = "decision question must contain at most 50 words"
            elif question_type not in QUESTION_TYPES:
                reason = f"unknown question_type: {question_type!r}"
            elif not rationale:
                reason = "question rationale is empty"
            elif not decision_use:
                reason = "question decision_use is empty"
            elif not isinstance(refs, list) or not refs:
                reason = "question must reference at least one reconciled role"
            elif any(str(ref) not in valid_refs for ref in refs):
                reason = "question contains an invalid grounded_role_ref"
            elif not isinstance(requirements, list) or not any(
                isinstance(item, str) and item.strip() for item in requirements
            ):
                reason = "question answer_requirements must be a non-empty string list"
            elif not isinstance(spans, list) or not spans or not all(
                isinstance(span, str) and span.strip() for span in spans
            ):
                reason = "question evidence_spans must be a non-empty string list"
            elif any(span.strip() not in full_text for span in spans):
                reason = "question contains a non-verbatim evidence span"
            elif not 0 <= confidence <= 1:
                reason = "question confidence must be between 0 and 1"
            elif question.casefold() in seen:
                reason = "duplicate decision question"
            else:
                seen.add(question.casefold())
                accepted.append({
                    "question_id": _question_id(paper_id, question),
                    "question": question,
                    "question_type": question_type,
                    "rationale": rationale,
                    "decision_use": decision_use,
                    "grounded_role_refs": [str(ref) for ref in refs],
                    "answer_requirements": [
                        str(item).strip() for item in requirements if str(item).strip()
                    ],
                    "evidence_spans": [span.strip() for span in spans],
                    "confidence": confidence,
                })
        if reason:
            rejected.append({
                "stage": "question_generation",
                "model_item_index": index,
                "reason": reason,
                "candidate": row,
            })
    return accepted, rejected


def extract_role_questions(paper_id: str, full_text: str) -> RoleQuestionRecord:
    record = RoleQuestionRecord(paper_id)
    for chunk in split_into_chunks(full_text):
        items, rejected = _extract_chunk(chunk, paper_id)
        for item in items:
            record.raw_by_role[item["role"]].append(item)
        record.rejected_items.extend(rejected)
        record.chunks_processed += 1

    bounded = {
        role: items[:MAX_FINAL_ITEMS_PER_ROLE]
        for role, items in record.raw_by_role.items()
    }
    user = (
        f"PAPER ID: {paper_id}\n\n"
        "ROLE CANDIDATES:\n"
        f"{json.dumps(bounded, ensure_ascii=False)}"
    )
    result = chat_json(_FINALIZE_SYSTEM, user, max_tokens=12000)
    if not isinstance(result, dict):
        raise ValueError("model returned a non-object final role/question payload")
    reconciled, role_rejected, reference_map = _validate_reconciled_with_ref_map(
        result.get("reconciled_by_role"),
        full_text,
    )
    questions, question_rejected = _validate_questions(
        result.get("questions"),
        paper_id,
        full_text,
        reconciled,
        reference_map,
    )
    record.reconciled_by_role = reconciled
    record.questions = questions
    record.rejected_items.extend(role_rejected)
    record.rejected_items.extend(question_rejected)
    return record


def record_to_dict(record: RoleQuestionRecord) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "paper_id": record.paper_id,
        "chunks_processed": record.chunks_processed,
        "raw_by_role": record.raw_by_role,
        "reconciled_by_role": record.reconciled_by_role,
        "questions": record.questions,
        "rejected_items": record.rejected_items,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")

    files = sorted(args.input_dir.glob("*.txt"))
    if args.limit:
        files = files[:args.limit]
    if args.resume:
        files = [
            path for path in files
            if not (args.out_dir / f"{path.stem}.json").exists()
        ]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    print(
        f"[role-question-extract] provider={provider_info()} papers={len(files)}",
        file=sys.stderr,
    )

    def process(path: Path) -> tuple[str, int, int, int, int, float]:
        started = time.monotonic()
        text = path.read_text(encoding="utf-8", errors="ignore")
        record = extract_role_questions(path.stem, text)
        destination = args.out_dir / f"{path.stem}.json"
        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(record_to_dict(record), indent=2, ensure_ascii=False) + "\n"
        )
        temporary.replace(destination)
        role_items = sum(len(items) for items in record.reconciled_by_role.values())
        return (
            record.paper_id,
            record.chunks_processed,
            role_items,
            len(record.questions),
            len(record.rejected_items),
            time.monotonic() - started,
        )

    failures: list[tuple[str, Exception]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process, path): path for path in files}
        for future in as_completed(futures):
            source = futures[future]
            try:
                paper_id, chunks, roles, questions, rejected, elapsed = future.result()
            except Exception as error:
                failures.append((source.stem, error))
                print(
                    f"[role-question-extract] ERROR {source.stem}: {error}",
                    file=sys.stderr,
                )
                continue
            print(
                f"[role-question-extract] {paper_id}: chunks={chunks} roles={roles} "
                f"questions={questions} rejected={rejected} seconds={elapsed:.1f}",
                file=sys.stderr,
            )
    if failures:
        print(
            f"[role-question-extract] ERROR: {len(failures)} papers failed",
            file=sys.stderr,
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
