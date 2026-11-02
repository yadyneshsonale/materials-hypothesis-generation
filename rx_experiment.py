"""Experiment 44 (loop.md 25.1): runner and analysis for the focused-retrieval / evidence-use / refinement-loop arms.

Stages (resumable; all arms run in one process so that MATHG_MAX_PER_DEPLOYMENT caps every model's calls):
  python rx_experiment.py build [--workers N]          focused corpora (focused_search.build) for the 135 questions
  python rx_experiment.py screen_old [--workers N]     the same screener on the experiment-36 corpora (diagnostic)
  python rx_experiment.py generate [--arm A ...] [--workers N]
  python rx_experiment.py deepseek [--workers N]       DeepSeek reconstruction (hypo_loop cross_judge)
  python rx_experiment.py rq --rep R [--workers N]     research quality (rq_judge), DeepSeek, call R (1, 2, 3)
  python rx_experiment.py pairwise [--workers N]       DeepSeek target-free pairwise quality, both orders
  python rx_experiment.py packlabels [--workers N]     DeepSeek lever labels of the two packs (target-aware analysis)
  python rx_experiment.py report                       loop_rx/analysis_rx.json and analysis_rx.md
GPT-5.6 judging and audits use hypo_loop.py judge / audit with MATHG_LOOP_ROOT=loop_rx.
"""

from __future__ import annotations

import os

_E = os.path.join(os.path.dirname(os.path.abspath(__file__)), "experiments", "high_temperature_hea_qwen35b")
os.environ.setdefault("MATHG_CASES_DIR", os.path.join(_E, "benchmark_v3_1", "cases"))
os.environ.setdefault("MATHG_LOOP_ROOT", os.path.join(_E, "loop_rx"))

import argparse  # noqa: E402
import json  # noqa: E402
import statistics  # noqa: E402
from collections import Counter, defaultdict  # noqa: E402
from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

import diag_analysis as D  # noqa: E402
import focused_search as FS  # noqa: E402
import hypo_loop as H  # noqa: E402
import llm_client as lc  # noqa: E402
import loop_methods as LM  # noqa: E402
import refine_loop as RL  # noqa: E402
import round4_offline as R  # noqa: E402
import rq_judge as RQ  # noqa: E402
import web_analysis as W  # noqa: E402
import websearch as ws  # noqa: E402
from failure_clean import LABEL_SYSTEM  # noqa: E402,F401
from hypothesis_evidence_v2 import atomic_json  # noqa: E402
from stage_metrics import CROSS_JUDGE  # noqa: E402
from temporal_eval_v3 import _blind_candidate  # noqa: E402
from temporal_hypothesis_benchmark import _read_json  # noqa: E402

A, V = W.A, W.V
E = Path(_E)
OUT = H.OUT  # loop_rx unless MATHG_LOOP_ROOT says otherwise
ARMS = RL.RX_ARMS
BASE = "rx_base"
WRITER = "writer_only_b_o3mini"
RQ.ROOTS.update({arm: "loop_rx" for arm in ARMS})
CONTRASTS = (("rx_r", BASE), ("rx_u", BASE), ("rx_c", BASE), ("rx_ru", BASE), ("rx_ruc", BASE),
             ("rx_ruc", "rx_ru"), ("rx_ruc", "rx_ruc_select"))
PAIRWISE = (("rx_r", BASE), ("rx_u", BASE), ("rx_c", BASE), ("rx_ruc", BASE), ("rx_ruc", "rx_ruc_select"))
JUDGES = ("deep", "gpt")


def units() -> list[tuple[dict[str, Any], str]]:
    return H.units("all36") + H.units("test4")


# ---------------------------------------------------------------- generation

def generate(arms: list[str], workers: int) -> dict[str, int]:
    jobs = []
    for case, level in units():
        for sample in H.SAMPLES:
            for arm in arms:
                path = OUT / arm / "runs" / f"{H.run_id(case['paper_id'], level, arm, sample)}.json"
                if path.exists() and _read_json(path)["status"] == "ok":
                    continue
                if path.exists():
                    kept = OUT / arm / "failed_attempts" / path.name
                    kept.parent.mkdir(parents=True, exist_ok=True)
                    kept.write_text(path.read_text())
                jobs.append((arm, case, level, sample, False))
    counts: Counter[str] = Counter()
    with ThreadPoolExecutor(workers) as pool:
        futures = [pool.submit(H.generate_one, *job) for job in jobs]
        for future in as_completed(futures):
            future.result()
            counts["done"] += 1
    return {"jobs": len(jobs), **counts}


# ---------------------------------------------------------------- evaluation stages

