"""Build source passages, citation mentions, and table contexts for extracted papers."""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from chunking import _HEADER_RE

MAX_PASSAGE_CHARS = 2400
TABLE_CONTEXT_LINES = 80
_REFERENCE_START_RE = re.compile(r"^\s*\[(\d+)\]\s+(.+)")
_CITATION_RE = re.compile(r"\[((?:\d+\s*[-,;]?\s*)+)\]")
_TABLE_CAPTION_RE = re.compile(r"^\s*((?:supplementary\s+)?table)\s+([A-Z0-9IVX.-]+)[.:]?\s*(.*)$", re.I)
_COMPARISON_RE = re.compile(
    r"\b(?:compar(?:e|ed|ison)|outperform\w*|underperform\w*|higher than|lower than|"
    r"exceed\w*|baseline|versus|relative to)\b",
    re.I,
)


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:16]
    return f"{prefix}:{digest}"


def _normalized(text: str) -> str:
    text = re.sub(r"(?<=\w)-\s+(?=\w)", "", text)
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _sections(text: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    name = "Front matter"
    lines: list[str] = []
    for line in text.splitlines():
        match = _HEADER_RE.match(line)
        if match:
            if any(value.strip() for value in lines):
                sections.append((name, lines))
            name = match.group(1).title()
            lines = []
        else:
            lines.append(line)
    if any(value.strip() for value in lines):
        sections.append((name, lines))
    return sections


def _passage_blocks(lines: list[str]) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    current_chars = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                blocks.append("\n".join(current).strip())
                current, current_chars = [], 0
            continue
        if current and current_chars + len(line) + 1 > MAX_PASSAGE_CHARS:
            blocks.append("\n".join(current).strip())
            current = current[-2:]
            current_chars = sum(len(value) + 1 for value in current)
        current.append(line)
        current_chars += len(line) + 1
    if current:
        blocks.append("\n".join(current).strip())
    return blocks


def extract_passages(paper_id: str, text: str) -> list[dict[str, Any]]:
    passages: list[dict[str, Any]] = []
    for section_index, (section, lines) in enumerate(_sections(text)):
        for passage_index, block in enumerate(_passage_blocks(lines)):
            passages.append({
                "passage_id": _stable_id("passage", paper_id, str(section_index), str(passage_index), block),
                "paper_id": paper_id,
                "section": section,
                "section_index": section_index,
                "passage_index": passage_index,
                "text": block,
                "word_count": len(block.split()),
                "claim_ids": [],
                "citation_ids": [],
                "table_ids": [],
            })
    return passages


def extract_references(paper_id: str, text: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    current_number = ""
    current_lines: list[str] = []
    for line in text.splitlines():
        match = _REFERENCE_START_RE.match(line)
        if match:
            if current_number:
                entries.append(_reference_record(paper_id, current_number, current_lines))
            current_number = match.group(1)
            current_lines = [match.group(2).strip()]
        elif current_number and line.strip():
            current_lines.append(line.strip())
        elif current_number:
            entries.append(_reference_record(paper_id, current_number, current_lines))
            current_number, current_lines = "", []
    if current_number:
        entries.append(_reference_record(paper_id, current_number, current_lines))
    unique: dict[str, dict[str, Any]] = {}
    for entry in entries:
        unique.setdefault(entry["reference_number"], entry)
    return list(unique.values())


def _reference_record(paper_id: str, number: str, lines: list[str]) -> dict[str, Any]:
    text = " ".join(lines)
    doi_match = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+", text, re.I)
    arxiv_match = re.search(r"(?:arXiv\s*:\s*|arxiv\.org/(?:abs|pdf)/)(\d{4}\.\d{4,5})", text, re.I)
    return {
        "reference_id": _stable_id("reference", paper_id, number),
        "paper_id": paper_id,
        "reference_number": number,
        "raw_text": text,
        "doi": doi_match.group(0).rstrip(".,;)") if doi_match else "",
        "arxiv_id": arxiv_match.group(1) if arxiv_match else "",
        "resolution_status": "identifier_available" if doi_match or arxiv_match else "metadata_only",
    }


def extract_tables(paper_id: str, text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    tables: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        match = _TABLE_CAPTION_RE.match(line)
        if not match:
            continue
        end = min(index + TABLE_CONTEXT_LINES, len(lines))
        for candidate in range(index + 1, end):
            if _TABLE_CAPTION_RE.match(lines[candidate]):
                end = candidate
                break
        raw_lines = [value for value in lines[index:end] if value.strip()]
        numeric_lines = [value for value in raw_lines[1:] if len(re.findall(r"[-+]?\d+(?:\.\d+)?", value)) >= 2]
        label = match.group(2).rstrip(".:")
        table_id = _stable_id("table", paper_id, label, line)
        tables.append({
            "table_id": table_id,
            "paper_id": paper_id,
            "label": label,
            "caption": " ".join(match.groups()[2:]).strip(),
            "raw_text": "\n".join(raw_lines),
            "numeric_lines": numeric_lines,
            "structured_rows": [],
            "extraction_level": "raw_numeric_lines" if numeric_lines else "caption_context_only",
            "confidence": 0.6 if numeric_lines else 0.4,
        })
    return tables


def _claim_rows(record: dict[str, Any]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for role, claims in record.get("reconciled_by_role", {}).items():
        for index, claim in enumerate(claims):
            claim_id = f"{record['paper_id']}::{role}::{index}"
            evidence_values = claim.get("evidence_spans") or [claim.get("evidence_span", "")]
            for evidence in evidence_values:
                if evidence:
                    rows.append((claim_id, str(evidence)))
    return rows


def _anchor_claims(passages: list[dict[str, Any]], record: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    anchors: dict[str, list[dict[str, Any]]] = {}
    normalized_passages = [_normalized(passage["text"]) for passage in passages]
    for claim_id, evidence in _claim_rows(record):
        needle = _normalized(evidence)
        candidates = [(index, 1.0) for index, text in enumerate(normalized_passages) if needle and needle in text]
        if not candidates and needle:
            terms = set(needle.split())
            scores = []
            for text in normalized_passages:
                containment = len(terms & set(text.split())) / max(len(terms), 1)
                sequence = difflib.SequenceMatcher(None, needle, text, autojunk=False).quick_ratio()
                scores.append(max(containment, sequence))
            if scores and max(scores) >= 0.55:
                index = scores.index(max(scores))
                candidates = [(index, scores[index])]
        for index, score in candidates[:1]:
            passage_id = passages[index]["passage_id"]
            passages[index]["claim_ids"].append(claim_id)
            anchors.setdefault(claim_id, []).append({
                "passage_id": passage_id,
                "match_score": round(score, 4),
                "evidence_span": evidence,
            })
    return anchors


def build_source_bundle(paper_id: str, text: str, record: dict[str, Any]) -> dict[str, Any]:
    passages = extract_passages(paper_id, text)
    references = extract_references(paper_id, text)
    tables = extract_tables(paper_id, text)
    reference_by_number = {row["reference_number"]: row for row in references}
    mentions: list[dict[str, Any]] = []
    for passage in passages:
        if passage["section"].lower() == "references":
            continue
        for match in _CITATION_RE.finditer(passage["text"]):
            numbers = re.findall(r"\d+", match.group(1))
            for number in numbers:
                reference = reference_by_number.get(number)
                if not reference:
                    continue
                citation_id = _stable_id("citation", passage["passage_id"], number, match.group(0))
                mentions.append({
                    "citation_id": citation_id,
                    "paper_id": paper_id,
                    "passage_id": passage["passage_id"],
                    "reference_id": reference["reference_id"],
                    "reference_number": number,
                    "mention_text": match.group(0),
                    "context": passage["text"],
                })
                passage["citation_ids"].append(citation_id)
    for table in tables:
        caption_terms = set(_normalized(f"table {table['label']} {table['caption']}").split())
        candidates = []
        for passage in passages:
            overlap = len(caption_terms & set(_normalized(passage["text"]).split()))
            if overlap:
                candidates.append((overlap, passage))
        if candidates:
            passage = max(candidates, key=lambda value: value[0])[1]
            passage["table_ids"].append(table["table_id"])
            table["passage_id"] = passage["passage_id"]
        else:
            table["passage_id"] = ""
    claim_anchors = _anchor_claims(passages, record)
    comparison_contexts = []
    mention_by_id = {row["citation_id"]: row for row in mentions}
    reference_by_id = {row["reference_id"]: row for row in references}
    table_by_id = {row["table_id"]: row for row in tables}
    for passage in passages:
        if not _COMPARISON_RE.search(passage["text"]):
            continue
        cited_references_by_id: dict[str, dict[str, Any]] = {}
        for citation_id in passage["citation_ids"]:
            mention = mention_by_id[citation_id]
            reference = reference_by_id[mention["reference_id"]]
            cited_references_by_id.setdefault(reference["reference_id"], {
                "reference_number": mention["reference_number"],
                "reference_id": reference["reference_id"],
                "raw_text": reference["raw_text"],
                "doi": reference["doi"],
                "arxiv_id": reference["arxiv_id"],
                "resolution_status": reference["resolution_status"],
            })
        cited_references = list(cited_references_by_id.values())
        linked_tables = [table_by_id[table_id] for table_id in passage["table_ids"]]
        comparison_contexts.append({
            "comparison_id": _stable_id("comparison", passage["passage_id"]),
            "paper_id": paper_id,
            "passage_id": passage["passage_id"],
            "section": passage["section"],
            "text": passage["text"],
            "claim_ids": passage["claim_ids"],
            "cited_references": cited_references,
            "tables": linked_tables,
            "cross_paper": bool(cited_references),
            "cited_content_status": "requires_resolution" if cited_references else "not_applicable",
        })
    return {
        "paper_id": paper_id,
        "passages": passages,
        "references": references,
        "citation_mentions": mentions,
        "tables": tables,
        "comparison_contexts": comparison_contexts,
        "claim_passage_ids": claim_anchors,
    }


def aggregate_source_context(output_dir: Path) -> dict[str, Any]:
    bundles = [json.loads(path.read_text()) for path in sorted((output_dir / "papers").glob("*.json"))]
    keys = ("passages", "references", "citation_mentions", "tables", "comparison_contexts")
    for key in keys:
        rows = [row for bundle in bundles for row in bundle[key]]
        (output_dir / f"{key}.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    summary = {
        "papers": len(bundles),
        **{key: sum(len(bundle[key]) for bundle in bundles) for key in keys},
        "anchored_claims": sum(len(bundle["claim_passage_ids"]) for bundle in bundles),
        "table_extraction_levels": dict(Counter(
            table["extraction_level"] for bundle in bundles for table in bundle["tables"]
        )),
        "reference_resolution_status": dict(Counter(
            reference["resolution_status"] for bundle in bundles for reference in bundle["references"]
        )),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def load_context_index(context_dir: Path | None) -> dict[str, list[dict[str, Any]]]:
    if context_dir is None:
        return {}
    paper_dir = context_dir / "papers"
    if not paper_dir.exists():
        raise FileNotFoundError(f"source context directory not found: {paper_dir}")
    index: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(paper_dir.glob("*.json")):
        bundle = json.loads(path.read_text())
        passages = {row["passage_id"]: row for row in bundle["passages"]}
        references = {row["reference_id"]: row for row in bundle["references"]}
        mentions_by_passage: dict[str, dict[str, dict[str, Any]]] = {}
        for mention in bundle["citation_mentions"]:
            reference = references.get(mention["reference_id"], {})
            mentions_by_passage.setdefault(mention["passage_id"], {}).setdefault(mention["reference_id"], {
                "reference_number": mention["reference_number"],
                "mention_text": mention["mention_text"],
                "reference_id": mention["reference_id"],
                "reference_text": reference.get("raw_text", ""),
                "doi": reference.get("doi", ""),
                "arxiv_id": reference.get("arxiv_id", ""),
                "resolution_status": reference.get("resolution_status", "unresolved"),
            })
        tables_by_passage: dict[str, list[dict[str, Any]]] = {}
        for table in bundle["tables"]:
            table_context = {
                "passage_id": table.get("passage_id", ""),
                "section": passages.get(table.get("passage_id", ""), {}).get("section", ""),
                "text": table["raw_text"],
                "match_score": table["confidence"],
                "evidence_span": table["caption"],
                "citations": [],
                "tables": [{
                    "table_id": table["table_id"],
                    "label": table["label"],
                    "caption": table["caption"],
                    "raw_text": table["raw_text"],
                    "extraction_level": table["extraction_level"],
                    "confidence": table["confidence"],
                }],
                "context_type": "table",
                "paper_id": bundle["paper_id"],
            }
            index.setdefault(table["table_id"], []).append(table_context)
            if table.get("passage_id"):
                tables_by_passage.setdefault(table["passage_id"], []).extend(table_context["tables"])
        for claim_id, anchors in bundle["claim_passage_ids"].items():
            for anchor in anchors:
                passage = passages.get(anchor["passage_id"])
                if not passage:
                    continue
                index.setdefault(claim_id, []).append({
                    "passage_id": passage["passage_id"],
                    "section": passage["section"],
                    "text": passage["text"],
                    "match_score": anchor["match_score"],
                    "evidence_span": anchor["evidence_span"],
                    "citations": list(mentions_by_passage.get(passage["passage_id"], {}).values()),
                    "tables": tables_by_passage.get(passage["passage_id"], []),
                    "context_type": "claim_passage",
                    "paper_id": bundle["paper_id"],
                })
        for comparison in bundle.get("comparison_contexts", []):
            citations = [{
                "reference_number": reference["reference_number"],
                "mention_text": f"[{reference['reference_number']}]",
                "reference_id": reference["reference_id"],
                "reference_text": reference["raw_text"],
                "doi": reference["doi"],
                "arxiv_id": reference["arxiv_id"],
                "resolution_status": reference["resolution_status"],
            } for reference in comparison["cited_references"]]
            index.setdefault(comparison["comparison_id"], []).append({
                "passage_id": comparison["passage_id"],
                "section": comparison["section"],
                "text": comparison["text"],
                "match_score": 1.0,
                "evidence_span": comparison["text"],
                "citations": citations,
                "tables": comparison["tables"],
                "context_type": "comparison",
                "paper_id": bundle["paper_id"],
                "cross_paper": comparison["cross_paper"],
                "cited_content_status": comparison["cited_content_status"],
                "claim_ids": comparison["claim_ids"],
            })
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--outputs-dir", required=True, type=Path)
    parser.add_argument("--context-dir", required=True, type=Path)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    records = sorted(args.outputs_dir.glob("*.json"))
    if args.limit:
        records = records[:args.limit]
    paper_dir = args.context_dir / "papers"
    paper_dir.mkdir(parents=True, exist_ok=True)
    for record_path in records:
        source_path = args.source_dir / f"{record_path.stem}.txt"
        if not source_path.exists():
            raise FileNotFoundError(source_path)
        record = json.loads(record_path.read_text())
        bundle = build_source_bundle(record_path.stem, source_path.read_text(errors="ignore"), record)
        (paper_dir / record_path.name).write_text(json.dumps(bundle, indent=2))
        print(
            f"[context] {record_path.stem}: passages={len(bundle['passages'])} "
            f"references={len(bundle['references'])} mentions={len(bundle['citation_mentions'])} "
            f"tables={len(bundle['tables'])} anchored_claims={len(bundle['claim_passage_ids'])}"
        )
    summary = aggregate_source_context(args.context_dir)
    print(f"[context] complete {json.dumps(summary, sort_keys=True)}")


if __name__ == "__main__":
    main()