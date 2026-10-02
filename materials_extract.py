"""Extract linked processing-structure-property evidence units from paper text."""
from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from chunking import Chunk, split_into_chunks
from llm_client import TruncatedError, chat_json, provider_info
from materials_evidence import MaterialsEvidenceUnit, write_materials_record

MAX_SPLIT_DEPTH = 3

_EXTRACT_SYSTEM = """You extract linked, hypothesis-useful materials evidence from one paper section.

Do not return independent labels or disconnected facts. Each evidence unit must describe one
condition-specific chain for one material state:

composition/material + intervention or existing structure -> resulting structure/defect state ->
mechanism -> measured or calculated property outcome, with operating/test conditions and comparison.

Split records when materials, heat treatments, temperatures, environments, or loading conditions
differ. Never combine a mechanism from one system with an outcome from another. Use null, empty
strings, empty objects, or empty lists for information not stated; do not infer missing values.
Every evidence_span must be copied as an exact, contiguous verbatim substring of the supplied
section. Copy complete source sentences whenever possible. Never paraphrase, normalize notation or
spacing, insert ellipses, or join text separated in the source. Before returning JSON, verify that
each evidence_span can be found character-for-character in the section.

Extract only findings produced or analyzed by this paper's authors. Exclude claims attributed to
other authors, cited publications, or generic literature background, even when they contain a
complete quantitative chain. A prior result may appear only inside the comparison fields of a unit
whose intervention, mechanism, or outcome is a finding of this paper. In introductions, emit a unit
only for an explicit result, hypothesis, or model that the paper itself tests or develops. A
statement that the study investigates, characterizes, or provides insight into a topic is an
objective or method, not a property outcome.

Return JSON:
{"units": [{
  "evidence_type": "experiment|simulation|theory|mixed",
  "material": {"name": "", "composition": "", "form": "", "initial_state": ""},
  "intervention": {"action": "", "description": "", "parameters": {}},
  "structure": {"description": "", "phases": [], "microstructure": [], "defects": []},
  "mechanism": "",
  "outcome": {"property": "", "value": null, "unit": "", "direction": "",
              "measurement_method": ""},
  "conditions": {"temperature": "", "time": "", "environment": "", "load": "",
                 "strain_rate": "", "pressure": ""},
  "comparison": {"baseline_material": "", "baseline_state": "", "baseline_value": null,
                 "unit": "", "direction": ""},
  "limitations": [],
  "evidence_spans": ["verbatim text"],
  "confidence": 0.0
}]}.

Only emit a unit when the section supports a link from an intervention or structure to a mechanism
or property outcome. A material name alone, generic motivation, literature summary, or method
without an outcome is not an evidence unit."""


@dataclass
class ExtractionRecord:
    paper_id: str
    evidence_units: list[MaterialsEvidenceUnit] = field(default_factory=list)
    rejected_units: list[dict[str, Any]] = field(default_factory=list)
    chunks_processed: int = 0


def _extract_chunk(chunk: Chunk, paper_id: str, depth: int = 0) -> tuple[list[MaterialsEvidenceUnit], list[dict[str, Any]]]:
    user = f"--- SECTION: {chunk.section} ---\n{chunk.text}"
    try:
        result = chat_json(_EXTRACT_SYSTEM, user, max_tokens=8000)
    except TruncatedError:
        lines = chunk.text.splitlines()
        if depth >= MAX_SPLIT_DEPTH or len(lines) < 4:
            raise
        midpoint = len(lines) // 2
        first = Chunk(f"{chunk.section}/a", "\n".join(lines[:midpoint]), chunk.index)
        second = Chunk(f"{chunk.section}/b", "\n".join(lines[midpoint:]), chunk.index)
        first_units, first_rejected = _extract_chunk(first, paper_id, depth + 1)
        second_units, second_rejected = _extract_chunk(second, paper_id, depth + 1)
        return first_units + second_units, first_rejected + second_rejected

    rows = result.get("units", []) if isinstance(result, dict) else []
    if not isinstance(rows, list):
        raise ValueError(f"model returned non-list units for section {chunk.section}")
    units: list[MaterialsEvidenceUnit] = []
    rejected: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        candidate = dict(row) if isinstance(row, dict) else {"raw": row}
        candidate["source_section"] = chunk.section
        try:
            units.append(MaterialsEvidenceUnit.from_dict(
                candidate,
                paper_id=paper_id,
                source_text=chunk.text,
            ))
        except ValueError as error:
            rejected.append({
                "section": chunk.section,
                "model_unit_index": index,
                "reason": str(error),
                "candidate": candidate,
            })
    return units, rejected


def extract_materials_paper(paper_id: str, full_text: str) -> ExtractionRecord:
    record = ExtractionRecord(paper_id)
    seen: set[str] = set()
    for chunk in split_into_chunks(full_text):
        units, rejected = _extract_chunk(chunk, paper_id)
        for unit in units:
            if unit.unit_id not in seen:
                seen.add(unit.unit_id)
                record.evidence_units.append(unit)
        record.rejected_units.extend(rejected)
        record.chunks_processed += 1
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--resume", action="store_true", help="skip papers with an existing output")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")

    files = sorted(args.input_dir.glob("*.txt"))
    if args.limit:
        files = files[:args.limit]
    if args.resume:
        files = [path for path in files if not (args.out_dir / f"{path.stem}.json").exists()]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[materials-extract] provider={provider_info()} papers={len(files)}", file=sys.stderr)

    def process(source_path: Path) -> tuple[str, int, int, int, float]:
        started = time.monotonic()
        record = extract_materials_paper(
            source_path.stem,
            source_path.read_text(encoding="utf-8", errors="ignore"),
        )
        destination = args.out_dir / f"{source_path.stem}.json"
        write_materials_record(
            destination,
            record.paper_id,
            record.evidence_units,
            record.rejected_units,
        )
        return (
            record.paper_id,
            record.chunks_processed,
            len(record.evidence_units),
            len(record.rejected_units),
            time.monotonic() - started,
        )

    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process, path): path for path in files}
        for future in as_completed(futures):
            source_path = futures[future]
            try:
                paper_id, chunks, units, rejected, elapsed = future.result()
            except Exception as error:
                failures.append((source_path.stem, error))
                print(f"[materials-extract] ERROR {source_path.stem}: {error}", file=sys.stderr)
                continue
            print(
                f"[materials-extract] {paper_id}: chunks={chunks} units={units} "
                f"rejected={rejected} seconds={elapsed:.1f}",
                file=sys.stderr,
            )
    if failures:
        print(f"[materials-extract] ERROR: {len(failures)} papers failed", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
