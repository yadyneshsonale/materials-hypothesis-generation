"""Experiment 31 (loop.md section 14.1): SciMON-style input (benchmark v4) against benchmark v3.1, pre-registered.

Primary: for each configuration, v4 minus v3.1 GPT-5.6 reconstruction per paper (v3.1 = mean of its three levels),
paired over papers, paper-clustered bootstrap 95% CI, exact sign test, Holm across the configurations.
Secondary: v4 against each v3.1 level; configuration ranking on v4; DeepSeek and core; leakage audit (answer-word
overlap of the inputs and its rank correlation with the v4 score); results without flagged cases.
Reads run and judgment files directly from loop/ (v3.1) and loop_v4_scimon/ (v4). Output: loop_v4_scimon/analysis.json
"""

from __future__ import annotations

import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from hypothesis_evidence_v2 import atomic_json
from stage_metrics import HEDGE

ROOT = Path(__file__).resolve().parent
E = ROOT / "experiments" / "high_temperature_hea_qwen35b"
V31_ROOT, V4_ROOT = E / "loop", E / "loop_v4_scimon"
V4_CASES = E / "benchmark_v4_scimon" / "cases"
CONFIGS = ("closed_book", "closed_book_o3mini", "writer_only_b_o3mini", "text_chunks_b_o3mini")
V31_LEVELS = ("broad", "problem_constrained", "expert_context")
V31_SPLITS = {"validation", "dev", "test", "test2", "test3"}
DIMS = ("intervention_reconstruction", "condition_agreement", "mechanism_agreement", "outcome_agreement")
BOOTSTRAP = 10_000
SEED = 20261026


def recon(scores: dict[str, int]) -> float:
    return statistics.fmean(scores[d] for d in DIMS)


def core(scores: dict[str, int]) -> float:
    return statistics.fmean(scores[d] for d in ("intervention_reconstruction", "mechanism_agreement"))


def load(root: Path, method: str, judge: str, metric: Callable[[dict[str, int]], float],
         levels: tuple[str, ...] | None) -> dict[str, dict[str, list[float]]]:
    """{paper: {level: [score per sample]}} for successful, judged runs."""
    folder = "gpt56" if judge == "gpt" else "deepseek"
    out: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for path in sorted((root / method / "runs").glob("PMC*.json")):
        run = json.loads(path.read_text())
        if run.get("status") != "ok" or (levels and run["query_level"] not in levels):
            continue
        if root == V31_ROOT and run.get("benchmark", "v3.1") not in ("v3.1", "test2", "test3"):
            continue
        judgment = root / method / "judgments" / folder / path.name
        if judgment.exists():
            out[run["paper_id"]][run["query_level"]].append(metric(json.loads(judgment.read_text())["scores"]))
    return out


def per_paper(data: dict[str, dict[str, list[float]]], level: str | None = None) -> dict[str, float]:
    res = {}
    for pid, by_level in data.items():
        if level:
            if by_level.get(level):
                res[pid] = statistics.fmean(by_level[level])
        else:
            means = [statistics.fmean(v) for v in by_level.values() if v]
            if means:
                res[pid] = statistics.fmean(means)
    return res


def paired(a: dict[str, float], b: dict[str, float], papers: set[str] | None = None) -> dict[str, Any]:
    keys = sorted(k for k in set(a) & set(b) if papers is None or k in papers)
    diffs = [a[k] - b[k] for k in keys]
    if not diffs:
        return {"papers": 0}
    rng = random.Random(SEED)
    boots = sorted(statistics.fmean(rng.choice(diffs) for _ in diffs) for _ in range(BOOTSTRAP))
    up, down = sum(d > 0 for d in diffs), sum(d < 0 for d in diffs)
    n = up + down
    tail = sum(math.comb(n, k) for k in range(0, min(up, down) + 1)) / 2 ** n if n else 1.0
    return {"papers": len(keys), "a_mean": round(statistics.fmean(a[k] for k in keys), 3),
            "b_mean": round(statistics.fmean(b[k] for k in keys), 3), "diff": round(statistics.fmean(diffs), 3),
            "ci95": [round(boots[int(0.025 * BOOTSTRAP)], 3), round(boots[int(0.975 * BOOTSTRAP) - 1], 3)],
            "up": up, "down": down, "p": round(min(1.0, 2 * tail), 4)}


def holm(ps: list[float]) -> list[float]:
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adjusted, running = [0.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(ps) - rank) * ps[i]))
        adjusted[i] = round(running, 4)
    return adjusted


def spearman(x: list[float], y: list[float]) -> float | None:
    def ranks(v: list[float]) -> list[float]:
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    if len(x) < 3 or len(set(x)) < 2 or len(set(y)) < 2:
        return None
    rx, ry = ranks(x), ranks(y)
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    return round(num / math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)), 3)


