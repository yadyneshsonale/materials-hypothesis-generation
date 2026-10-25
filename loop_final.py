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

ROUNDS: dict[str, dict[str, Any]] = {
    # Round 1 (loop.md section 6): run once on the 4-paper test split.
    "round1": {"final": ("trend_ground_b_o3mini", "scaffold_ensemble", "closed_book", "text_chunks",
                         "closed_book_o3mini", "writer_only_b_o3mini"),
               "primary": ("trend_ground_b_o3mini", "closed_book"),
               "secondary": (("trend_ground_b_o3mini", "closed_book_o3mini"),
                             ("trend_ground_b_o3mini", "writer_only_b_o3mini"), ("scaffold_ensemble", "closed_book")),
               "splits": ("test", "dev", "all"), "prefix": "final"},
    # Round 2 (loop.md sections 10.1 and 10.5): no F2 qualified on dev, so the primary is the round-1 method
    # against closed_book on the fresh test2 set; run once.
    "round2": {"final": ("trend_ground_b_o3mini", "closed_book", "text_chunks", "closed_book_o3mini",
                         "writer_only_b_o3mini"),
               "primary": ("trend_ground_b_o3mini", "closed_book"),
               "secondary": (("writer_only_b_o3mini", "closed_book"), ("closed_book_o3mini", "closed_book")),
               "exploratory": (("trend_ground_b_o3mini", "closed_book_o3mini"),
                               ("trend_ground_b_o3mini", "writer_only_b_o3mini"), ("text_chunks", "closed_book")),
               "splits": ("test2",), "prefix": "final2"},
    # Round 3 (loop.md sections 11.1 and 11.6): F3 chosen on dev3 by rule; run once on the fresh test3 set.
    "round3": {"final": ("text_chunks_mbr_b_o3mini", "writer_only_b_o3mini", "trend_ground_b_o3mini", "closed_book"),
               "primary": ("text_chunks_mbr_b_o3mini", "writer_only_b_o3mini"),
               "secondary": (("text_chunks_mbr_b_o3mini", "closed_book"), ("writer_only_b_o3mini", "closed_book"),
                             ("trend_ground_b_o3mini", "closed_book")),
               "exploratory": (("text_chunks_mbr_b_o3mini", "trend_ground_b_o3mini"),),
               "splits": ("test3",), "prefix": "final3"},
}
FINAL = ROUNDS["round1"]["final"]
PRIMARY = ROUNDS["round1"]["primary"]
SECONDARY = ROUNDS["round1"]["secondary"]

# Round 3 (loop.md section 11): development on dev3 against the incumbent's fresh-sample replicate.
ROUND3_REFERENCE = "writer_only_b_o3mini_r3"
ROUND3_CANDIDATES = ("writer_only_b_o3mini", "forecast_writer_b_o3mini", "analogy_writer_b_o3mini",
                     "writer_only_b_o3mini_high", "writer_mbr_b_o3mini", "text_chunks_b_o3mini", "text_chunks_mbr_b_o3mini",
                     "trend_ground_b_o3mini", "closed_book_o3mini", "closed_book")


def dev3_compare(candidates: tuple[str, ...] = ROUND3_CANDIDATES, reference: str = ROUND3_REFERENCE) -> dict:
    """Every candidate against the reference on dev3 (24 papers), both judges, reconstruction and core."""
    rows = H.load_scored()
    out: dict[str, Any] = {"reference": reference, "split": "dev3", "methods": {}}
    for m in (reference, *candidates):
        rs = [r for r in rows if r["run"]["method"] == m and r["run"]["split"] in H.SPLITS["dev3"]]
        entry: dict[str, Any] = {"runs": len(rs), "judged_gpt": sum(1 for r in rs if r["gpt"]),
                                 "judged_deep": sum(1 for r in rs if r["deep"])}
        for judge in ("gpt", "deep"):
            for name, metric in (("recon", H.recon), ("core", H.core)):
                u = H.unit_scores(rows, m, judge, "dev3", metric)
                entry[f"{judge}_{name}"] = round(statistics.fmean(u.values()), 3) if u else None
                if m != reference:
                    entry[f"{judge}_{name}_vs_reference"] = H.paired(u, H.unit_scores(rows, reference, judge, "dev3",
                                                                                      metric))
        out["methods"][m] = entry
    atomic_json(H.OUT / "round3_dev3.json", out)
    return out


def analyse(split: str, round_: str = "round1", papers: set[str] | None = None, tag: str = "") -> dict:
    cfg = ROUNDS[round_]
    final, primary_pair, secondary_pairs = cfg["final"], cfg["primary"], cfg["secondary"]
    rows = [r for r in H.load_scored() if r["run"]["method"] in final
            and (papers is None or r["run"]["paper_id"] in papers)]
    table = {m: H.summarise(rows, m, split) for m in final}
    out = {"split": split, "table": table, "comparisons": {}}
    if papers is not None:
        out["papers"] = sorted(papers)
    for judge in ("gpt", "deep"):
        for metric_name, metric in (("recon", H.recon), ("core", H.core)):
            key = f"{judge}_{metric_name}"
            u = {m: H.unit_scores(rows, m, judge, split, metric) for m in final}
            primary = {"a": primary_pair[0], "b": primary_pair[1], **H.paired(u[primary_pair[0]], u[primary_pair[1]])}
            secondary = [{"a": a, "b": b, **H.paired(u[a], u[b])} for a, b in secondary_pairs]
            for item, adj in zip(secondary, holm_adjust([i.get("p", 1.0) for i in secondary])):
                item["holm_p"] = round(adj, 4)
            out["comparisons"][key] = {"primary": primary, "secondary": secondary}
            if cfg.get("exploratory"):
                out["comparisons"][key]["exploratory"] = [{"a": a, "b": b, **H.paired(u[a], u[b])}
                                                          for a, b in cfg["exploratory"]]
    atomic_json(H.OUT / f"{cfg['prefix']}_{split}{tag}.json", out)
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


