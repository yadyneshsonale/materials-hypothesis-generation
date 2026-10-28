"""Experiment 37 (loop.md 18.1-18.2): propose, critique, decide. The pre-registered analysis and the Q6 idea labels.

Usage:
  python pcd_analysis.py labels --method pcd_PCD_o3mini --method pcd_none_o3mini [--workers 8]
      One GPT-5.6 lever-label call per run labels every proposed idea and the final hypothesis (target-aware analysis
      only; stored in loop_pcd/<method>/idea_labels/, never shown to any method).
  python pcd_analysis.py report
      Q1-Q6, leaderboard, secondary metrics, cost and leakage: loop_pcd/analysis_pcd.json and analysis_pcd.md.
"""

from __future__ import annotations

import os

os.environ.setdefault("MATHG_CASES_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "experiments",
                                                      "high_temperature_hea_qwen35b", "benchmark_v3_1", "cases"))
os.environ.setdefault("MATHG_LOOP_ROOT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "experiments",
                                                      "high_temperature_hea_qwen35b", "loop_pcd"))

import argparse  # noqa: E402
import json  # noqa: E402
import random  # noqa: E402
import statistics  # noqa: E402
from collections import Counter  # noqa: E402
from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

import hypo_loop as H  # noqa: E402
import llm_client as lc  # noqa: E402
import web_analysis as W  # noqa: E402
from failure_clean import LABEL_SYSTEM  # noqa: E402
from hypothesis_evidence_v2 import atomic_json  # noqa: E402
from stage_metrics import HEDGE  # noqa: E402
from temporal_hypothesis_benchmark import _read_json  # noqa: E402

A, V = W.A, W.V
E = W.E
PCD = H.OUT  # loop_pcd/ unless MATHG_LOOP_ROOT says otherwise
JUDGES = ("gpt", "deep")
GRID = ("none", "P", "C", "D", "PC", "PD", "CD", "PCD")
FULL, NONE = "pcd_PCD_o3mini", "pcd_none_o3mini"
Q6 = (NONE, FULL)
BASELINES = {"writer_only_b_o3mini": W.FIXED, "closed_book_o3mini": W.FIXED, "closed_book": W.FIXED,
             "web_text_chunks_b_o3mini": W.WEB, "web_agent_o3mini": W.WEB, "web_text_64k_b_o3mini": W.WEB,
             "web_text_chunks": W.WEB, "web_agent": W.WEB}
LABEL_TARGET = ("material_initial_state", "intervention", "structural_mediator", "mechanism", "predicted_outcome")
OUTPUT_FIELDS = tuple(f for f in H.HYPOTHESIS_FIELDS if not f.endswith("_ids"))  # the final hypothesis's text fields
DIM_SHORT = {"problem_alignment": "problem", "intervention_reconstruction": "interv.", "condition_agreement": "cond.",
             "mechanism_agreement": "mech.", "outcome_agreement": "outcome", "baseline_quality": "baseline",
             "boundary_quality": "boundary", "experiment_discriminability": "experiment",
             "evidence_validity": "evidence", "novelty": "novelty"}


def root_of(method: str) -> Path:
    return PCD if method.startswith("pcd_") else BASELINES[method]


def configs() -> list[str]:
    return sorted(p.name for p in PCD.iterdir() if (p / "runs").is_dir())


_SCORES: dict[tuple[str, str], dict[str, float]] = {}


def scores(method: str, judge: str) -> dict[str, float]:
    if (method, judge) not in _SCORES:
        _SCORES[(method, judge)] = W.per_paper(root_of(method), method, judge)
    return _SCORES[(method, judge)]


# ---------------------------------------------------------------- comparisons

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


def web_main_effects() -> dict[str, Any]:
    """Q3: per paper, the mean of the 4 grid cells with web at a role minus the mean of the 4 without."""
    out: dict[str, Any] = {}
    for j in JUDGES:
        cells = {f: scores(f"pcd_{f}_o3mini", j) for f in GRID}
        papers = set.intersection(*(set(c) for c in cells.values()))
        items = []
        for role in "PCD":
            with_role = {p: statistics.fmean(cells[f][p] for f in GRID if role in f) for p in papers}
            without = {p: statistics.fmean(cells[f][p] for f in GRID if role not in f) for p in papers}
            items.append({"config": f"web at {role}", **A.paired(with_role, without)})
        out[j] = V.holm_family(items)
        out[f"cell_means_{j}"] = {f: W.A_mean([cells[f][p] for p in papers]) for f in GRID}
    return out


