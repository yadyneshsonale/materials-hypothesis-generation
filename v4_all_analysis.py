"""Experiment 32 (loop.md 15.1): every experiment re-run on the SciMON-style input (benchmark v4), pre-registered.

Family H: the harness, loop/ (v3.1) vs loop_v4_scimon/ (v4), 52 configurations, 36 papers.
- H1: v4 - v3.1 per configuration, with Holm across all 52.
- H2: v4 leaderboard, and each configuration vs the Llama baseline and vs o3-mini closed-book.
- H3: rank agreement of the two formats.
- H4: earlier conclusions re-tested on v4.
- H5: H2 and H4 on the unflagged and the non-steering papers.
- H6: leakage rho.

Family S: the experiment-21 suite, rerun_v3/ (v3) vs rerun_v4_scimon/ (v4), 26 arms, 12 papers.
- S1: v4 - v3 per arm.
- S2: each arm vs raw text chunks and vs closed-book, on v4 and on v3.
- S3: does any arm beat closed-book?

Outputs: loop_v4_scimon/analysis_all.json and analysis_all.md; rerun_v4_scimon/comparison/analysis.json and tables.md.
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import compare_rerun as CR
import v4_scimon_analysis as A
from hypothesis_evidence_v2 import atomic_json

E = A.E
REPLICATES = {"trend_ground_b_o3mini_r2", "writer_only_b_o3mini_r3"}
LLAMA, O3_CLOSED, WRITER = "closed_book", "closed_book_o3mini", "writer_only_b_o3mini"
SENSITIVITY = {"papers_n1_b_o3mini": WRITER, "papers_n3_b_o3mini": WRITER, "papers_n10_b_o3mini": WRITER,
               "papers_n30_b_o3mini": WRITER, "papers_random10_b_o3mini": "papers_n10_b_o3mini",
               "text_4k_b_o3mini": WRITER, "text_64k_b_o3mini": WRITER, "writer_only_b_o3mini_low": WRITER,
               "writer_only_b_o3mini_high": WRITER}
V3_ROOT, V4_SUITE = E / "rerun_v3", E / "rerun_v4_scimon"
SUITE_TEXT, SUITE_CLOSED = "exp14_rubrics:text_chunks", "exp14_rubrics:closed_book"
JUDGES = ("gpt", "deep")


def harness_configs() -> list[str]:
    return sorted(p.name for p in A.V31_ROOT.iterdir() if (p / "runs").is_dir() and p.name not in REPLICATES)


def holm_family(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for item, adj in zip(items, A.holm([i.get("p", 1.0) for i in items])):
        item["holm_p"] = adj
    return items


def significant(item: dict[str, Any]) -> int:
    """+1 / -1 when Holm p < 0.05 in that direction, else 0."""
    if not item.get("papers") or item.get("holm_p", 1.0) >= 0.05:
        return 0
    return 1 if item["diff"] > 0 else -1


def compare_all(scores: dict[str, dict[str, float]], configs: list[str], base: str,
                papers: set[str] | None = None) -> list[dict[str, Any]]:
    return holm_family([{"config": m, "vs": base, **A.paired(scores[m], scores[base], papers)}
                        for m in configs if m != base and m in scores and base in scores])


def subsets(cases: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
    return {"unflagged": {p for p, c in cases.items() if not c["flags"]},
            "non_steering": {p for p, c in cases.items() if not c["queries"]["scimon"]["steers_to_answer"]}}


def style_all(configs: list[str]) -> dict[str, Any]:
    """must_obey.md 6.8 for every configuration: does the v4 score simply track length, hedging or specificity?
    Mean features on v4 and v3.1, and Spearman rho of each feature with the GPT-5.6 score, within configurations
    and pooled over all v4 runs. Same feature definitions as experiment 31 (v4_scimon_analysis.style_features)."""
    pooled: dict[str, list[tuple[float, float]]] = defaultdict(list)
    per: dict[str, Any] = {}
    for m in configs:
        entry: dict[str, Any] = {}
        for label, root, levels in (("v4", A.V4_ROOT, ("scimon",)), ("v31", A.V31_ROOT, A.V31_LEVELS)):
            feats, scores = [], []
            for path in sorted((root / m / "runs").glob("PMC*.json")):
                run = json.loads(path.read_text())
                if run.get("status") != "ok" or run["query_level"] not in levels:
                    continue
                if root == A.V31_ROOT and run.get("benchmark", "v3.1") not in ("v3.1", "test2", "test3"):
                    continue
                judgment = root / m / "judgments" / "gpt56" / path.name
                if not judgment.exists():
                    continue
                audit_path = root / m / "audit" / path.name
                feats.append(A.style_features(run, json.loads(audit_path.read_text()) if audit_path.exists() else None))
                scores.append(A.recon(json.loads(judgment.read_text())["scores"]))
            block: dict[str, Any] = {"runs": len(feats),
                                     "audited": sum(1 for x in feats if x["specificity"] == x["specificity"])}
            for f in ("length_chars", "hedges", "specificity"):
                pairs = [(x[f], s) for x, s in zip(feats, scores) if x[f] == x[f]]
                block[f] = round(statistics.fmean(a for a, _ in pairs), 3) if pairs else None
                if label == "v4":
                    block[f"rho_{f}"] = A.spearman([a for a, _ in pairs], [b for _, b in pairs])
                    pooled[f] += pairs
            entry[label] = block
        per[m] = entry
    rhos = {f: [e["v4"].get(f"rho_{f}") for e in per.values() if e["v4"].get(f"rho_{f}") is not None]
            for f in ("length_chars", "hedges", "specificity")}
    return {"per_configuration": per,
            "pooled_rho_v4": {f: A.spearman([a for a, _ in p], [b for _, b in p]) for f, p in pooled.items()},
            "within_rho_v4_median": {f: round(statistics.median(v), 3) if v else None for f, v in rhos.items()},
            "audited_v4_runs": sum(e["v4"]["audited"] for e in per.values())}


def harness() -> dict[str, Any]:
    cases = {p.stem: json.loads(p.read_text()) for p in sorted(A.V4_CASES.glob("PMC*.json"))}
    configs = harness_configs()
    v4 = {j: {m: A.per_paper(A.load(A.V4_ROOT, m, j, A.recon, ("scimon",))) for m in configs} for j in JUDGES}
    v31 = {j: {m: A.per_paper(A.load(A.V31_ROOT, m, j, A.recon, A.V31_LEVELS)) for m in configs} for j in JUDGES}
    v4 = {j: {m: s for m, s in d.items() if s} for j, d in v4.items()}
    out: dict[str, Any] = {"configurations": configs, "v4_runs_present": {
        m: len(list((A.V4_ROOT / m / "runs").glob("PMC*.json"))) for m in configs}}
    out["H1_v4_minus_v31"] = {j: holm_family([{"config": m, **A.paired(v4[j][m], v31[j][m])}
                                               for m in configs if m in v4[j] and v31[j].get(m)]) for j in JUDGES}
    out["H2_leaderboard"] = {m: {"papers": len(v4["gpt"].get(m, {})),
                                 **{j: round(statistics.fmean(v4[j][m].values()), 3) if v4[j].get(m) else None
                                    for j in JUDGES}} for m in configs}
    out["H2_vs_baselines"] = {j: {b: compare_all(v4[j], configs, b) for b in (LLAMA, O3_CLOSED)} for j in JUDGES}
    out["H3_rank_agreement"] = {}
    for j in JUDGES:
        pairs, relative = [], []
        for m in configs:
            if m not in v4[j] or not v31[j].get(m):
                continue
            common = sorted(set(v4[j][m]) & set(v31[j][m]))
            if not common:
                continue
            pairs.append((statistics.fmean(v4[j][m][p] for p in common), statistics.fmean(v31[j][m][p] for p in common)))
            if m != LLAMA:
                both = [p for p in common if p in v4[j].get(LLAMA, {}) and p in v31[j].get(LLAMA, {})]
                if both:
                    relative.append((statistics.fmean(v4[j][m][p] - v4[j][LLAMA][p] for p in both),
                                     statistics.fmean(v31[j][m][p] - v31[j][LLAMA][p] for p in both)))
        out["H3_rank_agreement"][j] = {
            "configurations": len(pairs), "rho_means_on_common_papers": A.spearman(*map(list, zip(*pairs))) if pairs else None,
            "rho_relative_to_llama_baseline": A.spearman(*map(list, zip(*relative))) if relative else None}
    h4: dict[str, Any] = {}
    for j in JUDGES:
        vs_writer_v4 = compare_all(v4[j], configs, WRITER)
        vs_writer_v31 = compare_all(v31[j], [m for m in configs if v31[j].get(m)], WRITER)
        v31_by = {i["config"]: i for i in vs_writer_v31}
        conflicts = [{"config": i["config"], "v4": i["diff"], "v31": v31_by[i["config"]]["diff"]}
                     for i in vs_writer_v4 if i["config"] in v31_by
                     and significant(i) * significant(v31_by[i["config"]]) == -1]
        sens = [{"config": m, "vs": b, **A.paired(v4[j].get(m, {}), v4[j].get(b, {}))} for m, b in SENSITIVITY.items()]
        sens31 = [{"config": m, "vs": b, **A.paired(v31[j].get(m, {}), v31[j].get(b, {}))}
                  for m, b in SENSITIVITY.items()]
        h4[j] = {"writer_vs_llama": A.paired(v4[j].get(WRITER, {}), v4[j].get(LLAMA, {})),
                 "vs_writer_v4": vs_writer_v4, "vs_writer_v31": vs_writer_v31,
                 "beats_writer_v4": [i["config"] for i in vs_writer_v4 if significant(i) == 1],
                 "sensitivity_v4": sens, "sensitivity_v31": sens31, "opposite_significant": conflicts}
    out["H4"] = h4
    rule = {}
    for j in JUDGES:
        v31_llama = {i["config"]: i for i in compare_all(v31[j], [m for m in configs if v31[j].get(m)], LLAMA)}
        rule[j] = [{"config": i["config"], "vs": LLAMA, "v4": i["diff"], "v31": v31_llama[i["config"]]["diff"]}
                   for i in out["H2_vs_baselines"][j][LLAMA] if i["config"] in v31_llama
                   and significant(i) * significant(v31_llama[i["config"]]) == -1]
    out["H2_opposite_significant_vs_llama"] = rule
    subs = subsets(cases)
    out["H5_subsets"] = {name: {"papers": len(ps), **{j: {
        "vs_llama": compare_all(v4[j], configs, LLAMA, ps), "vs_o3mini_closed": compare_all(v4[j], configs, O3_CLOSED, ps),
        "vs_writer": compare_all(v4[j], configs, WRITER, ps)} for j in JUDGES}} for name, ps in subs.items()}
    overlap = {p: c["queries"]["scimon"]["overlap"] for p, c in cases.items()}
    out["H6_rho_overlap_vs_score"] = {m: A.spearman([overlap[p] for p in sorted(s)], [s[p] for p in sorted(s)])
                                      for m, s in v4["gpt"].items()}
    gpt_rho = out["H3_rank_agreement"]["gpt"]["rho_means_on_common_papers"]
    out["style_must_obey_6_8"] = style_all(configs)
    out["decision"] = {"rank_rho_below_0_5": gpt_rho is not None and gpt_rho < 0.5,
                       "opposite_significant_H4": {j: h4[j]["opposite_significant"] for j in JUDGES},
                       "opposite_significant_H2_vs_llama": rule}
    return out


def suite_extra_deep(root: Path) -> dict[tuple[str, str, str], list[float]]:
    """DeepSeek scores for experiments 7, 9 and 11 written by suite_extra_eval.py."""
    scores: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for sub, label in (("eval_v3", "exp7_eval_v3"), ("eval_v4_matkg", "exp9_matkg")):
        for path in sorted((root / sub / "judgments" / "deepseek").glob("PMC*.json")):
            run = json.loads((root / sub / "runs" / path.name).read_text())
            if label == "exp9_matkg" and run["setting"] != "tool_agent_kg":
                continue
            scores[(f"{label}:{run['setting']}", run["paper_id"], run["query_level"])].append(
                A.recon(json.loads(path.read_text())["scores"]))
    folders = [(root / "eval_critique" / "baseline_resample" / "judgments" / "deepseek", "tool_agent_resample")]
    folders += [(p, p.name.removeprefix("deepseek_")) for p in sorted((root / "eval_critique" / "judgments").glob("deepseek_*"))]
    for folder, arm in folders:
        for path in sorted(folder.glob("PMC*.json")):
            paper, level = path.stem.split("__")[:2]
            scores[(f"exp11_critique:{arm}", paper, level)].append(A.recon(json.loads(path.read_text())["scores"]))
    return scores


def per_paper_arm(scores: dict[tuple[str, str, str], list[float]]) -> dict[str, dict[str, float]]:
    by: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for (arm, paper, level), values in scores.items():
        by[arm][paper][level] += values
    return {arm: {p: statistics.fmean(statistics.fmean(v) for v in lv.values()) for p, lv in papers.items()}
            for arm, papers in by.items()}


def suite() -> dict[str, Any]:
    old, new = CR.load(V3_ROOT), CR.load(V4_SUITE)
    for key, values in suite_extra_deep(V4_SUITE).items():
        new["deep"].setdefault(key, values)
    v3 = {j: per_paper_arm(old[j]) for j in JUDGES}
    v4 = {j: per_paper_arm(new[j]) for j in JUDGES}
    arms = sorted(set(v3["gpt"]) | set(v4["gpt"]))
    cases = {p.stem: json.loads(p.read_text()) for p in sorted((A.V4_CASES.parent / "cases_original12").glob("PMC*.json"))}
    out: dict[str, Any] = {"arms": arms, "papers": len(cases)}
    out["S1_v4_minus_v3"] = {j: holm_family([{"config": a, **A.paired(v4[j][a], v3[j][a])} for a in arms
                                             if v4[j].get(a) and v3[j].get(a)]) for j in JUDGES}
    out["leaderboard"] = {a: {f"{fmt}_{j}": (round(statistics.fmean(d[j][a].values()), 3) if d[j].get(a) else None)
                              for fmt, d in (("v4", v4), ("v3", v3)) for j in JUDGES} for a in arms}
    out["S2"] = {}
    for j in JUDGES:
        block = {}
        for base in (SUITE_TEXT, SUITE_CLOSED):
            on_v4 = compare_all(v4[j], arms, base)
            on_v3 = compare_all(v3[j], arms, base)
            v3_by = {i["config"]: i for i in on_v3}
            block[base] = {"v4": on_v4, "v3": on_v3, "opposite_significant": [
                {"config": i["config"], "v4": i["diff"], "v3": v3_by[i["config"]]["diff"]} for i in on_v4
                if i["config"] in v3_by and significant(i) * significant(v3_by[i["config"]]) == -1]}
        out["S2"][j] = block
    out["S3_beats_closed_book_v4"] = {j: [i["config"] for i in out["S2"][j][SUITE_CLOSED]["v4"] if significant(i) == 1]
                                      for j in JUDGES}
    unflagged = {p for p, c in cases.items() if not c["flags"]}
    out["unflagged_papers"] = sorted(unflagged)
    out["S2_unflagged_vs_closed_book"] = {j: compare_all(v4[j], arms, SUITE_CLOSED, unflagged) for j in JUDGES}
    extraction: dict[str, int] = defaultdict(int)
    for graph in sorted((V4_SUITE / "citegraph" / "cases").glob("PMC*/graph.json")):
        for node in json.loads(graph.read_text())["nodes"].values():
            if node.get("pmcid"):
                card = E / "citegraph" / "papers" / node["pmcid"] / "card.json"
                extractor = json.loads(card.read_text()).get("extractor", "?") if card.exists() else "none"
                extraction[str(extractor)] += 1
    out["citegraph_full_text_nodes_by_extractor"] = dict(extraction)
    return out


def _f(x: Any) -> str:
    return "-" if x is None else (f"{x:+.2f}" if isinstance(x, float) else str(x))


def _ci(i: dict[str, Any]) -> str:
    return f"[{i['ci95'][0]:+.2f}, {i['ci95'][1]:+.2f}]" if i.get("ci95") else "-"


def render_harness(h: dict[str, Any]) -> str:
    g1 = {i["config"]: i for i in h["H1_v4_minus_v31"]["gpt"]}
    d1 = {i["config"]: i for i in h["H1_v4_minus_v31"]["deep"]}
    gl = {i["config"]: i for i in h["H2_vs_baselines"]["gpt"][LLAMA]}
    dl = {i["config"]: i for i in h["H2_vs_baselines"]["deep"][LLAMA]}
    gw = {i["config"]: i for i in h["H4"]["gpt"]["vs_writer_v4"]}
    lines = ["# Experiment 32: harness configurations on the SciMON-style input (v4)", "",
             "| configuration | v4 runs | v4 GPT-5.6 | v4 DeepSeek | v4 − v3.1 GPT [CI] (papers, Holm p) | v4 − v3.1 DeepSeek | "
             "vs Llama GPT [CI] (Holm p) | vs Llama DeepSeek | vs writer GPT [CI] (Holm p) |",
             "|---|---:|---:|---:|---|---|---|---|---|"]
    order = sorted(h["H2_leaderboard"], key=lambda m: -(h["H2_leaderboard"][m]["gpt"] or -9))
    for m in order:
        s = h["H2_leaderboard"][m]

        def cell(d: dict[str, Any], key: str, papers: bool = False) -> str:
            i = d.get(key)
            if not i or not i.get("papers"):
                return "-"
            extra = f"{i['papers']}, " if papers else ""
            return f"{i['diff']:+.2f} {_ci(i)} ({extra}{i['holm_p']})"
        lines.append(f"| {m} | {h['v4_runs_present'][m]} | {s['gpt'] if s['gpt'] is not None else '-'} | "
                     f"{s['deep'] if s['deep'] is not None else '-'} | {cell(g1, m, True)} | {cell(d1, m)} | "
                     f"{cell(gl, m)} | {cell(dl, m)} | {cell(gw, m)} |")
    lines += ["", "H3 rank agreement: " + json.dumps(h["H3_rank_agreement"]), "",
              "Decision: " + json.dumps(h["decision"]), ""]
    return "\n".join(lines)


def render_suite(s: dict[str, Any]) -> str:
    g1 = {i["config"]: i for i in s["S1_v4_minus_v3"]["gpt"]}
    gt = {i["config"]: i for i in s["S2"]["gpt"][SUITE_TEXT]["v4"]}
    gc = {i["config"]: i for i in s["S2"]["gpt"][SUITE_CLOSED]["v4"]}
    dc = {i["config"]: i for i in s["S2"]["deep"][SUITE_CLOSED]["v4"]}
    lines = ["# Experiment 32: the experiment-21 suite on the SciMON-style input (v4), 12 papers", "",
             "| arm | v4 GPT | v4 DeepSeek | v3 GPT | v3 DeepSeek | v4 − v3 GPT [CI] (Holm p) | v4 vs text chunks GPT | "
             "v4 vs closed-book GPT | v4 vs closed-book DeepSeek |", "|---|---:|---:|---:|---:|---|---|---|---|"]

    def cell(d: dict[str, Any], key: str) -> str:
        i = d.get(key)
        return f"{i['diff']:+.2f} {_ci(i)} ({i['holm_p']})" if i and i.get("papers") else "-"
    for a in sorted(s["leaderboard"], key=lambda a: -(s["leaderboard"][a]["v4_gpt"] or -9)):
        b = s["leaderboard"][a]
        lines.append(f"| {a} | {b['v4_gpt']} | {b['v4_deep']} | {b['v3_gpt']} | {b['v3_deep']} | {cell(g1, a)} | "
                     f"{cell(gt, a)} | {cell(gc, a)} | {cell(dc, a)} |")
    lines += ["", "S3 beats closed-book on v4: " + json.dumps(s["S3_beats_closed_book_v4"]),
              "Citation-graph full-text nodes by extractor: " + json.dumps(s["citegraph_full_text_nodes_by_extractor"]), ""]
    return "\n".join(lines)


def main() -> None:
    h = harness()
    atomic_json(A.V4_ROOT / "analysis_all.json", h)
    (A.V4_ROOT / "analysis_all.md").write_text(render_harness(h))
    s = suite()
    atomic_json(V4_SUITE / "comparison" / "analysis.json", s)
    (V4_SUITE / "comparison" / "tables.md").write_text(render_suite(s))
    print(render_harness(h))
    print(render_suite(s))


if __name__ == "__main__":
    main()
