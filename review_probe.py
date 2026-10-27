"""Experiment 34, B1 (loop.md 16.1): memorisation probe for the candidate stronger generators (must_obey.md 2.3).

Each candidate gets only the title and year of each paper it is eligible for, and is asked what the paper did and
found. GPT-5.6 scores the recall against the answer key, with the same prompts as memorisation_probe.py. Eligible
means published more than 31 days after the model's cutoff.

The Llama-3.3 control is probed on all 36 papers. Rule (loop.md 16.1 addendum): a candidate is excluded if its
specific-recall rate exceeds the control's on the same papers by more than 15 percentage points.

Output: review_eval/probe/.
"""

from __future__ import annotations

import json
import statistics
from datetime import date, timedelta
from typing import Any

import llm_client as lc
import memorisation_probe as P
import review_measurement as M
import rubric_eval as rx
from hypothesis_evidence_v2 import atomic_json
from must_obey_check import MARGIN_DAYS, MODEL_CUTOFFS
from temporal_hypothesis_benchmark import _read_json

OUT = M.OUT / "probe"
CONTROL = "llama-3.3-70b"
CANDIDATES = {
    "gpt-4o": {"deployment": "gpt-4o_2024-11-20", "token_field": "max_completion_tokens", "temperature": 0.2,
               "max_tokens": 1500},
    "o3": {"deployment": "o3_2025-04-16", "token_field": "max_completion_tokens", "temperature": None,
           "max_tokens": 12000},
    "o4-mini": {"deployment": "o4-mini_2025-04-16", "token_field": "max_completion_tokens", "temperature": None,
                "max_tokens": 12000},
    "gpt-4.1": {"deployment": "gpt-4.1_2025-04-14", "token_field": "max_completion_tokens", "temperature": 0.2,
                "max_tokens": 1500},
    "gpt-5": {"deployment": "gpt-5_2025-08-07", "token_field": "max_completion_tokens", "temperature": None,
              "max_tokens": 12000},
}
SPECS = {CONTROL: {"deployment": "Llama-3.3-70B-Instruct_5", "token_field": "max_tokens", "temperature": 0.2,
                   "max_tokens": 1500}, **CANDIDATES}
DIMS = ("intervention", "structure", "mechanism", "quantitative_results")
EXCLUDE_MARGIN = 0.15


def titles() -> dict[str, str]:
    out = {pid: str(rx.metadata()[pid]["title"]) for pid in rx.cases()}
    for name in ("benchmark_test2", "benchmark_test3"):
        for row in _read_json(M.E / name / "selected.json"):
            out[row["pmcid"]] = str(row["title"])
    return out


def eligible_papers(model: str, cases: dict[str, dict[str, Any]]) -> list[str]:
    if model == CONTROL:
        return sorted(cases)
    cutoff = date.fromisoformat(MODEL_CUTOFFS[SPECS[model]["deployment"]])
    return sorted(p for p, c in cases.items()
                  if date.fromisoformat(c["publication_date"]) > cutoff + timedelta(days=MARGIN_DAYS))


def probe_one(pid: str, model: str, sample: int, case: dict[str, Any], title: str) -> None:
    path = OUT / "runs" / f"{pid}__{model}__s{sample}.json"
    if path.exists():
        return
    spec = SPECS[model]
    user = json.dumps({"title": title, "year": str(case["publication_date"])[:4]}, ensure_ascii=False)
    recollection = lc.trapi_chat_json(spec["deployment"], P.PROBE_SYSTEM, user, max_tokens=spec["max_tokens"],
                                      token_field=spec["token_field"], temperature=spec["temperature"])
    target = {k: case["hidden_target"].get(k) for k in ("material_initial_state", "intervention",
                                                         "structural_mediator", "mechanism", "actual_result")}
    score = lc.judge_chat_json(P.SCORE_SYSTEM, json.dumps({"title": title, "actual": target,
                                                           "recollection": recollection}, ensure_ascii=False),
                               max_tokens=4000)
    atomic_json(path, {"paper_id": pid, "model": model, "deployment": spec["deployment"], "sample": sample,
                       "title": title, "recollection": recollection, "score": score})


def run(workers: int) -> dict[str, int]:
    cases, names = M.held_out_cases(), titles()
    jobs = [(pid, model, s, cases[pid], names[pid]) for model in SPECS for pid in eligible_papers(model, cases)
            for s in P.SAMPLES if not (OUT / "runs" / f"{pid}__{model}__s{s}.json").exists()]
    return M.parallel(jobs, probe_one, workers, "probe")


def specific(record: dict[str, Any]) -> bool:
    return any(int(record["score"].get(d, 0) or 0) == 2 for d in DIMS)


def summary() -> dict[str, Any]:
    records = [_read_json(p) for p in sorted((OUT / "runs").glob("PMC*.json"))]
    cases = M.held_out_cases()
    out: dict[str, Any] = {}
    for model in CANDIDATES:
        papers = set(eligible_papers(model, cases))
        mine = [r for r in records if r["model"] == model and r["paper_id"] in papers]
        ctrl = [r for r in records if r["model"] == CONTROL and r["paper_id"] in papers]
        if not mine or not ctrl:
            continue
        rate, base = statistics.fmean(map(specific, mine)), statistics.fmean(map(specific, ctrl))
        out[model] = {"papers": len(papers), "runs": len(mine), "claims_to_remember":
                      round(statistics.fmean(bool(r["recollection"].get("remembers")) for r in mine), 3),
                      "specific_recall": round(rate, 3), "control_specific_recall_same_papers": round(base, 3),
                      "excess": round(rate - base, 3), "excluded": rate - base > EXCLUDE_MARGIN}
    atomic_json(OUT / "summary.json", out)
    return out


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("run", "summary"))
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    print(run(args.workers) if args.stage == "run" else json.dumps(summary(), indent=1))
