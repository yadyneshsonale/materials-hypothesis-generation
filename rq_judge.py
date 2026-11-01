"""Experiment 43 (loop.md 24.1): research quality (RQ) on the expert's blind Part-1 scales, judged by o1 and DeepSeek.

RQ is a target-free measure of hypothesis quality, not of agreement with the paper. The judge sees what the expert
sees: the research question and the hypothesis as rendered in the expert package (`expert_eval_builder`), with no
citations, no evidence and no answer key. It rates plausibility, testability and usefulness (1-5, the expert's
anchors verbatim); RQ = their mean minus 1, on 0-4.

Stages (resumable; MATHG_PENDING_SHUFFLE=<seed> or MATHG_PENDING_REVERSE=1 give another job order):
  python rq_judge.py controls --judge J              the 216 sanity controls of experiment 33
  python rq_judge.py expert --judge J                the 60 expert-package items
  python rq_judge.py retest --judge J                the 135 sample-1 writer runs, judged a second time
  python rq_judge.py runs --judge J --method M ...   every run of the given configurations
  python rq_judge.py report                          loop_rq/analysis_rq.json and analysis_rq.md
J = o1 or deepseek (gpt56 is possible but capacity-limited).
"""

from __future__ import annotations

import os

_E = os.path.join(os.path.dirname(os.path.abspath(__file__)), "experiments", "high_temperature_hea_qwen35b")
os.environ.setdefault("MATHG_CASES_DIR", os.path.join(_E, "benchmark_v3_1", "cases"))
os.environ.setdefault("MATHG_LOOP_ROOT", os.path.join(_E, "loop_rq"))

import argparse  # noqa: E402
import json  # noqa: E402
import random  # noqa: E402
import statistics  # noqa: E402
from collections import defaultdict  # noqa: E402
from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

import expert_eval_builder as B  # noqa: E402
import hypo_loop as H  # noqa: E402
import llm_client as lc  # noqa: E402
import review_measurement as RM  # noqa: E402
import round4_offline as R  # noqa: E402
import web_analysis as W  # noqa: E402
from hypothesis_evidence_v2 import atomic_json  # noqa: E402
from stage_metrics import CROSS_JUDGE  # noqa: E402
from temporal_hypothesis_benchmark import _read_json  # noqa: E402

A, V = W.A, W.V
E = Path(_E)
OUT = E / "loop_rq"
RQ_DIR = OUT / "rq"
O1 = "o1_2024-12-17"
SCALES = ("plausibility", "testability", "usefulness")
JUDGES = ("o1", "deepseek")
WRITER = "writer_only_b_o3mini"
PHASE_B = ("writer_only_b_o3mini", "web_text_64k_b_o3mini", "web64k_v2_b_o3mini", "writer_study_b_o3mini",
           "closed_book", "closed_book_o3mini")
REFERENCE = "oracle_hint_full_b_o3mini"  # the authors' study written by the same writer: a reference, not a method
ROOTS = {"writer_only_b_o3mini": "loop", "closed_book": "loop", "closed_book_o3mini": "loop",
         "web_text_64k_b_o3mini": "loop_web", "web64k_v2_b_o3mini": "loop_v2", "writer_study_b_o3mini": "loop_study",
         "oracle_hint_full_b_o3mini": "loop_diag"}
TARGET = 2.5

