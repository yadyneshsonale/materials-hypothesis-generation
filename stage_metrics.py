"""Intermediate-stage metrics for every hypothesis-generation method on the 12 held-out HEA cases.

Methods: closed_book, text_oneshot, v2_oneshot, tool_agent (eval_v3); resample, self_revise, critique
(eval_critique); tool_agent_kg (eval_v4_matkg). Nothing is regenerated; metrics are computed over stored outputs,
plus two judge-reliability passes (GPT-5.6 rejudging and a cross-family judge).

Stages (each resumable, one JSON per unit):
  replay          deterministic replay of each tool run's searches, reads and KG lookups (per-step results)
  embed           text-embedding-3-large (256 dims) for queries, search strings, results and hypotheses
  audit           GPT-5.6, target-free: claim grounding, causal chain, contradictions, mechanism source,
                  falsifiability, specificity, stated uncertainty, composition claims
  inferability    GPT-5.6, diagnostic: how much of the hidden target each query states or implies
  revision-review GPT-5.6, target-free: critic-finding validity and uptake, and fix type per changed field
  retest          GPT-5.6 judge run twice more on every judged output (test-retest reliability)
  cross-judge     DeepSeek-V4-Pro judge on every judged output (cross-family agreement)
  report          all metric tables

Target-free stages never receive the hidden target (asserted on every call). Diagnostic stages read it for
analysis only; nothing they produce feeds back into any generation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests

import llm_client as lc
from failure_analysis import ARMS, HEDGE, TARGET_TYPES, spearman
from hypothesis_evidence_v2 import atomic_json, load_evidence
from matkg_index import TemporalKG
from temporal_eval_critique import EVIDENCE_TEXT_CHARS
from temporal_eval_v3 import (
    ALL_DIMENSIONS,
    EXPERIMENT_DIR,
    HYPOTHESIS_FIELDS,
    PAGE_CHARS,
    PRIMARY_DIMENSIONS,
    QUERY_LEVELS,
    EligibleCorpus,
    _blind_candidate,
    _snippet,
    build_corpus,
    judge_absolute,
    kg_excluded_dois,
)
from temporal_hypothesis_benchmark import _SCORE_SYSTEM, _date_map, _read_json, _validate_score

OUT = EXPERIMENT_DIR / "stage_metrics"
CASES_DIR = EXPERIMENT_DIR / "temporal_v2" / "benchmark_cases"
METADATA = EXPERIMENT_DIR / "temporal_v2" / "temporal_metadata.json"
V2_DIR = EXPERIMENT_DIR / "temporal_v2" / "materials_evidence_v2"
PAPER_MAPS = EXPERIMENT_DIR / "section_aware" / "paper_maps"
V3 = EXPERIMENT_DIR / "eval_v3"
V4 = EXPERIMENT_DIR / "eval_v4_matkg"
CRIT = EXPERIMENT_DIR / "eval_critique"
CEILING = EXPERIMENT_DIR / "failure_analysis" / "evidence_ceiling"
DEFAULT_KG_DB = Path.home() / "matkg_index" / "entdoi.sqlite"

TOOL_ARMS = ("tool_agent", "resample", "tool_agent_kg")
ONESHOT_ARMS = ("text_oneshot", "v2_oneshot")
REVISION_ARMS = ("self_revise", "critique")
ONESHOT_TEXT_CHARS = 1600
AUDIT_TEXT_CHARS = 4000
CROSS_JUDGE = {"deployment": "DeepSeek-V4-Pro_2026-04-23", "token_field": "max_tokens", "temperature": 0.0}
EMBED_DEPLOYMENT = "text-embedding-3-large_1"
EMBED_DIMS = 256
SUPPORT_LEVELS = ("entailed", "partial", "unsupported")

# Elemental data: atomic mass (g/mol), room-temperature density (g/cm^3), valence electron concentration.
ELEMENTS: dict[str, tuple[float, float, int]] = {
    "Li": (6.94, 0.534, 1), "B": (10.81, 2.34, 3), "C": (12.01, 2.27, 4), "Mg": (24.31, 1.74, 2),
    "Al": (26.98, 2.70, 3), "Si": (28.09, 2.33, 4), "Ca": (40.08, 1.55, 2), "Sc": (44.96, 2.99, 3),
    "Ti": (47.87, 4.51, 4), "V": (50.94, 6.11, 5), "Cr": (52.00, 7.19, 6), "Mn": (54.94, 7.21, 7),
    "Fe": (55.85, 7.87, 8), "Co": (58.93, 8.90, 9), "Ni": (58.69, 8.91, 10), "Cu": (63.55, 8.96, 11),
    "Zn": (65.38, 7.14, 12), "Ga": (69.72, 5.91, 3), "Y": (88.91, 4.47, 3), "Zr": (91.22, 6.51, 4),
    "Nb": (92.91, 8.57, 5), "Mo": (95.95, 10.28, 6), "Ru": (101.07, 12.45, 8), "Pd": (106.42, 12.02, 10),
    "Ag": (107.87, 10.49, 11), "Sn": (118.71, 7.29, 4), "Hf": (178.49, 13.31, 4), "Ta": (180.95, 16.65, 5),
    "W": (183.84, 19.25, 6), "Re": (186.21, 21.02, 7), "Ir": (192.22, 22.56, 9), "Pt": (195.08, 21.45, 10),
    "Au": (196.97, 19.30, 11),
}
VEC_BCC_BELOW = 6.87  # Guo et al. 2011 empirical rule for HEA solid solutions
VEC_FCC_AT_LEAST = 8.0

AUDIT_SYSTEM = (
    "You audit one materials-science hypothesis produced by a generator. You see the task query, the hypothesis "
    "fields, and the full text of the evidence records it cites. You do not know the true answer, and you must not "
    "judge whether the hypothesis is correct; judge only its internal quality and its grounding. Return JSON with: "
    "\"claims\": list of atomic factual or causal claims in the hypothesis (at most 20), each {\"text\": str, "
    "\"field\": str, \"needs_support\": bool (true if it asserts a fact, value or mechanism that evidence should back), "
    "\"support\": one of entailed|partial|unsupported (whether the cited evidence backs it; unsupported when no cited "
    "record backs it), \"supporting_ids\": [record_ids among the cited records], \"same_system\": one of "
    "yes|no|unclear|na (whether the supporting evidence concerns the same alloy system as the claim; na if "
    "unsupported)}; \"chain\": {\"intervention_to_mediator\": 0-2, \"mediator_to_mechanism\": 0-2, "
    "\"mechanism_to_outcome\": 0-2} (2 = explicit and coherent link, 1 = vague or partly coherent, 0 = missing or "
    "incoherent); \"contradictions\": list of {\"fields\": [str], \"description\": str} for statements that contradict "
    "each other across fields; \"mechanism_source\": one of same_system_evidence|transferred_with_justification|"
    "transferred_without_justification|not_from_evidence; \"falsifiability\": {\"measurable_variable\": bool, "
    "\"threshold\": bool, \"control\": bool, \"decisive_outcome\": bool}; \"specificity\": {\"composition_quantified\": "
    "bool, \"process_parameters\": bool, \"outcome_quantified\": bool}; \"stated_uncertainty\": 0-2 (0 confident, "
    "2 highly uncertain); \"composition_claims\": list of {\"base\": {element: atomic_percent}, \"modified\": "
    "{element: atomic_percent}, \"claimed_density_change\": one of increase|decrease|none|unspecified, "
    "\"claimed_phase\": one of BCC|FCC|BCC+FCC|other|unspecified} for every explicit base-to-modified composition "
    "change (use element symbols; give atomic percents that sum to about 100; omit a claim if a composition is not "
    "stated)."
)
INFERABILITY_SYSTEM = (
    "You assess benchmark queries. The input has a query given to a hypothesis generator and the hidden result it is "
    "scored against. For each hidden-result field, rate how much the query alone gives away or implies: 2 the query "
    "states it or makes it near-certain, 1 the query points toward it but other answers are plausible, 0 the query "
    "does not imply it. Also estimate answer_space: how many substantially different reasonable interventions the "
    "query admits: one of single|few|many. Return JSON {\"fields\": {field: 0-2}, \"answer_space\": str, "
    "\"reason\": str}."
)
REVIEW_SYSTEM = (
    "You compare an original materials-science hypothesis with its revision. The input may include critic findings "
    "(with evidence labels) and the evidence records (labelled E1, E2, ...). For each finding decide validity: valid "
    "(the evidence and materials reasoning confirm the problem), partly_valid, or invalid; uptake: addressed, partly, "
    "or ignored in the revision; and fix: corrected (replaced with a supported or more precise statement), hedged "
    "(softened with uncertainty language without correcting), deleted, or none. For each hypothesis field that "
    "changed, classify the change: corrected, hedged, deleted, new_claim, rephrased. Return JSON {\"findings\": "
    "[{\"index\": int, \"validity\": str, \"uptake\": str, \"fix\": str}], \"field_changes\": [{\"field\": str, "
    "\"change\": str}]}."
)

_print_lock = threading.Lock()


# ---------------------------------------------------------------- context and units

_contexts: dict[str, dict[str, Any]] = {}
_context_lock = threading.Lock()
_meta: dict[str, Any] = {}


def metadata() -> dict[str, dict[str, Any]]:
    if "metadata" not in _meta:
        _meta["metadata"] = _date_map(METADATA)
        _meta["v2"] = load_evidence(V2_DIR)
    return _meta["metadata"]


def context(case: dict[str, Any]) -> dict[str, Any]:
    pid = case["paper_id"]
    with _context_lock:
        if pid not in _contexts:
            meta = metadata()
            eligible, chunks, units = build_corpus(pid, case["publication_date"], meta, _meta["v2"], PAPER_MAPS)
            records = [*chunks, *units]
            _contexts[pid] = {"eligible": eligible, "records": records,
                              "lookup": {r.record_id: r for r in records}}
        return _contexts[pid]


def cases() -> dict[str, dict[str, Any]]:
    if "cases" not in _meta:
        _meta["cases"] = {c["paper_id"]: c for c in (_read_json(p) for p in sorted(CASES_DIR.glob("PMC*.json")))}
    return _meta["cases"]


def run_jobs(stage: str, jobs: list[tuple[str, tuple[Any, ...]]], fn: Any, workers: int) -> dict[str, int]:
    """Run named jobs in parallel; a failed job is logged to errors/<stage>/ and retried on the next --resume run."""
    errors = OUT / "errors" / stage
    errors.mkdir(parents=True, exist_ok=True)
    done = failed = 0

    def safe(name: str, args: tuple[Any, ...]) -> bool:
        try:
            fn(*args)
        except Exception as error:  # noqa: BLE001 - logged and retried on resume
            atomic_json(errors / f"{name}.json", {"job": name, "error": f"{type(error).__name__}: {str(error)[:500]}"})
            return False
        (errors / f"{name}.json").unlink(missing_ok=True)
        return True

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for future in as_completed([pool.submit(safe, name, args) for name, args in jobs]):
            if future.result():
                done += 1
            else:
                failed += 1
    return {"done": done, "failed": failed}


def _judgment(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    judgment = _read_json(path)
    scores = judgment["scores"]
    return {"scores": scores, "classification": judgment.get("classification", ""),
            "recon": statistics.fmean(scores[d] for d in PRIMARY_DIMENSIONS),
            "overall": statistics.fmean(scores[d] for d in ALL_DIMENSIONS)}


def _reads(trace: list[dict[str, Any]]) -> list[tuple[str, int]]:
    out = []
    for step in trace:
        if step.get("tool") == "read_record" and isinstance(step.get("args"), dict) and "record_id" in step["args"] \
                and not step.get("refused"):
            try:
                offset = max(0, int(step["args"].get("offset", 0) or 0))
            except (TypeError, ValueError):
                offset = 0
            out.append((str(step["args"]["record_id"]), offset))
    return out


def load_units() -> list[dict[str, Any]]:
    all_cases = cases()
    units: list[dict[str, Any]] = []

    def base_unit(arm: str, paper_id: str, level: str) -> dict[str, Any]:
        return {"arm": arm, "paper_id": paper_id, "query_level": level, "key": f"{arm}__{paper_id}__{level}",
                "date": all_cases[paper_id]["publication_date"], "target_type": TARGET_TYPES[paper_id]}

    for setting in ("closed_book", "text_oneshot", "v2_oneshot", "tool_agent"):
        for run_path in sorted((V3 / "runs").glob(f"PMC*__{setting}.json")):
            units.append(_run_unit(base_unit(setting, *run_path.stem.split("__")[:2]), _read_json(run_path),
                                   V3 / "judgments" / "absolute" / run_path.name))
    for run_path in sorted((V4 / "runs").glob("PMC*__tool_agent_kg.json")):
        units.append(_run_unit(base_unit("tool_agent_kg", *run_path.stem.split("__")[:2]), _read_json(run_path),
                               V4 / "judgments" / "absolute" / run_path.name))
    for run_path in sorted((CRIT / "baseline_resample" / "runs").glob("PMC*__tool_agent.json")):
        units.append(_run_unit(base_unit("resample", *run_path.stem.split("__")[:2]), _read_json(run_path),
                               CRIT / "baseline_resample" / "judgments" / "absolute" / run_path.name))
    for arm in REVISION_ARMS:
        for rec_path in sorted((CRIT / "revisions" / arm).glob("PMC*.json")):
            rec = _read_json(rec_path)
            base = _read_json(V3 / "runs" / rec_path.name)
            unit = base_unit(arm, rec["paper_id"], rec["query_level"])
            unit.update({
                "query": rec["query"], "status": rec.get("status", ""),
                "generation": rec.get("revised_generation") or {},
                "cited_ids": rec.get("revised_cited_evidence_ids", []),
                "cited_evidence": rec.get("cited_evidence", []),
                "seen_ids": [], "read_ids": [], "read_offsets": {},
                "available": {"kind": "revision", "ids": sorted(base["accessed_record_ids"])},
                "trace": [], "tool_calls": base["tool_calls"], "turns": base["turns"], "elapsed": None,
                "critics": rec.get("critics", []), "reviser_status": (rec.get("reviser") or {}).get("status", ""),
                "base_generation": base["generation"], "base_accessed": sorted(base["accessed_record_ids"]),
                "original_cited_ids": rec.get("original_cited_evidence_ids", []),
                "judgment": _judgment(CRIT / "judgments" / arm / rec_path.name),
            })
            units.append(unit)
    return units


def _run_unit(unit: dict[str, Any], run: dict[str, Any], judgment_path: Path) -> dict[str, Any]:
    arm = unit["arm"]
    reads = _reads(run["tool_trace"]) if arm in TOOL_ARMS else []
    offsets: dict[str, int] = {}
    for rid, offset in reads:
        offsets[rid] = max(offsets.get(rid, 0), offset)
    read_ids = sorted(offsets)
    if arm in TOOL_ARMS:
        available = {"kind": "tool", "ids": read_ids}
        seen = sorted(set(run["accessed_record_ids"]) - set(read_ids))
    elif arm in ONESHOT_ARMS:
        available = {"kind": "oneshot", "ids": list(run["accessed_record_ids"])}
        seen = []
    else:
        available = {"kind": "none", "ids": []}
        seen = []
    unit.update({
        "query": run["query"], "status": run["status"], "generation": run.get("generation") or {},
        "cited_ids": run["cited_evidence_ids"], "cited_evidence": run.get("cited_evidence", []),
        "accessed_ids": list(run["accessed_record_ids"]), "seen_ids": seen, "read_ids": read_ids,
        "read_offsets": offsets, "read_calls": len(reads), "available": available, "trace": run["tool_trace"],
        "tool_calls": run["tool_calls"], "turns": run["turns"], "elapsed": run.get("elapsed_seconds"),
        "citation_status": (run.get("generation") or {}).get("citation_validation", {}).get("status", ""),
        "judgment": _judgment(judgment_path),
    })
    return unit


def record_text(unit: dict[str, Any], record_id: str, kg_texts: dict[str, str]) -> str:
    if record_id.startswith("KG::"):
        return kg_texts.get(record_id, "")
    record = context(cases()[unit["paper_id"]])["lookup"].get(record_id)
    return record.text if record else ""


def available_text(unit: dict[str, Any], kg_texts: dict[str, str]) -> str:
    """The evidence text this method actually had in front of it."""
    kind = unit["available"]["kind"]
    if kind == "none":
        return ""
    lookup = context(cases()[unit["paper_id"]])["lookup"]
    parts = []
    if kind == "oneshot":
        for rid in unit["available"]["ids"]:
            if rid in lookup:
                parts.append(lookup[rid].text[:ONESHOT_TEXT_CHARS])
    elif kind == "revision":
        for rid in unit["available"]["ids"]:
            text = kg_texts.get(rid, "") if rid.startswith("KG::") else (lookup[rid].text if rid in lookup else "")
            parts.append(text[:EVIDENCE_TEXT_CHARS])
    else:
        for rid, offset in unit["read_offsets"].items():
            text = kg_texts.get(rid, "") if rid.startswith("KG::") else (lookup[rid].text if rid in lookup else "")
            parts.append(text[:offset + PAGE_CHARS])
        for rid in unit["seen_ids"]:
            text = kg_texts.get(rid, "") if rid.startswith("KG::") else (lookup[rid].text if rid in lookup else "")
            parts.append(_snippet(text))
    return "\n".join(parts)


def hypothesis_fields(generation: dict[str, Any]) -> dict[str, Any]:
    return {k: generation.get(k) for k in HYPOTHESIS_FIELDS if k in generation}


# ---------------------------------------------------------------- deterministic helpers

NUMBER = re.compile(r"(?<![A-Za-z0-9_])(\d+(?:\.\d+)?)(?![\d])")
QUANTITY = re.compile(
    r"\d+(?:\.\d+)?\s*(?:%|at\.?\s?%|wt\.?\s?%|vol\.?\s?%|°\s?C|K\b|GPa|MPa|HV|g\s?/\s?cm|nm|µm|um|mm|h\b|hours?|"
    r"min\b|s\b|s\^?-1|J|eV|Å|K/s|°C/min)", re.IGNORECASE)


def numbers_in(text: str) -> list[str]:
    values = []
    for match in NUMBER.finditer(text or ""):
        value = match.group(1)
        if len(value) <= 1 and "." not in value:
            continue  # single digits are mostly list markers or element counts
        values.append(value.rstrip("0").rstrip(".") if "." in value else value)
    return values


def traced_share(numbers: list[str], evidence: str) -> float | None:
    if not numbers:
        return None
    evidence_numbers = set(numbers_in(evidence))
    return sum(n in evidence_numbers for n in numbers) / len(numbers)


def quantified_count(text: str) -> int:
    return len(QUANTITY.findall(text or ""))


def _normalise(comp: dict[str, Any]) -> dict[str, float] | None:
    clean: dict[str, float] = {}
    for element, value in (comp or {}).items():
        symbol = str(element).strip()
        if symbol not in ELEMENTS:
            return None
        try:
            amount = float(value)
        except (TypeError, ValueError):
            return None
        if amount < 0:
            return None
        clean[symbol] = clean.get(symbol, 0.0) + amount
    total = sum(clean.values())
    if total <= 0:
        return None
    return {k: v / total for k, v in clean.items()}


def rom_density(comp: dict[str, float]) -> float:
    mass = sum(c * ELEMENTS[e][0] for e, c in comp.items())
    volume = sum(c * ELEMENTS[e][0] / ELEMENTS[e][1] for e, c in comp.items())
    return mass / volume


def vec(comp: dict[str, float]) -> float:
    return sum(c * ELEMENTS[e][2] for e, c in comp.items())


def check_composition_claim(claim: dict[str, Any]) -> dict[str, Any]:
    base = _normalise(claim.get("base") or {})
    modified = _normalise(claim.get("modified") or {})
    result: dict[str, Any] = {"density": "unverifiable", "phase": "unverifiable"}
    direction = str(claim.get("claimed_density_change", "unspecified")).lower()
    if base and modified and direction in ("increase", "decrease"):
        before, after = rom_density(base), rom_density(modified)
        result["density_before"], result["density_after"] = round(before, 3), round(after, 3)
        actual = "increase" if after > before * 1.005 else "decrease" if after < before * 0.995 else "none"
        result["density"] = "consistent" if actual == direction else "inconsistent"
    phase = str(claim.get("claimed_phase", "unspecified")).upper()
    if modified and phase in ("BCC", "FCC"):
        value = vec(modified)
        result["vec"] = round(value, 2)
        predicted = "BCC" if value < VEC_BCC_BELOW else "FCC" if value >= VEC_FCC_AT_LEAST else "mixed"
        result["phase"] = "consistent" if predicted == phase else "ambiguous" if predicted == "mixed" else "inconsistent"
    return result


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def icc1(rows: list[list[float]]) -> float:
    """One-way random-effects ICC(1) for units (rows) each judged k times."""
    rows = [r for r in rows if len(r) >= 2]
    if len(rows) < 2:
        return float("nan")
    k = min(len(r) for r in rows)
    rows = [r[:k] for r in rows]
    grand = statistics.fmean(v for r in rows for v in r)
    n = len(rows)
    ms_between = k * sum((statistics.fmean(r) - grand) ** 2 for r in rows) / (n - 1)
    ms_within = sum((v - statistics.fmean(r)) ** 2 for r in rows for v in r) / (n * (k - 1))
    denom = ms_between + (k - 1) * ms_within
    return (ms_between - ms_within) / denom if denom else float("nan")


def kendall_tau(a: list[float], b: list[float]) -> float:
    pairs = concordant = discordant = 0
    for i in range(len(a)):
        for j in range(i + 1, len(a)):
            s = (a[i] - a[j]) * (b[i] - b[j])
            pairs += 1
            concordant += s > 0
            discordant += s < 0
    return (concordant - discordant) / pairs if pairs else float("nan")


def hedges(generation: dict[str, Any]) -> int:
    return len(HEDGE.findall(f"{generation.get('hypothesis', '')} {generation.get('predicted_outcome', '')}"))


def specificity_text(generation: dict[str, Any]) -> str:
    return " ".join(str(generation.get(k, "")) for k in ("hypothesis", "intervention", "conditions", "predicted_outcome"))


def supportive_ids(paper_id: str) -> set[str]:
    path = CEILING / f"{paper_id}.json"
    if not path.exists():
        return set()
    return {r["record_id"] for r in _read_json(path)["records"]
            if r["intervention_support"] >= 1 or r["mechanism_support"] >= 1}


# ---------------------------------------------------------------- stage: replay

def replay(workers: int, resume: bool, kg_db: Path) -> dict[str, int]:
    out_dir = OUT / "replay"
    out_dir.mkdir(parents=True, exist_ok=True)
    all_cases = cases()
    meta = metadata()
    jobs = [u for u in load_units() if u["arm"] in TOOL_ARMS
            and not (resume and (out_dir / f"{u['key']}.json").exists())]

    def job(unit: dict[str, Any]) -> bool:
        case = all_cases[unit["paper_id"]]
        ctx = context(case)
        kg = TemporalKG(kg_db, case["publication_date"], kg_excluded_dois(unit["paper_id"], meta)) \
            if unit["arm"] == "tool_agent_kg" else None
        corpus = EligibleCorpus(meta, ctx["eligible"], ctx["records"], kg=kg)
        steps: list[dict[str, Any]] = []
        kg_texts: dict[str, str] = {}
        try:
            executed = 0
            for step in unit["trace"]:
                tool = step.get("tool")
                if tool == "submit_hypothesis" or step.get("refused") or tool is None:
                    continue
                args = step.get("args") if isinstance(step.get("args"), dict) else {}
                executed += 1
                ids: list[str] = []
                if tool == "search_corpus":
                    ids = [r["record_id"] for r in corpus.search(str(args.get("query", "")), args.get("k", 6))["results"]]
                elif tool == "read_record":
                    rid = str(args.get("record_id", ""))
                    if rid in corpus.lookup:
                        corpus.read(rid, args.get("offset", 0))
                        ids = [rid]
                elif tool == "kg_lookup" and kg is not None:
                    result = corpus.kg_lookup(str(args.get("topic", "")))
                    for fact in result.get("facts", []):
                        rid = fact["record_id"]
                        kg_texts[rid] = corpus.lookup[rid].text
                        ids.append(rid)
                elif tool == "list_papers":
                    ids = []
                steps.append({"step": executed, "tool": tool, "args": args, "ids": ids})
        finally:
            if kg is not None:
                kg.close()
        replayed = {rid for s in steps for rid in s["ids"]}
        stored = set(unit["accessed_ids"])
        atomic_json(out_dir / f"{unit['key']}.json", {
            "unit": unit["key"], "steps": steps, "kg_texts": kg_texts,
            "consistent": replayed == stored,
            "missing_from_replay": sorted(stored - replayed), "extra_in_replay": sorted(replayed - stored),
        })
        return replayed == stored

    result = run_jobs("replay", [(u["key"], (u,)) for u in jobs], job, workers)
    result["consistent"] = sum(1 for p in out_dir.glob("*.json") if _read_json(p)["consistent"])
    return result


def load_replays() -> dict[str, dict[str, Any]]:
    return {p.stem: _read_json(p) for p in sorted((OUT / "replay").glob("*.json"))}


def all_kg_texts(replays: dict[str, dict[str, Any]]) -> dict[str, str]:
    texts: dict[str, str] = {}
    for r in replays.values():
        texts.update(r.get("kg_texts", {}))
    return texts


# ---------------------------------------------------------------- stage: embeddings

_embed_lock = threading.Lock()


def _embed_cache_path() -> Path:
    return OUT / "cache" / "embeddings.json"


def _load_embed_cache() -> dict[str, list[float]]:
    path = _embed_cache_path()
    return json.loads(path.read_text()) if path.exists() else {}


def _key(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def embed_texts(texts: list[str], cache: dict[str, list[float]]) -> None:
    pending = sorted({t for t in texts if t and _key(t) not in cache})
    url = (f"{lc.TRAPI_ENDPOINT}/openai/deployments/{EMBED_DEPLOYMENT}/embeddings"
           f"?api-version={lc.TRAPI_API_VERSION}")
    for start in range(0, len(pending), 64):
        batch = pending[start:start + 64]
        for attempt in range(5):
            response = requests.post(url, headers={"Authorization": f"Bearer {lc._trapi_token()}",
                                                   "Content-Type": "application/json"},
                                     json={"input": [t[:6000] for t in batch], "dimensions": EMBED_DIMS}, timeout=120)
            if response.status_code == 429:
                import time
                time.sleep(10 * (attempt + 1))
                continue
            response.raise_for_status()
            for text, item in zip(batch, response.json()["data"]):
                cache[_key(text)] = [round(v, 5) for v in item["embedding"]]
            break
        else:
            raise lc.LLMError("embedding requests kept failing")


def embed_stage() -> dict[str, int]:
    (OUT / "cache").mkdir(parents=True, exist_ok=True)
    cache = _load_embed_cache()
    units = load_units()
    replays = load_replays()
    kg_texts = all_kg_texts(replays)
    texts: list[str] = []
    for unit in units:
        texts.append(unit["query"])
        texts.append(str(unit["generation"].get("intervention", "")))
        texts.append(str(unit["generation"].get("mechanism", "")))
        replay_row = replays.get(unit["key"])
        if replay_row:
            for step in replay_row["steps"]:
                if step["tool"] == "search_corpus":
                    texts.append(str(step["args"].get("query", "")))
                for rid in step["ids"]:
                    texts.append(record_text(unit, rid, kg_texts)[:2000])
        for rid in unit["read_ids"]:
            texts.append(record_text(unit, rid, kg_texts)[:2000])
    embed_texts(texts, cache)
    _embed_cache_path().write_text(json.dumps(cache))
    return {"embeddings": len(cache)}


# ---------------------------------------------------------------- LLM stages

def _int02(value: Any) -> int:
    try:
        return max(0, min(2, int(value)))
    except (TypeError, ValueError):
        return 0


def _validated_audit(raw: Any) -> dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    claims = []
    for item in raw.get("claims", [])[:20] if isinstance(raw.get("claims"), list) else []:
        if not isinstance(item, dict):
            continue
        support = str(item.get("support", "unsupported")).lower()
        same = str(item.get("same_system", "na")).lower()
        claims.append({
            "text": str(item.get("text", ""))[:400], "field": str(item.get("field", "")),
            "needs_support": bool(item.get("needs_support", True)),
            "support": support if support in SUPPORT_LEVELS else "unsupported",
            "supporting_ids": [str(x) for x in item.get("supporting_ids", []) if isinstance(x, (str, int))],
            "same_system": same if same in ("yes", "no", "unclear", "na") else "unclear",
        })
    chain_raw = raw.get("chain") if isinstance(raw.get("chain"), dict) else {}
    chain = {k: _int02(chain_raw.get(k)) for k in ("intervention_to_mediator", "mediator_to_mechanism",
                                                    "mechanism_to_outcome")}
    falsi_raw = raw.get("falsifiability") if isinstance(raw.get("falsifiability"), dict) else {}
    spec_raw = raw.get("specificity") if isinstance(raw.get("specificity"), dict) else {}
    source = str(raw.get("mechanism_source", "not_from_evidence"))
    uncertainty = _int02(raw.get("stated_uncertainty"))
    return {
        "claims": claims, "chain": chain,
        "contradictions": [c for c in raw.get("contradictions", []) if isinstance(c, dict)]
        if isinstance(raw.get("contradictions"), list) else [],
        "mechanism_source": source if source in ("same_system_evidence", "transferred_with_justification",
                                                 "transferred_without_justification", "not_from_evidence")
        else "not_from_evidence",
        "falsifiability": {k: bool(falsi_raw.get(k, False)) for k in
                           ("measurable_variable", "threshold", "control", "decisive_outcome")},
        "specificity": {k: bool(spec_raw.get(k, False)) for k in
                        ("composition_quantified", "process_parameters", "outcome_quantified")},
        "stated_uncertainty": uncertainty,
        "composition_claims": [c for c in raw.get("composition_claims", []) if isinstance(c, dict)][:6]
        if isinstance(raw.get("composition_claims"), list) else [],
    }


def assert_target_free(payload: dict[str, Any]) -> None:
    if "hidden_target" in json.dumps(payload, ensure_ascii=False):
        raise ValueError("target-free stages must never receive the hidden target")


def audit_stage(workers: int, resume: bool) -> dict[str, int]:
    out_dir = OUT / "audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    kg_texts = all_kg_texts(load_replays())
    jobs = [u for u in load_units() if u["judgment"] and not (resume and (out_dir / f"{u['key']}.json").exists())]

    def job(unit: dict[str, Any]) -> None:
        cited = []
        for rid in unit["cited_ids"]:
            text = record_text(unit, rid, kg_texts)
            if not text:
                text = next((c.get("text", "") for c in unit["cited_evidence"] if c.get("record_id") == rid), "")
            cited.append({"record_id": rid, "text": text[:AUDIT_TEXT_CHARS]})
        payload = {"query": unit["query"], "hypothesis": hypothesis_fields(unit["generation"]), "cited_evidence": cited}
        assert_target_free(payload)
        raw = lc.judge_chat_json(AUDIT_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=16000)
        atomic_json(out_dir / f"{unit['key']}.json", {"unit": unit["key"], "auditor": lc.judge_info(),
                                                        **_validated_audit(raw)})

    return run_jobs("audit", [(u["key"], (u,)) for u in jobs], job, workers)


def inferability_stage(workers: int, resume: bool) -> dict[str, int]:
    out_dir = OUT / "inferability"
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = [(c, lvl) for c in cases().values() for lvl in QUERY_LEVELS
            if not (resume and (out_dir / f"{c['paper_id']}__{lvl}.json").exists())]
    fields = ("material_initial_state", "intervention", "conditions", "structural_mediator", "mechanism",
              "predicted_outcome", "baseline", "boundary")

    def job(case: dict[str, Any], level: str) -> None:
        payload = {"query": case["queries"][level]["text"],
                   "hidden_result": {f: case["hidden_target"].get(f) for f in fields}}
        raw = lc.judge_chat_json(INFERABILITY_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=8000)
        raw = raw if isinstance(raw, dict) else {}
        rated = raw.get("fields") if isinstance(raw.get("fields"), dict) else {}
        values = {}
        for f in fields:
            try:
                values[f] = max(0, min(2, int(rated.get(f, 0))))
            except (TypeError, ValueError):
                values[f] = 0
        space = str(raw.get("answer_space", "many")).lower()
        atomic_json(out_dir / f"{case['paper_id']}__{level}.json", {
            "paper_id": case["paper_id"], "query_level": level, "fields": values,
            "answer_space": space if space in ("single", "few", "many") else "many",
            "reason": str(raw.get("reason", ""))[:800]})

    return run_jobs("inferability", [(f"{c['paper_id']}__{lvl}", (c, lvl)) for c, lvl in jobs], job, workers)


def revision_review_stage(workers: int, resume: bool) -> dict[str, int]:
    out_dir = OUT / "revision_review"
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = [u for u in load_units() if u["arm"] in REVISION_ARMS and u["judgment"]
            and not (resume and (out_dir / f"{u['key']}.json").exists())]

    def job(unit: dict[str, Any]) -> None:
        lookup = context(cases()[unit["paper_id"]])["lookup"]
        labels = {rid: f"E{i + 1}" for i, rid in enumerate(unit["base_accessed"])}
        findings = []
        for critic in unit["critics"]:
            for finding in critic.get("findings", []):
                findings.append({"index": len(findings), "role": critic["role"], **finding})
        payload = {
            "original": hypothesis_fields(unit["base_generation"]),
            "revised": hypothesis_fields(unit["generation"]),
            "findings": findings,
            "evidence": [{"label": labels[rid], "record_id": rid,
                          "text": lookup[rid].text[:EVIDENCE_TEXT_CHARS] if rid in lookup else ""}
                         for rid in unit["base_accessed"]],
        }
        assert_target_free(payload)
        raw = lc.judge_chat_json(REVIEW_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=16000)
        raw = raw if isinstance(raw, dict) else {}
        reviewed = []
        for item in raw.get("findings", []) if isinstance(raw.get("findings"), list) else []:
            if isinstance(item, dict):
                reviewed.append({k: str(item.get(k, "")) for k in ("validity", "uptake", "fix")} |
                                {"index": item.get("index")})
        changes = [{"field": str(c.get("field", "")), "change": str(c.get("change", ""))}
                   for c in (raw.get("field_changes") or []) if isinstance(c, dict)]
        atomic_json(out_dir / f"{unit['key']}.json", {"unit": unit["key"], "reviewer": lc.judge_info(),
                                                        "findings_total": len(findings), "findings": reviewed,
                                                        "field_changes": changes})

    return run_jobs("revision_review", [(u["key"], (u,)) for u in jobs], job, workers)


def _run_like(unit: dict[str, Any]) -> dict[str, Any]:
    return {"run_id": unit["key"], "query": unit["query"], "generation": unit["generation"],
            "cited_evidence": unit["cited_evidence"]}


def retest_stage(workers: int, resume: bool, repeats: int = 2) -> dict[str, int]:
    out_dir = OUT / "retest"
    out_dir.mkdir(parents=True, exist_ok=True)
    all_cases = cases()
    jobs = [(u, r) for u in load_units() if u["judgment"] for r in range(1, repeats + 1)
            if not (resume and (out_dir / f"{u['key']}__r{r}.json").exists())]

    def job(unit: dict[str, Any], repeat: int) -> None:
        judgment = judge_absolute(_run_like(unit), all_cases[unit["paper_id"]])
        atomic_json(out_dir / f"{unit['key']}__r{repeat}.json", judgment)

    return run_jobs("retest", [(f"{u['key']}__r{r}", (u, r)) for u, r in jobs], job, workers)


def cross_judge_stage(workers: int, resume: bool) -> dict[str, int]:
    out_dir = OUT / "cross_judge"
    out_dir.mkdir(parents=True, exist_ok=True)
    all_cases = cases()
    jobs = [u for u in load_units() if u["judgment"] and not (resume and (out_dir / f"{u['key']}.json").exists())]

    def job(unit: dict[str, Any]) -> None:
        generation, evidence = _blind_candidate(_run_like(unit))
        payload = {"query": unit["query"], "hidden_target": all_cases[unit["paper_id"]]["hidden_target"],
                   "generated_hypothesis": generation, "cited_evidence": evidence}
        raw = lc.trapi_chat_json(CROSS_JUDGE["deployment"], _SCORE_SYSTEM, json.dumps(payload, ensure_ascii=False),
                                 max_tokens=8000, token_field=CROSS_JUDGE["token_field"],
                                 temperature=CROSS_JUDGE["temperature"], retries=6)
        score = _validate_score(raw)
        atomic_json(out_dir / f"{unit['key']}.json", {"unit": unit["key"], "judge": f"trapi:{CROSS_JUDGE['deployment']}",
                                                        "scores": score["scores"],
                                                        "classification": score.get("classification", "")})

    return run_jobs("cross_judge", [(u["key"], (u,)) for u in jobs], job, workers)


# ---------------------------------------------------------------- report

def mean(values: list[float]) -> float:
    values = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return statistics.fmean(values) if values else float("nan")


def r2(value: Any) -> Any:
    return round(value, 3) if isinstance(value, float) and not math.isnan(value) else (None if isinstance(value, float) else value)


def report() -> dict[str, Any]:
    results = OUT / "results"
    results.mkdir(parents=True, exist_ok=True)
    units = load_units()
    judged = [u for u in units if u["judgment"]]
    replays = load_replays()
    kg_texts = all_kg_texts(replays)
    cache = _load_embed_cache()
    emb = lambda text: cache.get(_key(text)) if text else None  # noqa: E731
    audits = {p.stem: _read_json(p) for p in sorted((OUT / "audit").glob("*.json"))}
    infer = {p.stem: _read_json(p) for p in sorted((OUT / "inferability").glob("*.json"))}
    reviews = {p.stem: _read_json(p) for p in sorted((OUT / "revision_review").glob("*.json"))}
    retests: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in sorted((OUT / "retest").glob("*.json")):
        retests[p.stem.rsplit("__r", 1)[0]].append(_read_json(p))
    cross = {p.stem: _read_json(p) for p in sorted((OUT / "cross_judge").glob("*.json"))}
    by_arm = {arm: [u for u in judged if u["arm"] == arm] for arm in ARMS}

    # ---- stage 1: query
    query_stage = {}
    for lvl in QUERY_LEVELS:
        rows = [v for k, v in infer.items() if k.endswith(f"__{lvl}")]
        if not rows:
            continue
        query_stage[lvl] = {
            "inferability_mean": r2(mean([mean(list(r["fields"].values())) for r in rows])),
            "intervention_stated_or_implied": r2(mean([r["fields"]["intervention"] / 2 for r in rows])),
            "mechanism_stated_or_implied": r2(mean([r["fields"]["mechanism"] / 2 for r in rows])),
            "outcome_stated_or_implied": r2(mean([r["fields"]["predicted_outcome"] / 2 for r in rows])),
            "answer_space": dict(Counter(r["answer_space"] for r in rows)),
        }
    diversity = {}
    for lvl in QUERY_LEVELS:
        spreads = []
        for paper in sorted(TARGET_TYPES):
            vecs = [emb(str(u["generation"].get("intervention", ""))) for u in judged
                    if u["paper_id"] == paper and u["query_level"] == lvl]
            vecs = [v for v in vecs if v]
            if len(vecs) >= 2:
                spreads.append(mean([1 - cosine(vecs[i], vecs[j]) for i in range(len(vecs))
                                     for j in range(i + 1, len(vecs))]))
        diversity[lvl] = r2(mean(spreads))
    # inferability vs score
    infer_vs_score = []
    for u in judged:
        row = infer.get(f"{u['paper_id']}__{u['query_level']}")
        if row:
            infer_vs_score.append((mean(list(row["fields"].values())), u["judgment"]["recon"]))
    query_stage["spearman_inferability_vs_score"] = r2(spearman([a for a, _ in infer_vs_score],
                                                                [b for _, b in infer_vs_score]))

    # ---- stages 2 and 3: retrieval and reading
    retrieval = {}
    for arm in (*ONESHOT_ARMS, *TOOL_ARMS):
        rows = []
        for u in by_arm[arm]:
            support = supportive_ids(u["paper_id"])
            if arm in ONESHOT_ARMS:
                seen = set(u["available"]["ids"])
                read = seen
                steps = []
                first_hit = None
            else:
                rp = replays.get(u["key"], {"steps": []})
                steps = rp["steps"]
                seen = {rid for s in steps for rid in s["ids"]}
                read = set(u["read_ids"])
                first_hit = next((s["step"] for s in steps if set(s["ids"]) & support), None)
            searches = [s for s in steps if s["tool"] == "search_corpus"]
            search_vecs = [emb(str(s["args"].get("query", ""))) for s in searches]
            novelty = [1 - cosine(search_vecs[i], search_vecs[i - 1]) for i in range(1, len(search_vecs))
                       if search_vecs[i] and search_vecs[i - 1]]
            qv = emb(u["query"])
            result_ids = [rid for s in searches for rid in s["ids"]] if steps else list(seen)
            sims = [cosine(qv, v) for v in (emb(record_text(u, rid, kg_texts)[:2000]) for rid in result_ids) if v and qv]
            lookup = context(cases()[u["paper_id"]])["lookup"]
            papers = {lookup[rid].paper_id for rid in seen if rid in lookup}
            sections = {lookup[rid].kind for rid in seen if rid in lookup}
            seen_support = seen & support
            rows.append({
                "recall": len(seen_support) / len(support) if support else None,
                "read_recall": len(read & support) / len(support) if support else None,
                "first_hit": first_hit, "hit_any": bool(seen_support),
                "missed": (len(seen_support - read) / len(seen_support)) if seen_support and arm in TOOL_ARMS else None,
                "novelty": mean(novelty) if novelty else None,
                "result_relevance": mean(sims) if sims else None,
                "distinct_papers": len(papers), "distinct_sections": len(sections),
                "paging_waste": ((u["read_calls"] - len(u["read_ids"])) / u["read_calls"])
                if arm in TOOL_ARMS and u.get("read_calls") else None,
                "yield": len(u["read_ids"]) / u["tool_calls"] if arm in TOOL_ARMS and u["tool_calls"] else None,
                "utilisation": len(set(u["cited_ids"]) & read) / len(read) if read else None,
                "recon": u["judgment"]["recon"],
            })
        retrieval[arm] = {
            "units": len(rows),
            "supportive_recall": r2(mean([r["recall"] for r in rows])),
            "supportive_read_recall": r2(mean([r["read_recall"] for r in rows])),
            "units_with_supportive_hit": r2(mean([1.0 if r["hit_any"] else 0.0 for r in rows])),
            "steps_to_first_supportive_hit": r2(mean([r["first_hit"] for r in rows if r["first_hit"]])),
            "missed_opportunity": r2(mean([r["missed"] for r in rows])),
            "search_novelty": r2(mean([r["novelty"] for r in rows])),
            "result_relevance_to_query": r2(mean([r["result_relevance"] for r in rows])),
            "distinct_papers_seen": r2(mean([r["distinct_papers"] for r in rows])),
            "distinct_section_kinds_seen": r2(mean([r["distinct_sections"] for r in rows])),
            "paging_waste": r2(mean([r["paging_waste"] for r in rows])),
            "distinct_reads_per_call": r2(mean([r["yield"] for r in rows])),
            "evidence_utilisation": r2(mean([r["utilisation"] for r in rows])),
            "spearman_recall_vs_score": r2(spearman([r["recall"] or 0 for r in rows], [r["recon"] for r in rows])),
        }
    consistency = {"replayed": len(replays), "consistent": sum(1 for r in replays.values() if r["consistent"])}

    # ---- stages 4-6: grounding, reasoning, form
    grounding, reasoning, form, physics = {}, {}, {}, {}
    for arm in ARMS:
        rows = by_arm[arm]
        g_rows, r_rows, f_rows = [], [], []
        density_checks, phase_checks = Counter(), Counter()
        for u in rows:
            a = audits.get(u["key"])
            gen = u["generation"]
            numbers = numbers_in(" ".join(str(gen.get(k, "")) for k in HYPOTHESIS_FIELDS
                                          if k not in ("supporting_evidence_ids", "conflicting_evidence_ids")))
            traced = traced_share(numbers, available_text(u, kg_texts))
            f_rows.append({"hedges": hedges(gen), "quantities": quantified_count(specificity_text(gen)),
                           "length": len(specificity_text(gen)), "traced": traced,
                           "claims": len(a["claims"]) if a else None,
                           "falsi": mean([1.0 if v else 0.0 for v in a["falsifiability"].values()]) if a else None,
                           "spec": mean([1.0 if v else 0.0 for v in a["specificity"].values()]) if a else None,
                           "uncertainty": a["stated_uncertainty"] if a else None, "recon": u["judgment"]["recon"]})
            if not a:
                continue
            needing = [c for c in a["claims"] if c["needs_support"]]
            supported = [c for c in needing if c["support"] in ("entailed", "partial")]
            cited = set(u["cited_ids"])
            used = {rid for c in supported for rid in c["supporting_ids"]} & cited
            g_rows.append({
                "entailed": sum(c["support"] == "entailed" for c in needing) / len(needing) if needing else None,
                "supported": len(supported) / len(needing) if needing else None,
                "citation_precision": len(used) / len(cited) if cited else None,
                "cross_system": sum(c["same_system"] == "no" for c in supported) / len(supported) if supported else None,
                "claims": len(a["claims"]),
            })
            r_rows.append({
                "chain": mean(list(a["chain"].values())) / 2,
                "chain_complete": all(v == 2 for v in a["chain"].values()),
                "contradictions": len(a["contradictions"]),
                "source": a["mechanism_source"],
            })
            for claim in a["composition_claims"]:
                check = check_composition_claim(claim)
                density_checks[check["density"]] += 1
                phase_checks[check["phase"]] += 1
        grounding[arm] = {
            "audited": len(g_rows),
            "claims_per_hypothesis": r2(mean([r["claims"] for r in g_rows])),
            "claim_entailed_rate": r2(mean([r["entailed"] for r in g_rows])),
            "claim_supported_rate": r2(mean([r["supported"] for r in g_rows])),
            "citation_precision": r2(mean([r["citation_precision"] for r in g_rows])),
            "cross_system_support_rate": r2(mean([r["cross_system"] for r in g_rows])),
            "numbers_traced_to_evidence": r2(mean([r["traced"] for r in f_rows])),
        }
        sources = Counter(r["source"] for r in r_rows)
        reasoning[arm] = {
            "causal_chain_score": r2(mean([r["chain"] for r in r_rows])),
            "complete_chain_rate": r2(mean([1.0 if r["chain_complete"] else 0.0 for r in r_rows])),
            "contradictions_per_hypothesis": r2(mean([r["contradictions"] for r in r_rows])),
            "units_with_contradiction": r2(mean([1.0 if r["contradictions"] else 0.0 for r in r_rows])),
            "mechanism_source": {k: r2(v / len(r_rows)) for k, v in sources.items()} if r_rows else None,
            "transferred_without_justification": r2(sources["transferred_without_justification"] / len(r_rows))
            if r_rows else None,
        }
        physics[arm] = {"density_checks": dict(density_checks), "phase_checks": dict(phase_checks)}
        form[arm] = {
            "hedges_per_hypothesis": r2(mean([r["hedges"] for r in f_rows])),
            "hedges_per_claim": r2(mean([r["hedges"] / r["claims"] for r in f_rows if r["claims"]])),
            "quantities_per_hypothesis": r2(mean([r["quantities"] for r in f_rows])),
            "specificity_checklist": r2(mean([r["spec"] for r in f_rows])),
            "falsifiability_checklist": r2(mean([r["falsi"] for r in f_rows])),
            "stated_uncertainty": r2(mean([r["uncertainty"] for r in f_rows])),
            "calibration_spearman_uncertainty_vs_score": r2(spearman(
                [r["uncertainty"] for r in f_rows if r["uncertainty"] is not None],
                [r["recon"] for r in f_rows if r["uncertainty"] is not None])),
        }
    # best-of-k and diversity
    def unit_key(u: dict[str, Any]) -> tuple[str, str]:
        return (u["paper_id"], u["query_level"])
    ta = {unit_key(u): u for u in by_arm["tool_agent"]}
    rs = {unit_key(u): u for u in by_arm["resample"]}
    common = sorted(set(ta) & set(rs))
    best_of = {
        "tool_agent_mean": r2(mean([ta[k]["judgment"]["recon"] for k in common])),
        "resample_mean": r2(mean([rs[k]["judgment"]["recon"] for k in common])),
        "best_of_2": r2(mean([max(ta[k]["judgment"]["recon"], rs[k]["judgment"]["recon"]) for k in common])),
        "sample_intervention_distance": r2(mean([
            1 - cosine(emb(str(ta[k]["generation"].get("intervention", ""))) or [0], emb(str(rs[k]["generation"].get("intervention", ""))) or [0])
            for k in common])),
    }
    all_units_by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for u in judged:
        all_units_by_key[unit_key(u)].append(u)
    best_of["best_of_all_methods"] = r2(mean([max(x["judgment"]["recon"] for x in v) for v in all_units_by_key.values()]))
    best_of["oracle_gain_over_best_single_method"] = r2(best_of["best_of_all_methods"] - max(
        mean([u["judgment"]["recon"] for u in by_arm[arm]]) for arm in ARMS))

    # ---- stage 7: critique and revision
    revision = {}
    for arm in REVISION_ARMS:
        rows = by_arm[arm]
        validity, uptake, fixes, changes = Counter(), Counter(), Counter(), Counter()
        harm = help_ = 0
        dims = 0
        churn = []
        for u in rows:
            rv = reviews.get(u["key"])
            if rv:
                for f in rv["findings"]:
                    validity[f["validity"]] += 1
                    uptake[f["uptake"]] += 1
                    fixes[f["fix"]] += 1
                for c in rv["field_changes"]:
                    changes[c["change"]] += 1
            base = ta.get(unit_key(u))
            if base:
                for d in PRIMARY_DIMENSIONS:
                    before, after = base["judgment"]["scores"][d], u["judgment"]["scores"][d]
                    harm += after <= before - 1
                    help_ += after >= before + 1
                    dims += 1
            churn.append(len(set(u["cited_ids"]) ^ set(u.get("original_cited_ids", []))))
        total_f = sum(validity.values())
        revision[arm] = {
            "findings_reviewed": total_f,
            "finding_validity": {k: r2(v / max(1, total_f)) for k, v in validity.items()},
            "finding_uptake": {k: r2(v / max(1, total_f)) for k, v in uptake.items()},
            "finding_fix_type": {k: r2(v / max(1, total_f)) for k, v in fixes.items()},
            "field_change_types": dict(changes),
            "harm_rate_per_dimension": r2(harm / max(1, dims)),
            "help_rate_per_dimension": r2(help_ / max(1, dims)),
            "citation_churn_per_unit": r2(mean(churn)),
        }
    harm = help_ = dims = 0
    for k in common:
        for d in PRIMARY_DIMENSIONS:
            before, after = ta[k]["judgment"]["scores"][d], rs[k]["judgment"]["scores"][d]
            harm += after <= before - 1
            help_ += after >= before + 1
            dims += 1
    revision["resample_reference"] = {"harm_rate_per_dimension": r2(harm / max(1, dims)),
                                      "help_rate_per_dimension": r2(help_ / max(1, dims))}

    # ---- stage 8: KG
    kg_rows = by_arm["tool_agent_kg"]
    kg_calls = kg_used = 0
    fact_sims = []
    for u in kg_rows:
        rp = replays.get(u["key"], {"steps": []})
        calls = [s for s in rp["steps"] if s["tool"] == "kg_lookup"]
        kg_calls += len(calls)
        used = {rid for rid in u["read_ids"] if rid.startswith("KG::")} | {rid for rid in u["cited_ids"] if rid.startswith("KG::")}
        kg_used += len(used)
        qv = emb(u["query"])
        for s in calls:
            for rid in s["ids"]:
                fv = emb(kg_texts.get(rid, "")[:2000])
                if qv and fv:
                    fact_sims.append(cosine(qv, fv))
    kg_stage = {
        "kg_lookups": kg_calls,
        "kg_facts_read_or_cited_per_lookup": r2(kg_used / max(1, kg_calls)),
        "kg_fact_relevance_to_query": r2(mean(fact_sims)),
        "paper_result_relevance_to_query": retrieval["tool_agent_kg"]["result_relevance_to_query"],
        "searches_per_run_kg": r2(mean([sum(1 for s in replays.get(u["key"], {"steps": []})["steps"] if s["tool"] == "search_corpus") for u in kg_rows])),
        "searches_per_run_plain": r2(mean([sum(1 for s in replays.get(u["key"], {"steps": []})["steps"] if s["tool"] == "search_corpus") for u in by_arm["tool_agent"]])),
        "supportive_recall_kg": retrieval["tool_agent_kg"]["supportive_recall"],
        "supportive_recall_plain": retrieval["tool_agent"]["supportive_recall"],
    }

    # ---- stage 9: judge reliability
    rows3 = []
    class_agree = class_total = 0
    for u in judged:
        extra = retests.get(u["key"], [])
        if len(extra) >= 2:
            values = [u["judgment"]["recon"]] + [statistics.fmean(e["scores"][d] for d in PRIMARY_DIMENSIONS) for e in extra[:2]]
            rows3.append(values)
            classes = [u["judgment"]["classification"]] + [e.get("classification", "") for e in extra[:2]]
            class_agree += len(set(classes)) == 1
            class_total += 1
    judge_noise = {
        "units_with_3_judgments": len(rows3),
        "mean_within_unit_sd": r2(mean([statistics.pstdev(r) for r in rows3])),
        "mean_abs_diff_original_vs_rejudge": r2(mean([abs(r[0] - r[1]) for r in rows3] + [abs(r[0] - r[2]) for r in rows3])),
        "icc1_reconstruction": r2(icc1(rows3)),
        "classification_identical_all_3": r2(class_agree / max(1, class_total)),
    }
    method_means_3 = {}
    for arm in ARMS:
        vals = [mean([u["judgment"]["recon"]] + [statistics.fmean(e["scores"][d] for d in PRIMARY_DIMENSIONS)
                                                 for e in retests.get(u["key"], [])]) for u in by_arm[arm]]
        method_means_3[arm] = r2(mean(vals))
    judge_noise["method_means_original_judge"] = {arm: r2(mean([u["judgment"]["recon"] for u in by_arm[arm]])) for arm in ARMS}
    judge_noise["method_means_avg_of_3_judgments"] = method_means_3
    gen_noise = [abs(ta[k]["judgment"]["recon"] - rs[k]["judgment"]["recon"]) for k in common]
    judge_noise["generation_plus_judge_abs_diff_reference"] = r2(mean(gen_noise))

    pairs = [(u["judgment"]["recon"], statistics.fmean(cross[u["key"]]["scores"][d] for d in PRIMARY_DIMENSIONS))
             for u in judged if u["key"] in cross]
    method_gpt = [mean([u["judgment"]["recon"] for u in by_arm[arm]]) for arm in ARMS]
    method_x = [mean([statistics.fmean(cross[u["key"]]["scores"][d] for d in PRIMARY_DIMENSIONS)
                      for u in by_arm[arm] if u["key"] in cross]) for arm in ARMS]
    cross_stage = {
        "units": len(pairs),
        "spearman_unit_scores": r2(spearman([a for a, _ in pairs], [b for _, b in pairs])),
        "mean_difference_cross_minus_gpt": r2(mean([b - a for a, b in pairs])),
        "mean_abs_difference": r2(mean([abs(b - a) for a, b in pairs])),
        "method_means_cross_judge": {arm: r2(v) for arm, v in zip(ARMS, method_x)},
        "kendall_tau_method_ranking": r2(kendall_tau(method_gpt, method_x)),
        "classification_agreement": r2(mean([1.0 if cross[u["key"]]["classification"] == u["judgment"]["classification"] else 0.0
                                             for u in judged if u["key"] in cross])),
    }
    style = {}
    for name, getter in (("length_chars", lambda u: len(specificity_text(u["generation"]))),
                         ("hedges", lambda u: hedges(u["generation"])),
                         ("citations", lambda u: len(u["cited_ids"])),
                         ("quantities", lambda u: quantified_count(specificity_text(u["generation"])))):
        within = []
        for lvl in QUERY_LEVELS:
            rows = [u for u in judged if u["query_level"] == lvl]
            within.append(spearman([getter(u) for u in rows], [u["judgment"]["recon"] for u in rows]))
        style[name] = {"spearman_all": r2(spearman([getter(u) for u in judged], [u["judgment"]["recon"] for u in judged])),
                       "spearman_within_level_mean": r2(mean(within))}
    position = {}
    for name, directory in (("eval_v3", V3), ("eval_v4_matkg", V4)):
        ps = [_read_json(p) for p in sorted((directory / "judgments" / "pairwise").glob("*.json"))]
        position[name] = r2(sum(p["consistency"] == "consistent" for p in ps) / max(1, len(ps)))

    # ---- stage 10: cost
    cost = {}
    for arm in ARMS:
        rows = by_arm[arm]
        calls = []
        for u in rows:
            if arm in ("closed_book", *ONESHOT_ARMS):
                calls.append(1 + (u.get("citation_status") == "valid_after_regeneration"))
            elif arm in TOOL_ARMS:
                calls.append(u["turns"])
            else:
                reviser = 2 if u.get("reviser_status") == "revised_after_repair" else 1
                calls.append(u["turns"] + reviser + (3 if arm == "critique" else 0))
        cost[arm] = {"model_calls_per_unit": r2(mean(calls)),
                     "generation_seconds_per_unit": r2(mean([u["elapsed"] for u in rows if u.get("elapsed")])),
                     "reconstruction_per_10_calls": r2(10 * mean([u["judgment"]["recon"] for u in rows]) / max(1e-9, mean(calls)))}

    analysis = {
        "query_stage": query_stage, "cross_method_intervention_diversity": diversity,
        "retrieval_and_reading": retrieval, "replay_consistency": consistency,
        "grounding": grounding, "reasoning": reasoning, "physical_checks": physics, "form": form,
        "best_of": best_of, "revision": revision, "kg": kg_stage,
        "judge_reliability": judge_noise, "cross_judge": cross_stage, "style_bias": style,
        "position_consistency": position, "cost": cost,
        "counts": {"units": len(units), "judged": len(judged), "audits": len(audits), "inferability": len(infer),
                   "reviews": len(reviews), "retest_units": sum(len(v) >= 2 for v in retests.values()),
                   "cross_judged": len(cross)},
    }
    atomic_json(results / "stage_metrics.json", analysis)
    (results / "stage_tables.md").write_text(render(analysis))
    write_calibration_sheet(judged)
    return analysis


def write_calibration_sheet(judged: list[dict[str, Any]], n: int = 30) -> None:
    """Stratified sample for expert calibration: every method, every level, spread of judge scores."""
    import random
    rng = random.Random(20261022)
    picked = []
    for arm in ARMS:
        pool = sorted([u for u in judged if u["arm"] == arm], key=lambda u: u["judgment"]["recon"])
        if not pool:
            continue
        thirds = [pool[: len(pool) // 3], pool[len(pool) // 3: 2 * len(pool) // 3], pool[2 * len(pool) // 3:]]
        for third in thirds:
            if third and len(picked) < n:
                picked.append(rng.choice(third))
    while len(picked) < n:
        candidate = rng.choice(judged)
        if candidate not in picked:
            picked.append(candidate)
    lines = ["# Expert calibration sheet", "",
             "Score each hypothesis against the paper's actual result on the same 0–4 scales the judge used "
             "(intervention, condition, mechanism, outcome). Judge scores are deliberately not shown.", "",
             "| # | Unit | Expert intervention | Expert condition | Expert mechanism | Expert outcome | Notes |",
             "|---:|---|---|---|---|---|---|"]
    for i, u in enumerate(picked, 1):
        lines.append(f"| {i} | {u['key']} | | | | | |")
    (OUT / "results" / "expert_calibration_sheet.md").write_text("\n".join(lines) + "\n")


def _f(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, dict):
        return ", ".join(f"{k}: {_f(v)}" for k, v in value.items()) or "n/a"
    return str(value)


def _table(title: str, rows: dict[str, dict[str, Any]], columns: list[str] | None = None) -> list[str]:
    cols = columns or list(rows)
    metrics = list(dict.fromkeys(k for c in cols for k in rows.get(c, {})))
    out = [f"## {title}", "", "| Metric | " + " | ".join(cols) + " |", "|---|" + "---:|" * len(cols)]
    for m in metrics:
        out.append(f"| {m} | " + " | ".join(_f(rows.get(c, {}).get(m)) for c in cols) + " |")
    return out + [""]


def render(a: dict[str, Any]) -> str:
    lines = ["# Intermediate-stage metrics", ""]
    q = {k: v for k, v in a["query_stage"].items() if isinstance(v, dict)}
    lines += _table("1. Query stage (diagnostic: inferability needs the hidden target)", q, list(q))
    lines += [f"Spearman, query inferability vs reconstruction (all units): {_f(a['query_stage'].get('spearman_inferability_vs_score'))}.",
              "", "Cross-method intervention diversity (mean pairwise embedding distance between the methods' "
              "interventions for the same unit): " + ", ".join(f"{k} {_f(v)}" for k, v in a["cross_method_intervention_diversity"].items()) + ".", ""]
    lines += _table("2–3. Retrieval and reading", a["retrieval_and_reading"])
    lines += [f"Replay consistency: {a['replay_consistency']['consistent']} of {a['replay_consistency']['replayed']} tool runs "
              "reproduce exactly the stored accessed records.", ""]
    lines += _table("4. Grounding (target-free)", a["grounding"])
    lines += _table("5. Reasoning (target-free)", {k: {kk: vv for kk, vv in v.items()} for k, v in a["reasoning"].items()})
    lines += _table("5b. Physical checks on extracted composition claims", a["physical_checks"])
    lines += _table("6. Hypothesis form", a["form"])
    lines += ["## 6b. Sampling", "", "| Metric | Value |", "|---|---:|"] + [f"| {k} | {_f(v)} |" for k, v in a["best_of"].items()] + [""]
    lines += _table("7. Critique and revision", a["revision"])
    lines += ["## 8. Knowledge graph", "", "| Metric | Value |", "|---|---:|"] + [f"| {k} | {_f(v)} |" for k, v in a["kg"].items()] + [""]
    j = a["judge_reliability"]
    lines += ["## 9. Judge reliability", "", "| Metric | Value |", "|---|---:|"]
    lines += [f"| {k} | {_f(v)} |" for k, v in j.items() if not isinstance(v, dict)]
    lines += ["", "| Method | Original judge | Mean of 3 GPT-5.6 judgments | DeepSeek-V4-Pro judge |", "|---|---:|---:|---:|"]
    for arm in ARMS:
        lines.append(f"| {arm} | {_f(j['method_means_original_judge'][arm])} | {_f(j['method_means_avg_of_3_judgments'][arm])} | "
                     f"{_f(a['cross_judge']['method_means_cross_judge'][arm])} |")
    lines += ["", "| Cross-judge metric | Value |", "|---|---:|"] + [f"| {k} | {_f(v)} |" for k, v in a["cross_judge"].items() if not isinstance(v, dict)]
    lines += ["", "| Style feature | Spearman with reconstruction (all) | Mean within-level Spearman |", "|---|---:|---:|"]
    lines += [f"| {k} | {_f(v['spearman_all'])} | {_f(v['spearman_within_level_mean'])} |" for k, v in a["style_bias"].items()]
    lines += ["", "Pairwise position consistency: " + ", ".join(f"{k} {_f(v)}" for k, v in a["position_consistency"].items()) + ".", ""]
    lines += _table("10. Cost", a["cost"])
    lines += [f"Counts: {_f(a['counts'])}."]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("replay", "audit", "inferability", "revision-review", "retest", "cross-judge"):
        p = sub.add_parser(name)
        p.add_argument("--workers", type=int, default=6)
        p.add_argument("--resume", action="store_true")
        if name == "replay":
            p.add_argument("--kg-db", type=Path, default=DEFAULT_KG_DB)
    sub.add_parser("embed")
    sub.add_parser("report")
    args = parser.parse_args()
    if args.command == "replay":
        result: Any = replay(args.workers, args.resume, args.kg_db)
    elif args.command == "embed":
        result = embed_stage()
    elif args.command == "audit":
        result = audit_stage(args.workers, args.resume)
    elif args.command == "inferability":
        result = inferability_stage(args.workers, args.resume)
    elif args.command == "revision-review":
        result = revision_review_stage(args.workers, args.resume)
    elif args.command == "retest":
        result = retest_stage(args.workers, args.resume)
    elif args.command == "cross-judge":
        result = cross_judge_stage(args.workers, args.resume)
    else:
        result = report()["counts"]
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
