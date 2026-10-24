"""Extraction-rubric experiment: what should be extracted from earlier papers and shown to the hypothesis agent?

Four extraction rubrics are applied to every paper with the local generator model (Qwen3.5-35B-A3B), so the
extractor adds no knowledge source beyond what the generator already has. Every extracted item must carry at least
one verbatim quote from the paper; items whose quotes cannot be found in the text are dropped.

  card        one structured digest per paper window: question, system, route, findings, mechanism, limits, future work
  effects     intervention -> effect records from the paper's own results (base system, change, conditions,
              structure change, property change with direction and magnitude, attributed mechanism)
  mechanisms  mechanism statements with scope: system, operating conditions, evidence type, stated limits
  gaps        stated limitations, open problems, failed attempts, trade-offs and future work, with the lever to pull

Arms (one-shot generation with an identical evidence budget, two samples per unit):
  closed_book, text_chunks (raw section text), v2_units (existing structured units), card, effects, mechanisms,
  gaps, mixed (effects + mechanisms + gaps in one pool)

Stages: extract -> generate -> judge (GPT-5.6) / cross-judge (DeepSeek-V4-Pro) / audit (target-free GPT-5.6) /
ceiling (diagnostic GPT-5.6) -> report. Each stage is resumable and logs failed jobs for retry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import time
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import llm_client as lc
from failure_analysis import CEILING_SYSTEM, ORACLE_TEXT_CHARS, TARGET_TYPES, spearman, target_text
from hypothesis_evidence_v2 import atomic_json, load_evidence
from stage_metrics import AUDIT_SYSTEM, CROSS_JUDGE, HEDGE, _validated_audit, assert_target_free, kendall_tau
from temporal_eval_v3 import (
    ALL_DIMENSIONS,
    CASES_DIR,
    RUN_ROOT,
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    CITED_TEXT_CHARS,
    EXPERIMENT_DIR,
    HYPOTHESIS_FIELDS,
    PRIMARY_DIMENSIONS,
    QUERY_LEVELS,
    _blind_candidate,
    _generator_identity,
    build_corpus,
    cluster_bootstrap,
    exact_sign_test,
    holm_adjust,
    judge_absolute,
    run_closed_book,
)
from temporal_hypothesis_benchmark import (
    RetrievalRecord,
    _SCORE_SYSTEM,
    _date_map,
    _read_json,
    _validate_score,
    compact_evidence_payload,
    generate_with_citation_repair,
    retrieve,
)

OUT = RUN_ROOT / "rubric_eval"
# Rubric extractions describe pre-cutoff corpus papers only and are shared by every run root.
EXTRACTIONS = EXPERIMENT_DIR / "rubric_eval" / "extractions"
TEXT_DIR = EXPERIMENT_DIR / "data" / "corpus" / "text"
METADATA = EXPERIMENT_DIR / "temporal_v2" / "temporal_metadata.json"
V2_DIR = EXPERIMENT_DIR / "temporal_v2" / "materials_evidence_v2"
PAPER_MAPS = EXPERIMENT_DIR / "section_aware" / "paper_maps"

RUBRICS = ("card", "effects", "mechanisms", "gaps")
ARMS = ("closed_book", "text_chunks", "v2_units", "card", "effects", "mechanisms", "gaps", "mixed")
REPRESENTATIONS = ARMS[1:]
PRIMARY_BASELINE = "text_chunks"
SAMPLES = (1, 2)
WINDOW_CHARS = 48000
EXTRACT_MAX_TOKENS = 7000
EVIDENCE_BUDGET_CHARS = 16000
RECORD_MAX_CHARS = 1600
# Paper cards average about 2,900 characters; a 1,600 cap would cut their mechanism, limitations and future-work
# fields. Cards get a larger per-record cap inside the same total budget, so the card arm shows fewer, whole cards.
RECORD_MAX_CHARS_BY_ARM = {"card": 3200}
MAX_RECORDS = 24
MIN_QUOTE_CHARS = 20
MAX_QUOTES = 3
ORACLE_K = 20

BACK_MATTER = re.compile(
    r"^(references|reference|acknowledg(e)?ments?|funding( statement)?|author contributions|conflicts? of interest|"
    r"competing interests?|data availability( statement)?|supplementary (materials?|information)|declaration of "
    r"competing interest|institutional review board statement|informed consent statement)\s*$", re.IGNORECASE)

COMMON_RULES = (
    "Use only the paper text provided; do not add knowledge from anywhere else. Report what this paper's authors "
    "did, observed, argued or proposed, not results that the paper attributes to cited works. Every item must "
    "include \"quotes\": 1 to 3 exact, verbatim copies of sentences or sentence fragments (20 to 300 characters "
    "each) from the provided text that support the item; copy them character for character. Give numbers with "
    "units when the text gives them. Write \"not stated\" for fields the text does not cover. Return a JSON object "
    "{\"items\": [...]}."
)
RUBRIC_PROMPTS = {
    "card": (
        "You write a structured digest of one high-entropy-alloy research paper (or one part of it) for a scientist "
        "who will use earlier literature to propose new hypotheses. Produce exactly one item with fields: "
        "\"research_question\", \"material_system\" (compositions or alloy family), \"processing_route\" (method and "
        "key parameters), \"test_conditions\", \"key_findings\" (list of 3-8 findings with numbers), \"mechanism\" "
        "(the authors' explanation), \"limitations\" (stated by the authors), \"future_work\" (stated by the "
        "authors), \"quotes\". " + COMMON_RULES
    ),
    "effects": (
        "You extract intervention-effect records from one high-entropy-alloy research paper (or one part of it): "
        "each record is something the authors changed and what happened as a result, from their own experiments or "
        "simulations. Produce up to 12 items with fields: \"base_system\" (the starting alloy or state), "
        "\"intervention\" (what was changed and by how much: composition, processing, treatment, test condition), "
        "\"processing\" (route and parameters), \"test_conditions\", \"structure_change\" (phases, microstructure, "
        "defects), \"property_change\" (property, direction and magnitude with units, compared with what), "
        "\"attributed_mechanism\" (the authors' explanation, or \"not stated\"), \"evidence_type\" (one of measured, "
        "simulated, calculated), \"quotes\". " + COMMON_RULES
    ),
    "mechanisms": (
        "You extract mechanism statements from one high-entropy-alloy research paper (or one part of it), each "
        "with its scope, so a reader can judge whether it transfers to another alloy. Produce up to 8 items with "
        "fields: \"mechanism\" (the causal explanation the authors give), \"system\" (the specific compositions or "
        "alloy class it was shown for), \"operating_conditions\" (temperature, stress, environment, processing state "
        "in which it was observed), \"evidence_type\" (one of measured, simulated, inferred), "
        "\"supporting_observation\" (the observation offered for it), \"scope_limits\" (where the authors say it "
        "does not hold, was not tested, or competes with another mechanism), \"alternatives_considered\", "
        "\"quotes\". " + COMMON_RULES
    ),
    "gaps": (
        "You extract research gaps and levers from one high-entropy-alloy research paper (or one part of it): "
        "problems the authors state remain open, limitations of their results, attempts that failed, trade-offs "
        "they observed, and work they propose next. Produce up to 8 items with fields: \"type\" (one of limitation, "
        "open_problem, failed_attempt, tradeoff, future_work), \"statement\", \"system\" (the alloy or class it "
        "concerns), \"lever\" (the variable that could be changed to address it, as stated or directly implied by "
        "the text), \"quotes\". " + COMMON_RULES
    ),
}
RENDER_FIELDS = {
    "card": [("Question", "research_question"), ("System", "material_system"), ("Processing", "processing_route"),
             ("Test conditions", "test_conditions"), ("Findings", "key_findings"), ("Mechanism", "mechanism"),
             ("Limitations", "limitations"), ("Future work", "future_work")],
    "effects": [("Base system", "base_system"), ("Intervention", "intervention"), ("Processing", "processing"),
                ("Test conditions", "test_conditions"), ("Structure change", "structure_change"),
                ("Property change", "property_change"), ("Mechanism", "attributed_mechanism"),
                ("Evidence", "evidence_type")],
    "mechanisms": [("Mechanism", "mechanism"), ("System", "system"), ("Conditions", "operating_conditions"),
                   ("Evidence", "evidence_type"), ("Observation", "supporting_observation"),
                   ("Scope limits", "scope_limits"), ("Alternatives", "alternatives_considered")],
    "gaps": [("Type", "type"), ("Statement", "statement"), ("System", "system"), ("Lever", "lever")],
}
RUBRIC_LABEL = {"card": "Paper card", "effects": "Intervention effect", "mechanisms": "Mechanism with scope",
                "gaps": "Gap and lever"}
KEY_FIELD = {"card": "key_findings", "effects": "intervention", "mechanisms": "mechanism", "gaps": "statement"}


# ---------------------------------------------------------------- shared helpers

def run_jobs(stage: str, jobs: list[tuple[str, tuple[Any, ...]]], fn: Any, workers: int) -> dict[str, int]:
    errors = OUT / "errors" / stage
    errors.mkdir(parents=True, exist_ok=True)
    counts = Counter()

    def safe(name: str, args: tuple[Any, ...]) -> str:
        try:
            fn(*args)
        except Exception as error:  # noqa: BLE001 - logged and retried on resume
            atomic_json(errors / f"{name}.json", {"job": name, "error": f"{type(error).__name__}: {str(error)[:600]}"})
            return "failed"
        (errors / f"{name}.json").unlink(missing_ok=True)
        return "done"

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for future in as_completed([pool.submit(safe, name, args) for name, args in jobs]):
            counts[future.result()] += 1
    return {"jobs": len(jobs), **dict(counts)}


_cache: dict[str, Any] = {}


def metadata() -> dict[str, dict[str, Any]]:
    if "metadata" not in _cache:
        _cache["metadata"] = _date_map(METADATA)
    return _cache["metadata"]


def cases() -> dict[str, dict[str, Any]]:
    if "cases" not in _cache:
        _cache["cases"] = {c["paper_id"]: c for c in (_read_json(p) for p in sorted(CASES_DIR.glob("PMC*.json")))}
    return _cache["cases"]


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text or "")).lower()
    text = re.sub(r"[^0-9a-z]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def strip_back_matter(text: str) -> str:
    lines = text.splitlines()
    total = len(text)
    position = 0
    for line in lines:
        if BACK_MATTER.match(line.strip()) and position > 0.4 * total:
            return text[:position].rstrip()
        position += len(line) + 1
    return text


def windows(text: str, size: int = WINDOW_CHARS) -> list[str]:
    if len(text) <= size:
        return [text]
    parts: list[str] = []
    paragraphs = text.split("\n")
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 1 > size and current:
            parts.append(current)
            current = ""
        while len(paragraph) > size:
            parts.append(paragraph[:size])
            paragraph = paragraph[size:]
        current = f"{current}\n{paragraph}" if current else paragraph
    if current.strip():
        parts.append(current)
    return parts


def valid_quotes(quotes: Any, window_norm: str) -> list[str]:
    kept = []
    for quote in quotes if isinstance(quotes, list) else []:
        text = str(quote).strip()
        norm = normalise(text)
        if len(norm) >= MIN_QUOTE_CHARS and norm in window_norm:
            kept.append(text[:400])
        if len(kept) >= MAX_QUOTES:
            break
    return kept


def _field_text(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(str(v) for v in value if str(v).strip())
    return str(value or "").strip()


def is_substantive(rubric: str, item: dict[str, Any]) -> bool:
    key = _field_text(item.get(KEY_FIELD[rubric]))
    return bool(key) and key.lower() not in ("not stated", "none", "n/a")


def render(rubric: str, item: dict[str, Any]) -> str:
    parts = [RUBRIC_LABEL[rubric] + "."]
    for label, field in RENDER_FIELDS[rubric]:
        value = _field_text(item.get(field))
        if value and value.lower() != "not stated":
            parts.append(f"{label}: {value}.")
    if item.get("quotes"):
        parts.append(f"Quote: \"{item['quotes'][0]}\"")
    return " ".join(parts)


# ---------------------------------------------------------------- stage: extract

def extract_window(rubric: str, paper_id: str, title: str, window: str, part: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    user = json.dumps({"paper_title": title, "part": part, "text": window}, ensure_ascii=False)
    try:
        raw = lc.chat_json(RUBRIC_PROMPTS[rubric], user, max_tokens=EXTRACT_MAX_TOKENS, retries=3)
    except lc.TruncatedError:
        if len(window) < 12000:
            raise
        half = len(window) // 2
        cut = window.rfind("\n", 0, half) or half
        left, left_stats = extract_window(rubric, paper_id, title, window[:cut], f"{part}a")
        right, right_stats = extract_window(rubric, paper_id, title, window[cut:], f"{part}b")
        return left + right, {k: left_stats.get(k, 0) + right_stats.get(k, 0) for k in set(left_stats) | set(right_stats)}
    items = raw.get("items", []) if isinstance(raw, dict) else []
    window_norm = normalise(window)
    kept: list[dict[str, Any]] = []
    stats = Counter(proposed=len(items) if isinstance(items, list) else 0)
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            stats["malformed"] += 1
            continue
        quotes = valid_quotes(item.get("quotes"), window_norm)
        if not quotes:
            stats["no_valid_quote"] += 1
            continue
        if not is_substantive(rubric, item):
            stats["empty"] += 1
            continue
        stats["kept"] += 1
        stats["quotes_offered"] += len(item.get("quotes") or [])
        stats["quotes_valid"] += len(quotes)
        kept.append({**{k: v for k, v in item.items() if k != "quotes"}, "quotes": quotes, "part": part})
    return kept, dict(stats)


def extract_paper(rubric: str, paper_id: str) -> None:
    meta = metadata()[paper_id]
    text = strip_back_matter((TEXT_DIR / f"{paper_id}.txt").read_text())
    parts = windows(text)
    items: list[dict[str, Any]] = []
    stats: Counter[str] = Counter()
    for index, window in enumerate(parts, 1):
        found, window_stats = extract_window(rubric, paper_id, str(meta.get("title", "")), window,
                                             f"{index}/{len(parts)}")
        items += found
        stats.update(window_stats)
    records = []
    for index, item in enumerate(items):
        text_value = render(rubric, item)
        digest = hashlib.sha1(text_value.encode("utf-8")).hexdigest()[:10]
        records.append({"record_id": f"{paper_id}::rubric_{rubric}::{index:03d}::{digest}", "item": item,
                        "text": text_value})
    atomic_json(EXTRACTIONS / rubric / f"{paper_id}.json", {
        "paper_id": paper_id, "rubric": rubric, "extractor": _generator_identity(),
        "source_chars": len(text), "windows": len(parts), "stats": dict(stats), "records": records,
    })


def extract_stage(workers: int, resume: bool, rubrics: tuple[str, ...]) -> dict[str, int]:
    papers = sorted(p.stem for p in TEXT_DIR.glob("PMC*.txt"))
    jobs = [(f"{r}__{p}", (r, p)) for r in rubrics for p in papers
            if not (resume and (EXTRACTIONS / r / f"{p}.json").exists())]
    return run_jobs("extract", jobs, extract_paper, workers)


# ---------------------------------------------------------------- records per representation

def rubric_records(rubric: str) -> list[RetrievalRecord]:
    key = f"records_{rubric}"
    if key not in _cache:
        meta = metadata()
        records = []
        for path in sorted((EXTRACTIONS / rubric).glob("PMC*.json")):
            payload = _read_json(path)
            pid = payload["paper_id"]
            for rec in payload["records"]:
                records.append(RetrievalRecord(rec["record_id"], pid, meta[pid]["earliest_public_date"],
                                               f"rubric:{rubric}", rec["text"], {"rubric": rubric}))
        _cache[key] = records
    return _cache[key]


def case_pool(case: dict[str, Any], representation: str) -> tuple[set[str], list[RetrievalRecord]]:
    key = f"pool_{case['paper_id']}_{representation}"
    if key in _cache:
        return _cache[key]
    if "v2" not in _cache:
        _cache["v2"] = load_evidence(V2_DIR)
    eligible, chunks, units = build_corpus(case["paper_id"], case["publication_date"], metadata(), _cache["v2"],
                                           PAPER_MAPS)
    if representation == "text_chunks":
        pool = chunks
    elif representation == "v2_units":
        pool = units
    elif representation == "mixed":
        pool = [r for rubric in ("effects", "mechanisms", "gaps") for r in rubric_records(rubric)
                if r.paper_id in eligible]
    else:
        pool = [r for r in rubric_records(representation) if r.paper_id in eligible]
    _cache[key] = (eligible, pool)
    return _cache[key]


def record_cap(arm: str) -> int:
    return RECORD_MAX_CHARS_BY_ARM.get(arm, RECORD_MAX_CHARS)


def pack(query: str, pool: list[RetrievalRecord], cap: int = RECORD_MAX_CHARS) -> list[RetrievalRecord]:
    """Top-ranked records until the shared character budget is reached (identical budget for every arm)."""
    packed: list[RetrievalRecord] = []
    used = 0
    for record in retrieve(query, pool, limit=len(pool)):
        size = min(len(record.text), cap)
        if used + size > EVIDENCE_BUDGET_CHARS:
            continue
        packed.append(record)
        used += size
        if len(packed) >= MAX_RECORDS or used >= EVIDENCE_BUDGET_CHARS - 200:
            break
    return packed


# ---------------------------------------------------------------- stage: generate

def run_id(paper_id: str, level: str, arm: str, sample: int) -> str:
    return f"{paper_id}__{level}__{arm}__s{sample}"


def leakage_audit(records: list[RetrievalRecord], case: dict[str, Any]) -> dict[str, int]:
    meta = metadata()
    family = str(meta[case["paper_id"]].get("work_family_id") or "")
    return {
        "temporal_violations": sum(r.publication_date >= case["publication_date"] for r in records),
        "test_paper_leaks": sum(r.paper_id == case["paper_id"] for r in records),
        "family_leaks": sum(bool(family) and str(meta.get(r.paper_id, {}).get("work_family_id") or "") == family
                            for r in records),
    }


def generate_one(case: dict[str, Any], level: str, arm: str, sample: int) -> None:
    query = case["queries"][level]["text"]
    cutoff = case["publication_date"]
    started = time.time()
    status, error, generation, packed = "ok", None, None, []
    try:
        if arm == "closed_book":
            generation, _ = run_closed_book(query, cutoff)
        else:
            _, pool = case_pool(case, arm)
            packed = pack(query, pool, record_cap(arm))
            generation = generate_with_citation_repair(
                {"query": query, "knowledge_cutoff": cutoff,
                 "eligible_evidence": compact_evidence_payload(packed, max_text_chars=record_cap(arm))},
                {r.record_id for r in packed})
    except Exception as caught:  # noqa: BLE001 - failed runs are recorded, never dropped
        status, error = "failed", f"{type(caught).__name__}: {caught}"
    lookup = {r.record_id: r for r in packed}
    cited = sorted(set((generation or {}).get("supporting_evidence_ids", [])
                       + (generation or {}).get("conflicting_evidence_ids", [])))
    audit = leakage_audit(packed, case)
    audit["invalid_citations"] = len(set(cited) - set(lookup))
    atomic_json(OUT / "runs" / f"{run_id(case['paper_id'], level, arm, sample)}.json", {
        "run_id": run_id(case["paper_id"], level, arm, sample), "paper_id": case["paper_id"], "query_level": level,
        "arm": arm, "sample": sample, "query": query, "publication_date": cutoff, "generator": _generator_identity(),
        "status": status, "error": error, "generation": generation,
        "packed_ids": [r.record_id for r in packed],
        "packed_chars": sum(min(len(r.text), record_cap(arm)) for r in packed),
        "packed_papers": len({r.paper_id for r in packed}),
        "cited_ids": cited,
        "cited_evidence": [{"record_id": rid, "paper_id": lookup[rid].paper_id,
                            "publication_date": lookup[rid].publication_date, "kind": lookup[rid].kind,
                            "text": lookup[rid].text[:CITED_TEXT_CHARS]} for rid in cited if rid in lookup],
        "audit": audit, "elapsed_seconds": round(time.time() - started, 2),
    })


def generate_stage(workers: int, resume: bool, arms: tuple[str, ...]) -> dict[str, int]:
    jobs = []
    for case in cases().values():
        for level in QUERY_LEVELS:
            for arm in arms:
                for sample in SAMPLES:
                    path = OUT / "runs" / f"{run_id(case['paper_id'], level, arm, sample)}.json"
                    if resume and path.exists() and _read_json(path)["status"] == "ok":
                        continue
                    jobs.append((path.stem, (case, level, arm, sample)))
    return run_jobs("generate", jobs, generate_one, workers)


def load_runs() -> dict[str, dict[str, Any]]:
    return {p.stem: _read_json(p) for p in sorted((OUT / "runs").glob("PMC*.json"))}


# ---------------------------------------------------------------- stages: judge, cross-judge, audit, ceiling

def judge_stage(workers: int, resume: bool) -> dict[str, int]:
    out = OUT / "judgments" / "gpt56"
    jobs = [(rid, (run,)) for rid, run in load_runs().items()
            if run["status"] == "ok" and not (resume and (out / f"{rid}.json").exists())]

    def job(run: dict[str, Any]) -> None:
        judgment = judge_absolute(run, cases()[run["paper_id"]])
        atomic_json(out / f"{run['run_id']}.json", judgment)

    return run_jobs("judge", jobs, job, workers)


def cross_judge_stage(workers: int, resume: bool) -> dict[str, int]:
    out = OUT / "judgments" / "deepseek"
    jobs = [(rid, (run,)) for rid, run in load_runs().items()
            if run["status"] == "ok" and not (resume and (out / f"{rid}.json").exists())]

    def job(run: dict[str, Any]) -> None:
        generation, evidence = _blind_candidate(run)
        payload = {"query": run["query"], "hidden_target": cases()[run["paper_id"]]["hidden_target"],
                   "generated_hypothesis": generation, "cited_evidence": evidence}
        raw = lc.trapi_chat_json(CROSS_JUDGE["deployment"], _SCORE_SYSTEM, json.dumps(payload, ensure_ascii=False),
                                 max_tokens=8000, token_field=CROSS_JUDGE["token_field"],
                                 temperature=CROSS_JUDGE["temperature"], retries=6)
        score = _validate_score(raw)
        atomic_json(out / f"{run['run_id']}.json", {"run_id": run["run_id"], "judge": f"trapi:{CROSS_JUDGE['deployment']}",
                                                    "scores": score["scores"],
                                                    "classification": score.get("classification", "")})

    return run_jobs("cross_judge", jobs, job, workers)


def audit_stage(workers: int, resume: bool) -> dict[str, int]:
    out = OUT / "audit"
    jobs = [(rid, (run,)) for rid, run in load_runs().items()
            if run["status"] == "ok" and not (resume and (out / f"{rid}.json").exists())]

    def job(run: dict[str, Any]) -> None:
        payload = {"query": run["query"],
                   "hypothesis": {k: run["generation"].get(k) for k in HYPOTHESIS_FIELDS if k in run["generation"]},
                   "cited_evidence": [{"record_id": c["record_id"], "text": c["text"]} for c in run["cited_evidence"]]}
        assert_target_free(payload)
        raw = lc.judge_chat_json(AUDIT_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=16000)
        atomic_json(out / f"{run['run_id']}.json", {"run_id": run["run_id"], "auditor": lc.judge_info(),
                                                    **_validated_audit(raw)})

    return run_jobs("audit", jobs, job, workers)


def ceiling_stage(workers: int, resume: bool) -> dict[str, int]:
    """Diagnostic: does each representation of the eligible papers still carry what anticipates the target?"""
    out = OUT / "ceiling"
    jobs = []
    for case in cases().values():
        for rep in REPRESENTATIONS:
            if not (resume and (out / rep / f"{case['paper_id']}.json").exists()):
                jobs.append((f"{rep}__{case['paper_id']}", (case, rep)))

    def job(case: dict[str, Any], rep: str) -> None:
        _, pool = case_pool(case, rep)
        top = retrieve(target_text(case["hidden_target"]), pool, limit=ORACLE_K)
        if any(r.publication_date >= case["publication_date"] or r.paper_id == case["paper_id"] for r in top):
            raise ValueError("ceiling retrieval returned an ineligible record")
        labels = {f"R{i + 1}": r for i, r in enumerate(top)}
        payload = {
            "later_paper_date": case["publication_date"],
            "later_paper_result": {k: case["hidden_target"].get(k) for k in (
                "material_initial_state", "intervention", "structural_mediator", "mechanism", "predicted_outcome")},
            "earlier_records": [{"label": label, "date": r.publication_date, "text": r.text[:ORACLE_TEXT_CHARS]}
                                for label, r in labels.items()],
        }
        raw = lc.judge_chat_json(CEILING_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=12000)
        raw = raw if isinstance(raw, dict) else {}
        ratings = {}
        for item in raw.get("records", []) if isinstance(raw.get("records"), list) else []:
            if isinstance(item, dict) and str(item.get("label")) in labels:
                ratings[labels[str(item["label"])].record_id] = {
                    "intervention_support": _int02(item.get("intervention_support")),
                    "mechanism_support": _int02(item.get("mechanism_support"))}
        atomic_json(out / rep / f"{case['paper_id']}.json", {
            "paper_id": case["paper_id"], "representation": rep, "pool_size": len(pool), "coder": lc.judge_info(),
            "records": [{"record_id": r.record_id, **ratings.get(r.record_id, {"intervention_support": 0,
                                                                                "mechanism_support": 0})} for r in top],
            "reconstructibility": _int02(raw.get("reconstructibility")), "reason": str(raw.get("reason", ""))[:1200]})

    return run_jobs("ceiling", jobs, job, workers)


def _int02(value: Any) -> int:
    try:
        return max(0, min(2, int(value)))
    except (TypeError, ValueError):
        return 0


# ---------------------------------------------------------------- report

def mean(values: list[Any]) -> float:
    values = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return statistics.fmean(values) if values else float("nan")


def r3(value: Any) -> Any:
    if isinstance(value, float):
        return None if math.isnan(value) else round(value, 3)
    return value


def recon(scores: dict[str, int]) -> float:
    return statistics.fmean(scores[d] for d in PRIMARY_DIMENSIONS)


def unit_scores(judgments: dict[str, dict[str, Any]], runs: dict[str, dict[str, Any]], arm: str
                ) -> dict[tuple[str, str], float]:
    """Unit score = mean over the available samples of that unit."""
    per_unit: dict[tuple[str, str], list[float]] = defaultdict(list)
    for rid, judgment in judgments.items():
        run = runs.get(rid)
        if run and run["arm"] == arm:
            per_unit[(run["paper_id"], run["query_level"])].append(recon(judgment["scores"]))
    return {key: statistics.fmean(values) for key, values in per_unit.items()}


def paired(a: dict[tuple[str, str], float], b: dict[tuple[str, str], float], name_a: str, name_b: str
           ) -> dict[str, Any]:
    common = sorted(set(a) & set(b))
    per_paper: dict[str, list[float]] = defaultdict(list)
    for key in common:
        per_paper[key[0]].append(a[key] - b[key])
    if not per_paper:
        return {"a": name_a, "b": name_b, "units": 0}
    point, low, high = cluster_bootstrap(per_paper)
    p_value, positive, negative = exact_sign_test([statistics.fmean(v) for v in per_paper.values()])
    return {"a": name_a, "b": name_b, "units": len(common), "papers": len(per_paper),
            "mean_difference": round(point, 3), "ci95": [round(low, 3), round(high, 3)],
            "papers_a_higher": positive, "papers_b_higher": negative, "sign_test_p": round(p_value, 4)}


def report() -> dict[str, Any]:
    results = OUT / "results"
    results.mkdir(parents=True, exist_ok=True)
    runs = load_runs()
    gpt = {p.stem: _read_json(p) for p in sorted((OUT / "judgments" / "gpt56").glob("*.json"))}
    deep = {p.stem: _read_json(p) for p in sorted((OUT / "judgments" / "deepseek").glob("*.json"))}
    audits = {p.stem: _read_json(p) for p in sorted((OUT / "audit").glob("*.json"))}
    ceilings = {rep: {p.stem: _read_json(p) for p in sorted((OUT / "ceiling" / rep).glob("PMC*.json"))}
                for rep in REPRESENTATIONS}
    all_cases = cases()

    # extraction
    extraction = {}
    for rubric in RUBRICS:
        files = [_read_json(p) for p in sorted((EXTRACTIONS / rubric).glob("PMC*.json"))]
        stats: Counter[str] = Counter()
        for f in files:
            stats.update(f["stats"])
        records = [r for f in files for r in f["records"]]
        extraction[rubric] = {
            "papers": len(files), "windows": sum(f["windows"] for f in files), "records": len(records),
            "records_per_paper": r3(len(records) / max(1, len(files))),
            "proposed_items": stats["proposed"], "kept_rate": r3(stats["kept"] / max(1, stats["proposed"])),
            "dropped_no_valid_quote": stats["no_valid_quote"], "dropped_empty": stats["empty"],
            "dropped_malformed": stats["malformed"],
            "valid_quotes_per_kept_item": r3(stats["quotes_valid"] / max(1, stats["kept"])),
            "quote_validity_of_kept_items": r3(stats["quotes_valid"] / max(1, stats["quotes_offered"])),
            "mean_record_chars": r3(mean([len(r["text"]) for r in records])),
            "compression_vs_source": r3(sum(len(r["text"]) for r in records) / max(1, sum(f["source_chars"] for f in files))),
        }

    # ceilings
    ceiling = {}
    supportive: dict[str, dict[str, set[str]]] = {}
    for rep, per_case in ceilings.items():
        supportive[rep] = {pid: {r["record_id"] for r in c["records"]
                                 if r["intervention_support"] >= 1 or r["mechanism_support"] >= 1}
                           for pid, c in per_case.items()}
        strong = [sum(1 for r in c["records"] if r["intervention_support"] == 2 or r["mechanism_support"] == 2)
                  for c in per_case.values()]
        ceiling[rep] = {
            "cases": len(per_case),
            "reconstructibility_mean": r3(mean([c["reconstructibility"] for c in per_case.values()])),
            "supportive_in_top20": r3(mean([len(s) for s in supportive[rep].values()])),
            "strongly_supportive_in_top20": r3(mean(strong)),
            "mean_pool_size": r3(mean([c["pool_size"] for c in per_case.values()])),
        }

    by_arm: dict[str, Any] = {}
    units_gpt: dict[str, dict[tuple[str, str], float]] = {}
    units_deep: dict[str, dict[tuple[str, str], float]] = {}
    for arm in ARMS:
        arm_runs = {rid: r for rid, r in runs.items() if r["arm"] == arm}
        ok = [r for r in arm_runs.values() if r["status"] == "ok"]
        judged = [gpt[rid] for rid in arm_runs if rid in gpt]
        units_gpt[arm] = unit_scores(gpt, runs, arm)
        units_deep[arm] = unit_scores(deep, runs, arm)
        per_sample = {s: r3(mean([recon(gpt[rid]["scores"]) for rid, r in arm_runs.items() if rid in gpt
                                  and r["sample"] == s])) for s in SAMPLES}
        sample_pairs = []
        for case in all_cases.values():
            for level in QUERY_LEVELS:
                ids = [run_id(case["paper_id"], level, arm, s) for s in SAMPLES]
                if all(i in gpt for i in ids):
                    sample_pairs.append(abs(recon(gpt[ids[0]]["scores"]) - recon(gpt[ids[1]]["scores"])))
        classes = Counter(gpt[rid].get("classification", "") for rid in arm_runs if rid in gpt)
        arm_audits = [audits[rid] for rid in arm_runs if rid in audits]
        claim_rows = []
        for a in arm_audits:
            needing = [c for c in a["claims"] if c["needs_support"]]
            supported = [c for c in needing if c["support"] in ("entailed", "partial")]
            claim_rows.append({
                "entailed": sum(c["support"] == "entailed" for c in needing) / len(needing) if needing else None,
                "supported": len(supported) / len(needing) if needing else None,
                "cross": sum(c["same_system"] == "no" for c in supported) / len(supported) if supported else None})
        support_in_context = []
        for r in ok:
            sup = supportive.get(arm, {}).get(r["paper_id"])
            if sup is not None and r["packed_ids"]:
                support_in_context.append(len(set(r["packed_ids"]) & sup))
        by_arm[arm] = {
            "runs": len(arm_runs), "failed": len(arm_runs) - len(ok), "judged": len(judged),
            "reconstruction_gpt56": r3(mean(list(units_gpt[arm].values()))),
            "reconstruction_gpt56_by_sample": per_sample,
            "reconstruction_deepseek": r3(mean(list(units_deep[arm].values()))),
            "overall_gpt56": r3(mean([statistics.fmean(j["scores"][d] for d in ALL_DIMENSIONS) for j in judged])),
            "by_level": {lvl: r3(mean([v for k, v in units_gpt[arm].items() if k[1] == lvl])) for lvl in QUERY_LEVELS},
            "dimensions": {d: r3(mean([j["scores"][d] for j in judged])) for d in ALL_DIMENSIONS},
            "hard_failure_rate": r3(mean([1.0 if v <= 0.5 else 0.0 for v in units_gpt[arm].values()])),
            "classifications": dict(classes),
            "sample_to_sample_abs_diff": r3(mean(sample_pairs)),
            "packed_records": r3(mean([len(r["packed_ids"]) for r in ok])) if arm != "closed_book" else 0,
            "packed_chars": r3(mean([r["packed_chars"] for r in ok])) if arm != "closed_book" else 0,
            "packed_papers": r3(mean([r["packed_papers"] for r in ok])) if arm != "closed_book" else 0,
            "supportive_records_in_context": r3(mean(support_in_context)) if support_in_context else None,
            "citations_per_hypothesis": r3(mean([len(r["cited_ids"]) for r in ok])),
            "claim_entailed_rate": r3(mean([c["entailed"] for c in claim_rows])),
            "claim_supported_rate": r3(mean([c["supported"] for c in claim_rows])),
            "cross_system_support_rate": r3(mean([c["cross"] for c in claim_rows])),
            "mechanism_transferred_without_justification": r3(mean(
                [1.0 if a["mechanism_source"] == "transferred_without_justification" else 0.0 for a in arm_audits])),
            "complete_chain_rate": r3(mean([1.0 if all(v == 2 for v in a["chain"].values()) else 0.0 for a in arm_audits])),
            "contradictions_per_hypothesis": r3(mean([len(a["contradictions"]) for a in arm_audits])),
            "falsifiability": r3(mean([mean([1.0 if v else 0.0 for v in a["falsifiability"].values()]) for a in arm_audits])),
            "specificity": r3(mean([mean([1.0 if v else 0.0 for v in a["specificity"].values()]) for a in arm_audits])),
            "hedges_per_hypothesis": r3(mean([len(HEDGE.findall(f"{r['generation'].get('hypothesis', '')} "
                                                                f"{r['generation'].get('predicted_outcome', '')}"))
                                              for r in ok])),
        }

    primary_arms = [a for a in ARMS if a not in ("closed_book", PRIMARY_BASELINE, "v2_units")]
    comparisons = {"gpt56": [], "deepseek": []}
    for judge_name, units in (("gpt56", units_gpt), ("deepseek", units_deep)):
        primary = [paired(units[a], units[PRIMARY_BASELINE], a, PRIMARY_BASELINE) for a in primary_arms]
        for item, adj in zip(primary, holm_adjust([c.get("sign_test_p", 1.0) for c in primary])):
            item["holm_p"] = round(adj, 4)
            item["role"] = "primary"
        secondary = [paired(units[a], units[PRIMARY_BASELINE], a, PRIMARY_BASELINE) for a in ("v2_units", "closed_book")]
        for item in secondary:
            item["role"] = "secondary"
        best = max(ARMS, key=lambda a: mean(list(units[a].values())))
        others = [paired(units[best], units[a], best, a) for a in ARMS if a != best]
        for item in others:
            item["role"] = "best_vs_other"
        comparisons[judge_name] = primary + secondary + others

    gpt_means = [mean(list(units_gpt[a].values())) for a in ARMS]
    deep_means = [mean(list(units_deep[a].values())) for a in ARMS]
    rank_gpt = sorted(ARMS, key=lambda a: -mean(list(units_gpt[a].values())))
    rank_deep = sorted(ARMS, key=lambda a: -mean(list(units_deep[a].values())))
    expected = len(all_cases) * len(QUERY_LEVELS) * len(ARMS) * len(SAMPLES)
    integrity = {
        "expected_runs": expected, "runs": len(runs), "ok": sum(r["status"] == "ok" for r in runs.values()),
        "judged_gpt56": len(gpt), "judged_deepseek": len(deep), "audited": len(audits),
        "ceiling_files": sum(len(v) for v in ceilings.values()),
        "temporal_violations": sum(r["audit"]["temporal_violations"] for r in runs.values()),
        "test_paper_leaks": sum(r["audit"]["test_paper_leaks"] for r in runs.values()),
        "family_leaks": sum(r["audit"]["family_leaks"] for r in runs.values()),
        "invalid_citations": sum(r["audit"]["invalid_citations"] for r in runs.values()),
        "stage_errors": {p.name: len(list(p.glob("*.json"))) for p in sorted((OUT / "errors").glob("*")) if p.is_dir()},
        "generators": sorted({r["generator"] for r in runs.values()}),
    }
    integrity["verified"] = bool(
        integrity["runs"] == expected and integrity["ok"] == expected and integrity["judged_gpt56"] == expected
        and integrity["judged_deepseek"] == expected and integrity["temporal_violations"] == 0
        and integrity["test_paper_leaks"] == 0 and integrity["family_leaks"] == 0
        and integrity["invalid_citations"] == 0 and len(integrity["generators"]) == 1)
    analysis = {
        "config": {"evidence_budget_chars": EVIDENCE_BUDGET_CHARS, "record_max_chars": RECORD_MAX_CHARS,
                   "record_max_chars_by_arm": RECORD_MAX_CHARS_BY_ARM,
                   "max_records": MAX_RECORDS, "samples": list(SAMPLES), "window_chars": WINDOW_CHARS,
                   "bootstrap": {"resamples": BOOTSTRAP_RESAMPLES, "seed": BOOTSTRAP_SEED}},
        "extraction": extraction, "ceiling": ceiling, "by_arm": by_arm, "comparisons": comparisons,
        "ranking": {"gpt56": rank_gpt, "deepseek": rank_deep,
                    "kendall_tau": r3(kendall_tau(gpt_means, deep_means))},
        "integrity": integrity,
    }
    atomic_json(results / "analysis.json", analysis)
    (results / "tables.md").write_text(render_report(analysis))
    return analysis


def _f(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, dict):
        return ", ".join(f"{k}: {_f(v)}" for k, v in value.items()) or "n/a"
    if isinstance(value, list):
        return ", ".join(_f(v) for v in value)
    return str(value)


def _grid(title: str, rows: dict[str, dict[str, Any]], cols: list[str], metrics: list[str]) -> list[str]:
    out = [f"## {title}", "", "| Metric | " + " | ".join(cols) + " |", "|---|" + "---:|" * len(cols)]
    for m in metrics:
        out.append(f"| {m} | " + " | ".join(_f(rows.get(c, {}).get(m)) for c in cols) + " |")
    return out + [""]


def render_report(a: dict[str, Any]) -> str:
    lines = ["# Extraction-rubric experiment", "", f"Integrity: {_f(a['integrity'])}", ""]
    lines += _grid("Extraction", a["extraction"], list(RUBRICS), list(next(iter(a["extraction"].values()))))
    lines += _grid("Evidence ceiling per representation", a["ceiling"], list(REPRESENTATIONS),
                   list(next(iter(a["ceiling"].values()))))
    score_metrics = ["reconstruction_gpt56", "reconstruction_gpt56_by_sample", "reconstruction_deepseek",
                     "overall_gpt56", "hard_failure_rate", "sample_to_sample_abs_diff", "classifications", "failed"]
    lines += _grid("Scores", a["by_arm"], list(ARMS), score_metrics)
    lines += ["## Reconstruction by query level (GPT-5.6)", "", "| Level | " + " | ".join(ARMS) + " |",
              "|---|" + "---:|" * len(ARMS)]
    for lvl in QUERY_LEVELS:
        lines.append(f"| {lvl} | " + " | ".join(_f(a["by_arm"][arm]["by_level"][lvl]) for arm in ARMS) + " |")
    lines += ["", "## Judge dimensions (GPT-5.6, mean over runs)", "", "| Dimension | " + " | ".join(ARMS) + " |",
              "|---|" + "---:|" * len(ARMS)]
    for d in ALL_DIMENSIONS:
        lines.append(f"| {d} | " + " | ".join(_f(a["by_arm"][arm]["dimensions"][d]) for arm in ARMS) + " |")
    lines += [""]
    why = ["packed_records", "packed_chars", "packed_papers", "supportive_records_in_context",
           "citations_per_hypothesis", "claim_entailed_rate", "claim_supported_rate", "cross_system_support_rate",
           "mechanism_transferred_without_justification", "complete_chain_rate", "contradictions_per_hypothesis",
           "falsifiability", "specificity", "hedges_per_hypothesis"]
    lines += _grid("Context and process (why)", a["by_arm"], list(ARMS), why)
    for judge_name, items in a["comparisons"].items():
        lines += [f"## Paired comparisons ({judge_name}, unit = mean of 2 samples, papers bootstrap)", "",
                  "| A | B | Role | Units | Mean diff | 95% CI | Papers A higher / B higher | Sign p | Holm p |",
                  "|---|---|---|---:|---:|---|---:|---:|---:|"]
        for c in items:
            if not c.get("units"):
                continue
            lines.append(f"| {c['a']} | {c['b']} | {c['role']} | {c['units']} | {c['mean_difference']:+.3f} | "
                         f"[{c['ci95'][0]:+.3f}, {c['ci95'][1]:+.3f}] | {c['papers_a_higher']} / {c['papers_b_higher']} | "
                         f"{c['sign_test_p']:.3f} | {_f(c.get('holm_p'))} |")
        lines += [""]
    lines += [f"Ranking GPT-5.6: {', '.join(a['ranking']['gpt56'])}.",
              f"Ranking DeepSeek-V4-Pro: {', '.join(a['ranking']['deepseek'])}.",
              f"Kendall tau between the two rankings: {_f(a['ranking']['kendall_tau'])}."]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("extract", "generate", "judge", "cross-judge", "audit", "ceiling"):
        p = sub.add_parser(name)
        p.add_argument("--workers", type=int, default=4)
        p.add_argument("--resume", action="store_true")
        if name == "extract":
            p.add_argument("--rubric", action="append", choices=RUBRICS)
        if name == "generate":
            p.add_argument("--arm", action="append", choices=ARMS)
    sub.add_parser("report")
    args = parser.parse_args()
    if args.command == "extract":
        result: Any = extract_stage(args.workers, args.resume, tuple(args.rubric or RUBRICS))
    elif args.command == "generate":
        result = generate_stage(args.workers, args.resume, tuple(args.arm or ARMS))
    elif args.command == "judge":
        result = judge_stage(args.workers, args.resume)
    elif args.command == "cross-judge":
        result = cross_judge_stage(args.workers, args.resume)
    elif args.command == "audit":
        result = audit_stage(args.workers, args.resume)
    elif args.command == "ceiling":
        result = ceiling_stage(args.workers, args.resume)
    else:
        result = report()["integrity"]
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