# The expert package's Part 1 instructions (expert_evaluation/1_read_first/README.md), verbatim where they define the
# fields and the three scales. Fixed in loop.md 24.1 before any call.
RQ_SYSTEM = """You are an experienced materials scientist rating research hypotheses on high-temperature high-entropy alloys.

What the AI systems were asked to do: each system saw only the research question, not the paper. It had to propose one hypothesis that answers the question, in a fixed structure:
- Main hypothesis: the proposal in one or two sentences.
- Starting material: the alloy or material and its state before the change (as cast, annealed, coating, ...).
- What is changed or studied: the intervention: a composition change, a process, a heat treatment, a coating, or, for some questions, the study or simulation to be done.
- Conditions: processing, test or simulation conditions (temperature, time, atmosphere, loading, ...).
- Structure through which it acts: the microstructural or structural feature that mediates the effect (phases, precipitates, grain boundaries, defects, ordering, ...).
- Mechanism: why the change should produce the effect.
- Predicted outcome: what should happen to the property, compared with the baseline.
- Compared with (baseline): the reference condition the prediction is compared with.
- Where it should hold (boundary): the range of materials or conditions where the prediction should apply.
- Main uncertainty: what could make the hypothesis wrong.
- Test that would falsify it: an experiment or simulation, and the result that would prove the hypothesis wrong.
A field shown as "—" was left empty by its author. Rate the hypothesis on what is there.

Rate the hypothesis on three separate aspects. They are independent: a hypothesis can be plausible but hard to test, or testable but not useful.

Plausibility (1-5): is it scientifically sound for this material and these conditions?
1 = Physically wrong, or contradicts well-established knowledge
2 = Doubtful: major scientific problems
3 = Possible, but with notable gaps or questionable steps
4 = Sound, with minor issues
5 = Fully sound and convincing

Testability (1-5): could it be clearly tested, and would the proposed test decide it?
1 = Cannot be tested as written, or too vague to test
2 = A test is mentioned, but it would not really decide the question
3 = Testable, but the test is weak, incomplete or impractical
4 = Clear, feasible test with minor gaps
5 = Clear, feasible test with a decisive criterion for proving it wrong

Usefulness (1-5): would it help a researcher working on exactly this question?
1 = Not useful: off-topic, trivial or wrong
2 = Of little use
3 = Moderately useful
4 = Useful: worth testing
5 = Very useful: I would want to see it tested

Length or the number of details does not make a hypothesis better in itself.

Return JSON: {"plausibility_reason": "one sentence", "plausibility": integer 1-5, "testability_reason": "one sentence", "testability": integer 1-5, "usefulness_reason": "one sentence", "usefulness": integer 1-5}. Give each reason before its score."""


# ---------------------------------------------------------------- payload, judge, validation

def render(generation: dict[str, Any]) -> str:
    """The hypothesis exactly as the expert package shows it, without the 'Hypothesis A' heading."""
    return "\n".join(B.render_hypothesis("", H._schema_only(generation))[2:]).strip()


def payload(query: str, generation: dict[str, Any]) -> str:
    text = json.dumps({"research_question": query, "hypothesis": render(generation)}, ensure_ascii=False)
    if "hidden_target" in text or "supporting_evidence_ids" in text:
        raise H.TargetLeak("RQ payload must contain only the question and the rendered hypothesis")
    return text


def validate(raw: Any) -> dict[str, Any] | None:
    """The three integer scores and their reasons, or None if any score is missing or out of range."""
    if not isinstance(raw, dict):
        return None
    scores, reasons = {}, {}
    for scale in SCALES:
        try:
            value = int(raw.get(scale))
        except (TypeError, ValueError):
            return None
        if not 1 <= value <= 5 or float(raw.get(scale)) != value:
            return None
        scores[scale] = value
        reasons[scale] = str(raw.get(f"{scale}_reason", ""))[:600]
    return {"scores": scores, "reasons": reasons}


def rq(scores: dict[str, int]) -> float:
    return statistics.fmean(scores[s] for s in SCALES) - 1.0


def call(judge: str, user: str) -> Any:
    if judge == "o1":
        return lc.trapi_chat_json(O1, RQ_SYSTEM, user, max_tokens=16000, token_field="max_completion_tokens",
                                  temperature=None, retries=8)
    if judge == "deepseek":
        return lc.trapi_chat_json(CROSS_JUDGE["deployment"], RQ_SYSTEM, user, max_tokens=4000,
                                  token_field=CROSS_JUDGE["token_field"], temperature=CROSS_JUDGE["temperature"],
                                  retries=8)
    if judge == "gpt56":
        return lc.judge_chat_json(RQ_SYSTEM, user, max_tokens=8000)
    raise ValueError(f"unknown RQ judge {judge!r}")


def judge(judge_name: str, query: str, generation: dict[str, Any], attempts: int = 3) -> dict[str, Any]:
    user = payload(query, generation)
    for attempt in range(attempts):
        result = validate(call(judge_name, user))
        if result is not None:
            return {"judge": judge_name, **result, "rq": round(rq(result["scores"]), 4), "attempts": attempt + 1}
    raise lc.LLMError(f"RQ judge {judge_name} gave no valid scores in {attempts} attempts")


# ---------------------------------------------------------------- items

def root_of(method: str) -> Path:
    return E / ROOTS[method] if method in ROOTS else OUT


