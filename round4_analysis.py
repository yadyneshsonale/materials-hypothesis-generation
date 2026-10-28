"""Experiment 38 (loop.md 19.1): synthesis. Draft class labels and the pre-registered analysis.

Usage:
  python round4_analysis.py drafts   gpt-4o-mini labels the study type of every draft and final hypothesis
                                     (target-free; loop_r4/<method>/draft_classes/)
  python round4_analysis.py report   Q1, Q2, secondary metrics and leakage: loop_r4/analysis_r4.json and .md
"""

from __future__ import annotations

import os

_E = os.path.join(os.path.dirname(os.path.abspath(__file__)), "experiments", "high_temperature_hea_qwen35b")
os.environ.setdefault("MATHG_CASES_DIR", os.path.join(_E, "benchmark_v3_1", "cases"))
os.environ.setdefault("MATHG_LOOP_ROOT", os.path.join(_E, "loop_r4"))

import argparse  # noqa: E402
import json  # noqa: E402
import statistics  # noqa: E402
from collections import Counter, defaultdict  # noqa: E402
from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

import hypo_loop as H  # noqa: E402
import llm_client as lc  # noqa: E402
import round4_offline as R  # noqa: E402
import web_analysis as W  # noqa: E402
from hypothesis_evidence_v2 import atomic_json  # noqa: E402
from stage_metrics import HEDGE  # noqa: E402
from temporal_hypothesis_benchmark import _read_json  # noqa: E402

A, V = W.A, W.V
R4 = H.OUT  # loop_r4/ unless MATHG_LOOP_ROOT says otherwise
JUDGES = ("gpt", "deep")
SYNTH = ("synth_k4_b_o3mini", "synth_crowd_b_o3mini", "synth_mixed_b_o3mini", "synth_k1_b_o3mini")
REPLICATE = "writer_only_b_o3mini_r5"
INCUMBENT = "writer_only_b_o3mini"
REFERENCE = "incumbent (original + replicate)"
OUTPUT_FIELDS = tuple(f for f in H.HYPOTHESIS_FIELDS if not f.endswith("_ids"))

HYP_CLASSIFY_SYSTEM = R.CLASSIFY_SYSTEM.replace(
    "You classify the main contribution of a materials-science research paper from its title and abstract.",
    "You classify the main intervention or study that each of several materials-science hypotheses proposes.").replace(
    "Return JSON {\"class\": one of the classes, \"study\": \"the paper's main intervention or study in at most 15 "
    "words\"}.", "Return JSON {\"items\": [{\"id\": the hypothesis id, \"class\": one of the classes}]} with one "
    "entry per hypothesis.")


def root_of(method: str) -> Path:
    return E_LOOP if method == INCUMBENT else R4


E_LOOP = W.E / "loop"


def _load(method: str, judge: str) -> dict[str, dict[str, list[float]]]:
    return W.load(root_of(method), method, judge)


_SCORES: dict[tuple[str, str], dict[str, float]] = {}


def scores(method: str, judge: str) -> dict[str, float]:
    """Per-paper means. The reference pools the incumbent's original runs and its fresh replicate (4 per unit)."""
    if (method, judge) not in _SCORES:
        if method == REFERENCE:
            merged: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
            for m in (INCUMBENT, REPLICATE):
                for paper, levels in _load(m, judge).items():
                    for level, values in levels.items():
                        merged[paper][level].extend(values)
            _SCORES[(method, judge)] = A.per_paper(merged)
        else:
            _SCORES[(method, judge)] = W.per_paper(root_of(method), method, judge)
    return _SCORES[(method, judge)]


