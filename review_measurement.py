"""Experiment 33 (loop.md 16.1): measurement checks suggested by two model reviews, run before any method changes.

Stages:
- output-audit: A1, offline. Format failures, abstentions, repairs and truncations, with their scores.
- controls-build, controls-judge: A3. Sanity controls built by code from the frozen answer keys, scored by both
  judges.
- triage: A5. Model, judge or answer-key error, for a stratified sample of scored runs.
- key-audit: A6. Each answer key checked against its paper.
- report: summary of A1, A2 (two-judge mean), A3, A5 and A6, written to review_eval/measurement.json.

Outputs go to experiments/high_temperature_hea_qwen35b/review_eval/.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import statistics
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

import llm_client as lc
import v4_scimon_analysis as A
from answer_render import render as render_answer_key
from hypothesis_evidence_v2 import atomic_json
from stage_metrics import CROSS_JUDGE
from temporal_eval_v3 import EXPERIMENT_DIR, PRIMARY_DIMENSIONS, judge_absolute
from temporal_hypothesis_benchmark import _SCORE_SYSTEM, _read_json, _validate_score

E = EXPERIMENT_DIR
OUT = E / "review_eval"
CASE_DIRS = (E / "benchmark_v3_1" / "cases", E / "benchmark_test2" / "cases", E / "benchmark_test3" / "cases")
PAPER_DIRS = (E / "outputs" / "papers", E / "benchmark_test2" / "papers", E / "benchmark_test3" / "papers",
              E / "benchmark_test4" / "papers")
LEVELS = ("broad", "problem_constrained", "expert_context")
TARGET_FIELDS = ("material_initial_state", "intervention", "conditions", "structural_mediator", "mechanism",
                 "predicted_outcome", "baseline", "boundary", "discriminating_measurement", "actual_result")
CONTROLS = ("positive", "hard_negative", "random_negative", "intervention_swap", "mechanism_swap", "generic")
SEED = 20261026
JUDGES = ("gpt56", "deepseek")


# ---------------------------------------------------------------- shared helpers

def held_out_cases(extra_dirs: tuple[Path, ...] = ()) -> dict[str, dict[str, Any]]:
    """The 36 held-out cases (v3.1 questions) keyed by paper id; extra_dirs adds later sets (test4)."""
    cases: dict[str, dict[str, Any]] = {}
    for directory in (*CASE_DIRS, *extra_dirs):
        for path in sorted(directory.glob("PMC*.json")):
            case = _read_json(path)
            cases.setdefault(case["paper_id"], case)
    return dict(sorted(cases.items()))


def paper_xml(paper_id: str) -> Path:
    for directory in PAPER_DIRS:
        path = directory / paper_id / "input" / "article.xml"
        if path.exists():
            return path
    raise FileNotFoundError(f"no article.xml for {paper_id}")


def paper_text(paper_id: str, limit: int = 30000) -> str:
    from benchmark_test2 import non_intro_text  # imported late: the builder module pulls in the query writer
    return non_intro_text(paper_xml(paper_id), limit=limit)


def gap_type(case: dict[str, Any]) -> str:
    gap = case.get("gap")
    value = gap.get("gap_type") if isinstance(gap, dict) else gap
    return value if value in ("design", "understanding", "method") else "design"


def recon(scores: dict[str, int]) -> float:
    return statistics.fmean(scores[d] for d in PRIMARY_DIMENSIONS)


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", str(text).lower()) if len(t) > 2}


def jaccard(a: str, b: str) -> float:
    x, y = _tokens(a), _tokens(b)
    return len(x & y) / len(x | y) if x | y else 0.0


def parallel(jobs: list[tuple[Any, ...]], fn: Callable[..., None], workers: int, label: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    with ThreadPoolExecutor(workers) as pool:
        futures = {pool.submit(fn, *job): job for job in jobs}
        for future in as_completed(futures):
            try:
                future.result()
                counts["done"] += 1
            except Exception as error:  # noqa: BLE001 - logged; the next call resumes
                counts["failed"] += 1
                print(f"[{label}] {type(error).__name__}: {str(error)[:200]}", flush=True)
    return {"jobs": len(jobs), **counts}


def interleaved(jobs_by_judge: dict[str, list[Any]], fn: Callable[[str, Any], None], workers: int,
                label: str) -> dict[str, int]:
    """Runs each judge's jobs in its own pool, at the same time, so the fast judge (DeepSeek) is not held up by the
    rate-limited one (GPT-5.6)."""
    with ThreadPoolExecutor(len(jobs_by_judge)) as outer:
        futures = {j: outer.submit(parallel, [(j, item) for item in items], fn, workers, f"{label}-{j}")
                   for j, items in jobs_by_judge.items()}
        results = {j: f.result() for j, f in futures.items()}
    return {f"{j}_{k}": v for j, r in results.items() for k, v in r.items()}


def deepseek_json(system: str, payload: dict[str, Any], max_tokens: int = 8000) -> Any:
    return lc.trapi_chat_json(CROSS_JUDGE["deployment"], system, json.dumps(payload, ensure_ascii=False),
                              max_tokens=max_tokens, token_field=CROSS_JUDGE["token_field"],
                              temperature=CROSS_JUDGE["temperature"], retries=6)


def gpt_json(system: str, payload: dict[str, Any], max_tokens: int = 16000) -> Any:
    return lc.judge_chat_json(system, json.dumps(payload, ensure_ascii=False), max_tokens=max_tokens)


# ---------------------------------------------------------------- A1 output audit (offline)

ABSTAIN = re.compile(r"\b(unknown|cannot be determined|can ?not be determined|insufficient (evidence|information)|"
                     r"lack of evidence|not enough (evidence|information)|no (specific )?(evidence|information) "
                     r"(is )?available)\b", re.IGNORECASE)
CORE = ("hypothesis", "intervention", "mechanism")


def run_flags(run: dict[str, Any]) -> dict[str, bool]:
    if run.get("status") != "ok":
        return {"failed": True}
    g = run.get("generation") or {}
    text = " ".join(str(g.get(k, "")) for k in ("hypothesis", "intervention"))
    models = run.get("models") or {}
    return {"failed": False,
            "empty_core": any(not str(g.get(k, "") or "").strip() for k in CORE),
            "short": len(str(g.get("hypothesis", "") or "").strip()) < 40,
            "abstention": bool(ABSTAIN.search(text)),
            "repair": any("repair" in k for k in models),
            "truncation_retry": any(t.get("event") == "truncated" for t in run.get("trace", []))}


def _score_for(run_path: Path) -> float | None:
    base = run_path.parent.parent
    for folder in ("judgments/gpt56", "judgments/absolute"):
        path = base / folder / run_path.name
        if path.exists():
            try:
                return recon(_read_json(path)["scores"])
            except (KeyError, TypeError):
                return None
    return None


def run_dirs() -> list[tuple[str, Path]]:
    dirs: list[tuple[str, Path]] = []
    for root, label in ((E / "loop", "loop"), (E / "loop_v4_scimon", "loop_v4")):
        dirs += [(f"{label}:{p.parent.name}", p) for p in sorted(root.glob("*/runs"))]
    for root, label in ((E / "rerun_v3", "suite_v3"), (E / "rerun_v4_scimon", "suite_v4")):
        for sub in ("eval_v3", "eval_v4_matkg", "eval_critique/baseline_resample", "rubric_eval", "improvements",
                    "citegraph"):
            if (root / sub / "runs").exists():
                dirs.append((f"{label}:{sub}", root / sub / "runs"))
    return dirs


def output_audit() -> dict[str, Any]:
    per: dict[str, Any] = {}
    for name, directory in run_dirs():
        counts: Counter[str] = Counter()
        flagged_scores: dict[str, list[float]] = defaultdict(list)
        clean_scores: list[float] = []
        for path in sorted(directory.glob("PMC*.json")):
            run = _read_json(path)
            flags = run_flags(run)
            counts["runs"] += 1
            for key, value in flags.items():
                counts[key] += int(value)
            score = _score_for(path) if not flags["failed"] else None
            if score is None:
                continue
            bad = [k for k in ("empty_core", "short", "abstention") if flags.get(k)]
            for key in bad:
                flagged_scores[key].append(score)
            if not bad:
                clean_scores.append(score)
        entry: dict[str, Any] = dict(counts)
        entry["format_failure_share"] = round((counts["empty_core"] + counts["truncation_retry"]) /
                                              max(1, counts["runs"]), 4)
        entry["mean_score_clean"] = round(statistics.fmean(clean_scores), 3) if clean_scores else None
        entry["mean_score_flagged"] = {k: round(statistics.fmean(v), 3) for k, v in flagged_scores.items() if v}
        per[name] = entry
    claimed = [k for k in per if k.split(":")[1] in ("closed_book", "writer_only_b_o3mini")]
    action = {k: per[k]["format_failure_share"] for k in claimed if per[k]["format_failure_share"] > 0.02}
    result = {"per_directory": per, "claimed_directories_over_2pct": action,
              "totals": dict(sum((Counter({k: v for k, v in e.items() if isinstance(v, int)}) for e in per.values()),
                                 Counter()))}
    atomic_json(OUT / "output_audit.json", result)
    return result


# ---------------------------------------------------------------- A3 judge sanity controls

GENERIC = {
    "design": {
        "hypothesis": "Adding an oxide-forming element (Al or Cr) to the high-entropy alloy will form a continuous "
                      "protective oxide scale and improve its high-temperature performance relative to the base "
                      "alloy.",
        "material_initial_state": "The base high-entropy alloy in the as-cast state.",
        "intervention": "Alloying with 5-10 at.% Al or Cr.",
        "conditions": "Isothermal exposure at 1000 C in air.",
        "structural_mediator": "A continuous, adherent Al2O3 or Cr2O3 scale.",
        "mechanism": "Selective oxidation forms a slow-growing protective scale that limits oxygen ingress.",
        "predicted_outcome": "Lower mass gain and slower degradation than the base alloy.",
        "baseline": "The base alloy without the addition.",
        "boundary": "Holds while the scale stays continuous and adherent."},
    "understanding": {
        "hypothesis": "The observed behaviour is controlled by thermally activated diffusion and the stability of "
                      "the solid-solution phase, which microstructural analysis before and after exposure will "
                      "reveal.",
        "material_initial_state": "The high-entropy alloy as processed.",
        "intervention": "Systematic characterisation after exposure at several temperatures.",
        "conditions": "Exposure between 600 and 1200 C.",
        "structural_mediator": "Phase decomposition and precipitation.",
        "mechanism": "Sluggish diffusion and lattice distortion change with temperature and alter phase stability.",
        "predicted_outcome": "Property changes coincide with the onset of phase decomposition.",
        "baseline": "The as-processed alloy.",
        "boundary": "Holds within the temperature range studied."},
    "method": {
        "hypothesis": "Combining CALPHAD thermodynamic modelling with targeted experiments will predict the "
                      "high-temperature behaviour of the alloy more reliably than trial-and-error testing.",
        "material_initial_state": "Candidate high-entropy alloy compositions.",
        "intervention": "A CALPHAD-guided design and validation workflow.",
        "conditions": "Predictions validated at 800-1200 C.",
        "structural_mediator": "Predicted phase fractions and stability ranges.",
        "mechanism": "Thermodynamic databases capture the phase equilibria that govern high-temperature behaviour.",
        "predicted_outcome": "Better agreement between predicted and measured phases than empirical screening.",
        "baseline": "Empirical trial-and-error screening.",
        "boundary": "Holds where the thermodynamic database is reliable."},
}


def render(target: dict[str, Any]) -> dict[str, Any]:
    """An answer key rendered into the generator's output schema by code (no LLM)."""
    return render_answer_key(target)


