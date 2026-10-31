"""Experiment 42 (loop.md 23.1): stage changes from six reviews. Evaluation stages and the report.

Usage (each stage is resumable; MATHG_PENDING_SHUFFLE=<seed> gives a second process another job order):
  python v2_analysis.py rejudge             GPT-5.6 (v1) judges the baselines again in this session (must_obey 6.10)
  python v2_analysis.py judge2 --judge J    measurement v2 (judge_v2.py) for every compared configuration, the 216
                                            sanity controls and the test-retest set; J = gpt56 or deepseek
  python v2_analysis.py packlabels          GPT-5.6 labels the retrieval-v2 packs' passages against the key
                                            (target-aware analysis only)
  python v2_analysis.py pairwise --judge J  target-free quality: web64k_v2_b_o3mini vs the writer, both orders
  python v2_analysis.py report              loop_v2/analysis_v2.json and analysis_v2.md
"""

from __future__ import annotations

import os

_E = os.path.join(os.path.dirname(os.path.abspath(__file__)), "experiments", "high_temperature_hea_qwen35b")
os.environ.setdefault("MATHG_CASES_DIR", os.path.join(_E, "benchmark_v3_1", "cases"))
os.environ.setdefault("MATHG_LOOP_ROOT", os.path.join(_E, "loop_v2"))

import argparse  # noqa: E402
import json  # noqa: E402
import random  # noqa: E402
import re  # noqa: E402
import statistics  # noqa: E402
from collections import Counter, defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

import diag_analysis as D  # noqa: E402
import hypo_loop as H  # noqa: E402
import judge_v2 as J2  # noqa: E402
import loop_methods as LM  # noqa: E402
import review_measurement as RM  # noqa: E402
import round4_offline as R  # noqa: E402
import stage_v2 as S2  # noqa: E402
from hypothesis_evidence_v2 import atomic_json  # noqa: E402
from temporal_eval_v3 import _blind_candidate, judge_absolute  # noqa: E402
from temporal_hypothesis_benchmark import _read_json  # noqa: E402

A, V, W = D.A, D.V, D.W
E = W.E
V2 = H.OUT  # loop_v2/ unless MATHG_LOOP_ROOT says otherwise
WRITER_V2, R2, BEST = LM.V2_CONFIGS
WRITER, Q64 = "writer_only_b_o3mini", "web_text_64k_b_o3mini"
BASELINES = (WRITER, Q64)
JUDGED_V2 = LM.V2_CONFIGS + (WRITER, Q64, "closed_book_o3mini", "closed_book", "writer_study_b_o3mini",
                             "oracle_hint_lever_b_o3mini")
JUDGES = ("gpt", "deep")
MISMATCHED = ("PMC12525334", "PMC12985727", "PMC12991304")  # question-key mismatches found by the judge review
NUMBER = re.compile(r"\d+(?:\.\d+)?\s*(?:°\s*C|K\b|h\b|min\b|s\b|MPa|GPa|wt\.?\s?%|at\.?\s?%|%|µm|μm|nm\b|mm\b|kV|W\b)")


def root_of(method: str) -> Path:
    if method in LM.V2_CONFIGS:
        return V2
    if method.startswith("oracle_"):
        return E / "loop_diag"
    if method == "writer_study_b_o3mini":
        return E / "loop_study"
    if method.startswith("web_"):
        return E / "loop_web"
    return E / "loop"


def runs_of(method: str) -> list[dict[str, Any]]:
    return [r for r in W.runs(root_of(method), method) if r.get("status") == "ok"
            and r.get("benchmark", "v3.1") in R.BENCHMARKS]


def _shuffle(jobs: list[Any]) -> list[Any]:
    if os.environ.get("MATHG_PENDING_SHUFFLE"):
        random.Random(int(os.environ["MATHG_PENDING_SHUFFLE"])).shuffle(jobs)
    if os.environ.get("MATHG_PENDING_REVERSE"):
        jobs.reverse()  # a second loop on the same stage starts from the other end
    return jobs


# ---------------------------------------------------------------- v1 same-session baselines

def rejudge_stage(workers: int) -> dict[str, Any]:
    cases = H.cases()
    jobs = _shuffle([(r, V2 / "same_session" / m / f"{r['run_id']}.json") for m in BASELINES for r in runs_of(m)
                     if not (V2 / "same_session" / m / f"{r['run_id']}.json").exists()])

    def job(j: tuple[dict[str, Any], Path]) -> None:
        if not j[1].exists():
            atomic_json(j[1], judge_absolute(j[0], cases[j[0]["paper_id"]]))

    return D._parallel(jobs, job, workers, "rejudge")


