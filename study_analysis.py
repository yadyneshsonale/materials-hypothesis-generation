"""Experiment 41 (loop.md 22.1): the complete-study writer. Same-session baselines, quality judges and the report.

Usage (each stage is resumable):
  python study_analysis.py rejudge    GPT-5.6 judges the baselines again in this session (must_obey.md 6.10)
  python study_analysis.py pairwise   target-free pairwise quality judge, both orders: writer_study_b_o3mini vs the
                                      writer (GPT-5.6, DeepSeek, o1; must_obey.md 6.11)
  python study_analysis.py report     loop_study/analysis_study.json and analysis_study.md
"""

from __future__ import annotations

import os

_E = os.path.join(os.path.dirname(os.path.abspath(__file__)), "experiments", "high_temperature_hea_qwen35b")
os.environ.setdefault("MATHG_CASES_DIR", os.path.join(_E, "benchmark_v3_1", "cases"))
os.environ.setdefault("MATHG_LOOP_ROOT", os.path.join(_E, "loop_study"))

import argparse  # noqa: E402
import json  # noqa: E402
import random  # noqa: E402
import re  # noqa: E402
import statistics  # noqa: E402
from collections import defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

import diag_analysis as D  # noqa: E402
import hypo_loop as H  # noqa: E402
import loop_methods as LM  # noqa: E402
import round4_offline as R  # noqa: E402
from hypothesis_evidence_v2 import atomic_json  # noqa: E402
from temporal_eval_v3 import _blind_candidate, judge_absolute  # noqa: E402
from temporal_hypothesis_benchmark import _read_json  # noqa: E402

A, V, W = D.A, D.V, D.W
ST = H.OUT  # loop_study/ unless MATHG_LOOP_ROOT says otherwise
STUDY, TYPES, DESIGN, WEB_STUDY = LM.STUDY_CONFIGS
WRITER, Q64 = D.WRITER, D.Q64
BASELINES = (WRITER, Q64)
JUDGES = ("gpt", "deep")
ROUTE = re.compile(r"\b(arc[- ]melt\w*|vacuum arc|induction melt\w*|cast(ing)?|spark plasma|sps\b|powder metallurgy|"
                   r"mechanical(ly)? alloy\w*|ball[- ]mill\w*|hot[- ]press\w*|additive manufactur\w*|laser powder bed|"
                   r"lpbf|slm\b|directed energy|3d print\w*|homogeni[sz]\w*|anneal\w*|sinter\w*|hip\b|hot isostatic|"
                   r"forg\w*|roll\w*|sputter\w*|spray\w*|deposit\w*)", re.I)


def root_of(method: str) -> Path:
    return ST if method in LM.STUDY_CONFIGS else D.root_of(method)


def runs_of(method: str) -> list[dict[str, Any]]:
    return [r for r in W.runs(root_of(method), method) if r.get("status") == "ok"
            and r.get("benchmark", "v3.1") in R.BENCHMARKS]


def rejudge_stage(workers: int) -> dict[str, Any]:
    cases = H.cases()
    jobs = [(r, ST / "same_session" / m / f"{r['run_id']}.json") for m in BASELINES for r in runs_of(m)]
    jobs = [j for j in jobs if not j[1].exists()]
    if os.environ.get("MATHG_PENDING_SHUFFLE"):
        random.Random(int(os.environ["MATHG_PENDING_SHUFFLE"])).shuffle(jobs)

    def job(j: tuple[dict[str, Any], Path]) -> None:
        if not j[1].exists():
            atomic_json(j[1], judge_absolute(j[0], cases[j[0]["paper_id"]]))

    return D._parallel(jobs, job, workers, "rejudge")


_SCORES: dict[tuple[str, str], dict[str, float]] = {}


def scores(method: str, judge: str) -> dict[str, float]:
    """GPT-5.6 baselines from their same-session judgments; DeepSeek from the original ones (no drift, loop.md 20.2)."""
    if (method, judge) not in _SCORES:
        if judge == "gpt" and method in BASELINES:
            data: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
            for path in (ST / "same_session" / method).glob("PMC*.json"):
                paper, level = path.name.split("__")[:2]
                data[paper][level].append(R.recon(_read_json(path)["scores"]))
            _SCORES[(method, judge)] = A.per_paper(data)
        else:
            _SCORES[(method, judge)] = W.per_paper(root_of(method), method, judge)
    return _SCORES[(method, judge)]


def verdict(g: dict[str, Any], d: dict[str, Any]) -> str:
    if not g.get("papers"):
        return "no data"
    if g["ci95"][0] > 0 and d.get("diff", 0) > 0:
        return "raises the score"
    if g["ci95"][1] < 0 and d.get("diff", 0) < 0:
        return "lowers the score"
    return "no detectable difference"