def runs_of(method: str) -> list[dict[str, Any]]:
    root = OUT if method in ARMS else RQ.root_of(method)
    return [r for r in W.runs(root, method) if r.get("status") == "ok"]


def _parallel(jobs: list[Any], fn: Any, workers: int, tag: str) -> dict[str, int]:
    return D._parallel(jobs, fn, workers, tag)


def pairwise_stage(workers: int, judge: str = "deepseek", pairs: tuple[tuple[str, str], ...] = PAIRWISE
                   ) -> dict[str, int]:
    jobs = []
    for new, base in pairs:
        base_runs = {D.key_of(r): r for r in runs_of(base)}
        for r in runs_of(new):
            k = D.key_of(r)
            if k in base_runs:
                for order in ("baseline_first", "new_first"):
                    path = OUT / "pairwise" / f"{new}__vs__{base}" / judge / f"{k[0]}__{k[1]}__s{k[2]}__{order}.json"
                    if not path.exists():
                        jobs.append((judge, order, base_runs[k], r, path))

    def job(j: tuple[Any, ...]) -> None:
        judge_name, order, b, n, path = j
        if path.exists():
            return
        first, second = (b, n) if order == "baseline_first" else (n, b)
        ga, ea = _blind_candidate(first)
        gb, eb = _blind_candidate(second)
        user = json.dumps({"research_question": b["query"], "candidate_A": {"hypothesis": ga, "cited_evidence": ea},
                           "candidate_B": {"hypothesis": gb, "cited_evidence": eb}}, ensure_ascii=False)
        raw = D.pair_call(judge_name, user)
        raw = raw if isinstance(raw, dict) else {}
        winner = str(raw.get("winner", "tie")).strip().upper()
        winner = winner if winner in ("A", "B", "TIE") else "TIE"
        side = "B" if order == "baseline_first" else "A"
        H.write_once(path, {"judge": judge_name, "order": order, "winner": winner, "new_won": winner == side,
                            "baseline_won": winner not in (side, "TIE"), "reason": str(raw.get("reason", ""))[:600]})

    return _parallel(jobs, job, workers, "pairwise")


def r2_pack_for(case: dict[str, Any], level: str) -> list[Any]:
    h = H.Harness(case, level, 0)
    h.source = "web"
    return LM.r2_pack(h, RL.BUDGET)


def label_batch(case: dict[str, Any], records: list[Any]) -> dict[str, int]:
    """DeepSeek lever labels (D.ITEM_LABEL_SYSTEM, target-aware; analysis only), 24 passages per call."""
    out: dict[str, int] = {}
    for start in range(0, len(records), 24):
        batch = records[start:start + 24]
        items = [{"id": n + 1, "text": r.text[:1600]} for n, r in enumerate(batch)]
        raw = lc.trapi_chat_json(CROSS_JUDGE["deployment"], D.ITEM_LABEL_SYSTEM,
                                 json.dumps({"target": D.target_payload(case), "items": items}, ensure_ascii=False),
                                 max_tokens=6000, token_field=CROSS_JUDGE["token_field"],
                                 temperature=CROSS_JUDGE["temperature"], retries=8)
        labels = {}
        for item in (raw.get("items") if isinstance(raw, dict) else None) or []:
            try:
                labels[int(item.get("id"))] = max(0, min(3, int(item.get("lever_match"))))
            except (TypeError, ValueError, AttributeError):
                continue
        for n, record in enumerate(batch):
            out[record.record_id] = labels.get(n + 1)
    return out


def packlabels_stage(workers: int) -> dict[str, int]:
    jobs = []
    for case, level in units():
        for pack in ("focused", "r2"):
            path = OUT / "pack_labels" / pack / f"{case['paper_id']}__{level}.json"
            if not path.exists():
                jobs.append((case, level, pack, path))

    def job(j: tuple[Any, ...]) -> None:
        case, level, pack, path = j
        records = FS.pack_records(case["paper_id"], level) if pack == "focused" else r2_pack_for(case, level)
        labels = label_batch(case, records)
        H.write_once(path, {"pack": pack, "paper_id": case["paper_id"], "level": level, "labeller":
                            f"trapi:{CROSS_JUDGE['deployment']}", "items": [{"record_id": r.record_id,
                                                                             "lever_match": labels.get(r.record_id)}
                                                                            for r in records]})

    return _parallel(jobs, job, workers, "packlabels")


# ---------------------------------------------------------------- analysis

def _check_judge(judge: str) -> None:
    # web_analysis.load reads DeepSeek for any name other than "gpt", so a wrong name would silently swap judges.
    if judge not in JUDGES:
        raise ValueError(f"judge must be one of {JUDGES}, not {judge!r}")