_SCORES: dict[tuple[str, str], dict[str, float]] = {}


def scores(method: str, judge: str, exclude: tuple[str, ...] = ()) -> dict[str, float]:
    """v1 per-paper reconstruction. GPT-5.6 baselines use their same-session judgments (DeepSeek did not drift)."""
    key = (method, judge)
    if key not in _SCORES:
        if judge == "gpt" and method in BASELINES:
            data: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
            for path in (V2 / "same_session" / method).glob("PMC*.json"):
                paper, level = path.name.split("__")[:2]
                data[paper][level].append(R.recon(_read_json(path)["scores"]))
            _SCORES[key] = A.per_paper(data)
        else:
            _SCORES[key] = W.per_paper(root_of(method), method, judge)
    return {p: v for p, v in _SCORES[key].items() if p not in exclude}


def verdict(g: dict[str, Any], d: dict[str, Any]) -> str:
    if not g.get("papers"):
        return "no data"
    if g["ci95"][0] > 0 and d.get("diff", 0) > 0:
        return "raises the score"
    if g["ci95"][1] < 0 and d.get("diff", 0) < 0:
        return "lowers the score"
    return "no detectable difference"


def family(pairs: list[tuple[str, str]], score_fn=scores, exclude: tuple[str, ...] = ()) -> dict[str, Any]:
    out: dict[str, Any] = {j: V.holm_family([{"config": a, "vs": b, **A.paired(score_fn(a, j, exclude),
                                                                                score_fn(b, j, exclude))}
                                             for a, b in pairs]) for j in JUDGES}
    out["decision"] = {f"{g['config']} vs {g['vs']}": verdict(g, d) for g, d in zip(out["gpt"], out["deep"])}
    return out


# ---------------------------------------------------------------- measurement v2

def v2_path(kind: str, judge: str, name: str, item: str) -> Path:
    return V2 / "judge_v2" / kind / name / judge / f"{item}.json"


def judge2_stage(judge: str, workers: int) -> dict[str, Any]:
    """Jobs in priority order (the thread pool takes them first in, first out): the sanity controls and the
    test-retest set (validation), then the configurations in JUDGED_V2 order (the five of Q1-Q2 first)."""
    cases = H.cases()
    control_cases = RM.held_out_cases()
    jobs: list[tuple[Path, str, dict[str, Any], dict[str, Any]]] = []
    for item in RM.load_controls():
        path = v2_path("controls", judge, "controls", item["run_id"])
        if not path.exists():
            jobs.append((path, item["query"], control_cases[item["paper_id"]]["hidden_target"], item["generation"]))
    for r in runs_of(WRITER):
        if int(r["sample"]) == 1:
            path = v2_path("retest", judge, WRITER, r["run_id"])
            if not path.exists():
                jobs.append((path, r["query"], cases[r["paper_id"]]["hidden_target"], r["generation"]))
    for method in JUDGED_V2:
        for r in runs_of(method):
            path = v2_path("runs", judge, method, r["run_id"])
            if not path.exists():
                jobs.append((path, r["query"], cases[r["paper_id"]]["hidden_target"], r["generation"]))
    jobs = _shuffle(jobs)

    def job(j: tuple[Path, str, dict[str, Any], dict[str, Any]]) -> None:
        path, query, target, generation = j
        if not path.exists():
            atomic_json(path, {"item": path.stem, **J2.judge(judge, query, target, generation)})

    return D._parallel(jobs, job, workers, f"judge2-{judge}")


def v2_scores(method: str, judge: str, exclude: tuple[str, ...] = ()) -> dict[str, float]:
    folder = "gpt56" if judge == "gpt" else "deepseek"
    data: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for path in (V2 / "judge_v2" / "runs" / method / folder).glob("PMC*.json"):
        paper, level = path.name.split("__")[:2]
        data[paper][level].append(J2.recon(_read_json(path)["scores"]))
    return {p: v for p, v in A.per_paper(data).items() if p not in exclude}


