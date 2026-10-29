"""Experiment 40 (loop.md 21.1): the evidence-choosing agent. Same-session baselines, quality judges and the report.

Usage (each stage is resumable):
  python agent_analysis.py rejudge    GPT-5.6 judges the baselines again in this session (must_obey.md 6.10)
  python agent_analysis.py pairwise   target-free pairwise quality judge, both orders: the agent vs the writer and vs
                                      web_text_64k_b_o3mini (GPT-5.6, DeepSeek, o1; must_obey.md 6.11)
  python agent_analysis.py report     loop_agent/analysis_agent.json and analysis_agent.md
"""

from __future__ import annotations

import os

_E = os.path.join(os.path.dirname(os.path.abspath(__file__)), "experiments", "high_temperature_hea_qwen35b")
os.environ.setdefault("MATHG_CASES_DIR", os.path.join(_E, "benchmark_v3_1", "cases"))
os.environ.setdefault("MATHG_LOOP_ROOT", os.path.join(_E, "loop_agent"))

import argparse  # noqa: E402
import json  # noqa: E402
import random  # noqa: E402
import statistics  # noqa: E402
from collections import Counter, defaultdict  # noqa: E402
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
AG = H.OUT  # loop_agent/ unless MATHG_LOOP_ROOT says otherwise
AGENT, ONLY, DRAFT = LM.AGENT_CONFIGS
WRITER, Q64, T16 = D.WRITER, D.Q64, D.T16
BASELINES = (WRITER, Q64)
COMPARISONS = {"agent_vs_writer": (WRITER, AGENT), "agent_vs_q64": (Q64, AGENT)}
JUDGES = ("gpt", "deep")


def root_of(method: str) -> Path:
    if method in LM.AGENT_CONFIGS:
        return AG
    if method.startswith("oracle_"):
        return W.E / "loop_diag"  # the experiment-39 reference (D.DIAG follows MATHG_LOOP_ROOT, set to loop_agent here)
    return D.root_of(method)


def runs_of(method: str) -> list[dict[str, Any]]:
    return [r for r in W.runs(root_of(method), method) if r.get("status") == "ok"
            and r.get("benchmark", "v3.1") in R.BENCHMARKS]


# ---------------------------------------------------------------- same-session baselines (must_obey.md 6.10)

def rejudge_stage(workers: int) -> dict[str, Any]:
    cases = H.cases()
    jobs = [(r, AG / "same_session" / m / f"{r['run_id']}.json") for m in BASELINES for r in runs_of(m)]
    jobs = [j for j in jobs if not j[1].exists()]
    if os.environ.get("MATHG_PENDING_SHUFFLE"):
        random.Random(int(os.environ["MATHG_PENDING_SHUFFLE"])).shuffle(jobs)

    def job(j: tuple[dict[str, Any], Path]) -> None:
        if not j[1].exists():
            atomic_json(j[1], judge_absolute(j[0], cases[j[0]["paper_id"]]))

    return D._parallel(jobs, job, workers, "rejudge")


_SCORES: dict[tuple[str, str], dict[str, float]] = {}


def scores(method: str, judge: str) -> dict[str, float]:
    """Per-paper reconstruction. GPT-5.6 scores of the baselines come from their same-session judgments; DeepSeek did
    not drift (loop.md 20.2), so its original judgments are used."""
    if (method, judge) not in _SCORES:
        if judge == "gpt" and method in BASELINES:
            data: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
            for path in (AG / "same_session" / method).glob("PMC*.json"):
                paper, level = path.name.split("__")[:2]
                data[paper][level].append(R.recon(_read_json(path)["scores"]))
            _SCORES[(method, judge)] = A.per_paper(data)
        else:
            _SCORES[(method, judge)] = W.per_paper(root_of(method), method, judge)
    return _SCORES[(method, judge)]


