"""Experiment 49 (loop.md 28.1): pilot of the per-paper generate -> critique -> narrow method on the 8 dev papers.

Stages (resumable; at most 6 workers per model per TRAPI instance, enforced in-process by MATHG_MAX_PER_DEPLOYMENT):
  python perpaper_eval.py generate [--workers N]          perpaper: 8 dev papers x 3 levels x 2 samples = 48 runs
  python perpaper_eval.py rq --rep R [--workers N]        research quality (rq_judge), DeepSeek, call R (1, 2, 3)
  python perpaper_eval.py noncopy [--workers N]           non-copying (noncopy_eval, the shared focused passages)
  python perpaper_eval.py noncopy_source [--workers N]    diagnostic: the same judge shown the source paper's text
  python perpaper_eval.py pairwise --judge J --base B     pairwise v2 vs B (writer or draft), both orders
  python perpaper_eval.py report                          loop_quality/analysis_perpaper.{json,md}
"""

from __future__ import annotations

import rx_experiment as X  # noqa: I001 - first: it points MATHG_LOOP_ROOT at loop_rx before hypo_loop loads

import argparse  # noqa: E402
import statistics  # noqa: E402
from collections import Counter  # noqa: E402
from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: E402
from typing import Any  # noqa: E402

import hypo_loop as H  # noqa: E402
import loop_methods as LM  # noqa: E402
import noncopy_eval as N  # noqa: E402
import perpaper_loop as PP  # noqa: E402
import quality_eval as Q  # noqa: E402
import rq_judge as RQ  # noqa: E402
import rubric_eval as rx  # noqa: E402
from hypothesis_evidence_v2 import atomic_json  # noqa: E402
from temporal_hypothesis_benchmark import _read_json  # noqa: E402

A = Q.A
ARM = "perpaper"
DRAFT = "agent_draft_ground_b_o3mini"
WRITER = Q.WRITER
BASES = {"writer": WRITER, "draft": DRAFT}
OUT = Q.OUT
SOURCE_DIR = N.NONCOPY_DIR.parent / "noncopy_source"


def units() -> list[tuple[dict[str, Any], str]]:
    return H.units("dev")


def generate(workers: int, part: int = 0, parts: int = 1, arm: str = ARM, scope: str = "dev",
             samples: tuple[int, ...] = tuple(H.SAMPLES)) -> dict[str, int]:
    """This process's share of the runs (every parts-th unit, from part), so two processes can use both instances.
    scope "all45" = every benchmark paper (loop.md 28.3)."""
    jobs = []
    chosen = X.units() if scope == "all45" else units()
    for n, (case, level, sample) in enumerate((c, l, s) for c, l in chosen for s in samples):
        if n % parts != part:
            continue
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


def dev_runs(method: str) -> list[dict[str, Any]]:
    papers = {c["paper_id"] for c, _ in units()}
    return [r for r in RQ.runs_of(method) if r["paper_id"] in papers]


# ---------------------------------------------------------------- the source-paper copying diagnostic

def source_view(run: dict[str, Any]) -> dict[str, Any]:
    """noncopy_eval.view, but the passages are the text of the paper the rank-1 hypothesis was derived from."""
    paper_id = run["notes"]["top3"][0]["paper"]
    manifest = PP.FS.build(run["paper_id"], run["query_level"])
    paper = next(p for p in manifest["papers"] if p["pmcid"] == paper_id)
    records = PP.paper_text(paper)
    labels = {r.record_id: f"P{n + 1}" for n, r in enumerate(records)}
    generation = {k: v for k, v in run["generation"].items() if k != "citation_validation"}
    for field in ("supporting_evidence_ids", "conflicting_evidence_ids"):
        generation[field] = [labels[i] for i in generation.get(field, []) if i in labels]
    cap = rx.record_cap("text_chunks")
    passages = []
    for r in records:
        item = LM.v2_item(r, cap)
        passages.append({"id": labels[r.record_id], "paper_title": item["paper_title"], "section": item["section"],
                         "publication_date": item["publication_date"], "text": item["evidence"]})
    return {"query": run["query"], "generation": generation, "passages": passages}


