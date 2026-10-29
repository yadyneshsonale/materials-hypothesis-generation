"""Experiment 40 (loop.md 21.1): offline checks behind the new agent, on existing runs and the experiment-39 labels.

Target-aware analysis only: the GPT-5.6 pack labels say which passages carry the paper's lever. Nothing here is
shown to a method.

Usage:
  python agent_offline.py rerank   re-rank each unit's labelled 64,000-character pack down to 16,000 characters and
                                   measure the share of passages that carry the paper's lever
  python agent_offline.py group    o3-mini (target-free) groups each pack's passages by approach and rates how
                                   directly each addresses the question's limitation (cached, resumable)
  python agent_offline.py rules    how often a decision rule over those groups picks the paper's lever
Outputs: experiments/high_temperature_hea_qwen35b/loop_agent/offline/.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

import diag_analysis as D
import hypo_loop as H
import llm_client as lc
import loop_methods as LM
from citegraph import bm25, content_terms
from hypothesis_evidence_v2 import atomic_json

OUT = D.E / "loop_agent" / "offline"
GROUPS = OUT / "groups_Q64"
BUDGET = 16000
O3MINI = "o3-mini_2025-01-31"


def q64_units() -> list[dict[str, Any]]:
    return [json.loads(p.read_text()) for p in sorted((D.DIAG / "pack_labels" / "Q64").glob("*.json"))]


def take(order: list[str], texts: dict[str, str]) -> list[str]:
    """The first records of an order within the standard budget (16,000 characters, ≤ 24 records)."""
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


def rerank() -> dict[str, Any]:
    ev = D.W.Evidence()
    cases = H.cases()
    writer = {D.key_of(r): r["generation"] for r in D.runs_of(D.WRITER)}
    ideas = {}
    for p in sorted((D.E / "loop_pcd" / "pcd_none_o3mini" / "runs").glob("*.json")):
        r = json.loads(p.read_text())
        if r.get("status") == "ok":
            ideas[D.key_of(r)] = r["notes"].get("proposals", [])

    def text_of(g: dict[str, Any]) -> str:
        return " ".join(str(g.get(f) or "") for f in ("intervention", "structural_mediator", "mechanism"))

    density: dict[str, list[float]] = defaultdict(list)
    contains: dict[str, list[bool]] = defaultdict(list)
    for d in q64_units():
        paper, level = d["paper_id"], d["level"]
        lab = {i["record_id"]: i["lever_match"] for i in d["items"] if i["lever_match"] is not None}
        texts = {rid: ev.web(rid).text for rid in lab}
        dates = {rid: ev.web(rid).publication_date or "" for rid in lab}
        docs = {rid: content_terms(texts[rid]) for rid in lab}
        query = cases[paper]["queries"][level]["text"]

        def by(search: str) -> list[str]:
            scores = bm25(content_terms(search), docs)
            return sorted(lab, key=lambda r: (-scores.get(r, 0.0), r))

        draft1, draft2 = writer.get((paper, level, 1), {}), writer.get((paper, level, 2), {})
        orders: dict[str, list[str]] = {
            "question order": list(lab),
            "BM25 on the question's content words": by(query),
            "the writer's closed-book draft (HyDE)": by(text_of(draft1)),
            "both writer drafts": by(text_of(draft1) + " " + text_of(draft2)),
            "question and draft": by(query + " " + text_of(draft1)),
            "newest papers first": sorted(lab, key=lambda r: dates[r], reverse=True),
        }
        proposals = ideas.get((paper, level, 1), [])
        if proposals:
            ranks = [by(text_of(i)) for i in proposals]
            merged: list[str] = []
            for k in range(len(lab)):
                for rk in ranks:
                    if k < len(rk) and rk[k] not in merged:
                        merged.append(rk[k])
            orders["four pcd ideas, round robin"] = merged
        for name, order in orders.items():
            top = take(order, texts)
            flags = [lab[r] >= 2 for r in top]
            density[name].append(statistics.fmean(flags) if flags else 0.0)
            contains[name].append(any(flags))
        density["the whole 64,000-character pool"].append(statistics.fmean(v >= 2 for v in lab.values()))
    return {name: {"units": len(v), "lever_passage_share": round(statistics.fmean(v), 3),
                   "pack_contains_lever": round(statistics.fmean(contains[name]), 3) if contains[name] else None}
            for name, v in density.items()}


def group(workers: int = 12) -> dict[str, Any]:
    ev = D.W.Evidence()
    cases = H.cases()
    GROUPS.mkdir(parents=True, exist_ok=True)
    jobs = [d for d in q64_units() if not (GROUPS / f"{d['paper_id']}__{d['level']}.json").exists()]

    def job(d: dict[str, Any]) -> None:
        items = [{"id": n + 1, "text": ev.web(i["record_id"]).text[:1600]} for n, i in enumerate(d["items"])]
        query = cases[d["paper_id"]]["queries"][d["level"]]["text"]
        raw = lc.trapi_chat_json(O3MINI, LM.GROUP_SYSTEM, json.dumps({"research_question": query, "passages": items},
                                                                     ensure_ascii=False),
                                 max_tokens=20000, temperature=None, retries=8)
        atomic_json(GROUPS / f"{d['paper_id']}__{d['level']}.json",
                    {"paper_id": d["paper_id"], "level": d["level"], "groups": (raw or {}).get("groups", []),
                     "record_ids": [i["record_id"] for i in d["items"]]})

    return D._parallel(jobs, job, workers, "group")


def rules() -> dict[str, Any]:
    writer_labels = D.labels_of(D.WRITER)
    results: dict[str, list[bool | float]] = defaultdict(list)
    sizes = []
    for path in sorted(GROUPS.glob("*.json")):
        g = json.loads(path.read_text())
        lab = json.loads((D.DIAG / "pack_labels" / "Q64" / path.name).read_text())
        lever = {n + 1: i["lever_match"] for n, i in enumerate(lab["items"])}
        paper_of = {n + 1: i["record_id"].split("::")[0] for n, i in enumerate(lab["items"])}
        groups = []
        for gr in g["groups"]:
            ids = [i for i in gr.get("passage_ids", []) if isinstance(i, int) and lever.get(i) is not None]
            if not ids:
                continue
            groups.append({"size": len(ids), "papers": len({paper_of[i] for i in ids}),
                           "addresses": LM.agent_int(gr.get("addresses_question")),
                           "majority": statistics.fmean(lever[i] >= 2 for i in ids) >= 0.5,
                           "any": any(lever[i] >= 2 for i in ids)})
        if not groups:
            continue
        sizes.append(len(groups))
        pickers: dict[str, Callable[[dict[str, Any]], tuple[int, ...]]] = {
            "most direct, then more papers, then more passages (the agent's rule)":
                lambda x: (x["addresses"], x["papers"], x["size"]),
            "largest group": lambda x: (x["size"], x["papers"]),
            "most papers": lambda x: (x["papers"], x["size"]),
            "directness x size": lambda x: (x["addresses"] * x["size"], x["papers"]),
        }
        for name, key in pickers.items():
            chosen = max(groups, key=key)  # max keeps the first listed group among ties
            results[f"{name}: majority of passages carry the lever"].append(chosen["majority"])
            results[f"{name}: any passage carries the lever"].append(chosen["any"])
        results["random group: majority"].append(statistics.fmean(x["majority"] for x in groups))
        results["some group matches: majority"].append(any(x["majority"] for x in groups))
        labs = [writer_labels.get((g["paper_id"], g["level"], s)) for s in (1, 2)]
        results["the writer's own choice: lever >= 2"].append(statistics.fmean(x["lever_match"] >= 2 for x in labs if x))
    return {"units": len(sizes), "groups_per_unit": round(statistics.fmean(sizes), 1),
            **{k: round(statistics.fmean(float(x) for x in v), 3) for k, v in results.items()}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("rerank", "group", "rules"))
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"rerank": rerank, "group": group, "rules": rules}[args.stage]()
    atomic_json(OUT / f"{args.stage}.json", result)
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
