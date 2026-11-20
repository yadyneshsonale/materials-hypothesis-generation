"""Collect the numbers, prompts and the example run for the 2026-11-20 deck (the per-paper method, loop.md 28).
Writes deck_inputs.json. Sources: loop_rx/perpaper_dated runs (loop.md 28.4-28.5), analysis_perpaper_dated.json (the
pre-registered pilot), the judges' stored outputs (all 45 papers, exploratory), the method's prompts.

    ./.venv/bin/python presentations/2026-11-20_per_paper_method/collect_inputs.py
"""

from __future__ import annotations

import json
import os
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import rx_experiment  # noqa: E402,F401 - first: it sets the loop root
import focused_search as FS  # noqa: E402
import noncopy_eval as N  # noqa: E402
import perpaper_eval as E  # noqa: E402
import perpaper_loop as P  # noqa: E402
import rq_judge as RQ  # noqa: E402

ARM = E.ARM = "perpaper_dated"
EXAMPLE = ("PMC11643467", "problem_constrained", 1)
ALL = {c["paper_id"] for c, _ in E.X.units()}


def s1(method: str, fn) -> dict:
    return {k: v for k, v in fn(method).items() if k[0] in ALL and k[2] == 1}


def mean_scales(method: str) -> dict:
    out = {"rq": E.Q.mean_of(E.Q.per_paper(s1(method, E.rq)))}
    for s in E.Q.SCALES:
        out[s] = E.Q.mean_of(E.Q.per_paper(s1(method, E.scale(s))))
    return out


def paired(fn, a: str, b: str) -> dict:
    x, y = s1(a, fn), s1(b, fn)
    keys = x.keys() & y.keys()
    return E.A.paired(E.Q.per_paper({k: x[k] for k in keys}), E.Q.per_paper({k: y[k] for k in keys}))


def process(runs: list[dict]) -> dict:
    papers = [p for r in runs for p in r["notes"]["papers"]]
    corpus = [len(FS.build(r["paper_id"], r["query_level"])["papers"]) for r in runs]
    kg = [p["background"]["kg_facts"] for p in papers]
    txt = [p["background"]["texts"] for p in papers]
    return {
        "runs": len(runs), "corpus_papers": statistics.fmean(corpus), "papers": statistics.fmean(
            len(r["notes"]["papers"]) for r in runs),
        "paper_chars": statistics.fmean(p["paper_chars"] for p in papers),
        "texts": statistics.fmean(txt), "kg": statistics.fmean(kg),
        "round1_share": sum(bool(p.get("n_accepted")) and p["n_rounds"] == 1 for p in papers) / len(papers),
        "rounds_mean": statistics.fmean(p["n_rounds"] for p in papers),
        "rounds_max": max(p["n_rounds"] for p in papers),
        "dropped_share": sum(not p.get("n_accepted") for p in papers) / len(papers),
        "accepted": statistics.fmean(r["notes"]["summary"]["accepted"] for r in runs),
        "pool": statistics.fmean(r["notes"]["summary"]["pool_after_dedupe"] for r in runs),
        "matches": statistics.fmean(len(r["notes"].get("matches", [])) for r in runs),
        "tied_share": sum(bool(r["notes"]["tournament"].get("rank1_tied")) for r in runs) / len(runs),
        "calls": statistics.fmean(r["llm_calls"] for r in runs),
        "calls_by_role": {role: statistics.fmean(sum(1 for t in r["trace"] if t.get("role") == role and "event" not in t)
                                                 for r in runs) for role in ("generator", "generator_revise",
                                                                             "critic", "narrow")},
        "minutes": statistics.fmean(r["elapsed_seconds"] for r in runs) / 60,
        "pass_round1": {c: statistics.fmean(v[c] for p in papers for v in p["rounds"][0]["verdicts"])
                        for c in P.CRITERIA},
    }


def main() -> None:
    runs = [r for r in RQ.runs_of(ARM) if r["sample"] == 1 and r["paper_id"] in ALL]
    pilot = json.loads((E.OUT / "analysis_perpaper_dated.json").read_text())
    draft, writer = E.DRAFT, E.WRITER
    full = {
        "means": {m: mean_scales(m) for m in (ARM, draft, "rx_r", writer)},
        "vs": {name: {"rq": paired(E.rq, ARM, base), **{s: paired(E.scale(s), ARM, base) for s in E.Q.SCALES},
                      **{j: E.pair(base, j, scope="all45") for j in ("deepseek", "o1")}}
               for name, base in (("draft", draft), ("writer", writer))},
    }
    ex = json.loads((E.H.OUT / ARM / "runs" / f"{EXAMPLE[0]}__{EXAMPLE[1]}__{ARM}__s{EXAMPLE[2]}.json").read_text())
    manifest = FS.build(EXAMPLE[0], EXAMPLE[1])
    out = {
        "process": process(runs),
        "pilot": {"rows": pilot["rows"], "contrasts": pilot["contrasts"], "decision": pilot["decision"],
                  "diagnostics": pilot["diagnostics"], "leakage": pilot["leakage"]},
        "all45": full,
        "corpus": json.loads((ROOT / "experiments/high_temperature_hea_qwen35b/materials_texts/sources.json")
                             .read_text())["sources"],
        "corpus_unique": len(P.MT.load()),
        "corpus_unique_by_source": {src: sum(r["source"] == src for r in P.MT.load()) for src in P.MT.BUILDERS},
        "prompts": {"PLAN": FS.PLAN_SYSTEM, "SCREEN": FS.SCREEN_SYSTEM, "GENERATOR": P.GENERATOR_SYSTEM.replace(
            "{k}", str(P.K)), "CRITIC": P.CRITIC_SYSTEM, "NARROW": P.NARROW_SYSTEM, "RQ": RQ.RQ_SYSTEM,
            "PAIR_V2": N.PAIR_SYSTEM_V2},
        "models": {"plan": FS.PLAN_MODEL, "screen": getattr(FS, "SCREEN_MODEL", "gpt-4o")},
        "example": {"run": {k: ex[k] for k in ("run_id", "query", "publication_date", "generation", "audit",
                                                "llm_calls", "elapsed_seconds", "cited_evidence")},
                    "notes": ex["notes"], "plan": manifest["plan"], "searches": manifest["searches"],
                    "unique_hits": manifest["unique_hits"], "admitted": manifest["admitted"],
                    "screened": manifest["screened"], "corpus_papers": len(manifest["papers"])},
    }
    (HERE / "deck_inputs.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str) + "\n")
    print(json.dumps(out["process"], indent=1, default=str))
    print(json.dumps(full["means"], indent=1))


if __name__ == "__main__":
    main()