def noncopy_source_stage(workers: int) -> dict[str, int]:
    jobs = [(SOURCE_DIR / ARM / "deepseek" / f"{r['run_id']}.json", r) for r in dev_runs(ARM)]
    jobs = [j for j in jobs if not j[0].exists()]

    def job(j: tuple[Any, dict[str, Any]]) -> None:
        path, run = j
        if not path.exists():
            H.write_once(path, {"run_id": run["run_id"], "source_paper": run["notes"]["top3"][0]["paper"],
                                **N.judge("deepseek", source_view(run))})

    return Q._run(jobs, job, workers, "noncopy-source")


# ---------------------------------------------------------------- report

def _per(method: str, fn: Any) -> dict[tuple[str, str, int], float]:
    papers = {c["paper_id"] for c, _ in units()}
    return {k: v for k, v in fn(method).items() if k[0] in papers}


def rq(method: str) -> dict[tuple[str, str, int], float]:
    return {k: x["rq"] for k, x in Q.rq_values(method).items()}


def scale(name: str) -> Any:
    return lambda method: {k: float(x["scores"][name]) for k, x in Q.rq_values(method).items()}


def nc(method: str) -> dict[tuple[str, str, int], float]:
    return {k: float(x["non_copying"]) for k, x in N.load(method).items()}


def vs(fn: Any, a: str, b: str) -> dict[str, Any]:
    x, y = _per(a, fn), _per(b, fn)
    keys = x.keys() & y.keys()
    if not keys:
        return {"papers": 0}
    return A.paired(Q.per_paper({k: x[k] for k in keys}), Q.per_paper({k: y[k] for k in keys}))


def mean(method: str, fn: Any) -> float | None:
    values = _per(method, fn)
    return Q.mean_of(Q.per_paper(values)) if values else None


def pair(base: str, judge: str) -> dict[str, Any]:
    outcomes = {k: v for k, v in Q.pair_outcomes(ARM, base, judge, N.PAIR_DIR).items()}
    if not outcomes:
        return {"pairs": 0}
    pp = Q.per_paper(outcomes)
    values = list(outcomes.values())
    return {"pairs": len(values), "new_wins": round(sum(v == 1 for v in values) / len(values), 3),
            "base_wins": round(sum(v == -1 for v in values) / len(values), 3), **A.paired(pp, {p: 0.0 for p in pp})}


def diagnostics() -> dict[str, Any]:
    runs = dev_runs(ARM)
    every = list((H.OUT / ARM / "runs").glob("PMC*.json"))
    papers = [p for r in runs for p in r["notes"]["papers"]]
    rounds = [p["n_rounds"] for p in papers if p.get("n_rounds")]
    verdicts = [v for p in papers for rd in p.get("rounds", []) for v in rd.get("verdicts", [])]
    first = [v for p in papers for rd in p.get("rounds", [])[:1] for v in rd.get("verdicts", [])]
    sources = Counter(r["notes"]["top3"][0]["paper"] for r in runs)
    return {
        "runs_ok": len(runs), "runs_failed": len(every) - len(runs),
        "calls_mean": round(statistics.fmean(r["llm_calls"] for r in runs), 1) if runs else None,
        "calls_max": max((r["llm_calls"] for r in runs), default=None),
        "minutes_mean": round(statistics.fmean(r["elapsed_seconds"] for r in runs) / 60, 1) if runs else None,
        "papers_per_run": round(statistics.fmean(len(r["notes"]["papers"]) for r in runs), 2) if runs else None,
        "papers_with_accepted": round(statistics.fmean(r["notes"]["summary"]["papers_with_accepted"] for r in runs),
                                      2) if runs else None,
        "papers_dropped_share": round(sum(not p.get("n_accepted") for p in papers) / max(1, len(papers)), 3),
        "paper_errors": sum(bool(p.get("error")) for p in papers),
        "pool_after_dedupe_mean": round(statistics.fmean(r["notes"]["summary"]["pool_after_dedupe"] for r in runs),
                                        1) if runs else None,
        "rounds_to_accept": dict(sorted(Counter(p["n_rounds"] for p in papers if p.get("n_accepted")).items())),
        "rounds_mean": round(statistics.fmean(rounds), 2) if rounds else None,
        "accepted_in_round_1_share": round(sum(bool(p.get("n_accepted")) and p["n_rounds"] == 1 for p in papers)
                                           / max(1, len(papers)), 3),
        "criterion_pass_rate_round_1": {c: round(sum(v[c] for v in first) / max(1, len(first)), 3)
                                        for c in PP.CRITERIA},
        "criterion_pass_rate_all_rounds": {c: round(sum(v[c] for v in verdicts) / max(1, len(verdicts)), 3)
                                           for c in PP.CRITERIA},
        "rank1_source_paper_grade": dict(Counter(
            next((p.get("grade") for p in r["notes"]["papers"] if p["paper"] == r["notes"]["top3"][0]["paper"]),
                 None) for r in runs)),
        "distinct_rank1_sources": len(sources),
        "rank1_tied_share": round(sum(bool(r["notes"]["tournament"].get("rank1_tied")) for r in runs)
                                  / max(1, len(runs)), 3),
        "tournament_formats": dict(Counter(r["notes"]["tournament"]["format"] for r in runs)),
        "rubber_stamp_flag": None,  # filled below
    }


