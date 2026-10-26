"""Citation-graph variant: per-case paper graphs built from the citation neighbourhood of the query.

For each held-out case (cutoff t = the case's publication date, query q = its problem_constrained query):

  S0  seeds        Europe PMC open-access full-text papers first published before t, relevant to q (top 40 per search
                   phrase), ranked by citations received before the cutoff year (OpenAlex counts_by_year); top N = 10,
                   excluding the held-out paper, its work family and near-duplicate titles.
  S1  expansion    for each seed, its top k = 3 references by (co-citation by seeds, relevance to q, pre-cutoff
                   citations) that have open full text; references without open full text are skipped.
  extraction       local Qwen: one paper card per full-text paper (rubric from experiment 14, quote-verified), and for
                   every sentence citing up to 4 references, one statement per cited reference describing what the
                   citing paper says about it (finding, method, support, contradiction, extension, comparison).
  graph G          nodes = S0 + S1 + references of S0 and S1 (OpenAlex works). A node holds its own card (full-text
                   papers only) and every statement made about it by papers in S0 + S1. All data is pre-cutoff.

Variants (generator Qwen, same evidence budget and two samples per unit as experiment 14):
  graph_selection            cards of the graph's full-text papers (control: the graph only chooses papers)
  graph_profiles             node profiles: own card + what citing papers say about the node
  graph_profiles_systemmatch profiles + the experiment-16 transfer appraisal, using citer statements as evidence
  corroboration_weighted     profiles ranked by relevance x number of independent citers; contradictions listed first
  graph_tool_agent           tool agent with search_nodes, read_node, who_cites, references, submit_hypothesis
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import statistics
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests

import llm_client as lc
import rubric_eval as rx
from hypothesis_evidence_v2 import atomic_json
from temporal_eval_v3 import EXPERIMENT_DIR, QUERY_LEVELS, RUN_ROOT, _generator_identity
from temporal_hypothesis_benchmark import _read_json

OUT = RUN_ROOT / "citegraph"
# Downloaded papers, their cards and citer statements are pre-cutoff material shared by every run root.
PAPERS = EXPERIMENT_DIR / "citegraph" / "papers"
CASES_OUT = OUT / "cases"
# The query the graph is built from (search phrases, seed relevance, expansion relevance). Benchmark v4 has a single
# level, so its rerun sets MATHG_GRAPH_LEVEL=scimon (loop.md 15.1).
GRAPH_LEVEL = os.environ.get("MATHG_GRAPH_LEVEL", "problem_constrained")
N_SEEDS = 10
K_PER_SEED = 3
SEARCH_POOL_PER_PHRASE = 100
RELEVANT_POOL = 40
MAX_REFS_PER_CONTEXT = 4
CONTEXT_BATCH = 20
MAX_CONTEXTS_PER_PAPER = 60
CONTEXT_MAX_TOKENS = 9000
CARD_WINDOWS = 2
MIN_GROUNDING = 0.5
RELATIONS = {"finding", "method", "supports", "contradicts", "extends", "compares", "background"}
TITLE_MATCH = 0.6
MIN_EXPANSION_RELEVANCE = 0.4
DUPLICATE_TITLE = 0.8
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
OPENALEX = "https://api.openalex.org/works"
OA_SELECT = "id,doi,display_name,publication_date,publication_year,cited_by_count,counts_by_year,ids,type,referenced_works"
ALLOWED_TYPES = {"research-article", "review-article", "Journal Article", "Review", "rapid-communication",
                 "brief-report", "article-commentary"}
EXCLUDED_TYPES = {"data-paper", "Dataset", "Editorial", "Erratum", "correction", "retraction", "Published Erratum"}
HEADERS = {"User-Agent": "mathg-citegraph/1.0 (research; contact via repository)"}

KEYWORD_SYSTEM = (
    "You turn a materials-science research question into literature-search phrases. Return JSON "
    "{\"phrases\": [three phrases]}. Each phrase has 2 to 6 words and names the material system or alloy family, "
    "and the property, process or mechanism the question is about. Use only terms from or directly implied by the "
    "question. No boolean operators or quotes."
)
CONTEXT_SYSTEM = (
    "You read sentences from a materials-science paper (the citing paper). Each sentence cites one or more earlier "
    "works, marked [R1], [R2] and so on, and each marker is listed with the reference it points to. For each sentence "
    "and each marker in it, write what the citing paper says about that cited work, if the sentence says something "
    "specific about it. Return JSON {\"statements\": [{\"ctx\": str, \"ref\": str, \"relation\": one of "
    "finding|method|supports|contradicts|extends|compares|background, \"attributed\": what the cited work found, "
    "did, proposed or measured according to this sentence (one sentence, keep numbers and alloy names), "
    "\"cited_system\": the material or alloy system the cited work concerns (or \"not stated\"), \"applied_to\": the "
    "material or system the citing paper applies or compares it to (or \"not stated\"), \"numbers\": any values given "
    "(or \"\")}]}. Relations: finding = reports a result of the cited work; method = the citing paper uses its method "
    "or data; supports = the citing paper's result agrees with it; contradicts = disagrees with it; extends = builds "
    "on it for a new case; compares = sets it against other work; background = generic mention with no specific "
    "content (give attributed \"\" in that case). Use only what the sentence says."
)


# ---------------------------------------------------------------- job runner

def run_jobs(stage: str, jobs: list[tuple[str, tuple[Any, ...]]], fn: Any, workers: int) -> dict[str, int]:
    errors = OUT / "errors" / stage
    errors.mkdir(parents=True, exist_ok=True)
    counts: Counter[str] = Counter()

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


# ---------------------------------------------------------------- HTTP helpers

def _get(url: str, params: dict[str, Any] | None = None, timeout: int = 60, tries: int = 5,
         raw: bool = False) -> Any:
    for attempt in range(tries):
        try:
            response = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        except requests.RequestException:
            time.sleep(3 * (attempt + 1))
            continue
        if response.status_code == 404:
            return None
        if response.status_code in (429, 500, 502, 503, 504):
            time.sleep(5 * (attempt + 1))
            continue
        response.raise_for_status()
        time.sleep(0.15)
        return response.text if raw else response.json()
    raise RuntimeError(f"request kept failing: {url} {params}")


def norm_doi(value: str | None) -> str:
    value = str(value or "").strip().lower()
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", value)


def short_oa(value: str) -> str:
    return str(value).rsplit("/", 1)[-1]


STOPWORDS = set("""the and for with from that this into within between versus than then their there these those which
while where when what whose given propose proposed specify specific expected must aim aims using used use via based
under over also such both each other more most less least can could would should may might will its not are was were
been being has have had how why does did one two three new novel study studies effect effects role roles case
experiment experiments falsification falsify distinguish intervention operating regime regimes trade off compared
literature reports reported report baseline approach method methods result results analysis investigation suffers
suffer introduce introducing induce inducing mitigate target targeted rather well like only any all some due""".split())


def _stem(token: str) -> str:
    return token[:-1] if len(token) > 4 and token.endswith("s") and not token.endswith("ss") else token


def title_tokens(text: str) -> set[str]:
    return {_stem(t) for t in rx.normalise(text).split() if len(t) > 2 and t not in STOPWORDS}


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def pre_cutoff_citations(work: dict[str, Any], cutoff: str) -> int:
    year = int(cutoff[:4])
    later = sum(c["cited_by_count"] for c in work.get("counts_by_year", []) if c["year"] >= year)
    return max(0, int(work.get("cited_by_count") or 0) - later)


def openalex_by_dois(dois: list[str]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    clean = sorted({d for d in dois if d})
    for start in range(0, len(clean), 40):
        chunk = clean[start:start + 40]
        data = _get(OPENALEX, {"filter": "doi:" + "|".join(chunk), "per-page": 50, "select": OA_SELECT})
        for work in (data or {}).get("results", []):
            found[norm_doi(work.get("doi"))] = work
    return found


def openalex_by_ids(ids: list[str]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    clean = sorted({short_oa(i) for i in ids if i})
    for start in range(0, len(clean), 50):
        chunk = clean[start:start + 50]
        data = _get(OPENALEX, {"filter": "openalex_id:" + "|".join(chunk), "per-page": 50, "select": OA_SELECT})
        for work in (data or {}).get("results", []):
            found[short_oa(work["id"])] = work
    return found


def epmc_search(query: str, page_size: int = 100) -> list[dict[str, Any]]:
    data = _get(f"{EPMC}/search", {"query": query, "format": "json", "pageSize": page_size, "resultType": "core"})
    return (data or {}).get("resultList", {}).get("result", [])


def epmc_oa_by_dois(dois: list[str]) -> dict[str, dict[str, Any]]:
    """DOI -> Europe PMC record, for records with open-access full text."""
    found: dict[str, dict[str, Any]] = {}
    clean = sorted({d for d in dois if d})
    for start in range(0, len(clean), 20):
        chunk = clean[start:start + 20]
        query = "(" + " OR ".join(f'DOI:"{d}"' for d in chunk) + ") AND OPEN_ACCESS:y AND HAS_FT:y"
        for record in epmc_search(query, page_size=100):
            if record.get("pmcid") and record.get("doi"):
                found[norm_doi(record["doi"])] = record
    return found


# ---------------------------------------------------------------- target exclusion

def target_exclusion(case: dict[str, Any]) -> dict[str, Any]:
    meta = rx.metadata()
    target = meta[case["paper_id"]]
    family = str(target.get("work_family_id") or "")
    dois = {norm_doi(target.get("doi"))}
    pmcids = {case["paper_id"]}
    titles = [title_tokens(str(target.get("title", "")))]
    if family:
        for pid, row in meta.items():
            if row.get("work_family_id") == family:
                dois.add(norm_doi(row.get("doi")))
                pmcids.add(pid)
                titles.append(title_tokens(str(row.get("title", ""))))
    return {"dois": {d for d in dois if d}, "pmcids": pmcids, "titles": titles}


def is_excluded(exclusion: dict[str, Any], doi: str = "", pmcid: str = "", title: str = "") -> bool:
    if doi and norm_doi(doi) in exclusion["dois"]:
        return True
    if pmcid and pmcid in exclusion["pmcids"]:
        return True
    tokens = title_tokens(title)
    return bool(tokens) and any(jaccard(tokens, t) >= DUPLICATE_TITLE for t in exclusion["titles"])


# ---------------------------------------------------------------- stage: keywords and seeds

def case_dir(paper_id: str) -> Path:
    return CASES_OUT / paper_id


def graph_query(case: dict[str, Any]) -> str:
    return case["queries"][GRAPH_LEVEL]["text"]


def keywords(case: dict[str, Any]) -> list[str]:
    path = case_dir(case["paper_id"]) / "keywords.json"
    if path.exists():
        return _read_json(path)["phrases"]
    query = graph_query(case)
    raw = lc.chat_json(KEYWORD_SYSTEM, json.dumps({"question": query}, ensure_ascii=False), max_tokens=800, retries=3)
    phrases = [re.sub(r"[\"()]", " ", str(p)).strip() for p in (raw.get("phrases", []) if isinstance(raw, dict) else [])]
    phrases = [re.sub(r"\s+", " ", p) for p in phrases if 2 <= len(p.split()) <= 8][:3]
    if not phrases:
        raise ValueError("keyword extraction returned no usable phrases")
    atomic_json(path, {"paper_id": case["paper_id"], "query": query, "phrases": phrases,
                       "generator": _generator_identity()})
    return phrases


def day_before(date: str) -> str:
    from datetime import date as _date, timedelta
    y, m, d = (int(x) for x in date.split("-"))
    return (_date(y, m, d) - timedelta(days=1)).isoformat()


SHORT_STOP = {"of", "in", "to", "by", "on", "at", "as", "or", "an", "is", "be", "it", "we", "vs", "via", "and", "the"}
DOMAIN_ANCHOR = ('(ABSTRACT:"high entropy" OR ABSTRACT:"high-entropy" OR ABSTRACT:"multi-principal" OR '
                 'ABSTRACT:"multi-principal-element" OR ABSTRACT:"complex concentrated" OR ABSTRACT:"medium entropy" '
                 'OR ABSTRACT:"medium-entropy" OR TITLE:"high entropy" OR TITLE:"high-entropy")')


def content_terms(text: str) -> list[str]:
    return [t for t in rx.normalise(text).split() if len(t) >= 2 and t not in STOPWORDS and t not in SHORT_STOP]


def bm25(query_terms: list[str], docs: dict[str, list[str]], k1: float = 1.2, b: float = 0.75) -> dict[str, float]:
    n = len(docs) or 1
    avg = sum(len(d) for d in docs.values()) / n if docs else 1.0
    df = Counter(t for d in docs.values() for t in set(d))
    scores = {}
    for key, doc in docs.items():
        tf = Counter(doc)
        score = 0.0
        for term in set(query_terms):
            if term not in tf:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            score += idf * tf[term] * (k1 + 1) / (tf[term] + k1 * (1 - b + b * len(doc) / max(avg, 1.0)))
        scores[key] = score
    return scores


def seeds_for_case(case: dict[str, Any]) -> dict[str, Any]:
    """Relevance pool (domain-anchored Europe PMC search, re-ranked by BM25 on title + abstract against the query
    and its search phrases), top RELEVANT_POOL kept, then ordered by citations received before the cutoff year."""
    phrases = keywords(case)
    query = graph_query(case)
    exclusion = target_exclusion(case)
    last_day = day_before(case["publication_date"])
    candidates: dict[str, dict[str, Any]] = {}
    for phrase in phrases:
        terms = list(dict.fromkeys(content_terms(phrase)))
        words = " OR ".join(f"ABSTRACT:{t}" for t in terms) or phrase
        search = (f"({words}) AND {DOMAIN_ANCHOR} AND OPEN_ACCESS:y AND HAS_FT:y "
                  f"AND FIRST_PDATE:[1900-01-01 TO {last_day}]")
        for rank, record in enumerate(epmc_search(search, page_size=SEARCH_POOL_PER_PHRASE)):
            pmcid, doi = record.get("pmcid"), norm_doi(record.get("doi"))
            types = set(record.get("pubTypeList", {}).get("pubType", []))
            if not pmcid or not doi or types & EXCLUDED_TYPES:
                continue
            if record.get("firstPublicationDate", "9999") >= case["publication_date"]:
                continue
            if is_excluded(exclusion, doi, pmcid, record.get("title", "")):
                continue
            entry = candidates.setdefault(pmcid, {"pmcid": pmcid, "doi": doi, "title": record.get("title", ""),
                                                  "abstract": record.get("abstractText", ""),
                                                  "first_date": record.get("firstPublicationDate"),
                                                  "types": sorted(types), "phrases": []})
            entry["phrases"].append(phrase)
    query_terms = content_terms(query) + [t for p in phrases for t in content_terms(p)]
    scores = bm25(query_terms, {k: content_terms(f"{v['title']} {v['title']} {v['abstract']}")
                                for k, v in candidates.items()})
    relevant = sorted(candidates.values(), key=lambda e: (-scores[e["pmcid"]], e["pmcid"]))[:RELEVANT_POOL]
    works = openalex_by_dois([c["doi"] for c in relevant])
    ranked = []
    for entry in relevant:
        work = works.get(entry["doi"])
        if not work:
            continue
        entry["relevance"] = round(scores[entry["pmcid"]], 3)
        entry["openalex_id"] = short_oa(work["id"])
        entry["pre_cutoff_citations"] = pre_cutoff_citations(work, case["publication_date"])
        entry["cited_by_count_now"] = int(work.get("cited_by_count") or 0)
        entry.pop("abstract", None)
        ranked.append(entry)
    ranked.sort(key=lambda e: (-e["pre_cutoff_citations"], -e["relevance"], e["pmcid"]))
    payload = {"paper_id": case["paper_id"], "cutoff": case["publication_date"], "phrases": phrases,
               "candidates": len(candidates), "relevant_pool": len(relevant), "with_openalex": len(ranked),
               "ranked": ranked}
    atomic_json(case_dir(case["paper_id"]) / "seed_candidates.json", payload)
    return payload


# ---------------------------------------------------------------- full text and parsing

def fetch_xml(pmcid: str) -> str | None:
    path = PAPERS / pmcid / "paper.xml"
    if path.exists():
        return path.read_text()
    try:
        text = _get(f"{EPMC}/{pmcid}/fullTextXML", raw=True, timeout=120)
    except RuntimeError as error:
        # A full text the server keeps failing to deliver (persistent 5xx after retries) counts as unavailable, like a
        # 404: the paper is skipped by the same rule as papers without open full text.
        print(f"[citegraph] full text unavailable, skipped: {pmcid} ({error})", flush=True)
        return None
    if not text or "<body" not in text:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return text


def _text(element: ET.Element | None) -> str:
    return re.sub(r"\s+", " ", "".join(element.itertext())).strip() if element is not None else ""


SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[])")
ABBREVIATIONS = re.compile(r"\b(et al|Fig|Figs|Eq|Eqs|Ref|Refs|i\.e|e\.g|vs|approx|ca|No|Tab)\.$", re.IGNORECASE)


def split_sentences(text: str) -> list[str]:
    parts = SENTENCE_SPLIT.split(text)
    merged: list[str] = []
    for part in parts:
        if merged and ABBREVIATIONS.search(merged[-1]):
            merged[-1] = f"{merged[-1]} {part}"
        else:
            merged.append(part)
    return [p.strip() for p in merged if p.strip()]


def paragraph_with_markers(p: ET.Element, rid_order: dict[str, int]) -> str:
    """Render a <p> with bibr xrefs replaced by ⟦rid⟧ tokens; expand numeric ranges like [3–6]."""
    out: list[str] = []
    last_rid: str | None = None

    def walk(node: ET.Element) -> None:
        nonlocal last_rid
        if node.tag == "xref" and node.get("ref-type") == "bibr":
            rids = (node.get("rid") or "").split()
            for rid in rids:
                if last_rid and out and re.fullmatch(r"\s*[–-]\s*", out[-1] or "") and rid in rid_order \
                        and last_rid in rid_order:
                    out.pop()
                    lo, hi = rid_order[last_rid], rid_order[rid]
                    between = [r for r, i in rid_order.items() if lo < i < hi]
                    out.extend(f"⟦{r}⟧" for r in between)
                out.append(f"⟦{rid}⟧")
                last_rid = rid
            if node.tail:
                out.append(node.tail)
            return
        if node.tag in ("table-wrap", "fig", "disp-formula", "table"):
            if node.tail:
                out.append(node.tail)
            return
        if node.text:
            out.append(node.text)
        for child in node:
            walk(child)
        if node.tail and node is not p:
            out.append(node.tail)

    walk(p)
    return re.sub(r"\s+", " ", "".join(out)).strip()


XLINK = "{http://www.w3.org/1999/xlink}href"
SKIP_ANCESTORS = {"ref-list", "fn-group", "table-wrap", "fig", "back", "ack", "app-group", "glossary"}


def _ref_ids(ref: ET.Element) -> dict[str, str]:
    ids = {"doi": "", "pmid": "", "pmcid": ""}
    for element in ref.iter():
        kind, value = "", ""
        if element.tag == "pub-id":
            kind, value = element.get("pub-id-type", ""), element.text or ""
        elif element.tag == "ext-link":
            kind, value = element.get("ext-link-type", ""), element.get(XLINK) or element.text or ""
        kind = kind.lower()
        if kind in ids and value.strip() and not ids[kind]:
            ids[kind] = norm_doi(value) if kind == "doi" else value.strip()
    return ids


def parse_jats(pmcid: str, xml: str) -> dict[str, Any]:
    root = ET.fromstring(xml)
    parent = {child: node for node in root.iter() for child in node}

    def excluded(element: ET.Element) -> bool:
        node = parent.get(element)
        while node is not None:
            if node.tag in SKIP_ANCESTORS or node.tag == "p" or (node.tag == "sec" and "ref" in (node.get("sec-type") or "")):
                return True
            node = parent.get(node)
        return False

    title = _text(root.find(".//article-meta/title-group/article-title"))
    abstract = " ".join(_text(a) for a in root.findall(".//article-meta/abstract"))
    refs = []
    rid_order: dict[str, int] = {}
    for index, ref in enumerate(root.iter("ref")):
        rid = ref.get("id") or f"ref{index}"
        rid_order[rid] = index
        raw = _text(ref)
        ids = _ref_ids(ref)
        if not ids["doi"]:
            match = re.search(r"10\.\d{4,9}/[^\s\"<>]+", raw)
            ids["doi"] = norm_doi(match.group(0).rstrip(".,;)")) if match else ""
        refs.append({"rid": rid, "label": _text(ref.find("label")), **ids,
                     "title": _text(ref.find(".//article-title")), "year": _text(ref.find(".//year"))[:4],
                     "raw": raw[:400]})
    body = root.find(".//body")
    sections: list[str] = []
    contexts: list[dict[str, Any]] = []
    if body is not None:
        for element in body.iter():
            if element.tag == "title" and parent.get(element) is not None and parent[element].tag == "sec" \
                    and not excluded(parent[element]) and "ref" not in (parent[element].get("sec-type") or ""):
                sections.append(f"\n{_text(element)}\n")
            if element.tag != "p" or excluded(element):
                continue
            rendered = paragraph_with_markers(element, rid_order)
            sections.append(re.sub(r"⟦[^⟧]+⟧", "", rendered))
            sentences = split_sentences(rendered)
            for s_index, sentence in enumerate(sentences):
                rids = [r for r in dict.fromkeys(re.findall(r"⟦([^⟧]+)⟧", sentence)) if r in rid_order]
                if not rids:
                    continue
                previous = sentences[s_index - 1] if s_index else ""
                contexts.append({"rids": rids, "sentence": sentence, "previous": previous})
    body_text = re.sub(r"\n{3,}", "\n\n", "\n".join(sections)).strip()
    return {"pmcid": pmcid, "title": title, "abstract": abstract, "text": f"{title}\n\nAbstract\n{abstract}\n\n{body_text}",
            "refs": refs, "contexts": contexts}


def resolve_refs(parsed: dict[str, Any], doi: str) -> dict[str, Any]:
    """Map each reference to an OpenAlex work using the paper's OpenAlex reference list."""
    work = openalex_by_dois([doi]).get(norm_doi(doi)) if doi else None
    referenced = [short_oa(w) for w in (work or {}).get("referenced_works", [])]
    meta = openalex_by_ids(referenced) if referenced else {}
    by_doi = {norm_doi(w.get("doi")): wid for wid, w in meta.items() if w.get("doi")}
    by_pmid = {str(w.get("ids", {}).get("pmid", "")).rsplit("/", 1)[-1]: wid for wid, w in meta.items()
               if w.get("ids", {}).get("pmid")}
    by_title = [(wid, title_tokens(w.get("display_name") or "")) for wid, w in meta.items()]
    resolved = {}
    method = Counter()
    for ref in parsed["refs"]:
        wid = by_doi.get(ref["doi"]) if ref["doi"] else None
        how = "doi" if wid else ""
        if not wid and ref["pmid"]:
            wid = by_pmid.get(ref["pmid"])
            how = "pmid" if wid else ""
        if not wid:
            ref_tokens = title_tokens(ref["title"]) if ref["title"] else title_tokens(ref["raw"])
            best, score = None, 0.0
            for candidate, tokens in by_title:
                if not tokens:
                    continue
                value = jaccard(ref_tokens, tokens) if ref["title"] else len(tokens & ref_tokens) / len(tokens)
                if value > score:
                    best, score = candidate, value
            threshold = TITLE_MATCH if ref["title"] else 0.85
            if best and score >= threshold:
                wid, how = best, "title"
        if wid:
            resolved[ref["rid"]] = wid
        method[how or "unresolved"] += 1
    return {"openalex_id": short_oa(work["id"]) if work else "", "publication_date": (work or {}).get("publication_date"),
            "resolved": resolved, "resolution": dict(method),
            "ref_works": {wid: {"title": w.get("display_name"), "doi": norm_doi(w.get("doi")),
                                "publication_date": w.get("publication_date"), "type": w.get("type"),
                                "cited_by_count": w.get("cited_by_count"), "counts_by_year": w.get("counts_by_year", [])}
                          for wid, w in meta.items()}}


