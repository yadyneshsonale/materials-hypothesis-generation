"""Fresh held-out test set (test2), built by the rule pre-registered in loop.md section 10.1 (2026-10-25 04:20).

Stages (each resumable; console output is limited to IDs, counts and gate statistics so that the method designer
does not read titles, queries or targets before the final runs):
  search   Europe PMC search with the corpus query, restricted to the date window (extended back by month if needed).
  screen   Walk the ranking: not in the corpus or a near-duplicate of a corpus title; research article with
           methods/results sections (the corpus validator); open-access JATS XML; topic rule (GPT-5.6 on title and
           abstract); redacted Introduction >= 1,000 characters. Stop at 12 eligible papers.
  target   Hidden target (experiment-3 schema) extracted by GPT-5.6 from the abstract and every section except the
           Introduction. Never shown to a query-facing model.
  queries  v3 writer, checker and lexical gate on the redacted Introduction (query_builder_v3), then the v3.1 gap
           classifier and gap templates (query_builder_v3_1). Failing levels are flagged and kept.
Outputs: benchmark_test2/{search.json, screening.json, papers/ (raw XML, not committed), targets/, build_log/,
cases/, metadata.json}.
"""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

import requests

import llm_client as lc
import query_builder_v3 as v3
import query_builder_v3_1 as v31
from hypothesis_evidence_v2 import atomic_json
from import_jats_corpus import validate_primary_research
from temporal_eval_v3 import EXPERIMENT_DIR, QUERY_LEVELS
from temporal_hypothesis_benchmark import _read_json

OUT = EXPERIMENT_DIR / "benchmark_test2"
PAPERS = OUT / "papers"
CASES_OUT = OUT / "cases"
CORPUS_METADATA = EXPERIMENT_DIR / "temporal_v2" / "temporal_metadata.json"
EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
TOPIC = ('TITLE_ABS:("high entropy alloy" OR "high-entropy alloy") AND TITLE_ABS:("high temperature" OR '
         '"high-temperature" OR "elevated temperature" OR refractory OR creep OR oxidation OR "thermal stability" OR '
         '"hot corrosion" OR "temperature-dependent" OR superalloy OR "extreme temperature" OR "phase stability") '
         'AND OPEN_ACCESS:Y AND HAS_FT:Y')
WINDOW = ("2026-02-17", "2026-10-15")
FLOOR = "2024-02-01"
EXTEND = True
SPLIT = "test2"
RULE = "loop.md section 10.1"
EXCLUDE_SETS: tuple[str, ...] = ()
# Held-out sets built by this procedure. test2: loop.md 10.1 (window extended back by month until 12 qualify).
# test3: loop.md 11.1 (the window before test2, ranked by citations, never extended; excludes test2 papers).
SETS: dict[str, dict[str, Any]] = {
    "test2": {"out": "benchmark_test2", "window": ("2026-02-17", "2026-10-15"), "extend": True, "split": "test2",
              "rule": "loop.md section 10.1", "exclude_sets": ()},
    "test3": {"out": "benchmark_test3", "window": ("2024-02-01", "2025-07-16"), "extend": False, "split": "test3",
              "rule": "loop.md section 11.1", "exclude_sets": ("test2",)},
    # test4: loop.md 16.1 C1. From 2024-11-01, so every candidate generator (latest cutoff 2024-09-30, plus the 31-day
    # margin) is eligible on every paper. Never extended; the first 24 that qualify, ranked by citations.
    "test4": {"out": "benchmark_test4", "window": ("2024-11-01", "2026-10-26"), "extend": False, "split": "test4",
              "rule": "loop.md section 16.1", "exclude_sets": ("test2", "test3"), "n_cases": 24},
}


def configure(name: str) -> None:
    global OUT, PAPERS, CASES_OUT, WINDOW, EXTEND, SPLIT, RULE, EXCLUDE_SETS, N_CASES
    cfg = SETS[name]
    OUT = EXPERIMENT_DIR / cfg["out"]
    PAPERS, CASES_OUT = OUT / "papers", OUT / "cases"
    WINDOW, EXTEND, SPLIT, RULE, EXCLUDE_SETS = cfg["window"], cfg["extend"], cfg["split"], cfg["rule"], \
        cfg["exclude_sets"]
    N_CASES = cfg.get("n_cases", 12)


