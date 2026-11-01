"""Experiment 44 (loop.md 25.1): focused retrieval ("retrieval v3").

The experiment-36 corpora search an OR of single words (e.g. `ABSTRACT:density OR ABSTRACT:reduction`) inside the
high-entropy-alloy domain and rank by BM25 that includes the question template's words, so they hold many papers that
share a word with the question but not its topic. Retrieval v3 searches for the question's concepts and checks every
paper and passage for relevance before a writer sees it:

  plan      o3-mini (pre-cutoff, from the question only) writes concept groups (material system, material class,
            property or limitation, regime, approaches and mechanisms to look up), each a list of short phrases, and
            searches that combine 2-3 groups;
  search    Europe PMC: AND over the groups, OR of TITLE_ABS phrases within a group, plus websearch.filters (open
            access with full text, no preprints, before the case date); a search with too few hits drops its last
            group;
  admit     websearch.admit: two date sources, types, the case paper and its work family, held-out papers;
  screen    gpt-4o (pre-cutoff) grades each candidate's title and abstract 0-3 for relevance to the question;
  select    grade >= 2, by grade then BM25; XML parse and websearch's checks (cites the case, version overlap, length);
  expand    references co-cited by >= 2 selected papers, open access, admitted and screened the same way;
  passages  section passages of the selected papers, the best by BM25 per paper, graded 0-3 by gpt-4o; grade 3 then
            2 packed to the budget (titles and sections in the payload, as in experiment 42).

Every model call goes through a Harness (target guard and trace). Every result passes websearch's filters in code
before any model sees it, and the manifest logs every query, hit count, grade and the pack.

Stages:
  python focused_search.py build [--workers N] [--case PMC... --level L]   one manifest per question (cached)
  python focused_search.py screen_old [--workers N]   the same screener on the experiment-36 corpora (diagnostic)
  python focused_search.py stats                       relevance and size statistics of both
"""

from __future__ import annotations

import os

_E = os.path.join(os.path.dirname(os.path.abspath(__file__)), "experiments", "high_temperature_hea_qwen35b")
os.environ.setdefault("MATHG_CASES_DIR", os.path.join(_E, "benchmark_v3_1", "cases"))

import argparse  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import statistics  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
from collections import Counter  # noqa: E402
from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

import citegraph as cg  # noqa: E402
import hypo_loop as H  # noqa: E402
import stage_v2 as S2  # noqa: E402
import websearch as ws  # noqa: E402
from hypothesis_evidence_v2 import atomic_json  # noqa: E402
from temporal_hypothesis_benchmark import RetrievalRecord, _read_json  # noqa: E402

OUT = ws.OUT / "focused"
PLAN_MODEL, SCREEN_MODEL = "o3mini", "4o"
SEARCH_LIMIT = 200
SCREEN_TOP = 120
SCREEN_BATCH, PASSAGE_BATCH = 20, 20
MAX_PAPERS, MAX_EXPANSION = 30, 10
PASSAGES_PER_PAPER = 6
BUDGET = 64000  # the evidence budget of web_text_64k_b_o3mini and web64k_r2_b_o3mini
MIN_HITS = 3
KEEP_GRADE = 2
ABSTRACT_CHARS, PASSAGE_SHOWN = 1500, 1200