def prepare_paper(pmcid: str, doi: str) -> dict[str, Any] | None:
    """Fetch, parse and resolve one full-text paper (cached)."""
    path = PAPERS / pmcid / "parsed.json"
    if path.exists():
        return _read_json(path)
    xml = fetch_xml(pmcid)
    if xml is None:
        return None
    try:
        parsed = parse_jats(pmcid, xml)
    except ET.ParseError:
        return None
    parsed.update(resolve_refs(parsed, doi))
    parsed["doi"] = norm_doi(doi)
    atomic_json(path, parsed)
    return parsed


def select_seeds(case: dict[str, Any]) -> list[dict[str, Any]]:
    path = case_dir(case["paper_id"]) / "seeds.json"
    if path.exists():
        return _read_json(path)["seeds"]
    ranked = seeds_for_case(case)["ranked"]
    seeds = []
    for entry in ranked:
        parsed = prepare_paper(entry["pmcid"], entry["doi"])
        if parsed is None or not parsed.get("openalex_id") or len(parsed["contexts"]) < 3:
            continue
        seeds.append({**entry, "openalex_id": parsed["openalex_id"]})
        if len(seeds) == N_SEEDS:
            break
    atomic_json(path, {"paper_id": case["paper_id"], "seeds": seeds})
    return seeds