def background_leakage() -> dict[str, int]:
    """Teaching-text passages and graph facts each run saw, re-checked: no HEA mention (loop.md 28.1), no date at
    or after the case's cutoff."""
    texts = {r["record_id"]: r for r in PP.MT.load()}
    out = Counter()
    for run in dev_runs(ARM):
        for rid in run["seen_ids"]:
            if rid.startswith("TXT::"):
                r = texts.get(rid)
                out["text_passages_seen"] += 1
                out["text_unknown_ids"] += r is None
                if r is not None:
                    out["text_hea_mentions"] += bool(PP.MT.HEA.search(r["text"]))
                    out["text_undated"] += not r.get("date")
                    out["text_date_violations"] += bool(r.get("date")) and str(r["date"]) >= run["publication_date"]
            elif rid.startswith("KG::"):
                out["kg_facts_seen"] += 1
    return dict(out)


def paper_leakage() -> dict[str, Any]:
    """rx_experiment.leakage for this arm's paper passages only: teaching-text and graph IDs are not Europe PMC records
    (they are re-checked by background_leakage)."""
    totals: Counter[str] = Counter()
    checked = violations = 0
    evidence = X.W.Evidence()
    for run in dev_runs(ARM):
        for key, value in (run.get("audit") or {}).items():
            totals[key] += int(value or 0)
        cutoff = X.ws.CaseFilter(run["paper_id"]).cutoff
        for rid in run["seen_ids"]:
            if rid.startswith(("TXT::", "KG::")):
                continue
            record = evidence.web(rid)
            if record is None:
                continue
            checked += 1
            dates = [d for d in (record.structured or {}).get("dates", {}).values() if d]
            violations += any(str(d) >= cutoff for d in dates + [record.publication_date])
    return {"counters": dict(totals), "records_rechecked": checked, "date_violations": violations}


def report() -> dict[str, Any]:
    d = diagnostics()
    d["rubber_stamp_flag"] = d["accepted_in_round_1_share"] > 0.8
    rows = {m: {"rq": mean(m, rq), **{s: mean(m, scale(s)) for s in Q.SCALES}, "non_copying": mean(m, nc)}
            for m in (ARM, DRAFT, WRITER, "rx_r")}
    src = {r["run_id"]: _read_json(SOURCE_DIR / ARM / "deepseek" / f"{r['run_id']}.json")
           for r in dev_runs(ARM) if (SOURCE_DIR / ARM / "deepseek" / f"{r['run_id']}.json").exists()}
    rows[ARM]["non_copying_vs_source_paper"] = (round(statistics.fmean(x["non_copying"] for x in src.values()), 2)
                                                if src else None)
    contrasts = {}
    for name, base in BASES.items():
        contrasts[name] = {"rq": vs(rq, ARM, base), **{s: vs(scale(s), ARM, base) for s in Q.SCALES},
                           "non_copying": vs(nc, ARM, base),
                           **{f"pairwise_v2_{j}": pair(base, j) for j in ("deepseek", "o1")}}
    c = contrasts["draft"]
    both = all(c[f"pairwise_v2_{j}"].get("papers") and c[f"pairwise_v2_{j}"]["diff"] > 0 for j in ("deepseek", "o1"))
    rq_ok = c["rq"].get("papers") and c["rq"]["diff"] >= -0.1
    decision = ("go: run all 45 papers" if both and rq_ok and not d["rubber_stamp_flag"] else
                "fix the critic first (rubber-stamping)" if d["rubber_stamp_flag"] else "no-go")
    return {"diagnostics": d, "rows": rows, "contrasts": contrasts, "decision": decision,
            "leakage": {**paper_leakage(), "background": background_leakage()}, "note": "pilot on 8 dev papers; exploratory (loop.md 28.1)"}


