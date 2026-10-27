"""Experiment 36 (loop.md 17.1, 17.2): web search for papers, with strict date filtering and citation-graph expansion.

The engine is Europe PMC's live REST search (open-access JATS XML full text). Crossref is the second, independent
source of publication dates and types, and each paper's own JATS reference list gives its references. (OpenAlex,
the planned second source, became unavailable during the build: loop.md 17.2.) Every result passes a filter in code
before any model sees it (must_obey.md 4.1, 4.2, 4.7):
  (a) every known date is before the case's date: Europe PMC's first and electronic publication dates and Crossref's
      publication date (both sources are required; a partial date counts as the end of its month or year);
  (b) not the case paper or its work family: DOI, PMCID, title Jaccard >= 0.8, or >= 0.5 with the same first author;
  (c) not one of the 45 held-out papers, which are never evidence for any case;
  (d) not a preprint, review, editorial, erratum, correction, retraction, comment or data paper (types from both
      sources; titles announcing a review also count);
  (e) after XML parsing: the paper does not cite the case paper (DOI or near-identical title in its references);
  (f) it contains fewer than 5% of the case paper's 12-word passages (non-introduction text);
  (g) it has at least 3,000 characters of text.
Ranking uses BM25 on title and abstract only, never citation counts or other present-day signals.

Stages:
  build   one corpus per held-out paper and question: the first N = 50 papers of the web search (seeds), then up to
          50 references cited by at least 2 seeds (citation-graph expansion);
  gate    re-checks every corpus paper against every rule before any run (and against OpenAlex dates where cached);
  stats   corpus statistics.

WebTools is the live web-search tool for agents. It applies the same rules on every call and logs what it returns.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import re
import statistics
import threading
import time
import xml.etree.ElementTree as ET
from collections import Counter, OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

import citegraph as cg
import llm_client as lc
from hypothesis_evidence_v2 import atomic_json
from temporal_eval_v3 import EXPERIMENT_DIR, SNIPPET_CHARS, EligibleCorpus
from temporal_hypothesis_benchmark import RetrievalRecord, _read_json

OUT = EXPERIMENT_DIR / "websearch"
PARSED = OUT / "papers"  # JATS parses (text, references, citation contexts); raw XML is cached in citegraph/papers
HELD_OUT_DIRS = ("benchmark_v3_1", "benchmark_test2", "benchmark_test3", "benchmark_test4")
LEVELS = ("broad", "problem_constrained", "expert_context")
PHRASE_MODEL = "Llama-3.3-70B-Instruct_5"  # pre-cutoff (must_obey.md 4.6)
CROSSREF = "https://api.crossref.org/works"
N_SEEDS = 50
MAX_EXPANSION = 50
MIN_COCITATION = 2
MAX_HITS_PER_PHRASE = 2000
FAMILY_TITLE, FAMILY_TITLE_SAME_AUTHOR = 0.8, 0.5
SHINGLE_WORDS, VERSION_SHARE = 12, 0.05
MIN_TEXT_CHARS = 3000
PASSAGE_CHARS, CARD_CHARS, PAGE_CHARS = 1600, 3200, 2400
AGENT_HITS, AGENT_RETURN, AGENT_PARSE_LIMIT, AGENT_REFERENCES, MAX_READS = 200, 8, 16, 10, 6
WEB_IN_SEARCH = 3  # live web-search papers added to each search_corpus result of the suite's tool agent
BAD_TYPES = {"review", "review-article", "systematic review", "systematic-review", "editorial", "erratum",
             "published erratum", "correction", "retraction", "retraction of publication", "retracted publication",
             "data-paper", "dataset", "preprint", "comment", "news", "paratext"}
BAD_CROSSREF_TYPES = {"posted-content", "peer-review", "dataset", "database", "component", "report", "dissertation",
                      "standard", "grant", "book-review"}
REVIEW_TITLE = re.compile(r"\b(a review|review of|reviews? on|critical review|mini[- ]review|overview|perspectives?|"
                          r"recent (advances|progress|developments)|progress in|state[- ]of[- ]the[- ]art|"
                          r"roadmap|tutorial)\b", re.IGNORECASE)
GENERIC_TERMS = {"high", "entropy", "alloy", "alloys", "hea", "heas", "multi", "principal", "element", "elements",
                 "material", "materials", "property", "properties", "multicomponent", "concentrated", "complex"}
LITE_FIELDS = ("pmcid", "pmid", "doi", "title", "firstPublicationDate", "source")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------- polite, rate-limited HTTP (all threads and processes)

_MIN_INTERVAL = 0.12  # Europe PMC: about 8 requests per second in total
_CROSSREF_INTERVAL = 1.05  # Crossref public pool: 1 request per second, one at a time
_original_get = cg._get


def _clock(name: str, interval: float) -> None:
    """Waits for a shared request clock: a timestamp in a locked file, so every thread and process takes turns."""
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            handle.seek(0)
            try:
                last = float(handle.read().strip() or 0)
            except ValueError:
                last = 0.0
            wait = last + interval - time.time()
            if wait > 0:
                time.sleep(wait)
            handle.seek(0)
            handle.truncate()
            handle.write(f"{time.time():.4f}")
            handle.flush()
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _rate_limited_get(url: str, params: dict[str, Any] | None = None, timeout: int = 60, tries: int = 5,
                      raw: bool = False) -> Any:
    _clock(".request_clock", _MIN_INTERVAL)
    return _original_get(url, params=params, timeout=timeout, tries=tries, raw=raw)


cg._get = _rate_limited_get  # citegraph's Europe PMC helpers (search, full text) share the limiter


def _crossref_get(url: str, params: dict[str, Any] | None = None) -> Any:
    """Crossref allows one request at a time: the lock is held for the whole request."""
    path = OUT / ".crossref_lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            handle.seek(0)
            try:
                last = float(handle.read().strip() or 0)
            except ValueError:
                last = 0.0
            wait = last + _CROSSREF_INTERVAL - time.time()
            if wait > 0:
                time.sleep(wait)
            try:
                return _original_get(url, params=params, timeout=120, tries=6)
            finally:
                handle.seek(0)
                handle.truncate()
                handle.write(f"{time.time():.4f}")
                handle.flush()
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


# ---------------------------------------------------------------- small helpers

def day_before(iso: str) -> str:
    return (date.fromisoformat(iso) - timedelta(days=1)).isoformat()


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]


def surname(author_string: str) -> str:
    first = str(author_string or "").split(",")[0].strip()
    return first.split(" ")[0].lower() if first else ""


def pub_types(row: dict[str, Any]) -> set[str]:
    types = (row.get("pubTypeList") or {}).get("pubType") or []
    if isinstance(types, str):
        types = [types]
    return {str(t).strip().lower() for t in types}


def end_of_parts(parts: list[Any]) -> str:
    """Crossref date-parts as an ISO date; a partial date counts as the last day of its month or year (strict)."""
    year = int(parts[0])
    month = int(parts[1]) if len(parts) > 1 and parts[1] else 12
    if len(parts) > 2 and parts[2]:
        return date(year, month, int(parts[2])).isoformat()
    following = date(year + (month == 12), month % 12 + 1, 1)
    return (following - timedelta(days=1)).isoformat()


_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def _lock(name: str) -> threading.Lock:
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(name, threading.Lock())


# ---------------------------------------------------------------- held-out registry

_REGISTRY: dict[str, Any] = {}


def held_out_cases() -> dict[str, dict[str, Any]]:
    if "cases" not in _REGISTRY:
        cases: dict[str, dict[str, Any]] = {}
        for name in HELD_OUT_DIRS:
            for path in sorted((EXPERIMENT_DIR / name / "cases").glob("PMC*.json")):
                case = _read_json(path)
                cases.setdefault(case["paper_id"], case)
        _REGISTRY["cases"] = cases
    return _REGISTRY["cases"]


def heldout() -> dict[str, dict[str, Any]]:
    """All held-out papers with PMCID, DOIs, title, first author and date. Never evidence for any case (rule c)."""
    with _lock("heldout"):
        if "heldout" in _REGISTRY:
            return _REGISTRY["heldout"]
        path = OUT / "heldout.json"
        if not path.exists():
            import rubric_eval as rx
            meta = dict(rx.metadata())
            for name in HELD_OUT_DIRS[1:]:
                if (EXPERIMENT_DIR / name / "metadata.json").exists():
                    meta.update(_read_json(EXPERIMENT_DIR / name / "metadata.json"))
            rows: dict[str, dict[str, Any]] = {}
            for pid, case in held_out_cases().items():
                info = meta.get(pid, {})
                found = cg._get(f"{cg.EPMC}/search", {"query": f"PMCID:{pid}", "format": "json",
                                                      "resultType": "core", "pageSize": 5})
                hit = next((r for r in (found or {}).get("resultList", {}).get("result", [])
                            if r.get("pmcid") == pid), {})
                dois = {cg.norm_doi(info.get("doi")), cg.norm_doi(hit.get("doi"))}
                dois |= {cg.norm_doi(str(i)[4:]) for i in info.get("work_family_identifiers") or []
                         if str(i).startswith("doi:")}
                rows[pid] = {"paper_id": pid, "date": case["publication_date"], "split": case["split"],
                             "doi": cg.norm_doi(info.get("doi") or hit.get("doi")), "dois": sorted(d for d in dois if d),
                             "title": str(info.get("title") or hit.get("title") or ""),
                             "first_author": surname(hit.get("authorString", ""))}
            atomic_json(path, rows)
        _REGISTRY["heldout"] = _read_json(path)
        return _REGISTRY["heldout"]


# ---------------------------------------------------------------- the case filter (rules a-g)

def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(text).lower())


def shingles(text: str, n: int = SHINGLE_WORDS) -> set[int]:
    words = _words(text)
    return {hash(" ".join(words[i:i + n])) for i in range(max(0, len(words) - n + 1))}


_SHINGLES: dict[str, set[int]] = {}


class CaseFilter:
    def __init__(self, case_id: str):
        registry = heldout()
        row = registry[case_id]
        self.case_id = case_id
        self.cutoff = row["date"]
        self.dois = set(row["dois"])
        self.title = cg.title_tokens(row["title"])
        self.first_author = row["first_author"]
        self.held_pmcids = set(registry)
        self.held_dois = {d for r in registry.values() for d in r["dois"]}
        self.held_titles = [cg.title_tokens(r["title"]) for r in registry.values() if r["title"]]

    def case_shingles(self) -> set[int]:
        with _lock(f"shingles:{self.case_id}"):
            if self.case_id not in _SHINGLES:
                from review_measurement import paper_text
                _SHINGLES[self.case_id] = shingles(paper_text(self.case_id, limit=400000))
        return _SHINGLES[self.case_id]

    def identity(self, pmcid: str = "", doi: str = "", title: str = "", first_author: str = "") -> str | None:
        """Rules (b) and (c): the case paper, its work family, or any held-out paper."""
        doi = cg.norm_doi(doi)
        tokens = cg.title_tokens(title)
        if pmcid == self.case_id or (doi and doi in self.dois):
            return "case_paper"
        if tokens and self.title:
            overlap = cg.jaccard(tokens, self.title)
            if overlap >= FAMILY_TITLE or (overlap >= FAMILY_TITLE_SAME_AUTHOR and first_author
                                           and first_author == self.first_author):
                return "case_family"
        if pmcid in self.held_pmcids or (doi and doi in self.held_dois):
            return "held_out"
        if tokens and any(cg.jaccard(tokens, t) >= FAMILY_TITLE for t in self.held_titles):
            return "held_out"
        return None

    def check_row(self, row: dict[str, Any]) -> str | None:
        """Rules (a)-(d) on a Europe PMC core record."""
        if not row.get("pmcid"):
            return "no_pmcid"
        if str(row.get("source", "")).upper() == "PPR" or "preprint" in pub_types(row):
            return "preprint"
        if pub_types(row) & BAD_TYPES:
            return "excluded_type"
        if REVIEW_TITLE.search(str(row.get("title", ""))):
            return "excluded_type_title"
        first = str(row.get("firstPublicationDate") or "")[:10]
        electronic = str(row.get("electronicPublicationDate") or "")[:10]
        if not DATE_RE.match(first):
            return "no_date"
        if first >= self.cutoff or (electronic and electronic >= self.cutoff):
            return "after_cutoff"
        return self.identity(row.get("pmcid", ""), row.get("doi", ""), row.get("title", ""),
                             surname(row.get("authorString", "")))

    def check_crossref(self, work: dict[str, Any] | None) -> str | None:
        """Rule (a) second source and rule (d) on Crossref: a paper without a Crossref date is not kept."""
        if not work or not DATE_RE.match(str(work.get("published") or "")):
            return "no_crossref_date"
        if str(work["published"]) >= self.cutoff:
            return "after_cutoff_crossref"
        if str(work.get("type") or "").lower() in BAD_CROSSREF_TYPES:
            return "excluded_type_crossref"
        return None

    def check_parsed(self, parsed: dict[str, Any]) -> str | None:
        """Rules (e)-(g), after the XML is parsed."""
        for ref in parsed.get("refs", []):
            if ref.get("doi") and cg.norm_doi(ref["doi"]) in self.dois:
                return "cites_case"
            text = ref.get("title") or ref.get("raw") or ""
            if self.title and text:
                tokens = cg.title_tokens(text)
                overlap = (cg.jaccard(tokens, self.title) if ref.get("title")
                           else len(tokens & self.title) / len(self.title))
                if overlap >= FAMILY_TITLE and len(self.title) >= 4:
                    return "cites_case"
        text = str(parsed.get("text", ""))
        if len(text) < MIN_TEXT_CHARS:
            return "short_text"
        case = self.case_shingles()
        if case and len(case & shingles(text)) / len(case) >= VERSION_SHARE:
            return "version_overlap"
        return None


# ---------------------------------------------------------------- Europe PMC search, records, Crossref dates

def _keep_core(row: dict[str, Any]) -> dict[str, Any]:
    return {"pmcid": row.get("pmcid"), "pmid": row.get("pmid"), "doi": cg.norm_doi(row.get("doi")),
            "title": row.get("title", ""), "authorString": row.get("authorString", ""),
            "journal": ((row.get("journalInfo") or {}).get("journal") or {}).get("title", ""),
            "firstPublicationDate": row.get("firstPublicationDate"),
            "electronicPublicationDate": row.get("electronicPublicationDate"),
            "source": row.get("source"), "pubTypeList": row.get("pubTypeList") or {},
            "abstractText": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(row.get("abstractText") or ""))).strip()}


def search(query: str, limit: int, core: bool = False) -> dict[str, Any]:
    """All hits of a query (up to limit), cached by query text. Core results are also stored per paper."""
    path = OUT / "search" / f"{sha(query + str(limit) + str(core))}.json"
    if path.exists():
        return _read_json(path)
    rows: list[dict[str, Any]] = []
    cursor, hits = "*", 0
    while len(rows) < limit:
        data = cg._get(f"{cg.EPMC}/search", {"query": query, "format": "json",
                                             "resultType": "core" if core else "lite",
                                             "pageSize": min(1000, limit - len(rows)), "cursorMark": cursor},
                       timeout=180) or {}
        hits = int(data.get("hitCount") or 0)
        page = data.get("resultList", {}).get("result", [])
        if core:
            for row in page:
                if row.get("pmcid"):
                    record_path = OUT / "records" / f"{row['pmcid']}.json"
                    if not record_path.exists():
                        atomic_json(record_path, _keep_core(row))
            rows += [{"pmcid": r.get("pmcid")} for r in page]
        else:
            rows += [{k: r.get(k) for k in LITE_FIELDS} for r in page]
        nxt = data.get("nextCursorMark")
        if not page or not nxt or nxt == cursor:
            break
        cursor = nxt
    result = {"query": query, "hit_count": hits, "fetched": len(rows), "searched_at": time.strftime("%Y-%m-%d"),
              "rows": rows}
    atomic_json(path, result)
    return result


def core_records(pmcids: list[str]) -> dict[str, dict[str, Any]]:
    """Europe PMC core records (abstract, authors, all dates, types) by PMCID, cached one file per paper."""
    out: dict[str, dict[str, Any]] = {}
    missing = []
    for pmcid in dict.fromkeys(p for p in pmcids if p):
        path = OUT / "records" / f"{pmcid}.json"
        if path.exists():
            out[pmcid] = _read_json(path)
        else:
            missing.append(pmcid)
    for start in range(0, len(missing), 40):
        chunk = missing[start:start + 40]
        data = cg._get(f"{cg.EPMC}/search", {"query": " OR ".join(f"PMCID:{p}" for p in chunk), "format": "json",
                                             "resultType": "core", "pageSize": 100}, timeout=180) or {}
        for row in data.get("resultList", {}).get("result", []):
            pmcid = row.get("pmcid")
            if pmcid in chunk and pmcid not in out:
                out[pmcid] = _keep_core(row)
                atomic_json(OUT / "records" / f"{pmcid}.json", out[pmcid])
    return out


_CROSSREF: dict[str, Any] = {}


def _crossref_item(work: dict[str, Any]) -> dict[str, Any]:
    parts = (work.get("published") or work.get("issued") or {}).get("date-parts") or [[None]]
    title = work.get("title") or [""]
    return {"published": end_of_parts(parts[0]) if parts and parts[0] and parts[0][0] else None,
            "published_parts": parts[0] if parts else None, "type": work.get("type"),
            "title": title[0] if isinstance(title, list) and title else str(title)}


def crossref_works(dois: list[str]) -> dict[str, dict[str, Any] | None]:
    """Crossref publication date (earliest of print and online, as deposited), type and title by DOI. Cached."""
    path = OUT / "crossref_by_doi.json"
    with _lock("crossref"):
        if not _CROSSREF and path.exists():
            _CROSSREF.update(_read_json(path))
        missing = sorted({cg.norm_doi(d) for d in dois if d} - set(_CROSSREF))
    if missing:
        found: dict[str, dict[str, Any]] = {}
        singles = sorted(d for d in missing if "," in d or len(d) >= 200)
        transient: list[str] = []
        batchable = [d for d in missing if d not in singles]
        for start in range(0, len(batchable), 40):
            chunk = batchable[start:start + 40]
            try:
                data = _crossref_get(CROSSREF, {"filter": ",".join(f"doi:{d}" for d in chunk), "rows": 100,
                                                "select": "DOI,type,title,published,issued"}) or {}
            except Exception:  # noqa: BLE001 - a malformed DOI can fail a batch; its DOIs are looked up one by one
                singles += chunk
                continue
            for work in (data.get("message") or {}).get("items", []):
                found[cg.norm_doi(work.get("DOI"))] = _crossref_item(work)
        for doi in singles:
            try:
                data = _crossref_get(f"{CROSSREF}/{quote(doi, safe='')}") or {}
            except RuntimeError:  # Crossref kept failing: not cached, so the lookup is retried later
                transient.append(doi)
                continue
            except Exception:  # noqa: BLE001 - rejected request (malformed DOI): no record, so no second date
                continue
            if data.get("message"):
                found[doi] = _crossref_item(data["message"])
        with _lock("crossref"):
            for doi in missing:
                if doi not in transient:
                    _CROSSREF[doi] = found.get(doi)
            atomic_json(path, _CROSSREF)
        if transient:
            raise RuntimeError(f"Crossref did not respond for {len(transient)} DOIs; retry later")
    return {cg.norm_doi(d): _CROSSREF.get(cg.norm_doi(d)) for d in dois if d}


def paper_entry(row: dict[str, Any], work: dict[str, Any] | None) -> dict[str, Any]:
    dates = {"epmc_first": str(row.get("firstPublicationDate") or "")[:10],
             "epmc_electronic": str(row.get("electronicPublicationDate") or "")[:10],
             "crossref": str((work or {}).get("published") or "")[:10]}
    known = [d for d in dates.values() if DATE_RE.match(d)]
    return {"pmcid": row["pmcid"], "doi": cg.norm_doi(row.get("doi")), "title": row.get("title", ""),
            "first_author": surname(row.get("authorString", "")), "journal": row.get("journal", ""),
            "dates": dates, "date": min(known), "latest_date": max(known)}


def load_parsed(pmcid: str) -> dict[str, Any]:
    return _read_json(PARSED / f"{pmcid}.json")


def parsed_paper(pmcid: str) -> dict[str, Any] | None:
    """The paper's JATS XML (Europe PMC, cached) parsed into text, references and citation contexts."""
    path = PARSED / f"{pmcid}.json"
    with _lock(f"paper:{pmcid}"):
        if path.exists():
            return _read_json(path)
        try:
            xml = cg.fetch_xml(pmcid)
        except Exception as error:  # noqa: BLE001 - a paper that cannot be fetched is skipped and counted
            print(f"[websearch] {pmcid}: {type(error).__name__}: {str(error)[:120]}", flush=True)
            return None
        if xml is None:
            return None
        try:
            parsed = cg.parse_jats(pmcid, xml)
        except ET.ParseError:
            return None
        for ref in parsed["refs"]:
            ref["doi"] = cg.norm_doi(ref.get("doi"))
        atomic_json(path, parsed)
        return parsed