# ---------------------------------------------------------------- stage: expansion

def query_relevance(query_tokens: set[str], title: str) -> float:
    tokens = title_tokens(title)
    return len(tokens & query_tokens) / math.sqrt(max(1, len(tokens)))


def select_expansion(case: dict[str, Any]) -> list[dict[str, Any]]:
    path = case_dir(case["paper_id"]) / "expansion.json"
    if path.exists():
        return _read_json(path)["expansion"]
    seeds = select_seeds(case)
    exclusion = target_exclusion(case)
    query_tokens = title_tokens(graph_query(case) + " " + " ".join(keywords(case)))
    seed_ids = {s["openalex_id"] for s in seeds}
    parsed = {s["pmcid"]: _read_json(PAPERS / s["pmcid"] / "parsed.json") for s in seeds}
    cocitation: Counter[str] = Counter()
    info: dict[str, dict[str, Any]] = {}
    for p in parsed.values():
        for wid, w in p["ref_works"].items():
            cocitation[wid] += 1
            info[wid] = w
    eligible = {wid: w for wid, w in info.items()
                if wid not in seed_ids and (w.get("publication_date") or "9999") < case["publication_date"]
                and not is_excluded(exclusion, w.get("doi", ""), "", w.get("title") or "")}
    oa = epmc_oa_by_dois([w["doi"] for w in eligible.values() if w.get("doi")])
    chosen: list[dict[str, Any]] = []
    taken: set[str] = set()
    skipped_no_fulltext = 0
    for seed in seeds:
        refs = [wid for wid in parsed[seed["pmcid"]]["ref_works"] if wid in eligible
                and query_relevance(query_tokens, eligible[wid].get("title") or "") >= MIN_EXPANSION_RELEVANCE]
        refs.sort(key=lambda wid: (-cocitation[wid], -query_relevance(query_tokens, eligible[wid].get("title") or ""),
                                   -pre_cutoff_citations(eligible[wid], case["publication_date"]), wid))
        picked = 0
        for wid in refs:
            if wid in taken:
                continue
            record = oa.get(eligible[wid].get("doi") or "")
            if not record or record.get("firstPublicationDate", "9999") >= case["publication_date"] \
                    or is_excluded(exclusion, record.get("doi", ""), record.get("pmcid", ""), record.get("title", "")):
                skipped_no_fulltext += 1
                continue
            paper = prepare_paper(record["pmcid"], record["doi"])
            if paper is None or not paper.get("openalex_id"):
                skipped_no_fulltext += 1
                continue
            chosen.append({"pmcid": record["pmcid"], "doi": norm_doi(record["doi"]), "openalex_id": wid,
                           "title": eligible[wid].get("title"), "from_seed": seed["openalex_id"],
                           "cocitation": cocitation[wid],
                           "relevance": round(query_relevance(query_tokens, eligible[wid].get("title") or ""), 3),
                           "pre_cutoff_citations": pre_cutoff_citations(eligible[wid], case["publication_date"]),
                           "first_date": record.get("firstPublicationDate")})
            taken.add(wid)
            picked += 1
            if picked == K_PER_SEED:
                break
    atomic_json(path, {"paper_id": case["paper_id"], "expansion": chosen, "references_considered": len(eligible),
                       "with_open_fulltext": len(oa), "skipped_without_fulltext": skipped_no_fulltext})
    return chosen


