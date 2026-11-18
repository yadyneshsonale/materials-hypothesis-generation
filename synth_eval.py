"""Experiment 48 (loop.md 27.7): evaluate the synthesis writers against the focused-retrieval writer rx_r.

Stages (resumable; at most 6 workers per model):
  python synth_eval.py generate [--arm A] [--workers N] synth_a, synth_b: 135 questions x 2 samples
  python synth_eval.py noncopy                          non-copying (noncopy_eval), DeepSeek
  python synth_eval.py rq --rep R                       research quality (rq_judge), DeepSeek, call R (1, 2, 3)
  python synth_eval.py pairwise --judge J --prompt P    each arm vs rx_r, both orders; P = v1 (experiment 46) or v2
  python synth_eval.py report                           loop_quality/analysis_synth.{json,md}
"""

from __future__ import annotations

import rx_experiment as X  # noqa: I001 - first: it points MATHG_LOOP_ROOT at loop_rx before hypo_loop loads

import argparse  # noqa: E402
from collections import Counter  # noqa: E402
from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: E402
from typing import Any  # noqa: E402

import diag_analysis as D  # noqa: E402
import hypo_loop as H  # noqa: E402
import noncopy_eval as N  # noqa: E402
import quality_eval as Q  # noqa: E402
import rq_judge as RQ  # noqa: E402
import synth_loop as SL  # noqa: E402
from hypothesis_evidence_v2 import atomic_json  # noqa: E402
from temporal_hypothesis_benchmark import _read_json  # noqa: E402

A = Q.A
ARMS = SL.SYNTH_ARMS
DRAFT = "agent_draft_ground_b_o3mini"  # evaluation-only addition (loop.md 27.7, 01:37): existing runs
BASE = "rx_r"
PROMPTS = {"v1": (D.QUALITY_PAIR_SYSTEM, Q.PAIR_DIR), "v2": (N.PAIR_SYSTEM_V2, N.PAIR_DIR)}
OUT = Q.OUT


def generate(workers: int, arms: list[str] | None = None) -> dict[str, int]:
    jobs = []
    for case, level in X.units():
        for sample in H.SAMPLES:
            for arm in arms or ARMS:
                path = H.OUT / arm / "runs" / f"{H.run_id(case['paper_id'], level, arm, sample)}.json"
                if path.exists() and _read_json(path)["status"] == "ok":
                    continue
                if path.exists():
                    kept = H.OUT / arm / "failed_attempts" / path.name
                    kept.parent.mkdir(parents=True, exist_ok=True)
                    kept.write_text(path.read_text())
                jobs.append((arm, case, level, sample, False))
    counts: Counter[str] = Counter()
    with ThreadPoolExecutor(workers) as pool:
        for future in as_completed([pool.submit(H.generate_one, *j) for j in jobs]):
            future.result()
            counts["done"] += 1
    return {"jobs": len(jobs), **counts}


def nc(method: str) -> dict[tuple[str, str, int], float]:
    return {k: float(x["non_copying"]) for k, x in N.load(method).items()}


def rq(method: str) -> dict[tuple[str, str, int], float]:
    return {k: x["rq"] for k, x in Q.rq_values(method).items()}


def scale(method: str, name: str) -> dict[tuple[str, str, int], float]:
    return {k: float(x["scores"][name]) for k, x in Q.rq_values(method).items()}


def vs(fn: Any, arm: str, base: str = BASE) -> dict[str, Any]:
    a, b = fn(arm), fn(base)
    if not a or not b:
        return {"papers": 0}
    return A.paired(Q.per_paper(a), Q.per_paper(b))


def arm_row(arm: str) -> dict[str, Any]:
    runs = RQ.runs_of(arm)
    every = list((RQ.root_of(arm) / arm / "runs").glob("PMC*.json"))
    n = N.load(arm)
    return {"runs_ok": len(runs), "runs_failed": len(every) - len(runs),
            "calls": round(sum(r["llm_calls"] for r in runs) / len(runs), 2) if runs else None,
            "words": round(sum(RQ.words(r["generation"]) for r in runs) / len(runs), 1) if runs else None,
            "papers_cited": round(sum(len({c.split("::")[0] for c in r["cited_ids"]}) for r in runs) / len(runs), 2)
            if runs else None,
            "non_copying": Q.mean_of(Q.per_paper(nc(arm))), "nc_judged": len(n),
            "nc_distribution": dict(sorted(Counter(int(x["non_copying"]) for x in n.values()).items())),
            "rq": Q.mean_of(Q.per_paper(rq(arm))), "rq_judged": len(Q.rq_values(arm)),
            "scales": {s: Q.mean_of(Q.per_paper(scale(arm, s))) for s in Q.SCALES},
            "sp2": Q.mean_of(Q.per_paper(N.sp2_values(arm)))}