def bm25_rank(query_terms: list[str], rows: dict[str, dict[str, Any]]) -> list[str]:
    docs = {pid: cg.content_terms(f"{r.get('title', '')} {r.get('title', '')} {r.get('abstractText', '')}")
            for pid, r in rows.items()}
    scores = cg.bm25(query_terms, docs)
    return sorted(rows, key=lambda pid: (-scores[pid], pid))


def oa_by_dois(dois: list[str]) -> dict[str, dict[str, Any]]:
    """DOI -> Europe PMC record with open-access full text (citegraph.epmc_oa_by_dois, made robust). A malformed DOI
    makes Europe PMC fail the whole query, so a failing batch is split until that DOI is isolated and skipped. Many
    failing single DOIs mean the service is down, and the call fails instead of returning less."""
    found: dict[str, dict[str, Any]] = {}
    skipped: list[str] = []

    def lookup(chunk: list[str]) -> None:
        query = "(" + " OR ".join(f'DOI:"{d}"' for d in chunk) + ") AND OPEN_ACCESS:y AND HAS_FT:y"
        try:
            records = cg.epmc_search(query, page_size=100)
        except RuntimeError:
            if len(chunk) == 1:
                skipped.append(chunk[0])
                if len(skipped) > 5:
                    raise
                return
            lookup(chunk[:len(chunk) // 2])
            lookup(chunk[len(chunk) // 2:])
            return
        for record in records:
            if record.get("pmcid") and record.get("doi"):
                found[cg.norm_doi(record["doi"])] = record

    clean = sorted({d for d in dois if d and '"' not in d and "\\" not in d})
    for start in range(0, len(clean), 20):
        lookup(clean[start:start + 20])
    if skipped:
        print(f"[websearch] Europe PMC rejected {len(skipped)} DOI(s), skipped: {skipped}", flush=True)
    return found


def admit(flt: CaseFilter, rows: dict[str, dict[str, Any]], reasons: Counter[str] | None = None
          ) -> dict[str, dict[str, Any]]:
    """Rules (a)-(d) on Europe PMC records and their Crossref works."""
    reasons = reasons if reasons is not None else Counter()
    kept = {}
    for pmcid, row in rows.items():
        reason = flt.check_row(row)
        if reason:
            reasons[reason] += 1
        else:
            kept[pmcid] = row
    works = crossref_works([r["doi"] for r in kept.values() if r.get("doi")])
    out = {}
    for pmcid, row in kept.items():
        reason = flt.check_crossref(works.get(row.get("doi") or ""))
        if reason:
            reasons[reason] += 1
        else:
            out[pmcid] = row
    return out


# ---------------------------------------------------------------- the per-question corpus

def filters(cutoff: str) -> str:
    return f"OPEN_ACCESS:y AND HAS_FT:y AND NOT SRC:PPR AND FIRST_PDATE:[1900-01-01 TO {day_before(cutoff)}]"


def corpus_stem(case_id: str, level: str, question: str | None = None) -> Path:
    """Corpora are per question. The harness's v3.1 questions use <level>; any other wording of a question (the
    suite's v3 questions, loop.md 17.1) gets its own corpus, <level>.q<hash>."""
    if question is None or question == held_out_cases()[case_id]["queries"][level]["text"]:
        return OUT / "corpora" / case_id / level
    return OUT / "corpora" / case_id / f"{level}.q{sha(question)[:8]}"


def corpus_path(case_id: str, level: str, question: str | None = None) -> Path:
    return Path(f"{corpus_stem(case_id, level, question)}.json")


def phrases_for(case_id: str, level: str, question: str) -> list[str]:
    path = Path(f"{corpus_stem(case_id, level, question)}.phrases.json")
    if path.exists():
        return _read_json(path)["phrases"]
    raw = lc.trapi_chat_json(PHRASE_MODEL, cg.KEYWORD_SYSTEM, json.dumps({"question": question}, ensure_ascii=False),
                             max_tokens=800, token_field="max_tokens", temperature=0.0, retries=8)
    phrases = [re.sub(r"\s+", " ", re.sub(r"[\"()]", " ", str(p))).strip()
               for p in (raw.get("phrases", []) if isinstance(raw, dict) else [])]
    phrases = [p for p in phrases if 2 <= len(p.split()) <= 8][:3]
    if not phrases:
        raise ValueError(f"{case_id}/{level}: no usable search phrases")
    atomic_json(path, {"case": case_id, "level": level, "question": question, "phrases": phrases,
                       "writer": f"trapi:{PHRASE_MODEL}"})
    return phrases


def phrase_query(phrase: str, cutoff: str) -> str:
    """OR of the phrase's content terms in the abstract, within the HEA domain. Generic HEA words are dropped from the
    OR because the domain anchor already requires them (otherwise every domain paper would match)."""
    terms = [t for t in dict.fromkeys(cg.content_terms(phrase)) if t not in GENERIC_TERMS]
    core = f"({' OR '.join(f'ABSTRACT:{t}' for t in terms)}) AND {cg.DOMAIN_ANCHOR}" if terms else cg.DOMAIN_ANCHOR
    return f"{core} AND {filters(cutoff)}"


def build_corpus(case_id: str, level: str, question: str | None = None) -> dict[str, Any]:
    question = question or held_out_cases()[case_id]["queries"][level]["text"]
    path = corpus_path(case_id, level, question)
    if path.exists():
        return _read_json(path)
    flt = CaseFilter(case_id)
    phrases = phrases_for(case_id, level, question)
    reasons: Counter[str] = Counter()
    searches, hits = [], {}
    for phrase in phrases:
        result = search(phrase_query(phrase, flt.cutoff), MAX_HITS_PER_PHRASE)
        searches.append({"phrase": phrase, "query": result["query"], "hit_count": result["hit_count"],
                         "fetched": result["fetched"], "searched_at": result["searched_at"]})
        for row in result["rows"]:
            if row.get("pmcid"):
                hits.setdefault(row["pmcid"], row)
    rows = core_records(list(hits))
    reasons["no_core_record"] += len(set(hits) - set(rows))
    candidates = admit(flt, rows, reasons)
    works = crossref_works([r["doi"] for r in candidates.values() if r.get("doi")])
    query_terms = cg.content_terms(question) + [t for p in phrases for t in cg.content_terms(p)]
    ranked = bm25_rank(query_terms, candidates)
    seeds: list[dict[str, Any]] = []
    with ThreadPoolExecutor(6) as pool:
        for start in range(0, len(ranked), 18):
            if len(seeds) >= N_SEEDS:
                break
            batch = ranked[start:start + 18]
            parsed = dict(zip(batch, pool.map(parsed_paper, batch)))
            for rank, pmcid in enumerate(batch, start + 1):
                if len(seeds) >= N_SEEDS:
                    break
                paper = parsed[pmcid]
                reason = "no_xml" if paper is None else flt.check_parsed(paper)
                if reason:
                    reasons[reason] += 1
                    continue
                entry = paper_entry(candidates[pmcid], works.get(candidates[pmcid].get("doi") or ""))
                seeds.append({**entry, "role": "seed", "rank": rank})
    expansion, exp_reasons = expand(seeds, flt, query_terms)
    reasons.update({f"expansion_{k}": v for k, v in exp_reasons.items()})
    manifest = {"case": case_id, "level": level, "cutoff": flt.cutoff, "question": question, "phrases": phrases,
                "phrase_writer": f"trapi:{PHRASE_MODEL}", "searches": searches, "unique_hits": len(hits),
                "candidates_after_filters": len(candidates), "n_seeds": N_SEEDS, "seeds": seeds,
                "expansion": expansion, "rejected": dict(reasons), "rules": "loop.md 17.1, 17.2",
                "date_sources": ["europe_pmc", "crossref"], "built_at": time.strftime("%Y-%m-%d %H:%M")}
    atomic_json(path, manifest)
    return manifest


def expand(seeds: list[dict[str, Any]], flt: CaseFilter, query_terms: list[str]
           ) -> tuple[list[dict[str, Any]], Counter[str]]:
    """Backward citation-graph expansion: references (by DOI, from the seeds' JATS reference lists) cited by at least
    MIN_COCITATION seeds (must_obey.md 4.3)."""
    reasons: Counter[str] = Counter()
    cocited: Counter[str] = Counter()
    seed_dois = {s["doi"] for s in seeds if s.get("doi")}
    seed_pmcids = {s["pmcid"] for s in seeds}
    for seed in seeds:
        for doi in {cg.norm_doi(r.get("doi")) for r in load_parsed(seed["pmcid"]).get("refs", [])} - {""}:
            cocited[doi] += 1
    frequent = sorted(d for d, c in cocited.items() if c >= MIN_COCITATION and d not in seed_dois)
    works = crossref_works(frequent)
    eligible = []
    for doi in frequent:
        work = works.get(doi)
        reason = flt.check_crossref(work)
        if not reason and REVIEW_TITLE.search(str((work or {}).get("title") or "")):
            reason = "excluded_type_title"
        reason = reason or flt.identity("", doi, str((work or {}).get("title") or ""))
        if reason:
            reasons[reason] += 1
        else:
            eligible.append(doi)
    title_scores = cg.bm25(query_terms, {d: cg.content_terms(str(works[d].get("title") or "")) for d in eligible})
    eligible.sort(key=lambda d: (-cocited[d], -title_scores.get(d, 0.0), d))
    chosen: list[dict[str, Any]] = []
    for start in range(0, len(eligible), 100):
        if len(chosen) >= MAX_EXPANSION:
            break
        chunk = eligible[start:start + 100]
        open_records = oa_by_dois(chunk)
        rows = core_records([open_records[d]["pmcid"] for d in chunk if d in open_records])
        for doi in chunk:
            if len(chosen) >= MAX_EXPANSION:
                break
            record = open_records.get(doi)
            if not record:
                reasons["no_open_xml"] += 1
                continue
            row = rows.get(record["pmcid"])
            if row is None or record["pmcid"] in seed_pmcids:
                reasons["no_core_record" if row is None else "already_seed"] += 1
                continue
            reason = flt.check_row(row) or flt.check_crossref(works.get(doi))
            if reason:
                reasons[reason] += 1
                continue
            parsed = parsed_paper(row["pmcid"])
            reason = "no_xml" if parsed is None else flt.check_parsed(parsed)
            if reason:
                reasons[reason] += 1
                continue
            chosen.append({**paper_entry(row, works.get(doi)), "role": "expansion", "cocitation": cocited[doi]})
    return chosen, reasons


# ---------------------------------------------------------------- evidence records

def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40] or "text"


def _is_heading(line: str) -> bool:
    return len(line) <= 120 and len(line.split()) <= 12 and not re.search(r"[.!?:;,]$", line)


BACK_MATTER = re.compile(r"data availability|author contribution|conflicts? of interest|competing interest|funding|"
                         r"acknowledg|declaration|supplementary|supporting information|abbreviations|"
                         r"institutional review|informed consent|ethic|credit authorship", re.IGNORECASE)


def sections(parsed: dict[str, Any]) -> list[tuple[str, str]]:
    """(section, paragraph) pairs from citegraph.parse_jats text: the abstract, then body paragraphs under their
    headings. parse_jats puts each heading on its own line between blank lines, and paragraphs on single lines."""
    out: list[tuple[str, str]] = []
    if parsed.get("abstract"):
        out.append(("Abstract", str(parsed["abstract"])))
    parts = str(parsed.get("text", "")).split("\n\n", 2)
    lines = parts[2].split("\n") if len(parts) == 3 else []
    section = "Body"
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue
        isolated = (i == 0 or not lines[i - 1].strip()) and (i + 1 >= len(lines) or not lines[i + 1].strip())
        if isolated and _is_heading(line):
            section = line
            continue
        if not BACK_MATTER.search(section):
            out.append((section, line))
    return out


def _record(entry: dict[str, Any], rid: str, kind: str, text: str) -> RetrievalRecord:
    # publication_date is the latest of the paper's known dates, so the standard temporal audit checks the strictest one
    return RetrievalRecord(rid, entry["pmcid"], entry["latest_date"], kind, text,
                           {"source": "web", "doi": entry["doi"], "title": entry["title"], "dates": entry["dates"],
                            "role": entry.get("role", "")})


def passages(entry: dict[str, Any], parsed: dict[str, Any]) -> list[RetrievalRecord]:
    """Section-aligned passages of at most PASSAGE_CHARS characters, verbatim from the XML."""
    records: list[RetrievalRecord] = []
    buffer, section = "", ""

    def flush() -> None:
        nonlocal buffer
        text = buffer.strip()
        if text:
            records.append(_record(entry, f"{entry['pmcid']}::web::{len(records):03d}::{_slug(section)}",
                                   f"web:{section}"[:80], text))
        buffer = ""

    for sec, paragraph in sections(parsed):
        if sec != section:
            flush()
            section = sec
        pieces = [paragraph] if len(paragraph) <= PASSAGE_CHARS else cg.split_sentences(paragraph)
        for piece in pieces:
            piece = piece[:PASSAGE_CHARS]
            if buffer and len(buffer) + len(piece) + 1 > PASSAGE_CHARS:
                flush()
            buffer = f"{buffer} {piece}" if buffer else piece
    flush()
    return records


def card(entry: dict[str, Any], parsed: dict[str, Any]) -> RetrievalRecord:
    """Title, abstract and conclusions, verbatim (replaces the LLM-extracted cards on the web corpus)."""
    conclusion = " ".join(p for s, p in sections(parsed) if re.search(r"conclu|summary", s, re.IGNORECASE))
    text = f"{parsed.get('title', '')}\n\nAbstract: {parsed.get('abstract', '')}"
    if conclusion:
        text += f"\n\nConclusions: {conclusion}"
    return _record(entry, f"{entry['pmcid']}::webcard", "web:card", text[:CARD_CHARS])


def page_text(parsed: dict[str, Any]) -> str:
    out, current = [], None
    for sec, paragraph in sections(parsed):
        if sec != current:
            out.append(f"## {sec}")
            current = sec
        out.append(paragraph)
    return "\n".join(out)


_RECORDS: OrderedDict[tuple[str, ...], list[RetrievalRecord]] = OrderedDict()
_RECORDS_MAX = 24


def corpus_papers(case_id: str, level: str, question: str | None = None) -> list[dict[str, Any]]:
    manifest = _read_json(corpus_path(case_id, level, question))
    return manifest["seeds"] + manifest["expansion"]


def case_records(case_id: str, level: str, representation: str, question: str | None = None
                 ) -> list[RetrievalRecord]:
    """The evidence pool of one question: passages ("text_chunks") or cards ("card") of its web corpus."""
    key = (case_id, level, representation, str(corpus_stem(case_id, level, question)))
    with _lock("records"):
        if key in _RECORDS:
            _RECORDS.move_to_end(key)
            return _RECORDS[key]
    if representation not in ("text_chunks", "card"):
        raise ValueError(f"representation {representation!r} is not available on the web corpus")
    records: list[RetrievalRecord] = []
    for entry in corpus_papers(case_id, level, question):
        parsed = load_parsed(entry["pmcid"])
        records += passages(entry, parsed) if representation == "text_chunks" else [card(entry, parsed)]
    with _lock("records"):
        _RECORDS[key] = records
        while len(_RECORDS) > _RECORDS_MAX:
            _RECORDS.popitem(last=False)
    return records


def entry_for(pmcid: str) -> dict[str, Any] | None:
    row = core_records([pmcid]).get(pmcid)
    if row is None:
        return None
    work = crossref_works([row["doi"]]).get(row["doi"]) if row.get("doi") else None
    return {**paper_entry(row, work), "role": "resolved"}


def resolve(record_id: str) -> RetrievalRecord | None:
    """Rebuilds any web record from the caches (critics' evidence, the evidence-leak test)."""
    pmcid, _, rest = str(record_id).partition("::")
    if not (PARSED / f"{pmcid}.json").exists():
        return None
    entry = entry_for(pmcid)
    if entry is None:
        return None
    parsed = load_parsed(pmcid)
    if rest.startswith("web::"):
        return next((r for r in passages(entry, parsed) if r.record_id == record_id), None)
    if rest == "webcard":
        return card(entry, parsed)
    if rest.startswith("page::"):
        number = int(rest.split("::")[1])
        return _record(entry, record_id, "web:page", page_text(parsed)[(number - 1) * PAGE_CHARS:number * PAGE_CHARS])
    if rest == "paper":
        return _record(entry, record_id, "web:paper", page_text(parsed))
    if rest == "search_result":
        abstract = str(core_records([pmcid])[pmcid].get("abstractText", ""))[:300]
        return _record(entry, record_id, "web:search_result", f"{entry['title']}\n{abstract}")
    if rest == "reference":
        return _record(entry, record_id, "web:reference", entry["title"])
    return None


class WebLookup(dict):
    """record_id -> RetrievalRecord that rebuilds web records it was not given (papers found by an agent's search)."""

    def __missing__(self, key: str) -> RetrievalRecord:
        record = resolve(key)
        if record is None:
            raise KeyError(key)
        self[key] = record
        return record

    def __contains__(self, key: object) -> bool:
        if dict.__contains__(self, key):
            return True
        try:
            self[key]  # type: ignore[index]
        except (KeyError, ValueError):
            return False
        return True

    def get(self, key: str, default: Any = None) -> Any:  # type: ignore[override]
        try:
            return self[key]
        except (KeyError, ValueError):
            return default


# ---------------------------------------------------------------- leakage audit of what a run saw

def audit_records(records: list[RetrievalRecord], case_id: str) -> dict[str, int]:
    """Counters for web records (must_obey.md 4.8); every one must be zero. Re-checks every stored date and identity."""
    flt = CaseFilter(case_id)
    counts = {"temporal_violations": 0, "test_paper_leaks": 0, "family_leaks": 0, "target_doi_or_title_leaks": 0}
    for record in records:
        info = record.structured or {}
        dates = info.get("dates") or {}
        known = [d for d in dates.values() if d] + [record.publication_date]
        counts["temporal_violations"] += int(any(str(d) >= flt.cutoff for d in known)
                                             or not DATE_RE.match(str(dates.get("crossref", ""))))
        counts["test_paper_leaks"] += int(record.paper_id == case_id)
        identity = flt.identity(record.paper_id, info.get("doi", ""), info.get("title", ""))
        counts["target_doi_or_title_leaks"] += int(identity in ("case_paper", "case_family"))
        counts["family_leaks"] += int(identity == "held_out")
    return counts


# ---------------------------------------------------------------- the live web-search tool for agents

TOOL_DOC = [
    {"name": "web_search", "arguments": {"query": "keywords (no quotes or boolean operators)"},
     "returns": f"up to {AGENT_RETURN} open-access papers published before the knowledge cutoff, with paper_id, "
                "title, date, journal and the start of the abstract"},
    {"name": "read_paper", "arguments": {"paper_id": "a paper_id returned by a tool", "page": "page number, from 1"},
     "returns": f"one {PAGE_CHARS}-character page of the paper's full text and the number of pages; at most "
                f"{MAX_READS} pages per question"},
    {"name": "references", "arguments": {"paper_id": "a paper_id returned by a tool"},
     "returns": "the paper's references that are open access and published before the cutoff"},
    {"name": "finish", "arguments": {}, "returns": "ends the search; the pages read become the evidence"},
]


def agent_query(query: str, cutoff: str) -> str:
    """Plain keywords only: field syntax, ranges and boolean operators cannot reach the engine, so an agent cannot
    widen the date filter (results are also re-checked in code)."""
    words = [w for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-.]*", query)
             if w.upper() not in ("AND", "OR", "NOT", "TO")]
    return f"({' '.join(words[:12]) or 'high entropy alloy'}) AND {filters(cutoff)}"


class WebTools:
    """web_search, read_paper and references for one run. Every result passes CaseFilter (rules a-g) before it is
    shown, and every call is logged with the IDs and dates of what it returned."""

    def __init__(self, case_id: str, level: str):
        self.flt = CaseFilter(case_id)
        self.case_id, self.level = case_id, level
        self.allowed: dict[str, dict[str, Any]] = {}
        self.log: list[dict[str, Any]] = []
        self.pages: dict[str, RetrievalRecord] = {}
        self.listed: dict[str, RetrievalRecord] = {}  # search results and reference lists shown to the model

    def call(self, action: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            if action == "web_search":
                return self.web_search(arguments.get("query", ""))
            if action == "read_paper":
                return self.read_paper(arguments.get("paper_id", ""), arguments.get("page", 1))
            if action == "references":
                return self.references(arguments.get("paper_id", ""))
        except RuntimeError as error:  # the service kept failing after retries; the agent may try again
            self.log.append({"tool": action, "arguments": arguments, "error": str(error)[:200]})
            return {"error": "the literature service did not respond; try again or use another tool"}
        return {"error": f"unknown action {action!r}; use web_search, read_paper, references or finish"}

    def _usable(self, pmcid: str) -> dict[str, Any] | None:
        """Rules (e)-(g) need the parsed XML, so a paper is parsed before it is listed."""
        parsed = parsed_paper(pmcid)
        if parsed is None or self.flt.check_parsed(parsed):
            return None
        return parsed

    def _list(self, entry: dict[str, Any], text: str, kind: str) -> None:
        self.allowed.setdefault(entry["pmcid"], entry)
        rid = f"{entry['pmcid']}::{kind}"
        self.listed[rid] = _record(entry, rid, f"web:{kind}", text)

    def web_search(self, query: Any) -> dict[str, Any]:
        query = re.sub(r"\s+", " ", str(query or "")).strip()[:300]
        if not query:
            return {"error": "empty query"}
        result = search(agent_query(query, self.flt.cutoff), AGENT_HITS, core=True)
        rows = admit(self.flt, core_records([r["pmcid"] for r in result["rows"] if r.get("pmcid")]))
        broadened = None
        if len(rows) < AGENT_RETURN:
            # All words must match in a free-text query, so a long query can return few papers. Like a web engine's
            # partial matching, papers in the HEA domain matching any of the words are added and BM25 ranks them all.
            terms = [t for t in dict.fromkeys(cg.content_terms(query)) if t not in GENERIC_TERMS][:10]
            if terms:
                broadened = search(f"({' OR '.join(f'TITLE_ABS:{t}' for t in terms)}) AND {cg.DOMAIN_ANCHOR} AND "
                                   f"{filters(self.flt.cutoff)}", AGENT_HITS, core=True)
                extra = [r["pmcid"] for r in broadened["rows"] if r.get("pmcid") and r["pmcid"] not in rows]
                rows.update(admit(self.flt, core_records(extra)))
        works = crossref_works([r["doi"] for r in rows.values() if r.get("doi")])
        papers, refused = [], 0
        for pmcid in bm25_rank(cg.content_terms(query), rows)[:AGENT_PARSE_LIMIT]:
            if len(papers) >= AGENT_RETURN:
                break
            if self._usable(pmcid) is None:
                refused += 1
                continue
            entry = {**paper_entry(rows[pmcid], works.get(rows[pmcid].get("doi") or "")), "role": "agent_search"}
            snippet = str(rows[pmcid].get("abstractText", ""))[:300]
            self._list(entry, f"{entry['title']}\n{snippet}", "search_result")
            papers.append({"paper_id": pmcid, "title": entry["title"], "publication_date": entry["latest_date"],
                           "journal": entry["journal"], "abstract_start": snippet})
        self.log.append({"tool": "web_search", "query": query, "engine_query": result["query"],
                         "hit_count": result["hit_count"], "refused_after_parsing": refused,
                         "broadened_query": broadened["query"] if broadened else None,
                         "broadened_hit_count": broadened["hit_count"] if broadened else None,
                         "returned": [{"paper_id": p["paper_id"], "date": p["publication_date"]} for p in papers]})
        return {"query": query, "papers": papers, "note": "" if papers else "no eligible papers; try other keywords"}

    def read_paper(self, paper_id: Any, page: Any = 1) -> dict[str, Any]:
        entry = self.allowed.get(str(paper_id).strip())
        if entry is None:
            return {"error": f"unknown paper_id {paper_id!r}; use a paper_id returned by web_search or references"}
        text = page_text(load_parsed(entry["pmcid"]))
        pages = max(1, -(-len(text) // PAGE_CHARS))
        try:
            number = max(1, min(int(page), pages))
        except (TypeError, ValueError):
            number = 1
        rid = f"{entry['pmcid']}::page::{number:03d}"
        if rid not in self.pages:
            if len(self.pages) >= MAX_READS:
                return {"error": f"the limit of {MAX_READS} pages is reached; call finish"}
            self.pages[rid] = _record(entry, rid, "web:page", text[(number - 1) * PAGE_CHARS:number * PAGE_CHARS])
            self.log.append({"tool": "read_paper", "paper_id": entry["pmcid"], "page": number,
                             "date": entry["latest_date"]})
        return {"record_id": rid, "paper_id": entry["pmcid"], "title": entry["title"],
                "publication_date": entry["latest_date"], "page": number, "pages": pages,
                "text": self.pages[rid].text}

    def references(self, paper_id: Any) -> dict[str, Any]:
        entry = self.allowed.get(str(paper_id).strip())
        if entry is None:
            return {"error": f"unknown paper_id {paper_id!r}; use a paper_id returned by web_search or references"}
        dois = list(dict.fromkeys(cg.norm_doi(r.get("doi")) for r in load_parsed(entry["pmcid"]).get("refs", [])
                                  if r.get("doi")))[:80]
        works = crossref_works(dois)
        dois = [d for d in dois if not self.flt.check_crossref(works.get(d))
                and not self.flt.identity("", d, str((works.get(d) or {}).get("title") or ""))]
        open_records = oa_by_dois(dois)
        rows = admit(self.flt, core_records([r["pmcid"] for r in open_records.values()]))
        out = []
        for pmcid, row in rows.items():
            if len(out) >= AGENT_REFERENCES:
                break
            if self._usable(pmcid) is None:
                continue
            ref = {**paper_entry(row, works.get(row.get("doi") or "")), "role": "agent_reference"}
            self._list(ref, ref["title"], "reference")
            out.append({"paper_id": pmcid, "title": ref["title"], "publication_date": ref["latest_date"]})
        self.log.append({"tool": "references", "paper_id": entry["pmcid"],
                         "returned": [{"paper_id": r["paper_id"], "date": r["publication_date"]} for r in out]})
        return {"paper_id": entry["pmcid"], "references": out,
                "note": "" if out else "no open-access references before the cutoff"}


class WebEligibleCorpus(EligibleCorpus):
    """The suite's tool agent (experiments 7, 9, 11) on the web corpus of its question, with live web search inside
    its search tool. With Llama on Azure, any tool beyond experiment 7's four breaks the model's tool-call format
    (loop.md 17.3), so search_corpus returns the corpus's best passages and the live web search's best papers,
    alternately; a web paper is a readable record <pmcid>::paper (read_record pages through it)."""

    def __init__(self, case_id: str, level: str, question: str, kg: Any = None):
        papers = corpus_papers(case_id, level, question)
        metadata = {e["pmcid"]: {"earliest_public_date": e["latest_date"], "title": e["title"]} for e in papers}
        super().__init__(metadata, set(metadata), case_records(case_id, level, "text_chunks", question), kg=kg)
        self.tools = WebTools(case_id, level)

    def search(self, query: str, k: Any = 6) -> dict[str, Any]:
        found = super().search(query, k)
        corpus, live = found["results"], self.web_search(query, WEB_IN_SEARCH)["results"]
        merged = []
        for i in range(max(len(corpus), len(live))):
            merged += corpus[i:i + 1] + live[i:i + 1]
        found["results"] = merged
        found["note"] = "" if merged else "no matches; try different terms"
        return found

    def web_search(self, query: str, limit: int = AGENT_RETURN) -> dict[str, Any]:
        found = self.tools.call("web_search", {"query": query})
        if "error" in found:
            return {"query": query, "results": [], "note": found["error"]}
        results = []
        for paper in found.get("papers", [])[:limit]:
            rid = f"{paper['paper_id']}::paper"
            if rid not in self.lookup:
                self.lookup[rid] = _record(self.tools.allowed[paper["paper_id"]], rid, "web:paper",
                                           page_text(load_parsed(paper["paper_id"])))
            self.seen_ids.add(rid)
            results.append({"record_id": rid, "paper_id": paper["paper_id"], "publication_date":
                            paper["publication_date"], "kind": "web:paper", "snippet": f"{paper['title']}. "
                            f"{paper['abstract_start']}"[:SNIPPET_CHARS]})
        return {"query": found.get("query", query), "results": results, "note": found.get("note", "")}



# ---------------------------------------------------------------- citation graph of a web corpus (experiment 17 arms)

def web_graph(case_id: str, question: str | None = None, level: str = "problem_constrained") -> dict[str, Any]:
    """citegraph's graph schema built from a web corpus. Nodes are the corpus papers (XML cards) and the works they
    cite (by DOI, dated by Crossref); the statements about a node are the verbatim sentences in which corpus papers
    cite it (no LLM extraction). A node's citation count is the number of corpus papers citing it."""
    flt = CaseFilter(case_id)
    cutoff = flt.cutoff
    papers = corpus_papers(case_id, level, question)
    parsed_by = {e["pmcid"]: load_parsed(e["pmcid"]) for e in papers}
    ref_dois = {cg.norm_doi(r.get("doi")) for p in parsed_by.values() for r in p.get("refs", [])} - {""}
    works = crossref_works(sorted(ref_dois))
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[tuple[str, str]] = []
    dropped: Counter[str] = Counter()

    def node(wid: str, **fields: Any) -> dict[str, Any]:
        entry = nodes.setdefault(wid, {"id": wid, "roles": [], "card": [], "statements": [], "references": [],
                                       "pmcid": "", "title": "", "doi": "", "publication_date": "",
                                       "pre_cutoff_citations": 0})
        for key, value in fields.items():
            if value and not entry.get(key):
                entry[key] = value
        return entry

    for entry in papers:
        parsed = parsed_by[entry["pmcid"]]
        n = node(entry["doi"], pmcid=entry["pmcid"], title=parsed["title"] or entry["title"], doi=entry["doi"],
                 publication_date=entry["latest_date"])
        n["roles"].append(entry["role"])
        n["card"] = [card(entry, parsed).text]
    for entry in papers:
        parsed, wid = parsed_by[entry["pmcid"]], entry["doi"]
        n = nodes[wid]
        by_rid = {}
        for ref in parsed.get("refs", []):
            doi = cg.norm_doi(ref.get("doi"))
            work = works.get(doi) if doi else None
            if not doi or doi == wid:
                dropped["reference_without_doi"] += 1
                continue
            if flt.check_crossref(work):
                dropped["reference_undated_after_cutoff_or_excluded_type"] += 1
                continue
            if flt.identity("", doi, str(work.get("title") or ref.get("title") or "")):
                dropped["reference_case_or_held_out"] += 1
                continue
            ref_node = node(doi, title=work.get("title") or ref.get("title"), doi=doi,
                            publication_date=work["published"])
            if not ref_node["roles"]:
                ref_node["roles"].append("reference")
            by_rid[ref["rid"]] = doi
            if doi not in n["references"]:
                n["references"].append(doi)
                edges.append((wid, doi))
        for index, ctx in enumerate(parsed.get("contexts", [])):
            if len(ctx["rids"]) > cg.MAX_REFS_PER_CONTEXT:
                continue
            sentence = cg.clean_sentence(ctx["sentence"])
            for rid in ctx["rids"]:
                cited = by_rid.get(rid)
                if not cited or len(sentence) < 30:
                    dropped["statement_unresolved_or_dropped_node"] += 1
                    continue
                nodes[cited]["statements"].append({
                    "ctx": f"c{index}", "rid": rid, "cited": cited, "relation": "cites", "attributed": sentence[:500],
                    "cited_system": "not stated", "applied_to": "not stated", "numbers": "", "quote": sentence[:600],
                    "grounding": 1.0, "citer": wid, "citer_title": n["title"], "citer_date": n["publication_date"]})
    citing: Counter[str] = Counter(b for _, b in set(edges))
    for wid, n in nodes.items():
        seen, unique = set(), []
        for st in n["statements"]:
            key = (st["citer"], st["attributed"])
            if key not in seen:
                seen.add(key)
                unique.append(st)
        n["statements"] = unique
        n["citers"] = sorted({st["citer"] for st in n["statements"]})
        n["pre_cutoff_citations"] = citing[wid]
    return {"paper_id": case_id, "cutoff": cutoff, "source": "web",
            "corpus": str(corpus_path(case_id, level, question).relative_to(OUT)), "nodes": nodes, "edges": edges,
            "stats": {"nodes": len(nodes), "full_text_nodes": sum(bool(n["pmcid"]) for n in nodes.values()),
                      "seeds": sum("seed" in n["roles"] for n in nodes.values()),
                      "expansion": sum("expansion" in n["roles"] for n in nodes.values()), "edges": len(edges),
                      "nodes_with_statements": sum(bool(n["statements"]) for n in nodes.values()),
                      "statements": sum(len(n["statements"]) for n in nodes.values()),
                      "nodes_with_2plus_citers": sum(len(n["citers"]) >= 2 for n in nodes.values()),
                      "contradicting_statements": 0, "dropped": dict(dropped)}}


# ---------------------------------------------------------------- stages

def build_all(workers: int, case_ids: list[str] | None = None, levels: tuple[str, ...] = LEVELS,
              cases_dir: Path | None = None) -> dict[str, int]:
    """Builds every missing corpus. With cases_dir, the questions come from that case set (corpora of questions
    worded differently from v3.1 are stored apart, see corpus_stem)."""
    heldout()
    questions = {cid: case["queries"] for cid, case in held_out_cases().items()}
    if cases_dir is not None:
        questions = {c["paper_id"]: c["queries"] for c in (_read_json(p) for p in sorted(cases_dir.glob("PMC*.json")))}
    jobs = [(cid, level, questions[cid][level]["text"]) for cid in sorted(questions)
            if not case_ids or cid in case_ids for level in levels
            if not corpus_path(cid, level, questions[cid][level]["text"]).exists()]
    counts: Counter[str] = Counter()
    with ThreadPoolExecutor(workers) as pool:
        futures = {pool.submit(build_corpus, cid, level, question): (cid, level) for cid, level, question in jobs}
        for future in as_completed(futures):
            cid, level = futures[future]
            try:
                manifest = future.result()
                counts["built"] += 1
                print(f"[websearch] {cid}/{level}: seeds {len(manifest['seeds'])}, expansion "
                      f"{len(manifest['expansion'])}, unique hits {manifest['unique_hits']} "
                      f"({counts['built']}/{len(jobs)})", flush=True)
            except Exception as error:  # noqa: BLE001 - reported; the next call resumes
                counts["failed"] += 1
                print(f"[websearch] FAILED {cid}/{level}: {type(error).__name__}: {str(error)[:300]}", flush=True)
    return {"jobs": len(jobs), **counts}


def manifests() -> list[dict[str, Any]]:
    return [_read_json(p) for p in sorted((OUT / "corpora").glob("PMC*/*.json")) if not p.name.endswith(".phrases.json")]


def gate() -> dict[str, Any]:
    """Re-checks every corpus paper against rules (a)-(g) from stored data. Any violation fails the gate. OpenAlex
    dates cached before OpenAlex became unavailable (loop.md 17.2) are a third, extra date check where present."""
    violations: list[str] = []
    checked = 0
    openalex = _read_json(OUT / "openalex_by_doi.json") if (OUT / "openalex_by_doi.json").exists() else {}
    works = crossref_works([e["doi"] for m in manifests() for e in m["seeds"] + m["expansion"]])
    third = 0
    for manifest in manifests():
        flt = CaseFilter(manifest["case"])
        for entry in manifest["seeds"] + manifest["expansion"]:
            checked += 1
            where = f"{manifest['case']}/{manifest['level']}/{entry['pmcid']}"
            dates = entry["dates"]
            if not all(DATE_RE.match(dates.get(k) or "") for k in ("epmc_first", "crossref")):
                violations.append(f"{where}: a required date is missing: {dates}")
            if any(d and d >= flt.cutoff for d in dates.values()) or entry["latest_date"] >= flt.cutoff:
                violations.append(f"{where}: dated on or after the cutoff {flt.cutoff}: {dates}")
            reason = flt.check_row(_read_json(OUT / "records" / f"{entry['pmcid']}.json")) or flt.check_crossref(
                works.get(entry["doi"]))
            if reason:
                violations.append(f"{where}: {reason}")
            work = openalex.get(entry["doi"])
            if work and work.get("publication_date"):
                third += 1
                if str(work["publication_date"]) >= flt.cutoff:
                    violations.append(f"{where}: OpenAlex date {work['publication_date']} is on or after the cutoff")
            if not (PARSED / f"{entry['pmcid']}.json").exists():
                violations.append(f"{where}: missing parsed XML")
                continue
            reason = flt.check_parsed(load_parsed(entry["pmcid"]))
            if reason:
                violations.append(f"{where}: {reason}")
    result = {"corpora": len(manifests()), "corpus_papers_checked": checked, "checked_against_openalex_too": third,
              "violations": violations, "passed": not violations and checked > 0,
              "checked_at": time.strftime("%Y-%m-%d %H:%M")}
    atomic_json(OUT / "gate.json", result)
    return result


def stats() -> dict[str, Any]:
    ms = manifests()
    harness = [m for m in ms if m["question"] == held_out_cases()[m["case"]]["queries"][m["level"]]["text"]]
    unique = {e["pmcid"] for m in ms for e in m["seeds"] + m["expansion"]}
    rejected: Counter[str] = Counter()
    for m in ms:
        rejected.update(m["rejected"])

    def spread(values: list[int]) -> dict[str, Any]:
        return {"min": min(values), "median": statistics.median(values), "max": max(values)} if values else {}

    out = {"corpora": len(ms), "harness_corpora_v3_1": len(harness), "suite_only_corpora_v3": len(ms) - len(harness),
           "unique_papers": len(unique),
           "unique_seed_papers": len({e["pmcid"] for m in ms for e in m["seeds"]}),
           "unique_expansion_papers": len({e["pmcid"] for m in ms for e in m["expansion"]}),
           "seeds_per_corpus": spread([len(m["seeds"]) for m in ms]),
           "expansion_per_corpus": spread([len(m["expansion"]) for m in ms]),
           "unique_hits_per_corpus": spread([m["unique_hits"] for m in ms]),
           "candidates_after_filters": spread([m["candidates_after_filters"] for m in ms]),
           "days_before_cutoff_latest_paper": spread([
               (date.fromisoformat(m["cutoff"]) - max(date.fromisoformat(e["latest_date"])
                                                      for e in m["seeds"] + m["expansion"])).days
               for m in ms if m["seeds"]]),
           "rejected_total": dict(rejected.most_common())}
    atomic_json(OUT / "stats.json", out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("build", "gate", "stats"))
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--case", action="append")
    parser.add_argument("--level", action="append", choices=LEVELS)
    parser.add_argument("--cases-dir", type=Path, help="build the corpora of this case set's questions")
    args = parser.parse_args()
    if args.stage == "build":
        print(build_all(args.workers, args.case, tuple(args.level or LEVELS), args.cases_dir))
    elif args.stage == "gate":
        result = gate()
        print(json.dumps({k: v if k != "violations" else v[:20] for k, v in result.items()}, indent=1))
    else:
        print(json.dumps(stats(), indent=1))


if __name__ == "__main__":
    main()