def runs_of(method: str) -> list[dict[str, Any]]:
    return [r for r in W.runs(root_of(method), method) if r.get("status") == "ok"
            and r.get("benchmark", "v3.1") in R.BENCHMARKS]


def path_of(kind: str, name: str, judge_name: str, item: str) -> Path:
    return RQ_DIR / kind / name / judge_name / f"{item}.json"


def control_items() -> list[tuple[str, str, str, dict[str, Any]]]:
    return [("controls", "controls", c["run_id"], {"query": c["query"], "generation": c["generation"]})
            for c in RM.load_controls()]


def expert_entries() -> list[dict[str, Any]]:
    """The 60 expert-package items (key.json order), read from where they live. `expert_eval_builder.items()` reads
    runs from H.OUT, which is loop_rq in this process, so it cannot be used here."""
    key = _read_json(B.INTERNAL / "key.json")
    out = []
    for q in key["questions"]:
        for label in "ABC":
            entry = q["labels"][label]
            if entry["source"] == "reference":
                generation = _read_json(B.INTERNAL / "references" / f"{q['paper_id']}.json")["generation"]
            else:
                generation = _read_json(E / "loop" / entry["method"] / "runs" / f"{entry['run_id']}.json")["generation"]
            out.append({"item": f"{q['qid']}-{label}", "paper_id": q["paper_id"], "source": entry["source"],
                        "generation": H._schema_only(generation)})
    return out


def expert_items() -> list[tuple[str, str, str, dict[str, Any]]]:
    cases = H.cases()
    return [("expert", "expert", it["item"], {"query": cases[it["paper_id"]]["queries"][B.LEVEL]["text"],
                                               "generation": it["generation"]}) for it in expert_entries()]


def retest_items() -> list[tuple[str, str, str, dict[str, Any]]]:
    return [("retest", WRITER, r["run_id"], {"query": r["query"], "generation": r["generation"]})
            for r in runs_of(WRITER) if int(r["sample"]) == 1]


def run_items(methods: list[str]) -> list[tuple[str, str, str, dict[str, Any]]]:
    return [("runs", m, r["run_id"], {"query": r["query"], "generation": r["generation"]})
            for m in methods for r in runs_of(m)]


def _order(jobs: list[Any]) -> list[Any]:
    if os.environ.get("MATHG_PENDING_SHUFFLE"):
        random.Random(int(os.environ["MATHG_PENDING_SHUFFLE"])).shuffle(jobs)
    if os.environ.get("MATHG_PENDING_REVERSE"):
        jobs.reverse()
    return jobs


def run_stage(items: list[tuple[str, str, str, dict[str, Any]]], judge_name: str, workers: int) -> dict[str, int]:
    jobs = _order([(path_of(k, n, judge_name, i), i, d) for k, n, i, d in items
                   if not path_of(k, n, judge_name, i).exists()])
    counts = {"jobs": len(jobs), "done": 0, "failed": 0}

    def job(j: tuple[Path, str, dict[str, Any]]) -> None:
        path, item, data = j
        if not path.exists():
            H.write_once(path, {"item": item, **judge(judge_name, data["query"], data["generation"])})

    with ThreadPoolExecutor(workers) as pool:
        futures = [pool.submit(job, j) for j in jobs]
        for future in as_completed(futures):
            try:
                future.result()
                counts["done"] += 1
            except Exception as error:  # noqa: BLE001 - logged; a rerun resumes
                counts["failed"] += 1
                print(f"[rq-{judge_name}] {type(error).__name__}: {str(error)[:200]}", flush=True)
    return counts


# ---------------------------------------------------------------- analysis

# (report name, judge, number of independent calls averaged per item). DeepSeek-3 is the post-hoc amendment of
# loop.md 24.2; the single-call views are the pre-registered ones.
VIEWS = (("o1", "o1", 1), ("deepseek", "deepseek", 1), ("deepseek3", "deepseek", 3))


def rep_kind(kind: str, rep: int) -> str:
    return kind if rep == 1 else f"{kind}_rep{rep}"


def _load_one(kind: str, name: str, judge_name: str) -> dict[str, dict[str, Any]]:
    folder = RQ_DIR / kind / name / judge_name
    return {p.stem: _read_json(p) for p in sorted(folder.glob("*.json"))} if folder.exists() else {}