def v2_validation() -> dict[str, Any]:
    out: dict[str, Any] = {}
    controls = {}
    for judge, folder in (("gpt56", "gpt56"), ("deepseek", "deepseek")):
        items = {p.stem: _read_json(p) for p in sorted((V2 / "judge_v2" / "controls" / "controls" / folder).glob("*.json"))}
        controls[judge] = items
    summary = RM.controls_summary(controls)
    for judge, s in summary.items():
        out[judge] = {"controls": s}
    for judge, folder in (("gpt56", "gpt56"), ("deepseek", "deepseek")):
        by_lever: dict[int, list[int]] = defaultdict(list)
        for method in JUDGED_V2:
            root = root_of(method)
            for r in runs_of(method):
                label_path = root / method / "labels" / f"{r['run_id']}.json"
                path = v2_path("runs", folder, method, r["run_id"])
                if label_path.exists() and path.exists():
                    by_lever[int(_read_json(label_path)["lever_match"])].append(
                        _read_json(path)["scores"]["intervention_reconstruction"])
        means = {k: round(statistics.fmean(v), 3) for k, v in sorted(by_lever.items()) if v}
        counts = {k: len(v) for k, v in sorted(by_lever.items())}
        monotonic = all(k in means for k in (0, 1, 2)) and means[0] < means[1] < means[2]
        pairs = []
        for p in sorted((V2 / "judge_v2" / "retest" / WRITER / folder).glob("*.json")):
            first = v2_path("runs", folder, WRITER, p.stem)
            if first.exists():
                pairs.append((J2.recon(_read_json(first)["scores"]), J2.recon(_read_json(p)["scores"])))
        rho = R.spearman([a for a, _ in pairs], [b for _, b in pairs]) if len(pairs) > 5 else None
        checks = dict(out[judge]["controls"]["checks"])
        checks["C5_monotonic_partial_credit"] = monotonic
        checks["C6_retest_rho_ge_0.80"] = rho is not None and rho >= 0.80
        out[judge].update({"intervention_by_lever_label": means, "lever_label_counts": counts,
                           "retest": {"runs": len(pairs), "rho": round(rho, 3) if rho is not None else None,
                                      "mean_abs_diff": round(statistics.fmean(abs(a - b) for a, b in pairs), 3)
                                      if pairs else None},
                           "checks": checks, "validated": all(checks.values())})
    return out


# ---------------------------------------------------------------- pack labels, pairwise quality

def packlabels_stage(workers: int) -> dict[str, Any]:
    cases = H.cases()
    evidence = W.Evidence()
    jobs = [r for r in runs_of(R2) if int(r["sample"]) == 1
            and not (V2 / "pack_labels" / "R2" / f"{r['paper_id']}__{r['query_level']}.json").exists()]

    def job(run: dict[str, Any]) -> None:
        records = [evidence.web(rid) for rid in run["seen_ids"]]
        items = [{"id": n + 1, "text": rec.text[:1600]} for n, rec in enumerate(records) if rec is not None]
        labels = D.label_items(cases[run["paper_id"]], items)
        atomic_json(V2 / "pack_labels" / "R2" / f"{run['paper_id']}__{run['query_level']}.json",
                    {"pack": "R2", "paper_id": run["paper_id"], "level": run["query_level"],
                     "items": [{"record_id": run["seen_ids"][i["id"] - 1], "lever_match": labels.get(i["id"])}
                               for i in items]})

    return D._parallel(jobs, job, workers, "packlabels")


def pairwise_stage(workers: int, judges: tuple[str, ...]) -> dict[str, Any]:
    base = {D.key_of(r): r for r in runs_of(WRITER)}
    jobs = []
    for r in runs_of(BEST):
        k = D.key_of(r)
        if k in base:
            for judge in judges:
                for order in ("baseline_first", "new_first"):
                    path = V2 / "pairwise" / "best_vs_writer" / judge / f"{k[0]}__{k[1]}__s{k[2]}__{order}.json"
                    if not path.exists():
                        jobs.append((judge, order, base[k], r, path))
    jobs = _shuffle(jobs)

    def job(j: tuple[Any, ...]) -> None:
        judge, order, b, n, path = j
        if path.exists():
            return
        first, second = (b, n) if order == "baseline_first" else (n, b)
        ga, ea = _blind_candidate(first)
        gb, eb = _blind_candidate(second)
        user = json.dumps({"research_question": b["query"], "candidate_A": {"hypothesis": ga, "cited_evidence": ea},
                           "candidate_B": {"hypothesis": gb, "cited_evidence": eb}}, ensure_ascii=False)
        raw = D.pair_call(judge, user)
        raw = raw if isinstance(raw, dict) else {}
        winner = str(raw.get("winner", "tie")).strip().upper()
        winner = winner if winner in ("A", "B", "TIE") else "TIE"
        side = "B" if order == "baseline_first" else "A"
        atomic_json(path, {"judge": judge, "order": order, "winner": winner, "new_won": winner == side,
                           "baseline_won": winner not in (side, "TIE"), "reason": str(raw.get("reason", ""))[:600]})

    return D._parallel(jobs, job, workers, "pairwise")


