"""Round 4 (experiment 38, loop.md 19): offline checks before any new method is built.

Every check uses existing runs, judgments and labels on the 45 spent papers (target-aware analysis only).

Usage:
  python round4_offline.py decompose   what a class hit and a lever hit are worth for the incumbent
  python round4_offline.py pools       export judged o3-mini hypotheses per unit for the likelihood scorer
  python round4_offline.py simpool     every run of the strongest o3-mini configurations (simulation pool)
  python round4_offline.py classify    gpt-4o-mini labels each earlier web-corpus paper's study type (cached)
  python round4_offline.py baserate    do the earlier papers' study types predict the target's type?
  python round4_offline.py pmi         does a pre-cutoff LM's likelihood select the better hypothesis?
Outputs: experiments/high_temperature_hea_qwen35b/loop_r4/offline/.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import hypo_loop  # noqa: F401 - sets the harness's environment defaults before the shared modules load
import llm_client as lc
from failure_clean import TARGET_TYPES
from hypothesis_evidence_v2 import atomic_json
from temporal_eval_v3 import PRIMARY_DIMENSIONS, cluster_bootstrap, exact_sign_test

E = Path(__file__).resolve().parent / "experiments" / "high_temperature_hea_qwen35b"
ROOTS = (E / "loop", E / "loop_web", E / "loop_pcd")
OUT = E / "loop_r4" / "offline"
WEB = E / "websearch"
O3 = "trapi:o3-mini_2025-01-31"
BENCHMARKS = ("v3.1", "test2", "test3", "test4")
CLASSIFIER = "gpt-4o-mini_2024-07-18"  # pre-cutoff (must_obey.md 2): it reads earlier papers, never a query
SEED = 20261028
POOL_CAP = 24
TEXT_FIELDS = ("hypothesis", "intervention", "conditions", "mechanism", "predicted_outcome")

CLASSIFY_SYSTEM = (
    "You classify the main contribution of a materials-science research paper from its title and abstract. "
    "Classes: composition_change (changing the alloy composition or adding elements); processing_route (the "
    "synthesis or manufacturing route, e.g. additive manufacturing, powder metallurgy, casting, sputtering); "
    "heat_or_thermomechanical_treatment (annealing, ageing, rolling, forging or other treatment after processing); "
    "microstructure_architecture (a designed microstructure, e.g. heterogeneous, lamellar, gradient or precipitate "
    "architecture); surface_or_coating (coatings, cladding or surface treatment); computational_method_development "
    "(a new machine-learning or computational method or tool); simulation_study (a DFT, molecular-dynamics, CALPHAD "
    "or phase-field study of a material); experimental_characterization_study (characterising behaviour or "
    "mechanisms of a material without a designed change); other. Return JSON {\"class\": one of the classes, "
    "\"study\": \"the paper's main intervention or study in at most 15 words\"}."
)


def recon(scores: dict[str, int]) -> float:
    return statistics.fmean(scores[d] for d in PRIMARY_DIMENSIONS)


def read(path: Path) -> Any:
    return json.loads(path.read_text())


def judged_runs() -> list[dict[str, Any]]:
    """Every successful run on the 45 papers with a GPT-5.6 judgment, with its judgments and label attached."""
    rows = []
    for root in ROOTS:
        for method_dir in sorted(p for p in root.iterdir() if (p / "runs").is_dir()):
            for path in sorted((method_dir / "runs").glob("PMC*.json")):
                run = read(path)
                if run.get("status") != "ok" or run.get("benchmark", "v3.1") not in BENCHMARKS:
                    continue
                gpt = method_dir / "judgments" / "gpt56" / path.name
                if not gpt.exists():
                    continue
                deep = method_dir / "judgments" / "deepseek" / path.name
                label = method_dir / "labels" / path.name
                rows.append({"root": root.name, "method": run["method"], "run_id": run["run_id"],
                             "paper": run["paper_id"], "level": run["query_level"], "query": run["query"],
                             "models": sorted(set((run.get("models") or {}).values())),
                             "closed_book": not run.get("seen_ids"), "generation": run["generation"],
                             "gpt": recon(read(gpt)["scores"]), "gpt_dims": read(gpt)["scores"],
                             "deep": recon(read(deep)["scores"]) if deep.exists() else None,
                             "label": read(label) if label.exists() else None})
    return rows


def unit_targets(rows: list[dict[str, Any]]) -> dict[tuple[str, str], str]:
    """The target's study type per unit: the majority over every label of every configuration."""
    votes: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for r in rows:
        if r["label"] and r["label"].get("target_type") in TARGET_TYPES:
            votes[(r["paper"], r["level"])][r["label"]["target_type"]] += 1
    return {u: c.most_common(1)[0][0] for u, c in votes.items()}


