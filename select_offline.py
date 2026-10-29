"""Experiment 41 (loop.md 22): offline screening of target-free selection rules over existing judged hypotheses.

Every candidate is a judged o3-mini hypothesis that already exists for the unit (oracle diagnostics excluded), so a
selection rule's effect is measured exactly with the judges' existing scores, not with a proxy label.

Usage:
  python select_offline.py pool       build the candidate pool with target-free features
  python select_offline.py rules      evaluate fixed selection rules
  python select_offline.py lopo       evaluate a leave-one-paper-out learned reranker
Outputs: experiments/high_temperature_hea_qwen35b/loop_select/offline/.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import diag_analysis as D
import hypo_loop as H
import round4_offline as R
from citegraph import content_terms
from hypothesis_evidence_v2 import atomic_json
from temporal_hypothesis_benchmark import _read_json

E = D.E
OUT = E / "loop_select" / "offline"
ROOTS = (E / "loop", E / "loop_web", E / "loop_pcd", E / "loop_r4", E / "loop_agent", E / "loop_diag")
O3 = "trapi:o3-mini_2025-01-31"
TEXT = ("intervention", "structural_mediator", "mechanism")


def candidates() -> list[dict[str, Any]]:
    """Every judged, target-free o3-mini hypothesis on the 45 papers (o3-mini writer; Llama-3.3 may only have written
    web search phrases)."""
    rows = []
    for root in ROOTS:
        for mdir in sorted(p for p in root.iterdir() if (p / "runs").is_dir()):
            if mdir.name.startswith("oracle_"):
                continue
            for path in sorted((mdir / "runs").glob("PMC*.json")):
                run = json.loads(path.read_text())
                if run.get("status") != "ok" or run.get("benchmark", "v3.1") not in R.BENCHMARKS:
                    continue
                models = set((run.get("models") or {}).values())
                if O3 not in models or any(m != O3 and "Llama" not in m for m in models):
                    continue
                if any(k != "web_query_writer" and "Llama" in v for k, v in (run.get("models") or {}).items()):
                    continue
                gpt = mdir / "judgments" / "gpt56" / path.name
                deep = mdir / "judgments" / "deepseek" / path.name
                if not gpt.exists() or not deep.exists():
                    continue
                g = run["generation"]
                rows.append({"root": root.name, "method": run["method"], "run_id": run["run_id"],
                             "paper": run["paper_id"], "level": run["query_level"], "query": run["query"],
                             "evidence": bool(run.get("seen_ids")),
                             "text": " ".join(str(g.get(f) or "") for f in TEXT),
                             "gpt": R.recon(_read_json(gpt)["scores"]), "deep": R.recon(_read_json(deep)["scores"])})
    return rows


def corpus_docs(paper: str, level: str) -> dict[str, list[str]]:
    """Titles and abstracts of the unit's web corpus (every paper dated before the held-out paper)."""
    corpus = _read_json(R.WEB / "corpora" / paper / f"{level}.json")
    docs = {}
    for s in corpus["seeds"] + corpus.get("expansion", []):
        path = R.WEB / "papers" / f"{s['pmcid']}.json"
        if path.exists():
            d = _read_json(path)
            docs[s["pmcid"]] = content_terms(f"{d.get('title', '')} {d.get('abstract') or ''}")
    return docs


def bm25_all(query: list[str], docs: dict[str, list[str]], df: Counter, avg: float) -> list[float]:
    n = len(docs)
    out = []
    qs = set(query)
    for doc in docs.values():
        tf = Counter(doc)
        s = 0.0
        for t in qs:
            if t in tf:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * tf[t] * 2.2 / (tf[t] + 1.2 * (0.25 + 0.75 * len(doc) / avg))
        out.append(s)
    return out


def pool() -> dict[str, Any]:
    rows = candidates()
    by_unit: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_unit[(r["paper"], r["level"])].append(r)
    for (paper, level), cands in by_unit.items():
        docs = corpus_docs(paper, level)
        df = Counter(t for d in docs.values() for t in set(d))
        avg = statistics.fmean(len(d) for d in docs.values()) if docs else 1.0
        terms = [set(content_terms(c["text"])) for c in cands]
        for c, t in zip(cands, terms):
            scores = sorted(bm25_all(list(t), docs, df, avg), reverse=True) if docs else [0.0]
            c["support_top5"] = statistics.fmean(scores[:5])
            c["support_top1"] = scores[0]
            c["support_papers"] = sum(1 for s in scores if s >= 0.5 * scores[0]) if scores[0] > 0 else 0
            others = [o for o in terms if o is not t]
            c["consensus"] = statistics.fmean(len(t & o) / max(1, len(t | o)) for o in others) if others else 0.0
            c["words"] = len(c["text"].split())
            c["closed_book"] = not c["evidence"]
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "pool.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return {"candidates": len(rows), "units": len(by_unit),
            "per_unit": round(statistics.fmean(len(v) for v in by_unit.values()), 1),
            "methods": len({r["method"] for r in rows})}


