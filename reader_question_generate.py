"""Generate high-recall, paper-grounded questions that mimic active scientific reading."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from llm_client import TruncatedError, chat_json, provider_info
from role_question_extract import (
    READER_INTENTS,
    READER_QUESTION_TYPES,
    _link_questions_to_roles,
    _reader_question_id,
    _reading_chunks,
    _validate_reconciled,
)

SCHEMA_VERSION = "reader-question-3.0"
READING_STEPS = {
    "clarify",
    "inspect_choice",
    "trace_mechanism",
    "test_evidence",
    "compare",
    "assess_relevance",
    "change_variable",
    "find_boundary",
    "identify_gap",
    "plan_follow_up",
}
RELEVANCE_LEVELS = {"direct", "adjacent", "exploratory"}
RECENT_QUESTION_LIMIT = 12
_SPACE_RE = re.compile(r"\s+")

_SYSTEM = """You are simulating the questions an expert materials scientist naturally asks while
reading a research paper. High recall is the goal: capture the stream of useful curiosity now;
relevance filtering happens later.

For each meaningful claim, method choice, material, parameter, comparison, mechanism, figure,
result, assumption, or limitation in CURRENT PASSAGE, ask distinct questions such as:
- What exactly does this mean, refer to, or measure?
- What material, composition, instrument, model, parameter, or procedure are they using?
- Why did they choose it instead of an alternative?
- Why might this work, and what evidence supports that explanation?
- Is the evidence sufficient, controlled, and consistent with the proposed mechanism?
- How does it compare with a baseline, another alloy, or prior work?
- Is it relevant or transferable to my material, process, scale, or service condition?
- If composition, temperature, time, atmosphere, load, or processing changed, would it still work?
- Where does it stop working, and what failure mode or confounder matters?
- What detail is missing for replication?
- What should I check next in this paper or in a follow-up experiment?

Generate {target_min} to {target_max} questions unless the passage truly cannot support that many.
Multiple questions may arise from one sentence when they represent different thoughts. Do not cap
the output by category. Do not reject a question merely because it is exploratory or may be
answered later in the paper.

Context state is provided only to maintain continuity and avoid exact repetition. Every question
must be triggered by CURRENT PASSAGE, and evidence_span must be one exact contiguous substring
copied from CURRENT PASSAGE. Never use context-state text as evidence. Never insert ellipses,
normalize notation, join separated text, or invent a paper detail.

Use these reading_step values:
clarify, inspect_choice, trace_mechanism, test_evidence, compare, assess_relevance,
change_variable, find_boundary, identify_gap, plan_follow_up.

Use these question_type values:
clarification, rationale, mechanism, method, evidence, comparison, relevance, counterfactual,
boundary, assumption, limitation, transfer, replication, follow_up.

Use these reader_intent values: understand, evaluate, apply, replicate, extend.
Use these relevance values:
- direct: directly about the paper's system, claim, method, or conclusion;
- adjacent: transfers or compares it to a closely related system or condition;
- exploratory: a farther extension still concretely triggered by the passage.

Each question must:
- end in "?";
- contain one primary thought in at most 60 words;
- include a short rationale explaining why a reader asks it;
- include exactly one verbatim evidence_span from CURRENT PASSAGE;
- assign confidence from 0 to 1 for how clearly the passage triggers the question.