def bootstrap(per_paper: dict[str, list[float]]) -> dict[str, Any]:
    point, low, high = cluster_bootstrap(dict(sorted(per_paper.items())))
    p, up, down = exact_sign_test([statistics.fmean(v) for _, v in sorted(per_paper.items())])
    return {"diff": round(point, 3), "ci95": [round(low, 3), round(high, 3)], "papers_up": up, "papers_down": down,
            "p": round(p, 4), "papers": len(per_paper)}


# ---------------------------------------------------------------- 1. decomposition

def decompose(rows: list[dict[str, Any]]) -> dict[str, Any]:
    inc = [r for r in rows if r["method"] == "writer_only_b_o3mini" and r["root"] == "loop"]
    targets = unit_targets(rows)
    out: dict[str, Any] = {"runs": len(inc), "gpt_mean": round(statistics.fmean(r["gpt"] for r in inc), 3)}
    by_lever: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for r in inc:
        if r["label"]:
            by_lever[int(r["label"]["lever_match"])].append(r)
    out["by_lever"] = {k: {"share": round(len(v) / len(inc), 3), "gpt": round(statistics.fmean(x["gpt"] for x in v), 3),
                           **{d: round(statistics.fmean(x["gpt_dims"][d] for x in v), 2) for d in PRIMARY_DIMENSIONS}}
                       for k, v in sorted(by_lever.items())}
    cls = Counter()
    for r in inc:
        if r["label"]:
            cls[(r["label"]["intervention_class"], targets.get((r["paper"], r["level"])))] += 1
    out["writer_class_vs_target"] = {f"{a} -> {b}": n for (a, b), n in cls.most_common(25)}
    proposed = Counter(r["label"]["intervention_class"] for r in inc if r["label"])
    actual = Counter(targets.get((r["paper"], r["level"])) for r in inc if r["label"])
    out["class_shares"] = {c: {"writer": round(proposed[c] / sum(proposed.values()), 3),
                               "targets": round(actual[c] / sum(actual.values()), 3)} for c in TARGET_TYPES}
    hits = [r["label"]["intervention_class"] == targets.get((r["paper"], r["level"])) for r in inc if r["label"]]
    out["class_hit"] = round(statistics.fmean(hits), 3)
    by_type: dict[str, list[float]] = defaultdict(list)
    for r in inc:
        by_type[targets.get((r["paper"], r["level"]), "?")].append(r["gpt"])
    out["gpt_by_target_type"] = {k: [round(statistics.fmean(v), 3), len(v)] for k, v in sorted(by_type.items())}
    # Headroom: the best judged o3-mini hypothesis per unit vs the pool mean (what a perfect selector would gain).
    pools = defaultdict(list)
    for r in rows:
        if r["models"] == [O3]:
            pools[(r["paper"], r["level"])].append(r["gpt"])
    out["o3mini_pool"] = {"units": len(pools), "mean_size": round(statistics.fmean(len(v) for v in pools.values()), 1),
                          "pool_mean": round(statistics.fmean(statistics.fmean(v) for v in pools.values()), 3),
                          "best": round(statistics.fmean(max(v) for v in pools.values()), 3)}
    return out


# ---------------------------------------------------------------- 2. pools for the likelihood scorer

def compact(generation: dict[str, Any]) -> str:
    return " ".join(f"{k.replace('_', ' ').capitalize()}: {str(generation.get(k) or '').strip()[:600]}"
                    for k in TEXT_FIELDS if generation.get(k))