def _c(x: dict[str, Any]) -> str:
    if not x or not x.get("papers"):
        return "–"
    return f"{x['diff']:+.2f} [{x['ci95'][0]:+.2f}, {x['ci95'][1]:+.2f}], {x['up']} vs {x['down']} papers"


def _f(x: Any) -> str:
    return "–" if x is None else f"{x:.2f}" if isinstance(x, float) else str(x)


def render(r: dict[str, Any]) -> str:
    L = ["# Experiment 49 pilot: per-paper generate → critique → narrow", "",
         "Pre-registered in loop.md 28.1. 8 dev papers × 3 levels × 2 samples. o3-mini agents; DeepSeek RQ (3 calls), "
         "non-copying and pairwise v2; o1 pairwise v2.", "", f"**Decision rule: {r['decision']}**", "",
         "| Method | RQ | Plaus. | Test. | Useful. | Non-copying |", "|---|---:|---:|---:|---:|---:|"]
    for m, x in r["rows"].items():
        L.append(f"| `{m}` | {_f(x['rq'])} | {_f(x['plausibility'])} | {_f(x['testability'])} | "
                 f"{_f(x['usefulness'])} | {_f(x['non_copying'])} |")
    L += ["", f"Non-copying of the rank-1 hypothesis against its own source paper (diagnostic): "
          f"{_f(r['rows'][ARM]['non_copying_vs_source_paper'])}", ""]
    for name, c in r["contrasts"].items():
        L += [f"## perpaper vs `{BASES[name]}` (paired by paper)", "",
              f"- RQ: {_c(c['rq'])}; plausibility {_c(c['plausibility'])}; testability {_c(c['testability'])}; "
              f"usefulness {_c(c['usefulness'])}", f"- Non-copying: {_c(c['non_copying'])}",
              f"- Pairwise v2: DeepSeek {_c(c['pairwise_v2_deepseek'])}; o1 {_c(c['pairwise_v2_o1'])}", ""]
    L += ["## Diagnostics", ""] + [f"- {k}: {v}" for k, v in r["diagnostics"].items()]
    L += ["", "## Leakage", "", str(r["leakage"]), ""]
    return "\n".join(L)


def main() -> None:
    global ARM
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("generate", "rq", "noncopy", "noncopy_source", "pairwise", "report"))
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--rep", type=int, default=1)
    parser.add_argument("--judge", default="deepseek", choices=("deepseek", "o1"))
    parser.add_argument("--base", default="draft", choices=tuple(BASES))
    parser.add_argument("--part", type=int, default=0)
    parser.add_argument("--parts", type=int, default=1)
    parser.add_argument("--arm", default=ARM, choices=PP.ARMS,
                        help="the arm to generate or evaluate (loop.md 28.4: perpaper_dated)")
    parser.add_argument("--scope", default="dev", choices=("dev", "all45"))
    parser.add_argument("--samples", type=int, nargs="+", default=list(H.SAMPLES))
    args = parser.parse_args()
    ARM = args.arm
    if args.stage == "generate":
        print(generate(args.workers, args.part, args.parts, ARM, args.scope, tuple(args.samples)))
    elif args.stage == "rq":
        items = RQ.run_items([ARM])
        if args.rep > 1:
            items = [(RQ.rep_kind(k, args.rep), n, i, d) for k, n, i, d in items]
        print(RQ.run_stage(items, "deepseek", args.workers))
    elif args.stage == "noncopy":
        print(N.noncopy_stage([ARM], "deepseek", args.workers))
    elif args.stage == "noncopy_source":
        print(noncopy_source_stage(args.workers))
    elif args.stage == "pairwise":
        print(Q.pairwise_stage([ARM], args.judge, args.workers, BASES[args.base], N.PAIR_SYSTEM_V2, N.PAIR_DIR))
    else:
        result = report()
        name = "analysis_perpaper" if ARM == "perpaper" else f"analysis_{ARM}"
        atomic_json(OUT / f"{name}.json", result)
        (OUT / f"{name}.md").write_text(render(result))
        print(render(result))


if __name__ == "__main__":
    main()