def recon_scores(method: str, judge: str) -> dict[str, float]:
    _check_judge(judge)
    root = OUT if method in ARMS else RQ.root_of(method)
    return W.per_paper(root, method, judge)


def judged_count(method: str, judge: str) -> int:
    _check_judge(judge)
    root = OUT if method in ARMS else RQ.root_of(method)
    folder = "deepseek" if judge == "deep" else "gpt56"
    return len(list((root / method / "judgments" / folder).glob("*.json")))


def rq_scores(method: str, k: int) -> dict[str, float]:
    return RQ.per_paper(method, "deepseek", k)


def contrasts(score_fn: Any) -> list[dict[str, Any]]:
    items = []
    for new, base in CONTRASTS:
        a, b = score_fn(new), score_fn(base)
        if a and b:
            items.append({"config": new, "vs": base, **A.paired(a, b)})
    return V.holm_family(items)


def interaction(score_fn: Any) -> dict[str, Any]:
    """R x U on per-paper means: (ru - r) - (u - base)."""
    s = {arm: score_fn(arm) for arm in ("rx_base", "rx_r", "rx_u", "rx_ru")}
    papers = sorted(set.intersection(*(set(v) for v in s.values()))) if all(s.values()) else []
    if not papers:
        return {"papers": 0}
    diff = {p: (s["rx_ru"][p] - s["rx_r"][p]) - (s["rx_u"][p] - s["rx_base"][p]) for p in papers}
    return A.paired(diff, {p: 0.0 for p in papers})


def dims(method: str, folder: str) -> dict[str, float | None]:
    root = OUT if method in ARMS else RQ.root_of(method)
    judged = [_read_json(p)["scores"] for p in (root / method / "judgments" / folder).glob("*.json")]
    return {d: W.A_mean([s[d] for s in judged]) for d in ("intervention_reconstruction", "condition_agreement",
                                                          "mechanism_agreement", "outcome_agreement")}


def pairwise_results() -> dict[str, Any]:
    out = {}
    items = []
    for new, base in PAIRWISE:
        name = f"{new}__vs__{base}"
        by_pair: dict[str, dict[str, Any]] = defaultdict(dict)
        for path in sorted((OUT / "pairwise" / name / "deepseek").glob("*.json")):
            stem, order = path.stem.rsplit("__", 1)
            by_pair[stem][order] = _read_json(path)
        per_paper: dict[str, list[float]] = defaultdict(list)
        for stem, orders in by_pair.items():
            if len(orders) == 2:
                won = all(o["new_won"] for o in orders.values())
                lost = all(o["baseline_won"] for o in orders.values())
                per_paper[stem.split("__")[0]].append(1.0 if won else -1.0 if lost else 0.0)
        if not per_paper:
            out[name] = {"pairs": 0}
            continue
        vals = [v for vs in per_paper.values() for v in vs]
        paired = A.paired({p: statistics.fmean(v) for p, v in per_paper.items()}, {p: 0.0 for p in per_paper})
        out[name] = {"pairs": len(vals), "new_wins": D.share([v == 1 for v in vals]),
                     "base_wins": D.share([v == -1 for v in vals]), "net_preference_for_new": paired}
        items.append({"config": name, **paired})
    for item in V.holm_family(items):
        out[item["config"]]["net_preference_for_new"]["holm_p"] = item["holm_p"]
    return out


def pack_density() -> dict[str, Any]:
    out: dict[str, Any] = {}
    per_paper: dict[str, dict[str, float]] = {}
    for pack in ("focused", "r2"):
        dens, contains = [], []
        by: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        for path in sorted((OUT / "pack_labels" / pack).glob("*.json")):
            values = [i["lever_match"] for i in _read_json(path)["items"] if i["lever_match"] is not None]
            if values:
                share = statistics.fmean(v >= 2 for v in values)
                dens.append(share)
                contains.append(any(v >= 2 for v in values))
                paper, level = path.stem.split("__")[:2]
                by[paper][level].append(share)
        per_paper[pack] = A.per_paper(by)
        out[pack] = {"units": len(dens), "lever_passage_share": round(statistics.fmean(dens), 3) if dens else None,
                     "pack_contains_lever": D.share(contains)}
    if per_paper["focused"] and per_paper["r2"]:
        out["focused_minus_r2"] = A.paired(per_paper["focused"], per_paper["r2"])
    return out