def pairwise_results() -> dict[str, Any]:
    out: dict[str, Any] = {}
    items = []
    for judge in D.PAIR_JUDGES:
        by_pair: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        for path in sorted((V2 / "pairwise" / "best_vs_writer" / judge).glob("*.json")):
            stem, order = path.stem.rsplit("__", 1)
            by_pair[stem][order] = _read_json(path)
        per_paper: dict[str, list[float]] = defaultdict(list)
        for stem, orders in by_pair.items():
            if len(orders) == 2:
                won = all(o["new_won"] for o in orders.values())
                lost = all(o["baseline_won"] for o in orders.values())
                per_paper[stem.split("__")[0]].append(1.0 if won else -1.0 if lost else 0.0)
        if not per_paper:
            out[judge] = {"pairs": 0}
            continue
        vals = [v for vs in per_paper.values() for v in vs]
        paired = A.paired({p: statistics.fmean(v) for p, v in per_paper.items()}, {p: 0.0 for p in per_paper})
        out[judge] = {"pairs": len(vals), "new_wins": D.share([v == 1 for v in vals]),
                      "writer_wins": D.share([v == -1 for v in vals]), "net_preference_for_new": paired}
        items.append({"config": judge, **paired})
    for item in V.holm_family(items):
        out[item["config"]]["net_preference_for_new"]["holm_p"] = item["holm_p"]
    return out


# ---------------------------------------------------------------- diagnostics, leakage, report

def diagnostics(method: str) -> dict[str, Any]:
    root = root_of(method)
    runs = runs_of(method)
    labels, judged = [], []
    for r in runs:
        lp = root / method / "labels" / f"{r['run_id']}.json"
        gp = root / method / "judgments" / "gpt56" / f"{r['run_id']}.json"
        if lp.exists():
            labels.append(_read_json(lp))
        if gp.exists():
            judged.append(_read_json(gp))
    invented = []
    for r in runs:
        q = r["query"]
        g = r["generation"]
        nums = NUMBER.findall(f"{g.get('conditions', '')} {g.get('predicted_outcome', '')}")
        invented.append(any(n.replace(" ", "") not in q.replace(" ", "") for n in nums))
    return {"runs": len(runs), "lever_ge2": D.share([lb["lever_match"] >= 2 for lb in labels]),
            "dims_gpt": {d: W.A_mean([x["scores"][d] for x in judged]) for d in J2.DIMENSIONS},
            "unsupported_gpt": D.share([x.get("classification") == "unsupported" for x in judged]),
            "invented_numbers": D.share(invented),
            "citation_filtered": sum(1 for r in runs if (r["generation"].get("citation_validation") or {})
                                     .get("status") == "filtered_unknown_ids"),
            "llm_calls": W.A_mean([r["llm_calls"] for r in runs]), "chars_in": W.A_mean([r["chars_in"] for r in runs])}


def citation_slips() -> dict[str, Any]:
    """Citation slips of the evidence configurations (repaired by filtering) and the paired v1 score difference
    against web_text_64k_b_o3mini by filter status: does the repair explain the result?"""
    base = {D.key_of(r): r for r in runs_of(Q64)}
    out: dict[str, Any] = {}
    for method in (R2, BEST):
        kinds: Counter = Counter()
        groups: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        for r in runs_of(method):
            g = r["generation"]
            kinds += S2.classify_removed((g.get("citation_validation") or {}).get("removed_unknown_ids") or [],
                                         r["seen_ids"])
            filtered = (g.get("citation_validation") or {}).get("status") == "filtered_unknown_ids"
            left = len(g.get("supporting_evidence_ids") or []) + len(g.get("conflicting_evidence_ids") or [])
            group = "valid" if not filtered else "filtered, citations left" if left else "filtered, none left"
            b = base.get(D.key_of(r))
            for folder in ("gpt56", "deepseek"):
                a_path = V2 / method / "judgments" / folder / f"{r['run_id']}.json"
                b_path = root_of(Q64) / Q64 / "judgments" / folder / f"{b['run_id']}.json" if b else None
                if a_path.exists() and b_path is not None and b_path.exists():
                    groups[folder][group].append(R.recon(_read_json(a_path)["scores"])
                                                 - R.recon(_read_json(b_path)["scores"]))
        out[method] = {"removed_ids": dict(kinds),
                       "difference_vs_web_text_64k": {f: {k: {"runs": len(v), "mean": round(statistics.fmean(v), 3)}
                                                          for k, v in gs.items()} for f, gs in groups.items()}}
    return out