def family(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    out: dict[str, Any] = {j: V.holm_family([{"config": a, "vs": b, **A.paired(scores(a, j), scores(b, j))}
                                             for a, b in pairs]) for j in JUDGES}
    out["decision"] = {f"{g['config']} vs {g['vs']}": verdict(g, d) for g, d in zip(out["gpt"], out["deep"])}
    return out


def labels_of(method: str) -> dict[tuple[str, str, int], dict[str, Any]]:
    root = root_of(method)
    out = {}
    for r in runs_of(method):
        path = root / method / "labels" / f"{r['run_id']}.json"
        if path.exists():
            out[D.key_of(r)] = _read_json(path)
    return out


def profile(method: str, targets: dict[tuple[str, str], str]) -> dict[str, Any]:
    root = root_of(method)
    runs = runs_of(method)
    judged = {j: {} for j in JUDGES}
    for r in runs:
        for j, folder in (("gpt", "gpt56"), ("deep", "deepseek")):
            path = root / method / "judgments" / folder / f"{r['run_id']}.json"
            if path.exists():
                judged[j][r["run_id"]] = _read_json(path)
    labs = labels_of(method)
    by_type: dict[str, list[bool]] = defaultdict(list)
    for k, lb in labs.items():
        by_type[targets.get(k[:2], "?")].append(lb["lever_match"] >= 2)
    out: dict[str, Any] = {
        "runs": len(runs), "gpt": W.A_mean(list(scores(method, "gpt").values())),
        "deep": W.A_mean(list(scores(method, "deep").values())),
        "lever_ge2": D.share([lb["lever_match"] >= 2 for lb in labs.values()]),
        "class_hit": D.share([lb["intervention_class"] == targets.get(k[:2]) for k, lb in labs.items()
                              if targets.get(k[:2])]),
        "lever_ge2_by_target_type": {t: D.share(v) for t, v in sorted(by_type.items())},
        "names_processing_route": D.share([bool(ROUTE.search(str(r["generation"].get("intervention", ""))))
                                           for r in runs]),
        "unsupported_gpt": D.share([x.get("classification") == "unsupported" for x in judged["gpt"].values()])}
    for j in JUDGES:
        out[f"dims_{j}"] = {d: W.A_mean([x["scores"][d] for x in judged[j].values()]) for d in H.ALL_DIMENSIONS}
    return out


def pairwise_stage(workers: int, judges: tuple[str, ...]) -> dict[str, Any]:
    base_runs = {D.key_of(r): r for r in runs_of(WRITER)}
    jobs = []
    for r in runs_of(STUDY):
        k = D.key_of(r)
        if k not in base_runs:
            continue
        for judge in judges:
            for order in ("baseline_first", "new_first"):
                path = ST / "pairwise" / "study_vs_writer" / judge / f"{k[0]}__{k[1]}__s{k[2]}__{order}.json"
                if not path.exists():
                    jobs.append((judge, order, base_runs[k], r, path))
    if os.environ.get("MATHG_PENDING_SHUFFLE"):
        random.Random(int(os.environ["MATHG_PENDING_SHUFFLE"])).shuffle(jobs)

    def job(j: tuple[Any, ...]) -> None:
        judge, order, base, new, path = j
        if path.exists():
            return
        first, second = (base, new) if order == "baseline_first" else (new, base)
        ga, ea = _blind_candidate(first)
        gb, eb = _blind_candidate(second)
        user = json.dumps({"research_question": base["query"], "candidate_A": {"hypothesis": ga, "cited_evidence": ea},
                           "candidate_B": {"hypothesis": gb, "cited_evidence": eb}}, ensure_ascii=False)
        raw = D.pair_call(judge, user)
        raw = raw if isinstance(raw, dict) else {}
        winner = str(raw.get("winner", "tie")).strip().upper()
        winner = winner if winner in ("A", "B", "TIE") else "TIE"
        new_side = "B" if order == "baseline_first" else "A"
        atomic_json(path, {"judge": judge, "order": order, "winner": winner, "new_won": winner == new_side,
                           "baseline_won": winner not in (new_side, "TIE"), "reason": str(raw.get("reason", ""))[:600],
                           "baseline_run": base["run_id"], "new_run": new["run_id"]})

    return D._parallel(jobs, job, workers, "pairwise")


def pairwise_results() -> dict[str, Any]:
    out: dict[str, Any] = {}
    items = []
    for judge in D.PAIR_JUDGES:
        by_pair: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        for path in sorted((ST / "pairwise" / "study_vs_writer" / judge).glob("*.json")):
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


def leakage() -> dict[str, Any]:
    cases = H.cases()
    evidence = W.Evidence()
    violations, checked = [], 0
    for run in W.runs(ST, WEB_STUDY):
        cutoff = cases[run["paper_id"]]["publication_date"]
        for rid in run["seen_ids"]:
            record = evidence.web(rid)
            if record is None:
                continue
            checked += 1
            dates = [x for x in (record.structured or {}).get("dates", {}).values() if x]
            if any(x >= cutoff for x in dates + [record.publication_date]):
                violations.append(f"{run['run_id']}: {rid}")
    return {"counters": W.counters(ST), "web_records_rechecked": checked, "date_violations": len(violations)}


def report() -> dict[str, Any]:
    targets = R.unit_targets(R.judged_runs())
    r: dict[str, Any] = {
        "Q1_primary": family([(STUDY, WRITER), (WEB_STUDY, Q64)]),
        "Q2_components": family([(TYPES, WRITER), (DESIGN, WRITER)]),
        "Q3_profiles": {m: profile(m, targets) for m in (WRITER, Q64) + LM.STUDY_CONFIGS},
        "Q4_quality": pairwise_results(),
        "same_session_baselines": {m: {"same_session_gpt": W.A_mean(list(scores(m, "gpt").values())),
                                       "rejudged_runs": len(list((ST / "same_session" / m).glob("*.json")))}
                                   for m in BASELINES},
        "leakage": leakage(),
    }
    r["decision"] = {k: v for fam in ("Q1_primary", "Q2_components") for k, v in r[fam]["decision"].items()}
    return r


def render(r: dict[str, Any]) -> str:
    L = ["# Experiment 41: a complete-study writer", "", "Pre-registered in loop.md 22.1. GPT-5.6 baselines are "
         "judged again in this session (must_obey.md 6.10).", ""]
    for fam, title in (("Q1_primary", "Q1 (primary)"), ("Q2_components", "Q2 (components)")):
        L += [f"## {title}", "", "| comparison | GPT-5.6 [CI] | DeepSeek [CI] | decision |", "|---|---|---|---|"]
        for g, d in zip(r[fam]["gpt"], r[fam]["deep"]):
            L.append(f"| {g['config']} vs {g['vs']} | {D._cell(g)} | {D._cell(d)} | "
                     f"{r[fam]['decision'][g['config'] + ' vs ' + g['vs']]} |")
        L.append("")
    L += ["## Q3: failure points", "", "| configuration | runs | GPT-5.6 | DeepSeek | lever ≥ 2 | class hit | lever ≥ 2 on "
          "processing-route papers | on simulation papers | names a route | intervention | conditions | mechanism | "
          "outcome | unsupported |", "|---|" + "---:|" * 14]
    for m, p in r["Q3_profiles"].items():
        bt, dg = p["lever_ge2_by_target_type"], p["dims_gpt"]
        L.append(f"| {m} | {p['runs']} | {p['gpt']} | {p['deep']} | {p['lever_ge2']} | {p['class_hit']} | "
                 f"{bt.get('processing_route')} | {bt.get('simulation_study')} | {p['names_processing_route']} | "
                 f"{dg['intervention_reconstruction']} | {dg['condition_agreement']} | {dg['mechanism_agreement']} | "
                 f"{dg['outcome_agreement']} | {p['unsupported_gpt']} |")
    L += ["", "## Q4: quality without the answer key (writer_study_b_o3mini vs the writer)", "",
          "| judge | pairs | new wins | writer wins | net preference [CI] |", "|---|---:|---:|---:|---|"]
    for judge, v in r["Q4_quality"].items():
        if v.get("pairs"):
            L.append(f"| {judge} | {v['pairs']} | {v['new_wins']} | {v['writer_wins']} | "
                     f"{D._cell(v['net_preference_for_new'])} |")
    lk = r["leakage"]
    L += ["", f"Same-session baselines: {json.dumps(r['same_session_baselines'])}", "", "## Leakage", "",
          f"Counters over {lk['counters']['runs_checked']} runs: {json.dumps(lk['counters']['totals'])}; web records "
          f"re-checked: {lk['web_records_rechecked']}, date violations: {lk['date_violations']}.", ""]
    return "\n".join(L)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("rejudge", "pairwise", "report"))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--judge", action="append", choices=D.PAIR_JUDGES)
    args = parser.parse_args()
    if args.stage == "report":
        r = report()
        atomic_json(ST / "analysis_study.json", r)
        (ST / "analysis_study.md").write_text(render(r))
        print(render(r))
    elif args.stage == "rejudge":
        print(rejudge_stage(args.workers))
    else:
        print(pairwise_stage(args.workers, tuple(args.judge or D.PAIR_JUDGES)))


if __name__ == "__main__":
    main()