def load(kind: str, name: str, judge_name: str, k: int = 1) -> dict[str, dict[str, Any]]:
    """The judgments of one set; with k > 1, the mean of k independent calls, for the items that have all k."""
    sets = [_load_one(rep_kind(kind, r), name, judge_name) for r in range(1, k + 1)]
    if k == 1:
        return sets[0]
    common = sorted(set(sets[0]).intersection(*map(set, sets[1:])))
    return {i: {"item": i, "scores": {s: statistics.fmean(x[i]["scores"][s] for x in sets) for s in SCALES},
                "rq": statistics.fmean(x[i]["rq"] for x in sets)} for i in common}


def per_paper(method: str, judge_name: str, k: int = 1, value=lambda x: x["rq"]) -> dict[str, float]:
    data: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for item, x in load("runs", method, judge_name, k).items():
        paper, level = item.split("__")[:2]
        data[paper][level].append(value(x))
    return A.per_paper(data)


def mean_ci(values: dict[str, float]) -> dict[str, Any]:
    """Mean of per-paper values with the paired-bootstrap CI (difference from 0)."""
    if not values:
        return {"papers": 0}
    out = A.paired(values, {p: 0.0 for p in values})
    return {"papers": out["papers"], "mean": out["diff"], "ci95": out["ci95"]}


def spearman(a: list[float], b: list[float]) -> float | None:
    rho = R.spearman(a, b) if len(a) > 5 else None
    return round(rho, 3) if rho is not None else None


def validation(judge_name: str, k: int = 1) -> dict[str, Any]:
    controls = load("controls", "controls", judge_name, k)
    by: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for item, x in controls.items():
        paper, control = item.split("__")[:2]
        by[control][paper] = x

    def mean(control: str, scale: str | None = None) -> float | None:
        vals = [x["rq"] if scale is None else x["scores"][scale] for x in by.get(control, {}).values()]
        return round(statistics.fmean(vals), 3) if vals else None

    means = {c: {"rq": mean(c), **{s: mean(c, s) for s in SCALES}, "n": len(by.get(c, {}))} for c in RM.CONTROLS}
    first = load("runs", WRITER, judge_name, k)
    second = load("retest", WRITER, judge_name, k)
    pairs = [(first[i]["rq"], second[i]["rq"]) for i in second if i in first]
    rho = spearman([a for a, _ in pairs], [b for _, b in pairs])

    def gap(a: str, b: str, scale: str | None) -> float | None:
        x, y = (means[a]["rq"], means[b]["rq"]) if scale is None else (means[a][scale], means[b][scale])
        return round(x - y, 3) if x is not None and y is not None else None

    complete = all(means[c]["n"] == 36 for c in RM.CONTROLS)
    checks = {
        "C1_relevance_usefulness_gap_ge_1": (g := gap("positive", "random_negative", "usefulness")) is not None
        and g >= 1.0,
        "C2_specificity_rq_gap_ge_1": (g := gap("positive", "generic", None)) is not None and g >= 1.0,
        "C3_consistency_plausibility_gaps_ge_0.5": all(
            (g := gap("positive", s, "plausibility")) is not None and g >= 0.5
            for s in ("intervention_swap", "mechanism_swap")),
        "C4_retest_rho_ge_0.80": rho is not None and rho >= 0.80 and len(pairs) >= 135,
    }
    brown = round(2 * rho / (1 + rho), 3) if rho is not None and rho > -1 else None
    return {"calls_per_item": k, "controls_complete": complete, "means_by_control": means,
            "gaps": {"usefulness_positive_minus_random": gap("positive", "random_negative", "usefulness"),
                     "rq_positive_minus_generic": gap("positive", "generic", None),
                     "plausibility_positive_minus_intervention_swap": gap("positive", "intervention_swap",
                                                                          "plausibility"),
                     "plausibility_positive_minus_mechanism_swap": gap("positive", "mechanism_swap", "plausibility"),
                     "rq_positive_minus_hard_negative": gap("positive", "hard_negative", None)},
            "retest": {"pairs": len(pairs), "rho": rho, "spearman_brown_two_calls": brown,
                       "mean_abs_diff": round(statistics.fmean(abs(a - b) for a, b in pairs), 3) if pairs else None},
            "checks": checks, "internally_validated": complete and all(checks.values()),
            "fallback_two_calls_ok": k == 1 and (not checks["C4_retest_rho_ge_0.80"]) and brown is not None
            and brown >= 0.80}


