"""Extract normalized, temporally auditable materials evidence from paper text."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chunking import Chunk, split_into_chunks
from hypothesis_evidence_v2 import (
    SCHEMA_VERSION,
    HypothesisEvidenceUnit,
    atomic_json,
    write_evidence_record,
)
from llm_client import TruncatedError, chat_json, provider_info

MAX_SPLIT_DEPTH = 3

_SYSTEM = """You extract normalized evidence for materials hypothesis generation from ONE section
of ONE paper. Preserve complete links between sample, processing, structure, conditions,
measurement, comparison, mechanism, boundary, and provenance.

Extract current-paper findings and cited-work claims as separate units. Set claim_ownership to
current_paper only when this paper produced, calculated, simulated, or explicitly tested the
claim. Set it to cited_work for literature/background claims. Never merge them.

Create a stable local sample_id such as sample_as_cast, sample_annealed_1000C, simulation_SRO, or
sample_unknown. Split units when sample state, composition, treatment, temperature, environment,
load, or mechanism differs. Represent processing as an ordered sequence. Use numeric values only
for measurement values, uncertainties, and composition fractions. Put qualifiers in text fields.
Use null when a numeric value is absent. Do not infer missing values or convert units unless both
the source value and conversion are unambiguous; preserve the reported unit.

Mechanism status must be observed, inferred, calculated, simulated, cited, hypothesized, or
contradicted. Evidence strength must be direct_measurement, controlled_intervention, correlation,
simulation, thermodynamic_calculation, author_interpretation, or cited_claim.

Every evidence_span must be an exact contiguous substring of CURRENT SECTION. Copy complete
sentences when possible. Never paraphrase a span, join separated text, insert ellipses, or
normalize notation. result_revealing is true when the record discloses an intervention, result,
mechanism, conclusion, or quantitative finding that must be hidden from a held-out test query.

Return JSON only:
{"units": [{
  "study_type": "experiment|simulation|theory|mixed",
  "claim_ownership": "current_paper|cited_work",
  "sample": {
    "sample_id": "",
    "material_name": "",
    "nominal_composition": "",
    "measured_composition": "",
    "composition": [
      {"element": "", "fraction": null,
       "fraction_unit": "at.%|wt.%|mole_fraction|mass_fraction",
       "uncertainty": null}
    ],
    "form": "",
    "initial_state": "",
    "dimensions_orientation": "",
    "density_porosity": ""
  },
  "process_steps": [
    {"sequence": 1, "action": "", "parameters": {}, "resulting_state": ""}
  ],
  "structure_observations": [
    {"feature": "", "value": null, "unit": "", "qualitative_value": "",
     "uncertainty": null, "method": "", "status": "observed|inferred|calculated|simulated"}
  ],
  "test_conditions": {
    "temperature": "", "time": "", "environment": "", "pressure": "",
    "stress_load": "", "strain_rate": "", "thermal_history": "",
    "radiation": "", "tribology": "", "simulation_conditions": ""
  },
  "measurements": [
    {"property": "", "value": null, "unit": "", "uncertainty": null,
     "direction": "", "method": "", "replicates": null}
  ],
  "comparison": {
    "baseline_sample_id": "", "baseline_description": "",
    "changed_variables": [], "controlled_variables": [],
    "confounders": [], "effect_size": null, "effect_unit": ""
  },
  "mechanisms": [
    {"assertion": "", "status": "inferred",
     "evidence_strength": "author_interpretation",
     "source_ownership": "current_paper", "supported_by": [],
     "alternatives": [], "discriminating_measurement": ""}
  ],
  "boundaries": [
    {"variable": "", "operator": "", "value": null, "unit": "",
     "failure_mode": "", "evidence_status": "observed|inferred|hypothesized"}
  ],
  "limitations": [
    {"type": "experimental|measurement|model|applicability|confounder",
     "description": "", "impact": ""}
  ],
  "evidence_spans": ["exact source text"],
  "result_revealing": true,
  "extraction_confidence": 0.0
}]}.