def load_pool() -> dict[tuple[str, str], list[dict[str, Any]]]:
    by_unit: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for line in (OUT / "pool.jsonl").read_text().splitlines():
        r = json.loads(line)
        by_unit[(r["paper"], r["level"])].append(r)
    return by_unit


def evaluate(choice: dict[tuple[str, str], dict[str, Any]], by_unit: dict) -> dict[str, Any]:
    """Selected candidate vs the incumbent writer's mean on the same unit, and vs a random pick (pool mean)."""
    out = {}
    for j in ("gpt", "deep"):
        vs_writer: dict[str, list[float]] = defaultdict(list)
        vs_pool: dict[str, list[float]] = defaultdict(list)
        sel = []
        for unit, c in choice.items():
            cands = by_unit[unit]
            writer = [x[j] for x in cands if x["method"] == "writer_only_b_o3mini"]
            if not writer:
                continue
            sel.append(c[j])
            vs_writer[unit[0]].append(c[j] - statistics.fmean(writer))
            vs_pool[unit[0]].append(c[j] - statistics.fmean(x[j] for x in cands))
        out[j] = {"selected_mean": round(statistics.fmean(sel), 3), "vs_writer": R.bootstrap(vs_writer),
                  "vs_random_pick": R.bootstrap(vs_pool)}
    return out


def rules() -> dict[str, Any]:
    by_unit = load_pool()
    signals = {"most literature support (top-5 BM25)": lambda c: c["support_top5"],
               "least literature support": lambda c: -c["support_top5"],
               "most literature support (top-1)": lambda c: c["support_top1"],
               "most supporting papers": lambda c: c["support_papers"],
               "most consensus (approach words shared with other candidates)": lambda c: c["consensus"],
               "least consensus": lambda c: -c["consensus"],
               "consensus x support": lambda c: c["consensus"] * c["support_top5"]}
    out: dict[str, Any] = {"units": len(by_unit), "per_unit": round(statistics.fmean(len(v) for v in by_unit.values()), 1),
                           "oracle_best": {j: round(statistics.fmean(max(x[j] for x in v) for v in by_unit.values()), 3)
                                           for j in ("gpt", "deep")}}
    for name, key in signals.items():
        choice = {u: max(v, key=lambda c: (key(c), c["run_id"])) for u, v in by_unit.items()}
        out[name] = evaluate(choice, by_unit)
    return out


FEATURES = ("support_top5", "support_top1", "support_papers", "consensus", "words", "closed_book")


def zscore(values: list[float]) -> list[float]:
    m, s = statistics.fmean(values), statistics.pstdev(values) or 1.0
    return [(v - m) / s for v in values]


def lopo() -> dict[str, Any]:
    """Leave-one-paper-out ridge regression of the within-unit z-scored GPT-5.6 score on within-unit z-scored target-free
    features; the selected candidate is the one with the highest prediction in each held-out unit."""
    import numpy as np
    by_unit = load_pool()
    X, y, paper_of, unit_of = [], [], [], []
    rows_of_unit = {}
    for unit, cands in by_unit.items():
        feats = [zscore([float(c[f]) for c in cands]) for f in FEATURES]
        target = zscore([c["gpt"] for c in cands])
        rows_of_unit[unit] = []
        for i, c in enumerate(cands):
            X.append([feats[k][i] for k in range(len(FEATURES))])
            y.append(target[i])
            paper_of.append(unit[0])
            unit_of.append(unit)
            rows_of_unit[unit].append(len(X) - 1)
    X, y = np.array(X), np.array(y)
    choice = {}
    coefs = []
    for paper in sorted(set(paper_of)):
        train = np.array([p != paper for p in paper_of])
        A = X[train]
        w = np.linalg.solve(A.T @ A + 10.0 * np.eye(A.shape[1]), A.T @ y[train])
        coefs.append(w)
        for unit in [u for u in rows_of_unit if u[0] == paper]:
            idx = rows_of_unit[unit]
            pred = X[idx] @ w
            choice[unit] = by_unit[unit][int(np.argmax(pred))]
    mean_w = np.mean(coefs, axis=0)
    return {"features": dict(zip(FEATURES, [round(float(v), 3) for v in mean_w])), **evaluate(choice, by_unit)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("pool", "rules", "lopo"))
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"pool": pool, "rules": rules, "lopo": lopo}[args.stage]()
    atomic_json(OUT / f"{args.stage}.json", result)
    print(json.dumps(result, indent=1)[:6000])


if __name__ == "__main__":
    main()