def flag_group(case: dict[str, Any]) -> str:
    """Partition by the gate result: clean; flagged but passed the gate (no background or no relation); failed."""
    flags = set(case["flags"])
    return "clean" if not flags else "failed_gate" if "failed_gate" in flags else "flagged_passed_gate"


def style_features(run: dict[str, Any], audit: dict[str, Any] | None) -> dict[str, float]:
    """Same definitions as loop_final.style_features (must_obey.md 6.8)."""
    g = run["generation"]
    text = " ".join(str(g.get(k, "")) for k in ("hypothesis", "intervention", "mechanism", "predicted_outcome"))
    spec = audit["specificity"] if audit else None
    return {"length_chars": float(len(text)),
            "hedges": float(len(HEDGE.findall(f"{g.get('hypothesis', '')} {g.get('predicted_outcome', '')}"))),
            "specificity": statistics.fmean(1.0 if v else 0.0 for v in spec.values()) if spec else float("nan")}


def style(cases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """must_obey.md 6.8: does the v4 score simply track length, hedging or specificity? Per configuration: mean style
    features on v4 and v3.1 (same papers), and Spearman rho between each feature and the GPT-5.6 score on v4 runs."""
    out: dict[str, Any] = {}
    for m in CONFIGS:
        block: dict[str, Any] = {}
        for label, root, levels in (("v4", V4_ROOT, ("scimon",)), ("v3.1", V31_ROOT, V31_LEVELS)):
            feats, scores = [], []
            for path in sorted((root / m / "runs").glob("PMC*.json")):
                run = json.loads(path.read_text())
                if run.get("status") != "ok" or run["query_level"] not in levels or run["paper_id"] not in cases:
                    continue
                if root == V31_ROOT and run.get("benchmark", "v3.1") not in ("v3.1", "test2", "test3"):
                    continue
                judgment = root / m / "judgments" / "gpt56" / path.name
                audit_path = root / m / "audit" / path.name
                if not judgment.exists():
                    continue
                feats.append(style_features(run, json.loads(audit_path.read_text()) if audit_path.exists() else None))
                scores.append(recon(json.loads(judgment.read_text())["scores"]))
            entry: dict[str, Any] = {"runs": len(feats),
                                     "audited_runs": sum(1 for x in feats if x["specificity"] == x["specificity"])}
            for f in ("length_chars", "hedges", "specificity"):
                pairs = [(x[f], s) for x, s in zip(feats, scores) if x[f] == x[f]]
                entry[f] = round(statistics.fmean(a for a, _ in pairs), 3) if pairs else None
                if label == "v4":
                    entry[f"rho_{f}_vs_gpt56"] = spearman([a for a, _ in pairs], [b for _, b in pairs])
            block[label] = entry
        out[m] = block
    return out


def exploratory(cases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Added after the results, to apply the pre-registered interpretation rule (check leakage before crediting the
    format): v4 - v3.1 by flag group and by the checker's steers_to_answer verdict, and per judge dimension."""
    groups = {pid: flag_group(c) for pid, c in cases.items()}
    steers = {pid: "steers" if c["queries"]["scimon"]["steers_to_answer"] else "does_not_steer"
              for pid, c in cases.items()}
    out: dict[str, Any] = {}
    for judge in ("gpt", "deep"):
        block: dict[str, Any] = {}
        for m in CONFIGS:
            v4 = per_paper(load(V4_ROOT, m, judge, recon, ("scimon",)))
            v31 = per_paper(load(V31_ROOT, m, judge, recon, V31_LEVELS))
            row: dict[str, Any] = {}
            for label, mapping in (("flag_group", groups), ("checker", steers)):
                for g in sorted(set(mapping.values())):
                    row[f"{label}:{g}"] = paired(v4, v31, {p for p, v in mapping.items() if v == g})
            dims = {}
            for dim in DIMS:
                a = per_paper(load(V4_ROOT, m, judge, lambda s, d=dim: s[d], ("scimon",)))
                b = per_paper(load(V31_ROOT, m, judge, lambda s, d=dim: s[d], V31_LEVELS))
                dims[dim] = paired(a, b)
            row["dimensions"] = dims
            block[m] = row
        out[judge] = block
    return out


def main() -> None:
    cases = {p.stem: json.loads(p.read_text()) for p in sorted(V4_CASES.glob("PMC*.json"))}
    unflagged = {pid for pid, c in cases.items() if not c["flags"]}
    result: dict[str, Any] = {"cases": len(cases), "unflagged": len(unflagged),
                              "flags": {pid: c["flags"] for pid, c in cases.items() if c["flags"]}}
    for judge in ("gpt", "deep"):
        for name, metric in (("recon", recon), ("core", core)):
            key = f"{judge}_{name}"
            v4 = {m: per_paper(load(V4_ROOT, m, judge, metric, ("scimon",))) for m in CONFIGS}
            v31_data = {m: load(V31_ROOT, m, judge, metric, V31_LEVELS) for m in CONFIGS}
            v31 = {m: per_paper(v31_data[m]) for m in CONFIGS}
            primary = [{"config": m, **paired(v4[m], v31[m])} for m in CONFIGS]
            for item, adj in zip(primary, holm([i.get("p", 1.0) for i in primary])):
                item["holm_p"] = adj
            block = {"v4_minus_v31": primary,
                     "v4_minus_v31_unflagged": [{"config": m, **paired(v4[m], v31[m], unflagged)} for m in CONFIGS],
                     "v4_minus_v31_level": {m: {lvl: paired(v4[m], per_paper(v31_data[m], lvl)) for lvl in V31_LEVELS}
                                            for m in CONFIGS},
                     "v4_means": {m: round(statistics.fmean(v4[m].values()), 3) if v4[m] else None for m in CONFIGS},
                     "v4_ranking": {f"{a} - {b}": paired(v4[a], v4[b]) for a, b in (
                         ("writer_only_b_o3mini", "closed_book"), ("closed_book_o3mini", "closed_book"),
                         ("writer_only_b_o3mini", "closed_book_o3mini"),
                         ("text_chunks_b_o3mini", "writer_only_b_o3mini"))}}
            if judge == "gpt" and name == "recon":
                overlap = {pid: c["queries"]["scimon"]["overlap"] for pid, c in cases.items()}
                block["leakage_rho_overlap_vs_v4_score"] = {
                    m: spearman([overlap[p] for p in sorted(v4[m]) if p in overlap],
                                [v4[m][p] for p in sorted(v4[m]) if p in overlap]) for m in CONFIGS}
            result[key] = block
    v31_overlap = defaultdict(list)
    for path in sorted((E / "benchmark_v3_1" / "cases").glob("PMC*.json")) + \
            sorted((E / "benchmark_test2" / "cases").glob("PMC*.json")) + \
            sorted((E / "benchmark_test3" / "cases").glob("PMC*.json")):
        case = json.loads(path.read_text())
        for lvl in V31_LEVELS:
            v31_overlap[lvl].append(case["queries"][lvl]["overlap"])
    result["answer_word_overlap"] = {"v4_scimon": round(statistics.fmean(c["queries"]["scimon"]["overlap"]
                                                                         for c in cases.values()), 3),
                                     **{f"v3.1_{lvl}": round(statistics.fmean(v), 3) for lvl, v in v31_overlap.items()}}
    result["exploratory_not_preregistered"] = exploratory(cases)
    result["style_must_obey_6_8"] = style(cases)
    atomic_json(V4_ROOT / "analysis.json", result)
    g = result["gpt_recon"]
    print("v4 means (GPT-5.6):", g["v4_means"])
    for item in g["v4_minus_v31"]:
        print(f"  {item['config']:22s} v4 {item.get('a_mean')} vs v3.1 {item.get('b_mean')}: {item.get('diff')} "
              f"{item.get('ci95')} up/down {item.get('up')}/{item.get('down')} Holm {item.get('holm_p')} "
              f"papers {item.get('papers')}")
    print("unflagged:", [(i["config"], i.get("diff"), i.get("ci95"), i.get("papers")) for i in g["v4_minus_v31_unflagged"]])
    print("ranking on v4:", {k: (v.get("diff"), v.get("ci95")) for k, v in g["v4_ranking"].items()})
    print("DeepSeek v4 - v3.1:", [(i["config"], i.get("diff"), i.get("ci95")) for i in result["deep_recon"]["v4_minus_v31"]])
    print("overlap:", result["answer_word_overlap"], "rho:", g["leakage_rho_overlap_vs_v4_score"])
    print("exploratory (not pre-registered), v4 - v3.1 by group:")
    for judge, block in result["exploratory_not_preregistered"].items():
        for m, row in block.items():
            print(f"  {judge:4s} {m:22s}", {k: (v.get("papers"), v.get("diff"), v.get("ci95")) for k, v in row.items()
                                           if k != "dimensions"})
            print(f"  {'':4s} {'':22s} dims", {k.split("_")[0]: (v.get("a_mean"), v.get("b_mean"), v.get("diff"),
                                                                 v.get("ci95")) for k, v in row["dimensions"].items()})
    print("style (must_obey 6.8):")
    for m, block in result["style_must_obey_6_8"].items():
        print(f"  {m:22s}", block)


if __name__ == "__main__":
    main()