def expert_summary(judge_name: str, k: int = 1) -> dict[str, Any]:
    items = load("expert", "expert", judge_name, k)
    sources = {it["item"]: it["source"] for it in expert_entries()}
    by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item, x in items.items():
        by[sources.get(item, "?")].append(x)
    return {src: {"n": len(xs), "rq": round(statistics.fmean(x["rq"] for x in xs), 3),
                  **{s: round(statistics.fmean(x["scores"][s] for x in xs), 3) for s in SCALES}}
            for src, xs in sorted(by.items())}


def words(generation: dict[str, Any]) -> int:
    return len(render(generation).split())


def configuration(method: str, judge_name: str, k: int = 1) -> dict[str, Any]:
    items = load("runs", method, judge_name, k)
    runs = {r["run_id"]: r for r in runs_of(method)}
    ranked = [(x["rq"], words(runs[i]["generation"])) for i, x in items.items() if i in runs]
    return {"judged": len(items), "runs": len(runs), **mean_ci(per_paper(method, judge_name, k)),
            "scales": {s: round(statistics.fmean(x["scores"][s] for x in items.values()), 3) if items else None
                       for s in SCALES},
            "share_ge_target": round(sum(x["rq"] >= TARGET for x in items.values()) / len(items), 3) if items
            else None,
            "words": round(statistics.fmean(w for _, w in ranked), 1) if ranked else None,
            "rho_rq_words": spearman([a for a, _ in ranked], [b for _, b in ranked])}


def comparisons(methods: list[str]) -> dict[str, Any]:
    """Paired against the writer, for the configurations judged completely in that view."""
    out = {}
    for view, judge_name, k in VIEWS:
        base = per_paper(WRITER, judge_name, k)
        items = []
        for m in methods:
            if m == WRITER or len(load("runs", m, judge_name, k)) < len(runs_of(m)):
                continue
            other = per_paper(m, judge_name, k)
            if other and base:
                items.append({"config": m, "vs": WRITER, **A.paired(other, base)})
        out[view] = V.holm_family(items)
    return out


def agreement(methods: list[str]) -> dict[str, Any]:
    out = {}
    for name, k in (("o1_vs_deepseek", 1), ("o1_vs_deepseek3", 3)):
        a, b = [], []
        for m in methods:
            x, y = load("runs", m, "o1"), load("runs", m, "deepseek", k)
            for i in sorted(set(x) & set(y)):
                a.append(x[i]["rq"])
                b.append(y[i]["rq"])
        out[name] = {"runs": len(a), "spearman": spearman(a, b)}
    return out


def audit_convergence(methods: list[str]) -> dict[str, Any]:
    """RQ testability against the GPT-5.6 audit's falsifiability, and plausibility against contradictions."""
    out = {}
    for view, judge_name, k in VIEWS:
        t, f, p, c = [], [], [], []
        for m in methods:
            for i, x in load("runs", m, judge_name, k).items():
                path = root_of(m) / m / "audit" / f"{i}.json"
                if path.exists():
                    audit = _read_json(path)
                    fals = audit.get("falsifiability") or {}
                    if fals:
                        t.append(x["scores"]["testability"])
                        f.append(statistics.fmean(1.0 if v else 0.0 for v in fals.values()))
                    p.append(x["scores"]["plausibility"])
                    c.append(float(len(audit.get("contradictions", []))))
        out[view] = {"testability_vs_falsifiability": spearman(t, f),
                     "plausibility_vs_contradictions": spearman(p, c), "runs": len(p)}
    return out


def report(methods: list[str]) -> dict[str, Any]:
    names = [m for m in methods if any(load("runs", m, j) for j in JUDGES)]
    return {
        "validation": {v: validation(j, k) for v, j, k in VIEWS},
        "expert_items": {v: expert_summary(j, k) for v, j, k in VIEWS},
        "configurations": {m: {v: configuration(m, j, k) for v, j, k in VIEWS} for m in names},
        "vs_writer": comparisons([m for m in names if m != REFERENCE]),
        "judge_agreement": agreement(names),
        "audit_convergence": audit_convergence([m for m in names if m != REFERENCE]),
        "target": TARGET,
    }