def pack_density() -> dict[str, Any]:
    out = {}
    for name, folder in (("R2 (retrieval v2, 64,000 characters)", V2 / "pack_labels" / "R2"),
                         ("Q64 (question order, 64,000 characters)", E / "loop_diag" / "pack_labels" / "Q64")):
        dens, contains = [], []
        for path in sorted(folder.glob("*.json")):
            values = [i["lever_match"] for i in _read_json(path)["items"] if i["lever_match"] is not None]
            if values:
                dens.append(statistics.fmean(v >= 2 for v in values))
                contains.append(any(v >= 2 for v in values))
        out[name] = {"units": len(dens), "lever_passage_share": round(statistics.fmean(dens), 3) if dens else None,
                     "pack_contains_lever": D.share(contains)}
    return out


def leakage() -> dict[str, Any]:
    cases = H.cases()
    evidence = W.Evidence()
    violations, checked = [], 0
    for method in LM.V2_CONFIGS:
        for run in W.runs(V2, method):
            cutoff = cases[run["paper_id"]]["publication_date"]
            for rid in run["seen_ids"]:
                record = evidence.web(rid)
                if record is None:
                    continue
                checked += 1
                dates = [x for x in (record.structured or {}).get("dates", {}).values() if x]
                if any(x >= cutoff for x in dates + [record.publication_date]):
                    violations.append(f"{run['run_id']}: {rid}")
    return {"counters": W.counters(V2), "web_records_rechecked": checked, "date_violations": len(violations)}


def completeness() -> dict[str, Any]:
    """How much of each pre-registered evaluation exists on disk (the report may be written before all of it)."""
    def count(pattern: str) -> int:
        return len(list(V2.glob(pattern)))

    return {
        "v1_gpt56_new_runs": {m: count(f"{m}/judgments/gpt56/*.json") for m in LM.V2_CONFIGS},
        "v1_deepseek_new_runs": {m: count(f"{m}/judgments/deepseek/*.json") for m in LM.V2_CONFIGS},
        "same_session_gpt56_baselines": {m: count(f"same_session/{m}/PMC*.json") for m in BASELINES},
        "audits": {m: count(f"{m}/audit/*.json") for m in LM.V2_CONFIGS},
        "lever_labels": {m: count(f"{m}/labels/*.json") for m in LM.V2_CONFIGS},
        "pack_labels_R2": count("pack_labels/R2/*.json"),
        "pairwise": {j: count(f"pairwise/best_vs_writer/{j}/*.json") for j in D.PAIR_JUDGES},
        "v2": {folder: {"runs": {m: count(f"judge_v2/runs/{m}/{folder}/*.json") for m in JUDGED_V2},
                        "controls": count(f"judge_v2/controls/controls/{folder}/*.json"),
                        "retest": count(f"judge_v2/retest/{WRITER}/{folder}/*.json")}
               for folder in ("gpt56", "deepseek")},
        "planned": {"runs_per_configuration": 270, "same_session_per_baseline": 270, "pack_labels": 135,
                    "pairwise_per_judge": 540, "v2_controls": 216, "v2_retest": 135},
    }