# ---------------------------------------------------------------- Q6: coverage and selection

def idea_text(idea: dict[str, Any]) -> str:
    return " | ".join(f"{k}: {str(idea.get(k, ''))[:400]}" for k in ("intervention", "mechanism", "material_system"))


def final_text(generation: dict[str, Any]) -> str:
    return " | ".join(f"{k}: {str(generation.get(k, ''))[:400]}" for k in ("hypothesis", "intervention", "mechanism"))


def _lever(item: dict[str, Any] | None) -> int | None:
    if not item:
        return None
    try:
        return max(0, min(3, int(item.get("lever_match"))))
    except (TypeError, ValueError):
        return None


def label_run(run: dict[str, Any], case: dict[str, Any]) -> None:
    ideas = run["notes"].get("proposals", [])
    hypotheses = [{"id": n + 1, "text": idea_text(i)} for n, i in enumerate(ideas)]
    hypotheses.append({"id": len(ideas) + 1, "text": final_text(run["generation"])})
    payload = {"research_question": run["query"],
               "hidden_target": {k: case["hidden_target"].get(k) for k in LABEL_TARGET}, "hypotheses": hypotheses}
    raw = lc.judge_chat_json(LABEL_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=6000)
    items: dict[int, dict[str, Any]] = {}
    for item in raw.get("hypotheses", []) if isinstance(raw, dict) else []:
        try:
            items[int(item.get("id"))] = item
        except (TypeError, ValueError, AttributeError):
            continue

    def lab(n: int) -> dict[str, Any]:
        item = items.get(n)
        return {"lever_match": _lever(item), "intervention_class": str((item or {}).get("intervention_class", ""))}

    atomic_json(PCD / run["method"] / "idea_labels" / f"{run['run_id']}.json", {
        "run_id": run["run_id"], "labeller": lc.judge_info(), "trapi_instance": H.trapi_instance(),
        "ideas": [{"id": i["id"], **lab(n + 1)} for n, i in enumerate(ideas)], "final": lab(len(ideas) + 1),
        "target_type": raw.get("target_type") if isinstance(raw, dict) else None})


def label_stage(methods: list[str], workers: int) -> dict[str, int]:
    cases = H.cases()

    def written(run: dict[str, Any]) -> bool:
        return (PCD / run["method"] / "idea_labels" / f"{run['run_id']}.json").exists()

    jobs = [r for r in H.all_runs(methods) if r["status"] == "ok" and not written(r)]
    if os.environ.get("MATHG_PENDING_SHUFFLE"):  # an extra loop takes jobs in another order, as in hypo_loop._pending
        random.Random(int(os.environ["MATHG_PENDING_SHUFFLE"])).shuffle(jobs)

    def job(run: dict[str, Any]) -> bool:
        if written(run):  # by another process after the job list was made
            return False
        label_run(run, cases[run["paper_id"]])
        return True

    counts: Counter[str] = Counter()
    with ThreadPoolExecutor(workers) as pool:
        futures = [pool.submit(job, r) for r in jobs]
        for future in as_completed(futures):
            try:
                counts["done" if future.result() else "skipped"] += 1
            except Exception as error:  # noqa: BLE001 - logged; the next call resumes
                counts["failed"] += 1
                print(f"[pcd-labels] {type(error).__name__}: {str(error)[:200]}", flush=True)
    return {"jobs": len(jobs), **counts}