def pools(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rng = random.Random(SEED)
    by_unit: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r["models"] == [O3]:
            by_unit[(r["paper"], r["level"])].append(r)
    out_rows = []
    for unit in sorted(by_unit):
        cands = sorted(by_unit[unit], key=lambda r: r["run_id"])
        rng.shuffle(cands)
        for r in cands[:POOL_CAP]:
            out_rows.append({"unit": f"{unit[0]}|{unit[1]}", "paper": unit[0], "level": unit[1],
                             "root": r["root"], "method": r["method"], "run_id": r["run_id"],
                             "closed_book": r["closed_book"], "question": r["query"], "text": compact(r["generation"]),
                             "gpt": r["gpt"], "deep": r["deep"],
                             "lever": r["label"]["lever_match"] if r["label"] else None})
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "pmi_pool.jsonl").open("w") as f:
        for row in out_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"units": len(by_unit), "candidates": len(out_rows)}


# ---------------------------------------------------------------- 3. study types of the earlier papers

def corpus_papers() -> dict[str, list[dict[str, Any]]]:
    """Per unit, the web corpus's seeds in BM25 rank order (experiment 36; every one dated before the paper)."""
    out = {}
    for path in sorted((WEB / "corpora").glob("PMC*/*.json")):
        if path.name.endswith(".phrases.json"):
            continue
        corpus = read(path)
        out[f"{corpus['case']}|{corpus['level']}"] = sorted(corpus["seeds"], key=lambda s: s["rank"])
    return out


def classify(workers: int = 16) -> dict[str, Any]:
    cache_path = OUT / "paper_classes.json"
    cache: dict[str, Any] = read(cache_path) if cache_path.exists() else {}
    wanted = sorted({s["pmcid"] for seeds in corpus_papers().values() for s in seeds} - set(cache))

    def job(pmcid: str) -> tuple[str, dict[str, Any]]:
        paper = read(WEB / "papers" / f"{pmcid}.json")
        user = json.dumps({"title": paper.get("title", ""), "abstract": (paper.get("abstract") or "")[:2500]},
                          ensure_ascii=False)
        raw = lc.trapi_chat_json(CLASSIFIER, CLASSIFY_SYSTEM, user, max_tokens=300, temperature=0.0, retries=8)
        cls = raw.get("class") if isinstance(raw, dict) else None
        return pmcid, {"class": cls if cls in TARGET_TYPES else "other", "study": str((raw or {}).get("study", ""))}

    failed = 0
    with ThreadPoolExecutor(workers) as pool:
        for future in as_completed([pool.submit(job, p) for p in wanted]):
            try:
                pmcid, value = future.result()
                cache[pmcid] = value
            except Exception as error:  # noqa: BLE001 - logged; rerun resumes
                failed += 1
                print(f"[classify] {type(error).__name__}: {str(error)[:150]}", flush=True)
    atomic_json(cache_path, {k: cache[k] for k in sorted(cache)})
    return {"papers": len(cache), "new": len(wanted) - failed, "failed": failed, "classifier": CLASSIFIER,
            "classes": dict(Counter(v["class"] for v in cache.values()).most_common())}


def baserate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    classes = read(OUT / "paper_classes.json")
    seeds = corpus_papers()
    targets = unit_targets(rows)
    o3 = defaultdict(list)
    for r in rows:
        if r["models"] == [O3] and r["label"]:
            o3[(r["paper"], r["level"])].append(r["label"]["intervention_class"])
    out: dict[str, Any] = {}
    for k in (5, 10, 20, 50):
        modal_hit, p_target, o3_hit, units = [], [], [], 0
        for unit, target in sorted(targets.items()):
            ranked = [classes[s["pmcid"]]["class"] for s in seeds.get(f"{unit[0]}|{unit[1]}", [])[:k]
                      if s["pmcid"] in classes]
            if not ranked or not o3.get(unit):
                continue
            units += 1
            counts = Counter(ranked)
            top = max(counts.values())
            modal_hit.append(sum(1 for c, n in counts.items() if n == top and c == target) / sum(
                1 for n in counts.values() if n == top))  # ties share the hit
            p_target.append(counts[target] / len(ranked))
            o3_hit.append(statistics.fmean(c == target for c in o3[unit]))
        out[f"top{k}"] = {"units": units, "literature_modal_class_hit": round(statistics.fmean(modal_hit), 3),
                          "literature_share_of_target_class": round(statistics.fmean(p_target), 3),
                          "o3mini_class_hit": round(statistics.fmean(o3_hit), 3)}
    # The target type's share among all earlier papers vs among the o3-mini hypotheses (does the literature put more
    # mass on the right type than the model does?).
    return out


