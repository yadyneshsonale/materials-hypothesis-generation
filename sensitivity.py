"""Experiment 29 (loop.md section 12): sensitivity of the score to one input at a time, around the recommended
configuration (o3-mini with WRITER_B). Pre-registered analysis:

  A. number of papers as context (top-N paper cards): N = 0, 1, 3, 10, 30
  B. amount of raw text (top chunks): 0, 4k, 16k, 64k characters
  C. relevance vs volume: 10 relevant vs 10 random papers
  D. reasoning effort: low, medium, high
  E. detail in the question (existing runs): broad, problem_constrained, expert_context, on all 36 papers

Dose 0 (closed-book) pools the incumbent and its fresh-sample replicate (the same configuration, 4 samples per
unit). Trend test: within each paper, the mean score per dose; Spearman rho between dose and score; the mean rho
over papers; a two-sided p-value from 10,000 within-paper permutations (fixed seed). Output: loop/sensitivity.json.
"""

from __future__ import annotations

import random
import statistics
from collections import defaultdict
from typing import Any, Callable

import hypo_loop as H
from hypothesis_evidence_v2 import atomic_json
from loop_final import spearman

CLOSED = ("writer_only_b_o3mini", "writer_only_b_o3mini_r3")
FACTORS: dict[str, list[tuple[str, tuple[str, ...]]]] = {
    "A_papers": [("0", CLOSED), ("1", ("papers_n1_b_o3mini",)), ("3", ("papers_n3_b_o3mini",)),
                 ("10", ("papers_n10_b_o3mini",)), ("30", ("papers_n30_b_o3mini",))],
    "B_text_chars": [("0", CLOSED), ("4000", ("text_4k_b_o3mini",)), ("16000", ("text_chunks_b_o3mini",)),
                     ("64000", ("text_64k_b_o3mini",))],
    "D_effort": [("low", ("writer_only_b_o3mini_low",)), ("medium", CLOSED), ("high", ("writer_only_b_o3mini_high",))],
}
CONTRASTS = (("C_relevance", ("papers_n10_b_o3mini",), ("papers_random10_b_o3mini",)),)
DIMS = ("intervention_reconstruction", "condition_agreement", "mechanism_agreement", "outcome_agreement")
PERMUTATIONS = 10_000
SEED = 20261025


def unit_means(rows: list[dict[str, Any]], methods: tuple[str, ...], judge: str, splits: set[str],
               metric: Callable[[dict[str, int]], float] = H.recon) -> dict[tuple[str, str], float]:
    per: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in rows:
        if r["run"]["method"] in methods and r["run"]["split"] in splits and r.get(judge):
            per[(r["run"]["paper_id"], r["run"]["query_level"])].append(metric(r[judge]["scores"]))
    return {k: statistics.fmean(v) for k, v in sorted(per.items())}


def paper_means(units: dict[tuple[str, str], float]) -> dict[str, float]:
    per: dict[str, list[float]] = defaultdict(list)
    for (pid, _level), v in units.items():
        per[pid].append(v)
    return {pid: statistics.fmean(v) for pid, v in sorted(per.items())}


def trend_test(per_dose: list[dict[str, float]], seed: int = SEED) -> dict[str, Any]:
    """Mean within-paper Spearman rho between dose order and score, with a within-paper permutation p-value."""
    papers = sorted(set.intersection(*[set(d) for d in per_dose]))
    doses = list(range(len(per_dose)))
    vectors = [[per_dose[i][p] for i in doses] for p in papers]

    def stat(vs: list[list[float]]) -> float:
        rhos = [spearman(doses, v) for v in vs]
        rhos = [r for r in rhos if r is not None]
        return statistics.fmean(rhos) if rhos else 0.0

    observed = stat(vectors)
    rng = random.Random(seed)
    extreme = 0
    for _ in range(PERMUTATIONS):
        shuffled = []
        for v in vectors:
            w = list(v)
            rng.shuffle(w)
            shuffled.append(w)
        extreme += abs(stat(shuffled)) >= abs(observed) - 1e-12
    return {"papers": len(papers), "mean_rho": round(observed, 3), "p_two_sided": round((extreme + 1) / (PERMUTATIONS + 1), 4)}