def report() -> dict[str, Any]:
    q1 = [(BEST, WRITER), (BEST, Q64)]
    q2 = [(WRITER_V2, WRITER), (R2, Q64), (BEST, R2)]
    v1_means = {m: {j: W.A_mean(list(scores(m, j).values())) for j in JUDGES} for m in JUDGED_V2}
    v2_means = {m: {j: W.A_mean(list(v2_scores(m, j).values())) for j in JUDGES} for m in JUDGED_V2}
    ranks = {}
    for j in JUDGES:
        ms = [m for m in JUDGED_V2 if v1_means[m][j] is not None and v2_means[m][j] is not None]
        rho = R.spearman([v1_means[m][j] for m in ms], [v2_means[m][j] for m in ms])
        ranks[j] = {"configurations": len(ms), "spearman_v1_v2": round(rho, 3) if rho is not None else None}
    return {
        "Q1_primary_v1": family(q1), "Q2_stages_v1": family(q2),
        "Q1_v1_without_mismatched_papers": family(q1, exclude=MISMATCHED),
        "Q3_quality": pairwise_results(),
        "Q4_v2_validation": v2_validation(),
        "Q4_v2_means": v2_means, "v1_means": v1_means, "Q4_v2_rank_agreement": ranks,
        "Q4_Q1_v2": family(q1, v2_scores), "Q4_Q2_v2": family(q2, v2_scores),
        "diagnostics": {m: diagnostics(m) for m in LM.V2_CONFIGS + BASELINES},
        "pack_density": pack_density(), "citation_slips": citation_slips(), "leakage": leakage(),
        "completeness": completeness(),
        "same_session_baselines": {m: {"same_session_gpt": v1_means[m]["gpt"],
                                       "original_gpt": W.A_mean(list(W.per_paper(root_of(m), m, "gpt").values()))}
                                   for m in BASELINES},
    }


def _family_md(title: str, fam: dict[str, Any], gpt_incomplete: bool = False) -> list[str]:
    lines = [f"## {title}", "", "| comparison | GPT-5.6 [CI] | DeepSeek [CI] | decision |", "|---|---|---|---|"]
    for g, d in zip(fam["gpt"], fam["deep"]):
        gpt = "incomplete" if gpt_incomplete else D._cell(g)
        decision = "no GPT-5.6 data" if gpt_incomplete else fam["decision"][g["config"] + " vs " + g["vs"]]
        lines.append(f"| {g['config']} vs {g['vs']} | {gpt} | {D._cell(d)} | {decision} |")
    return lines + [""]