def excluded_rows() -> list[dict[str, Any]]:
    """Corpus papers plus the papers of earlier held-out sets (title and ID), for exclusion and near-duplicates."""
    rows = [{"paper_id": c["paper_id"], "title": c.get("title", "")} for c in corpus()]
    for name in EXCLUDE_SETS:
        path = EXPERIMENT_DIR / SETS[name]["out"] / "selected.json"
        rows += [{"paper_id": p["pmcid"], "title": p.get("title", "")} for p in _read_json(path)]
    return rows


N_CASES = 12
MIN_INTRO_CHARS = 1000
NEAR_DUPLICATE = 0.8
BUILDER = "gpt-5.6-sol_2026-07-09"
TOPIC_SYSTEM = (
    "You screen papers for a materials-science corpus. Inclusion rule: the paper directly studies elevated-"
    "temperature, refractory/extreme-environment, creep, oxidation, hot-corrosion, melting, thermal/phase-stability "
    "or temperature-dependent behaviour of a high-entropy alloy (multi-principal-element alloy), and it is primary "
    "research, not a review. Use only the title and abstract. Return JSON {\"include\": true|false, \"reason\": str}."
)
TARGET_SYSTEM = (
    "You build the hidden answer key of a temporal hypothesis-reconstruction benchmark case. You receive one paper's "
    "abstract and its sections other than the Introduction. Construct the hidden structured target from the paper's "
    "own results (current-paper evidence): what the paper did and found. Preserve uncertainty rather than filling "
    "absent details. Fields: material_initial_state (the starting material and its state), intervention (the "
    "intervention or study the paper made, with its key parameters), conditions (processing, test or simulation "
    "conditions), structural_mediator (the structure or state through which the effect acts), mechanism, "
    "predicted_outcome (the outcome the paper reports, stated as a prediction relative to the baseline), baseline, "
    "boundary (where the result holds), discriminating_measurement (the measurement that tests it), actual_result "
    "(the main quantitative or qualitative result). Return JSON {\"hidden_target\": {\"material_initial_state\": str, "
    "\"intervention\": str, \"conditions\": str, \"structural_mediator\": str, \"mechanism\": str, "
    "\"predicted_outcome\": str, \"baseline\": str, \"boundary\": str, \"discriminating_measurement\": str, "
    "\"actual_result\": str}}."
)
TARGET_FIELDS = ("material_initial_state", "intervention", "conditions", "structural_mediator", "mechanism",
                 "predicted_outcome", "baseline", "boundary", "discriminating_measurement", "actual_result")