def acquire(case_ids: list[str] | None) -> dict[str, Any]:
    summary = {}
    for case in rx.cases().values():
        if case_ids and case["paper_id"] not in case_ids:
            continue
        seeds = select_seeds(case)
        expansion = select_expansion(case)
        summary[case["paper_id"]] = {"seeds": len(seeds), "expansion": len(expansion)}
        print(f"[citegraph] {case['paper_id']}: seeds {len(seeds)}, expansion {len(expansion)}", flush=True)
    return summary


# ---------------------------------------------------------------- stage: extraction (cards and citation contexts)

def full_text_papers(case_ids: list[str] | None = None) -> dict[str, dict[str, Any]]:
    """Every seed and expansion paper of every case (pmcid -> first entry seen)."""
    papers: dict[str, dict[str, Any]] = {}
    for case in rx.cases().values():
        if case_ids and case["paper_id"] not in case_ids:
            continue
        for name in ("seeds", "expansion"):
            path = case_dir(case["paper_id"]) / f"{name}.json"
            if path.exists():
                for entry in _read_json(path)[name]:
                    papers.setdefault(entry["pmcid"], entry)
    return papers


def extract_card(pmcid: str) -> None:
    parsed = _read_json(PAPERS / pmcid / "parsed.json")
    parts = rx.windows(parsed["text"])[:CARD_WINDOWS]
    records, stats = [], Counter()
    for index, window in enumerate(parts, 1):
        found, window_stats = rx.extract_window("card", pmcid, parsed["title"], window, f"{index}/{len(parts)}")
        stats.update(window_stats)
        for item in found:
            records.append({"item": item, "text": rx.render("card", item)})
    atomic_json(PAPERS / pmcid / "card.json", {"pmcid": pmcid, "extractor": _generator_identity(),
                                               "windows": len(parts), "stats": dict(stats), "records": records})