def generic_hypothesis(kind: str) -> dict[str, Any]:
    g = dict(GENERIC[kind])
    return {**g, "uncertainty": "", "supporting_evidence_ids": [], "conflicting_evidence_ids": [],
            "falsification_experiment": {"design": "Compare treated and reference samples under the stated "
                                                   "conditions.", "measurements": ["the property of interest"],
                                         "falsification_rule": "No improvement over the baseline rejects it."}}


def similarity_key(target: dict[str, Any]) -> str:
    return " ".join(str(target.get(k, "")) for k in ("material_initial_state", "intervention", "mechanism"))


def build_controls(cases: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    ids = sorted(cases)
    items = []
    for pid in ids:
        case = cases[pid]
        target = case["hidden_target"]
        others = [o for o in ids if o != pid]
        hard = max(others, key=lambda o: (jaccard(similarity_key(target), similarity_key(cases[o]["hidden_target"])),
                                          o))
        rand = rng.choice([o for o in others if o != hard])
        positive = render(target)
        hard_t = cases[hard]["hidden_target"]
        int_swap = render({**target, "intervention": hard_t.get("intervention", "")})
        mech_swap = render({**target, "mechanism": hard_t.get("mechanism", ""),
                            "structural_mediator": hard_t.get("structural_mediator", "")})
        built = {"positive": (positive, pid), "hard_negative": (render(hard_t), hard),
                 "random_negative": (render(cases[rand]["hidden_target"]), rand),
                 "intervention_swap": (int_swap, hard), "mechanism_swap": (mech_swap, hard),
                 "generic": (generic_hypothesis(gap_type(case)), "generic")}
        for control in CONTROLS:
            generation, source = built[control]
            items.append({"run_id": f"{pid}__{control}", "paper_id": pid, "control": control, "source": source,
                          "query": case["queries"]["problem_constrained"]["text"], "query_level":
                          "problem_constrained", "generation": generation, "cited_evidence": []})
    return items


def controls_build() -> dict[str, int]:
    items = build_controls(held_out_cases())
    for item in items:
        atomic_json(OUT / "controls" / "items" / f"{item['run_id']}.json", item)
    return {"items": len(items)}


def load_controls() -> list[dict[str, Any]]:
    return [_read_json(p) for p in sorted((OUT / "controls" / "items").glob("PMC*.json"))]


def judge_04(item: dict[str, Any], case: dict[str, Any], judge: str) -> dict[str, Any]:
    """The study's 0-4 judges, unchanged: GPT-5.6 via judge_absolute, DeepSeek with the cross-judge payload."""
    if judge == "gpt56":
        return judge_absolute(item, case)
    from temporal_eval_v3 import _blind_candidate
    generation, evidence = _blind_candidate(item)
    raw = deepseek_json(_SCORE_SYSTEM, {"query": item["query"], "hidden_target": case["hidden_target"],
                                        "generated_hypothesis": generation, "cited_evidence": evidence})
    score = _validate_score(raw)
    return {"run_id": item["run_id"], "judge": f"trapi:{CROSS_JUDGE['deployment']}", "scores": score["scores"],
            "classification": score.get("classification", "")}


def controls_judge(workers: int) -> dict[str, Any]:
    cases = held_out_cases()
    folders = {j: OUT / "controls" / "judgments" / j for j in JUDGES}
    jobs = {j: [item for item in load_controls() if not (folders[j] / f"{item['run_id']}.json").exists()]
            for j in JUDGES}

    def job(judge: str, item: dict[str, Any]) -> None:
        atomic_json(folders[judge] / f"{item['run_id']}.json", judge_04(item, cases[item["paper_id"]], judge))

    return interleaved(jobs, job, workers, "controls")


def auc(positives: list[float], negatives: list[float]) -> float | None:
    if not positives or not negatives:
        return None
    wins = sum((p > n) + 0.5 * (p == n) for p in positives for n in negatives)
    return round(wins / (len(positives) * len(negatives)), 3)


def controls_summary(scores: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    """scores[judge][item_id] = judgment (with 'scores'). Applies the pre-registered checks C1-C4 per judge."""
    out: dict[str, Any] = {}
    for judge, items in scores.items():
        by: dict[str, dict[str, dict[str, int]]] = defaultdict(dict)
        for item_id, judgment in items.items():
            pid, control = item_id.split("__")
            by[control][pid] = judgment["scores"]
        means = {c: round(statistics.fmean(recon(s) for s in by[c].values()), 3) for c in CONTROLS if by.get(c)}
        pos = [recon(s) for s in by.get("positive", {}).values()]
        neg = [recon(s) for c in ("hard_negative", "random_negative") for s in by.get(c, {}).values()]

        def drop(control: str, dim: str) -> float | None:
            pairs = [(by["positive"][p][dim], by[control][p][dim]) for p in by.get(control, {}) if p in by["positive"]]
            return round(statistics.fmean(a - b for a, b in pairs), 3) if pairs else None
        swaps = {c: {"intervention_drop": drop(c, "intervention_reconstruction"),
                     "mechanism_drop": drop(c, "mechanism_agreement")} for c in ("intervention_swap", "mechanism_swap")
                 if by.get(c) and by.get("positive")}
        c1 = auc(pos, neg)
        checks = {"C1_auc_ge_0.90": c1 is not None and c1 >= 0.90,
                  "C2_positive_ge_3_and_random_le_1": means.get("positive", 0) >= 3.0 and means.get(
                      "random_negative", 4) <= 1.0,
                  "C3_swaps_hit_their_dimension": bool(swaps) and all(v is not None for s in swaps.values()
                                                                      for v in s.values())
                  and swaps["intervention_swap"]["intervention_drop"] > swaps["intervention_swap"]["mechanism_drop"]
                  and swaps["mechanism_swap"]["mechanism_drop"] > swaps["mechanism_swap"]["intervention_drop"],
                  "C4_generic_2_below_positive": means.get("positive", 0) - means.get("generic", 4) >= 2.0}
        out[judge] = {"n": {c: len(by.get(c, {})) for c in CONTROLS}, "means": means, "auc_positive_vs_negatives": c1,
                      "swap_drops": swaps, "checks": checks}
    return out


# ---------------------------------------------------------------- A5 failure triage

TRIAGE_SYSTEM = (
    "You audit one scored item of a materials-science hypothesis benchmark. A model proposed a hypothesis for a "
    "research question, and two AI judges scored how well it reconstructs the paper's actual study (0-4 per "
    "dimension; reconstruction = mean of intervention, conditions, mechanism and outcome agreement). You see the "
    "paper's abstract and non-introduction sections, the benchmark's answer key extracted from that paper, the "
    "question, the hypothesis and the judges' scores. Decide the main reason for the score. Categories: "
    "answer_key_error (the answer key misstates or omits what the paper did, and this changes the score); "
    "judge_too_harsh (the hypothesis matches the paper more than the scores credit); judge_too_lenient (the scores "
    "credit content the hypothesis does not have); valid_alternative (a scientifically reasonable hypothesis for the "
    "question that the paper simply did not test); wrong (contradicted by the paper or by established materials "
    "science); generic (too vague to test, or not specific to this question); fairly_scored (the scores are about "
    "right and none of the above dominates). Return JSON {\"primary_cause\": one category, \"fair_reconstruction\": "
    "your own reconstruction score from 0 to 4 with one decimal, \"answer_key_ok\": true or false, \"reason\": one or "
    "two sentences}."
)
TRIAGE_CAUSES = ("answer_key_error", "judge_too_harsh", "judge_too_lenient", "valid_alternative", "wrong", "generic",
                 "fairly_scored")
HYPOTHESIS_KEYS = ("hypothesis", "material_initial_state", "intervention", "conditions", "structural_mediator",
                   "mechanism", "predicted_outcome", "baseline", "boundary", "falsification_experiment")


def scored_runs(method: str) -> list[dict[str, Any]]:
    base = E / "loop" / method
    rows = []
    for path in sorted((base / "runs").glob("PMC*.json")):
        run = _read_json(path)
        if run.get("status") != "ok" or run["query_level"] not in LEVELS or \
                run.get("benchmark", "v3.1") not in ("v3.1", "test2", "test3"):
            continue
        g, d = base / "judgments" / "gpt56" / path.name, base / "judgments" / "deepseek" / path.name
        if g.exists() and d.exists():
            rows.append({"run": run, "gpt": recon(_read_json(g)["scores"]), "deep": recon(_read_json(d)["scores"]),
                         "gpt_scores": _read_json(g)["scores"]})
    return rows


def _take(rows: list[dict[str, Any]], key: Callable[[dict[str, Any]], Any], n: int, per_paper: int,
          taken: set[str]) -> list[dict[str, Any]]:
    chosen: list[dict[str, Any]] = []
    count: Counter[str] = Counter()
    for row in sorted(rows, key=key):
        rid, pid = row["run"]["run_id"], row["run"]["paper_id"]
        if rid in taken or count[pid] >= per_paper:
            continue
        chosen.append(row)
        taken.add(rid)
        count[pid] += 1
        if len(chosen) == n:
            break
    return chosen


def triage_sample() -> list[dict[str, Any]]:
    writer, llama = scored_runs("writer_only_b_o3mini"), scored_runs("closed_book")
    taken: set[str] = set()
    median = statistics.median(r["gpt"] for r in writer)
    strata = [("writer_low", _take(writer, lambda r: (r["gpt"], r["run"]["run_id"]), 24, 2, taken)),
              ("llama_low", _take(llama, lambda r: (r["gpt"], r["run"]["run_id"]), 12, 1, taken)),
              ("writer_high", _take(writer, lambda r: (-r["gpt"], r["run"]["run_id"]), 12, 2, taken)),
              ("writer_mid", _take(writer, lambda r: (abs(r["gpt"] - median), r["run"]["run_id"]), 12, 1, taken))]
    return [{**row, "stratum": name} for name, rows in strata for row in rows]


def triage(workers: int) -> dict[str, Any]:
    cases = held_out_cases()
    sample = triage_sample()
    atomic_json(OUT / "triage" / "sample.json", [{"run_id": r["run"]["run_id"], "method": r["run"]["method"],
                                                  "stratum": r["stratum"], "gpt56": r["gpt"], "deepseek": r["deep"]}
                                                 for r in sample])
    texts: dict[str, str] = {}
    folders = {j: OUT / "triage" / j for j in JUDGES}
    jobs = {j: [row for row in sample if not (folders[j] / f"{row['run']['run_id']}.json").exists()] for j in JUDGES}

    def job(judge: str, row: dict[str, Any]) -> None:
        run = row["run"]
        pid = run["paper_id"]
        if pid not in texts:
            texts[pid] = paper_text(pid)
        payload = {"paper_without_introduction": texts[pid], "answer_key": cases[pid]["hidden_target"],
                   "question": run["query"],
                   "hypothesis": {k: run["generation"].get(k) for k in HYPOTHESIS_KEYS},
                   "judge_scores": {"judge_1_reconstruction": round(row["gpt"], 2),
                                    "judge_1_dimensions": {d: row["gpt_scores"][d] for d in PRIMARY_DIMENSIONS},
                                    "judge_2_reconstruction": round(row["deep"], 2)}}
        raw = gpt_json(TRIAGE_SYSTEM, payload) if judge == "gpt56" else deepseek_json(TRIAGE_SYSTEM, payload)
        cause = str(raw.get("primary_cause", "")).strip() if isinstance(raw, dict) else ""
        if cause not in TRIAGE_CAUSES:
            raise ValueError(f"invalid triage cause {cause!r}")
        try:
            fair = max(0.0, min(4.0, float(raw.get("fair_reconstruction"))))
        except (TypeError, ValueError):
            fair = None
        atomic_json(folders[judge] / f"{run['run_id']}.json",
                    {"run_id": run["run_id"], "triager": "trapi:" + (lc.JUDGE_TRAPI_DEPLOYMENT if judge == "gpt56"
                                                                     else CROSS_JUDGE["deployment"]),
                     "stratum": row["stratum"], "primary_cause": cause, "fair_reconstruction": fair,
                     "answer_key_ok": bool(raw.get("answer_key_ok", True)), "reason": str(raw.get("reason", ""))})

    return interleaved(jobs, job, workers, "triage")


def kappa(a: list[str], b: list[str]) -> float | None:
    if not a or len(a) != len(b):
        return None
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return round((observed - expected) / (1 - expected), 3) if expected < 1 else None


def triage_summary() -> dict[str, Any]:
    results = {j: {p.stem: _read_json(p) for p in sorted((OUT / "triage" / j).glob("PMC*.json"))} for j in JUDGES}
    common = sorted(set(results["gpt56"]) & set(results["deepseek"]))
    out: dict[str, Any] = {"items": len(common),
                           "kappa_primary_cause": kappa([results["gpt56"][r]["primary_cause"] for r in common],
                                                        [results["deepseek"][r]["primary_cause"] for r in common])}
    measurement = ("answer_key_error", "judge_too_harsh", "judge_too_lenient")
    for judge in JUDGES:
        rows = [results[judge][r] for r in common]
        by_stratum: dict[str, Counter[str]] = defaultdict(Counter)
        for row in rows:
            by_stratum[row["stratum"]][row["primary_cause"]] += 1
        low = [r for r in rows if r["stratum"] in ("writer_low", "llama_low")]
        out[judge] = {"causes": dict(Counter(r["primary_cause"] for r in rows)),
                      "by_stratum": {k: dict(v) for k, v in by_stratum.items()},
                      "low_score_share_measurement": round(sum(r["primary_cause"] in measurement for r in low) /
                                                           max(1, len(low)), 3),
                      "low_score_share_valid_alternative": round(sum(r["primary_cause"] == "valid_alternative"
                                                                     for r in low) / max(1, len(low)), 3),
                      "answer_key_not_ok": sum(not r["answer_key_ok"] for r in rows)}
    return out


# ---------------------------------------------------------------- A6 answer-key audit

KEY_AUDIT_SYSTEM = (
    "You check the hidden answer key of a materials-science benchmark case against the paper it was extracted from. "
    "You see the paper's abstract and its sections other than the Introduction, and the answer-key fields. For each "
    "field, judge whether the paper supports it: supported; partial (partly right, imprecise, or missing an "
    "essential element); unsupported (not in the paper, or contradicted); empty_ok (left empty, and the paper indeed "
    "gives no such information). Also judge central_lever: does the intervention field describe the paper's central "
    "manipulated variable or study (yes, partly, no)? Give an overall verdict: ok (fit for scoring); minor (small "
    "errors that would not change scores much); major (errors in the intervention, mechanism or outcome that would "
    "mislead a judge). Return JSON {\"fields\": {field name: verdict}, \"central_lever\": \"yes|partly|no\", "
    "\"overall\": \"ok|minor|major\", \"issues\": [short strings]}."
)
FIELD_VERDICTS = ("supported", "partial", "unsupported", "empty_ok")


def key_audit(workers: int, extra_dirs: tuple[Path, ...] = (), subdir: str = "key_audit") -> dict[str, Any]:
    cases = held_out_cases(extra_dirs)
    if extra_dirs:
        wanted = {_read_json(p)["paper_id"] for d in extra_dirs for p in d.glob("PMC*.json")}
        cases = {k: v for k, v in cases.items() if k in wanted}
    folders = {j: OUT / subdir / j for j in JUDGES}
    jobs = {j: [pid for pid in cases if not (folders[j] / f"{pid}.json").exists()] for j in JUDGES}

    def job(judge: str, pid: str) -> None:
        payload = {"paper_without_introduction": paper_text(pid, limit=45000),
                   "answer_key": {f: cases[pid]["hidden_target"].get(f, "") for f in TARGET_FIELDS}}
        raw = gpt_json(KEY_AUDIT_SYSTEM, payload) if judge == "gpt56" else deepseek_json(KEY_AUDIT_SYSTEM, payload)
        if not isinstance(raw, dict) or raw.get("overall") not in ("ok", "minor", "major"):
            raise ValueError(f"{pid}: invalid key audit")
        fields = {f: (str(raw.get("fields", {}).get(f, "")).strip().lower()) for f in TARGET_FIELDS}
        fields = {f: (v if v in FIELD_VERDICTS else "partial") for f, v in fields.items()}
        atomic_json(folders[judge] / f"{pid}.json", {"paper_id": pid, "auditor": "trapi:" + (
            lc.JUDGE_TRAPI_DEPLOYMENT if judge == "gpt56" else CROSS_JUDGE["deployment"]), "fields": fields,
            "central_lever": str(raw.get("central_lever", "")), "overall": raw["overall"],
            "issues": [str(i) for i in raw.get("issues", [])][:10]})

    return interleaved(jobs, job, workers, "key-audit")


def flagged(gpt: dict[str, Any], deep: dict[str, Any]) -> bool:
    """Pre-registered flag (loop.md 16.1, A6): major by both auditors, or major by one with an unsupported
    intervention or mechanism from the other."""
    if gpt["overall"] == "major" and deep["overall"] == "major":
        return True
    for a, b in ((gpt, deep), (deep, gpt)):
        if a["overall"] == "major" and any(b["fields"].get(f) == "unsupported" for f in ("intervention", "mechanism")):
            return True
    return False


def key_audit_summary(subdir: str = "key_audit") -> dict[str, Any]:
    res = {j: {p.stem: _read_json(p) for p in sorted((OUT / subdir / j).glob("PMC*.json"))} for j in JUDGES}
    common = sorted(set(res["gpt56"]) & set(res["deepseek"]))
    out: dict[str, Any] = {"papers": len(common),
                           "flagged": [p for p in common if flagged(res["gpt56"][p], res["deepseek"][p])]}
    for judge in JUDGES:
        rows = [res[judge][p] for p in common]
        out[judge] = {"overall": dict(Counter(r["overall"] for r in rows)),
                      "central_lever": dict(Counter(r["central_lever"] for r in rows)),
                      "field_verdicts": {f: dict(Counter(r["fields"][f] for r in rows)) for f in TARGET_FIELDS}}
    out["kappa_overall"] = kappa([res["gpt56"][p]["overall"] for p in common],
                                 [res["deepseek"][p]["overall"] for p in common])
    return out


# ---------------------------------------------------------------- A2 two-judge mean and the report

def split_papers() -> dict[str, set[str]]:
    groups: dict[str, set[str]] = defaultdict(set)
    for pid, case in held_out_cases().items():
        groups[case["split"] if case["split"] in ("test", "test2", "test3") else "dev"].add(pid)
    groups["fresh28"] = groups["test"] | groups["test2"] | groups["test3"]
    groups["all36"] = set(held_out_cases())
    return groups


def two_judge(root: Path, method: str, levels: tuple[str, ...]) -> dict[str, dict[str, float]]:
    data = {j: A.per_paper(A.load(root, method, j, A.recon, levels)) for j in ("gpt", "deep")}
    both = sorted(set(data["gpt"]) & set(data["deep"]))
    return {"gpt": data["gpt"], "deep": data["deep"], "mean": {p: (data["gpt"][p] + data["deep"][p]) / 2
                                                               for p in both}}


def combined_report() -> dict[str, Any]:
    groups = split_papers()
    v31 = {m: two_judge(A.V31_ROOT, m, A.V31_LEVELS) for m in ("writer_only_b_o3mini", "closed_book")}
    v4 = {m: two_judge(A.V4_ROOT, m, ("scimon",)) for m in ("writer_only_b_o3mini", "closed_book")}
    out: dict[str, Any] = {}
    for name in ("test", "test2", "test3", "fresh28", "all36"):
        out[f"v3.1_{name}"] = {k: A.paired(v31["writer_only_b_o3mini"][k], v31["closed_book"][k], groups[name])
                               for k in ("gpt", "deep", "mean")}
    out["v4_all36"] = {k: A.paired(v4["writer_only_b_o3mini"][k], v4["closed_book"][k]) for k in ("gpt", "deep",
                                                                                                  "mean")}
    return out


def report() -> dict[str, Any]:
    result: dict[str, Any] = {}
    if (OUT / "output_audit.json").exists():
        audit = _read_json(OUT / "output_audit.json")
        result["A1_output_audit"] = {"totals": audit["totals"],
                                     "claimed_directories_over_2pct": audit["claimed_directories_over_2pct"]}
    result["A2_two_judge_mean"] = combined_report()
    scores = {j: {p.stem: _read_json(p) for p in sorted((OUT / "controls" / "judgments" / j).glob("PMC*.json"))}
              for j in JUDGES}
    if all(scores.values()):
        result["A3_controls"] = controls_summary(scores)
    if any((OUT / "triage" / j).exists() for j in JUDGES):
        result["A5_triage"] = triage_summary()
    if any((OUT / "key_audit" / j).exists() for j in JUDGES):
        result["A6_key_audit"] = key_audit_summary()
    atomic_json(OUT / "measurement.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("output-audit", "controls-build", "controls-judge", "triage", "key-audit",
                                          "report"))
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if args.stage == "output-audit":
        result = output_audit()
        print(json.dumps({"totals": result["totals"], "over_2pct": result["claimed_directories_over_2pct"]}))
    elif args.stage == "controls-build":
        print(controls_build())
    elif args.stage == "controls-judge":
        print(controls_judge(args.workers))
    elif args.stage == "triage":
        print(triage(args.workers))
    elif args.stage == "key-audit":
        print(key_audit(args.workers))
    else:
        print(json.dumps(report(), indent=1)[:6000])


if __name__ == "__main__":
    main()
