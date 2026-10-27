"""Temporal hypothesis evaluation v3: paper-date cutoffs, leakage audits, GPT-5.6 judging.

Each held-out paper P has cutoff = P's earliest public date. The agent may access only papers Q with
earliest_public_date(Q) < cutoff, Q != P, and Q outside P's work family (the rule in
temporal_hypothesis_benchmark._eligible). Generation runs on the local Qwen model served by llama.cpp.
Judging runs on TRAPI GPT-5.6 (llm_client.judge_chat_json), so the generator never scores its own output.

Settings:
  closed_book   query only; memorization baseline
  text_oneshot  BM25 over section chunks of eligible papers, one generation
  v2_oneshot    BM25 over normalized v2 evidence units of eligible papers, one generation
  tool_agent    Qwen calls tools over the same eligible corpus, reads what it cites, then submits
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests

from hypothesis_evidence_v2 import atomic_json, load_evidence
from llm_client import LLMError, judge_chat_json, judge_info, provider_info, trapi_chat_with_tools
from matkg_index import TemporalKG, fact_record_id, fact_text
from temporal_hypothesis_benchmark import (
    QUERY_LEVELS,
    RetrievalRecord,
    _SCORE_SYSTEM,
    _date_map,
    _eligible,
    _flatten,
    _read_json,
    _validate_generation,
    _validate_score,
    compact_evidence_payload,
    generate_with_citation_repair,
    retrieve,
)

SCHEMA_VERSION = "temporal-eval-v3-1.0"
SETTINGS = ("closed_book", "text_oneshot", "v2_oneshot", "tool_agent")
PAIRS = (
    ("tool_agent", "text_oneshot"),
    ("tool_agent", "v2_oneshot"),
    ("tool_agent", "closed_book"),
)
PRIMARY_DIMENSIONS = (
    "intervention_reconstruction",
    "condition_agreement",
    "mechanism_agreement",
    "outcome_agreement",
)
ALL_DIMENSIONS = (
    "problem_alignment",
    "intervention_reconstruction",
    "condition_agreement",
    "mechanism_agreement",
    "outcome_agreement",
    "baseline_quality",
    "boundary_quality",
    "experiment_discriminability",
    "evidence_validity",
    "novelty",
)
HYPOTHESIS_FIELDS = (
    "hypothesis", "material_initial_state", "intervention", "conditions", "structural_mediator",
    "mechanism", "predicted_outcome", "baseline", "boundary", "uncertainty",
    "supporting_evidence_ids", "conflicting_evidence_ids", "falsification_experiment",
)
ONESHOT_LIMIT = 14
MAX_TOOL_CALLS = 12
MAX_MODEL_TURNS = 16
PAGE_CHARS = 2400
SNIPPET_CHARS = 280
CITED_TEXT_CHARS = 1200
BOOTSTRAP_RESAMPLES = 10000
BOOTSTRAP_SEED = 20260421

EXPERIMENT_DIR = Path(__file__).resolve().parent / "experiments" / "high_temperature_hea_qwen35b"
# Outputs and benchmark cases can be redirected so a rerun (for example on rebuilt queries) never overwrites
# earlier results. Input data (corpus, metadata, evidence, paper maps, MatKG) always come from EXPERIMENT_DIR.
RUN_ROOT = Path(os.environ.get("MATHG_RUN_ROOT", str(EXPERIMENT_DIR)))
CASES_DIR = Path(os.environ.get("MATHG_CASES_DIR", str(EXPERIMENT_DIR / "temporal_v2" / "benchmark_cases")))

TOOL_SYSTEM = (
    "You are a materials-science hypothesis agent in a leakage-audited chronological benchmark. "
    "You may use only papers published before the knowledge cutoff in the task, and the tools return only "
    "such papers. Work in this order: explore with list_papers or search_corpus; read_record every record you "
    "will cite; then call submit_hypothesis exactly once. You have at most {max_calls} tool calls. Cite record "
    "IDs exactly as the tools returned them, and only after reading them. If the evidence is insufficient, state "
    "the uncertainty instead of inventing support. The hypothesis object must contain: {fields}."
)

TOOLS = [
    {"type": "function", "function": {
        "name": "list_papers",
        "description": "List the papers you may use (published before the knowledge cutoff) with paper_id, publication_date and title.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    }},
    {"type": "function", "function": {
        "name": "search_corpus",
        "description": ("Search the eligible corpus. Returns the best-matching records with record_id, paper_id, "
                        "publication_date, kind (chunk:<section> for paper text, v2_evidence for structured evidence "
                        "units) and a short snippet."),
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "k": {"type": "integer", "minimum": 1, "maximum": 8}},
            "required": ["query"],
            "additionalProperties": False,
        },
    }},
    {"type": "function", "function": {
        "name": "read_record",
        "description": ("Read one record, about 2400 characters per page. Returns text and next_offset (null when "
                        "finished). A record can be cited only after it has been read."),
        "parameters": {
            "type": "object",
            "properties": {"record_id": {"type": "string"}, "offset": {"type": "integer", "minimum": 0}},
            "required": ["record_id"],
            "additionalProperties": False,
        },
    }},
    {"type": "function", "function": {
        "name": "submit_hypothesis",
        "description": "Submit the final hypothesis as one JSON object with the requested fields. Call exactly once.",
        "parameters": {
            "type": "object",
            "properties": {"hypothesis": {"type": "object"}},
            "required": ["hypothesis"],
            "additionalProperties": False,
        },
    }},
]
SUBMIT_ONLY = [TOOLS[-1]]
KG_TOOL = {"type": "function", "function": {
    "name": "kg_lookup",
    "description": ("Look up materials-knowledge-graph co-occurrence statistics for a topic phrase (an element, "
                    "property, process or microstructure term). Returns facts built only from papers published before "
                    "the cutoff, each with a record_id. A fact can be cited only after read_record on that record_id."),
    "parameters": {
        "type": "object",
        "properties": {"topic": {"type": "string"}},
        "required": ["topic"],
        "additionalProperties": False,
    },
}}
KG_TOOLS = TOOLS[:3] + [KG_TOOL, TOOLS[3]]
KG_SYSTEM_NOTE = (" You may also call kg_lookup(topic) for co-occurrence facts from earlier materials abstracts; "
                  "read a fact's record_id before citing it.")


# Experiment 36 (loop.md 17.1, 17.3): with MATHG_EVIDENCE=web the corpus is the question's web-search corpus, and
# search_corpus also returns live web-search results (websearch.WebEligibleCorpus).
def evidence_mode() -> str:
    return os.environ.get("MATHG_EVIDENCE", "fixed")


PAIR_SYSTEM = (
    "You compare two materials-science hypotheses written for the same query. Decide which one better "
    "reconstructs the hidden paper target. Judge scientific agreement with the target, fidelity of intervention, "
    "conditions, mechanism and outcome, and evidence discipline (claims must be supported by the cited evidence "
    "texts). Do not reward length, confidence, or wording overlap. Return JSON only: "
    "{\"winner\": \"A\" | \"B\" | \"tie\", \"confidence\": 0.0, \"reason\": \"\"}."
)


# ---------------------------------------------------------------- corpus

def eligible_ids(metadata: dict[str, dict[str, Any]], test_paper_id: str, cutoff: str) -> set[str]:
    return {pid for pid in metadata if _eligible(pid, test_paper_id, cutoff, metadata)}


def _snippet(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    if len(collapsed) <= SNIPPET_CHARS:
        return collapsed
    return collapsed[:SNIPPET_CHARS].rsplit(" ", 1)[0] + " ..."


def build_corpus(
    test_paper_id: str,
    cutoff: str,
    metadata: dict[str, dict[str, Any]],
    v2_units: list[Any],
    paper_maps_dir: Path,
) -> tuple[set[str], list[RetrievalRecord], list[RetrievalRecord]]:
    eligible = eligible_ids(metadata, test_paper_id, cutoff)
    chunk_records: list[RetrievalRecord] = []
    for pid in sorted(eligible):
        path = paper_maps_dir / f"{pid}.json"
        if not path.exists():
            continue
        for chunk in _read_json(path)["chunks"]:
            chunk_records.append(RetrievalRecord(
                chunk["chunk_id"],
                pid,
                metadata[pid]["earliest_public_date"],
                f"chunk:{chunk['section']}",
                chunk["text"],
                {"section": chunk["section"], "chunk_index": chunk["chunk_index"]},
            ))
    unit_records = [
        RetrievalRecord(
            unit.unit_id,
            unit.paper_id,
            metadata[unit.paper_id]["earliest_public_date"],
            "v2_evidence",
            _flatten(unit.to_dict()),
            unit.to_dict(),
        )
        for unit in v2_units
        if unit.paper_id in eligible
    ]
    return eligible, chunk_records, unit_records


def audit_accessed(
    record_ids: list[str],
    lookup: dict[str, RetrievalRecord],
    test_paper_id: str,
    cutoff: str,
    metadata: dict[str, dict[str, Any]],
) -> dict[str, int]:
    test_family = str(metadata[test_paper_id].get("work_family_id") or "")
    counts = {"temporal_violations": 0, "test_paper_leaks": 0, "family_leaks": 0, "unknown_record_ids": 0}
    for record_id in record_ids:
        record = lookup.get(record_id)
        if record is None:
            counts["unknown_record_ids"] += 1
            continue
        counts["temporal_violations"] += int(record.publication_date >= cutoff)
        counts["test_paper_leaks"] += int(record.paper_id == test_paper_id)
        family = str(metadata.get(record.paper_id, {}).get("work_family_id") or "")
        counts["family_leaks"] += int(bool(test_family and family and family == test_family))
    return counts


def query_leak(query: str, row: dict[str, Any]) -> bool:
    text = query.casefold()
    doi = str(row.get("doi") or "").casefold()
    title = str(row.get("title") or "").casefold()[:60]
    return bool((doi and doi in text) or (len(title) >= 20 and title in text))


# ---------------------------------------------------------------- local generation

def call_local_with_tools(messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
    if provider_info() == "trapi":
        return trapi_chat_with_tools(messages, tools)
    base = os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:8000/v1").rstrip("/")
    body: dict[str, Any] = {
        "model": os.environ.get("OPENAI_MODEL", "local"),
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0.2,
        # Same output cap as one-shot generation in generate_with_citation_repair (max_tokens=5000).
        "max_tokens": 5000,
    }
    template_kwargs = os.environ.get("OPENAI_CHAT_TEMPLATE_KWARGS")
    if template_kwargs:
        body["chat_template_kwargs"] = json.loads(template_kwargs)
    timeout = float(os.environ.get("MATHG_REQUEST_TIMEOUT", "300"))
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            response = requests.post(f"{base}/chat/completions", json=body, timeout=timeout)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]
        except Exception as error:  # noqa: BLE001 - retry transient local-server failures
            last_error = error
            time.sleep(2 ** attempt)
    raise LLMError(f"tool-call request failed after 4 attempts: {last_error}")


class EligibleCorpus:
    """Tool-facing view of the eligible corpus. Every record it returns is already cutoff-eligible."""

    def __init__(self, metadata: dict[str, dict[str, Any]], eligible: set[str], records: list[RetrievalRecord],
                 kg: Any = None):
        self.metadata = metadata
        self.eligible = eligible
        self.records = list(records)
        self.lookup = {record.record_id: record for record in self.records}
        self.seen_ids: set[str] = set()
        self.read_ids: set[str] = set()
        self.kg = kg

    def kg_lookup(self, topic: str) -> dict[str, Any]:
        """Pre-cutoff MatKG co-occurrence facts. Each fact becomes a readable record (must be read before citing)."""
        if self.kg is None:
            return {"error": "kg_lookup is not enabled for this run"}
        found = self.kg.cooccurrences(topic)
        facts = []
        for fact in found["facts"]:
            record_id = fact_record_id(found["anchors"], fact["neighbor"])
            record = RetrievalRecord(
                record_id, f"matkg:{record_id.rsplit('::', 1)[-1]}", f"{fact['latest_year']}-12-31",
                "kg_cooccurrence", fact_text(found["anchors"], fact), {"papers": fact["papers"]},
            )
            self.lookup[record_id] = record
            self.seen_ids.add(record_id)
            facts.append({"record_id": record_id, "neighbor": fact["neighbor"], "snippet": _snippet(record.text)})
        return {"topic": topic, "matched_terms": found["anchors"], "facts": facts,
                "note": "" if facts else "no pre-cutoff facts for this topic; try a different term"}

    def list_papers(self) -> dict[str, Any]:
        papers = sorted(self.eligible, key=lambda pid: (self.metadata[pid]["earliest_public_date"], pid))
        return {"papers": [
            {
                "paper_id": pid,
                "publication_date": self.metadata[pid]["earliest_public_date"],
                "title": str(self.metadata[pid].get("title", "")),
            }
            for pid in papers
        ]}

    def search(self, query: str, k: Any = 6) -> dict[str, Any]:
        try:
            limit = max(1, min(int(k), 8))
        except (TypeError, ValueError):
            limit = 6
        hits = retrieve(query, self.records, limit=limit)
        results = []
        for record in hits:
            self.seen_ids.add(record.record_id)
            results.append({
                "record_id": record.record_id,
                "paper_id": record.paper_id,
                "publication_date": record.publication_date,
                "kind": record.kind,
                "snippet": _snippet(record.text),
            })
        return {"query": query, "results": results,
                "note": "" if results else "no matches; try different terms"}

    def read(self, record_id: str, offset: Any = 0) -> dict[str, Any]:
        record = self.lookup.get(record_id)
        if record is None:
            return {"error": f"unknown record_id {record_id!r}; use search_corpus or list_papers"}
        try:
            start = max(0, int(offset))
        except (TypeError, ValueError):
            start = 0
        end = start + PAGE_CHARS
        self.read_ids.add(record_id)
        return {
            "record_id": record_id,
            "paper_id": record.paper_id,
            "publication_date": record.publication_date,
            "kind": record.kind,
            "offset": start,
            "text": record.text[start:end],
            "next_offset": end if end < len(record.text) else None,
        }


def run_closed_book(query: str, cutoff: str) -> tuple[dict[str, Any], list[str]]:
    generation = generate_with_citation_repair(
        {"query": query, "knowledge_cutoff": cutoff, "eligible_evidence": []},
        set(),
    )
    return generation, []


def run_oneshot(query: str, cutoff: str, records: list[RetrievalRecord]) -> tuple[dict[str, Any], list[str]]:
    selected = retrieve(query, records, limit=ONESHOT_LIMIT)
    generation = generate_with_citation_repair(
        {"query": query, "knowledge_cutoff": cutoff, "eligible_evidence": compact_evidence_payload(selected)},
        {record.record_id for record in selected},
    )
    return generation, [record.record_id for record in selected]


def run_tool_agent(
    query: str,
    cutoff: str,
    corpus: EligibleCorpus,
    *,
    call_model: Any = call_local_with_tools,
    kg_enabled: bool = False,
) -> dict[str, Any]:
    trace: list[dict[str, Any]] = []
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": TOOL_SYSTEM.format(
            max_calls=MAX_TOOL_CALLS, fields=", ".join(HYPOTHESIS_FIELDS)) + (KG_SYSTEM_NOTE if kg_enabled else "")},
        {"role": "user", "content": json.dumps({"query": query, "knowledge_cutoff": cutoff}, ensure_ascii=False)},
    ]
    tools = KG_TOOLS if kg_enabled else TOOLS
    tool_calls = 0
    for turn in range(MAX_MODEL_TURNS):
        message = call_model(messages, tools)
        calls = message.get("tool_calls") or []
        if not calls:
            messages.append({"role": "assistant", "content": message.get("content") or ""})
            messages.append({"role": "user", "content": "Call submit_hypothesis now with the final hypothesis object."})
            continue
        messages.append({"role": "assistant", "content": message.get("content") or "", "tool_calls": calls})
        for call in calls:
            name = call["function"]["name"]
            raw_arguments = call["function"].get("arguments") or "{}"
            try:
                args = json.loads(raw_arguments)
            except json.JSONDecodeError:
                args = None
            if name == "submit_hypothesis":
                hypothesis = args.get("hypothesis") if isinstance(args, dict) else None
                try:
                    validated = _validate_generation(hypothesis, corpus.read_ids)
                except ValueError as error:
                    result = {"accepted": False, "error": str(error),
                              "instruction": "Fix the object and call submit_hypothesis again. Cite only records you have read."}
                    trace.append({"turn": turn, "tool": name, "accepted": False, "error": str(error)})
                    messages.append({"role": "tool", "tool_call_id": call["id"],
                                     "content": json.dumps(result, ensure_ascii=False)})
                    continue
                trace.append({"turn": turn, "tool": name, "accepted": True})
                validated = {**validated, "citation_validation": {"status": "valid", "removed_unknown_ids": []}}
                return {"generation": validated, "trace": trace, "tool_calls": tool_calls, "turns": turn + 1}
            if tool_calls >= MAX_TOOL_CALLS:
                result = {"error": "tool budget exhausted; call submit_hypothesis"}
                trace.append({"turn": turn, "tool": name, "refused": "budget_exhausted"})
                messages.append({"role": "tool", "tool_call_id": call["id"],
                                 "content": json.dumps(result, ensure_ascii=False)})
                continue
            if not isinstance(args, dict):
                result: dict[str, Any] = {"error": "tool arguments must be a JSON object"}
            elif name == "list_papers":
                result = corpus.list_papers()
            elif name == "search_corpus":
                result = corpus.search(str(args.get("query", "")), args.get("k", 6))
            elif name == "read_record":
                result = corpus.read(str(args.get("record_id", "")), args.get("offset", 0))
            elif name == "kg_lookup":
                result = corpus.kg_lookup(str(args.get("topic", "")))
            else:
                result = {"error": f"unknown tool {name}"}
            tool_calls += 1
            encoded = json.dumps(result, ensure_ascii=False)
            trace.append({"turn": turn, "tool": name, "args": args if isinstance(args, dict) else raw_arguments,
                          "result_chars": len(encoded)})
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": encoded})
            if tool_calls >= MAX_TOOL_CALLS:
                tools = SUBMIT_ONLY
        if tool_calls >= MAX_TOOL_CALLS:
            messages.append({"role": "user", "content": "The tool budget is used up. Call submit_hypothesis now."})
    raise LLMError(f"tool agent submitted no valid hypothesis within {MAX_MODEL_TURNS} turns")


def _generator_identity() -> str:
    if provider_info() == "trapi":
        return f"trapi:{os.environ.get('TRAPI_DEPLOYMENT', '')}"
    return f"{provider_info()}:{os.environ.get('OPENAI_MODEL', '')}"


def kg_excluded_dois(paper_id: str, metadata: dict[str, dict[str, Any]]) -> set[str]:
    """DOIs that must never contribute KG facts: the held-out paper and its work family."""
    target = metadata[paper_id]
    family = str(target.get("work_family_id") or "")
    dois = {str(target.get("doi") or "")}
    if family:
        dois |= {str(row.get("doi") or "") for row in metadata.values() if row.get("work_family_id") == family}
    return {doi.lower() for doi in dois if doi}


def build_corpus_and_run(
    case: dict[str, Any],
    level: str,
    setting: str,
    metadata: dict[str, dict[str, Any]],
    v2_units: list[Any],
    paper_maps_dir: Path,
    output_dir: Path,
    kg_db: Path | None = None,
) -> dict[str, Any]:
    paper_id = case["paper_id"]
    cutoff = case["publication_date"]
    query = case["queries"][level]["text"]
    run_id = f"{paper_id}__{level}__{setting}"
    web = evidence_mode() == "web"
    if web:
        import websearch
        chunk_records = websearch.case_records(paper_id, level, "text_chunks", question=query)
        unit_records: list[RetrievalRecord] = []
        eligible = {record.paper_id for record in chunk_records}
    else:
        eligible, chunk_records, unit_records = build_corpus(paper_id, cutoff, metadata, v2_units, paper_maps_dir)
    records = chunk_records + unit_records
    lookup = {record.record_id: record for record in records}
    started = time.time()
    status, error = "ok", None
    generation: dict[str, Any] | None = None
    accessed: list[str] = []
    trace: list[dict[str, Any]] = []
    web_log: list[dict[str, Any]] = []
    tool_calls = turns = 0
    try:
        if setting == "closed_book":
            generation, accessed = run_closed_book(query, cutoff)
        elif setting == "text_oneshot":
            generation, accessed = run_oneshot(query, cutoff, chunk_records)
        elif setting == "v2_oneshot":
            if web:
                raise ValueError("v2_oneshot has no web-corpus version (LLM-extracted units, loop.md 17.1)")
            generation, accessed = run_oneshot(query, cutoff, unit_records)
        elif setting in ("tool_agent", "tool_agent_kg"):
            kg = None
            if setting == "tool_agent_kg":
                if kg_db is None:
                    raise ValueError("tool_agent_kg requires a MatKG index (kg_db)")
                kg = TemporalKG(kg_db, cutoff, kg_excluded_dois(paper_id, metadata))
            corpus = None
            try:
                corpus = (websearch.WebEligibleCorpus(paper_id, level, query, kg=kg) if web
                          else EligibleCorpus(metadata, eligible, records, kg=kg))
                result = run_tool_agent(query, cutoff, corpus, kg_enabled=kg is not None)
            finally:
                if kg is not None:
                    kg.close()
                if web and corpus is not None:
                    web_log = corpus.tools.log
            lookup.update(corpus.lookup)
            generation = result["generation"]
            accessed = sorted(corpus.seen_ids | corpus.read_ids)
            trace, tool_calls, turns = result["trace"], result["tool_calls"], result["turns"]
        else:
            raise ValueError(f"unknown setting {setting}")
    except Exception as caught:  # noqa: BLE001 - failed runs are recorded, never silently dropped
        status, error = "failed", f"{type(caught).__name__}: {caught}"
    cited = sorted(set(
        (generation or {}).get("supporting_evidence_ids", []) + (generation or {}).get("conflicting_evidence_ids", [])
    ))
    def is_web(rid: str) -> bool:
        return rid in lookup and (lookup[rid].structured or {}).get("source") == "web"

    audit = audit_accessed([rid for rid in accessed if not is_web(rid)], lookup, paper_id, cutoff, metadata)
    if web:
        audit["target_doi_or_title_leaks"] = 0
        for key, value in websearch.audit_records([lookup[rid] for rid in accessed if is_web(rid)], paper_id).items():
            audit[key] = audit.get(key, 0) + value
    audit["invalid_citations"] = len(set(cited) - set(accessed))
    audit["query_leak"] = int(query_leak(query, metadata[paper_id]))
    cited_evidence = [{
        "record_id": rid,
        "paper_id": lookup[rid].paper_id,
        "publication_date": lookup[rid].publication_date,
        "kind": lookup[rid].kind,
        "text": lookup[rid].text[:CITED_TEXT_CHARS],
    } for rid in cited if rid in lookup]
    result = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "paper_id": paper_id,
        "query_level": level,
        "setting": setting,
        "publication_date": cutoff,
        "query": query,
        "generator": _generator_identity(),
        "eligible_paper_count": len(eligible),
        "corpus_records": {"chunks": len(chunk_records), "evidence_units": len(unit_records)},
        "status": status,
        "error": error,
        "generation": generation,
        "accessed_record_ids": accessed,
        "cited_evidence_ids": cited,
        "cited_evidence": cited_evidence,
        "tool_calls": tool_calls,
        "turns": turns,
        "tool_trace": trace,
        "audit": audit,
        **({"evidence_source": "web", "web_tool_log": web_log,
            "models": {"web_query_writer": f"trapi:{websearch.PHRASE_MODEL}"}} if web else {}),
        "elapsed_seconds": round(time.time() - started, 2),
    }
    atomic_json(output_dir / "runs" / f"{run_id}.json", result)
    return result


def load_cases(cases_dir: Path, case_ids: list[str] | None) -> list[dict[str, Any]]:
    cases = [
        _read_json(path) for path in sorted(cases_dir.glob("PMC*.json"))
        if path.name != "summary.json"
    ]
    if case_ids:
        wanted = set(case_ids)
        cases = [case for case in cases if case["paper_id"] in wanted]
    return cases


def generate_all(
    *,
    cases_dir: Path,
    metadata_path: Path,
    v2_dir: Path,
    paper_maps_dir: Path,
    output_dir: Path,
    settings: tuple[str, ...],
    levels: tuple[str, ...],
    case_ids: list[str] | None,
    workers: int,
    resume: bool,
    kg_db: Path | None = None,
) -> dict[str, int]:
    metadata = _date_map(metadata_path)
    v2_units = load_evidence(v2_dir)
    cases = load_cases(cases_dir, case_ids)
    (output_dir / "runs").mkdir(parents=True, exist_ok=True)
    jobs = []
    for case in cases:
        for level in levels:
            for setting in settings:
                run_id = f"{case['paper_id']}__{level}__{setting}"
                run_path = output_dir / "runs" / f"{run_id}.json"
                if resume and run_path.exists() and _read_json(run_path)["status"] == "ok":
                    continue
                jobs.append((case, level, setting))
    completed = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(build_corpus_and_run, case, level, setting, metadata, v2_units, paper_maps_dir, output_dir,
                        kg_db)
            for case, level, setting in jobs
        ]
        for future in as_completed(futures):
            row = future.result()
            completed += 1
            print(f"[eval-v3] {row['run_id']} {row['status']} tool_calls={row['tool_calls']} "
                  f"elapsed={row['elapsed_seconds']}s", file=sys.stderr, flush=True)
    return {"jobs": len(jobs), "completed": completed}


# ---------------------------------------------------------------- judging

def _blind_candidate(run: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Hide record IDs, source kinds and pipeline metadata so the judge cannot tell settings apart.

    Cited records get neutral labels (E1, E2, ...) used in both the citation lists and the evidence list.
    """
    labels = {record["record_id"]: f"E{index + 1}" for index, record in enumerate(run["cited_evidence"])}
    generation = {key: value for key, value in run["generation"].items() if key != "citation_validation"}
    for field in ("supporting_evidence_ids", "conflicting_evidence_ids"):
        generation[field] = [labels[rid] for rid in generation.get(field, []) if rid in labels]
    evidence = [{
        "evidence_id": labels[record["record_id"]],
        "paper_id": record["paper_id"],
        "publication_date": record["publication_date"],
        "text": record["text"],
    } for record in run["cited_evidence"]]
    return generation, evidence