def _tokens(title: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", str(title).lower()))


def jaccard(a: str, b: str) -> float:
    x, y = _tokens(a), _tokens(b)
    return len(x & y) / len(x | y) if x | y else 0.0


def corpus() -> list[dict[str, Any]]:
    return _read_json(CORPUS_METADATA)["papers"]


def earliest_date(row: dict[str, Any]) -> tuple[str, str]:
    dates = {"online_publication_date": row.get("electronicPublicationDate"),
             "first_publication_date": row.get("firstPublicationDate"),
             "print_publication_date": (row.get("journalInfo") or {}).get("printPublicationDate")}
    dated = sorted((str(v)[:10], k) for k, v in dates.items() if v and re.match(r"\d{4}-\d{2}-\d{2}", str(v)))
    return dated[0] if dated else ("", "none")


def _month_back(date: str) -> str:
    year, month, day = (int(p) for p in date.split("-"))
    year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    return f"{year:04d}-{month:02d}-{min(day, 28):02d}"


# ---------------------------------------------------------------- search

def search(start: str, end: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cursor = "*"
    query = f"{TOPIC} AND FIRST_PDATE:[{start} TO {end}] sort_cited:y"
    while True:
        response = requests.get(f"{EUROPE_PMC}/search", params={"query": query, "format": "json",
                                                                 "resultType": "core", "pageSize": 1000,
                                                                 "cursorMark": cursor}, timeout=120)
        response.raise_for_status()
        data = response.json()
        page = data.get("resultList", {}).get("result", [])
        rows += page
        nxt = data.get("nextCursorMark")
        if not page or not nxt or nxt == cursor:
            break
        cursor = nxt
    return rows


# ---------------------------------------------------------------- screen

def fetch_xml(pmcid: str) -> bytes:
    response = requests.get(f"{EUROPE_PMC}/{pmcid}/fullTextXML", timeout=120)
    response.raise_for_status()
    return response.content


def redacted_intro_from_xml(path: Path) -> dict[str, Any]:
    original = v3.PAPERS
    try:  # reuse the exact v3 redaction on this file
        v3.PAPERS = path.parent.parent.parent
        return v3.redacted_introduction(path.parent.parent.name)
    finally:
        v3.PAPERS = original


def has_intro_section(root: ET.Element) -> bool:
    body = root.find(".//body")
    return body is not None and any(s.find("title") is not None and "introduction" in v3._text(s.find("title")).lower()
                                    for s in body.findall("sec"))


def screen_one(row: dict[str, Any], corpus_rows: list[dict[str, Any]]) -> dict[str, Any]:
    pmcid = str(row.get("pmcid") or "")
    decision: dict[str, Any] = {"pmcid": pmcid, "cited_by": row.get("citedByCount", 0)}
    if not pmcid:
        return {**decision, "eligible": False, "reason": "no PMCID"}
    if pmcid in {c["paper_id"] for c in corpus_rows}:
        return {**decision, "eligible": False, "reason": "in corpus or an earlier held-out set"}
    near = max((jaccard(row.get("title", ""), c.get("title", "")) for c in corpus_rows), default=0.0)
    if near >= NEAR_DUPLICATE:
        return {**decision, "eligible": False, "reason": f"near-duplicate of an excluded title ({near:.2f})"}
    date, source = earliest_date(row)
    decision.update({"earliest_public_date": date, "date_source": source})
    path = PAPERS / pmcid / "input" / "article.xml"
    try:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(fetch_xml(pmcid))
        root = ET.parse(path).getroot()
        screening = validate_primary_research(root, row)
    except Exception as error:  # noqa: BLE001 - the reason is recorded
        return {**decision, "eligible": False, "reason": f"primary-research or XML check: {str(error)[:200]}"}
    if not has_intro_section(root):
        return {**decision, "eligible": False, "reason": "no Introduction section"}
    intro = redacted_intro_from_xml(path)
    decision["intro_chars"] = intro["kept_chars"]
    if intro["kept_chars"] < MIN_INTRO_CHARS:
        return {**decision, "eligible": False, "reason": f"redacted Introduction {intro['kept_chars']} chars"}
    topic = lc.trapi_chat_json(BUILDER, TOPIC_SYSTEM, json.dumps({"title": row.get("title", ""),
                                                                 "abstract": row.get("abstractText", "")},
                                                                ensure_ascii=False), max_tokens=2000)
    include = bool(topic.get("include")) if isinstance(topic, dict) else False
    decision.update({"topic_include": include, "topic_reason": str(topic.get("reason", ""))[:300]
                     if isinstance(topic, dict) else "", "screening": screening})
    if not include:
        return {**decision, "eligible": False, "reason": "topic rule"}
    return {**decision, "eligible": True, "reason": "eligible"}


def screen_stage() -> dict[str, Any]:
    corpus_rows = excluded_rows()
    start, rounds, decisions, eligible = WINDOW[0], [], [], []
    seen: set[str] = set()
    while True:
        rows = search(start, WINDOW[1])
        rounds.append({"window": [start, WINDOW[1]], "results": len(rows)})
        for row in rows:
            pmcid = str(row.get("pmcid") or row.get("id"))
            if pmcid in seen:
                continue
            seen.add(pmcid)
            decision = screen_one(row, corpus_rows)
            decision["rank_window_start"] = start
            decisions.append(decision)
            if decision["eligible"]:
                eligible.append({**decision, "title": row.get("title", ""), "doi": row.get("doi", ""),
                                 "journal": (row.get("journalInfo") or {}).get("journal", {}).get("title", ""),
                                 "pub_types": (row.get("pubTypeList") or {}).get("pubType", []),
                                 "abstract": row.get("abstractText", "")})
                if len(eligible) >= N_CASES:
                    break
        if len(eligible) >= N_CASES or start <= FLOOR or not EXTEND:
            break
        start = max(_month_back(start), FLOOR)
        seen = {d["pmcid"] for d in decisions}
    summary = {"rule": RULE, "rounds": rounds, "screened": len(decisions),
               "eligible": len(eligible), "reasons": dict(Counter(d["reason"].split(":")[0].split(" (")[0]
                                                                  for d in decisions)),
               "selected": [e["pmcid"] for e in eligible]}
    atomic_json(OUT / "screening.json", {"summary": summary, "decisions": decisions})
    atomic_json(OUT / "selected.json", eligible)
    return summary


# ---------------------------------------------------------------- hidden targets

def non_intro_text(path: Path, limit: int = 45000) -> str:
    root = ET.parse(path).getroot()
    parts = []
    abstract = root.find(".//abstract")
    if abstract is not None:
        parts.append("ABSTRACT\n" + v3._text(abstract))
    body = root.find(".//body")
    for sec in body.findall("sec") if body is not None else []:
        title = v3._text(sec.find("title")) if sec.find("title") is not None else ""
        if "introduction" in title.lower():
            continue
        parts.append(f"{title.upper()}\n" + v3._strip_citations(v3._text(sec)))
    return "\n\n".join(parts)[:limit]


def target_stage() -> dict[str, int]:
    done = 0
    for paper in _read_json(OUT / "selected.json"):
        dest = OUT / "targets" / f"{paper['pmcid']}.json"
        if dest.exists():
            done += 1
            continue
        text = non_intro_text(PAPERS / paper["pmcid"] / "input" / "article.xml")
        raw = lc.trapi_chat_json(BUILDER, TARGET_SYSTEM, json.dumps({"paper_without_introduction": text},
                                                                    ensure_ascii=False), max_tokens=8000)
        target = raw.get("hidden_target") if isinstance(raw, dict) else None
        if not isinstance(target, dict) or any(not str(target.get(f, "")).strip() for f in ("intervention",
                                                                                              "mechanism")):
            raise RuntimeError(f"{paper['pmcid']}: target extraction failed")
        atomic_json(dest, {"paper_id": paper["pmcid"], "extractor": f"trapi:{BUILDER}",
                           "source": "abstract and non-Introduction sections",
                           "hidden_target": {f: str(target.get(f, "")) for f in TARGET_FIELDS}})
        done += 1
    return {"targets": done}


# ---------------------------------------------------------------- queries (v3 then v3.1)

def _write_queries(system: str, intro: str, target: dict[str, Any]) -> tuple[dict[str, str], dict[str, Any], list]:
    payload: dict[str, Any] = {"introduction_without_own_contribution": intro}
    history: list[dict[str, Any]] = []
    queries: dict[str, str] = {}
    results: dict[str, dict[str, Any]] = {}
    for round_ in range(1, v3.MAX_ROUNDS + 1):
        raw = lc.trapi_chat_json(v3.WRITER, system, json.dumps(payload, ensure_ascii=False), max_tokens=6000)
        for level in QUERY_LEVELS:
            if level not in queries or not results.get(level, {}).get("passed"):
                text = str(raw.get(level, "")).strip() if isinstance(raw, dict) else ""
                if text:
                    queries[level] = text
        results = {level: v3.check(queries[level], target) for level in QUERY_LEVELS if level in queries}
        history.append({"round": round_, "queries": dict(queries), "checks": results})
        if len(results) == len(QUERY_LEVELS) and all(r["passed"] for r in results.values()):
            break
        payload = {"introduction_without_own_contribution": intro, "current_questions": queries,
                   "revision_requests": v3.revision_requests(results)}
    return queries, results, history


def classify_gap(intro: str) -> dict[str, Any]:
    raw = lc.trapi_chat_json(v3.WRITER, v31.GAP_SYSTEM, json.dumps({"introduction": intro}, ensure_ascii=False),
                             max_tokens=3000)
    gap = str(raw.get("gap_type", "")).strip().lower() if isinstance(raw, dict) else ""
    return {"gap_type": gap if gap in v31.GAP_TYPES else "design",
            "evidence": str(raw.get("evidence", ""))[:400] if isinstance(raw, dict) else "",
            "reason": str(raw.get("reason", ""))[:600] if isinstance(raw, dict) else "", "classifier": v3.WRITER}


def gap_system(gap_type: str) -> str:
    system = v3.WRITER_SYSTEM.replace(
        "- The question must stay general about the solution: ask what intervention could solve the problem, never "
        "hint at its direction or class (for example do not say 'via alloying', 'by heat treatment', 'by introducing "
        "a second phase').\n"
        "- Each question asks for one hypothesis with: the proposed intervention, the mechanism, the predicted outcome "
        "relative to a baseline, its boundary conditions, supporting prior evidence and a falsification experiment.\n",
        "- " + v31.GAP_TEMPLATES[gap_type] + "\n")
    if system == v3.WRITER_SYSTEM:
        raise RuntimeError("v3 writer prompt changed; template substitution failed")
    return system


def build_case(paper: dict[str, Any]) -> dict[str, Any]:
    pid = paper["pmcid"]
    target = _read_json(OUT / "targets" / f"{pid}.json")["hidden_target"]
    source = redacted_intro_from_xml(PAPERS / pid / "input" / "article.xml")
    queries, results, history = _write_queries(v3.WRITER_SYSTEM, source["text"], target)
    gap = classify_gap(source["text"])
    change = "none (design gap: v3 queries kept)"
    v3_queries = dict(queries)
    if gap["gap_type"] != "design":
        queries, results, history2 = _write_queries(gap_system(gap["gap_type"]), source["text"], target)
        history += [{**h, "pass": "v3.1"} for h in history2]
        change = f"queries rewritten for a {gap['gap_type']} gap"
    case = {
        "schema_version": f"benchmark-{SPLIT}-1.0", "paper_id": pid, "publication_date": paper["earliest_public_date"],
        "split": SPLIT, "benchmark_claim": "retrospective_temporal_reconstruction",
        "query_source": "introduction_without_own_contribution", "query_writer": f"trapi:{v3.WRITER}",
        "leakage_checker": f"trapi:{v3.CHECKER}", "gap": gap, "v3_1_change": change,
        "queries": {level: {"text": queries.get(level, ""), "passed_gate": results.get(level, {}).get("passed", False),
                            "overlap": results.get(level, {}).get("overlap"),
                            "raw_overlap_exp19_metric": round(v3.raw_overlap(queries.get(level, ""), target), 3),
                            "source_role_refs": []} for level in QUERY_LEVELS},
        "hidden_target": target, "hidden_target_source": f"extracted by trapi:{BUILDER} from the abstract and "
                                                           f"non-Introduction sections ({RULE})",
        "rounds": len(history), "source": {k: v for k, v in source.items() if k != "text"},
        "v3_queries": v3_queries,
    }
    atomic_json(OUT / "build_log" / f"{pid}.json", {"paper_id": pid, "gap": gap, "source_text": source["text"],
                                                     "history": history})
    atomic_json(CASES_OUT / f"{pid}.json", case)
    return case


def queries_stage(workers: int = 6) -> list[dict[str, Any]]:
    from concurrent.futures import ThreadPoolExecutor

    def one(paper: dict[str, Any]) -> dict[str, Any]:
        path = CASES_OUT / f"{paper['pmcid']}.json"
        case = _read_json(path) if path.exists() else build_case(paper)
        return {"paper_id": case["paper_id"], "date": case["publication_date"], "gap": case["gap"]["gap_type"],
                "gate": {l: q["passed_gate"] for l, q in case["queries"].items()},
                "overlap": {l: q["overlap"] for l, q in case["queries"].items()}}

    with ThreadPoolExecutor(workers) as pool:
        return list(pool.map(one, _read_json(OUT / "selected.json")))


def metadata_stage() -> dict[str, Any]:
    """Metadata rows in the corpus format, so the harness can date and exclude the held-out cases."""
    rows = {}
    for paper in _read_json(OUT / "selected.json"):
        rows[paper["pmcid"]] = {"paper_id": paper["pmcid"], "title": paper["title"], "doi": paper["doi"],
                                "earliest_public_date": paper["earliest_public_date"],
                                "earliest_public_date_source": paper["date_source"],
                                "work_family_id": f"doi:{paper['doi']}" if paper["doi"] else paper["pmcid"],
                                "journal": paper["journal"], "cited_by": paper["cited_by"], "split": SPLIT}
    atomic_json(OUT / "metadata.json", rows)
    return {"papers": len(rows), "dates": sorted(r["earliest_public_date"] for r in rows.values())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("screen", "target", "queries", "metadata", "all"))
    parser.add_argument("--set", default="test2", choices=tuple(SETS), help="which held-out set to build")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--retries", type=int, default=6, help="TRAPI retries per call (rate limits)")
    args = parser.parse_args()
    configure(args.set)
    if args.retries != 6:  # resilience only: more retries of the same call, no change to any prompt or rule
        _call = lc.trapi_chat_json

        def _patient(*a: Any, **kw: Any) -> Any:
            kw.setdefault("retries", args.retries)
            return _call(*a, **kw)
        lc.trapi_chat_json = _patient
    if args.stage in ("screen", "all"):
        if not (OUT / "selected.json").exists():
            print(json.dumps(screen_stage(), indent=1))
    if args.stage in ("target", "all"):
        print(target_stage())
    if args.stage in ("queries", "all"):
        for row in queries_stage(args.workers):
            print(json.dumps(row))
    if args.stage in ("metadata", "all"):
        print(metadata_stage())


if __name__ == "__main__":
    main()