def marker_text(text: str, labels: dict[str, str]) -> str:
    text = re.sub(r"⟦([^⟧]+)⟧", lambda m: f"[{labels[m.group(1)]}]" if m.group(1) in labels else "", text)
    text = re.sub(r"\[\s*((?:\[R\d+\][\s,;–-]*)+)\]", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_sentence(text: str) -> str:
    text = re.sub(r"⟦[^⟧]+⟧", "", text)
    text = re.sub(r"\[\s*[,;–-]*\s*\]|\(\s*[,;–-]*\s*\)", "", text)
    return re.sub(r"\s+", " ", text).strip()


def usable_contexts(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    keep = [c for c in parsed["contexts"]
            if len(c["rids"]) <= MAX_REFS_PER_CONTEXT and any(r in parsed["resolved"] for r in c["rids"])]
    if len(keep) > MAX_CONTEXTS_PER_PAPER:
        step = len(keep) / MAX_CONTEXTS_PER_PAPER
        keep = [keep[int(i * step)] for i in range(MAX_CONTEXTS_PER_PAPER)]
    return keep


def grounding(attributed: str, source: str) -> float:
    terms = set(content_terms(attributed))
    return len(terms & set(content_terms(source))) / len(terms) if terms else 0.0


def marker_label(ref: Any, info: dict[str, Any]) -> str | None:
    """The marker label a statement refers to. Some extractors (Llama-3.3) copy the marker's text, the cited title and
    year, instead of its label; such a ref is mapped back to the label whose text it matches."""
    label = str(ref or "").strip("[] ")
    if label in info["labels"]:
        return label
    wanted = rx.normalise(label)
    matches = [lab for lab, text in info["markers"].items() if wanted and rx.normalise(text) == wanted]
    return matches[0] if len(matches) == 1 else None


def extract_contexts(pmcid: str) -> None:
    parsed = _read_json(PAPERS / pmcid / "parsed.json")
    refs = {r["rid"]: r for r in parsed["refs"]}
    contexts = usable_contexts(parsed)
    statements, stats = [], Counter(contexts=len(contexts), skipped_wide=sum(
        1 for c in parsed["contexts"] if len(c["rids"]) > MAX_REFS_PER_CONTEXT))
    for start in range(0, len(contexts), CONTEXT_BATCH):
        batch = contexts[start:start + CONTEXT_BATCH]
        items, meta = [], {}
        for offset, ctx in enumerate(batch):
            ctx_id = f"c{start + offset}"
            resolved = [r for r in ctx["rids"] if r in parsed["resolved"]]
            labels = {rid: f"R{i + 1}" for i, rid in enumerate(resolved)}
            markers = {}
            for rid, label in labels.items():
                work = parsed["ref_works"].get(parsed["resolved"][rid], {})
                markers[label] = f"{work.get('title') or refs[rid]['title'] or refs[rid]['raw'][:160]} " \
                                 f"({str(work.get('publication_date') or refs[rid]['year'])[:4]})"
            items.append({"ctx": ctx_id, "previous_sentence": marker_text(ctx["previous"], {}),
                          "sentence": marker_text(ctx["sentence"], labels), "markers": markers})
            meta[ctx_id] = {"labels": {v: k for k, v in labels.items()}, "markers": markers,
                            "source": clean_sentence(ctx["previous"]) + " " + clean_sentence(ctx["sentence"]),
                            "sentence": clean_sentence(ctx["sentence"])}
        user = json.dumps({"citing_paper_title": parsed["title"], "sentences": items}, ensure_ascii=False)
        raw = lc.chat_json(CONTEXT_SYSTEM, user, max_tokens=CONTEXT_MAX_TOKENS, retries=3)
        found = raw.get("statements", []) if isinstance(raw, dict) else []
        stats["proposed"] += len(found) if isinstance(found, list) else 0
        for st in found if isinstance(found, list) else []:
            if not isinstance(st, dict) or st.get("ctx") not in meta:
                stats["malformed"] += 1
                continue
            info = meta[st["ctx"]]
            label = marker_label(st.get("ref"), info)
            rid = info["labels"].get(label) if label else None
            relation = str(st.get("relation", "")).strip().lower()
            attributed = str(st.get("attributed", "")).strip()
            if rid is None or relation not in RELATIONS:
                stats["malformed"] += 1
                continue
            if relation == "background" or not attributed:
                stats["background"] += 1
                continue
            score = grounding(attributed, info["source"] + " " + info["markers"][label])
            if score < MIN_GROUNDING:
                stats["ungrounded"] += 1
                continue
            stats["kept"] += 1
            statements.append({"ctx": st["ctx"], "rid": rid, "cited": parsed["resolved"][rid], "relation": relation,
                               "attributed": attributed[:500],
                               "cited_system": str(st.get("cited_system", "not stated"))[:200],
                               "applied_to": str(st.get("applied_to", "not stated"))[:200],
                               "numbers": str(st.get("numbers", ""))[:200], "quote": info["sentence"][:600],
                               "grounding": round(score, 3)})
    atomic_json(PAPERS / pmcid / "contexts.json", {"pmcid": pmcid, "extractor": _generator_identity(),
                                                   "stats": dict(stats), "statements": statements})


def extract_stage(workers: int, resume: bool, case_ids: list[str] | None = None) -> dict[str, int]:
    papers = sorted(full_text_papers(case_ids))
    jobs = [(f"card__{p}", (p,)) for p in papers if not (resume and (PAPERS / p / "card.json").exists())]
    jobs += [(f"contexts__{p}", (p,)) for p in papers if not (resume and (PAPERS / p / "contexts.json").exists())]

    def job(pmcid: str, kind: str) -> None:
        if resume and (PAPERS / pmcid / f"{'card' if kind == 'card' else 'contexts'}.json").exists():
            return
        (extract_card if kind == "card" else extract_contexts)(pmcid)

    return run_jobs("extract", [(name, (args[0], name.split("__")[0])) for name, args in jobs], job, workers)


# ---------------------------------------------------------------- stage: graph

def build_graph(case: dict[str, Any]) -> dict[str, Any]:
    cutoff = case["publication_date"]
    exclusion = target_exclusion(case)
    seeds = _read_json(case_dir(case["paper_id"]) / "seeds.json")["seeds"]
    expansion = _read_json(case_dir(case["paper_id"]) / "expansion.json")["expansion"]
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[tuple[str, str]] = []
    dropped = Counter()

    def node(wid: str, **fields: Any) -> dict[str, Any]:
        entry = nodes.setdefault(wid, {"id": wid, "roles": [], "card": [], "statements": [], "references": [],
                                       "pmcid": "", "title": "", "doi": "", "publication_date": "",
                                       "pre_cutoff_citations": 0})
        for key, value in fields.items():
            if value and not entry.get(key):
                entry[key] = value
        return entry

    full = [(s, "seed") for s in seeds] + [(e, "expansion") for e in expansion]
    for entry, role in full:
        parsed = _read_json(PAPERS / entry["pmcid"] / "parsed.json")
        wid = entry["openalex_id"]
        n = node(wid, pmcid=entry["pmcid"], title=parsed["title"] or entry.get("title"), doi=entry["doi"],
                 publication_date=entry.get("first_date"), pre_cutoff_citations=entry.get("pre_cutoff_citations", 0))
        if role not in n["roles"]:
            n["roles"].append(role)
        card_path = PAPERS / entry["pmcid"] / "card.json"
        if card_path.exists() and not n["card"]:
            n["card"] = [r["text"] for r in _read_json(card_path)["records"]]
        for ref_wid, work in parsed["ref_works"].items():
            date = work.get("publication_date") or "9999"
            if date >= cutoff or is_excluded(exclusion, work.get("doi", ""), "", work.get("title") or ""):
                dropped["reference_after_cutoff_or_target"] += 1
                continue
            ref = node(ref_wid, title=work.get("title"), doi=work.get("doi"), publication_date=date,
                       pre_cutoff_citations=pre_cutoff_citations(work, cutoff))
            if "reference" not in ref["roles"] and not ref["roles"]:
                ref["roles"].append("reference")
            if ref_wid not in n["references"]:
                n["references"].append(ref_wid)
                edges.append((wid, ref_wid))
        ctx_path = PAPERS / entry["pmcid"] / "contexts.json"
        if ctx_path.exists():
            for st in _read_json(ctx_path)["statements"]:
                if st["cited"] not in nodes or st["cited"] == wid:
                    dropped["statement_about_dropped_node"] += 1
                    continue
                nodes[st["cited"]]["statements"].append({**st, "citer": wid, "citer_title": n["title"],
                                                         "citer_date": n["publication_date"]})
    for n in nodes.values():
        seen = set()
        unique = []
        for st in n["statements"]:
            key = (st["citer"], rx.normalise(st["attributed"]))
            if key not in seen:
                seen.add(key)
                unique.append(st)
        n["statements"] = unique
        n["citers"] = sorted({st["citer"] for st in n["statements"]})
    graph = {"paper_id": case["paper_id"], "cutoff": cutoff, "nodes": nodes, "edges": edges,
             "stats": {"nodes": len(nodes), "full_text_nodes": sum(bool(n["pmcid"]) for n in nodes.values()),
                       "seeds": len(seeds), "expansion": len(expansion), "edges": len(edges),
                       "nodes_with_statements": sum(bool(n["statements"]) for n in nodes.values()),
                       "statements": sum(len(n["statements"]) for n in nodes.values()),
                       "nodes_with_2plus_citers": sum(len(n["citers"]) >= 2 for n in nodes.values()),
                       "contradicting_statements": sum(st["relation"] == "contradicts" for n in nodes.values()
                                                       for st in n["statements"]),
                       "dropped": dict(dropped)}}
    atomic_json(case_dir(case["paper_id"]) / "graph.json", graph)
    return graph


def graph_stage(case_ids: list[str] | None = None) -> dict[str, Any]:
    return {c["paper_id"]: build_graph(c)["stats"] for c in rx.cases().values()
            if not case_ids or c["paper_id"] in case_ids}


def load_graph(paper_id: str) -> dict[str, Any]:
    key = f"graph_{paper_id}"
    if key not in _cache:
        _cache[key] = _read_json(case_dir(paper_id) / "graph.json")
    return _cache[key]


_cache: dict[str, Any] = {}


# ---------------------------------------------------------------- evidence records per variant

from improvement_eval import SYSTEMMATCH_SYSTEM, generate_validated  # noqa: E402
from stage_metrics import AUDIT_SYSTEM, CROSS_JUDGE, HEDGE, _validated_audit, assert_target_free  # noqa: E402
from temporal_eval_v3 import (  # noqa: E402
    BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED, CITED_TEXT_CHARS, HYPOTHESIS_FIELDS, MAX_MODEL_TURNS, MAX_TOOL_CALLS,
    PAGE_CHARS, PRIMARY_DIMENSIONS, _blind_candidate, call_local_with_tools, cluster_bootstrap, exact_sign_test,
    holm_adjust, judge_absolute,
)
from temporal_hypothesis_benchmark import (  # noqa: E402
    _SCORE_SYSTEM, RetrievalRecord, _tokens, _validate_generation, _validate_score, compact_evidence_payload,
    generate_with_citation_repair, retrieve,
)

VARIANTS = ("graph_selection", "graph_profiles", "graph_profiles_systemmatch", "corroboration_weighted",
            "graph_tool_agent")
BASELINES = {"closed_book": rx.OUT, "text_chunks": rx.OUT, "card": rx.OUT,
             "card_systemmatch": RUN_ROOT / "improvements"}
PRIMARY_BASELINE = "text_chunks"
PROFILE_CAP = rx.RECORD_MAX_CHARS_BY_ARM["card"]
STATEMENTS_IN_PROFILE = 8
CORROBORATION_NOTE = (
    "Each evidence record is one paper node from a citation graph: the paper's own digest when its full text was "
    "read, followed by what later papers (all before the cutoff) say about it. Records are ordered by relevance "
    "and by how many independent papers corroborate them; statements labelled contradicts report disagreement."
)
GRAPH_TOOL_SYSTEM = (
    "You are a materials-science hypothesis agent in a leakage-audited chronological benchmark. You explore a "
    "citation graph of papers published before the knowledge cutoff; nodes are papers, and a node's profile holds "
    "the paper's own digest (when its full text was read) and what citing papers say about it. Tools: search_nodes "
    "finds relevant nodes; read_node reads a node profile; who_cites lists what citing papers say about a node; "
    "references lists the papers a node cites; path finds how two nodes are connected. Read every node you will "
    "cite with read_node, then call submit_hypothesis exactly once. You have at most {max_calls} tool calls. Cite "
    "node IDs exactly as returned and only after reading them. Use a mechanism from a node only if its alloy system "
    "and conditions transfer to the query's system. The hypothesis object must contain: {fields}."
)


def short_title(title: str, words: int = 10) -> str:
    parts = re.sub(r"<[^>]+>", "", str(title or "")).split()
    return " ".join(parts[:words]) + (" ..." if len(parts) > words else "")


def ordered_statements(node: dict[str, Any]) -> list[dict[str, Any]]:
    order = {"contradicts": 0, "supports": 1, "finding": 2, "extends": 3, "compares": 4, "method": 5}
    return sorted(node["statements"], key=lambda s: (order.get(s["relation"], 9), -s["grounding"], s["citer"],
                                                     s["ctx"]))


def profile_text(node: dict[str, Any], *, statements: int = STATEMENTS_IN_PROFILE, corroboration: bool = False,
                 card_chars: int = 1500) -> str:
    year = str(node.get("publication_date") or "")[:4]
    head = (f"Paper node: {re.sub(r'<[^>]+>', '', str(node.get('title') or 'untitled'))} ({year}). "
            f"Cited {node.get('pre_cutoff_citations', 0)} times before the cutoff; "
            f"{len(node.get('citers', []))} papers in this graph say something specific about it.")
    parts = [head]
    if corroboration:
        relations = Counter(s["relation"] for s in node["statements"])
        parts.append(f"Corroboration: {len(node.get('citers', []))} independent citing papers; "
                     f"{relations.get('supports', 0)} supporting, {relations.get('contradicts', 0)} contradicting, "
                     f"{relations.get('extends', 0)} extending statements.")
    if node.get("card"):
        card = " ".join(node["card"])
        parts.append("Own digest: " + (card[:card_chars].rsplit(" ", 1)[0] + " ..." if len(card) > card_chars
                                       else card))
    chosen = ordered_statements(node)[:statements]
    if chosen:
        parts.append("What citing papers say about it:")
        for st in chosen:
            extra = "; ".join(x for x in (
                f"system {st['cited_system']}" if st["cited_system"] not in ("", "not stated") else "",
                f"applied to {st['applied_to']}" if st["applied_to"] not in ("", "not stated") else "",
                f"values {st['numbers']}" if st["numbers"] else "") if x)
            parts.append(f"- {st['relation']} (from \"{short_title(st['citer_title'], 8)}\", "
                         f"{str(st['citer_date'])[:4]}): {st['attributed']}" + (f" [{extra}]" if extra else ""))
    return "\n".join(parts)


def node_date(node: dict[str, Any], cutoff: str) -> str:
    dates = [str(node.get("publication_date") or "")] + [str(s["citer_date"]) for s in node["statements"]]
    dates = [d for d in dates if d]
    return max(dates) if dates else cutoff


def node_record(node: dict[str, Any], graph: dict[str, Any], text: str) -> RetrievalRecord:
    return RetrievalRecord(f"node::{node['id']}", node["pmcid"] or node["id"], node_date(node, graph["cutoff"]),
                           "graph_node", text, {"doi": node.get("doi", ""), "citers": len(node.get("citers", []))})


def selection_pool(graph: dict[str, Any]) -> list[RetrievalRecord]:
    pool = []
    for node in graph["nodes"].values():
        for index, text in enumerate(node["card"]):
            pool.append(RetrievalRecord(f"{node['pmcid']}::card::{index}", node["pmcid"],
                                        str(node["publication_date"]), "graph_card", text, {"doi": node["doi"]}))
    return pool


def profile_pool(graph: dict[str, Any], corroboration: bool = False) -> list[RetrievalRecord]:
    return [node_record(n, graph, profile_text(n, corroboration=corroboration)) for n in graph["nodes"].values()
            if n["card"] or n["statements"]]


def lexical_score(query: str, text: str) -> float:
    """The score that temporal_hypothesis_benchmark.retrieve ranks by."""
    q = Counter(_tokens(query))
    d = Counter(_tokens(text))
    overlap = sum(min(c, d[t]) for t, c in q.items())
    if not overlap or not q:
        return 0.0
    return 2 * overlap / sum(q.values()) + overlap / math.sqrt(max(sum(d.values()), 1))


def pack_ranked(ranked: list[RetrievalRecord], cap: int) -> list[RetrievalRecord]:
    packed, used = [], 0
    for record in ranked:
        size = min(len(record.text), cap)
        if used + size > rx.EVIDENCE_BUDGET_CHARS:
            continue
        packed.append(record)
        used += size
        if len(packed) >= rx.MAX_RECORDS or used >= rx.EVIDENCE_BUDGET_CHARS - 200:
            break
    return packed


def corroboration_rank(query: str, pool: list[RetrievalRecord]) -> list[RetrievalRecord]:
    scored = [(lexical_score(query, r.text) * (1 + math.log1p(r.structured.get("citers", 0))), r) for r in pool]
    scored = [(s, r) for s, r in scored if s > 0]
    scored.sort(key=lambda x: (-x[0], x[1].publication_date, x[1].record_id))
    return [r for _, r in scored]


def graph_leakage(records: list[RetrievalRecord], case: dict[str, Any]) -> dict[str, int]:
    exclusion = target_exclusion(case)
    audit = rx.leakage_audit(records, case)
    audit["target_doi_or_title_leaks"] = sum(is_excluded(exclusion, r.structured.get("doi", ""), r.paper_id, "")
                                             for r in records)
    return audit


# ---------------------------------------------------------------- graph tool agent

class GraphTools:
    def __init__(self, graph: dict[str, Any]):
        self.graph = graph
        self.nodes = graph["nodes"]
        self.records = {f"node::{wid}": node_record(n, graph, profile_text(n, statements=40, card_chars=4000))
                        for wid, n in self.nodes.items() if n["card"] or n["statements"]}
        self.read_ids: set[str] = set()
        self.cited_by: dict[str, set[str]] = defaultdict(set)
        for a, b in graph["edges"]:
            self.cited_by[b].add(a)

    def _wid(self, node_id: str) -> str:
        return str(node_id).replace("node::", "").strip()

    def _brief(self, wid: str) -> dict[str, Any]:
        n = self.nodes[wid]
        return {"node_id": f"node::{wid}", "title": short_title(n["title"], 16),
                "year": str(n["publication_date"])[:4], "has_digest": bool(n["card"]),
                "statements_about_it": len(n["statements"]), "citing_papers": len(n.get("citers", []))}

    def search_nodes(self, query: str, k: Any = 6) -> dict[str, Any]:
        try:
            limit = max(1, min(int(k), 8))
        except (TypeError, ValueError):
            limit = 6
        hits = retrieve(query, list(self.records.values()), limit=limit)
        return {"query": query, "results": [{**self._brief(self._wid(r.record_id)),
                                             "snippet": r.text[:280]} for r in hits],
                "note": "" if hits else "no matches; try different terms"}

    def read_node(self, node_id: str, offset: Any = 0) -> dict[str, Any]:
        rid = f"node::{self._wid(node_id)}"
        record = self.records.get(rid)
        if record is None:
            return {"error": f"unknown or empty node {node_id!r}; use search_nodes"}
        try:
            start = max(0, int(offset))
        except (TypeError, ValueError):
            start = 0
        self.read_ids.add(rid)
        end = start + PAGE_CHARS
        return {"node_id": rid, "publication_date": record.publication_date, "offset": start,
                "text": record.text[start:end], "next_offset": end if end < len(record.text) else None}

    def who_cites(self, node_id: str) -> dict[str, Any]:
        wid = self._wid(node_id)
        if wid not in self.nodes:
            return {"error": f"unknown node {node_id!r}"}
        n = self.nodes[wid]
        return {"node_id": f"node::{wid}", "statements": [
            {"citer": f"node::{s['citer']}", "citer_title": short_title(s["citer_title"], 12),
             "relation": s["relation"], "says": s["attributed"][:300]} for s in ordered_statements(n)[:15]],
            "other_citing_nodes": [f"node::{c}" for c in sorted(self.cited_by[wid] - set(n.get("citers", [])))][:10]}

    def references(self, node_id: str) -> dict[str, Any]:
        wid = self._wid(node_id)
        if wid not in self.nodes:
            return {"error": f"unknown node {node_id!r}"}
        refs = [r for r in self.nodes[wid]["references"] if r in self.nodes]
        refs.sort(key=lambda r: (-len(self.nodes[r]["statements"]), -int(self.nodes[r]["pre_cutoff_citations"] or 0)))
        return {"node_id": f"node::{wid}", "references": [self._brief(r) for r in refs[:15]],
                "total_references": len(refs)}

    def path(self, source: str, target: str) -> dict[str, Any]:
        a, b = self._wid(source), self._wid(target)
        if a not in self.nodes or b not in self.nodes:
            return {"error": "unknown node"}
        neighbours: dict[str, set[str]] = defaultdict(set)
        for x, y in self.graph["edges"]:
            neighbours[x].add(y)
            neighbours[y].add(x)
        previous, frontier = {a: None}, [a]
        while frontier and b not in previous:
            nxt = []
            for x in frontier:
                for y in sorted(neighbours[x]):
                    if y not in previous:
                        previous[y] = x
                        nxt.append(y)
            frontier = nxt
        if b not in previous:
            return {"path": [], "note": "not connected"}
        chain, x = [], b
        while x is not None:
            chain.append(self._brief(x))
            x = previous[x]
        return {"path": list(reversed(chain))}


GRAPH_TOOLS = [
    {"type": "function", "function": {"name": "search_nodes", "description": "Find relevant paper nodes by text.",
     "parameters": {"type": "object", "properties": {"query": {"type": "string"},
                                                     "k": {"type": "integer", "minimum": 1, "maximum": 8}},
                    "required": ["query"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "read_node", "description": (
        "Read a node profile (about 2400 characters per page; next_offset is null when finished). A node can be "
        "cited only after it has been read."),
     "parameters": {"type": "object", "properties": {"node_id": {"type": "string"},
                                                     "offset": {"type": "integer", "minimum": 0}},
                    "required": ["node_id"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "who_cites", "description": "What citing papers say about a node.",
     "parameters": {"type": "object", "properties": {"node_id": {"type": "string"}}, "required": ["node_id"],
                    "additionalProperties": False}}},
    {"type": "function", "function": {"name": "references", "description": "Papers a node cites that are in the graph.",
     "parameters": {"type": "object", "properties": {"node_id": {"type": "string"}}, "required": ["node_id"],
                    "additionalProperties": False}}},
    {"type": "function", "function": {"name": "path", "description": "Shortest citation path between two nodes.",
     "parameters": {"type": "object", "properties": {"source": {"type": "string"}, "target": {"type": "string"}},
                    "required": ["source", "target"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "submit_hypothesis", "description": (
        "Submit the final hypothesis as one JSON object with the requested fields. Call exactly once."),
     "parameters": {"type": "object", "properties": {"hypothesis": {"type": "object"}}, "required": ["hypothesis"],
                    "additionalProperties": False}}},
]


def run_graph_agent(query: str, cutoff: str, tools: GraphTools, call_model: Any = call_local_with_tools
                    ) -> dict[str, Any]:
    trace: list[dict[str, Any]] = []
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": GRAPH_TOOL_SYSTEM.format(max_calls=MAX_TOOL_CALLS,
                                                               fields=", ".join(HYPOTHESIS_FIELDS))},
        {"role": "user", "content": json.dumps({"query": query, "knowledge_cutoff": cutoff}, ensure_ascii=False)},
    ]
    available = GRAPH_TOOLS
    calls_made = 0
    for turn in range(MAX_MODEL_TURNS):
        message = call_model(messages, available)
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
                    validated = _validate_generation(hypothesis, tools.read_ids)
                except ValueError as error:
                    trace.append({"turn": turn, "tool": name, "accepted": False, "error": str(error)})
                    messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(
                        {"accepted": False, "error": str(error),
                         "instruction": "Fix the object and call submit_hypothesis again. Cite only nodes you have read."})})
                    continue
                trace.append({"turn": turn, "tool": name, "accepted": True})
                validated = {**validated, "citation_validation": {"status": "valid", "removed_unknown_ids": []}}
                return {"generation": validated, "trace": trace, "tool_calls": calls_made, "turns": turn + 1}
            if calls_made >= MAX_TOOL_CALLS:
                result: dict[str, Any] = {"error": "tool budget exhausted; call submit_hypothesis"}
            elif not isinstance(args, dict):
                result = {"error": "tool arguments must be a JSON object"}
            elif name == "search_nodes":
                result = tools.search_nodes(str(args.get("query", "")), args.get("k", 6))
            elif name == "read_node":
                result = tools.read_node(str(args.get("node_id", "")), args.get("offset", 0))
            elif name == "who_cites":
                result = tools.who_cites(str(args.get("node_id", "")))
            elif name == "references":
                result = tools.references(str(args.get("node_id", "")))
            elif name == "path":
                result = tools.path(str(args.get("source", "")), str(args.get("target", "")))
            else:
                result = {"error": f"unknown tool {name}"}
            calls_made += 1
            encoded = json.dumps(result, ensure_ascii=False)
            trace.append({"turn": turn, "tool": name, "args": args if isinstance(args, dict) else raw_arguments,
                          "result_chars": len(encoded)})
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": encoded})
            if calls_made >= MAX_TOOL_CALLS:
                available = [GRAPH_TOOLS[-1]]
        if calls_made >= MAX_TOOL_CALLS:
            messages.append({"role": "user", "content": "The tool budget is used up. Call submit_hypothesis now."})
    raise lc.LLMError(f"graph agent submitted no valid hypothesis within {MAX_MODEL_TURNS} turns")


# ---------------------------------------------------------------- stage: generate

def run_id(paper_id: str, level: str, arm: str, sample: int) -> str:
    return rx.run_id(paper_id, level, arm, sample)


def evidence_for(case: dict[str, Any], level: str, arm: str) -> list[RetrievalRecord]:
    graph = load_graph(case["paper_id"])
    query = case["queries"][level]["text"]
    if arm == "graph_selection":
        return rx.pack(query, selection_pool(graph), PROFILE_CAP)
    if arm in ("graph_profiles", "graph_profiles_systemmatch"):
        return rx.pack(query, profile_pool(graph), PROFILE_CAP)
    if arm == "corroboration_weighted":
        return pack_ranked(corroboration_rank(query, profile_pool(graph, corroboration=True)), PROFILE_CAP)
    raise ValueError(f"no packed evidence for {arm}")


def generate_one(case: dict[str, Any], level: str, arm: str, sample: int) -> None:
    query = case["queries"][level]["text"]
    cutoff = case["publication_date"]
    started = time.time()
    status, error, generation, packed, extra = "ok", None, None, [], {}
    try:
        if arm == "graph_tool_agent":
            tools = GraphTools(load_graph(case["paper_id"]))
            result = run_graph_agent(query, cutoff, tools)
            generation = result["generation"]
            packed = [tools.records[rid] for rid in sorted(tools.read_ids)]
            extra = {"trace": result["trace"], "tool_calls": result["tool_calls"], "turns": result["turns"]}
        else:
            packed = evidence_for(case, level, arm)
            evidence = compact_evidence_payload(packed, max_text_chars=PROFILE_CAP)
            payload = {"query": query, "knowledge_cutoff": cutoff, "eligible_evidence": evidence}
            if arm == "graph_profiles_systemmatch":
                generation = generate_validated(SYSTEMMATCH_SYSTEM, payload, {r.record_id for r in packed})
                extra = {"target_system": generation.get("target_system", ""),
                         "evidence_appraisal": generation.get("evidence_appraisal", [])}
            else:
                if arm == "corroboration_weighted":
                    payload["evidence_note"] = CORROBORATION_NOTE
                generation = generate_with_citation_repair(payload, {r.record_id for r in packed})
    except Exception as caught:  # noqa: BLE001 - failed runs are recorded, never dropped
        status, error = "failed", f"{type(caught).__name__}: {caught}"
    lookup = {r.record_id: r for r in packed}
    cited = sorted(set((generation or {}).get("supporting_evidence_ids", [])
                       + (generation or {}).get("conflicting_evidence_ids", [])))
    audit = graph_leakage(packed, case)
    audit["invalid_citations"] = len(set(cited) - set(lookup))
    rid = run_id(case["paper_id"], level, arm, sample)
    atomic_json(OUT / "runs" / f"{rid}.json", {
        "run_id": rid, "paper_id": case["paper_id"], "query_level": level, "arm": arm, "sample": sample,
        "query": query, "publication_date": cutoff, "generator": _generator_identity(), "status": status,
        "error": error, "generation": generation, "packed_ids": [r.record_id for r in packed],
        "packed_chars": sum(min(len(r.text), PROFILE_CAP) for r in packed),
        "packed_papers": len({r.paper_id for r in packed}),
        "packed_with_citer_statements": sum(1 for r in packed if "What citing papers say" in r.text),
        "cited_ids": cited,
        "cited_evidence": [{"record_id": c, "paper_id": lookup[c].paper_id,
                            "publication_date": lookup[c].publication_date, "kind": lookup[c].kind,
                            "text": lookup[c].text[:CITED_TEXT_CHARS]} for c in cited if c in lookup],
        "audit": audit, "elapsed_seconds": round(time.time() - started, 2), **extra,
    })


def generate_stage(workers: int, resume: bool, arms: tuple[str, ...] = VARIANTS,
                   case_ids: list[str] | None = None) -> dict[str, int]:
    jobs = []
    for case in rx.cases().values():
        if case_ids and case["paper_id"] not in case_ids:
            continue
        for level in QUERY_LEVELS:
            for arm in arms:
                for sample in rx.SAMPLES:
                    path = OUT / "runs" / f"{run_id(case['paper_id'], level, arm, sample)}.json"
                    if resume and path.exists() and _read_json(path)["status"] == "ok":
                        continue
                    if path.exists():
                        kept = OUT / "failed_attempts" / path.name
                        kept.parent.mkdir(parents=True, exist_ok=True)
                        kept.write_text(path.read_text())
                    jobs.append((path.stem, (case, level, arm, sample)))
    return run_jobs("generate", jobs, generate_one, workers)


# ---------------------------------------------------------------- stages: judge, cross-judge, audit

def new_runs() -> dict[str, dict[str, Any]]:
    return {p.stem: _read_json(p) for p in sorted((OUT / "runs").glob("PMC*.json"))}


def judge_stage(workers: int, resume: bool) -> dict[str, int]:
    out = OUT / "judgments" / "gpt56"
    jobs = [(rid, (run,)) for rid, run in new_runs().items()
            if run["status"] == "ok" and not (resume and (out / f"{rid}.json").exists())]

    def job(run: dict[str, Any]) -> None:
        atomic_json(out / f"{run['run_id']}.json", judge_absolute(run, rx.cases()[run["paper_id"]]))

    return run_jobs("judge", jobs, job, workers)


def cross_judge_stage(workers: int, resume: bool) -> dict[str, int]:
    out = OUT / "judgments" / "deepseek"
    jobs = [(rid, (run,)) for rid, run in new_runs().items()
            if run["status"] == "ok" and not (resume and (out / f"{rid}.json").exists())]

    def job(run: dict[str, Any]) -> None:
        generation, evidence = _blind_candidate(run)
        payload = {"query": run["query"], "hidden_target": rx.cases()[run["paper_id"]]["hidden_target"],
                   "generated_hypothesis": generation, "cited_evidence": evidence}
        raw = lc.trapi_chat_json(CROSS_JUDGE["deployment"], _SCORE_SYSTEM, json.dumps(payload, ensure_ascii=False),
                                 max_tokens=8000, token_field=CROSS_JUDGE["token_field"],
                                 temperature=CROSS_JUDGE["temperature"], retries=6)
        score = _validate_score(raw)
        atomic_json(out / f"{run['run_id']}.json", {"run_id": run["run_id"],
                                                    "judge": f"trapi:{CROSS_JUDGE['deployment']}",
                                                    "scores": score["scores"],
                                                    "classification": score.get("classification", "")})

    return run_jobs("cross_judge", jobs, job, workers)


def audit_stage(workers: int, resume: bool) -> dict[str, int]:
    out = OUT / "audit"
    jobs = [(rid, (run,)) for rid, run in new_runs().items()
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


# ---------------------------------------------------------------- report

def mean(values: list[Any]) -> float | None:
    values = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return round(statistics.fmean(values), 3) if values else None


def recon(scores: dict[str, int]) -> float:
    return statistics.fmean(scores[d] for d in PRIMARY_DIMENSIONS)


def load_records() -> dict[tuple[str, str, str, int], dict[str, Any]]:
    sources: list[tuple[Path, dict[str, dict[str, Any]]]] = [(OUT, new_runs())]
    for arm, root in BASELINES.items():
        runs = {p.stem: _read_json(p) for p in sorted((root / "runs").glob(f"PMC*__{arm}__s*.json"))}
        sources.append((root, {k: v for k, v in runs.items() if v["arm"] == arm}))
    records = {}
    for root, runs in sources:
        for rid, run in runs.items():
            paths = {"gpt": root / "judgments" / "gpt56" / f"{rid}.json",
                     "deep": root / "judgments" / "deepseek" / f"{rid}.json", "audit": root / "audit" / f"{rid}.json"}
            records[(run["paper_id"], run["query_level"], run["arm"], run["sample"])] = {
                "run": run, **{k: _read_json(v) if v.exists() else None for k, v in paths.items()}}
    return records


def unit_scores(records: dict, arm: str, judge: str, levels: tuple[str, ...] = QUERY_LEVELS
                ) -> dict[tuple[str, str], float]:
    per: dict[tuple[str, str], list[float]] = defaultdict(list)
    for (paper, level, a, _), rec in records.items():
        if a == arm and level in levels and rec.get(judge):
            per[(paper, level)].append(recon(rec[judge]["scores"]))
    return {k: statistics.fmean(v) for k, v in per.items()}


def paired(a: dict, b: dict, name_a: str, name_b: str) -> dict[str, Any]:
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


def graph_statistics() -> dict[str, Any]:
    per_case = {}
    for case in rx.cases().values():
        path = case_dir(case["paper_id"]) / "graph.json"
        if path.exists():
            per_case[case["paper_id"]] = _read_json(path)["stats"]
    papers = full_text_papers()
    resolution: Counter[str] = Counter()
    ctx_stats: Counter[str] = Counter()
    card_records = 0
    for pmcid in papers:
        parsed = _read_json(PAPERS / pmcid / "parsed.json")
        resolution.update(parsed["resolution"])
        if (PAPERS / pmcid / "contexts.json").exists():
            ctx_stats.update(_read_json(PAPERS / pmcid / "contexts.json")["stats"])
        if (PAPERS / pmcid / "card.json").exists():
            card_records += len(_read_json(PAPERS / pmcid / "card.json")["records"])
    total = sum(resolution.values())
    keys = ("nodes", "full_text_nodes", "seeds", "expansion", "edges", "nodes_with_statements", "statements",
            "nodes_with_2plus_citers", "contradicting_statements")
    return {"cases": len(per_case), "unique_full_text_papers": len(papers), "card_records": card_records,
            "reference_resolution": {k: round(v / max(1, total), 3) for k, v in resolution.most_common()},
            "references_total": total, "context_extraction": dict(ctx_stats),
            "mean_per_case": {k: mean([s[k] for s in per_case.values()]) for k in keys}, "per_case": per_case}


def report() -> dict[str, Any]:
    records = load_records()
    arms = tuple(BASELINES) + VARIANTS
    by_arm: dict[str, Any] = {}
    for arm in arms:
        recs = [r for (p, lvl, a, s), r in records.items() if a == arm]
        judged = [r for r in recs if r["gpt"]]
        audits = [r["audit"] for r in judged if r["audit"]]
        units_g = unit_scores(records, arm, "gpt")
        units_d = unit_scores(records, arm, "deep")
        sources = Counter(a["mechanism_source"] for a in audits)
        by_arm[arm] = {
            "runs": len(recs), "failed": sum(1 for r in recs if r["run"]["status"] != "ok"), "judged": len(judged),
            "reconstruction_gpt56": mean(list(units_g.values())),
            "reconstruction_deepseek": mean(list(units_d.values())),
            "reconstruction_gpt56_non_broad": mean(list(unit_scores(
                records, arm, "gpt", ("problem_constrained", "expert_context")).values())),
            "by_level": {lvl: mean([v for k, v in units_g.items() if k[1] == lvl]) for lvl in QUERY_LEVELS},
            "failure_rate_by_level": {lvl: mean([1.0 if recon(r["gpt"]["scores"]) <= 1.0 else 0.0 for r in judged
                                                 if r["run"]["query_level"] == lvl]) for lvl in QUERY_LEVELS},
            **{dim.replace("_reconstruction", "").replace("_agreement", ""): mean([r["gpt"]["scores"][dim]
                                                                                    for r in judged])
               for dim in ("intervention_reconstruction", "mechanism_agreement", "outcome_agreement",
                           "evidence_validity", "novelty")},
            "mechanism_own_reasoning": round(sources["not_from_evidence"] / max(1, len(audits)), 3),
            "mechanism_transferred_unjustified": round(sources["transferred_without_justification"]
                                                       / max(1, len(audits)), 3),
            "complete_chain_rate": mean([1.0 if all(v == 2 for v in a["chain"].values()) else 0.0 for a in audits]),
            "specificity": mean([mean([1.0 if v else 0.0 for v in a["specificity"].values()]) for a in audits]),
            "citations_per_hypothesis": mean([len(r["run"]["cited_ids"]) for r in judged]),
            "packed_records": mean([len(r["run"].get("packed_ids", [])) for r in judged]),
            "packed_papers": mean([r["run"].get("packed_papers") for r in judged]),
            "packed_with_citer_statements": mean([r["run"].get("packed_with_citer_statements") for r in judged])
            if arm in VARIANTS else None,
            "hedges_per_hypothesis": mean([len(HEDGE.findall(f"{r['run']['generation'].get('hypothesis', '')} "
                                                             f"{r['run']['generation'].get('predicted_outcome', '')}"))
                                           for r in judged]),
        }
    agent = [r["run"] for (p, lvl, a, s), r in records.items() if a == "graph_tool_agent" and r["run"]["status"] == "ok"]
    tool_use: Counter[str] = Counter(t["tool"] for run in agent for t in run.get("trace", []))
    agent_behaviour = {"runs": len(agent), "tool_calls_mean": mean([run.get("tool_calls") for run in agent]),
                       "tool_use_share": {k: round(v / max(1, sum(tool_use.values())), 3)
                                          for k, v in tool_use.most_common()},
                       "nodes_read_mean": mean([len(run["packed_ids"]) for run in agent]),
                       "rejected_submissions": sum(1 for run in agent for t in run.get("trace", [])
                                                  if t["tool"] == "submit_hypothesis" and not t.get("accepted"))}
    comparisons: dict[str, list[dict[str, Any]]] = {}
    for judge in ("gpt", "deep"):
        base = unit_scores(records, PRIMARY_BASELINE, judge)
        primary = [paired(unit_scores(records, v, judge), base, v, PRIMARY_BASELINE) for v in VARIANTS]
        for item, adj in zip(primary, holm_adjust([c.get("sign_test_p", 1.0) for c in primary])):
            item.update({"holm_p": round(adj, 4), "role": "primary"})
        secondary = [paired(unit_scores(records, v, judge), unit_scores(records, b, judge), v, b)
                     for v in VARIANTS for b in ("card", "card_systemmatch", "closed_book")]
        secondary += [paired(unit_scores(records, a, judge), unit_scores(records, b, judge), a, b) for a, b in (
            ("graph_profiles", "graph_selection"), ("graph_profiles_systemmatch", "graph_profiles"),
            ("corroboration_weighted", "graph_profiles"), ("graph_tool_agent", "graph_profiles"))]
        for item in secondary:
            item["role"] = "secondary"
        comparisons[judge] = primary + secondary
    new = new_runs()
    expected = len(rx.cases()) * len(QUERY_LEVELS) * len(VARIANTS) * len(rx.SAMPLES)
    ok = sum(r["status"] == "ok" for r in new.values())
    leak_keys = ("temporal_violations", "test_paper_leaks", "family_leaks", "target_doi_or_title_leaks",
                 "invalid_citations")
    integrity = {
        "expected_runs": expected, "runs": len(new), "ok": ok,
        "judged_gpt56": len(list((OUT / "judgments" / "gpt56").glob("*.json"))),
        "judged_deepseek": len(list((OUT / "judgments" / "deepseek").glob("*.json"))),
        "audited": len(list((OUT / "audit").glob("*.json"))),
        **{k: sum(r["audit"].get(k, 0) for r in new.values()) for k in leak_keys},
        "stage_errors": {p.name: len(list(p.glob("*.json"))) for p in sorted((OUT / "errors").glob("*")) if p.is_dir()},
        "generators": sorted({r["generator"] for r in new.values()}),
    }
    # A run may stay failed only after its single retry (the first failed attempt is kept in failed_attempts/).
    failed = [rid for rid, r in new.items() if r["status"] != "ok"]
    integrity["failed_after_retry"] = failed
    retried = all((OUT / "failed_attempts" / f"{rid}.json").exists() for rid in failed)
    integrity["verified"] = bool(len(new) == expected and retried and integrity["judged_gpt56"] == ok
                                 and integrity["judged_deepseek"] == ok and integrity["audited"] == ok
                                 and all(integrity[k] == 0 for k in leak_keys) and len(integrity["generators"]) == 1)
    analysis = {"graph": graph_statistics(), "by_arm": by_arm, "agent_behaviour": agent_behaviour,
                "comparisons": comparisons, "integrity": integrity,
                "bootstrap": {"resamples": BOOTSTRAP_RESAMPLES, "seed": BOOTSTRAP_SEED}}
    (OUT / "results").mkdir(parents=True, exist_ok=True)
    atomic_json(OUT / "results" / "analysis.json", analysis)
    (OUT / "results" / "tables.md").write_text(render_report(analysis))
    return analysis


def _f(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".") if abs(value) < 100 else f"{value:.0f}"
    return str(value)


def render_report(a: dict[str, Any]) -> str:
    g = a["graph"]
    lines = ["# Citation-graph variant: results", "",
             f"Graph: {g['cases']} cases, {g['unique_full_text_papers']} unique full-text papers, "
             f"{g['references_total']} references (resolution {g['reference_resolution']}).", "",
             "| per case (mean) | " + " | ".join(g["mean_per_case"]) + " |",
             "|---|" + "---|" * len(g["mean_per_case"]),
             "| | " + " | ".join(_f(v) for v in g["mean_per_case"].values()) + " |", "",
             "## Scores by arm", "",
             "| arm | runs | failed | GPT-5.6 | DeepSeek | non-broad | broad | problem | expert | intervention | "
             "mechanism | outcome | evidence validity | novelty | own mechanism | unjustified transfer | specificity | "
             "packed papers | with citer statements |",
             "|---|" + "---|" * 19]
    for arm, s in a["by_arm"].items():
        lines.append("| " + " | ".join(_f(x) for x in (
            arm, s["runs"], s["failed"], s["reconstruction_gpt56"], s["reconstruction_deepseek"],
            s["reconstruction_gpt56_non_broad"], s["by_level"].get("broad"), s["by_level"].get("problem_constrained"),
            s["by_level"].get("expert_context"), s["intervention"], s["mechanism"], s["outcome"], s["evidence_validity"],
            s["novelty"], s["mechanism_own_reasoning"], s["mechanism_transferred_unjustified"], s["specificity"],
            s["packed_papers"], s["packed_with_citer_statements"])) + " |")
    for judge, label in (("gpt", "GPT-5.6"), ("deep", "DeepSeek-V4-Pro")):
        lines += ["", f"## Paired comparisons ({label})", "",
                  "| a | b | role | units | diff | 95% CI | a higher | b higher | p | Holm p |", "|---|" + "---|" * 9]
        for c in a["comparisons"][judge]:
            if c.get("units"):
                lines.append("| " + " | ".join(_f(x) for x in (
                    c["a"], c["b"], c["role"], c["units"], c["mean_difference"], f"[{c['ci95'][0]}, {c['ci95'][1]}]",
                    c["papers_a_higher"], c["papers_b_higher"], c["sign_test_p"], c.get("holm_p"))) + " |")
    lines += ["", "## Tool agent", "", "```", json.dumps(a["agent_behaviour"], indent=1), "```", "",
              "## Integrity", "", "```", json.dumps(a["integrity"], indent=1), "```", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- CLI

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("acquire", "extract", "graph", "generate", "judge", "cross_judge", "audit",
                                          "report"))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--cases", nargs="*")
    parser.add_argument("--arms", nargs="*", default=list(VARIANTS))
    args = parser.parse_args()
    resume = not args.no_resume
    if args.stage == "acquire":
        result: Any = acquire(args.cases)
    elif args.stage == "extract":
        result = extract_stage(args.workers, resume, args.cases)
    elif args.stage == "graph":
        result = graph_stage(args.cases)
    elif args.stage == "generate":
        result = generate_stage(args.workers, resume, tuple(args.arms), args.cases)
    elif args.stage == "judge":
        result = judge_stage(args.workers, resume)
    elif args.stage == "cross_judge":
        result = cross_judge_stage(args.workers, resume)
    elif args.stage == "audit":
        result = audit_stage(args.workers, resume)
    else:
        result = report()["integrity"]
    print(json.dumps(result, indent=1, default=str))


if __name__ == "__main__":
    main()
