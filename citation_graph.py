"""Citation-graph paper selection for the high-temperature HEA corpus.

Steps
1. Fetch OpenAlex metadata and reference lists for the 50 corpus papers (by DOI).
2. Build the in-corpus citation graph (corpus paper A cites corpus paper B) and compute
   in-degree and PageRank within the corpus.
3. Expand from the top seed papers: open-access journal articles that cite a seed and mention
   high-entropy alloys in the title or abstract.
4. Score every paper (corpus and candidates) three ways and compare the selections:
   - citation_only: Europe PMC citation count at selection time (the current method, for corpus papers),
     or OpenAlex citations for candidates, both per year of age.
   - graph: bibliographic coupling with the corpus plus in-corpus citation links.
   - combined: z-scored mean of impact, coupling and direct citations to the corpus.
Outputs are written under experiments/high_temperature_hea_qwen35b/citation_graph/.
"""

from __future__ import annotations

import json
import math
import re
import statistics
import time
from datetime import date
from pathlib import Path
from typing import Any

import networkx as nx
import requests

ROOT = Path(__file__).resolve().parent
EXPERIMENT = ROOT / "experiments" / "high_temperature_hea_qwen35b"
OUT = EXPERIMENT / "citation_graph"
MANIFEST = EXPERIMENT / "data" / "corpus" / "manifest.json"
API = "https://api.openalex.org/works"
SELECT = "id,doi,display_name,publication_year,cited_by_count,referenced_works,type,open_access,ids"
HEA_PATTERN = re.compile(r"high[\s\-]*entropy|\bRHEA\b|\bHEA\b|complex concentrated", re.IGNORECASE)
ALLOY_PATTERN = re.compile(r"alloy|superalloy|refractory|solid solution|eutectic", re.IGNORECASE)
OFF_TOPIC_PATTERN = re.compile(r"catal|electro|batter|ceramic|photo|supercapacit|energy storage|magnet|oxide|nitride|carbide", re.IGNORECASE)
REVIEW_PATTERN = re.compile(r"\b(review|overview|perspectives?|roadmap|survey)\b", re.IGNORECASE)
CURRENT_YEAR = date.today().year
SEED_COUNT = 10
CITING_PER_SEED = 60
SLEEP = 0.2


def _get(params: dict[str, Any]) -> dict[str, Any]:
    for attempt in range(5):
        response = requests.get(API, params=params, timeout=60,
                                headers={"User-Agent": "mathg-citation-graph/1.0"})
        if response.status_code == 429:
            time.sleep(5 * (attempt + 1))
            continue
        response.raise_for_status()
        time.sleep(SLEEP)
        return response.json()
    raise RuntimeError(f"OpenAlex request failed: {params}")


def short_id(url: str) -> str:
    return url.rsplit("/", 1)[-1]


