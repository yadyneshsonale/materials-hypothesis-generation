"""Experiment 42 (loop.md 23.1): offline checks of the reviewers' proposals on existing labels (target-aware analysis
only; nothing here is shown to a method).

Usage:
  python v2_offline.py retrieval   re-rank each unit's labelled 64,000-character pack; share of the top 16,000 characters
                                   that carries the paper's lever (experiment-39 pack labels)
  python v2_offline.py analogs     gap analogs: share of the k most gap-similar corpus papers that carry the paper's lever
                                   (experiment-39 corpus labels), with topic-similarity and random controls
  python v2_offline.py audit       print a few extracted gaps and studies for a manual parser check
Outputs: experiments/high_temperature_hea_qwen35b/loop_v2/offline/.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import diag_analysis as D
import hypo_loop as H
import round4_offline as R
import stage_v2 as S
import websearch as ws
from hypothesis_evidence_v2 import atomic_json

OUT = D.E / "loop_v2" / "offline"
BUDGET = 16000


def take(order: list[str], texts: dict[str, str]) -> list[str]:
    out, used = [], 0
    for rid in order:
        n = min(len(texts[rid]), 1600)
        if used + n > BUDGET:
            continue
        out.append(rid)
        used += n
        if len(out) >= 24 or used >= BUDGET - 200:
            break
    return out


def retrieval() -> dict[str, Any]:
    ev = D.W.Evidence()
    cases = H.cases()
    density: dict[str, list[float]] = defaultdict(list)
    contains: dict[str, list[bool]] = defaultdict(list)
    per_paper: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for p in sorted((D.DIAG / "pack_labels" / "Q64").glob("*.json")):
        d = json.loads(p.read_text())
        lab = {i["record_id"]: i["lever_match"] for i in d["items"] if i["lever_match"] is not None}
        recs = {rid: ev.web(rid) for rid in lab}
        texts = {rid: r.text for rid, r in recs.items()}
        q = cases[d["paper_id"]]["queries"][d["level"]]["text"]
        plain = S.bm25_scores(S.content_terms(q), {rid: S.content_terms(t) for rid, t in texts.items()})
        clean = S.bm25_scores(S.clean_terms(q), {rid: S.clean_terms(t) for rid, t in texts.items()})
        orders = {
            "question order (the existing pack)": list(lab),
            "BM25, content words": sorted(lab, key=lambda r: (-plain[r], r)),
            "BM25, schema words removed": sorted(lab, key=lambda r: (-clean[r], r)),
            "+ section weights": sorted(lab, key=lambda r: (-clean[r] * S.section_weight(recs[r].kind), r)),
            "+ section weights + action boost (retrieval v2)": [r.record_id for r in S.salience_order(q, list(recs.values()))],
        }
        for name, order in orders.items():
            top = take(order, texts)
            flags = [lab[r] >= 2 for r in top]
            value = statistics.fmean(flags) if flags else 0.0
            density[name].append(value)
            contains[name].append(any(flags))
            per_paper[name][d["paper_id"]].append(value)
    base = "question order (the existing pack)"
    out: dict[str, Any] = {}
    for name in density:
        diff = {p: [a - b for a, b in zip(per_paper[name][p], per_paper[base][p])] for p in per_paper[name]}
        out[name] = {"units": len(density[name]), "lever_passage_share_top16k": round(statistics.fmean(density[name]), 3),
                     "pack_contains_lever": round(statistics.fmean(contains[name]), 3),
                     "vs_question_order": R.bootstrap(diff) if name != base else None}
    return out


def unit_analogs(paper: str, level: str) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    analogs, abstracts = {}, {}
    for entry in ws.corpus_papers(paper, level):
        try:
            parsed = ws.load_parsed(entry["pmcid"])
        except Exception:  # noqa: BLE001 - a missing parse means no analog
            continue
        gs = S.gap_and_study(ws.sections(parsed))
        abstracts[entry["pmcid"]] = f"{parsed.get('title', '')} {parsed.get('abstract') or ''}"
        if gs:
            analogs[entry["pmcid"]] = gs
    return analogs, abstracts


def analogs() -> dict[str, Any]:
    cases = H.cases()
    rng = random.Random(20261030)
    shares: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    coverage, sizes = [], []
    for p in sorted((D.DIAG / "corpus_labels").glob("*.json")):
        d = json.loads(p.read_text())
        lab = {i["pmcid"]: i["lever_match"] for i in d["items"] if i["lever_match"] is not None}
        analog, abstracts = unit_analogs(d["paper_id"], d["level"])
        analog = {k: v for k, v in analog.items() if k in lab}
        coverage.append(len(analog) / max(1, len(lab)))
        sizes.append(len(analog))
        if not analog:
            continue
        q = cases[d["paper_id"]]["queries"][d["level"]]["text"]
        orders = {
            "gap similarity (the analog rule)": S.rank_analogs(q, analog),
            "topic similarity (title + abstract)": sorted(
                analog, key=lambda k: (-S.bm25_scores(S.clean_terms(q), {x: S.clean_terms(abstracts[x])
                                                                       for x in analog}).get(k, 0.0), k)),
            "random": rng.sample(sorted(analog), len(analog)),
        }
        for name, order in orders.items():
            for k in (1, 3, 5, 10):
                top = order[:k]
                shares[name][k].append(statistics.fmean(lab[x] >= 2 for x in top))
        shares["all analog papers"][0].append(statistics.fmean(lab[x] >= 2 for x in analog))
    out: dict[str, Any] = {"units": len(sizes), "analog_papers_per_unit": round(statistics.fmean(sizes), 1),
                           "share_of_corpus_papers_with_a_gap": round(statistics.fmean(coverage), 3)}
    for name, by_k in shares.items():
        out[name] = {f"top{k}" if k else "all": round(statistics.fmean(v), 3) for k, v in sorted(by_k.items())}
    return out


def audit(n: int = 4) -> dict[str, Any]:
    rng = random.Random(7)
    units = sorted((D.DIAG / "corpus_labels").glob("*.json"))
    shown = []
    for p in rng.sample(units, n):
        d = json.loads(p.read_text())
        analog, _ = unit_analogs(d["paper_id"], d["level"])
        if not analog:
            continue
        k = rng.choice(sorted(analog))
        shown.append({"pmcid": k, "gap_tail": analog[k]["gap"][-400:], "study_head": analog[k]["study"][:300]})
    return {"examples": shown}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("retrieval", "analogs", "audit"))
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"retrieval": retrieval, "analogs": analogs, "audit": audit}[args.stage]()
    atomic_json(OUT / f"{args.stage}.json", result)
    print(json.dumps(result, indent=1, ensure_ascii=False)[:5000])


if __name__ == "__main__":
    main()
