"""Experiment 22: failure analysis of the clean rerun (benchmark v3 queries, pre-cutoff generator), before any new
method is tried (must_obey.md section 8).

Inputs: every judged hypothesis of experiment 21 (rerun_v3), about 1,500 hypotheses from 26 arms. Questions:
  A. Which judge dimensions fail, and how are hypotheses classified?
  B. Which cases and levels are reachable at all (best hypothesis per unit, judge intervention score >= 2)?
  C. What kind of contribution is each target, and does the question ask for that kind? (GPT-5.6, analysis only)
  D. Is the generator in the right class but wrong on specifics, or in the wrong class? Lever match per hypothesis
     (GPT-5.6, analysis only; the labeller sees the target, which is allowed for evaluation, never for generation).
  E. Selection headroom: pass@k = chance that at least one of k hypotheses hits the target's lever, and the gap
     between the mean and the best hypothesis per unit.
  F. Error categories of the judges' fatal errors (same coder as experiments 12 and 15).
  G. Judge agreement (GPT-5.6 vs DeepSeek) per unit.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import llm_client as lc
from failure_analysis import CODER_SYSTEM, ERROR_CATEGORIES, spearman, validate_labels
from hypothesis_evidence_v2 import atomic_json
from temporal_eval_v3 import EXPERIMENT_DIR, PRIMARY_DIMENSIONS, QUERY_LEVELS, ALL_DIMENSIONS
from temporal_hypothesis_benchmark import _read_json

NEW = EXPERIMENT_DIR / "rerun_v3"
CASES = EXPERIMENT_DIR / "benchmark_v3" / "cases"
OUT = NEW / "failure"
TARGET_TYPES = ("composition_change", "processing_route", "heat_or_thermomechanical_treatment",
                "microstructure_architecture", "surface_or_coating", "computational_method_development",
                "simulation_study", "experimental_characterization_study", "other")
CODED_ARMS = ("exp14:closed_book", "exp14:text_chunks", "exp16:card_systemmatch", "exp17:graph_profiles",
              "exp7:tool_agent")
LABEL_SYSTEM = (
    "You analyse why generated materials-science hypotheses fail to reconstruct a published result. The input has "
    "the research question that was given to the generators, the paper's actual result (hidden target), and a "
    "numbered list of generated hypotheses. (1) Classify the target: target_type, one of " + ", ".join(TARGET_TYPES)
    + "; and question_fit: does the research question ask for the kind of contribution the target is (fits, partly "
    "or mismatch), with a one-sentence reason. For example, a target that is a simulation or characterization study "
    "does not fit a question that asks for an intervention to improve a property. (2) For each hypothesis give "
    "intervention_class (same list) and lever_match: 0 = a different kind of intervention than the target; 1 = the "
    "same kind but a different specific lever; 2 = the same lever with different specifics (element, amount, route "
    "or parameters); 3 = essentially the target's intervention. Return JSON {\"target_type\": str, \"question_fit\": "
    "str, \"question_fit_reason\": str, \"hypotheses\": [{\"id\": int, \"intervention_class\": str, "
    "\"lever_match\": int}]} with one entry per hypothesis."
)


def recon(scores: dict[str, int]) -> float:
    return statistics.fmean(scores[d] for d in PRIMARY_DIMENSIONS)


def cases() -> dict[str, dict[str, Any]]:
    return {c["paper_id"]: c for c in (_read_json(p) for p in sorted(CASES.glob("PMC*.json")))}


def collect() -> list[dict[str, Any]]:
    """Every judged rerun hypothesis: arm, unit, generation, GPT-5.6 and DeepSeek judgments."""
    rows: list[dict[str, Any]] = []

    def add(arm: str, run: dict[str, Any], generation: dict[str, Any] | None, gpt: Path, deep: Path | None,
            sample: int = 1) -> None:
        if not generation or not gpt.exists():
            return
        g = _read_json(gpt)
        rows.append({"arm": arm, "paper": run["paper_id"], "level": run["query_level"], "sample": sample,
                     "run_id": run["run_id"], "generation": generation, "scores": g["scores"],
                     "classification": g.get("classification", ""), "fatal_errors": g.get("fatal_errors", []),
                     "deep": _read_json(deep)["scores"] if deep and deep.exists() else None,
                     "tool_calls": run.get("tool_calls"), "cited": len(run.get("cited_ids")
                                                                       or run.get("cited_evidence_ids") or [])})

    for sub, tag in (("eval_v3", "exp7"),):
        for p in sorted((NEW / sub / "runs").glob("PMC*.json")):
            run = _read_json(p)
            if run.get("status") == "ok":
                add(f"{tag}:{run['setting']}", run, run["generation"], NEW / sub / "judgments" / "absolute" / p.name,
                    None)
    for p in sorted((NEW / "eval_v4_matkg" / "runs").glob("PMC*__tool_agent_kg.json")):
        run = _read_json(p)
        if run.get("status") == "ok":
            add("exp9:tool_agent_kg", run, run["generation"],
                NEW / "eval_v4_matkg" / "judgments" / "absolute" / p.name, None)
    for arm in ("critique", "self_revise"):
        for p in sorted((NEW / "eval_critique" / "revisions" / arm).glob("PMC*.json")):
            rev = _read_json(p)
            rev = {**rev, "run_id": rev.get("run_id", p.stem)}
            add(f"exp11:{arm}", rev, rev.get("revised_generation"),
                NEW / "eval_critique" / "judgments" / arm / p.name, None)
    for sub, tag in (("rubric_eval", "exp14"), ("improvements", "exp16"), ("citegraph", "exp17")):
        for p in sorted((NEW / sub / "runs").glob("PMC*.json")):
            run = _read_json(p)
            if run.get("status") == "ok":
                add(f"{tag}:{run['arm']}", run, run["generation"], NEW / sub / "judgments" / "gpt56" / p.name,
                    NEW / sub / "judgments" / "deepseek" / p.name, int(run.get("sample", 1)))
    return rows


def short(generation: dict[str, Any]) -> str:
    parts = [f"{k}: {str(generation.get(k, ''))[:260]}" for k in ("hypothesis", "intervention", "mechanism")]
    return " | ".join(parts)


# ---------------------------------------------------------------- stage: lever labels (analysis only)

def label_stage(workers: int, resume: bool) -> dict[str, int]:
    from concurrent.futures import ThreadPoolExecutor
    rows = collect()
    by_unit: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_unit[(r["paper"], r["level"])].append(r)
    all_cases = cases()
    out = OUT / "labels"

    def job(key: tuple[str, str]) -> str:
        path = out / f"{key[0]}__{key[1]}.json"
        if resume and path.exists():
            return "skipped"
        unit_rows = sorted(by_unit[key], key=lambda r: (r["arm"], r["sample"]))
        case = all_cases[key[0]]
        payload = {"research_question": case["queries"][key[1]]["text"],
                   "hidden_target": {k: case["hidden_target"].get(k) for k in (
                       "material_initial_state", "intervention", "structural_mediator", "mechanism",
                       "predicted_outcome")},
                   "hypotheses": [{"id": i, "text": short(r["generation"])} for i, r in enumerate(unit_rows)]}
        raw = lc.judge_chat_json(LABEL_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=16000)
        labels = {}
        for item in raw.get("hypotheses", []) if isinstance(raw, dict) else []:
            try:
                labels[int(item["id"])] = {"intervention_class": str(item.get("intervention_class", "other")),
                                           "lever_match": max(0, min(3, int(item.get("lever_match", 0))))}
            except (KeyError, TypeError, ValueError):
                continue
        atomic_json(path, {"paper": key[0], "level": key[1], "labeller": lc.judge_info(),
                           "target_type": raw.get("target_type") if isinstance(raw, dict) else None,
                           "question_fit": raw.get("question_fit") if isinstance(raw, dict) else None,
                           "question_fit_reason": raw.get("question_fit_reason") if isinstance(raw, dict) else None,
                           "items": [{"run_id": r["run_id"], "arm": r["arm"], "sample": r["sample"],
                                      **labels.get(i, {"intervention_class": "unlabelled", "lever_match": None})}
                                     for i, r in enumerate(unit_rows)]})
        return "done"

    with ThreadPoolExecutor(workers) as pool:
        return dict(Counter(pool.map(job, sorted(by_unit))))


# ---------------------------------------------------------------- stage: error coding

def code_stage(workers: int, resume: bool) -> dict[str, int]:
    from concurrent.futures import ThreadPoolExecutor
    rows = [r for r in collect() if r["arm"] in CODED_ARMS and r["fatal_errors"]]
    out = OUT / "error_codes"

    def job(r: dict[str, Any]) -> str:
        path = out / f"{r['arm'].replace(':', '__')}__{r['run_id']}__s{r['sample']}.json"
        if resume and path.exists():
            return "skipped"
        errors = [str(e) for e in r["fatal_errors"]]
        raw = lc.judge_chat_json(CODER_SYSTEM, json.dumps({"errors": [{"index": i, "text": t}
                                                                     for i, t in enumerate(errors)]},
                                                          ensure_ascii=False), max_tokens=6000)
        labels = validate_labels(raw, len(errors))
        atomic_json(path, {"arm": r["arm"], "run_id": r["run_id"], "paper": r["paper"], "level": r["level"],
                           "errors": [{"text": t, "category": labels[i]} for i, t in enumerate(errors)]})
        return "done"

    with ThreadPoolExecutor(workers) as pool:
        return dict(Counter(pool.map(job, rows)))


# ---------------------------------------------------------------- report

def mean(values: list[Any]) -> float | None:
    values = [v for v in values if v is not None]
    return round(statistics.fmean(values), 3) if values else None


def pass_at_k(n: int, c: int, k: int) -> float:
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def report() -> dict[str, Any]:
    rows = collect()
    all_cases = cases()
    labels: dict[str, dict[str, Any]] = {}
    unit_meta: dict[tuple[str, str], dict[str, Any]] = {}
    for p in sorted((OUT / "labels").glob("PMC*.json")):
        lab = _read_json(p)
        unit_meta[(lab["paper"], lab["level"])] = lab
        for item in lab["items"]:
            labels[f"{item['run_id']}::{item['arm']}::{item['sample']}"] = item
    for r in rows:
        r["recon"] = recon(r["scores"])
        lab = labels.get(f"{r['run_id']}::{r['arm']}::{r['sample']}", {})
        r["lever_match"] = lab.get("lever_match")
        r["class"] = lab.get("intervention_class")

    # A. dimensions and classifications
    dims = {d: mean([r["scores"][d] for r in rows]) for d in ALL_DIMENSIONS}
    classes = Counter(r["classification"] for r in rows)

    # B/E. per unit and per case reachability, pass@k
    by_unit: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_unit[(r["paper"], r["level"])].append(r)
    units = []
    for (paper, level), rs in sorted(by_unit.items()):
        n = len(rs)
        hits_judge = sum(1 for r in rs if r["scores"]["intervention_reconstruction"] >= 2)
        hits_lever = sum(1 for r in rs if (r["lever_match"] or 0) >= 2)
        meta = unit_meta.get((paper, level), {})
        units.append({"paper": paper, "level": level, "split": "test" if all_cases[paper]["split"] == "test" else "dev",
                      "n": n, "mean_recon": mean([r["recon"] for r in rs]), "max_recon": max(r["recon"] for r in rs),
                      "share_intervention_ge2": round(hits_judge / n, 3), "share_lever_ge2": round(hits_lever / n, 3),
                      "share_same_class": round(sum(1 for r in rs if (r["lever_match"] or 0) >= 1) / n, 3),
                      "pass@1": round(pass_at_k(n, hits_lever, 1), 3), "pass@5": round(pass_at_k(n, hits_lever, 5), 3),
                      "pass@10": round(pass_at_k(n, hits_lever, 10), 3),
                      "target_type": meta.get("target_type"), "question_fit": meta.get("question_fit")})
    per_case = {}
    for paper in sorted(all_cases):
        us = [u for u in units if u["paper"] == paper]
        fits = Counter(u["question_fit"] for u in us)
        per_case[paper] = {"split": us[0]["split"] if us else None,
                           "target_type": Counter(u["target_type"] for u in us).most_common(1)[0][0] if us else None,
                           "question_fit": fits.most_common(1)[0][0] if us else None,
                           "mean_recon": mean([u["mean_recon"] for u in us]),
                           "best_recon": max(u["max_recon"] for u in us) if us else None,
                           "share_lever_ge2": mean([u["share_lever_ge2"] for u in us]),
                           "share_same_class": mean([u["share_same_class"] for u in us])}
    fit_groups = {fit: {"cases": sum(1 for c in per_case.values() if c["question_fit"] == fit),
                        "mean_recon": mean([c["mean_recon"] for c in per_case.values() if c["question_fit"] == fit]),
                        "share_lever_ge2": mean([c["share_lever_ge2"] for c in per_case.values()
                                                 if c["question_fit"] == fit])}
                  for fit in ("fits", "partly", "mismatch")}

    # D. class vs specifics, and score by lever match
    lever_dist = Counter(r["lever_match"] for r in rows)
    recon_by_lever = {k: mean([r["recon"] for r in rows if r["lever_match"] == k]) for k in (0, 1, 2, 3)}

    # E. selection headroom
    headroom = {"mean_of_unit_means": mean([u["mean_recon"] for u in units]),
                "mean_of_unit_best": mean([u["max_recon"] for u in units]),
                "pass@1": mean([u["pass@1"] for u in units]), "pass@5": mean([u["pass@5"] for u in units]),
                "pass@10": mean([u["pass@10"] for u in units]),
                "units_with_no_lever_hit": sum(1 for u in units if u["share_lever_ge2"] == 0),
                "units": len(units)}

    # per arm
    arms = sorted({r["arm"] for r in rows})
    per_arm = {a: {"n": sum(1 for r in rows if r["arm"] == a),
                   "recon": mean([r["recon"] for r in rows if r["arm"] == a]),
                   "lever_ge2": mean([1.0 if (r["lever_match"] or 0) >= 2 else 0.0 for r in rows if r["arm"] == a]),
                   "same_class": mean([1.0 if (r["lever_match"] or 0) >= 1 else 0.0 for r in rows if r["arm"] == a]),
                   "problem_alignment": mean([r["scores"]["problem_alignment"] for r in rows if r["arm"] == a])}
               for a in arms}
    by_level = {lvl: {"recon": mean([r["recon"] for r in rows if r["level"] == lvl]),
                      "lever_ge2": mean([1.0 if (r["lever_match"] or 0) >= 2 else 0.0 for r in rows
                                         if r["level"] == lvl]),
                      "problem_alignment": mean([r["scores"]["problem_alignment"] for r in rows if r["level"] == lvl])}
                for lvl in QUERY_LEVELS}

    # F. error categories
    codes = [_read_json(p) for p in sorted((OUT / "error_codes").glob("*.json"))]
    error_mix = {}
    for arm in CODED_ARMS:
        cats = Counter(e["category"] for c in codes if c["arm"] == arm for e in c["errors"])
        total = sum(cats.values())
        error_mix[arm] = {"errors": total, **{k: round(cats[k] / total, 3) if total else None
                                              for k in ERROR_CATEGORIES}}
    pooled = Counter(e["category"] for c in codes for e in c["errors"])
    error_mix["pooled"] = {"errors": sum(pooled.values()),
                           **{k: round(pooled[k] / max(1, sum(pooled.values())), 3) for k in ERROR_CATEGORIES}}

    # G. judge agreement
    pairs = [(r["recon"], recon(r["deep"])) for r in rows if r["deep"]]
    unit_pairs: dict[tuple[str, str, str], list[tuple[float, float]]] = defaultdict(list)
    for r in rows:
        if r["deep"]:
            unit_pairs[(r["arm"], r["paper"], r["level"])].append((r["recon"], recon(r["deep"])))
    agreement = {"hypotheses": len(pairs), "spearman_hypothesis_level": round(spearman([a for a, _ in pairs],
                                                                                       [b for _, b in pairs]), 3),
                 "gpt_mean": mean([a for a, _ in pairs]), "deepseek_mean": mean([b for _, b in pairs])}
    analysis = {"hypotheses": len(rows), "dimensions": dims, "classifications": dict(classes),
                "lever_match_distribution": {str(k): v for k, v in sorted(lever_dist.items(), key=lambda x: str(x[0]))},
                "recon_by_lever_match": recon_by_lever, "per_case": per_case, "question_fit_groups": fit_groups,
                "selection_headroom": headroom, "per_arm": per_arm, "by_level": by_level, "error_mix": error_mix,
                "judge_agreement": agreement, "units": units}
    OUT.mkdir(parents=True, exist_ok=True)
    atomic_json(OUT / "analysis.json", analysis)
    return analysis


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("label", "code", "report"))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()
    if args.stage == "label":
        print(label_stage(args.workers, not args.no_resume))
    elif args.stage == "code":
        print(code_stage(args.workers, not args.no_resume))
    else:
        a = report()
        print(json.dumps({k: a[k] for k in a if k != "units"}, indent=1))


if __name__ == "__main__":
    main()
