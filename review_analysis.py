"""Experiments 34 and 35 (loop.md 16.1): analysis of the round-4 methods on dev36 and of the test4 finals.

Phase B (experiment 34):
- Each new configuration against the fresh replicate B0, on the configuration's eligible papers.
- Judges: GPT-5.6, DeepSeek, their mean, and the checklist score from both judges.
- The pre-registered finalist rule, with Holm across the 8 new configurations (GPT-5.6).
- Context: each configuration also against the original incumbent runs and the Llama baseline.
- Few-shot extractor-leakage check, and the router's agreement with the v3.1 gap labels.

Phase C (experiment 35):
- Each finalist against the incumbent on test4 (Holm), and the incumbent against the Llama baseline (replication).
- All results with and without papers flagged by the answer-key audit.

Outputs: review_eval/phase_b.json and review_eval/test4.json.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import review_measurement as M
import v4_scimon_analysis as A
from hypothesis_evidence_v2 import atomic_json
from temporal_hypothesis_benchmark import _read_json

LOOP = M.E / "loop"
B0 = "writer_only_b_o3mini_r4"
INCUMBENT, BASELINE = "writer_only_b_o3mini", "closed_book"
NEW = ("writer_only_b_4o", "writer_only_b_o4mini", "writer_only_b_41",
       "fewshot_similar_b_o3mini", "fewshot_diverse_b_o3mini", "router_b_o3mini")
# o3 and gpt-5 failed the memorisation probe (loop.md 16.3) and are not analysed. The pre-registered same-family check
# for gpt-5 is covered by the rule below, which requires a positive DeepSeek difference of every configuration.
SPENT = ("v3.1", "test2", "test3")
JUDGE_KEYS = ("gpt", "deep", "mean", "checklist_gpt", "checklist_deep")


def checklist_target(method: str, benchmarks: tuple[str, ...]) -> str:
    import checklist_judge as C
    if benchmarks == ("test4",):
        return "test4"
    return "runs" if method in C.KEY_CONFIGS else "phaseb"


def run_scores(method: str, benchmarks: tuple[str, ...]) -> dict[str, dict[str, float]]:
    """{run_id: {judge key: score}} for successful runs of the given benchmarks (v3.1 levels)."""
    base = LOOP / method
    target = checklist_target(method, benchmarks)
    out: dict[str, dict[str, float]] = {}
    for path in sorted((base / "runs").glob("PMC*.json")):
        run = _read_json(path)
        if run.get("status") != "ok" or run["query_level"] not in M.LEVELS or \
                run.get("benchmark", "v3.1") not in benchmarks:
            continue
        row: dict[str, float] = {}
        for key, folder in (("gpt", "gpt56"), ("deep", "deepseek")):
            p = base / "judgments" / folder / path.name
            if p.exists():
                row[key] = M.recon(_read_json(p)["scores"])
        if "gpt" in row and "deep" in row:
            row["mean"] = (row["gpt"] + row["deep"]) / 2
        for key, judge in (("checklist_gpt", "gpt56"), ("checklist_deep", "deepseek")):
            p = M.OUT / "checklist" / "scores" / target / judge / path.name
            if p.exists() and _read_json(p).get("checklist") is not None:
                row[key] = _read_json(p)["checklist"]
        out[run["run_id"]] = row
    return out


def per_paper(scores: dict[str, dict[str, float]], key: str) -> dict[str, float]:
    """Mean over samples within a level, then over levels, per paper."""
    units: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for rid, row in scores.items():
        if key in row:
            paper, level = rid.split("__")[:2]
            units[paper][level].append(row[key])
    return {p: statistics.fmean(statistics.fmean(v) for v in lv.values()) for p, lv in units.items()}


def compare(a: str, b: str, benchmarks: tuple[str, ...], papers: set[str] | None = None) -> dict[str, Any]:
    sa, sb = run_scores(a, benchmarks), run_scores(b, benchmarks)
    return {key: A.paired(per_paper(sa, key), per_paper(sb, key), papers) for key in JUDGE_KEYS}


def adopted() -> bool:
    path = M.OUT / "checklist" / "analysis.json"
    return bool(_read_json(path).get("adoption", {}).get("adopted")) if path.exists() else False


def finalist_rule(item: dict[str, Any], method: str, use_checklist: bool) -> dict[str, bool]:
    gpt, deep, chk = item["gpt"], item["deep"], item["checklist_gpt"]
    rule = {"gpt_ci_excludes_zero_positive": bool(gpt.get("papers")) and gpt["ci95"][0] > 0,
            "deepseek_positive": bool(deep.get("papers")) and deep["diff"] > 0}
    if use_checklist:
        rule["checklist_positive"] = bool(chk.get("papers")) and chk["diff"] > 0
    return rule


# ---------------------------------------------------------------- few-shot extractor-leakage check and router

STOP = set("the and for with that this from into than are was were been has have its their which while also these "
           "those such between under over more less higher lower increased decreased improved alloy alloys high "
           "entropy temperature".split())


def stems(text: str) -> set[str]:
    return {w[:7] for w in re.findall(r"[a-z]{4,}", str(text).lower()) if w not in STOP}


def answer_words(case: dict[str, Any], common: set[str]) -> set[str]:
    t = case["hidden_target"]
    words = stems(" ".join(str(t.get(k, "")) for k in ("intervention", "structural_mediator", "mechanism",
                                                         "predicted_outcome")))
    question = stems(" ".join(q["text"] for q in case["queries"].values()))
    return words - question - common


def exemplar_leakage() -> dict[str, Any]:
    """must_obey.md 4.5: do worked examples carry words of the case's own answer that are absent from the example
    paper's own text (words a post-cutoff extractor could have injected)? Compared with other cases' answer words."""
    from answer_render import render
    cases = M.held_out_cases()
    df = Counter(w for c in cases.values() for w in stems(json.dumps(c["hidden_target"])))
    common = {w for w, n in df.items() if n > 0.2 * len(cases)}
    words = {pid: answer_words(c, common) for pid, c in cases.items()}
    source = {pid: stems(M.paper_text(pid, limit=60000)) for pid in cases}
    own_hits = own_total = ctrl_hits = ctrl_total = 0
    pairs = 0
    for method in ("fewshot_similar_b_o3mini", "fewshot_diverse_b_o3mini"):
        for path in sorted((LOOP / method / "runs").glob("PMC*.json")):
            run = _read_json(path)
            pid = run["paper_id"]
            for ex in (run.get("notes") or {}).get("exemplars", []):
                injected = stems(json.dumps(render(cases[ex]["hidden_target"]))) - source[ex]
                pairs += 1
                own_hits += len(words[pid] & injected)
                own_total += len(words[pid])
                for other, w in words.items():
                    if other not in (pid, ex):
                        ctrl_hits += len(w & injected)
                        ctrl_total += len(w)
    own = own_hits / own_total if own_total else 0.0
    ctrl = ctrl_hits / ctrl_total if ctrl_total else 0.0
    return {"example_uses": pairs, "own_answer_words_injected_rate": round(own, 5),
            "other_cases_words_injected_rate": round(ctrl, 5), "ratio": round(own / ctrl, 3) if ctrl else None}


def router_agreement() -> dict[str, Any]:
    cases = M.held_out_cases()
    pairs = []
    for path in sorted((LOOP / "router_b_o3mini" / "runs").glob("PMC*.json")):
        run = _read_json(path)
        route = (run.get("notes") or {}).get("route")
        if route:
            pairs.append((M.gap_type(cases[run["paper_id"]]), route))
    return {"runs": len(pairs), "agreement": round(sum(a == b for a, b in pairs) / len(pairs), 3) if pairs else None,
            "confusion": {f"{a}->{b}": n for (a, b), n in sorted(Counter(pairs).items())}}


def exemplar_counts() -> dict[str, Any]:
    out = {}
    for method in ("fewshot_similar_b_o3mini", "fewshot_diverse_b_o3mini"):
        counts = Counter(len((_read_json(p).get("notes") or {}).get("exemplars", []))
                         for p in (LOOP / method / "runs").glob("PMC*.json"))
        out[method] = {str(k): v for k, v in sorted(counts.items())}
    return out


# ---------------------------------------------------------------- phase B and phase C

def phase_b() -> dict[str, Any]:
    use_checklist = adopted()
    items = []
    for method in NEW:
        if not (LOOP / method / "runs").exists():
            continue
        cmp = compare(method, B0, SPENT)
        items.append({"config": method, **cmp,
                      "vs_incumbent_runs": compare(method, INCUMBENT, SPENT)["gpt"],
                      "vs_llama_baseline": compare(method, BASELINE, SPENT)["gpt"]})
    gpt_items = [i["gpt"] for i in items]
    for item, adj in zip(items, A.holm([g.get("p", 1.0) for g in gpt_items])):
        item["gpt_holm_p"] = adj
        item["rule"] = finalist_rule(item, item["config"], use_checklist)
        item["passes"] = all(item["rule"].values())
    passing = sorted((i for i in items if i["passes"]), key=lambda i: -i["gpt"]["diff"])
    result = {"checklist_adopted": use_checklist, "anchor": B0,
              "anchor_vs_incumbent_runs": compare(B0, INCUMBENT, SPENT)["gpt"],
              "anchor_vs_llama": compare(B0, BASELINE, SPENT)["gpt"],
              "configs": items, "finalists": [i["config"] for i in passing[:3]],
              "fewshot_exemplars": exemplar_counts(), "router": router_agreement()}
    if any((LOOP / m / "runs").exists() for m in ("fewshot_similar_b_o3mini", "fewshot_diverse_b_o3mini")):
        result["fewshot_extractor_leakage"] = exemplar_leakage()
    atomic_json(M.OUT / "phase_b.json", result)
    return result


def test4(finalists: list[str]) -> dict[str, Any]:
    flagged: list[str] = []
    if (M.OUT / "key_audit_test4").exists():
        flagged = M.key_audit_summary("key_audit_test4")["flagged"]
    papers = {_read_json(p)["paper_id"] for p in (M.E / "benchmark_test4" / "cases").glob("PMC*.json")}
    keep = papers - set(flagged)
    primary = [{"config": f, **compare(f, INCUMBENT, ("test4",))} for f in finalists]
    for item, adj in zip(primary, A.holm([i["gpt"].get("p", 1.0) for i in primary])):
        item["gpt_holm_p"] = adj
    result = {"papers": len(papers), "flagged": flagged, "finalists": finalists,
              "primary_vs_incumbent": primary,
              "primary_vs_incumbent_unflagged": [{"config": f, **compare(f, INCUMBENT, ("test4",), keep)}
                                                 for f in finalists],
              "replication_incumbent_vs_baseline": compare(INCUMBENT, BASELINE, ("test4",)),
              "replication_unflagged": compare(INCUMBENT, BASELINE, ("test4",), keep),
              "pooled_fresh37_incumbent_vs_baseline": pooled_fresh(),
              "means": {m: {k: round(statistics.fmean(v.values()), 3) if v else None
                            for k, v in ((k, per_paper(run_scores(m, ("test4",)), k)) for k in JUDGE_KEYS)}
                        for m in (INCUMBENT, BASELINE, *finalists)}}
    atomic_json(M.OUT / "test4.json", result)
    return result


def pooled_fresh() -> dict[str, Any]:
    """Loop.md 16.1, addendum 2 (exploratory, as in rounds 2-3): incumbent vs Llama baseline over every fresh held-out
    paper, i.e. the 28 papers of test, test2 and test3 plus the 9 of test4, each scored on its first use."""
    fresh = M.split_papers()["fresh28"] | {_read_json(p)["paper_id"]
                                           for p in (M.E / "benchmark_test4" / "cases").glob("PMC*.json")}
    benchmarks = (*SPENT, "test4")
    out = compare(INCUMBENT, BASELINE, benchmarks, fresh)
    return {"papers_requested": len(fresh), **{k: v for k, v in out.items() if not k.startswith("checklist")}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("phase-b", "test4"))
    parser.add_argument("--finalist", action="append", default=[])
    args = parser.parse_args()
    out = phase_b() if args.stage == "phase-b" else test4(args.finalist)
    print(json.dumps(out, indent=1)[:12000])


if __name__ == "__main__":
    main()
