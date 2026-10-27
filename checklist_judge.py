"""Experiment 33, A4 (loop.md 16.1): a checklist judge built from the reviews' advice.

The reviews suggested yes/no criteria, partial credit, anchors and quoting before scoring. Each frozen answer key
becomes 6-12 atomic, checkable facts, tagged by judge dimension (intervention, conditions, mechanism, outcome). A
judge then marks each fact yes, partial or no for a hypothesis, after quoting the supporting span. It also says
whether the research question already states the fact. Code verifies every quote.

Score: per dimension, the mean over facts not given in the question (yes = 1, partial = 0.5, no = 0). The checklist
score is 4 x the mean over dimensions that have facts, on the same 0-4 scale as the reconstruction score.

Stages:
- facts: GPT-5.6 writes the facts, DeepSeek checks each against the key, unsupported facts are dropped, the rest is
  frozen.
- score: both judges score a target set (controls, runs, retest).
- analyze: reliability against the 0-4 judge, and the pre-registered adoption rule.

Outputs: review_eval/checklist/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import review_measurement as M
import v4_scimon_analysis as A
from hypothesis_evidence_v2 import atomic_json
from temporal_hypothesis_benchmark import _read_json

OUT = M.OUT / "checklist"
DIMENSIONS = ("intervention", "conditions", "mechanism", "outcome")
VERDICT = {"yes": 1.0, "partial": 0.5, "no": 0.0}
KEY_CONFIGS = ("closed_book", "closed_book_o3mini", "writer_only_b_o3mini", "trend_ground_b_o3mini",
               "text_chunks_b_o3mini")
# Experiment 34 configurations (loop.md 16.1, B0-B3); combinations are added here if the finalist rule calls for them.
PHASEB_CONFIGS = ("writer_only_b_o3mini_r4", "writer_only_b_4o", "writer_only_b_o4mini", "writer_only_b_41",
                  "fewshot_similar_b_o3mini", "fewshot_diverse_b_o3mini", "router_b_o3mini")
TARGET_CONFIGS = {"runs": KEY_CONFIGS, "retest": KEY_CONFIGS, "phaseb": PHASEB_CONFIGS}
TARGET_BENCHMARKS = {"runs": ("v3.1", "test2", "test3"), "retest": ("v3.1", "test2", "test3"),
                     "phaseb": ("v3.1", "test2", "test3"), "test4": ("test4",)}
RETEST_N = 60

FACTS_SYSTEM = (
    "You turn the hidden answer key of a materials-science hypothesis benchmark into atomic facts that a grader can "
    "check in a proposed hypothesis. Each fact is one specific, checkable claim about what this paper did or found, "
    "and is not true of high-entropy alloys in general. Cover four dimensions: intervention (what was changed or "
    "studied, with its key parameters such as composition, process or treatment settings); conditions (temperature, "
    "atmosphere, time, load or other test or processing conditions); mechanism (including the structural mediator, "
    "such as a phase, scale or defect, through which the effect acts); and outcome (the direction of the reported "
    "effect relative to the baseline; give a reported magnitude as a separate fact). Do not make facts about the "
    "starting material alone. Write 6 to 12 facts, at least one per dimension when the key has content for it. Mark "
    "core true for the facts that define the study, and false for details. Return JSON {\"facts\": [{\"id\": "
    "\"f1\", \"dimension\": \"intervention|conditions|mechanism|outcome\", \"core\": true|false, \"text\": str}]}."
)
FIDELITY_SYSTEM = (
    "You check facts derived from a benchmark answer key. For each fact, say whether the answer key supports it "
    "(the key states it or directly implies it). Return JSON {\"facts\": [{\"id\": str, \"supported\": true|false}]}."
)
SCORE_SYSTEM = (
    "You grade a proposed materials-science hypothesis against a list of facts about what a paper actually did and "
    "found. For each fact, in this order: first copy the shortest exact quote from the hypothesis that states it (an "
    "empty string if none); then give a verdict. yes: the hypothesis states the fact or an equivalent claim with the "
    "same specific content. partial: it states a less specific or partly matching version. no: absent or "
    "contradicted. Judge meaning, not wording, and do not credit generic statements that would fit any high-entropy "
    "alloy. Also mark given_in_question true if the research question itself already states the fact. Return JSON "
    "{\"facts\": [{\"id\": str, \"quote\": str, \"verdict\": \"yes|partial|no\", \"given_in_question\": "
    "true|false}]}."
)


def target_hash(target: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(target, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def clean_facts(raw: Any) -> list[dict[str, Any]]:
    facts = []
    for i, f in enumerate(raw.get("facts", []) if isinstance(raw, dict) else []):
        if not isinstance(f, dict):
            continue
        dim, text = str(f.get("dimension", "")).strip().lower(), str(f.get("text", "")).strip()
        if dim in DIMENSIONS and len(text) >= 10:
            facts.append({"id": f"f{i + 1}", "dimension": dim, "core": bool(f.get("core", False)), "text": text})
    return facts[:12]


def facts_stage(workers: int, extra_dirs: tuple[Path, ...] = ()) -> dict[str, Any]:
    """Freezes facts for the 36 held-out keys, plus any extra case directories (test4 after its finals)."""
    cases = M.held_out_cases(extra_dirs)
    folder = OUT / "facts"
    jobs = [(pid,) for pid in cases if not (folder / f"{pid}.json").exists()]

    def job(pid: str) -> None:
        target = {k: cases[pid]["hidden_target"].get(k, "") for k in M.TARGET_FIELDS}
        facts = clean_facts(M.gpt_json(FACTS_SYSTEM, {"answer_key": target}))
        if len(facts) < 4:
            raise ValueError(f"{pid}: only {len(facts)} usable facts")
        check = M.deepseek_json(FIDELITY_SYSTEM, {"answer_key": target,
                                                  "facts": [{"id": f["id"], "text": f["text"]} for f in facts]})
        supported = {str(c.get("id")) for c in (check.get("facts", []) if isinstance(check, dict) else [])
                     if isinstance(c, dict) and c.get("supported") is True}
        kept = [f for f in facts if f["id"] in supported]
        atomic_json(folder / f"{pid}.json", {"paper_id": pid, "target_hash": target_hash(cases[pid]["hidden_target"]),
                                             "writer": f"trapi:{M.lc.JUDGE_TRAPI_DEPLOYMENT}",
                                             "checker": f"trapi:{M.CROSS_JUDGE['deployment']}",
                                             "proposed": len(facts), "facts": kept,
                                             "dropped": [f for f in facts if f["id"] not in supported]})

    return M.parallel(jobs, job, workers, "facts")


def load_facts() -> dict[str, dict[str, Any]]:
    return {p.stem: _read_json(p) for p in sorted((OUT / "facts").glob("PMC*.json"))}


# ---------------------------------------------------------------- scoring

def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-z%.+-]+", " ", str(text).lower())).strip()


def hypothesis_text(generation: dict[str, Any]) -> str:
    parts = []
    for key in M.HYPOTHESIS_KEYS:
        value = generation.get(key)
        if isinstance(value, dict):
            parts += [str(v) if not isinstance(v, list) else " ".join(map(str, v)) for v in value.values()]
        elif value:
            parts.append(str(value))
    return " ".join(parts)


def verify_quote(quote: str, text: str) -> str:
    """'exact' when the normalised quote occurs in the normalised hypothesis; 'loose' when at least 80% of its
    content tokens occur in it; otherwise 'none'."""
    q = _norm(quote)
    if not q:
        return "none"
    if q in _norm(text):
        return "exact"
    tokens = [t for t in q.split() if len(t) > 2]
    have = set(_norm(text).split())
    if tokens and sum(t in have for t in tokens) / len(tokens) >= 0.8:
        return "loose"
    return "none"


def score_from(facts: list[dict[str, Any]], verdicts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    per_dim: dict[str, list[float]] = defaultdict(list)
    core: list[float] = []
    for fact in facts:
        v = verdicts.get(fact["id"])
        if v is None or v["given_in_question"]:
            continue
        per_dim[fact["dimension"]].append(VERDICT[v["verdict"]])
        if fact["core"]:
            core.append(VERDICT[v["verdict"]])
    dims = {d: round(statistics.fmean(per_dim[d]), 3) for d in DIMENSIONS if per_dim.get(d)}
    return {"dimensions": dims, "checklist": round(4 * statistics.fmean(dims.values()), 3) if dims else None,
            "core": round(4 * statistics.fmean(core), 3) if core else None}


def parse_verdicts(raw: Any, facts: list[dict[str, Any]], text: str) -> tuple[dict[str, dict[str, Any]], Counter]:
    stats: Counter[str] = Counter()
    wanted = {f["id"] for f in facts}
    out: dict[str, dict[str, Any]] = {}
    for item in raw.get("facts", []) if isinstance(raw, dict) else []:
        if not isinstance(item, dict) or str(item.get("id")) not in wanted:
            continue
        verdict = str(item.get("verdict", "no")).strip().lower()
        verdict = verdict if verdict in VERDICT else "no"
        quote = str(item.get("quote", ""))
        check = verify_quote(quote, text) if verdict != "no" else "n/a"
        if verdict != "no":
            stats[f"quote_{check}"] += 1
            if check == "none":
                verdict = "no"
        out[str(item["id"])] = {"verdict": verdict, "quote": quote[:300], "quote_check": check,
                                "given_in_question": bool(item.get("given_in_question", False))}
    for fact in facts:
        if fact["id"] not in out:
            stats["missing_verdict"] += 1
            out[fact["id"]] = {"verdict": "no", "quote": "", "quote_check": "n/a", "given_in_question": False}
    return out, stats


def score_one(item: dict[str, Any], facts: dict[str, Any], judge: str) -> dict[str, Any]:
    generation = {k: item["generation"].get(k) for k in M.HYPOTHESIS_KEYS}
    payload = {"research_question": item["query"], "hypothesis": generation,
               "facts": [{"id": f["id"], "dimension": f["dimension"], "text": f["text"]} for f in facts["facts"]]}
    raw = M.gpt_json(SCORE_SYSTEM, payload) if judge == "gpt56" else M.deepseek_json(SCORE_SYSTEM, payload,
                                                                                      max_tokens=12000)
    verdicts, stats = parse_verdicts(raw, facts["facts"], hypothesis_text(generation))
    return {"run_id": item["run_id"], "judge": judge, "facts_hash": facts["target_hash"], "verdicts": verdicts,
            "quote_stats": dict(stats), **score_from(facts["facts"], verdicts)}


def test4_configs() -> tuple[str, ...]:
    return tuple(sorted(p.parent.name for p in (M.E / "loop").glob("*/runs")
                        if any(json.loads(r.read_text()).get("split") == "test4" for r in list(p.glob("PMC*.json"))[:50])))


def items_for(target: str) -> list[dict[str, Any]]:
    """controls: the A3 items. runs: every v3.1 run of the five key configurations. retest: a seeded sample of 60 of
    those runs, scored a second time. phaseb: every run of the experiment-34 configurations on the spent papers.
    test4: every test4 final run (experiment 35)."""
    if target == "controls":
        return M.load_controls()
    configs = test4_configs() if target == "test4" else TARGET_CONFIGS[target]
    rows = []
    for method in configs:
        base = M.E / "loop" / method / "runs"
        for path in sorted(base.glob("PMC*.json")):
            run = _read_json(path)
            if run.get("status") == "ok" and run["query_level"] in M.LEVELS and \
                    run.get("benchmark", "v3.1") in TARGET_BENCHMARKS[target]:
                rows.append({"run_id": run["run_id"], "paper_id": run["paper_id"], "method": method,
                             "query": run["query"], "generation": run["generation"]})
    if target == "retest":
        return sorted(random.Random(M.SEED).sample(rows, RETEST_N), key=lambda r: r["run_id"])
    return rows


def score_stage(target: str, workers: int) -> dict[str, Any]:
    facts = load_facts()
    items = [i for i in items_for(target) if i["paper_id"] in facts]
    folders = {j: OUT / "scores" / target / j for j in M.JUDGES}
    jobs = {j: [item for item in items if not (folders[j] / f"{item['run_id']}.json").exists()] for j in M.JUDGES}

    def job(judge: str, item: dict[str, Any]) -> None:
        atomic_json(folders[judge] / f"{item['run_id']}.json", score_one(item, facts[item["paper_id"]], judge))

    return M.interleaved(jobs, job, workers, f"checklist-{target}")


# ---------------------------------------------------------------- analysis and adoption rule

def load_scores(target: str, judge: str) -> dict[str, dict[str, Any]]:
    return {p.stem: _read_json(p) for p in sorted((OUT / "scores" / target / judge).glob("PMC*.json"))}


def old_scores(run_ids: list[str], judge: str) -> dict[str, float]:
    folder = "gpt56" if judge == "gpt56" else "deepseek"
    out = {}
    for rid in run_ids:
        method = rid.split("__")[2]
        path = M.E / "loop" / method / "judgments" / folder / f"{rid}.json"
        if path.exists():
            out[rid] = M.recon(_read_json(path)["scores"])
    return out


def unit_means(scores: dict[str, float]) -> dict[str, float]:
    groups: dict[str, list[float]] = defaultdict(list)
    for rid, value in scores.items():
        paper, level, method = rid.split("__")[:3]
        groups[f"{paper}__{level}__{method}"].append(value)
    return {k: statistics.fmean(v) for k, v in groups.items()}


def analyze() -> dict[str, Any]:
    result: dict[str, Any] = {}
    runs = {j: load_scores("runs", j) for j in M.JUDGES}
    common = sorted(r for r in set(runs["gpt56"]) & set(runs["deepseek"])
                    if runs["gpt56"][r]["checklist"] is not None and runs["deepseek"][r]["checklist"] is not None)
    new = {j: {r: runs[j][r]["checklist"] for r in common} for j in M.JUDGES}
    old = {j: old_scores(common, j) for j in M.JUDGES}
    both_old = sorted(set(old["gpt56"]) & set(old["deepseek"]))
    rho_new = A.spearman([new["gpt56"][r] for r in both_old], [new["deepseek"][r] for r in both_old])
    rho_old = A.spearman([old["gpt56"][r] for r in both_old], [old["deepseek"][r] for r in both_old])
    un = {j: unit_means({r: new[j][r] for r in both_old}) for j in M.JUDGES}
    uo = {j: unit_means({r: old[j][r] for r in both_old}) for j in M.JUDGES}
    keys = sorted(un["gpt56"])
    result["inter_judge"] = {"runs": len(both_old), "rho_run_checklist": rho_new, "rho_run_0to4": rho_old,
                             "rho_unit_checklist": A.spearman([un["gpt56"][k] for k in keys],
                                                              [un["deepseek"][k] for k in keys]),
                             "rho_unit_0to4": A.spearman([uo["gpt56"][k] for k in keys], [uo["deepseek"][k] for k in keys])}
    result["checklist_vs_0to4_same_judge"] = {j: A.spearman([new[j][r] for r in both_old], [old[j][r] for r in both_old])
                                              for j in M.JUDGES}
    retest = {j: load_scores("retest", j) for j in M.JUDGES}
    result["retest"] = {}
    for j in M.JUDGES:
        ids = sorted(r for r in retest[j] if r in runs[j] and retest[j][r]["checklist"] is not None
                     and runs[j][r]["checklist"] is not None)
        result["retest"][j] = {"runs": len(ids), "rho": A.spearman([runs[j][r]["checklist"] for r in ids],
                                                                    [retest[j][r]["checklist"] for r in ids]),
                               "mean_abs_diff": round(statistics.fmean(abs(runs[j][r]["checklist"] -
                                                                           retest[j][r]["checklist"]) for r in ids), 3)
                               if ids else None}
    controls = {j: load_scores("controls", j) for j in M.JUDGES}
    result["controls"] = {}
    for j in M.JUDGES:
        by: dict[str, list[float]] = defaultdict(list)
        for item_id, s in controls[j].items():
            if s["checklist"] is not None:
                by[item_id.split("__")[1]].append(s["checklist"])
        result["controls"][j] = {"means": {c: round(statistics.fmean(v), 3) for c, v in by.items()},
                                 "auc_positive_vs_negatives": M.auc(by.get("positive", []),
                                                                    by.get("hard_negative", []) +
                                                                    by.get("random_negative", []))}
    quote: Counter[str] = Counter()
    for j in M.JUDGES:
        for s in list(runs[j].values()) + list(controls[j].values()):
            quote.update(s["quote_stats"])
    claimed = quote["quote_exact"] + quote["quote_loose"] + quote["quote_none"]
    result["quotes"] = {**dict(quote), "unverifiable_share": round(quote["quote_none"] / max(1, claimed), 4)}
    old_auc = {}
    if (M.OUT / "measurement.json").exists():
        a3 = _read_json(M.OUT / "measurement.json").get("A3_controls", {})
        old_auc = {j: a3.get(j, {}).get("auc_positive_vs_negatives") for j in M.JUDGES}
    result["old_control_auc"] = old_auc
    rule = {"rho_gain_ge_0.15": rho_new is not None and rho_old is not None and rho_new - rho_old >= 0.15,
            "auc_not_lower_by_gt_0.02": all(old_auc.get(j) is not None and
                                            result["controls"][j]["auc_positive_vs_negatives"] is not None and
                                            result["controls"][j]["auc_positive_vs_negatives"] >= old_auc[j] - 0.02
                                            for j in M.JUDGES),
            "unverifiable_quotes_lt_10pct": result["quotes"]["unverifiable_share"] < 0.10}
    result["adoption"] = {**rule, "adopted": all(rule.values())}
    facts = load_facts()
    result["facts"] = {"papers": len(facts), "kept_mean": round(statistics.fmean(len(f["facts"]) for f in
                                                                                  facts.values()), 2) if facts else None,
                       "dropped_total": sum(len(f["dropped"]) for f in facts.values()),
                       "per_dimension": dict(Counter(x["dimension"] for f in facts.values() for x in f["facts"]))}
    atomic_json(OUT / "analysis.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("facts", "score", "analyze"))
    parser.add_argument("--target", choices=("controls", "runs", "retest", "phaseb", "test4"), default="controls")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if args.stage == "facts":
        extra = (M.E / "benchmark_test4" / "cases",) if args.target == "test4" else ()
        print(facts_stage(args.workers, extra))
    elif args.stage == "score":
        print(score_stage(args.target, args.workers))
    else:
        print(json.dumps(analyze(), indent=1))


if __name__ == "__main__":
    main()