def selection(method: str) -> dict[str, Any]:
    rows = []
    for run in W.runs(PCD, method):
        path = PCD / method / "idea_labels" / f"{run['run_id']}.json"
        if run.get("status") != "ok" or not path.exists():
            continue
        lab = _read_json(path)
        ideas = {i["id"]: i for i in lab["ideas"] if i["lever_match"] is not None}
        if not ideas or lab["final"]["lever_match"] is None:
            continue
        decision = run["notes"].get("decision") or {}
        chosen = [c for c in decision.get("chosen_ids", []) if c in ideas]
        presentation = run["notes"].get("presentation", {})
        verdicts = {presentation.get(c["id"], c["id"]): c.get("verdict") for c in run["notes"].get("critiques") or []}
        rows.append({"any": max(i["lever_match"] for i in ideas.values()) >= 2, "final": lab["final"]["lever_match"] >= 2,
                     "chosen_match": any(ideas[c]["lever_match"] >= 2 for c in chosen), "first": chosen[:1] == ["I1"],
                     "mode": decision.get("mode", ""),
                     "classes": len({i["intervention_class"] for i in ideas.values() if i["intervention_class"]}),
                     "verdicts": [(ideas[i]["lever_match"] >= 2, verdicts.get(i)) for i in ideas if verdicts.get(i)]})
    if not rows:
        return {"runs": 0}
    recall = [r for r in rows if r["any"]]
    match_verdicts = Counter(v for r in rows for m, v in r["verdicts"] if m)
    other_verdicts = Counter(v for r in rows for m, v in r["verdicts"] if not m)
    return {"runs": len(rows),
            "proposal_recall_any_idea_lever_ge2": round(len(recall) / len(rows), 3),
            "final_lever_ge2": round(sum(r["final"] for r in rows) / len(rows), 3),
            "selection_given_recall_final_ge2": round(sum(r["final"] for r in recall) / len(recall), 3) if recall else None,
            "selection_given_recall_chosen_idea_ge2": round(sum(r["chosen_match"] for r in recall) / len(recall), 3)
            if recall else None,
            "decider_chose_proposers_first_idea": round(sum(r["first"] for r in rows) / len(rows), 3),
            "decision_modes": dict(Counter(r["mode"] for r in rows)),
            "distinct_intervention_classes_per_run": W.A_mean([r["classes"] for r in rows]),
            "critic_verdicts_on_matching_ideas": dict(match_verdicts),
            "critic_verdicts_on_other_ideas": dict(other_verdicts)}


# ---------------------------------------------------------------- leaderboard, secondary metrics, leakage

def run_stats(method: str) -> dict[str, Any]:
    root = root_of(method)
    runs = [r for r in W.runs(root, method) if r.get("benchmark", "v3.1") in ("v3.1", "test2", "test3", "test4")]
    ok = [r for r in runs if r.get("status") == "ok"]
    audits, labels = [], []
    judged: dict[str, list[dict[str, Any]]] = {j: [] for j in JUDGES}
    for r in ok:
        path = root / method / "audit" / f"{r['run_id']}.json"
        if path.exists():
            audits.append(_read_json(path))
        path = root / method / "labels" / f"{r['run_id']}.json"
        if path.exists():
            labels.append(_read_json(path))
        for judge, folder in (("gpt", "gpt56"), ("deep", "deepseek")):
            path = root / method / "judgments" / folder / f"{r['run_id']}.json"
            if path.exists():
                judged[judge].append(_read_json(path))
    g = scores(method, "gpt")
    d = scores(method, "deep")
    return {"runs": len(runs), "failed": len(runs) - len(ok), "papers": len(g),
            "gpt": W.A_mean(list(g.values())), "deep": W.A_mean(list(d.values())),
            "complete_chain": W.A_mean([float(all(v == 2 for v in a.get("chain", {}).values())) for a in audits]),
            "specificity": W.A_mean([statistics.fmean(1.0 if v else 0.0 for v in a["specificity"].values())
                                     for a in audits if a.get("specificity")]),
            "audited": len(audits),
            "hedges": W.A_mean([len(HEDGE.findall(f"{r['generation'].get('hypothesis', '')} "
                                                  f"{r['generation'].get('predicted_outcome', '')}")) for r in ok]),
            "llm_calls": W.A_mean([r["llm_calls"] for r in ok]), "chars_in": W.A_mean([r["chars_in"] for r in ok]),
            "seconds": W.A_mean([r["elapsed_seconds"] for r in ok]),
            # Secondary (18.1): run-level means of every judge dimension, as in hypo_loop.summarise.
            "dimensions": {judge: {dim: W.A_mean([j["scores"][dim] for j in judged[judge]])
                                   for dim in H.ALL_DIMENSIONS} for judge in JUDGES},
            "classification_gpt": dict(sorted(Counter(j.get("classification", "") for j in judged["gpt"]).items())),
            "unsupported_gpt": W.A_mean([float(j.get("classification") == "unsupported") for j in judged["gpt"]]),
            "output_chars": W.A_mean([float(sum(len(str(r["generation"].get(f) or "")) for f in OUTPUT_FIELDS))
                                      for r in ok]),
            "lever_ge2": W.A_mean([float(lb["lever_match"] >= 2) for lb in labels]), "labelled": len(labels)}