PLAN_SYSTEM = (
    "You plan a literature search for a materials-science research question, before anyone answers it. Use only the "
    "question and materials-science knowledge from before the knowledge cutoff. Write the concepts a researcher "
    "would search for, as groups of short search phrases (1 to 4 words each, as they would appear in titles or "
    "abstracts, with common synonyms and abbreviations):\n"
    "- \"material\": the specific material systems the question names (alloy names or compositions);\n"
    "- \"material_class\": the class of material as researchers name it (for example \"refractory high-entropy "
    "alloy\");\n"
    "- \"property\": the property, behaviour or limitation at stake;\n"
    "- \"regime\": the operating or test conditions, if the question states them;\n"
    "- \"approach_1\" ... \"approach_6\": approaches, mechanisms, phenomena or methods a researcher would look up to "
    "answer the question (compositions, processing routes, microstructures, mechanisms, characterisation or "
    "simulation methods), one per group.\n"
    "Omit a group the question gives no basis for. Each group has 1 to 6 phrases. Then write 6 to 8 searches; each "
    "is an AND of 2 or 3 group names, from specific (material AND property) to broader (material_class AND an "
    "approach). Return JSON {\"groups\": {group name: [phrases]}, \"searches\": [[group names], ...]}, where each "
    "search is a plain list of group names, for example [\"material\", \"property\"]."
)
SCREEN_SYSTEM = (
    "You screen search results for a materials-science research question. For each paper (title and abstract), "
    "grade how useful it is for answering the question:\n"
    "3 = directly on point: the same or a closely related material system AND the same property or limitation, or "
    "it reports an approach that directly addresses the question's limitation;\n"
    "2 = relevant: the same property or limitation in a related material class, the same material system with a "
    "related property, or a mechanism, approach or method the question could use;\n"
    "1 = tangential: the same broad field, but a different property and a different material system;\n"
    "0 = unrelated.\n"
    "Judge from the title and abstract only. If a search purpose is given, also count usefulness for that purpose. "
    "Return JSON {\"grades\": [{\"id\": int, \"grade\": 0-3, \"why\": \"at most 12 words\"}]} with one entry per "
    "paper."
)
PASSAGE_SYSTEM = (
    "You select evidence passages for a materials-science research question. For each passage (with its paper's "
    "title and section), grade:\n"
    "3 = reports a result, mechanism, condition or method that bears directly on the question;\n"
    "2 = useful background for the question (for example properties of the same system, or a related approach and "
    "its outcome);\n"
    "1 = generic or tangential;\n"
    "0 = irrelevant (for example sample preparation unrelated to the question).\n"
    "If a search purpose is given, also count usefulness for that purpose. Return JSON {\"grades\": [{\"id\": int, "
    "\"grade\": 0-3}]} with one entry per passage."
)
_PHRASE = re.compile(r"[^A-Za-z0-9 .\-+]")


# ---------------------------------------------------------------- the plan and the queries

def clean_phrase(text: Any) -> str:
    phrase = re.sub(r"\s+", " ", _PHRASE.sub(" ", str(text or ""))).strip(" .-+")
    words = [w for w in phrase.split() if w.upper() not in ("AND", "OR", "NOT", "TO")]
    return " ".join(words[:4]) if 1 <= len(words) else ""


def _search_names(item: Any) -> list[str]:
    """Group names of one search, from the forms models use: [names], [[names], "why"], {"groups": [names]},
    or "a AND b"."""
    if isinstance(item, dict):
        item = item.get("groups") or item.get("search") or item.get("names") or []
    if isinstance(item, str):
        item = re.split(r"\s+AND\s+|,", item)
    if isinstance(item, list) and item and isinstance(item[0], list):
        item = item[0]
    return [str(n) for n in item] if isinstance(item, list) else []


def parse_plan(raw: Any) -> dict[str, Any]:
    """Valid groups (1-6 clean, distinct phrases) and searches (AND of 2-3 existing groups, at most 8, distinct). If
    no search is usable, the first group is combined with each of the next ones."""
    raw = raw if isinstance(raw, dict) else {}
    groups: dict[str, list[str]] = {}
    for name, phrases in (raw.get("groups") or {}).items() if isinstance(raw.get("groups"), dict) else []:
        items = phrases if isinstance(phrases, list) else [phrases]
        clean = list(dict.fromkeys(p for p in (clean_phrase(x) for x in items) if p))[:6]
        key = re.sub(r"[^a-z0-9_]", "", str(name).lower())[:24]
        if key and clean:
            groups[key] = clean
    searches: list[list[str]] = []
    for item in raw.get("searches") or [] if isinstance(raw.get("searches"), list) else []:
        names = [re.sub(r"[^a-z0-9_]", "", n.lower())[:24] for n in _search_names(item)]
        names = list(dict.fromkeys(n for n in names if n in groups))
        if 2 <= len(names) <= 3 and names not in searches:
            searches.append(names)
    fallback = False
    if not searches and len(groups) >= 2:
        first, *rest = list(groups)
        searches = [[first, other] for other in rest[:6]]
        fallback = True
    return {"groups": groups, "searches": searches[:8], **({"fallback_searches": True} if fallback else {})}