def family(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    """Paired per-paper comparisons a - b for both judges, Holm within the family, and the pre-registered rule."""
    out: dict[str, Any] = {j: V.holm_family([{"config": a, "vs": b, **A.paired(scores(a, j), scores(b, j))}
                                             for a, b in pairs]) for j in JUDGES}
    decision = {}
    for g, d in zip(out["gpt"], out["deep"]):
        key = f"{g['config']} vs {g['vs']}"
        if not g.get("papers"):
            decision[key] = "no data"
        elif g["ci95"][0] > 0 and d.get("diff", 0) > 0:
            decision[key] = "better"
        elif g["ci95"][1] < 0 and d.get("diff", 0) < 0:
            decision[key] = "worse"
        else:
            decision[key] = "no detectable difference"
    out["decision"] = decision
    return out


# ---------------------------------------------------------------- draft class labels (target-free)

def hyp_text(g: dict[str, Any]) -> str:
    return " | ".join(f"{k}: {str(g.get(k) or '')[:400]}" for k in ("intervention", "hypothesis", "mechanism"))


def classify_run(run: dict[str, Any]) -> None:
    drafts = run["notes"].get("drafts") or []
    items = [{"id": d["id"], "text": hyp_text(d)} for d in drafts] + [{"id": "final", "text": hyp_text(
        run["generation"])}]
    raw = lc.trapi_chat_json(R.CLASSIFIER, HYP_CLASSIFY_SYSTEM, json.dumps({"hypotheses": items}, ensure_ascii=False),
                             max_tokens=800, temperature=0.0, retries=8)
    got = {str(i.get("id")): i.get("class") for i in (raw.get("items") or []) if isinstance(i, dict)} \
        if isinstance(raw, dict) else {}
    atomic_json(R4 / run["method"] / "draft_classes" / f"{run['run_id']}.json", {
        "run_id": run["run_id"], "classifier": R.CLASSIFIER,
        "classes": {i["id"]: (got.get(i["id"]) if got.get(i["id"]) in R.TARGET_TYPES else "other") for i in items}})


def drafts_stage(workers: int = 16) -> dict[str, int]:
    jobs = [r for m in SYNTH for r in W.runs(R4, m) if r.get("status") == "ok"
            and not (R4 / m / "draft_classes" / f"{r['run_id']}.json").exists()]
    counts: Counter[str] = Counter()
    with ThreadPoolExecutor(workers) as pool:
        for future in as_completed([pool.submit(classify_run, r) for r in jobs]):
            try:
                future.result()
                counts["done"] += 1
            except Exception as error:  # noqa: BLE001 - logged; a rerun resumes
                counts["failed"] += 1
                print(f"[drafts] {type(error).__name__}: {str(error)[:150]}", flush=True)
    return {"jobs": len(jobs), **counts}


def draft_agreement(method: str) -> dict[str, Any]:
    rows = []
    for run in W.runs(R4, method):
        path = R4 / method / "draft_classes" / f"{run['run_id']}.json"
        if run.get("status") != "ok" or not path.exists():
            continue
        classes = _read_json(path)["classes"]
        final = classes.pop("final", None)
        drafts = list(classes.values())
        counts = Counter(drafts)
        top = max(counts.values()) if counts else 0
        rows.append({"n": len(drafts), "shared": counts.get(final, 0) >= 2, "modal": counts.get(final, 0) == top,
                     "unanimous": len(counts) == 1, "final_in_drafts": final in counts, "final": final,
                     "drafts": drafts})
    if not rows:
        return {"runs": 0}
    final_dist = Counter(r["final"] for r in rows)
    draft_dist = Counter(c for r in rows for c in r["drafts"])
    return {"runs": len(rows), "drafts_per_run": round(statistics.fmean(r["n"] for r in rows), 2),
            "final_class_shared_by_2plus_drafts": round(statistics.fmean(r["shared"] for r in rows), 3),
            "final_class_is_modal_draft_class": round(statistics.fmean(r["modal"] for r in rows), 3),
            "drafts_unanimous": round(statistics.fmean(r["unanimous"] for r in rows), 3),
            "final_class_among_drafts": round(statistics.fmean(r["final_in_drafts"] for r in rows), 3),
            "final_classes": {c: round(n / len(rows), 3) for c, n in final_dist.most_common()},
            "draft_classes": {c: round(n / sum(draft_dist.values()), 3) for c, n in draft_dist.most_common()}}


# ---------------------------------------------------------------- leaderboard, secondary metrics, leakage

def run_stats(method: str, targets: dict[tuple[str, str], str]) -> dict[str, Any]:
    root = root_of(method)
    runs = [r for r in W.runs(root, method) if r.get("benchmark", "v3.1") in R.BENCHMARKS]
    ok = [r for r in runs if r.get("status") == "ok"]
    audits, labels, judged = [], [], {j: [] for j in JUDGES}
    for r in ok:
        for kind, folder in (("audit", "audit"), ("label", "labels"), ("gpt", "judgments/gpt56"),
                             ("deep", "judgments/deepseek")):
            path = root / method / folder / f"{r['run_id']}.json"
            if not path.exists():
                continue
            item = _read_json(path)
            if kind == "audit":
                audits.append(item)
            elif kind == "label":
                labels.append((item, targets.get((r["paper_id"], r["query_level"]))))
            else:
                judged[kind].append(item)
    g, d = scores(method, "gpt"), scores(method, "deep")
    return {"runs": len(runs), "failed": len(runs) - len(ok), "papers": len(g),
            "gpt": W.A_mean(list(g.values())), "deep": W.A_mean(list(d.values())),
            "dimensions": {j: {dim: W.A_mean([x["scores"][dim] for x in judged[j]]) for dim in H.ALL_DIMENSIONS}
                           for j in JUDGES},
            "lever_ge2": W.A_mean([float(lb["lever_match"] >= 2) for lb, _ in labels]),
            "class_hit": W.A_mean([float(lb["intervention_class"] == t) for lb, t in labels if t]),
            "labelled": len(labels), "audited": len(audits),
            "complete_chain": W.A_mean([float(all(v == 2 for v in a.get("chain", {}).values())) for a in audits]),
            "specificity": W.A_mean([statistics.fmean(1.0 if v else 0.0 for v in a["specificity"].values())
                                     for a in audits if a.get("specificity")]),
            "hedges": W.A_mean([len(HEDGE.findall(f"{r['generation'].get('hypothesis', '')} "
                                                  f"{r['generation'].get('predicted_outcome', '')}")) for r in ok]),
            "unsupported_gpt": W.A_mean([float(x.get("classification") == "unsupported") for x in judged["gpt"]]),
            "output_chars": W.A_mean([float(sum(len(str(r["generation"].get(f) or "")) for f in OUTPUT_FIELDS))
                                      for r in ok]),
            "llm_calls": W.A_mean([r["llm_calls"] for r in ok]), "chars_in": W.A_mean([r["chars_in"] for r in ok]),
            "seconds": W.A_mean([r["elapsed_seconds"] for r in ok]),
            "draft_failures": sum(len(r["notes"].get("draft_failures") or []) for r in ok)}


def leakage() -> dict[str, Any]:
    cases = H.cases()
    evidence = W.Evidence()
    violations, checked, unresolved = [], 0, 0
    for method in SYNTH + (REPLICATE,):
        for run in W.runs(R4, method):
            cutoff = cases[run["paper_id"]]["publication_date"]
            for rid in run["seen_ids"]:
                record = evidence.web(rid)
                if record is None:
                    unresolved += 1
                    continue
                checked += 1
                dates = [x for x in (record.structured or {}).get("dates", {}).values() if x]
                if any(x >= cutoff for x in dates + [record.publication_date]):
                    violations.append(f"{run['run_id']}: {rid}")
    return {"counters": W.counters(R4), "web_records_rechecked": checked, "unresolved": unresolved,
            "date_violations": len(violations), "examples": violations[:10]}


def report() -> dict[str, Any]:
    q1 = [(m, REFERENCE) for m in SYNTH]
    q2 = [("synth_k4_b_o3mini", "synth_k1_b_o3mini"), ("synth_crowd_b_o3mini", "synth_k4_b_o3mini"),
          ("synth_mixed_b_o3mini", "synth_k4_b_o3mini"), ("synth_k1_b_o3mini", REFERENCE)]
    targets = R.unit_targets(R.judged_runs())
    return {"Q1_vs_incumbent": family(q1), "Q2_ablations": family(q2),
            "noise_floor_replicate_vs_original": family([(REPLICATE, INCUMBENT)]),
            "leaderboard": {m: run_stats(m, targets) for m in SYNTH + (REPLICATE, INCUMBENT)},
            "draft_agreement": {m: draft_agreement(m) for m in SYNTH}, "leakage": leakage()}


# ---------------------------------------------------------------- markdown

def _cell(i: dict[str, Any] | None) -> str:
    if not i or not i.get("papers"):
        return "-"
    return f"{i['diff']:+.2f} {V._ci(i)} ({i['papers']} papers, {i['up']}/{i['down']}, Holm p " \
           f"{i['holm_p']})"


def _family_table(title: str, fam: dict[str, Any]) -> list[str]:
    lines = [f"## {title}", "", "| comparison | GPT-5.6 difference [CI] | DeepSeek difference [CI] | decision |",
             "|---|---|---|---|"]
    for g, d in zip(fam["gpt"], fam["deep"]):
        lines.append(f"| {g['config']} vs {g['vs']} | {_cell(g)} | {_cell(d)} | "
                     f"{fam['decision'][g['config'] + ' vs ' + g['vs']]} |")
    return lines + [""]


def render(r: dict[str, Any]) -> str:
    lines = ["# Experiment 38: synthesis (round 4)", ""]
    lines += _family_table("Q1 (primary): each synthesis configuration vs the incumbent (original + fresh replicate)",
                           r["Q1_vs_incumbent"])
    lines += _family_table("Q2: ablations", r["Q2_ablations"])
    lines += _family_table("Noise floor: fresh replicate vs the original incumbent",
                           r["noise_floor_replicate_vs_original"])
    board = r["leaderboard"]
    order = sorted(board, key=lambda m: -(board[m]["gpt"] or -9))
    lines += ["## Leaderboard (mean over papers)", "",
              "| configuration | runs | failed | papers | GPT-5.6 | DeepSeek | lever ≥ 2 | class hit | complete chain | "
              "specificity | audited runs | hedges | unsupported | output chars | calls | input chars | seconds | draft failures |",
              "|---|" + "---:|" * 17]
    for m in order:
        b = board[m]
        lines.append(f"| {m} | {b['runs']} | {b['failed']} | {b['papers']} | {b['gpt']} | {b['deep']} | "
                     f"{b['lever_ge2']} | {b['class_hit']} | {b['complete_chain']} | {b['specificity']} | {b['audited']} | "
                     f"{b['hedges']} | {b['unsupported_gpt']} | {b['output_chars']} | {b['llm_calls']} | "
                     f"{b['chars_in']} | {b['seconds']} | {b['draft_failures']} |")
    for j, name in (("gpt", "GPT-5.6"), ("deep", "DeepSeek")):
        lines += ["", f"## {name} judge dimensions (0–4, mean over runs)", "",
                  "| configuration | " + " | ".join(H.ALL_DIMENSIONS) + " |", "|---|" + "---:|" * len(H.ALL_DIMENSIONS)]
        for m in order:
            dims = board[m]["dimensions"][j]
            lines.append(f"| {m} | " + " | ".join(str(dims[x]) for x in H.ALL_DIMENSIONS) + " |")
    agree = r["draft_agreement"]
    keys = list(dict.fromkeys(k for s in agree.values() for k in s))
    lines += ["", "## Draft agreement (gpt-4o-mini study-type labels of drafts and final, target-free)", "",
              "| measure | " + " | ".join(f"`{m}`" for m in agree) + " |", "|---|" + "---|" * len(agree)]
    for k in keys:
        lines.append(f"| {k} | " + " | ".join(json.dumps(s.get(k)) for s in agree.values()) + " |")
    lk = r["leakage"]
    lines += ["", "## Leakage", "", f"Counters over {lk['counters']['runs_checked']} runs: "
              f"{json.dumps(lk['counters']['totals'])}; web records re-checked: {lk['web_records_rechecked']}, "
              f"date violations: {lk['date_violations']}, unresolved: {lk['unresolved']}.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("drafts", "report"))
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    if args.stage == "drafts":
        print(drafts_stage(args.workers))
        return
    r = report()
    atomic_json(R4 / "analysis_r4.json", r)
    (R4 / "analysis_r4.md").write_text(render(r))
    print(render(r))


if __name__ == "__main__":
    main()