def leakage() -> dict[str, Any]:
    cases = H.cases()
    evidence = W.Evidence()
    violations, checked, unresolved = [], 0, 0
    for method in configs():
        for run in W.runs(PCD, method):
            cutoff = cases[run["paper_id"]]["publication_date"]
            for rid in run["seen_ids"]:
                record = evidence.web(rid)
                if record is None:
                    unresolved += 1
                    continue
                checked += 1
                dates = [d for d in (record.structured or {}).get("dates", {}).values() if d]
                if any(d >= cutoff for d in dates + [record.publication_date]):
                    violations.append(f"{run['run_id']}: {rid}")
    return {"counters": W.counters(PCD), "web_records_rechecked": checked, "unresolved": unresolved,
            "date_violations": len(violations), "examples": violations[:10]}


def report() -> dict[str, Any]:
    q1 = [(FULL, b) for b in ("writer_only_b_o3mini", "closed_book_o3mini", "closed_book", "web_text_chunks_b_o3mini",
                              "web_agent_o3mini", "web_text_64k_b_o3mini")]
    q2 = [(NONE, "writer_only_b_o3mini"), (NONE, "closed_book_o3mini")]
    q3_cells = [(f"pcd_{f}_o3mini", NONE) for f in GRID if f != "none"]
    q4 = [(f"pcd_{w}_o3mini", f"pcd_{a}_{w}_o3mini") for w in ("none", "PCD") for a in ("nocritic", "nodecider", "k1")]
    q5 = [("pcd_none_llama", "closed_book"), ("pcd_PCD_llama", "closed_book"), ("pcd_PCD_llama", "web_text_chunks"),
          ("pcd_PCD_llama", "web_agent")]
    methods = configs() + list(BASELINES)
    return {"Q1_full_vs_baselines": family(q1), "Q2_no_web_vs_baselines": family(q2),
            "Q3_web_main_effects": web_main_effects(), "Q3_cells_vs_none": family(q3_cells),
            "Q4_structure": family(q4), "Q5_llama": family(q5),
            "Q6_selection": {m: selection(m) for m in Q6},
            "leaderboard": {m: run_stats(m) for m in methods}, "leakage": leakage()}


# ---------------------------------------------------------------- markdown

def _cell(i: dict[str, Any] | None) -> str:
    if not i or not i.get("papers"):
        return "-"
    return f"{i['diff']:+.2f} {V._ci(i)} ({i['papers']} papers, Holm p {i['holm_p']})"


def _family_table(title: str, fam: dict[str, Any]) -> list[str]:
    lines = [f"## {title}", "", "| comparison | GPT-5.6 difference [CI] | DeepSeek difference [CI] | decision |",
             "|---|---|---|---|"]
    for g, d in zip(fam["gpt"], fam["deep"]):
        lines.append(f"| {g['config']} vs {g['vs']} | {_cell(g)} | {_cell(d)} | "
                     f"{fam['decision'][g['config'] + ' vs ' + g['vs']]} |")
    return lines + [""]