def query_for(groups: dict[str, list[str]], names: list[str], cutoff: str) -> str:
    clauses = ["(" + " OR ".join(f'TITLE_ABS:"{p}"' for p in groups[n]) + ")" for n in names]
    return " AND ".join(clauses) + " AND " + ws.filters(cutoff)


def plan_terms(groups: dict[str, list[str]]) -> list[str]:
    return list(dict.fromkeys(t for phrases in groups.values() for p in phrases for t in cg.content_terms(p)))


def make_plan(h: H.Harness, system: str = PLAN_SYSTEM, model: str = PLAN_MODEL,
              extra: dict[str, Any] | None = None, role: str = "search_planner") -> dict[str, Any]:
    payload = {"question": h.query, "knowledge_cutoff": h.cutoff, **(extra or {})}
    plan = parse_plan(h.ask(role, model, system, payload, max_out=6000))
    if not plan["searches"]:
        retry = {**payload, "validation_error": "No usable search: each search must be an AND of 2 or 3 of your own "
                                                "group names, and each group must list short phrases."}
        plan = parse_plan(h.ask(f"{role}_retry", model, system, retry, max_out=6000))
    return plan


def run_searches(plan: dict[str, Any], flt: ws.CaseFilter) -> tuple[list[str], list[dict[str, Any]]]:
    """Europe PMC searches of a plan: the PMCIDs in search order and a log of every query."""
    pmcids: list[str] = []
    log: list[dict[str, Any]] = []
    for names in plan["searches"]:
        tried = names
        result = ws.search(query_for(plan["groups"], tried, flt.cutoff), SEARCH_LIMIT, core=True)
        if result["hit_count"] < MIN_HITS and len(names) == 3:
            tried = names[:2]
            result = ws.search(query_for(plan["groups"], tried, flt.cutoff), SEARCH_LIMIT, core=True)
        log.append({"groups": tried, "requested": names, "query": result["query"], "hit_count": result["hit_count"],
                    "fetched": result["fetched"], "searched_at": result["searched_at"]})
        pmcids += [r["pmcid"] for r in result["rows"] if r.get("pmcid")]
    return list(dict.fromkeys(pmcids)), log


# ---------------------------------------------------------------- grading