def _record_judge_error(path: Path, identity: dict[str, Any], error: Exception) -> None:
    atomic_json(path, {"schema_version": SCHEMA_VERSION, **identity,
                       "error_type": type(error).__name__, "error": str(error)[:500]})


def judge_absolute(run: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    generation, evidence = _blind_candidate(run)
    payload = {
        "query": run["query"],
        "hidden_target": case["hidden_target"],
        "generated_hypothesis": generation,
        "cited_evidence": evidence,
    }
    score = _validate_score(judge_chat_json(_SCORE_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=12000))
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run["run_id"],
        "judge": judge_info(),
        "scores": score["scores"],
        "classification": score.get("classification", ""),
        "fatal_errors": score.get("fatal_errors", []),
        "explanation": score.get("explanation", ""),
    }


def judge_pair_once(case: dict[str, Any], first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    """Judge with `first` shown as candidate A and `second` as candidate B."""
    generation_a, evidence_a = _blind_candidate(first)
    generation_b, evidence_b = _blind_candidate(second)
    payload = {
        "query": first["query"],
        "hidden_target": case["hidden_target"],
        "candidate_A": {"generated_hypothesis": generation_a, "cited_evidence": evidence_a},
        "candidate_B": {"generated_hypothesis": generation_b, "cited_evidence": evidence_b},
    }
    result = judge_chat_json(PAIR_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=12000)
    if not isinstance(result, dict):
        result = {}
    winner = str(result.get("winner", "tie")).strip().upper()
    if winner not in {"A", "B", "TIE"}:
        winner = "TIE"
    try:
        confidence = float(result.get("confidence", 0.0) or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    return {"winner": winner, "confidence": confidence, "reason": str(result.get("reason", ""))}


def resolve_pair(first_name: str, second_name: str, ab: dict[str, Any], ba: dict[str, Any]) -> tuple[str, str]:
    """Combine both presentation orders. Agreement means the same underlying setting wins both times."""
    from_ab = {"A": first_name, "B": second_name, "TIE": "tie"}[ab["winner"]]
    from_ba = {"A": second_name, "B": first_name, "TIE": "tie"}[ba["winner"]]
    if from_ab == from_ba:
        return from_ab, "consistent"
    return "tie", "position_inconsistent"


def judge_all(
    *,
    cases_dir: Path,
    output_dir: Path,
    workers: int,
    resume: bool,
    pairs: tuple[tuple[str, str], ...] = PAIRS,
) -> dict[str, int]:
    cases = {case["paper_id"]: case for case in load_cases(cases_dir, None)}
    runs = {
        payload["run_id"]: payload
        for payload in (_read_json(path) for path in sorted((output_dir / "runs").glob("PMC*.json")))
    }
    abs_dir = output_dir / "judgments" / "absolute"
    pair_dir = output_dir / "judgments" / "pairwise"
    errors_dir = output_dir / "judgments" / "errors"
    for directory in (abs_dir, pair_dir, errors_dir):
        directory.mkdir(parents=True, exist_ok=True)
    counts = {"absolute": 0, "pairwise": 0}

    def absolute_job(run: dict[str, Any]) -> None:
        error_path = errors_dir / f"{run['run_id']}.json"
        try:
            judgment = judge_absolute(run, cases[run["paper_id"]])
        except Exception as error:  # noqa: BLE001 - recorded and left unjudged so a rerun retries it
            _record_judge_error(error_path, {"run_id": run["run_id"]}, error)
            return
        atomic_json(abs_dir / f"{run['run_id']}.json", judgment)
        error_path.unlink(missing_ok=True)

    def pair_job(paper_id: str, level: str, first_name: str, second_name: str) -> None:
        name = f"{paper_id}__{level}__{first_name}__vs__{second_name}"
        error_path = errors_dir / f"{name}.json"
        first = runs[f"{paper_id}__{level}__{first_name}"]
        second = runs[f"{paper_id}__{level}__{second_name}"]
        try:
            ab = judge_pair_once(cases[paper_id], first, second)
            ba = judge_pair_once(cases[paper_id], second, first)
        except Exception as error:  # noqa: BLE001 - recorded and left unjudged so a rerun retries it
            _record_judge_error(error_path, {"pair": name}, error)
            return
        outcome, consistency = resolve_pair(first_name, second_name, ab, ba)
        atomic_json(pair_dir / f"{name}.json", {
            "schema_version": SCHEMA_VERSION,
            "paper_id": paper_id,
            "query_level": level,
            "setting_a": first_name,
            "setting_b": second_name,
            "judge": judge_info(),
            "order_a_first": ab,
            "order_b_first": ba,
            "outcome": outcome,
            "consistency": consistency,
        })
        error_path.unlink(missing_ok=True)

    abs_jobs = [
        run for run in runs.values()
        if run["status"] == "ok" and not (resume and (abs_dir / f"{run['run_id']}.json").exists())
    ]
    pair_jobs = []
    for first_name, second_name in pairs:
        for paper_id in sorted(cases):
            for level in QUERY_LEVELS:
                key_a, key_b = f"{paper_id}__{level}__{first_name}", f"{paper_id}__{level}__{second_name}"
                if key_a not in runs or key_b not in runs:
                    continue
                if runs[key_a]["status"] != "ok" or runs[key_b]["status"] != "ok":
                    continue
                target = pair_dir / f"{paper_id}__{level}__{first_name}__vs__{second_name}.json"
                if resume and target.exists():
                    continue
                pair_jobs.append((paper_id, level, first_name, second_name))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(absolute_job, run) for run in abs_jobs]
        futures += [pool.submit(pair_job, *job) for job in pair_jobs]
        for future in as_completed(futures):
            future.result()
    counts["absolute"] = len(abs_jobs)
    counts["pairwise"] = len(pair_jobs)
    return counts


# ---------------------------------------------------------------- analysis

def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def exact_sign_test(diffs: list[float]) -> tuple[float, int, int]:
    positives = sum(1 for d in diffs if d > 0)
    negatives = sum(1 for d in diffs if d < 0)
    n = positives + negatives
    if n == 0:
        return 1.0, positives, negatives
    k = min(positives, negatives)
    p_value = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)
    return p_value, positives, negatives