def render(r: dict[str, Any]) -> str:
    lines = ["# Experiment 37: propose, critique, decide", ""]
    lines += _family_table("Q1 (primary): full system (web at every role) vs the baselines", r["Q1_full_vs_baselines"])
    lines += _family_table("Q2: the framework without web", r["Q2_no_web_vs_baselines"])
    q3 = r["Q3_web_main_effects"]
    lines += ["## Q3: web evidence at each role (main effects over the 8-cell grid)", "",
              "| role | GPT-5.6 with − without [CI] | DeepSeek [CI] |", "|---|---|---|"]
    for g, d in zip(q3["gpt"], q3["deep"]):
        lines.append(f"| {g['config']} | {_cell(g)} | {_cell(d)} |")
    lines += ["", "Cell means (GPT-5.6): " + json.dumps(q3["cell_means_gpt"]),
              "Cell means (DeepSeek): " + json.dumps(q3["cell_means_deep"]), ""]
    lines += _family_table("Q3: each grid cell vs no web", r["Q3_cells_vs_none"])
    lines += _family_table("Q4: each agent's contribution (full minus ablation)", r["Q4_structure"])
    lines += _family_table("Q5: Llama-3.3 in every role", r["Q5_llama"])
    q6 = r["Q6_selection"]
    lines += ["## Q6: coverage and selection (idea labels: every proposed idea and the final hypothesis)", "",
              "| measure | " + " | ".join(f"`{m}`" for m in q6) + " |", "|---|" + "---|" * len(q6)]
    for key in dict.fromkeys(k for s in q6.values() for k in s):
        lines.append(f"| {key} | " + " | ".join(json.dumps(s.get(key)) for s in q6.values()) + " |")
    lines += ["", "## Leaderboard (mean over papers)", "",
              "| configuration | runs | failed | papers | GPT-5.6 | DeepSeek | complete chain | specificity | hedges | "
              "calls | input chars | seconds |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    board = r["leaderboard"]
    for m in sorted(board, key=lambda m: -(board[m]["gpt"] or -9)):
        b = board[m]
        lines.append(f"| {m} | {b['runs']} | {b['failed']} | {b['papers']} | {b['gpt']} | {b['deep']} | "
                     f"{b['complete_chain']} | {b['specificity']} | {b['hedges']} | {b['llm_calls']} | "
                     f"{b['chars_in']} | {b['seconds']} |")
    order = sorted(board, key=lambda m: -(board[m]["gpt"] or -9))
    for judge, name in (("gpt", "GPT-5.6"), ("deep", "DeepSeek")):
        lines += ["", f"## Secondary: {name} judge dimensions (0–4, mean over runs)", "",
                  "| configuration | " + " | ".join(DIM_SHORT[x] for x in H.ALL_DIMENSIONS) + " |",
                  "|---|" + "---:|" * len(H.ALL_DIMENSIONS)]
        for m in order:
            dims = board[m]["dimensions"][judge]
            lines.append(f"| {m} | " + " | ".join(str(dims[x]) for x in H.ALL_DIMENSIONS) + " |")
    lines += ["", "## Secondary: classification, length, lever labels", "",
              "Unsupported: share of runs the GPT-5.6 judge classes as unsupported. Output: characters in the final "
              "hypothesis's text fields. Lever ≥ 2: share of labelled runs (standard labels) whose intervention "
              "matches the paper's lever.", "",
              "| configuration | unsupported | output chars | lever ≥ 2 | labelled runs | audited runs |",
              "|---|---:|---:|---:|---:|---:|"]
    for m in order:
        b = board[m]
        lines.append(f"| {m} | {b['unsupported_gpt']} | {b['output_chars']} | {b['lever_ge2']} | {b['labelled']} | "
                     f"{b['audited']} |")
    lk = r["leakage"]
    lines += ["", "## Leakage", "", f"Counters over {lk['counters']['runs_checked']} runs: "
              f"{json.dumps(lk['counters']['totals'])}; web records re-checked: {lk['web_records_rechecked']}, "
              f"date violations: {lk['date_violations']}, unresolved: {lk['unresolved']}.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("labels", "report"))
    parser.add_argument("--method", action="append")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.stage == "labels":
        print(label_stage(args.method or list(Q6), args.workers))
        return
    r = report()
    atomic_json(PCD / "analysis_pcd.json", r)
    (PCD / "analysis_pcd.md").write_text(render(r))
    print(render(r))


if __name__ == "__main__":
    main()