def _fmt(x: dict[str, Any]) -> str:
    if not x.get("papers"):
        return "-"
    if x.get("judged", 0) < x.get("runs", 0):
        return f"incomplete ({x['judged']} of {x['runs']})"
    return f"{x['mean']:.3f} [{x['ci95'][0]:.2f}, {x['ci95'][1]:.2f}]"


def render_report(r: dict[str, Any]) -> str:
    views = [v for v, _, _ in VIEWS]
    L = ["# Experiment 43: research quality (RQ) on the expert's blind scales", "",
         "Pre-registered in loop.md 24.1. RQ = mean of plausibility, testability and usefulness (1-5) minus 1, on "
         "0-4; target-free and evidence-blind. Judges: o1 (primary; cannot know the papers) and DeepSeek. "
         "deepseek3 = the mean of three DeepSeek calls per item: a post-hoc amendment (loop.md 24.2), reported "
         "beside the pre-registered single-call views. RQ is not reconstruction.", "",
         "## Validation (sanity controls of experiment 33; re-test on 135 writer runs)", ""]
    for v, x in r["validation"].items():
        L.append(f"- **{v}** ({x['calls_per_item']} call(s) per item): internally validated "
                 f"{x['internally_validated']} (controls complete {x['controls_complete']}); checks "
                 f"{json.dumps(x['checks'])}; gaps {json.dumps(x['gaps'])}; re-test {json.dumps(x['retest'])}")
    L += ["", "| control | " + " | ".join(f"{v} RQ" for v in views) + " |", "|---|" + "---:|" * len(views)]
    for c in RM.CONTROLS:
        L.append(f"| {c} | " + " | ".join(str(r["validation"][v]["means_by_control"][c]["rq"]) for v in views) + " |")
    L += ["", "## Expert-package items (the authors' study, the Llama baseline, the writer)", ""]
    for v, x in r["expert_items"].items():
        L.append(f"- **{v}**: {json.dumps(x)}")
    L += ["", "## Configurations (per-paper means, 95% CI; target 2.5)", "",
          "| configuration | " + " | ".join(f"{v} RQ [CI]" for v in views) + " | " +
          " | ".join(f"{v} plaus/test/use" for v in views) + " | words | ≥ 2.5 (o1) |",
          "|---|" + "---|" * (2 * len(views) + 2)]
    for m, by in r["configurations"].items():
        scales = ["/".join(str(by[v]["scales"][s]) for s in SCALES) for v in views]
        L.append(f"| {m} | " + " | ".join(_fmt(by[v]) for v in views) + " | " + " | ".join(scales) +
                 f" | {max(by.values(), key=lambda x: x['judged'])['words']} | {by['o1']['share_ge_target']} |")
    L += ["", "## Against the writer (paired per paper, Holm)", ""]
    for v, items in r["vs_writer"].items():
        for it in items:
            if it.get("papers"):
                L.append(f"- {v}: {it['config']} − writer {it['diff']:+.3f} [{it['ci95'][0]:+.2f}, "
                         f"{it['ci95'][1]:+.2f}] ({it['up']}/{it['down']} papers, Holm p {it['holm_p']})")
    L += ["", f"Judge agreement (run level): {json.dumps(r['judge_agreement'])}", "",
          f"Convergence with the GPT-5.6 audits: {json.dumps(r['audit_convergence'])}", ""]
    return "\n".join(L)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("controls", "expert", "retest", "runs", "report"))
    parser.add_argument("--judge", action="append")
    parser.add_argument("--method", action="append")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--rep", type=int, default=1, help="independent repeat number (loop.md 24.2): 2, 3, ...")
    args = parser.parse_args()
    if args.stage == "report":
        methods = list(PHASE_B) + [REFERENCE] + [m for m in (args.method or []) if m not in PHASE_B]
        result = report(methods)
        atomic_json(OUT / "analysis_rq.json", result)
        (OUT / "analysis_rq.md").write_text(render_report(result))
        print(render_report(result))
        return
    items = {"controls": control_items, "expert": expert_items, "retest": retest_items}.get(args.stage)
    selected = items() if items else run_items(args.method or list(PHASE_B))
    if args.rep > 1:
        selected = [(rep_kind(k, args.rep), n, i, d) for k, n, i, d in selected]
    for judge_name in args.judge or ["o1"]:
        print(judge_name, run_stage(selected, judge_name, args.workers), flush=True)


if __name__ == "__main__":
    main()