def holm_adjust(p_values: list[float]) -> list[float]:
    """Holm-Bonferroni step-down adjustment, returned in the input order."""
    order = sorted(range(len(p_values)), key=lambda index: p_values[index])
    adjusted = [0.0] * len(p_values)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (len(p_values) - rank) * p_values[index]))
        adjusted[index] = running
    return adjusted


def cluster_bootstrap(per_paper: dict[str, list[float]]) -> tuple[float, float, float]:
    """Mean over papers of per-paper mean differences, with a 95% CI resampling papers."""
    paper_means = [mean(values) for values in per_paper.values()]
    point = mean(paper_means)
    rng = random.Random(BOOTSTRAP_SEED)
    n = len(paper_means)
    estimates = sorted(
        mean([paper_means[rng.randrange(n)] for _ in range(n)]) for _ in range(BOOTSTRAP_RESAMPLES)
    )
    low = estimates[int(0.025 * BOOTSTRAP_RESAMPLES)]
    high = estimates[int(0.975 * BOOTSTRAP_RESAMPLES) - 1]
    return point, low, high


def _load_dir(path: Path) -> dict[str, dict[str, Any]]:
    return {item.stem: _read_json(item) for item in sorted(path.glob("*.json"))} if path.exists() else {}


def analyze(*, cases_dir: Path, output_dir: Path) -> dict[str, Any]:
    cases = load_cases(cases_dir, None)
    expected_runs = len(cases) * len(QUERY_LEVELS) * len(SETTINGS)
    runs = _load_dir(output_dir / "runs")
    absolute = _load_dir(output_dir / "judgments" / "absolute")
    pairwise = _load_dir(output_dir / "judgments" / "pairwise")

    rows = []
    for run_id, run in runs.items():
        judgment = absolute.get(run_id)
        row = {
            "run_id": run_id, "paper_id": run["paper_id"], "query_level": run["query_level"],
            "setting": run["setting"], "status": run["status"], "judged": judgment is not None,
            "tool_calls": run["tool_calls"], "turns": run["turns"],
            "accessed": len(run["accessed_record_ids"]), "cited": len(run["cited_evidence_ids"]),
            "elapsed_seconds": run["elapsed_seconds"],
        }
        if judgment:
            scores = judgment["scores"]
            row.update({dim: scores[dim] for dim in ALL_DIMENSIONS})
            row["reconstruction_mean"] = mean([scores[d] for d in PRIMARY_DIMENSIONS])
            row["overall_mean"] = mean([scores[d] for d in ALL_DIMENSIONS])
            row["classification"] = judgment["classification"]
        rows.append(row)

    by_setting: dict[str, Any] = {}
    for setting in SETTINGS:
        selected = [row for row in rows if row["setting"] == setting]
        judged = [row for row in selected if row["judged"]]
        classes: dict[str, int] = defaultdict(int)
        for row in judged:
            classes[row["classification"]] += 1
        by_setting[setting] = {
            "runs_expected": len(cases) * len(QUERY_LEVELS),
            "runs_present": len(selected),
            "runs_failed": sum(1 for row in selected if row["status"] != "ok"),
            "runs_judged": len(judged),
            "reconstruction_mean": round(mean([row["reconstruction_mean"] for row in judged]), 4),
            "overall_mean": round(mean([row["overall_mean"] for row in judged]), 4),
            "dimension_means": {dim: round(mean([row[dim] for row in judged]), 4) for dim in ALL_DIMENSIONS},
            "classifications": dict(classes),
            "mean_tool_calls": round(mean([row["tool_calls"] for row in selected]), 2),
            "mean_turns": round(mean([row["turns"] for row in selected]), 2),
            "mean_accessed_records": round(mean([row["accessed"] for row in selected]), 2),
            "mean_cited_records": round(mean([row["cited"] for row in selected]), 2),
            "mean_elapsed_seconds": round(mean([row["elapsed_seconds"] for row in selected]), 2),
        }

    comparisons = []
    units: dict[str, dict[tuple[str, str], float]] = defaultdict(dict)
    for row in rows:
        if row["judged"]:
            units[row["setting"]][(row["paper_id"], row["query_level"])] = row["reconstruction_mean"]
    exploratory = [
        (first, second) for index, first in enumerate(SETTINGS) for second in SETTINGS[index + 1:]
        if (first, second) not in PAIRS and (second, first) not in PAIRS
    ]
    for first, second, role in ([(a, b, "primary") for a, b in PAIRS]
                                + [(a, b, "exploratory") for a, b in exploratory]):
        common = sorted(set(units[first]) & set(units[second]))
        per_paper: dict[str, list[float]] = defaultdict(list)
        for key in common:
            per_paper[key[0]].append(units[first][key] - units[second][key])
        if not per_paper:
            continue
        paper_diffs = [mean(values) for values in per_paper.values()]
        point, low, high = cluster_bootstrap(per_paper)
        p_value, positive, negative = exact_sign_test(paper_diffs)
        comparisons.append({
            "a": first, "b": second, "role": role, "metric": "reconstruction_mean (a minus b)",
            "units": len(common), "papers": len(per_paper),
            "mean_difference": round(point, 4),
            "ci95_cluster_bootstrap": [round(low, 4), round(high, 4)],
            "papers_a_higher": positive, "papers_b_higher": negative,
            "sign_test_p_two_sided": round(p_value, 4),
        })
    primary = [item for item in comparisons if item["role"] == "primary"]
    for item, adjusted in zip(primary, holm_adjust([item["sign_test_p_two_sided"] for item in primary])):
        item["holm_adjusted_p"] = round(adjusted, 4)

    pairwise_summary = []
    for first, second in PAIRS:
        judgments = [j for j in pairwise.values() if j["setting_a"] == first and j["setting_b"] == second]
        wins_a = sum(1 for j in judgments if j["outcome"] == first)
        wins_b = sum(1 for j in judgments if j["outcome"] == second)
        ties = sum(1 for j in judgments if j["outcome"] == "tie")
        inconsistent = sum(1 for j in judgments if j["consistency"] != "consistent")
        pairwise_summary.append({
            "a": first, "b": second, "judged_units": len(judgments),
            "a_wins": wins_a, "b_wins": wins_b, "ties": ties,
            "position_inconsistent": inconsistent,
            "a_win_rate_excluding_ties": round(wins_a / (wins_a + wins_b), 4) if wins_a + wins_b else None,
        })

    generators = sorted({run["generator"] for run in runs.values()})
    judges = sorted({judgment["judge"] for judgment in [*absolute.values(), *pairwise.values()]})
    pairs_expected = len(cases) * len(QUERY_LEVELS) * len(PAIRS)
    integrity = {
        "schema_version": SCHEMA_VERSION,
        "expected_runs": expected_runs,
        "runs_present": len(runs),
        "runs_failed": sum(1 for run in runs.values() if run["status"] != "ok"),
        "runs_judged": len(absolute),
        "temporal_violations": sum(run["audit"]["temporal_violations"] for run in runs.values()),
        "test_paper_leaks": sum(run["audit"]["test_paper_leaks"] for run in runs.values()),
        "family_leaks": sum(run["audit"]["family_leaks"] for run in runs.values()),
        "unknown_record_ids": sum(run["audit"]["unknown_record_ids"] for run in runs.values()),
        "invalid_citations": sum(run["audit"]["invalid_citations"] for run in runs.values()),
        "query_leaks": sum(run["audit"]["query_leak"] for run in runs.values()),
        "generators": generators,
        "judges": judges,
        "pairs_expected": pairs_expected,
        "pairs_judged": len(pairwise),
        "judge_errors": len(list((output_dir / "judgments" / "errors").glob("*.json"))),
    }
    integrity["verified"] = bool(
        integrity["runs_present"] == expected_runs
        and integrity["runs_failed"] == 0
        and integrity["runs_judged"] == expected_runs
        and integrity["pairs_judged"] == pairs_expected
        and integrity["judge_errors"] == 0
        and len(generators) == 1
        and len(judges) == 1
        and integrity["temporal_violations"] == 0
        and integrity["test_paper_leaks"] == 0
        and integrity["family_leaks"] == 0
        and integrity["unknown_record_ids"] == 0
        and integrity["invalid_citations"] == 0
        and integrity["query_leaks"] == 0
    )

    analysis = {
        "schema_version": SCHEMA_VERSION,
        "cases": len(cases),
        "query_levels": list(QUERY_LEVELS),
        "settings": list(SETTINGS),
        "primary_metric": "reconstruction_mean (mean of intervention, condition, mechanism, outcome; 0-4)",
        "by_setting": by_setting,
        "comparisons": comparisons,
        "pairwise": pairwise_summary,
        "integrity": integrity,
    }
    results = output_dir / "results"
    results.mkdir(parents=True, exist_ok=True)
    atomic_json(results / "analysis.json", analysis)
    atomic_json(results / "integrity_audit.json", integrity)
    (results / "summary.md").write_text(render_summary(analysis))
    return analysis