Return JSON only:
{{"questions": [
  {{"question": "...?", "question_type": "...", "reading_step": "...",
   "reader_intent": "...", "relevance": "...", "rationale": "...",
   "evidence_span": "...", "confidence": 0.0}}
]}}"""


@dataclass
class PaperResult:
    paper_id: str
    questions: list[dict[str, Any]]
    rejected_items: list[dict[str, Any]]
    chunks_processed: int
    model_calls: int
    resumed_chunks: int


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def _source_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _normalized_question(text: str) -> str:
    return _SPACE_RE.sub(" ", text).strip().casefold()


def _target_range(word_count: int) -> tuple[int, int]:
    minimum = max(3, min(16, word_count // 35))
    maximum = max(minimum + 4, min(30, word_count // 18))
    return minimum, maximum


def _context_state(
    paper_title: str,
    chunk_index: int,
    chunk_count: int,
    section: str,
    previous_tail: str,
    recent_questions: list[dict[str, Any]],
) -> str:
    recent = [
        {
            "question": item["question"],
            "question_type": item["question_type"],
            "reading_step": item["reading_step"],
        }
        for item in recent_questions[-RECENT_QUESTION_LIMIT:]
    ]
    return json.dumps({
        "paper_title": paper_title,
        "reading_progress": f"{chunk_index + 1}/{chunk_count}",
        "current_section": section,
        "previous_passage_tail_for_continuity_only": previous_tail,
        "recent_questions_to_avoid_exact_repetition": recent,
    }, ensure_ascii=False)


def _validate_chunk_questions(
    payload: Any,
    paper_id: str,
    section: str,
    chunk_index: int,
    chunk_text: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = payload.get("questions", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        return [], [{
            "stage": "reader_question_generation",
            "section": section,
            "chunk_index": chunk_index,
            "reason": "questions must be a list",
            "candidate": rows,
        }]
    accepted = []
    rejected = []
    seen = set()
    for row_index, row in enumerate(rows):
        reason = ""
        if not isinstance(row, dict):
            reason = "question must be an object"
        else:
            question = str(row.get("question", "")).strip()
            question_type = str(row.get("question_type", "")).strip().lower()
            reading_step = str(row.get("reading_step", "")).strip().lower()
            reader_intent = str(row.get("reader_intent", "")).strip().lower()
            relevance = str(row.get("relevance", "")).strip().lower()
            rationale = str(row.get("rationale", "")).strip()
            evidence_span = str(row.get("evidence_span", "")).strip()
            try:
                confidence = float(row.get("confidence", 1.0))
            except (TypeError, ValueError):
                confidence = -1
            if not question.endswith("?"):
                reason = "question must end with a question mark"
            elif len(question.split()) > 60:
                reason = "question must contain at most 60 words"
            elif question_type not in READER_QUESTION_TYPES:
                reason = f"unknown question_type: {question_type!r}"
            elif reading_step not in READING_STEPS:
                reason = f"unknown reading_step: {reading_step!r}"
            elif reader_intent not in READER_INTENTS:
                reason = f"unknown reader_intent: {reader_intent!r}"
            elif relevance not in RELEVANCE_LEVELS:
                reason = f"unknown relevance: {relevance!r}"
            elif not rationale:
                reason = "question rationale is empty"
            elif not evidence_span:
                reason = "question evidence_span is empty"
            elif evidence_span not in chunk_text:
                reason = f"non-verbatim evidence_span: {evidence_span[:120]!r}"
            elif not 0 <= confidence <= 1:
                reason = "question confidence must be between 0 and 1"
            elif _normalized_question(question) in seen:
                reason = "exact duplicate question in chunk"
            else:
                seen.add(_normalized_question(question))
                accepted.append({
                    "question_id": _reader_question_id(paper_id, question),
                    "question": question,
                    "question_type": question_type,
                    "reading_step": reading_step,
                    "reader_intent": reader_intent,
                    "relevance": relevance,
                    "rationale": rationale,
                    "source_section": section,
                    "chunk_index": chunk_index,
                    "grounded_role_refs": [],
                    "evidence_spans": [evidence_span],
                    "confidence": confidence,
                })
        if reason:
            rejected.append({
                "stage": "reader_question_generation",
                "section": section,
                "chunk_index": chunk_index,
                "model_item_index": row_index,
                "reason": reason,
                "candidate": row,
            })
    return accepted, rejected


def _generate_chunk(
    paper_id: str,
    paper_title: str,
    chunk: Any,
    chunk_count: int,
    previous_tail: str,
    recent_questions: list[dict[str, Any]],
    depth: int = 0,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    words = chunk.text.split()
    target_min, target_max = _target_range(len(words))
    system = _SYSTEM.format(target_min=target_min, target_max=target_max)
    user = (
        "CONTEXT STATE (continuity only; not evidence):\n"
        f"{_context_state(paper_title, chunk.index, chunk_count, chunk.section, previous_tail, recent_questions)}\n\n"
        f"--- CURRENT PASSAGE: {chunk.section} ---\n{chunk.text}"
    )
    try:
        payload = chat_json(system, user, max_tokens=8000)
    except TruncatedError:
        if depth >= 3 or len(words) < 120:
            raise
        midpoint = len(words) // 2
        from chunking import Chunk
        matches = list(re.finditer(r"\S+", chunk.text))
        split_offset = matches[midpoint].start()
        first = Chunk(f"{chunk.section}/a", chunk.text[:split_offset].rstrip(), chunk.index)
        second = Chunk(f"{chunk.section}/b", chunk.text[split_offset:].lstrip(), chunk.index)
        first_questions, first_rejected, first_calls = _generate_chunk(
            paper_id, paper_title, first, chunk_count, previous_tail, recent_questions, depth + 1
        )
        second_questions, second_rejected, second_calls = _generate_chunk(
            paper_id,
            paper_title,
            second,
            chunk_count,
            " ".join(words[max(0, midpoint - 80):midpoint]),
            recent_questions + first_questions,
            depth + 1,
        )
        return (
            first_questions + second_questions,
            first_rejected + second_rejected,
            first_calls + second_calls,
        )
    questions, rejected = _validate_chunk_questions(
        payload, paper_id, chunk.section, chunk.index, chunk.text
    )
    return questions, rejected, 1


def _load_title(papers_dir: Path, paper_id: str) -> str:
    metadata_path = papers_dir / paper_id / "metadata.json"
    if not metadata_path.exists():
        return paper_id
    metadata = json.loads(metadata_path.read_text())
    return str(metadata.get("title") or paper_id)


def _load_roles(papers_dir: Path, paper_id: str, full_text: str) -> dict[str, list[dict]]:
    roles_path = papers_dir / paper_id / "output" / "roles.json"
    payload = json.loads(roles_path.read_text())
    reconciled, rejected = _validate_reconciled(payload.get("reconciled_by_role"), full_text)
    if rejected:
        raise ValueError(f"{paper_id} has {len(rejected)} invalid persisted role items")
    return reconciled


def generate_paper(
    source_path: Path,
    papers_dir: Path,
    checkpoint_dir: Path,
) -> PaperResult:
    paper_id = source_path.stem
    full_text = source_path.read_text(encoding="utf-8", errors="ignore")
    chunks = _reading_chunks(full_text)
    source_digest = _source_hash(full_text)
    checkpoint_path = checkpoint_dir / f"{paper_id}.json"
    checkpoint: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "paper_id": paper_id,
        "source_sha256": source_digest,
        "completed_chunks": {},
    }
    if checkpoint_path.exists():
        loaded = json.loads(checkpoint_path.read_text())
        if (
            loaded.get("schema_version") == SCHEMA_VERSION
            and loaded.get("source_sha256") == source_digest
        ):
            checkpoint = loaded

    paper_title = _load_title(papers_dir, paper_id)
    questions = []
    rejected_items = []
    model_calls = 0
    resumed_chunks = 0
    completed = checkpoint["completed_chunks"]
    for position, chunk in enumerate(chunks):
        key = str(position)
        chunk_digest = _source_hash(chunk.text)
        saved = completed.get(key)
        if saved and saved.get("chunk_sha256") == chunk_digest:
            chunk_questions = saved.get("questions", [])
            chunk_rejected = saved.get("rejected_items", [])
            resumed_chunks += 1
        else:
            previous_words = chunks[position - 1].text.split() if position else []
            chunk_questions, chunk_rejected, calls = _generate_chunk(
                paper_id,
                paper_title,
                chunk,
                len(chunks),
                " ".join(previous_words[-100:]),
                questions,
            )
            model_calls += calls
            completed[key] = {
                "chunk_sha256": chunk_digest,
                "section": chunk.section,
                "questions": chunk_questions,
                "rejected_items": chunk_rejected,
            }
            _atomic_json(checkpoint_path, checkpoint)
        questions.extend(chunk_questions)
        rejected_items.extend(chunk_rejected)

    unique_questions = []
    seen = set()
    for question in questions:
        key = _normalized_question(question["question"])
        if key in seen:
            rejected_items.append({
                "stage": "paper_deduplication",
                "reason": "exact duplicate question across overlapping chunks",
                "candidate": question,
            })
            continue
        seen.add(key)
        unique_questions.append(question)
    reconciled = _load_roles(papers_dir, paper_id, full_text)
    _link_questions_to_roles(unique_questions, reconciled)
    return PaperResult(
        paper_id=paper_id,
        questions=unique_questions,
        rejected_items=rejected_items,
        chunks_processed=len(chunks),
        model_calls=model_calls,
        resumed_chunks=resumed_chunks,
    )


def _result_payload(result: PaperResult) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "paper_id": result.paper_id,
        "generation_mode": "high_recall_reader_questions",
        "steps": [
            "read overlapping paper passage",
            "carry recent paper-reading state",
            "generate many passage-triggered questions",
            "validate exact source grounding and schema",
            "remove exact duplicates only",
            "link questions to overlapping reconciled roles",
        ],
        "chunks_processed": result.chunks_processed,
        "model_calls": result.model_calls,
        "resumed_chunks": result.resumed_chunks,
        "questions": result.questions,
        "rejected_items": result.rejected_items,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--papers-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--checkpoint-dir", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--paper-id",
        action="append",
        help="Process only this paper ID; repeat to select multiple papers.",
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--install",
        action="store_true",
        help="Atomically replace each completed paper's output/questions.json.",
    )
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    files = sorted(args.input_dir.glob("*.txt"))
    if args.paper_id:
        selected = set(args.paper_id)
        files = [path for path in files if path.stem in selected]
        missing = selected - {path.stem for path in files}
        if missing:
            parser.error(f"paper IDs not found: {', '.join(sorted(missing))}")
    if args.limit:
        files = files[:args.limit]
    if args.resume:
        files = [
            path for path in files
            if not (args.out_dir / f"{path.stem}.json").exists()
        ]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    print(
        f"[reader-questions] provider={provider_info()} papers={len(files)} workers={args.workers}",
        file=sys.stderr,
    )

    def process(path: Path) -> tuple[PaperResult, float]:
        started = time.monotonic()
        result = generate_paper(path, args.papers_dir, args.checkpoint_dir)
        payload = _result_payload(result)
        _atomic_json(args.out_dir / f"{result.paper_id}.json", payload)
        if args.install:
            _atomic_json(
                args.papers_dir / result.paper_id / "output" / "questions.json",
                {
                    key: value
                    for key, value in payload.items()
                    if key != "rejected_items"
                },
            )
            _atomic_json(
                args.papers_dir / result.paper_id / "output" / "reader_question_rejections.json",
                {
                    "schema_version": SCHEMA_VERSION,
                    "paper_id": result.paper_id,
                    "rejected_items": result.rejected_items,
                },
            )
        return result, time.monotonic() - started

    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process, path): path for path in files}
        for future in as_completed(futures):
            path = futures[future]
            try:
                result, elapsed = future.result()
            except Exception as error:
                failures.append((path.stem, error))
                print(f"[reader-questions] ERROR {path.stem}: {error}", file=sys.stderr)
                continue
            print(
                f"[reader-questions] {result.paper_id}: chunks={result.chunks_processed} "
                f"questions={len(result.questions)} calls={result.model_calls} "
                f"resumed={result.resumed_chunks} rejected={len(result.rejected_items)} "
                f"seconds={elapsed:.1f}",
                file=sys.stderr,
            )
    if failures:
        print(f"[reader-questions] ERROR: {len(failures)} papers failed", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