def loop_diagnostics(arm: str) -> dict[str, Any]:
    runs = runs_of(arm)
    loops = [r["notes"].get("loop") for r in runs if r.get("notes", {}).get("loop")]
    if not loops:
        return {}
    first_kept = []
    critic_rho = []
    for lp in loops:
        first = lp["rounds"][0]
        first_kept.append(first["ranking"][0]["index"] == 0 and len(lp["rounds"]) == 1)
        for rnd in lp["rounds"]:
            means = {c: {k: statistics.fmean(v["scores"].values()) for k, v in by.items()}
                     for c, by in rnd["reviews"].items()}
            keys = sorted(set.intersection(*(set(m) for m in means.values()))) if means else []
            critics = sorted(means)
            for i in range(len(critics)):
                for j in range(i + 1, len(critics)):
                    if len(keys) >= 3:
                        rho = R.spearman([means[critics[i]][k] for k in keys], [means[critics[j]][k] for k in keys])
                        if rho is not None:
                            critic_rho.append((f"{critics[i]}~{critics[j]}", rho))
    by_pair: dict[str, list[float]] = defaultdict(list)
    for pair, rho in critic_rho:
        by_pair[pair].append(rho)
    return {"runs": len(loops), "stop": dict(Counter(lp["stop"] for lp in loops)),
            "critique_rounds": dict(Counter(lp["critique_rounds"] for lp in loops)),
            "final_fine": D.share([lp["final_fine"] for lp in loops]),
            "round1_first_candidate_selected_and_kept": D.share(first_kept),
            "critic_agreement_spearman": {k: round(statistics.fmean(v), 3) for k, v in sorted(by_pair.items())},
            "re_retrieval_added_records": W.A_mean([float(sum(len(x.get("added", [])) for x in
                                                              r["notes"].get("re_retrieval", []))) for r in runs])}


def arm_summary(arm: str) -> dict[str, Any]:
    runs = runs_of(arm)
    all_runs = W.runs(OUT, arm) if arm in ARMS else []
    return {"runs_ok": len(runs), "runs_failed": sum(r.get("status") != "ok" for r in all_runs),
            "deepseek_judged": judged_count(arm, "deep"), "gpt56_judged": judged_count(arm, "gpt"),
            "llm_calls": W.A_mean([float(r["llm_calls"]) for r in runs]),
            "chars_in": W.A_mean([float(r["chars_in"]) for r in runs]),
            "seconds": W.A_mean([float(r["elapsed_seconds"]) for r in runs]),
            "evidence_records_seen": W.A_mean([float(len(r["seen_ids"])) for r in runs])}


def leakage(arms: tuple[str, ...] | list[str] | None = None) -> dict[str, Any]:
    """The runs' leakage counters, and every seen web record's dates re-checked against its case (cached lookup)."""
    totals: Counter[str] = Counter()
    checked, violations = 0, 0
    evidence = W.Evidence()
    cutoffs: dict[str, str] = {}
    for arm in arms or ARMS:
        for run in W.runs(OUT, arm):
            for key, value in (run.get("audit") or {}).items():
                totals[key] += int(value or 0)
            cutoff = cutoffs.setdefault(run["paper_id"], ws.CaseFilter(run["paper_id"]).cutoff)
            for rid in run.get("seen_ids", []):
                record = evidence.web(rid)
                if record is None:
                    continue
                checked += 1
                dates = [d for d in (record.structured or {}).get("dates", {}).values() if d]
                if any(str(d) >= cutoff for d in dates + [record.publication_date]):
                    violations += 1
    return {"counters": dict(totals), "records_rechecked": checked, "date_violations": violations}


def report() -> dict[str, Any]:
    arms = list(ARMS)
    return {
        "arms": {a: arm_summary(a) for a in arms},
        "deepseek_recon_means": {a: W.A_mean(list(recon_scores(a, "deep").values())) for a in arms + [WRITER]},
        "gpt56_recon_means": {a: W.A_mean(list(recon_scores(a, "gpt").values())) for a in arms},
        "dims_deepseek": {a: dims(a, "deepseek") for a in arms},
        "contrasts_deepseek": contrasts(lambda m: recon_scores(m, "deep")),
        "contrasts_gpt56": contrasts(lambda m: recon_scores(m, "gpt")),
        "interaction_RxU_deepseek": interaction(lambda m: recon_scores(m, "deep")),
        "rq_means": {k: {a: W.A_mean(list(rq_scores(a, k).values())) for a in arms + [WRITER]} for k in (1, 3)},
        "contrasts_rq3": contrasts(lambda m: rq_scores(m, 3)),
        "pairwise_deepseek": pairwise_results(),
        "retrieval": {"screener": FS.stats(), "lever_density": pack_density()},
        "loops": {a: loop_diagnostics(a) for a in ("rx_c", "rx_ruc_select", "rx_ruc")},
        "leakage": leakage(),
    }