def robustness(round_: str = "round1") -> dict[str, Any]:
    cfg = ROUNDS[round_]
    final, primary_pair = cfg["final"], cfg["primary"]
    rows = [r for r in H.load_scored() if r["run"]["method"] in final and r["gpt"] and r["run"]["status"] == "ok"
            and any(r["run"]["split"] in H.SPLITS[s] for s in cfg["splits"])]
    out: dict[str, Any] = {"style_vs_score": {}, "primary_style_diffs": {}, "per_paper": {}}
    for judge in ("gpt", "deep"):
        scored = [r for r in rows if r[judge]]
        feats = [style_features(r) for r in scored]
        scores = [H.recon(r[judge]["scores"]) for r in scored]
        block: dict[str, Any] = {}
        for f in ("length_chars", "hedges", "specificity"):
            pairs = [(x[f], s) for x, s in zip(feats, scores) if x[f] == x[f]]
            within = {}
            for m in final:
                mp = [(x[f], s) for x, s, r in zip(feats, scores, scored) if r["run"]["method"] == m and x[f] == x[f]]
                within[m] = spearman([a for a, _ in mp], [b for _, b in mp])
            block[f] = {"pooled_rho": spearman([a for a, _ in pairs], [b for _, b in pairs]), "n": len(pairs),
                        "within_method_rho": within}
        out["style_vs_score"][judge] = block
    for split in sorted(cfg["splits"], key=("dev", "test", "all", "test2", "test3", "dev3").index):
        per_unit: dict[str, dict[tuple[str, str], list[dict[str, float]]]] = {m: defaultdict(list) for m in primary_pair}
        for r in rows:
            if r["run"]["method"] in primary_pair and r["run"]["split"] in H.SPLITS[split]:
                per_unit[r["run"]["method"]][(r["run"]["paper_id"], r["run"]["query_level"])].append(style_features(r))
        diffs = {}
        for f in ("length_chars", "hedges", "specificity"):
            a = {k: statistics.fmean(x[f] for x in v) for k, v in per_unit[primary_pair[0]].items()}
            b = {k: statistics.fmean(x[f] for x in v) for k, v in per_unit[primary_pair[1]].items()}
            if not a or not b:
                continue
            diffs[f] = {"a_mean": round(statistics.fmean(a.values()), 3), "b_mean": round(statistics.fmean(b.values()), 3),
                        **H.paired(a, b)}
        out["primary_style_diffs"][split] = diffs
        papers: dict[str, dict[str, Any]] = {}
        for judge in ("gpt", "deep"):
            for m in final:
                u = H.unit_scores(rows, m, judge, split)
                by_paper: dict[str, list[float]] = defaultdict(list)
                for (pid, _level), v in u.items():
                    by_paper[pid].append(v)
                for pid, v in sorted(by_paper.items()):
                    papers.setdefault(pid, {}).setdefault(judge, {})[m] = round(statistics.fmean(v), 3)
        out["per_paper"][split] = dict(sorted(papers.items()))
    name = "final_robustness.json" if round_ == "round1" else f"{cfg['prefix']}_robustness.json"
    atomic_json(H.OUT / name, out)
    return out


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--round", default="round1", choices=tuple(ROUNDS))
    args = parser.parse_args()
    rb = robustness(args.round)
    for judge, block in rb["style_vs_score"].items():
        for f, v in block.items():
            print(f"style[{judge}] {f}: pooled rho={v['pooled_rho']} n={v['n']} within={v['within_method_rho']}")
    for split, diffs in rb["primary_style_diffs"].items():
        print(f"primary style diffs ({split}):", {f: (d['a_mean'], d['b_mean'], d.get('diff'), d.get('ci95'))
                                                   for f, d in diffs.items()})
    for split in ROUNDS[args.round]["splits"]:
        a = analyse(split, args.round)
        _print(split, a)
    if args.round == "round2":  # pre-registered separate report: papers after GPT-5.6's cutoff (loop.md 10.5)
        late = {pid for pid, c in H.cases().items() if c["split"] == "test2" and c["publication_date"] >= "2026-02-17"}
        _print(f"test2, {len(late)} papers after 2026-02-16", analyse("test2", "round2", papers=late,
                                                                       tag="_after_gpt56_cutoff"))


def _print(label: str, a: dict) -> None:
    print(f"== {label}")
    for m, s in a["table"].items():
        print(f"  {m:28s} runs={s['runs']:2d} judged={s['judged']:2d} GPT={s['recon_gpt56']} DS={s['recon_deepseek']} "
              f"coreG={s['core_gpt56']} coreD={s['core_deepseek']}")
    for key, c in a["comparisons"].items():
        p = c["primary"]
        print(f"  [{key}] primary {p['a']} - {p['b']}: {p.get('diff')} {p.get('ci95')} "
              f"up/down={p.get('papers_up')}/{p.get('papers_down')} p={p.get('p')}")
        for sc in c["secondary"]:
            print(f"     secondary {sc['a']} - {sc['b']}: {sc.get('diff')} {sc.get('ci95')} Holm p={sc.get('holm_p')}")
        for sc in c.get("exploratory", []):
            print(f"     exploratory {sc['a']} - {sc['b']}: {sc.get('diff')} {sc.get('ci95')} p={sc.get('p')}")


if __name__ == "__main__":
    main()