def family(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    out: dict[str, Any] = {j: V.holm_family([{"config": a, "vs": b, **A.paired(scores(a, j), scores(b, j))}
                                             for a, b in pairs]) for j in JUDGES}
    out["decision"] = {f"{g['config']} vs {g['vs']}": verdict(g, d) for g, d in zip(out["gpt"], out["deep"])}
    return out


def verdict(g: dict[str, Any], d: dict[str, Any]) -> str:
    if not g.get("papers"):
        return "no data"
    if g["ci95"][0] > 0 and d.get("diff", 0) > 0:
        return "better"
    if g["ci95"][1] < 0 and d.get("diff", 0) < 0:
        return "worse"
    return "no detectable difference"


def factorial() -> dict[str, Any]:
    """Q2: main effects of choosing the approach from the evidence and of focused writing evidence, and their
    interaction, per paper over the 2 x 2 (the writer is the model-choice, no-evidence cell)."""
    cells = {("model", "none"): WRITER, ("model", "focused"): DRAFT, ("evidence", "none"): ONLY,
             ("evidence", "focused"): AGENT}
    out: dict[str, Any] = {}
    for j in JUDGES:
        s = {k: scores(m, j) for k, m in cells.items()}
        papers = sorted(set.intersection(*(set(v) for v in s.values())))
        choice = {p: (s[("evidence", "none")][p] + s[("evidence", "focused")][p]
                      - s[("model", "none")][p] - s[("model", "focused")][p]) / 2 for p in papers}
        ground = {p: (s[("model", "focused")][p] + s[("evidence", "focused")][p]
                      - s[("model", "none")][p] - s[("evidence", "none")][p]) / 2 for p in papers}
        inter = {p: (s[("evidence", "focused")][p] - s[("evidence", "none")][p]
                     - s[("model", "focused")][p] + s[("model", "none")][p]) for p in papers}
        zero = {p: 0.0 for p in papers}
        out[j] = V.holm_family([{"config": "choose the approach from the evidence", **A.paired(choice, zero)},
                                {"config": "focused writing evidence", **A.paired(ground, zero)},
                                {"config": "interaction", **A.paired(inter, zero)}])
        out[f"cell_means_{j}"] = {f"{a} choice, {b} evidence": W.A_mean([s[(a, b)][p] for p in papers])
                                  for (a, b) in cells}
    return out


# ---------------------------------------------------------------- target-free quality (must_obey.md 6.11)

def pairwise_stage(workers: int, judges: tuple[str, ...]) -> dict[str, Any]:
    jobs = []
    for comparison, (base, new) in COMPARISONS.items():
        base_runs = {D.key_of(r): r for r in runs_of(base)}
        for r in runs_of(new):
            k = D.key_of(r)
            if k not in base_runs:
                continue
            for judge in judges:
                for order in ("baseline_first", "agent_first"):
                    path = AG / "pairwise" / comparison / judge / f"{k[0]}__{k[1]}__s{k[2]}__{order}.json"
                    if not path.exists():
                        jobs.append((comparison, judge, order, base_runs[k], r, path))
    if os.environ.get("MATHG_PENDING_SHUFFLE"):
        random.Random(int(os.environ["MATHG_PENDING_SHUFFLE"])).shuffle(jobs)

    def job(j: tuple[Any, ...]) -> None:
        comparison, judge, order, base, new, path = j
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
        agent_side = "B" if order == "baseline_first" else "A"
        atomic_json(path, {"comparison": comparison, "judge": judge, "order": order, "winner": winner,
                           "agent_won": winner == agent_side, "baseline_won": winner not in (agent_side, "TIE"),
                           "confidence": raw.get("confidence"), "reason": str(raw.get("reason", ""))[:600],
                           "baseline_run": base["run_id"], "agent_run": new["run_id"]})

    return D._parallel(jobs, job, workers, "pairwise")


def pairwise_results() -> dict[str, Any]:
    out: dict[str, Any] = {}
    items = []
    for comparison in COMPARISONS:
        out[comparison] = {}
        for judge in D.PAIR_JUDGES:
            by_pair: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
            for path in sorted((AG / "pairwise" / comparison / judge).glob("*.json")):
                stem, order = path.stem.rsplit("__", 1)
                by_pair[stem][order] = _read_json(path)
            per_paper: dict[str, list[float]] = defaultdict(list)
            first = []
            for stem, orders in by_pair.items():
                if len(orders) < 2:
                    continue
                won = all(o["agent_won"] for o in orders.values())
                lost = all(o["baseline_won"] for o in orders.values())
                per_paper[stem.split("__")[0]].append(1.0 if won else -1.0 if lost else 0.0)
                first += [o["winner"] == "A" for o in orders.values()]
            if not per_paper:
                out[comparison][judge] = {"pairs": 0}
                continue
            vals = [v for vs in per_paper.values() for v in vs]
            paired = A.paired({p: statistics.fmean(v) for p, v in per_paper.items()}, {p: 0.0 for p in per_paper})
            out[comparison][judge] = {"pairs": len(vals), "agent_wins": D.share([v == 1.0 for v in vals]),
                                      "baseline_wins": D.share([v == -1.0 for v in vals]),
                                      "tie_or_inconsistent": D.share([v == 0.0 for v in vals]),
                                      "first_position_wins": D.share(first), "net_preference_for_agent": paired}
            items.append({"config": f"{comparison}:{judge}", **paired})
    for item in V.holm_family(items):
        comparison, judge = item["config"].split(":")
        out[comparison][judge]["net_preference_for_agent"]["holm_p"] = item["holm_p"]
    return out


# ---------------------------------------------------------------- mechanism, profiles, leakage

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
    judged = {j: [] for j in JUDGES}
    audits = []
    for r in runs:
        for j, folder in (("gpt", "gpt56"), ("deep", "deepseek")):
            path = root / method / "judgments" / folder / f"{r['run_id']}.json"
            if path.exists():
                judged[j].append(_read_json(path))
        path = root / method / "audit" / f"{r['run_id']}.json"
        if path.exists():
            audits.append(_read_json(path))
    labs = labels_of(method)
    out: dict[str, Any] = {
        "runs": len(runs), "papers": len(scores(method, "gpt")),
        "gpt": W.A_mean(list(scores(method, "gpt").values())), "deep": W.A_mean(list(scores(method, "deep").values())),
        "lever_ge2": D.share([lb["lever_match"] >= 2 for lb in labs.values()]),
        "class_hit": D.share([lb["intervention_class"] == targets.get(k[:2]) for k, lb in labs.items()
                              if targets.get(k[:2])]),
        "unsupported_gpt": D.share([x.get("classification") == "unsupported" for x in judged["gpt"]]),
        "complete_chain": W.A_mean([float(all(v == 2 for v in a.get("chain", {}).values())) for a in audits]),
        "specificity": W.A_mean([statistics.fmean(1.0 if v else 0.0 for v in a["specificity"].values())
                                 for a in audits if a.get("specificity")]),
        "audited": len(audits),
        "llm_calls": W.A_mean([r["llm_calls"] for r in runs]), "chars_in": W.A_mean([r["chars_in"] for r in runs]),
        "seconds": W.A_mean([r["elapsed_seconds"] for r in runs])}
    for j in JUDGES:
        out[f"dims_{j}"] = {d: W.A_mean([x["scores"][d] for x in judged[j]]) for d in H.ALL_DIMENSIONS}
    return out


def chooser_stats(method: str) -> dict[str, Any]:
    runs = runs_of(method)
    choices = [r["notes"].get("choice") or {} for r in runs]
    chosen = [c["chosen"] for c in choices if c.get("chosen")]
    packs = [r["notes"].get("focused_pack") for r in runs if r["notes"].get("focused_pack")]
    return {"runs": len(runs), "fallbacks": sum(1 for r in runs if r["notes"].get("fallback")),
            "groups_per_run": W.A_mean([c.get("groups", 0) for c in choices if c]),
            "chosen_addresses": dict(sorted(Counter(c["addresses"] for c in chosen).items())),
            "chosen_papers": W.A_mean([c["papers"] for c in chosen]),
            "chosen_passages": W.A_mean([c["passages"] for c in chosen]),
            "focused_pack_records": W.A_mean([p["records"] for p in packs]),
            "focused_pack_from_group": W.A_mean([p["from_chosen_group"] for p in packs]),
            "same_choice_both_samples": same_choice(runs)}


def same_choice(runs: list[dict[str, Any]]) -> float | None:
    by_unit: dict[tuple[str, str], list[str]] = defaultdict(list)
    for r in runs:
        c = (r["notes"].get("choice") or {}).get("chosen")
        if c:
            by_unit[(r["paper_id"], r["query_level"])].append(c["approach"].lower())
    pairs = [v for v in by_unit.values() if len(v) == 2]
    return D.share([a == b for a, b in pairs]) if pairs else None


def leakage() -> dict[str, Any]:
    cases = H.cases()
    evidence = W.Evidence()
    violations, checked, unresolved = [], 0, 0
    for method in LM.AGENT_CONFIGS:
        for run in W.runs(AG, method):
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
    return {"counters": W.counters(AG), "web_records_rechecked": checked, "unresolved": unresolved,
            "date_violations": len(violations), "examples": violations[:10]}


def report() -> dict[str, Any]:
    targets = R.unit_targets(R.judged_runs())
    r: dict[str, Any] = {
        "Q1_agent_vs_baselines": family([(AGENT, WRITER), (AGENT, Q64)]),
        "Q2_factorial": factorial(),
        "Q3_chooser": {m: chooser_stats(m) for m in (AGENT, ONLY)},
        "Q4_quality": pairwise_results(),
        "profiles": {m: profile(m, targets) for m in (WRITER, Q64) + LM.AGENT_CONFIGS + (T16,)},
        "same_session_baselines": {m: {"original_gpt": W.A_mean(list(W.per_paper(root_of(m), m, "gpt").values())),
                                       "same_session_gpt": W.A_mean(list(scores(m, "gpt").values())),
                                       "rejudged_runs": len(list((AG / "same_session" / m).glob("*.json")))}
                                   for m in BASELINES},
        "leakage": leakage(),
    }
    g = r["Q1_agent_vs_baselines"]["gpt"][0]
    d = r["Q1_agent_vs_baselines"]["deep"][0]
    quality_against = any(((r["Q4_quality"]["agent_vs_writer"].get(j) or {}).get("net_preference_for_agent") or {})
                          .get("ci95", [0, 0])[1] < 0 for j in D.PAIR_JUDGES)
    better = verdict(g, d) == "better" and not quality_against
    r["decision"] = ("the agent performs better than the writer (pre-registered rule)" if better else
                     "the pre-registered rule is not met")
    return r


# ---------------------------------------------------------------- markdown

def _cell(i: dict[str, Any] | None) -> str:
    return D._cell(i)


def render(r: dict[str, Any]) -> str:
    L = ["# Experiment 40: an agent that chooses its approach from the evidence", "",
         "Pre-registered in loop.md 21.1. GPT-5.6 baselines are judged again in the same session (must_obey.md 6.10).",
         "", f"**Decision:** {r['decision']}.", "", "## Q1 (primary): the agent vs the baselines", "",
         "| comparison | GPT-5.6 [CI] | DeepSeek [CI] | decision |", "|---|---|---|---|"]
    q1 = r["Q1_agent_vs_baselines"]
    for g, d in zip(q1["gpt"], q1["deep"]):
        L.append(f"| {g['config']} vs {g['vs']} | {_cell(g)} | {_cell(d)} | {q1['decision'][g['config'] + ' vs ' + g['vs']]} |")
    L += ["", "## Q2: the 2 × 2 (approach chosen by the model or from the evidence × focused writing evidence)", "",
          "| effect | GPT-5.6 [CI] | DeepSeek [CI] |", "|---|---|---|"]
    q2 = r["Q2_factorial"]
    for g, d in zip(q2["gpt"], q2["deep"]):
        L.append(f"| {g['config']} | {_cell(g)} | {_cell(d)} |")
    L += ["", f"Cell means, GPT-5.6: {json.dumps(q2['cell_means_gpt'])}",
          f"Cell means, DeepSeek: {json.dumps(q2['cell_means_deep'])}", "", "## Q3: the chooser", ""]
    for m, s in r["Q3_chooser"].items():
        L.append(f"- `{m}`: {json.dumps(s)}")
    L += ["", "## Q4: target-free quality (pairwise, both orders; +1 when the agent wins both orders)", "",
          "| comparison | judge | pairs | agent wins | baseline wins | tie or inconsistent | first position wins | "
          "net preference for the agent [CI] |", "|---|---|---:|---:|---:|---:|---:|---|"]
    for comparison, by_judge in r["Q4_quality"].items():
        for judge, v in by_judge.items():
            if not v.get("pairs"):
                L.append(f"| {comparison} | {judge} | 0 | | | | | |")
                continue
            L.append(f"| {comparison} | {judge} | {v['pairs']} | {v['agent_wins']} | {v['baseline_wins']} | "
                     f"{v['tie_or_inconsistent']} | {v['first_position_wins']} | {_cell(v['net_preference_for_agent'])} |")
    L += ["", "## Profiles", "", "| configuration | runs | GPT-5.6 | DeepSeek | lever ≥ 2 | class hit | intervention | "
          "conditions | mechanism | outcome | novelty | unsupported | complete chain | specificity | calls | seconds |",
          "|---|" + "---:|" * 15]
    for m, p in r["profiles"].items():
        dg = p["dims_gpt"]
        L.append(f"| {m} | {p['runs']} | {p['gpt']} | {p['deep']} | {p['lever_ge2']} | {p['class_hit']} | "
                 f"{dg['intervention_reconstruction']} | {dg['condition_agreement']} | {dg['mechanism_agreement']} | "
                 f"{dg['outcome_agreement']} | {dg['novelty']} | {p['unsupported_gpt']} | {p['complete_chain']} | "
                 f"{p['specificity']} | {p['llm_calls']} | {p['seconds']} |")
    L += ["", "GPT-5.6 of the baselines in the profiles and Q1–Q2: same-session judgments. "
          f"{json.dumps(r['same_session_baselines'])}", "",
          "The oracle pack (`oracle_targetpack_b_o3mini`) is an upper reference from experiment 39, not a comparison.", ""]
    lk = r["leakage"]
    L += ["## Leakage", "", f"Counters over {lk['counters']['runs_checked']} runs: "
          f"{json.dumps(lk['counters']['totals'])}; web records re-checked: {lk['web_records_rechecked']}, date "
          f"violations: {lk['date_violations']}, unresolved: {lk['unresolved']}.", ""]
    return "\n".join(L)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("rejudge", "pairwise", "report"))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--judge", action="append", choices=D.PAIR_JUDGES)
    args = parser.parse_args()
    if args.stage == "report":
        r = report()
        atomic_json(AG / "analysis_agent.json", r)
        (AG / "analysis_agent.md").write_text(render(r))
        print(render(r))
        return
    if args.stage == "rejudge":
        print(rejudge_stage(args.workers))
    else:
        print(pairwise_stage(args.workers, tuple(args.judge or D.PAIR_JUDGES)))


if __name__ == "__main__":
    main()