def dose_block(rows: list[dict[str, Any]], levels: list[tuple[str, tuple[str, ...]]], splits: set[str],
               reference: int = 0) -> dict[str, Any]:
    out: dict[str, Any] = {"levels": {}, "trend": {}}
    for judge in ("gpt", "deep"):
        for name, metric in (("recon", H.recon), ("core", H.core)):
            units = [unit_means(rows, methods, judge, splits, metric) for _, methods in levels]
            out["trend"][f"{judge}_{name}"] = trend_test([paper_means(u) for u in units])
            for (label, methods), u in zip(levels, units):
                entry = out["levels"].setdefault(label, {"methods": list(methods)})
                entry[f"{judge}_{name}"] = round(statistics.fmean(u.values()), 3) if u else None
                entry[f"{judge}_{name}_units"] = len(u)
                if label != levels[reference][0]:
                    entry[f"{judge}_{name}_vs_{levels[reference][0]}"] = H.paired(u, units[reference])
    for label, methods in levels:
        rs = [r for r in rows if r["run"]["method"] in methods and r["run"]["split"] in splits and r["gpt"]]
        entry = out["levels"][label]
        entry.update({d[:4]: round(statistics.fmean(r["gpt"]["scores"][d] for r in rs), 3) for d in DIMS})
        entry["chars_in_per_run"] = round(statistics.fmean(r["run"]["chars_in"] for r in rs))
        entry["cited_per_run"] = round(statistics.fmean(len(r["run"]["cited_ids"]) for r in rs), 2)
        entry["calls_per_run"] = round(statistics.fmean(r["run"]["llm_calls"] for r in rs), 2)
    return out


def main() -> None:
    rows = H.load_scored()
    dev3 = H.SPLITS["dev3"]
    result: dict[str, Any] = {"split": "dev3", "factors": {}, "contrasts": {}}
    for name, levels in FACTORS.items():
        result["factors"][name] = dose_block(rows, levels, dev3, reference=1 if name == "D_effort" else 0)
    for name, a, b in CONTRASTS:
        result["contrasts"][name] = {f"{judge}_{m}": H.paired(unit_means(rows, a, judge, dev3, metric),
                                                              unit_means(rows, b, judge, dev3, metric))
                                     for judge in ("gpt", "deep") for m, metric in (("recon", H.recon),
                                                                                    ("core", H.core))}
    # E. Detail in the question: the incumbent on every split where it ran (36 papers).
    all36 = {"dev", "test", "test2", "test3"}
    e: dict[str, Any] = {}
    for judge in ("gpt", "deep"):
        units = unit_means(rows, ("writer_only_b_o3mini",), judge, all36)
        by_level = [{pid: v for (pid, lvl), v in units.items() if lvl == level} for level in H.QUERY_LEVELS]
        e[judge] = {"means": {lvl: round(statistics.fmean(d.values()), 3) for lvl, d in zip(H.QUERY_LEVELS, by_level)},
                    "trend": trend_test(by_level)}
    result["E_question_detail"] = e
    atomic_json(H.OUT / "sensitivity.json", result)
    for name, block in result["factors"].items():
        print(f"== {name}")
        for label, entry in block["levels"].items():
            print(f"  {label:>6s}: GPT={entry['gpt_recon']} DS={entry['deep_recon']} core={entry['gpt_core']} "
                  f"I/C/M/O={entry['inte']}/{entry['cond']}/{entry['mech']}/{entry['outc']} "
                  f"chars_in={entry['chars_in_per_run']} cited={entry['cited_per_run']} units={entry['gpt_recon_units']}")
        print("  trend:", {k: (v["mean_rho"], v["p_two_sided"]) for k, v in block["trend"].items()})
    print("== contrasts:", {k: {m: (v.get("diff"), v.get("ci95")) for m, v in c.items()}
                           for k, c in result["contrasts"].items()})
    print("== E:", {j: (v["means"], v["trend"]["mean_rho"], v["trend"]["p_two_sided"]) for j, v in e.items()})


if __name__ == "__main__":
    main()