def _cell(x: dict[str, Any]) -> str:
    return D._cell(x) if x.get("papers") else "-"


def render(r: dict[str, Any]) -> str:
    L = ["# Experiment 44: focused retrieval, evidence use and a multi-critic refinement loop", "",
         "Pre-registered in loop.md 25.1. Interim decision judge: DeepSeek reconstruction (GPT-5.6 in the background);"
         " research quality (RQ, mean of three DeepSeek calls) and DeepSeek target-free pairwise quality alongside.",
         "", "## Arms", "", "| arm | runs ok | failed | DeepSeek judged | GPT-5.6 judged | DeepSeek recon | GPT-5.6 recon |"
         " RQ (3 calls) | calls | input chars | seconds |", "|---|" + "---:|" * 10]
    for a, s in r["arms"].items():
        L.append(f"| {a} | {s['runs_ok']} | {s['runs_failed']} | {s['deepseek_judged']} | {s['gpt56_judged']} | "
                 f"{r['deepseek_recon_means'][a]} | {r['gpt56_recon_means'][a]} | {r['rq_means'][3][a]} | "
                 f"{s['llm_calls']} | {s['chars_in']} | {s['seconds']} |")
    L += ["", f"Reference: {WRITER} DeepSeek {r['deepseek_recon_means'][WRITER]}, RQ {r['rq_means'][3][WRITER]}.", ""]
    for title, key in (("DeepSeek reconstruction (interim decision)", "contrasts_deepseek"),
                       ("GPT-5.6 reconstruction (as complete)", "contrasts_gpt56"),
                       ("Research quality (RQ, three DeepSeek calls)", "contrasts_rq3")):
        L += [f"## {title}", "", "| comparison | difference [CI] |", "|---|---|"]
        for it in r[key]:
            L.append(f"| {it['config']} vs {it['vs']} | {_cell(it)} |")
        L.append("")
    L += [f"R x U interaction (DeepSeek): {_cell(r['interaction_RxU_deepseek'])}", "",
          "## Pairwise quality without the answer key (DeepSeek, both orders)", ""]
    for name, v in r["pairwise_deepseek"].items():
        L.append(f"- {name}: pairs {v.get('pairs')}, new wins {v.get('new_wins')}, base wins {v.get('base_wins')}, "
                 f"net {_cell(v['net_preference_for_new']) if v.get('pairs') else '-'}")
    L += ["", "## DeepSeek dimensions", "", "| arm | intervention | conditions | mechanism | outcome |",
          "|---|---:|---:|---:|---:|"]
    for a, d in r["dims_deepseek"].items():
        L.append(f"| {a} | " + " | ".join(str(v) for v in d.values()) + " |")
    L += ["", "## Retrieval", "", f"Screener grades: {json.dumps(r['retrieval']['screener'])}", "",
          f"Lever density (DeepSeek labels; target-aware analysis only): {json.dumps(r['retrieval']['lever_density'])}",
          "", "## Loops", ""]
    for a, d in r["loops"].items():
        L.append(f"- {a}: {json.dumps(d)}")
    L += ["", "## Leakage", "", json.dumps(r["leakage"]), ""]
    return "\n".join(L)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("build", "screen_old", "generate", "deepseek", "rq", "pairwise",
                                          "packlabels", "report"))
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--arm", action="append")
    parser.add_argument("--rep", type=int, default=1)
    args = parser.parse_args()
    if args.stage == "build":
        print(FS.run_all(FS.build, args.workers, FS.units()))
    elif args.stage == "screen_old":
        print(FS.run_all(FS.screen_old, args.workers, FS.units()))
    elif args.stage == "generate":
        print(generate(args.arm or list(ARMS), args.workers))
    elif args.stage == "deepseek":
        print(H.cross_judge_stage(args.workers, list(ARMS)))
    elif args.stage == "rq":
        items = RQ.run_items(list(ARMS))
        if args.rep > 1:
            items = [(RQ.rep_kind(k, args.rep), n, i, d) for k, n, i, d in items]
        print(RQ.run_stage(items, "deepseek", args.workers))
    elif args.stage == "pairwise":
        print(pairwise_stage(args.workers))
    elif args.stage == "packlabels":
        print(packlabels_stage(args.workers))
    else:
        result = report()
        atomic_json(OUT / "analysis_rx.json", result)
        (OUT / "analysis_rx.md").write_text(render(result))
        print(render(result))


if __name__ == "__main__":
    main()