def report() -> dict[str, Any]:
    rows = {m: arm_row(m) for m in (*ARMS, DRAFT, BASE, Q.WRITER)}
    contrasts = {}
    for arm in (*ARMS, DRAFT):
        contrasts[arm] = {"non_copying": vs(nc, arm), "rq": vs(rq, arm), "sp2": vs(N.sp2_values, arm),
                          **{f"scale_{s}": vs(lambda m, s=s: scale(m, s), arm) for s in Q.SCALES},
                          "non_copying_vs_writer": vs(nc, arm, Q.WRITER)}
        for name, (_, root) in PROMPTS.items():
            for judge in ("deepseek", "gpt56"):
                contrasts[arm][f"pairwise_{name}_{judge}"] = Q.pair_result(arm, BASE, judge, root)
    for key in ("non_copying", "rq"):
        items = [{"config": a, **contrasts[a][key]} for a in ARMS if contrasts[a][key].get("papers")]
        for item in Q.V.holm_family(items):
            contrasts[item["config"]][key]["holm_p"] = item["holm_p"]
    decisions = {}
    for arm in (*ARMS, DRAFT):
        c = contrasts[arm]
        nc_up = c["non_copying"].get("papers") and c["non_copying"]["ci95"][0] > 0
        rq_ok = not (c["rq"].get("papers") and c["rq"]["ci95"][1] < 0)
        pw = c["pairwise_v2_deepseek"]
        pw_ok = not (pw.get("papers") and pw["ci95"][1] < 0)
        decisions[arm] = ("improves on rx_r" if nc_up and rq_ok and pw_ok else
                          "more original, but worse on quality" if nc_up else "no improvement")
    return {"rows": rows, "contrasts": contrasts, "decisions": decisions,
            "leakage": X.leakage(ARMS), "metric_note": "non-copying is unvalidated (loop.md 27.5)"}


def _c(x: dict[str, Any]) -> str:
    if not x or not x.get("papers"):
        return "–"
    holm = f", Holm {x['holm_p']}" if "holm_p" in x else ""
    return f"{x['diff']:+.2f} [{x['ci95'][0]:+.2f}, {x['ci95'][1]:+.2f}], {x['up']} vs {x['down']} papers{holm}"


def _f(x: Any) -> str:
    return "–" if x is None else f"{x:.2f}" if isinstance(x, float) else str(x)


def render(r: dict[str, Any]) -> str:
    L = ["# Experiment 48: writers that combine or extend several papers", "",
         "Pre-registered in loop.md 27.7. Same evidence pack as rx_r (focused retrieval); only the writer changes. "
         "Non-copying (1–5, unvalidated) and RQ (three DeepSeek calls); pairwise against rx_r in both orders.", "",
         "| Arm | Runs ok | Calls | Words | Papers cited | Non-copying | Scores 1/2/3/4/5 | RQ | Plaus. | Test. | Useful. "
         "| SP2 |", "|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|"]
    for m, x in r["rows"].items():
        d = x["nc_distribution"]
        s = x["scales"]
        L.append(f"| `{m}` | {x['runs_ok']} | {_f(x['calls'])} | {_f(x['words'])} | {_f(x['papers_cited'])} | "
                 f"{_f(x['non_copying'])} | {'/'.join(str(d.get(k, 0)) for k in range(1, 6))} | {_f(x['rq'])} | "
                 f"{_f(s['plausibility'])} | {_f(s['testability'])} | {_f(s['usefulness'])} | {_f(x['sp2'])} |")
    L += ["", "## Against rx_r (paired by paper)", ""]
    for arm, c in r["contrasts"].items():
        extra = " (evaluation-only addition; outside the Holm family)" if arm == DRAFT else ""
        L += [f"**`{arm}`: {r['decisions'][arm]}**{extra}", "",
              f"- Non-copying: {_c(c['non_copying'])} (vs the closed-book writer: {_c(c['non_copying_vs_writer'])})",
              f"- RQ: {_c(c['rq'])}; plausibility {_c(c['scale_plausibility'])}; testability "
              f"{_c(c['scale_testability'])}; usefulness {_c(c['scale_usefulness'])}",
              f"- SP2: {_c(c['sp2'])}",
              f"- Pairwise v2 (goes beyond the earlier work): DeepSeek {_c(c['pairwise_v2_deepseek'])}; GPT-5.6 "
              f"{_c(c['pairwise_v2_gpt56'])}",
              f"- Pairwise v1 (experiment-46 prompt): DeepSeek {_c(c['pairwise_v1_deepseek'])}", ""]
    L += ["## Leakage", "", str(r["leakage"]), ""]
    return "\n".join(L)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("generate", "noncopy", "rq", "pairwise", "report"))
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--rep", type=int, default=1)
    parser.add_argument("--judge", default="deepseek", choices=("deepseek", "gpt56"))
    parser.add_argument("--prompt", default="v2", choices=tuple(PROMPTS))
    parser.add_argument("--arm", action="append", choices=ARMS)
    args = parser.parse_args()
    if args.stage == "generate":
        print(generate(args.workers, args.arm))
    elif args.stage == "noncopy":
        print(N.noncopy_stage(list(ARMS), "deepseek", args.workers))
    elif args.stage == "rq":
        items = RQ.run_items(list(ARMS))
        if args.rep > 1:
            items = [(RQ.rep_kind(k, args.rep), n, i, d) for k, n, i, d in items]
        print(RQ.run_stage(items, "deepseek", args.workers))
    elif args.stage == "pairwise":
        system, root = PROMPTS[args.prompt]
        print(Q.pairwise_stage(list(ARMS), args.judge, args.workers, BASE, system, root))
    else:
        result = report()
        atomic_json(OUT / "analysis_synth.json", result)
        (OUT / "analysis_synth.md").write_text(render(result))
        print(render(result))


if __name__ == "__main__":
    main()
