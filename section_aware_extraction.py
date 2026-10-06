"""Generate cross-section questions and research threads from grounded paper evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chunking import Chunk, split_into_chunks
from hypothesis_evidence_v2 import atomic_json, load_evidence
from llm_client import LLMError, chat_json, provider_info

SCHEMA_VERSION = "section-aware-extraction-1.0"
TRIGGERS_PER_CALL = 2
MAX_RETRIEVED_CHUNKS = 4
MAX_CHUNK_EXCERPT_CHARS = 2400
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9.+-]*", re.IGNORECASE)
_REF_RE = re.compile(r"\b(?:fig(?:ure)?|table|section)\s*\.?\s*([a-z]?\d+[a-z]?)", re.IGNORECASE)

_SYSTEM = """You are a section-aware materials-science data extraction agent. For each supplied
grounded evidence trigger, inspect the retrieved passages from other parts of the SAME paper.
First reject passages that do not describe the same sample, material state, experiment, figure,
table, or directly relevant scientific comparison. Similar wording alone is not enough.

Then create one to three decision-relevant questions per trigger. Prefer questions that connect
processing, structure, test conditions, measurement, comparison, mechanism, boundary, or
limitation across sections. Do not ask a question that the supplied context already answers
completely. Instead record the known context and ask only about the unresolved scientific issue.
Questions should help hypothesis generation, mechanism discrimination, transfer, boundary
identification, or experiment design; omit superficial reading questions.

Use only supplied content. Never use outside knowledge. Every cross-section link must cite an exact
chunk_id and one or more exact contiguous spans from that chunk. Every question must cite the
trigger evidence_unit_id and source chunk IDs. It is valid to return no question when retrieval adds
no scientifically useful context.

Return JSON only:
{"triggers": [{
  "evidence_unit_id": "",
  "validated_links": [{
    "chunk_id": "", "relation": "method|sample_lineage|figure|table|mechanism|comparison|boundary",
    "evidence_spans": ["exact supplied span"], "reason": ""
  }],
  "questions": [{
    "question": "", "question_function":
      "explain_mechanism|test_evidence|compare|find_boundary|replicate|change_variable|transfer|plan_experiment",
    "why_it_matters": "", "known_context": "", "unresolved_information": "",
    "source_chunk_ids": [], "evidence_spans": ["exact supplied span"],
    "confidence": 0.0
  }],
  "research_thread": {
    "scientific_problem": "", "material_system": "", "sample_lineage": "",
    "intervention": "", "baseline": "", "conditions": "", "structure": "",
    "outcome": "", "mechanism": "", "alternative_explanations": [],
    "boundaries": [], "null_or_negative_results": [], "missing_information": [],
    "hypothesis_value": ""
  }
}]}.