def _grades(raw: Any, ids: list[int]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for item in (raw.get("grades") if isinstance(raw, dict) else None) or []:
        if not isinstance(item, dict):
            continue
        try:
            n, grade = int(item.get("id")), int(item.get("grade"))
        except (TypeError, ValueError):
            continue
        if n in ids and 0 <= grade <= 3:
            out[n] = {"grade": grade, "why": str(item.get("why", ""))[:120]}
    return out


def screen(h: H.Harness, rows: list[dict[str, Any]], purpose: str = "", role: str = "screener"
           ) -> dict[str, dict[str, Any]]:
    """pmcid -> {grade, why}; title and abstract only, in a seeded random order with neutral numbers (must_obey.md
    5.2). A paper the screener did not grade gets grade 0."""
    rows = list(rows)
    h.rng.shuffle(rows)
    out: dict[str, dict[str, Any]] = {}
    for start in range(0, len(rows), SCREEN_BATCH):
        batch = rows[start:start + SCREEN_BATCH]
        items = [{"id": n + 1, "title": re.sub(r"<[^>]+>", "", str(r.get("title", ""))),
                  "abstract": str(r.get("abstractText", ""))[:ABSTRACT_CHARS]} for n, r in enumerate(batch)]
        payload: dict[str, Any] = {"question": h.query, "papers": items}
        if purpose:
            payload["search_purpose"] = purpose
        graded = _grades(h.ask(role, SCREEN_MODEL, SCREEN_SYSTEM, payload, max_out=4000), [i["id"] for i in items])
        for n, row in enumerate(batch):
            out[row["pmcid"]] = graded.get(n + 1, {"grade": 0, "why": "ungraded"})
    return out


def grade_passages(h: H.Harness, records: list[RetrievalRecord], purpose: str = "", role: str = "passage_grader"
                   ) -> dict[str, int]:
    records = list(records)
    h.rng.shuffle(records)
    out: dict[str, int] = {}
    for start in range(0, len(records), PASSAGE_BATCH):
        batch = records[start:start + PASSAGE_BATCH]
        items = [{"id": n + 1, "paper_title": re.sub(r"<[^>]+>", "", str((r.structured or {}).get("title", "")))[:150],
                  "section": str(r.kind).split(":", 1)[-1][:60], "text": " ".join(r.text.split())[:PASSAGE_SHOWN]}
                 for n, r in enumerate(batch)]
        payload: dict[str, Any] = {"question": h.query, "passages": items}
        if purpose:
            payload["search_purpose"] = purpose
        graded = _grades(h.ask(role, SCREEN_MODEL, PASSAGE_SYSTEM, payload, max_out=3000), [i["id"] for i in items])
        for n, record in enumerate(batch):
            out[record.record_id] = graded.get(n + 1, {"grade": 0})["grade"]
    return out


# ---------------------------------------------------------------- papers and passages

def _usable(flt: ws.CaseFilter, pmcid: str) -> tuple[dict[str, Any] | None, str | None]:
    parsed = ws.parsed_paper(pmcid)
    if parsed is None:
        return None, "no_xml"
    return parsed, flt.check_parsed(parsed)


def select(flt: ws.CaseFilter, rows: dict[str, dict[str, Any]], grades: dict[str, dict[str, Any]],
           order: list[str], limit: int, role: str, reasons: Counter[str]) -> list[dict[str, Any]]:
    """Papers graded >= KEEP_GRADE, by grade then the given order, that pass the parsed-paper checks."""
    rank = {p: i for i, p in enumerate(order)}
    chosen: list[dict[str, Any]] = []
    works = ws.crossref_works([r["doi"] for r in rows.values() if r.get("doi")])
    for pmcid in sorted((p for p in grades if grades[p]["grade"] >= KEEP_GRADE and p in rows),
                        key=lambda p: (-grades[p]["grade"], rank.get(p, len(rank)), p)):
        if len(chosen) >= limit:
            break
        _, reason = _usable(flt, pmcid)
        if reason:
            reasons[reason] += 1
            continue
        entry = ws.paper_entry(rows[pmcid], works.get(rows[pmcid].get("doi") or ""))
        chosen.append({**entry, "role": role, "grade": grades[pmcid]["grade"], "why": grades[pmcid]["why"]})
    return chosen


def expansion_candidates(chosen: list[dict[str, Any]], flt: ws.CaseFilter, known: set[str], reasons: Counter[str]
                         ) -> tuple[dict[str, dict[str, Any]], Counter[str]]:
    """Backward expansion (must_obey.md 4.3): open-access references co-cited by >= 2 chosen papers."""
    cocited: Counter[str] = Counter()
    chosen_dois = {c["doi"] for c in chosen if c.get("doi")}
    for paper in chosen:
        for doi in {cg.norm_doi(r.get("doi")) for r in ws.load_parsed(paper["pmcid"]).get("refs", [])} - {""}:
            cocited[doi] += 1
    frequent = [d for d, c in cocited.most_common() if c >= 2 and d not in chosen_dois]
    found = ws.oa_by_dois(frequent) if frequent else {}
    pmcids = [found[d]["pmcid"] for d in frequent if d in found and found[d]["pmcid"] not in known]
    rows = ws.admit(flt, ws.core_records(pmcids), reasons)
    count = Counter({found[d]["pmcid"]: cocited[d] for d in frequent if d in found})
    return rows, count


def paper_records(entry: dict[str, Any]) -> list[RetrievalRecord]:
    return ws.passages(entry, ws.load_parsed(entry["pmcid"]))


def rank_passages(records: list[RetrievalRecord], terms: list[str], per_paper: int) -> list[RetrievalRecord]:
    """The best passages of each paper by BM25 on the plan's terms (the question template's words never count)."""
    docs = {r.record_id: S2.clean_terms(r.text) for r in records}
    scores = S2.bm25_scores(terms, docs)
    taken: Counter[str] = Counter()
    out = []
    for record in sorted(records, key=lambda r: (-scores.get(r.record_id, 0.0), r.record_id)):
        if taken[record.paper_id] < per_paper and scores.get(record.record_id, 0.0) > 0:
            out.append(record)
            taken[record.paper_id] += 1
    return out


def pack(records: list[RetrievalRecord], grades: dict[str, int], paper_grade: dict[str, int], budget: int,
         exclude: set[str] = frozenset()) -> list[RetrievalRecord]:
    """Grade 3 then grade 2 passages, by their paper's grade and then the given order, within the budget; sizes are
    counted as sent (title and section included); the record limit scales with the budget (24 per 16,000)."""
    import loop_methods as LM
    import rubric_eval as rx
    cap = rx.record_cap("text_chunks")
    max_records = max(1, round(rx.MAX_RECORDS * budget / rx.EVIDENCE_BUDGET_CHARS))
    order = {r.record_id: i for i, r in enumerate(records)}
    eligible = [r for r in records if grades.get(r.record_id, 0) >= KEEP_GRADE and r.record_id not in exclude]
    eligible.sort(key=lambda r: (-grades[r.record_id], -paper_grade.get(r.paper_id, 0), order[r.record_id]))
    packed, used = [], 0
    for record in eligible:
        size = LM.v2_item_size(LM.v2_item(record, cap))
        if used + size > budget:
            continue
        packed.append(record)
        used += size
        if len(packed) >= max_records or used >= budget - 200:
            break
    return packed


# ---------------------------------------------------------------- the per-question build

def manifest_path(case_id: str, level: str) -> Path:
    return OUT / case_id / f"{level}.json"


_BUILD_LOCKS: dict[str, threading.Lock] = {}
_BUILD_GUARD = threading.Lock()


def build(case_id: str, level: str) -> dict[str, Any]:
    path = manifest_path(case_id, level)
    if path.exists():
        return _read_json(path)
    with _BUILD_GUARD:
        lock = _BUILD_LOCKS.setdefault(f"{case_id}:{level}", threading.Lock())
    with lock:
        if path.exists():
            return _read_json(path)
        case = H.cases()[case_id]
        h = H.Harness(case, level, 0)
        flt = ws.CaseFilter(case_id)
        reasons: Counter[str] = Counter()
        plan = make_plan(h)
        searched, searches = run_searches(plan, flt)
        # Recall channel (loop.md 25.1): the experiment-36 corpus papers enter the same screening, so that a narrow
        # search cannot lose a relevant paper the earlier corpus had.
        old = [p["pmcid"] for p in ws.corpus_papers(case_id, level)]
        pmcids = list(dict.fromkeys(searched + old))
        rows = ws.admit(flt, ws.core_records(pmcids), reasons)
        channel = {p: ("both" if p in old else "search") if p in searched else "old_corpus" for p in rows}
        terms = plan_terms(plan["groups"])
        order = ws.bm25_rank(terms, rows)
        grades = screen(h, [rows[p] for p in order[:SCREEN_TOP]])
        chosen = select(flt, rows, grades, order, MAX_PAPERS, "focused_seed", reasons)
        for paper in chosen:
            paper["channel"] = channel.get(paper["pmcid"], "")
        exp_rows, cocited = expansion_candidates(chosen, flt, set(rows), reasons)
        exp_order = sorted(exp_rows, key=lambda p: (-cocited[p], p))
        exp_grades = screen(h, [exp_rows[p] for p in exp_order[:SCREEN_TOP]], role="screener_expansion")
        expansion = select(flt, exp_rows, exp_grades, exp_order, MAX_EXPANSION, "focused_expansion", reasons)
        papers = chosen + expansion
        records = [r for p in papers for r in paper_records(p)]
        candidates = rank_passages(records, terms, PASSAGES_PER_PAPER)
        passage_grades = grade_passages(h, candidates)
        packed = pack(candidates, passage_grades, {p["pmcid"]: p["grade"] for p in papers}, BUDGET)
        manifest = {
            "case": case_id, "level": level, "cutoff": flt.cutoff, "question": h.query, "plan": plan,
            "searches": searches, "unique_hits": len(searched), "old_corpus_papers": len(old),
            "admitted": len(rows), "channels": dict(Counter(channel.values())), "screened": len(grades),
            "screen_grades": {p: grades[p] for p in order[:SCREEN_TOP]},
            "expansion_screened": len(exp_grades), "expansion_grades": exp_grades,
            "papers": papers, "passage_grades": passage_grades, "pack": [r.record_id for r in packed],
            "pack_chars": sum(len(r.text) for r in packed), "rejected": dict(reasons),
            "models": h.models, "trace": h.trace, "rules": "loop.md 25.1; must_obey.md 4.7 (amended)",
            "built_at": time.strftime("%Y-%m-%d %H:%M")}
        atomic_json(path, manifest)
        return manifest


def pack_records(case_id: str, level: str) -> list[RetrievalRecord]:
    """The packed passages of a question, in pack order."""
    manifest = build(case_id, level)
    wanted = set(manifest["pack"])
    by_id = {r.record_id: r for p in manifest["papers"] for r in paper_records(p) if r.record_id in wanted}
    return [by_id[rid] for rid in manifest["pack"] if rid in by_id]


def all_records(case_id: str, level: str) -> list[RetrievalRecord]:
    """Every passage of every selected paper of a question (the pool for follow-up retrieval)."""
    return [r for p in build(case_id, level)["papers"] for r in paper_records(p)]


# ---------------------------------------------------------------- follow-up search inside a run (experiment 44 loop)

def followup(h: H.Harness, plan: dict[str, Any], purpose: str, exclude_papers: set[str], exclude_records: set[str],
             budget: int, max_papers: int = 8) -> tuple[list[RetrievalRecord], dict[str, Any]]:
    """A live search for a run's open doubts: the same filters, screening and passage grading as the build, for new
    papers only; returns graded passages within the budget and a log."""
    flt = ws.CaseFilter(h.case["paper_id"])
    reasons: Counter[str] = Counter()
    pmcids, searches = run_searches(plan, flt)
    rows = ws.admit(flt, ws.core_records([p for p in pmcids if p not in exclude_papers]), reasons)
    terms = plan_terms(plan["groups"])
    order = ws.bm25_rank(terms, rows)
    grades = screen(h, [rows[p] for p in order[:2 * SCREEN_BATCH]], purpose, role="followup_screener")
    chosen = select(flt, rows, grades, order, max_papers, "followup", reasons)
    records = [r for p in chosen for r in paper_records(p) if r.record_id not in exclude_records]
    candidates = rank_passages(records, terms + S2.clean_terms(purpose), 4)
    passage_grades = grade_passages(h, candidates, purpose, role="followup_passage_grader")
    packed = pack(candidates, passage_grades, {p["pmcid"]: p["grade"] for p in chosen}, budget, exclude_records)
    log = {"plan": plan, "searches": searches, "admitted": len(rows), "screened": len(grades),
           "papers": [{k: p[k] for k in ("pmcid", "title", "grade", "date", "latest_date")} for p in chosen],
           "packed": [r.record_id for r in packed], "rejected": dict(reasons)}
    return packed, log


# ---------------------------------------------------------------- diagnostics: the same screener on the old corpora

def old_grades_path(case_id: str, level: str) -> Path:
    return OUT / "old_corpus_grades" / case_id / f"{level}.json"


def screen_old(case_id: str, level: str) -> dict[str, Any]:
    path = old_grades_path(case_id, level)
    if path.exists():
        return _read_json(path)
    h = H.Harness(H.cases()[case_id], level, 0)
    papers = ws.corpus_papers(case_id, level)
    rows = ws.core_records([p["pmcid"] for p in papers])
    graded = screen(h, [rows[p["pmcid"]] for p in papers if p["pmcid"] in rows], role="screener_old_corpus")
    out = {"case": case_id, "level": level, "grades": graded,
           "roles": {p["pmcid"]: p.get("role", "") for p in papers}, "models": h.models}
    atomic_json(path, out)
    return out


def units() -> list[tuple[str, str]]:
    return [(c["paper_id"], level) for c, level in H.units("all36")] + \
        [(c["paper_id"], level) for c, level in H.units("test4")]


def run_all(fn: Any, workers: int, selected: list[tuple[str, str]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    with ThreadPoolExecutor(workers) as pool:
        futures = {pool.submit(fn, c, lvl): (c, lvl) for c, lvl in selected}
        for future in as_completed(futures):
            try:
                future.result()
                counts["done"] += 1
            except Exception as error:  # noqa: BLE001 - logged; a rerun resumes
                counts["failed"] += 1
                print(f"[focused] {futures[future]}: {type(error).__name__}: {str(error)[:300]}", flush=True)
    return dict(counts)


def stats() -> dict[str, Any]:
    new, old = [], []
    for case_id, level in units():
        if manifest_path(case_id, level).exists():
            new.append(_read_json(manifest_path(case_id, level)))
        if old_grades_path(case_id, level).exists():
            old.append(_read_json(old_grades_path(case_id, level)))

    def dist(grades: list[int]) -> dict[str, Any]:
        return {"papers": len(grades), **{f"grade_{g}": round(sum(x == g for x in grades) / len(grades), 3)
                                          for g in range(4)}} if grades else {"papers": 0}

    return {
        "focused": {"questions": len(new), "papers_per_question": round(statistics.fmean(len(m["papers"]) for m in new), 1)
                    if new else None,
                    "screened_grades": dist([g["grade"] for m in new for g in m["screen_grades"].values()]),
                    "selected_paper_grades": dist([p["grade"] for m in new for p in m["papers"]]),
                    "pack_passage_grades": dist([m["passage_grades"][r] for m in new for r in m["pack"]]),
                    "pack_chars_mean": round(statistics.fmean(m["pack_chars"] for m in new)) if new else None,
                    "questions_with_empty_pack": sum(not m["pack"] for m in new)},
        "old_corpus": {"questions": len(old),
                       "paper_grades": dist([g["grade"] for o in old for g in o["grades"].values()]),
                       "seed_grades": dist([g["grade"] for o in old for p, g in o["grades"].items()
                                            if o["roles"].get(p) == "seed"]),
                       "expansion_grades": dist([g["grade"] for o in old for p, g in o["grades"].items()
                                                 if o["roles"].get(p) == "expansion"])},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("build", "screen_old", "stats"))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--case", action="append")
    parser.add_argument("--level", action="append")
    args = parser.parse_args()
    selected = [(c, lvl) for c, lvl in units() if (not args.case or c in args.case)
                and (not args.level or lvl in args.level)]
    if args.stage == "build":
        print(run_all(build, args.workers, selected))
    elif args.stage == "screen_old":
        print(run_all(screen_old, args.workers, selected))
    else:
        result = stats()
        atomic_json(OUT / "stats.json", result)
        print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