# ---------------------------------------------------------------- 4. likelihood selection

def spearman(x: list[float], y: list[float]) -> float | None:
    def ranks(v: list[float]) -> list[float]:
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for t in range(i, j + 1):
                r[order[t]] = (i + j) / 2
            i = j + 1
        return r
    if len(x) < 3 or len(set(x)) < 2 or len(set(y)) < 2:
        return None
    rx, ry = ranks(x), ranks(y)
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else None


def pmi_eval() -> dict[str, Any]:
    scores = {}
    for line in (OUT / "pmi_scores.jsonl").read_text().splitlines():
        s = json.loads(line)
        scores[s["run_id"]] = s
    pool = [json.loads(line) for line in (OUT / "pmi_pool.jsonl").read_text().splitlines()]
    out: dict[str, Any] = {"scored": len(scores), "pool": len(pool),
                           "scorer": next(iter(scores.values())).get("model") if scores else None}
    out["simulation"] = simulate(scores) if (OUT / "pmi_pool_sim.jsonl").exists() else None
    for subset in ("all", "closed_book"):
        rows = [r for r in pool if r["run_id"] in scores and (subset == "all" or r["closed_book"])]
        units = defaultdict(list)
        for r in rows:
            units[r["unit"]].append(r)
        res: dict[str, Any] = {"units": len(units), "candidates": len(rows)}
        for signal in ("pmi_mean", "pmi_sum", "logp_cond_mean", "channel"):
            rho_gpt, rho_deep = [], []
            gain_gpt: dict[str, list[float]] = defaultdict(list)
            gain_deep: dict[str, list[float]] = defaultdict(list)
            for unit, cands in units.items():
                if len(cands) < 4:
                    continue
                sig = [scores[c["run_id"]][signal] for c in cands]
                rg = spearman(sig, [c["gpt"] for c in cands])
                if rg is not None:
                    rho_gpt.append(rg)
                deeps = [c for c in cands if c["deep"] is not None]
                rd = spearman([scores[c["run_id"]][signal] for c in deeps], [c["deep"] for c in deeps])
                if rd is not None:
                    rho_deep.append(rd)
                best = max(cands, key=lambda c: (scores[c["run_id"]][signal], c["run_id"]))
                gain_gpt[cands[0]["paper"]].append(best["gpt"] - statistics.fmean(c["gpt"] for c in cands))
                if best["deep"] is not None and deeps:
                    gain_deep[cands[0]["paper"]].append(best["deep"] - statistics.fmean(c["deep"] for c in deeps))
            res[signal] = {"rho_gpt_mean": round(statistics.fmean(rho_gpt), 3) if rho_gpt else None,
                           "rho_deep_mean": round(statistics.fmean(rho_deep), 3) if rho_deep else None,
                           "select_max_vs_pool_mean_gpt": bootstrap(gain_gpt) if gain_gpt else None,
                           "select_max_vs_pool_mean_deep": bootstrap(gain_deep) if gain_deep else None}
        out[subset] = res
    return out


SIM_CONFIGS = ("writer_only_b_o3mini", "writer_only_b_o3mini_r4", "closed_book_o3mini", "web_text_64k_b_o3mini",
               "web_text_chunks_b_o3mini", "text_chunks_b_o3mini")  # the strongest o3-mini configurations