def render(r: dict[str, Any]) -> str:
    L = ["# Experiment 42: stage changes from six reviews", "", "Pre-registered in loop.md 23.1. Primary metric: the "
         "original judge (v1); GPT-5.6 baselines judged again in this session. Measurement v2 is secondary.", ""]
    c = r["completeness"]
    L += ["## Completeness (items on disk when this report was written; loop.md 23.1 finalisation notes)", "",
          f"- v1 GPT-5.6, new runs: {json.dumps(c['v1_gpt56_new_runs'])} of 270 each",
          f"- v1 DeepSeek, new runs: {json.dumps(c['v1_deepseek_new_runs'])} of 270 each",
          f"- same-session GPT-5.6 baselines: {json.dumps(c['same_session_gpt56_baselines'])} of 270 each",
          f"- audits: {json.dumps(c['audits'])}; lever labels: {json.dumps(c['lever_labels'])} (of 270 each)",
          f"- pack labels: {c['pack_labels_R2']} of 135; pairwise: {json.dumps(c['pairwise'])} of 540 each",
          f"- measurement v2: {json.dumps(c['v2'])} (runs of 270 each; controls of 216; retest of 135)", ""]
    L += _family_md("Q1 (primary, v1): the combined configuration", r["Q1_primary_v1"])
    L += _family_md("Q2 (v1): each stage", r["Q2_stages_v1"])
    L += _family_md("Q1 (v1) without the three question-key mismatches (sensitivity)", r["Q1_v1_without_mismatched_papers"])
    L += ["## Q3: quality without the answer key (web64k_v2_b_o3mini vs the writer)", "",
          "| judge | pairs | new wins | writer wins | net preference [CI] |", "|---|---:|---:|---:|---|"]
    for judge, v in r["Q3_quality"].items():
        if v.get("pairs") and v["pairs"] < c["planned"]["pairwise_per_judge"] // 2:
            L.append(f"| {judge} | {v['pairs']} | incomplete ({v['pairs']} of "
                     f"{c['planned']['pairwise_per_judge'] // 2} pairs): not interpretable | | |")
        elif v.get("pairs"):
            L.append(f"| {judge} | {v['pairs']} | {v['new_wins']} | {v['writer_wins']} | "
                     f"{D._cell(v['net_preference_for_new'])} |")
    L += ["", "## Q4: measurement v2 (anchored, evidence-blind)", ""]
    v2_incomplete = {}
    for judge, v in r["Q4_v2_validation"].items():
        n_controls = c["v2"][judge]["controls"]
        n_retest = c["v2"][judge]["retest"]
        v2_runs = c["v2"][judge]["runs"]
        v2_incomplete[judge] = (n_controls < c["planned"]["v2_controls"] or n_retest < c["planned"]["v2_retest"]
                                or min(v2_runs.values()) < c["planned"]["runs_per_configuration"])
        if n_controls < c["planned"]["v2_controls"] or n_retest < c["planned"]["v2_retest"]:
            L.append(f"- {judge}: incomplete ({n_controls} of {c['planned']['v2_controls']} controls, {n_retest} of "
                     f"{c['planned']['v2_retest']} re-test items), so not evaluated; its numbers below are not "
                     f"interpretable")
            continue
        L.append(f"- {judge}: validated {v['validated']}; checks {json.dumps(v['checks'])}; intervention by lever "
                 f"label {json.dumps(v['intervention_by_lever_label'])}; retest {json.dumps(v['retest'])}; controls "
                 f"means {json.dumps(v['controls']['means'])}, AUC {v['controls']['auc_positive_vs_negatives']}")
    gpt_v2_head = "v2 GPT-5.6 (incomplete)" if v2_incomplete["gpt56"] else "v2 GPT-5.6"
    L += ["", f"| configuration | v1 GPT-5.6 | {gpt_v2_head} | v1 DeepSeek | v2 DeepSeek |", "|---|---:|---:|---:|---:|"]
    for m in JUDGED_V2:
        L.append(f"| {m} | {r['v1_means'][m]['gpt']} | {r['Q4_v2_means'][m]['gpt']} | {r['v1_means'][m]['deep']} | "
                 f"{r['Q4_v2_means'][m]['deep']} |")
    ranks = dict(r["Q4_v2_rank_agreement"])
    if v2_incomplete["gpt56"]:
        ranks["gpt"] = "GPT-5.6 v2 incomplete"
    L += ["", f"Rank agreement v1 vs v2: {json.dumps(ranks)}", ""]
    L += _family_md("Q1 under measurement v2", r["Q4_Q1_v2"], v2_incomplete["gpt56"])
    L += _family_md("Q2 under measurement v2", r["Q4_Q2_v2"], v2_incomplete["gpt56"])
    L += ["## Diagnostics", "", "| configuration | runs | lever ≥ 2 | intervention | conditions | mechanism | outcome | "
          "unsupported | invented numbers | citations filtered | calls | input chars |", "|---|" + "---:|" * 11]
    for m, d in r["diagnostics"].items():
        dg = d["dims_gpt"]
        L.append(f"| {m} | {d['runs']} | {d['lever_ge2']} | {dg['intervention_reconstruction']} | "
                 f"{dg['condition_agreement']} | {dg['mechanism_agreement']} | {dg['outcome_agreement']} | "
                 f"{d['unsupported_gpt']} | {d['invented_numbers']} | {d['citation_filtered']} | {d['llm_calls']} | "
                 f"{d['chars_in']} |")
    L += ["", f"Pack density: {json.dumps(r['pack_density'])}", "",
          f"Citation slips (repaired by filtering) and the v1 difference against web_text_64k by filter status: "
          f"{json.dumps(r['citation_slips'])}", "",
          f"Same-session baselines: {json.dumps(r['same_session_baselines'])}", "", "## Leakage", "",
          f"Counters over {r['leakage']['counters']['runs_checked']} runs: "
          f"{json.dumps(r['leakage']['counters']['totals'])}; web records re-checked: "
          f"{r['leakage']['web_records_rechecked']}, date violations: {r['leakage']['date_violations']}.", ""]
    return "\n".join(L)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("rejudge", "judge2", "packlabels", "pairwise", "report"))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--judge", action="append")
    args = parser.parse_args()
    if args.stage == "report":
        r = report()
        atomic_json(V2 / "analysis_v2.json", r)
        (V2 / "analysis_v2.md").write_text(render(r))
        print(render(r))
    elif args.stage == "rejudge":
        print(rejudge_stage(args.workers))
    elif args.stage == "judge2":
        for judge in args.judge or ("gpt56",):
            print(judge2_stage(judge, args.workers))
    elif args.stage == "packlabels":
        print(packlabels_stage(args.workers))
    else:
        print(pairwise_stage(args.workers, tuple(args.judge or D.PAIR_JUDGES)))


if __name__ == "__main__":
    main()
