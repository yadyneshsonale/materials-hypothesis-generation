"""Pre-registered final analysis (loop.md section 6): test split and all 12 cases.

Also writes the must_obey 6.8 style checks (does the score simply track length, hedging or specificity?) and the
per-paper breakdown to loop/final_robustness.json. These checks are descriptive and were not used to pick methods.
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from typing import Any

import hypo_loop as H
from hypothesis_evidence_v2 import atomic_json
from temporal_eval_v3 import holm_adjust

FINAL = ("trend_ground_b_o3mini", "scaffold_ensemble", "closed_book", "text_chunks", "closed_book_o3mini",
         "writer_only_b_o3mini")
PRIMARY = ("trend_ground_b_o3mini", "closed_book")
SECONDARY = (("trend_ground_b_o3mini", "closed_book_o3mini"), ("trend_ground_b_o3mini", "writer_only_b_o3mini"),
             ("scaffold_ensemble", "closed_book"))


def analyse(split: str) -> dict:
    rows = [r for r in H.load_scored() if r["run"]["method"] in FINAL]
    table = {m: H.summarise(rows, m, split) for m in FINAL}
    out = {"split": split, "table": table, "comparisons": {}}
    for judge in ("gpt", "deep"):
        for metric_name, metric in (("recon", H.recon), ("core", H.core)):
            key = f"{judge}_{metric_name}"
            u = {m: H.unit_scores(rows, m, judge, split, metric) for m in FINAL}
            primary = {"a": PRIMARY[0], "b": PRIMARY[1], **H.paired(u[PRIMARY[0]], u[PRIMARY[1]])}
            secondary = [{"a": a, "b": b, **H.paired(u[a], u[b])} for a, b in SECONDARY]
            for item, adj in zip(secondary, holm_adjust([i.get("p", 1.0) for i in secondary])):
                item["holm_p"] = round(adj, 4)
            out["comparisons"][key] = {"primary": primary, "secondary": secondary}
    atomic_json(H.OUT / f"final_{split}.json", out)
    return out


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(x: list[float], y: list[float]) -> float | None:
    if len(x) < 3 or len(set(x)) < 2 or len(set(y)) < 2:
        return None
    rx, ry = _ranks(x), _ranks(y)
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return round(num / den, 3)


def style_features(row: dict[str, Any]) -> dict[str, float]:
    g = row["run"]["generation"]
    text = " ".join(str(g.get(k, "")) for k in ("hypothesis", "intervention", "mechanism", "predicted_outcome"))
    spec = row["audit"]["specificity"] if row.get("audit") else None
    return {"length_chars": float(len(text)),
            "hedges": float(len(H.HEDGE.findall(f"{g.get('hypothesis', '')} {g.get('predicted_outcome', '')}"))),
            "specificity": statistics.fmean(1.0 if v else 0.0 for v in spec.values()) if spec else float("nan")}


def robustness() -> dict[str, Any]:
    rows = [r for r in H.load_scored() if r["run"]["method"] in FINAL and r["gpt"] and r["run"]["status"] == "ok"]
    out: dict[str, Any] = {"style_vs_score": {}, "primary_style_diffs": {}, "per_paper": {}}
    for judge in ("gpt", "deep"):
        scored = [r for r in rows if r[judge]]
        feats = [style_features(r) for r in scored]
        scores = [H.recon(r[judge]["scores"]) for r in scored]
        block: dict[str, Any] = {}
        for f in ("length_chars", "hedges", "specificity"):
            pairs = [(x[f], s) for x, s in zip(feats, scores) if x[f] == x[f]]
            within = {}
            for m in FINAL:
                mp = [(x[f], s) for x, s, r in zip(feats, scores, scored) if r["run"]["method"] == m and x[f] == x[f]]
                within[m] = spearman([a for a, _ in mp], [b for _, b in mp])
            block[f] = {"pooled_rho": spearman([a for a, _ in pairs], [b for _, b in pairs]), "n": len(pairs),
                        "within_method_rho": within}
        out["style_vs_score"][judge] = block
    for split in ("dev", "test", "all"):
        per_unit: dict[str, dict[tuple[str, str], list[dict[str, float]]]] = {m: defaultdict(list) for m in PRIMARY}
        for r in rows:
            if r["run"]["method"] in PRIMARY and (split == "all" or r["run"]["split"] == split):
                per_unit[r["run"]["method"]][(r["run"]["paper_id"], r["run"]["query_level"])].append(style_features(r))
        diffs = {}
        for f in ("length_chars", "hedges", "specificity"):
            a = {k: statistics.fmean(x[f] for x in v) for k, v in per_unit[PRIMARY[0]].items()}
            b = {k: statistics.fmean(x[f] for x in v) for k, v in per_unit[PRIMARY[1]].items()}
            diffs[f] = {"a_mean": round(statistics.fmean(a.values()), 3), "b_mean": round(statistics.fmean(b.values()), 3),
                        **H.paired(a, b)}
        out["primary_style_diffs"][split] = diffs
        papers: dict[str, dict[str, Any]] = {}
        for judge in ("gpt", "deep"):
            for m in FINAL:
                u = H.unit_scores(rows, m, judge, split)
                by_paper: dict[str, list[float]] = defaultdict(list)
                for (pid, _level), v in u.items():
                    by_paper[pid].append(v)
                for pid, v in sorted(by_paper.items()):
                    papers.setdefault(pid, {}).setdefault(judge, {})[m] = round(statistics.fmean(v), 3)
        out["per_paper"][split] = dict(sorted(papers.items()))
    atomic_json(H.OUT / "final_robustness.json", out)
    return out


if __name__ == "__main__":
    rb = robustness()
    for judge, block in rb["style_vs_score"].items():
        for f, v in block.items():
            print(f"style[{judge}] {f}: pooled rho={v['pooled_rho']} n={v['n']} within={v['within_method_rho']}")
    for split, diffs in rb["primary_style_diffs"].items():
        print(f"primary style diffs ({split}):", {f: (d['a_mean'], d['b_mean'], d.get('diff'), d.get('ci95'))
                                                   for f, d in diffs.items()})
    for split in ("test", "dev", "all"):
        a = analyse(split)
        print(f"== {split}")
        for m, s in a["table"].items():
            print(f"  {m:24s} runs={s['runs']:2d} judged={s['judged']:2d} GPT={s['recon_gpt56']} DS={s['recon_deepseek']} "
                  f"coreG={s['core_gpt56']} coreD={s['core_deepseek']}")
        for key, c in a["comparisons"].items():
            p = c["primary"]
            print(f"  [{key}] primary {p['a']} - {p['b']}: {p.get('diff')} {p.get('ci95')} p={p.get('p')}")
            for sc in c["secondary"]:
                print(f"     secondary {sc['a']} - {sc['b']}: {sc.get('diff')} {sc.get('ci95')} Holm p={sc.get('holm_p')}")