def fetch_corpus(dois: list[str]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for start in range(0, len(dois), 40):
        chunk = dois[start:start + 40]
        payload = _get({"filter": "doi:" + "|".join(f"https://doi.org/{d}" for d in chunk),
                        "per-page": 50, "select": SELECT})
        for work in payload.get("results", []):
            found[(work.get("doi") or "").replace("https://doi.org/", "").lower()] = work
    return found


def fetch_citing(seed_id: str, years_from: int) -> list[dict[str, Any]]:
    payload = _get({
        "filter": f"cites:{seed_id},is_oa:true,type:article,from_publication_date:{years_from}-01-01",
        "search": "high entropy alloy",
        "sort": "cited_by_count:desc",
        "per-page": CITING_PER_SEED,
        "select": SELECT,
    })
    return payload.get("results", [])


def is_review(work: dict[str, Any]) -> bool:
    return work.get("type") != "article" or bool(REVIEW_PATTERN.search(work.get("display_name") or ""))


def is_hea(work: dict[str, Any]) -> bool:
    title = work.get("display_name") or ""
    return (bool(HEA_PATTERN.search(title)) and bool(ALLOY_PATTERN.search(title))
            and not OFF_TOPIC_PATTERN.search(title))


def pagerank(graph: nx.DiGraph, damping: float = 0.85, iterations: int = 100) -> dict[str, float]:
    """Power-iteration PageRank (no scipy dependency)."""
    nodes = list(graph)
    count = len(nodes)
    rank = {node: 1 / count for node in nodes}
    for _ in range(iterations):
        dangling = sum(rank[node] for node in nodes if graph.out_degree(node) == 0)
        updated = {node: (1 - damping) / count + damping * dangling / count for node in nodes}
        for node in nodes:
            out = graph.out_degree(node)
            if out:
                share = damping * rank[node] / out
                for target in graph.successors(node):
                    updated[target] += share
        rank = updated
    return rank


def zscore(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    mean = statistics.fmean(values.values())
    spread = statistics.pstdev(values.values()) or 1.0
    return {key: (value - mean) / spread for key, value in values.items()}


def impact(work: dict[str, Any]) -> float:
    age = max(1, CURRENT_YEAR - int(work.get("publication_year") or CURRENT_YEAR) + 1)
    return math.log1p(int(work.get("cited_by_count") or 0) / age)


def europe_pmc_record(doi: str) -> dict[str, Any]:
    """Europe PMC lookup: PMC ID and open-access flag, which determine whether JATS full text exists."""
    for attempt in range(4):
        response = requests.get(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            params={"query": f'DOI:"{doi}"', "format": "json", "resultType": "core", "pageSize": 1},
            timeout=60,
        )
        if response.status_code == 200:
            time.sleep(SLEEP)
            results = response.json().get("resultList", {}).get("result", [])
            if results:
                record = results[0]
                return {"pmcid": record.get("pmcid") or "", "is_open_access": record.get("isOpenAccess") == "Y"}
            return {"pmcid": "", "is_open_access": False}
        time.sleep(3 * (attempt + 1))
    return {"pmcid": "", "is_open_access": False}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text())
    corpus_rows = {row["doi"].lower(): row for row in manifest}
    works = fetch_corpus(list(corpus_rows))
    missing = sorted(set(corpus_rows) - set(works))

    corpus_ids = {short_id(work["id"]): doi for doi, work in works.items()}
    corpus_refs = {short_id(w["id"]): {short_id(r) for r in w.get("referenced_works") or []}
                   for w in works.values()}
    union_refs = set().union(*corpus_refs.values()) if corpus_refs else set()

    graph = nx.DiGraph()
    graph.add_nodes_from(corpus_ids)
    for source, refs in corpus_refs.items():
        for target in refs & set(corpus_ids):
            graph.add_edge(source, target)
    ranks = pagerank(graph)

    seeds = sorted(corpus_ids, key=lambda sid: (-ranks.get(sid, 0), -int(works[corpus_ids[sid]]["cited_by_count"] or 0)))[:SEED_COUNT]
    candidates: dict[str, dict[str, Any]] = {}
    for seed in seeds:
        for work in fetch_citing(seed, years_from=2015):
            sid = short_id(work["id"])
            if sid in corpus_ids or is_review(work) or not is_hea(work):
                continue
            candidates.setdefault(sid, work)

    rows: list[dict[str, Any]] = []
    for doi, work in works.items():
        sid = short_id(work["id"])
        refs = corpus_refs[sid]
        rows.append({
            "source": "corpus", "openalex_id": sid, "doi": doi, "title": work.get("display_name"),
            "year": work.get("publication_year"), "cited_by": int(work.get("cited_by_count") or 0),
            "impact": impact(work), "direct_to_corpus": len(refs & set(corpus_ids)),
            "coupling": len(refs & union_refs - {sid}) / max(1, len(refs)),
            "in_corpus_indegree": graph.in_degree(sid), "pagerank": ranks.get(sid, 0.0),
            "europe_pmc_citations": int(corpus_rows[doi]["citation_count"]),
            "has_pmc": bool(europe_pmc_record(doi)["pmcid"]),
        })
    for sid, work in candidates.items():
        refs = {short_id(r) for r in work.get("referenced_works") or []}
        doi = (work.get("doi") or "").replace("https://doi.org/", "").lower()
        pmc = europe_pmc_record(doi) if doi else {"pmcid": "", "is_open_access": False}
        rows.append({
            "source": "candidate", "openalex_id": sid, "doi": doi,
            "title": work.get("display_name"), "year": work.get("publication_year"),
            "cited_by": int(work.get("cited_by_count") or 0), "impact": impact(work),
            "direct_to_corpus": len(refs & set(corpus_ids)),
            "coupling": len(refs & union_refs) / max(1, len(refs)),
            "in_corpus_indegree": 0, "pagerank": 0.0, "europe_pmc_citations": None,
            "has_pmc": bool(pmc["pmcid"]), "pmcid": pmc["pmcid"],
        })

    impact_z = zscore({r["openalex_id"]: r["impact"] for r in rows})
    coupling_z = zscore({r["openalex_id"]: r["coupling"] for r in rows})
    direct_z = zscore({r["openalex_id"]: float(r["direct_to_corpus"]) for r in rows})
    for row in rows:
        key = row["openalex_id"]
        row["score_citation_only"] = impact_z[key]
        row["score_graph"] = coupling_z[key] + direct_z[key]
        row["score_combined"] = (impact_z[key] + coupling_z[key] + direct_z[key]) / 3

    pool = [r for r in rows if r["source"] == "candidate"] + [r for r in rows if r["source"] == "corpus"]
    pmc_pool = [r for r in pool if r["has_pmc"]]
    selections: dict[str, list[str]] = {}
    for name in ("score_citation_only", "score_graph", "score_combined"):
        for label, population in (("oa", pool), ("pmc", pmc_pool)):
            ranked = sorted(population, key=lambda r: -r[name])
            selections[f"{name}|{label}"] = [r["openalex_id"] for r in ranked[:len(corpus_ids)]]
    current = set(corpus_ids)
    overlap = {name: len(set(ids) & current) for name, ids in selections.items()}
    new_counts = {name: sum(1 for sid in ids if sid not in current) for name, ids in selections.items()}

    summary = {
        "date": date.today().isoformat(),
        "corpus_papers": len(corpus_ids),
        "corpus_missing_in_openalex": missing,
        "corpus_edges": graph.number_of_edges(),
        "corpus_papers_with_any_corpus_link": sum(1 for n in graph if graph.degree(n) > 0),
        "seed_count": len(seeds),
        "candidates_after_filters": len(candidates),
        "candidates_with_pmc_id": sum(1 for r in rows if r["source"] == "candidate" and r["has_pmc"]),
        "candidate_year_range": [min((int(c.get("publication_year") or 0) for c in candidates.values()), default=None),
                                 max((int(c.get("publication_year") or 0) for c in candidates.values()), default=None)],
        "top_k": len(corpus_ids),
        "overlap_with_current_corpus": overlap,
        "new_papers_in_top_k": new_counts,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    (OUT / "rows.json").write_text(json.dumps(sorted(rows, key=lambda r: -r["score_combined"]), indent=1))
    (OUT / "selections.json").write_text(json.dumps({
        name: [{"openalex_id": sid, "title": next(r["title"] for r in rows if r["openalex_id"] == sid),
                "source": next(r["source"] for r in rows if r["openalex_id"] == sid)} for sid in ids]
        for name, ids in selections.items()}, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