Emit a result unit only when the section supports a process/structure plus a
measurement/mechanism. A Methods-only unit may omit measurement/mechanism only when it defines
the processing lineage of a sample explicitly prepared for this paper; set result_revealing=false
for such a unit. Do not invent sample links."""


@dataclass
class PaperExtraction:
    paper_id: str
    units: list[HypothesisEvidenceUnit]
    rejected: list[dict[str, Any]]
    chunks_processed: int
    model_calls: int
    resumed_chunks: int


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _validate_rows(
    payload: Any,
    paper_id: str,
    chunk: Chunk,
) -> tuple[list[HypothesisEvidenceUnit], list[dict[str, Any]]]:
    rows = payload.get("units", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        return [], [{
            "section": chunk.section,
            "reason": "units must be a list",
            "candidate": rows,
        }]
    accepted: list[HypothesisEvidenceUnit] = []
    rejected: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        candidate = dict(row) if isinstance(row, dict) else {"raw": row}
        candidate["source_section"] = chunk.section
        try:
            accepted.append(HypothesisEvidenceUnit.from_dict(
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
    return accepted, rejected


def _extract_chunk(
    chunk: Chunk,
    paper_id: str,
    depth: int = 0,
) -> tuple[list[HypothesisEvidenceUnit], list[dict[str, Any]], int]:
    try:
        payload = chat_json(
            _SYSTEM,
            f"PAPER ID: {paper_id}\nCURRENT SECTION: {chunk.section}\n\n{chunk.text}",
            max_tokens=12000,
        )
        units, rejected = _validate_rows(payload, paper_id, chunk)
        return units, rejected, 1
    except TruncatedError:
        lines = chunk.text.splitlines()
        if depth >= MAX_SPLIT_DEPTH or len(lines) < 4:
            raise
        middle = len(lines) // 2
        first = Chunk(f"{chunk.section}/a", "\n".join(lines[:middle]), chunk.index)
        second = Chunk(f"{chunk.section}/b", "\n".join(lines[middle:]), chunk.index)
        first_units, first_rejected, first_calls = _extract_chunk(first, paper_id, depth + 1)
        second_units, second_rejected, second_calls = _extract_chunk(second, paper_id, depth + 1)
        return (
            first_units + second_units,
            first_rejected + second_rejected,
            first_calls + second_calls,
        )


def extract_paper(source_path: Path, checkpoint_dir: Path) -> PaperExtraction:
    paper_id = source_path.stem
    text = source_path.read_text(encoding="utf-8", errors="ignore")
    chunks = split_into_chunks(text)
    checkpoint_path = checkpoint_dir / f"{paper_id}.json"
    checkpoint: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "paper_id": paper_id,
        "source_sha256": _digest(text),
        "completed_chunks": {},
    }
    if checkpoint_path.exists():
        loaded = json.loads(checkpoint_path.read_text())
        if (
            loaded.get("schema_version") == SCHEMA_VERSION
            and loaded.get("source_sha256") == checkpoint["source_sha256"]
        ):
            checkpoint = loaded

    units: list[HypothesisEvidenceUnit] = []
    rejected: list[dict[str, Any]] = []
    calls = 0
    resumed = 0
    for position, chunk in enumerate(chunks):
        saved = checkpoint["completed_chunks"].get(str(position))
        chunk_hash = _digest(chunk.text)
        if saved and saved.get("chunk_sha256") == chunk_hash:
            chunk_units, chunk_rejected = _validate_rows(
                {"units": saved.get("units", [])},
                paper_id,
                chunk,
            )
            chunk_rejected.extend(saved.get("rejected_units", []))
            resumed += 1
        else:
            chunk_units, chunk_rejected, chunk_calls = _extract_chunk(chunk, paper_id)
            calls += chunk_calls
            checkpoint["completed_chunks"][str(position)] = {
                "chunk_sha256": chunk_hash,
                "section": chunk.section,
                "units": [unit.to_dict() for unit in chunk_units],
                "rejected_units": chunk_rejected,
            }
            atomic_json(checkpoint_path, checkpoint)
        units.extend(chunk_units)
        rejected.extend(chunk_rejected)

    unique: list[HypothesisEvidenceUnit] = []
    seen: set[str] = set()
    for unit in units:
        if unit.unit_id in seen:
            continue
        seen.add(unit.unit_id)
        unique.append(unit)
    return PaperExtraction(paper_id, unique, rejected, len(chunks), calls, resumed)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--checkpoint-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--paper-id", action="append")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    files = sorted(args.input_dir.glob("*.txt"))
    if args.paper_id:
        selected = set(args.paper_id)
        files = [path for path in files if path.stem in selected]
    if args.limit:
        files = files[:args.limit]
    if args.resume:
        files = [path for path in files if not (args.out_dir / f"{path.stem}.json").exists()]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    print(
        f"[materials-v2] provider={provider_info()} papers={len(files)} workers={args.workers}",
        file=sys.stderr,
    )

    def process(path: Path) -> tuple[PaperExtraction, float]:
        started = time.monotonic()
        result = extract_paper(path, args.checkpoint_dir)
        write_evidence_record(
            args.out_dir / f"{result.paper_id}.json",
            result.paper_id,
            result.units,
            result.rejected,
            chunks_processed=result.chunks_processed,
            resumed_chunks=result.resumed_chunks,
        )
        return result, time.monotonic() - started

    failures: list[tuple[str, Exception]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process, path): path for path in files}
        for future in as_completed(futures):
            path = futures[future]
            try:
                result, elapsed = future.result()
            except Exception as error:
                failures.append((path.stem, error))
                print(f"[materials-v2] ERROR {path.stem}: {error}", file=sys.stderr)
                continue
            print(
                f"[materials-v2] {result.paper_id}: chunks={result.chunks_processed} "
                f"units={len(result.units)} calls={result.model_calls} "
                f"resumed={result.resumed_chunks} rejected={len(result.rejected)} "
                f"seconds={elapsed:.1f}",
                file=sys.stderr,
            )
    if failures:
        raise SystemExit(f"{len(failures)} v2 paper extractions failed")


if __name__ == "__main__":
    main()