Return exactly one trigger object for each supplied evidence_unit_id. Do not invent IDs."""


def _tokens(value: Any) -> Counter[str]:
    if isinstance(value, dict):
        text = " ".join(str(item) for item in value.values())
    elif isinstance(value, list):
        text = " ".join(str(item) for item in value)
    else:
        text = str(value or "")
    return Counter(
        token.casefold()
        for token in _TOKEN_RE.findall(text)
        if len(token) > 2
    )


def _chunk_id(paper_id: str, chunk: Chunk) -> str:
    digest = hashlib.sha256(chunk.text.encode()).hexdigest()[:10]
    section = re.sub(r"[^a-z0-9]+", "_", chunk.section.casefold()).strip("_")
    return f"{paper_id}::chunk::{chunk.index:03d}::{section}::{digest}"


def _content_types(text: str) -> list[str]:
    types = ["text"]
    if re.search(r"\bfig(?:ure)?\s*\.?\s*\d", text, re.IGNORECASE):
        types.append("figure_caption_or_reference")
    if re.search(r"\btable\s*\.?\s*\d", text, re.IGNORECASE):
        types.append("table_or_reference")
    return types


def build_paper_map(paper_id: str, text: str) -> dict[str, Any]:
    chunks = []
    for chunk in split_into_chunks(text):
        chunks.append({
            "chunk_id": _chunk_id(paper_id, chunk),
            "section": chunk.section,
            "chunk_index": chunk.index,
            "content_types": _content_types(chunk.text),
            "text": chunk.text,
            "text_sha256": hashlib.sha256(chunk.text.encode()).hexdigest(),
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "paper_id": paper_id,
        "chunks": chunks,
    }


def _anchor_ids(unit: dict[str, Any], chunks: list[dict[str, Any]]) -> list[str]:
    spans = [str(span) for span in unit.get("evidence_spans", []) if str(span).strip()]
    return [
        chunk["chunk_id"]
        for chunk in chunks
        if any(span in chunk["text"] for span in spans)
    ]


def _compact_unit(unit: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_unit_id": unit["unit_id"],
        "source_section": unit["source_section"],
        "claim_ownership": unit["claim_ownership"],
        "sample": unit["sample"],
        "process_steps": unit["process_steps"],
        "structure_observations": unit["structure_observations"],
        "test_conditions": unit["test_conditions"],
        "measurements": unit["measurements"],
        "comparison": unit["comparison"],
        "mechanisms": unit["mechanisms"],
        "boundaries": unit["boundaries"],
        "limitations": unit["limitations"],
        "evidence_spans": unit["evidence_spans"],
    }


def retrieve_chunks(
    unit: dict[str, Any],
    chunks: list[dict[str, Any]],
    *,
    limit: int = MAX_RETRIEVED_CHUNKS,
) -> tuple[list[str], list[dict[str, Any]]]:
    anchors = _anchor_ids(unit, chunks)
    anchor_set = set(anchors)
    query = _tokens(_compact_unit(unit))
    references = {
        match.group(0).casefold().replace(".", "")
        for span in unit.get("evidence_spans", [])
        for match in _REF_RE.finditer(str(span))
    }
    sample = unit.get("sample", {})
    exact_terms = {
        str(sample.get(key, "")).strip().casefold()
        for key in ("sample_id", "material_name", "nominal_composition")
        if str(sample.get(key, "")).strip()
    }
    source_section = str(unit.get("source_section", ""))
    scored: list[tuple[float, dict[str, Any]]] = []
    for chunk in chunks:
        if chunk["chunk_id"] in anchor_set:
            continue
        text_folded = chunk["text"].casefold()
        document = _tokens(chunk["text"])
        overlap = sum(min(count, document[token]) for token, count in query.items())
        if not overlap and not any(term in text_folded for term in exact_terms):
            continue
        score = overlap / max(sum(query.values()), 1)
        score += 2.0 * sum(term in text_folded for term in exact_terms)
        score += 3.0 * sum(reference in text_folded.replace(".", "") for reference in references)
        if chunk["section"] != source_section:
            score += 0.5
        if source_section.casefold().startswith("result") and chunk["section"].casefold() in {
            "methods", "materials", "materials and methods", "experimental",
            "discussion", "results and discussion",
        }:
            score += 0.75
        scored.append((score, chunk))
    scored.sort(key=lambda item: (-item[0], item[1]["chunk_index"]))
    return anchors, [row for _, row in scored[:limit]]


def _excerpt(
    text: str,
    query: Counter[str],
    required_spans: list[str],
) -> str:
    windows = []
    for span in required_spans:
        start = text.find(span)
        if start >= 0:
            left = max(0, start - 500)
            right = min(len(text), start + len(span) + 500)
            windows.append(text[left:right].strip())
    pieces = [
        piece.strip()
        for piece in re.split(r"\n{2,}|(?<=[.!?])\s+(?=[A-Z])", text)
        if piece.strip()
    ]
    ranked = sorted(
        pieces,
        key=lambda piece: (
            -sum(min(count, _tokens(piece)[token]) for token, count in query.items()),
            len(piece),
        ),
    )
    windows.extend(ranked[:8])
    selected = []
    used = 0
    for item in windows:
        if item in selected:
            continue
        remaining = MAX_CHUNK_EXCERPT_CHARS - used
        if remaining <= 0:
            break
        selected.append(item[:remaining])
        used += len(selected[-1]) + 2
    return "\n\n".join(selected)


def _compact_chunk(
    chunk: dict[str, Any],
    *,
    query: Counter[str],
    required_spans: list[str],
) -> dict[str, Any]:
    return {
        "chunk_id": chunk["chunk_id"],
        "section": chunk["section"],
        "content_types": chunk["content_types"],
        "text_excerpt": _excerpt(chunk["text"], query, required_spans),
    }


def _stable_question_id(paper_id: str, unit_id: str, question: str) -> str:
    digest = hashlib.sha256(
        json.dumps([unit_id, question], ensure_ascii=False).encode()
    ).hexdigest()[:16]
    return f"{paper_id}::cross_section_question::{digest}"


def _fallback_trigger(
    unit: dict[str, Any],
    anchor_ids: list[str],
    reason: str,
) -> dict[str, Any]:
    return {
        "evidence_unit_id": unit["unit_id"],
        "anchor_chunk_ids": anchor_ids,
        "validated_links": [],
        "questions": [],
        "research_thread": {
            "scientific_problem": "",
            "material_system": str(unit.get("sample", {}).get("material_name", "")),
            "sample_lineage": "",
            "intervention": "",
            "baseline": "",
            "conditions": "",
            "structure": "",
            "outcome": "",
            "mechanism": "",
            "alternative_explanations": [],
            "boundaries": [],
            "null_or_negative_results": [],
            "missing_information": [reason],
            "hypothesis_value": "",
        },
    }


def _validate_trigger(
    paper_id: str,
    unit: dict[str, Any],
    anchor_ids: list[str],
    retrieved: list[dict[str, Any]],
    generated: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rejected: list[dict[str, Any]] = []
    if not isinstance(generated, dict):
        return _fallback_trigger(unit, anchor_ids, "Model returned no valid trigger object."), [{
            "evidence_unit_id": unit["unit_id"],
            "reason": "trigger must be an object",
        }]
    allowed_chunks = {row["chunk_id"]: row for row in retrieved}
    allowed_chunks.update({
        row["chunk_id"]: row
        for row in retrieved
        if row["chunk_id"] in anchor_ids
    })
    links = []
    for link in generated.get("validated_links", []):
        if not isinstance(link, dict):
            continue
        chunk_id = str(link.get("chunk_id", ""))
        if chunk_id not in allowed_chunks:
            rejected.append({
                "evidence_unit_id": unit["unit_id"],
                "reason": f"unknown linked chunk_id={chunk_id}",
            })
            continue
        spans = [
            str(span).strip()
            for span in link.get("evidence_spans", [])
            if str(span).strip() and str(span).strip() in allowed_chunks[chunk_id]["text"]
        ]
        if not spans:
            rejected.append({
                "evidence_unit_id": unit["unit_id"],
                "reason": f"no exact linked spans for chunk_id={chunk_id}",
            })
            continue
        links.append({
            "chunk_id": chunk_id,
            "section": allowed_chunks[chunk_id]["section"],
            "relation": str(link.get("relation", "")).strip(),
            "evidence_spans": spans,
            "reason": str(link.get("reason", "")).strip(),
        })
    allowed_source_ids = set(anchor_ids) | {link["chunk_id"] for link in links}
    source_texts = {
        row["chunk_id"]: row["text"]
        for row in retrieved
        if row["chunk_id"] in allowed_source_ids
    }
    questions = []
    seen = set()
    for row in generated.get("questions", []):
        if not isinstance(row, dict):
            continue
        question = str(row.get("question", "")).strip()
        if not question or not question.endswith("?") or question.casefold() in seen:
            continue
        why_it_matters = str(row.get("why_it_matters", "")).strip()
        unresolved_information = str(row.get("unresolved_information", "")).strip()
        if not why_it_matters or not unresolved_information:
            rejected.append({
                "evidence_unit_id": unit["unit_id"],
                "question": question,
                "reason": "question requires why_it_matters and unresolved_information",
            })
            continue
        source_ids = [
            str(item) for item in row.get("source_chunk_ids", [])
            if str(item) in allowed_source_ids
        ]
        if not source_ids:
            source_ids = list(anchor_ids)
        spans = []
        for span in row.get("evidence_spans", []):
            span = str(span).strip()
            if span and any(span in source_texts.get(chunk_id, "") for chunk_id in source_ids):
                spans.append(span)
        trigger_spans = [
            str(span) for span in unit.get("evidence_spans", [])
            if any(str(span) in chunk["text"] for chunk in retrieved)
        ]
        if not spans:
            spans = trigger_spans[:2]
            source_ids = list(dict.fromkeys(source_ids + anchor_ids))
        if not spans:
            rejected.append({
                "evidence_unit_id": unit["unit_id"],
                "question": question,
                "reason": "question has no exact source span",
            })
            continue
        try:
            confidence = min(1.0, max(0.0, float(row.get("confidence", 0.0))))
        except (TypeError, ValueError):
            confidence = 0.0
        seen.add(question.casefold())
        questions.append({
            "question_id": _stable_question_id(paper_id, unit["unit_id"], question),
            "question": question,
            "question_function": str(row.get("question_function", "")).strip(),
            "why_it_matters": why_it_matters,
            "known_context": str(row.get("known_context", "")).strip(),
            "unresolved_information": unresolved_information,
            "source_chunk_ids": source_ids,
            "evidence_spans": spans,
            "confidence": confidence,
        })
    thread = generated.get("research_thread", {})
    if not isinstance(thread, dict):
        thread = {}
    string_fields = (
        "scientific_problem", "material_system", "sample_lineage", "intervention",
        "baseline", "conditions", "structure", "outcome", "mechanism", "hypothesis_value",
    )
    list_fields = (
        "alternative_explanations", "boundaries", "null_or_negative_results",
        "missing_information",
    )
    normalized_thread = {
        key: str(thread.get(key, "")).strip()
        for key in string_fields
    }
    normalized_thread.update({
        key: [
            str(item).strip()
            for item in thread.get(key, [])
            if str(item).strip()
        ] if isinstance(thread.get(key, []), list) else []
        for key in list_fields
    })
    normalized_thread["provenance"] = {
        "trigger_evidence_unit_id": unit["unit_id"],
        "supporting_chunk_ids": list(dict.fromkeys(
            anchor_ids + [link["chunk_id"] for link in links]
        )),
        "evidence_spans": list(dict.fromkeys(
            [
                str(span)
                for span in unit.get("evidence_spans", [])
                if str(span).strip()
            ]
            + [
                span
                for link in links
                for span in link["evidence_spans"]
            ]
        )),
    }
    return {
        "evidence_unit_id": unit["unit_id"],
        "anchor_chunk_ids": anchor_ids,
        "validated_links": links,
        "questions": questions,
        "research_thread": normalized_thread,
    }, rejected


@dataclass
class PaperResult:
    paper_id: str
    triggers: list[dict[str, Any]]
    rejected: list[dict[str, Any]]
    model_calls: int


def extract_paper(
    text_path: Path,
    evidence_path: Path,
    output_dir: Path,
    map_dir: Path,
    checkpoint_dir: Path,
    *,
    resume: bool,
    max_triggers: int | None = None,
) -> PaperResult:
    paper_id = text_path.stem
    destination = output_dir / f"{paper_id}.json"
    if resume and destination.exists():
        payload = json.loads(destination.read_text())
        return PaperResult(
            paper_id,
            payload.get("triggers", []),
            payload.get("rejected", []),
            0,
        )
    paper_map = build_paper_map(paper_id, text_path.read_text())
    atomic_json(map_dir / f"{paper_id}.json", paper_map)
    evidence_payload = json.loads(evidence_path.read_text())
    units = evidence_payload.get("evidence_units", [])
    if max_triggers is not None:
        units = units[:max_triggers]
    checkpoint_path = checkpoint_dir / f"{paper_id}.json"
    checkpoint = (
        json.loads(checkpoint_path.read_text())
        if resume and checkpoint_path.exists()
        else {"triggers": {}, "rejected": []}
    )
    stored = dict(checkpoint.get("triggers", {}))
    rejected = list(checkpoint.get("rejected", []))
    calls = 0
    chunks = paper_map["chunks"]
    for start in range(0, len(units), TRIGGERS_PER_CALL):
        batch = [unit for unit in units[start:start + TRIGGERS_PER_CALL] if unit["unit_id"] not in stored]
        if not batch:
            continue
        batch_inputs = []
        retrieval: dict[str, tuple[list[str], list[dict[str, Any]]]] = {}
        for unit in batch:
            anchors, candidates = retrieve_chunks(unit, chunks)
            all_chunks = [
                row for row in chunks
                if row["chunk_id"] in set(anchors)
            ] + candidates
            retrieval[unit["unit_id"]] = (anchors, all_chunks)
            query = _tokens(_compact_unit(unit))
            batch_inputs.append({
                "trigger": _compact_unit(unit),
                "anchor_chunk_ids": anchors,
                "retrieved_chunks": [
                    _compact_chunk(
                        row,
                        query=query,
                        required_spans=(
                            unit.get("evidence_spans", [])
                            if row["chunk_id"] in set(anchors)
                            else []
                        ),
                    )
                    for row in all_chunks
                ],
            })
        try:
            payload = chat_json(
                _SYSTEM,
                json.dumps({
                    "paper_id": paper_id,
                    "triggers": batch_inputs,
                }, ensure_ascii=False),
                max_tokens=10000,
            )
            calls += 1
            generated = {
                str(row.get("evidence_unit_id", "")): row
                for row in payload.get("triggers", [])
                if isinstance(row, dict)
            } if isinstance(payload, dict) else {}
        except LLMError as error:
            generated = {}
            rejected.append({"batch_start": start, "reason": str(error)})
        for unit in batch:
            anchors, supplied_chunks = retrieval[unit["unit_id"]]
            row, row_rejected = _validate_trigger(
                paper_id,
                unit,
                anchors,
                supplied_chunks,
                generated.get(unit["unit_id"]),
            )
            stored[unit["unit_id"]] = row
            rejected.extend(row_rejected)
        atomic_json(checkpoint_path, {
            "paper_id": paper_id,
            "triggers": stored,
            "rejected": rejected,
        })
    triggers = [stored[unit["unit_id"]] for unit in units]
    result = {
        "schema_version": SCHEMA_VERSION,
        "paper_id": paper_id,
        "provider": provider_info(),
        "trigger_count": len(triggers),
        "cross_section_link_count": sum(len(row["validated_links"]) for row in triggers),
        "question_count": sum(len(row["questions"]) for row in triggers),
        "triggers": triggers,
        "rejected": rejected,
    }
    atomic_json(destination, result)
    return PaperResult(paper_id, triggers, rejected, calls)


def run_corpus(
    text_dir: Path,
    evidence_dir: Path,
    output_dir: Path,
    map_dir: Path,
    checkpoint_dir: Path,
    *,
    workers: int,
    resume: bool,
    paper_ids: set[str] | None = None,
    max_triggers: int | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    map_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    paths = [
        path for path in sorted(text_dir.glob("PMC*.txt"))
        if (paper_ids is None or path.stem in paper_ids)
        and (evidence_dir / f"{path.stem}.json").exists()
    ]
    results = []
    failures = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                extract_paper,
                path,
                evidence_dir / f"{path.stem}.json",
                output_dir,
                map_dir,
                checkpoint_dir,
                resume=resume,
                max_triggers=max_triggers,
            ): path.stem
            for path in paths
        }
        for future in as_completed(futures):
            paper_id = futures[future]
            try:
                result = future.result()
                results.append(result)
                print(
                    f"[section-aware] {paper_id}: triggers={len(result.triggers)} "
                    f"questions={sum(len(row['questions']) for row in result.triggers)} "
                    f"links={sum(len(row['validated_links']) for row in result.triggers)} "
                    f"calls={result.model_calls}",
                    file=sys.stderr,
                )
            except Exception as error:
                failures.append({"paper_id": paper_id, "reason": str(error)})
    if failures:
        raise RuntimeError(f"{len(failures)} papers failed: {failures}")
    summary = {
        "schema_version": SCHEMA_VERSION,
        "papers": len(results),
        "triggers": sum(len(row.triggers) for row in results),
        "questions": sum(
            len(trigger["questions"])
            for row in results
            for trigger in row.triggers
        ),
        "cross_section_links": sum(
            len(trigger["validated_links"])
            for row in results
            for trigger in row.triggers
        ),
        "triggers_with_questions": sum(
            bool(trigger["questions"])
            for row in results
            for trigger in row.triggers
        ),
        "rejected_records": sum(len(row.rejected) for row in results),
    }
    atomic_json(output_dir / "summary.json", summary)
    return summary


def evaluate(
    text_dir: Path,
    evidence_dir: Path,
    output_dir: Path,
    result_path: Path,
) -> dict[str, Any]:
    evidence_lookup = {
        unit.unit_id: unit
        for unit in load_evidence(evidence_dir)
    }
    exact_spans = 0
    total_spans = 0
    unknown_evidence = 0
    unknown_chunks = 0
    invalid_thread_provenance = 0
    cross_section_questions = 0
    questions = 0
    links = 0
    triggers = 0
    papers = 0
    for path in sorted(output_dir.glob("PMC*.json")):
        payload = json.loads(path.read_text())
        paper_id = payload["paper_id"]
        paper_map = build_paper_map(paper_id, (text_dir / f"{paper_id}.txt").read_text())
        chunks = {row["chunk_id"]: row for row in paper_map["chunks"]}
        papers += 1
        for trigger in payload.get("triggers", []):
            triggers += 1
            unknown_evidence += trigger["evidence_unit_id"] not in evidence_lookup
            for link in trigger.get("validated_links", []):
                links += 1
                chunk = chunks.get(link["chunk_id"])
                unknown_chunks += chunk is None
                for span in link.get("evidence_spans", []):
                    total_spans += 1
                    exact_spans += bool(chunk and span in chunk["text"])
            provenance = trigger.get("research_thread", {}).get("provenance", {})
            invalid_thread_provenance += (
                provenance.get("trigger_evidence_unit_id") != trigger["evidence_unit_id"]
            )
            invalid_thread_provenance += sum(
                item not in chunks
                for item in provenance.get("supporting_chunk_ids", [])
            )
            for span in provenance.get("evidence_spans", []):
                total_spans += 1
                exact_spans += any(
                    span in chunks[item]["text"]
                    for item in provenance.get("supporting_chunk_ids", [])
                    if item in chunks
                )
            for question in trigger.get("questions", []):
                questions += 1
                source_sections = {
                    chunks[item]["section"]
                    for item in question.get("source_chunk_ids", [])
                    if item in chunks
                }
                cross_section_questions += len(source_sections) > 1
                for span in question.get("evidence_spans", []):
                    total_spans += 1
                    exact_spans += any(
                        item in chunks and span in chunks[item]["text"]
                        for item in question.get("source_chunk_ids", [])
                    )
    result = {
        "schema_version": SCHEMA_VERSION,
        "papers": papers,
        "triggers": triggers,
        "questions": questions,
        "cross_section_links": links,
        "cross_section_questions": cross_section_questions,
        "cross_section_question_rate": round(
            cross_section_questions / max(questions, 1), 4
        ),
        "exact_spans": exact_spans,
        "total_spans": total_spans,
        "grounding_rate": round(exact_spans / max(total_spans, 1), 4),
        "unknown_evidence_ids": unknown_evidence,
        "unknown_chunk_ids": unknown_chunks,
        "invalid_thread_provenance": invalid_thread_provenance,
        "verified": (
            exact_spans == total_spans
            and not unknown_evidence
            and not unknown_chunks
            and not invalid_thread_provenance
        ),
    }
    atomic_json(result_path, result)
    if not result["verified"]:
        raise ValueError(f"section-aware integrity failed: {result}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    extract = sub.add_parser("extract")
    extract.add_argument("--text-dir", type=Path, required=True)
    extract.add_argument("--evidence-dir", type=Path, required=True)
    extract.add_argument("--output-dir", type=Path, required=True)
    extract.add_argument("--map-dir", type=Path, required=True)
    extract.add_argument("--checkpoint-dir", type=Path, required=True)
    extract.add_argument("--workers", type=int, default=4)
    extract.add_argument("--resume", action="store_true")
    extract.add_argument("--paper-id", action="append")
    extract.add_argument("--max-triggers", type=int)
    evaluation = sub.add_parser("evaluate")
    evaluation.add_argument("--text-dir", type=Path, required=True)
    evaluation.add_argument("--evidence-dir", type=Path, required=True)
    evaluation.add_argument("--output-dir", type=Path, required=True)
    evaluation.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "extract":
        result = run_corpus(
            args.text_dir,
            args.evidence_dir,
            args.output_dir,
            args.map_dir,
            args.checkpoint_dir,
            workers=args.workers,
            resume=args.resume,
            paper_ids=set(args.paper_id) if args.paper_id else None,
            max_triggers=args.max_triggers,
        )
    else:
        result = evaluate(
            args.text_dir,
            args.evidence_dir,
            args.output_dir,
            args.output,
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