def simpool(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Every run of the strongest o3-mini configurations, for an offline simulation of select-by-likelihood."""
    out_rows = [{"unit": f"{r['paper']}|{r['level']}", "paper": r["paper"], "level": r["level"], "root": r["root"],
                 "method": r["method"], "run_id": r["run_id"], "closed_book": r["closed_book"],
                 "question": r["query"], "text": compact(r["generation"]), "gpt": r["gpt"], "deep": r["deep"],
                 "lever": r["label"]["lever_match"] if r["label"] else None}
                for r in rows if r["method"] in SIM_CONFIGS and O3 in r["models"]
                and all(m == O3 or "Llama" in m for m in r["models"])]  # web corpora: Llama-3.3 search phrases
    with (OUT / "pmi_pool_sim.jsonl").open("w") as f:
        for row in out_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"candidates": len(out_rows), "by_method": dict(Counter(r["method"] for r in out_rows))}


def simulate(scores: dict[str, Any]) -> dict[str, Any]:
    """Per unit: the candidate with the highest signal among the strongest configurations' runs, against the
    incumbent's mean on that unit (paired by paper), and against a random pick from the same pool."""
    pool = [json.loads(line) for line in (OUT / "pmi_pool_sim.jsonl").read_text().splitlines()]
    units: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in pool:
        if r["run_id"] in scores and r["deep"] is not None:
            units[r["unit"]].append(r)
    res: dict[str, Any] = {"units": len(units), "mean_pool_size": round(statistics.fmean(len(v) for v in
                                                                                         units.values()), 1)}
    for signal in ("pmi_mean", "channel", "combo"):
        sel: dict[str, dict[str, list[float]]] = {j: defaultdict(list) for j in ("gpt", "deep")}
        vs_pool: dict[str, dict[str, list[float]]] = {j: defaultdict(list) for j in ("gpt", "deep")}
        for unit, cands in units.items():
            inc = [c for c in cands if c["method"] == "writer_only_b_o3mini"]
            if not inc or len(cands) < 3:
                continue
            if signal == "combo":  # within-unit z-scores of the two signals, summed
                z = {}
                for s in ("pmi_mean", "channel"):
                    v = [scores[c["run_id"]][s] for c in cands]
                    m, sd = statistics.fmean(v), statistics.pstdev(v) or 1.0
                    for c in cands:
                        z[(c["run_id"], s)] = (scores[c["run_id"]][s] - m) / sd
                key = {c["run_id"]: z[(c["run_id"], "pmi_mean")] + z[(c["run_id"], "channel")] for c in cands}
            else:
                key = {c["run_id"]: scores[c["run_id"]][signal] for c in cands}
            best = max(cands, key=lambda c: (key[c["run_id"]], c["run_id"]))
            for j in ("gpt", "deep"):
                sel[j][best["paper"]].append(best[j] - statistics.fmean(c[j] for c in inc))
                vs_pool[j][best["paper"]].append(best[j] - statistics.fmean(c[j] for c in cands))
        res[signal] = {f"vs_incumbent_{j}": bootstrap(sel[j]) for j in ("gpt", "deep")}
        res[signal].update({f"vs_pool_mean_{j}": bootstrap(vs_pool[j]) for j in ("gpt", "deep")})
    pool_vs_inc = {j: defaultdict(list) for j in ("gpt", "deep")}
    for unit, cands in units.items():
        inc = [c for c in cands if c["method"] == "writer_only_b_o3mini"]
        if inc:
            for j in ("gpt", "deep"):
                pool_vs_inc[j][cands[0]["paper"]].append(statistics.fmean(c[j] for c in cands)
                                                         - statistics.fmean(c[j] for c in inc))
    res["random_pick_vs_incumbent"] = {j: bootstrap(pool_vs_inc[j]) for j in ("gpt", "deep")}
    return res


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("decompose", "pools", "simpool", "classify", "baserate", "pmi"))
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.stage == "classify":
        result = classify()
    elif args.stage == "pmi":
        result = pmi_eval()
    else:
        rows = judged_runs()
        result = {"decompose": decompose, "pools": pools, "simpool": simpool, "baserate": baserate}[args.stage](rows)
    atomic_json(OUT / f"{args.stage}.json", result)
    print(json.dumps(result, indent=1)[:6000])


if __name__ == "__main__":
    main()