def render_summary(analysis: dict[str, Any]) -> str:
    integrity = analysis["integrity"]
    header = (
        f"Integrity verified: {integrity['verified']}. Runs judged {integrity['runs_judged']}/{integrity['expected_runs']}; "
        f"pairs judged {integrity['pairs_judged']}/{integrity['pairs_expected']}; judge errors {integrity['judge_errors']}; "
        f"generator {', '.join(integrity['generators'])}; judge {', '.join(integrity['judges'])}."
    )
    lines = [header, "", "| Setting | Runs judged | Reconstruction (0-4) | Overall (0-4) | Failed | Tool calls | Records accessed |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for setting, row in analysis["by_setting"].items():
        lines.append(
            f"| {setting} | {row['runs_judged']}/{row['runs_expected']} | {row['reconstruction_mean']:.2f} | "
            f"{row['overall_mean']:.2f} | {row['runs_failed']} | {row['mean_tool_calls']:.1f} | "
            f"{row['mean_accessed_records']:.1f} |")
    lines += ["", "| A | B | Role | Units | Mean difference (A-B) | 95% CI (papers bootstrap) | Papers A higher / B higher | Sign-test p | Holm p (primary family) |",
              "|---|---|---|---:|---:|---|---:|---:|---:|"]
    for item in analysis["comparisons"]:
        low, high = item["ci95_cluster_bootstrap"]
        holm = f"{item['holm_adjusted_p']:.3f}" if "holm_adjusted_p" in item else "n/a"
        lines.append(
            f"| {item['a']} | {item['b']} | {item['role']} | {item['units']} | {item['mean_difference']:+.2f} | "
            f"[{low:+.2f}, {high:+.2f}] | {item['papers_a_higher']} / {item['papers_b_higher']} | "
            f"{item['sign_test_p_two_sided']:.3f} | {holm} |")
    lines += ["", "| A | B | Judged units | A wins | B wins | Ties | Position-inconsistent | A win rate (no ties) |",
              "|---|---|---:|---:|---:|---:|---:|---:|"]
    for item in analysis["pairwise"]:
        rate = "n/a" if item["a_win_rate_excluding_ties"] is None else f"{item['a_win_rate_excluding_ties']:.2f}"
        lines.append(
            f"| {item['a']} | {item['b']} | {item['judged_units']} | {item['a_wins']} | {item['b_wins']} | "
            f"{item['ties']} | {item['position_inconsistent']} | {rate} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases-dir", type=Path, default=CASES_DIR)
    parser.add_argument("--metadata", type=Path, default=EXPERIMENT_DIR / "temporal_v2" / "temporal_metadata.json")
    parser.add_argument("--v2-dir", type=Path, default=EXPERIMENT_DIR / "temporal_v2" / "materials_evidence_v2")
    parser.add_argument("--paper-maps-dir", type=Path, default=EXPERIMENT_DIR / "section_aware" / "paper_maps")
    parser.add_argument("--output-dir", type=Path, default=RUN_ROOT / "eval_v3")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("--setting", action="append", choices=SETTINGS + ("tool_agent_kg",))
    gen.add_argument("--level", action="append", choices=QUERY_LEVELS)
    gen.add_argument("--case", action="append")
    gen.add_argument("--workers", type=int, default=4)
    gen.add_argument("--resume", action="store_true")
    gen.add_argument("--kg-db", type=Path, default=None, help="MatKG SQLite index, required for tool_agent_kg")
    judge = sub.add_parser("judge")
    judge.add_argument("--workers", type=int, default=4)
    judge.add_argument("--resume", action="store_true")
    sub.add_parser("analyze")
    args = parser.parse_args()
    if args.command == "generate":
        result = generate_all(
            cases_dir=args.cases_dir, metadata_path=args.metadata, v2_dir=args.v2_dir,
            paper_maps_dir=args.paper_maps_dir, output_dir=args.output_dir,
            settings=tuple(args.setting or SETTINGS), levels=tuple(args.level or QUERY_LEVELS),
            case_ids=args.case, workers=args.workers, resume=args.resume, kg_db=args.kg_db,
        )
    elif args.command == "judge":
        result = judge_all(cases_dir=args.cases_dir, output_dir=args.output_dir,
                           workers=args.workers, resume=args.resume)
    else:
        result = analyze(cases_dir=args.cases_dir, output_dir=args.output_dir)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
