"""Experiment 46 (loop.md 27.1): strong research proposals as the only objective. Phase 0 (the instrument) and Phase 1
(every existing configuration scored on it).

The measure (must_obey.md 6.2, amended 2026-11-05):
- RQ: the expert's three blind scales (plausibility, testability, usefulness, 1-5), judged by DeepSeek-V4-Pro from the
  question and the hypothesis as the expert sees it (rq_judge.py; no citations, no evidence, no answer key); the mean
  of three calls; RQ = mean - 1, on 0-4.
- Grounding (new, 1-5): are the hypothesis's key premises supported by the earlier work it cites, accurately
  represented? DeepSeek-V4-Pro sees the question, the hypothesis (evidence IDs relabelled E1, E2, ...) and the cited
  passages. It enters the score only after validation (G1-G4, loop.md 27.1).
- SP, the strong-proposal score (0-4): the mean of the four 1-5 scales minus 1; RQ alone while grounding is not valid.
- Decisions: target-free pairwise preference in both orders (a win needs both), DeepSeek for development, GPT-5.6 held
  out to confirm, o1 as a further view.

Stages (resumable; one process per judge model, at most 6 workers each):
  python quality_eval.py list --phase a|a_vs|b|diag     configuration names, for the runners
  python quality_eval.py controls                       the 216 RQ sanity controls again, this session, one call
  python quality_eval.py ground_validate                grounding checks G1-G4 (sample 1 of web_text_64k_b_o3mini
                                                        and of the writer)
  python quality_eval.py rq --rep R [--kind K] --method M ...   RQ, DeepSeek, call R (rq_judge storage)
  python quality_eval.py ground --method M ...          grounding, DeepSeek, one call per run
  python quality_eval.py pairwise --judge J --method M ...      each method against the writer, both orders
  python quality_eval.py top_b [--n 5]                  the phase-1b configurations with the highest SP (names)
  python quality_eval.py finalists [--n 3]              the configurations for GPT-5.6 confirmation (names)
  python quality_eval.py report                         loop_quality/analysis_quality.json and .md
"""

from __future__ import annotations

import rq_judge as RQ  # noqa: I001 - first: it sets the case and loop roots before hypo_loop is imported

import argparse
import json
import statistics
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import diag_analysis as D
import hypo_loop as H
import llm_client as lc
import review_measurement as RM
from hypothesis_evidence_v2 import atomic_json
from stage_metrics import CROSS_JUDGE
from temporal_eval_v3 import _blind_candidate
from temporal_hypothesis_benchmark import _read_json

A, V = RQ.A, RQ.V
E = RQ.E
OUT = E / "loop_quality"
GROUND_DIR = OUT / "grounding"
PAIR_DIR = OUT / "pairwise"
WRITER = RQ.WRITER
REFERENCE = RQ.REFERENCE  # the authors' own study written as a proposal: a reference, never a method (5.4)
DEV = "deepseek"
PAIR_JUDGES = ("deepseek", "o1", "gpt56")
SESSION = "rerun46"  # the writer's RQ judged again in this session (must_obey.md 6.10)
SCALES = RQ.SCALES

# Phase 1a: configurations already scored on RQ in experiments 43-45 (old session), and the reference.
PHASE_A = ("writer_only_b_o3mini", "closed_book", "closed_book_o3mini", "writer_study_b_o3mini",
           "web_text_64k_b_o3mini", "web64k_v2_b_o3mini", "rx_base", "rx_r", "rx_u", "rx_ru", "rx_c", "rx_ruc_select",
           "rx_ruc", "edit_rx_base", "edit_rx_r")
# Phase 1b: every other configuration with all 270 runs, one per family first (loop.md 27.1).
PHASE_B = ("writer_v2_b_o3mini", "web64k_r2_b_o3mini", "web_study_64k_b_o3mini", "agent_choose_ground_b_o3mini",
           "pcd_PCD_o3mini", "synth_crowd_b_o3mini", "web_agent_b_o3mini", "read_web_chunks_b_o3mini",
           "web_text_chunks_b_o3mini", "writer_only_b_o3mini_r5",
           "writer_design_b_o3mini", "writer_types_b_o3mini", "agent_choose_only_b_o3mini",
           "agent_draft_ground_b_o3mini", "pcd_none_o3mini", "pcd_P_o3mini", "pcd_C_o3mini", "pcd_D_o3mini",
           "pcd_PC_o3mini", "pcd_PD_o3mini", "pcd_CD_o3mini", "pcd_k1_PCD_o3mini", "pcd_k1_none_o3mini",
           "pcd_nocritic_PCD_o3mini", "pcd_nocritic_none_o3mini", "pcd_nodecider_PCD_o3mini",
           "pcd_nodecider_none_o3mini", "pcd_PCD_llama", "pcd_none_llama", "synth_k1_b_o3mini", "synth_k4_b_o3mini",
           "synth_mixed_b_o3mini", "web_agent", "web_agent_o3mini", "web_text_chunks")
DIAGNOSTICS = ("oracle_hint_lever_b_o3mini", "oracle_hint_class_b_o3mini")  # answer-key hints: references only
VALIDATION_METHOD = "web_text_64k_b_o3mini"
EXPERIMENT_OF_ROOT = {"loop": "21-35", "loop_web": "36", "loop_pcd": "37", "loop_r4": "38", "loop_diag": "39",
                      "loop_agent": "40", "loop_study": "41", "loop_v2": "42", "loop_rx": "44-45"}

GROUNDING_SYSTEM = """You are an experienced materials scientist checking how well a research hypothesis on high-temperature high-entropy alloys is grounded in prior evidence. You see the research question, the hypothesis (as JSON; its evidence IDs refer to the cited passages) and the passages from earlier papers that it cites, labelled E1, E2, and so on. A hypothesis may cite no passages.

First list the key premises of the hypothesis: the specific claims about earlier results, material behaviour or mechanisms on which the proposal relies (at most five). Then rate:

Grounding (1-5): are these premises supported by specific prior evidence, accurately represented?
1 = No specific prior evidence for the key premises, or the cited evidence is misrepresented or contradicts them
2 = Little support: most key premises are unsupported, or the cited evidence is only loosely related to them
3 = Partly supported: some key premises are supported by the cited evidence, others are not
4 = Mostly supported: the key premises are supported by accurately represented evidence, with minor gaps or overstatements
5 = Fully supported: every key premise is supported by accurately represented cited evidence

Rate only the support for the premises, not whether the proposal is a good idea. Standard textbook knowledge needs no citation; specific claims about earlier results do. Citing more passages is not better in itself.

Return JSON: {"premises": ["each premise in a few words"], "grounding_reason": "one or two sentences", "grounding": integer 1-5}. Give the reason before the score."""


# ---------------------------------------------------------------- grounding judge

def ground_payload(query: str, generation: dict[str, Any], evidence: list[dict[str, Any]]) -> str:
    text = json.dumps({"research_question": query, "hypothesis": generation, "cited_evidence": evidence},
                      ensure_ascii=False)
    if "hidden_target" in text:
        raise H.TargetLeak("grounding payload must not contain the answer key")
    return text


def ground_validate(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    try:
        value = int(raw.get("grounding"))
    except (TypeError, ValueError):
        return None
    if not 1 <= value <= 5 or float(raw.get("grounding")) != value:
        return None
    premises = raw.get("premises") if isinstance(raw.get("premises"), list) else []
    return {"grounding": value, "reason": str(raw.get("grounding_reason", ""))[:600],
            "premises": [str(p)[:200] for p in premises[:5]]}


def ground_call(judge: str, user: str) -> Any:
    if judge == "deepseek":
        return lc.trapi_chat_json(CROSS_JUDGE["deployment"], GROUNDING_SYSTEM, user, max_tokens=4000,
                                  token_field=CROSS_JUDGE["token_field"], temperature=CROSS_JUDGE["temperature"],
                                  retries=8)
    if judge == "gpt56":
        return lc.judge_chat_json(GROUNDING_SYSTEM, user, max_tokens=8000)
    raise ValueError(f"unknown grounding judge {judge!r}")


def ground_judge(judge: str, data: dict[str, Any], attempts: int = 3) -> dict[str, Any]:
    user = ground_payload(data["query"], data["generation"], data["evidence"])
    for attempt in range(attempts):
        result = ground_validate(ground_call(judge, user))
        if result is not None:
            return {"judge": judge, **result, "attempts": attempt + 1}
    raise lc.LLMError(f"grounding judge {judge} gave no valid score in {attempts} attempts")


def ground_path(kind: str, name: str, judge: str, item: str) -> Path:
    return GROUND_DIR / kind / name / judge / f"{item}.json"


def blinded(run: dict[str, Any]) -> dict[str, Any]:
    generation, evidence = _blind_candidate(run)
    return {"query": run["query"], "generation": generation, "evidence": evidence}


def ground_items(methods: list[str], kind: str = "runs") -> list[tuple[str, str, str, dict[str, Any]]]:
    return [(kind, m, r["run_id"], blinded(r)) for m in methods for r in RQ.runs_of(m)]


def swap_controls(runs: list[dict[str, Any]]) -> list[tuple[str, str, str, dict[str, Any]]]:
    """G1: each citing run's passages replaced by the first k passages cited by the run of the next paper (sorted,
    cyclic) at the same level that cites at least k; the hypothesis and its labels E1..Ek are unchanged."""
    by_level: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        by_level[run["query_level"]].append(run)
    out = []
    for level_runs in by_level.values():
        level_runs.sort(key=lambda r: r["paper_id"])
        views = [blinded(r) for r in level_runs]
        for i, (run, view) in enumerate(zip(level_runs, views)):
            k = len(view["evidence"])
            if not k:
                continue
            donor = next((views[(i + j) % len(views)] for j in range(1, len(views))
                          if len(views[(i + j) % len(views)]["evidence"]) >= k), None)
            if donor is None:
                continue
            evidence = [{**e, "evidence_id": f"E{n + 1}"} for n, e in enumerate(donor["evidence"][:k])]
            out.append(("g_swap", run["method"], run["run_id"], {**view, "evidence": evidence}))
    return out


def removal_controls(runs: list[dict[str, Any]]) -> list[tuple[str, str, str, dict[str, Any]]]:
    """G2: the same hypotheses with every evidence ID and cited passage removed."""
    out = []
    for run in runs:
        view = blinded(run)
        if view["evidence"]:
            generation = {**view["generation"], "supporting_evidence_ids": [], "conflicting_evidence_ids": []}
            out.append(("g_removed", run["method"], run["run_id"], {**view, "generation": generation,
                                                                     "evidence": []}))
    return out


def validation_items() -> list[tuple[str, str, str, dict[str, Any]]]:
    runs = [r for r in RQ.runs_of(VALIDATION_METHOD) if int(r["sample"]) == 1]
    originals = ground_items([VALIDATION_METHOD])
    keep = {r["run_id"] for r in runs}
    writer = [i for i in ground_items([WRITER]) if i[2].endswith("__s1")]  # G4's closed-book group
    return ([i for i in originals if i[2] in keep] + [("g_retest", *i[1:]) for i in originals if i[2] in keep]
            + swap_controls(runs) + removal_controls(runs) + writer)


def _order(jobs: list[Any]) -> list[Any]:
    return RQ._order(jobs)


def _run(jobs: list[Any], fn: Any, workers: int, tag: str) -> dict[str, int]:
    counts = {"jobs": len(jobs), "done": 0, "failed": 0}
    with ThreadPoolExecutor(workers) as pool:
        futures = [pool.submit(fn, j) for j in jobs]
        for future in as_completed(futures):
            try:
                future.result()
                counts["done"] += 1
            except Exception as error:  # noqa: BLE001 - logged; a rerun resumes
                counts["failed"] += 1
                print(f"[{tag}] {type(error).__name__}: {str(error)[:200]}", flush=True)
    return counts


def ground_stage(items: list[tuple[str, str, str, dict[str, Any]]], judge: str, workers: int) -> dict[str, int]:
    jobs = _order([(ground_path(k, n, judge, i), i, d) for k, n, i, d in items
                   if not ground_path(k, n, judge, i).exists()])

    def job(j: tuple[Path, str, dict[str, Any]]) -> None:
        path, item, data = j
        if not path.exists():
            H.write_once(path, {"item": item, **ground_judge(judge, data)})

    return _run(jobs, job, workers, f"ground-{judge}")


def ground_load(kind: str, name: str, judge: str = DEV) -> dict[str, dict[str, Any]]:
    folder = GROUND_DIR / kind / name / judge
    return {p.stem: _read_json(p) for p in sorted(folder.glob("*.json"))} if folder.exists() else {}


# ---------------------------------------------------------------- pairwise preference against the writer

def pair_path(new: str, base: str, judge: str, key: tuple[str, str, int], order: str, root: Path | None = None
              ) -> Path:
    return (root or PAIR_DIR) / f"{new}__vs__{base}" / judge / f"{key[0]}__{key[1]}__s{key[2]}__{order}.json"


def pair_call(judge: str, user: str, system: str | None = None) -> Any:
    """diag_analysis.pair_call with a choice of prompt (experiment 47 uses a revised one)."""
    if system is None or system == D.QUALITY_PAIR_SYSTEM:
        return D.pair_call(judge, user)
    if judge == "gpt56":
        return lc.judge_chat_json(system, user, max_tokens=8000)
    if judge == "deepseek":
        return lc.trapi_chat_json(CROSS_JUDGE["deployment"], system, user, max_tokens=4000,
                                  token_field=CROSS_JUDGE["token_field"], temperature=CROSS_JUDGE["temperature"],
                                  retries=8)
    return lc.trapi_chat_json(D.O1, system, user, max_tokens=16000, token_field="max_completion_tokens",
                              temperature=None, retries=8)


def pairwise_stage(methods: list[str], judge: str, workers: int, base: str = WRITER, system: str | None = None,
                   root: Path | None = None) -> dict[str, int]:
    base_runs = {D.key_of(r): r for r in RQ.runs_of(base)}
    jobs = []
    for new in methods:
        for run in RQ.runs_of(new):
            key = D.key_of(run)
            if key in base_runs:
                for order in ("baseline_first", "new_first"):
                    path = pair_path(new, base, judge, key, order, root)
                    if not path.exists():
                        jobs.append((order, base_runs[key], run, path))

    def job(j: tuple[Any, ...]) -> None:
        order, b, n, path = j
        if path.exists():
            return
        first, second = (b, n) if order == "baseline_first" else (n, b)
        ga, ea = _blind_candidate(first)
        gb, eb = _blind_candidate(second)
        user = json.dumps({"research_question": b["query"], "candidate_A": {"hypothesis": ga, "cited_evidence": ea},
                           "candidate_B": {"hypothesis": gb, "cited_evidence": eb}}, ensure_ascii=False)
        if "hidden_target" in user:
            raise H.TargetLeak("pairwise payload must not contain the answer key")
        raw = pair_call(judge, user, system)
        raw = raw if isinstance(raw, dict) else {}
        winner = str(raw.get("winner", "tie")).strip().upper()
        winner = winner if winner in ("A", "B", "TIE") else "TIE"
        side = "B" if order == "baseline_first" else "A"
        H.write_once(path, {"judge": judge, "order": order, "winner": winner, "new_won": winner == side,
                            "baseline_won": winner not in (side, "TIE"), "reason": str(raw.get("reason", ""))[:600]})

    return _run(_order(jobs), job, workers, f"pairwise-{judge}")


def pair_outcomes(new: str, base: str, judge: str, root: Path | None = None) -> dict[tuple[str, str, int], float]:
    """Per question and sample: +1 when the new method wins in both orders, -1 when the base does, else 0."""
    folder = (root or PAIR_DIR) / f"{new}__vs__{base}" / judge
    by: dict[str, dict[str, Any]] = defaultdict(dict)
    for path in sorted(folder.glob("*.json")) if folder.exists() else []:
        stem, order = path.stem.rsplit("__", 1)
        by[stem][order] = _read_json(path)
    out = {}
    for stem, orders in by.items():
        if len(orders) == 2:
            paper, level, sample = stem.split("__")
            won = all(o["new_won"] for o in orders.values())
            lost = all(o["baseline_won"] for o in orders.values())
            out[(paper, level, int(sample.lstrip("s")))] = 1.0 if won else -1.0 if lost else 0.0
    return out


def per_paper(values: dict[tuple[str, str, int], float]) -> dict[str, float]:
    by: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for (paper, level, _), v in values.items():
        by[paper][level].append(v)
    return {p: statistics.fmean(statistics.fmean(v) for v in lv.values()) for p, lv in by.items()}


def pair_result(new: str, base: str, judge: str, root: Path | None = None) -> dict[str, Any]:
    outcomes = pair_outcomes(new, base, judge, root)
    if not outcomes:
        return {"pairs": 0}
    values = list(outcomes.values())
    pp = per_paper(outcomes)
    return {"pairs": len(values), "new_wins": D.share([v == 1 for v in values]),
            "base_wins": D.share([v == -1 for v in values]), **A.paired(pp, {p: 0.0 for p in pp})}


# ---------------------------------------------------------------- scores

def key_of_item(item: str) -> tuple[str, str, int]:
    paper, level, _, sample = item.split("__")
    return paper, level, int(sample.lstrip("s"))


def rq_values(method: str, kind: str = "runs", k: int = 3) -> dict[tuple[str, str, int], dict[str, Any]]:
    return {key_of_item(i): x for i, x in RQ.load(kind, method, DEV, k).items()}


def ground_values(method: str, kind: str = "runs") -> dict[tuple[str, str, int], int]:
    return {key_of_item(i): x["grounding"] for i, x in ground_load(kind, method).items()}


def sp_values(method: str, kind: str = "runs", with_grounding: bool = True) -> dict[tuple[str, str, int], float]:
    rq, gr = rq_values(method, kind), ground_values(method)
    if not with_grounding:
        return {k: x["rq"] for k, x in rq.items()}
    return {k: (sum(x["scores"][s] for s in SCALES) + gr[k]) / 4 - 1 for k, x in rq.items() if k in gr}


# ---------------------------------------------------------------- validation

def rq_controls(k: int = 1) -> dict[str, Any]:
    """The experiment-43 checks C1-C3 on this session's control judgments: one call (pre-registered), or the mean of
    three, as the RQ instrument itself (added at 01:15 after the single call missed C2 by 0.05, loop.md 27.2)."""
    by: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for item, x in RQ.load("controls_s46", "controls", DEV, k).items():
        paper, control = item.split("__")[:2]
        by[control][paper] = x

    def mean(control: str, scale: str | None = None) -> float | None:
        vals = [x["rq"] if scale is None else x["scores"][scale] for x in by.get(control, {}).values()]
        return round(statistics.fmean(vals), 3) if vals else None

    def gap(a: str, b: str, scale: str | None) -> float | None:
        x, y = mean(a, scale), mean(b, scale)
        return round(x - y, 3) if x is not None and y is not None else None

    checks = {"C1_usefulness_positive_minus_random_ge_1": (g := gap("positive", "random_negative", "usefulness"))
              is not None and g >= 1.0,
              "C2_rq_positive_minus_generic_ge_1": (g := gap("positive", "generic", None)) is not None and g >= 1.0,
              "C3_plausibility_positive_minus_swaps_ge_0.5": all(
                  (g := gap("positive", s, "plausibility")) is not None and g >= 0.5
                  for s in ("intervention_swap", "mechanism_swap"))}
    return {"items": sum(len(v) for v in by.values()),
            "means": {c: {"rq": mean(c), "n": len(by.get(c, {}))} for c in RM.CONTROLS},
            "gaps": {"usefulness_positive_minus_random": gap("positive", "random_negative", "usefulness"),
                     "rq_positive_minus_generic": gap("positive", "generic", None),
                     "plausibility_positive_minus_intervention_swap": gap("positive", "intervention_swap",
                                                                          "plausibility"),
                     "plausibility_positive_minus_mechanism_swap": gap("positive", "mechanism_swap",
                                                                       "plausibility")},
            "checks": checks, "passed": bool(by) and all(checks.values())}


def ground_validation() -> dict[str, Any]:
    """G1-G4 (loop.md 27.1). The smoke test found the originals near the floor (2, 1, 1), so the checks are relative:
    G1 swapped passages lower grounding (paired CI above 0, at most 10% of swaps higher); G2 with no citation the mean
    is at most 1.5; G3 re-test Spearman >= 0.70 for one call; G4 the evidence-based writer is better grounded than the
    closed-book writer (paired CI above 0)."""
    method = VALIDATION_METHOD
    orig = ground_load("runs", method)
    sets = {k: ground_load(k, method) for k in ("g_retest", "g_swap", "g_removed")}

    def paired(kind: str) -> dict[str, Any]:
        common = sorted(set(orig) & set(sets[kind]))
        if not common:
            return {"pairs": 0}
        a = per_paper({key_of_item(i): float(orig[i]["grounding"]) for i in common})
        b = per_paper({key_of_item(i): float(sets[kind][i]["grounding"]) for i in common})
        return {"pairs": len(common), "original_mean": round(statistics.fmean(orig[i]["grounding"] for i in common), 3),
                "control_mean": round(statistics.fmean(sets[kind][i]["grounding"] for i in common), 3),
                "control_higher_share": round(statistics.fmean(sets[kind][i]["grounding"] > orig[i]["grounding"]
                                                               for i in common), 3),
                "drop_by_paper": A.paired(a, b)}

    common = sorted(set(orig) & set(sets["g_retest"]))
    rho = RQ.spearman([orig[i]["grounding"] for i in common], [sets["g_retest"][i]["grounding"] for i in common])
    g1, g2 = paired("g_swap"), paired("g_removed")
    sample1 = {k: v for k, v in ground_values(method).items() if k[2] == 1}
    writer1 = {k: v for k, v in ground_values(WRITER).items() if k[2] == 1}
    g4 = A.paired(per_paper({k: float(v) for k, v in sample1.items()}),
                  per_paper({k: float(v) for k, v in writer1.items()})) if sample1 and writer1 else {"papers": 0}
    checks = {"G1_swap_lowers": bool(g1.get("pairs")) and g1["drop_by_paper"]["ci95"][0] > 0
              and g1["control_higher_share"] <= 0.10,
              "G2_no_citation_mean_le_1.5": bool(g2.get("pairs")) and g2["control_mean"] <= 1.5,
              "G3_retest_rho_ge_0.70": rho is not None and rho >= 0.70 and len(common) >= 130,
              "G4_evidence_writer_above_closed_book": bool(g4.get("papers")) and g4["ci95"][0] > 0}
    return {"G1_swap": g1, "G2_removal": g2,
            "G3_retest": {"pairs": len(common), "rho": rho,
                          "mean_abs_diff": round(statistics.fmean(abs(orig[i]["grounding"] -
                                                                      sets["g_retest"][i]["grounding"])
                                                                  for i in common), 3) if common else None},
            "G4_known_groups": g4, "checks": checks, "valid": all(checks.values())}


# ---------------------------------------------------------------- the leaderboard

def complete(method: str, kind: str = "runs") -> bool:
    runs = RQ.runs_of(method)
    return bool(runs) and len(RQ.load(kind, method, DEV, 3)) >= len(runs)


def writer_reference(method: str) -> tuple[str, str]:
    """(kind of the writer's RQ to compare with, label): phase-1a methods were judged with the writer's first set in
    experiments 43-45; later ones are compared with the writer's same-session set (must_obey.md 6.10)."""
    return ("runs", "experiments 43-45") if method in PHASE_A else (SESSION, "this session")


def row(method: str, grounding_valid: bool) -> dict[str, Any]:
    runs = RQ.runs_of(method)
    rq = rq_values(method)
    gr = ground_values(method)
    words = [RQ.words(r["generation"]) for r in runs]
    out: dict[str, Any] = {
        "root": RQ.root_of(method).name, "experiment": EXPERIMENT_OF_ROOT.get(RQ.root_of(method).name, ""),
        "runs": len(runs), "rq_judged": len(rq), "grounding_judged": len(gr), "complete": complete(method),
        "rq": mean_of(per_paper({k: x["rq"] for k, x in rq.items()})),
        "scales": {s: round(statistics.fmean(x["scores"][s] for x in rq.values()), 3) if rq else None
                   for s in SCALES},
        "grounding": mean_of(per_paper({k: float(v) for k, v in gr.items()})),
        "sp": mean_of(per_paper(sp_values(method, with_grounding=grounding_valid))),
        "words": round(statistics.fmean(words), 1) if words else None,
        "pairwise": {j: pair_result(method, WRITER, j) for j in PAIR_JUDGES if method != WRITER}}
    if method != WRITER and out["complete"]:
        kind, label = writer_reference(method)
        out["sp_vs_writer"] = {"writer_set": label, **A.paired(per_paper(sp_values(method,
                                                                                    with_grounding=grounding_valid)),
                                                                 per_paper(sp_values(WRITER, kind, grounding_valid)))}
        out["rq_vs_writer"] = {"writer_set": label, **A.paired(
            per_paper({k: x["rq"] for k, x in rq.items()}),
            per_paper({k: x["rq"] for k, x in rq_values(WRITER, kind).items()}))}
    return out


def mean_of(values: dict[str, float]) -> float | None:
    return round(statistics.fmean(values.values()), 3) if values else None


def incumbent(rows: dict[str, dict[str, Any]], writer_grounding: float | None) -> dict[str, Any]:
    """The pre-registered rule (loop.md 27.1): the method with the highest lower CI bound of DeepSeek's pairwise
    preference over the writer, if that bound is above 0, whose SP is not significantly below the writer's, whose
    grounding is not below the writer's, and, once judged, whose GPT-5.6 preference is above 0."""
    eligible = []
    for method, r in rows.items():
        p = r.get("pairwise", {}).get(DEV, {})
        if method in (WRITER, REFERENCE) or method in DIAGNOSTICS or not p.get("papers") or p["ci95"][0] <= 0:
            continue
        sp = r.get("sp_vs_writer", {})
        if sp.get("papers") and sp["ci95"][1] < 0:
            continue
        if writer_grounding is not None and r.get("grounding") is not None and r["grounding"] < writer_grounding:
            continue
        gpt = r["pairwise"].get("gpt56", {})
        if gpt.get("papers") and gpt["diff"] <= 0:
            continue
        eligible.append((p["ci95"][0], method, bool(gpt.get("papers"))))
    if not eligible:
        return {"incumbent": WRITER, "rule": "no method passed; the writer stays"}
    bound, method, confirmed = max(eligible)
    return {"incumbent": method, "deepseek_lower_bound": bound,
            "gpt56": "confirmed" if confirmed else "pending GPT-5.6 confirmation",
            "eligible": [m for _, m, _ in sorted(eligible, reverse=True)]}


def report() -> dict[str, Any]:
    gv = ground_validation()
    valid = gv["valid"]
    methods = [m for m in (*PHASE_A, *PHASE_B) if RQ.runs_of(m)]
    rows = {m: row(m, valid) for m in methods if rq_values(m)}
    references = {m: row(m, valid) for m in (REFERENCE, *DIAGNOSTICS) if rq_values(m)}
    for judge in PAIR_JUDGES:  # Holm across the methods' comparisons; references stay outside the family
        items = [{"config": m, **r["pairwise"][judge]} for m, r in rows.items()
                 if r.get("pairwise", {}).get(judge, {}).get("papers")]
        for item in V.holm_family(items):
            rows[item["config"]]["pairwise"][judge]["holm_p"] = item["holm_p"]
    writer_ground = rows.get(WRITER, {}).get("grounding")
    session = rq_values(WRITER, SESSION)
    drift = A.paired(per_paper({k: x["rq"] for k, x in session.items()}),
                     per_paper({k: x["rq"] for k, x in rq_values(WRITER).items()})) if session else {"papers": 0}
    return {"grounding_validation": gv, "sp_uses_grounding": valid,
            "rq_controls_this_session": {"one_call": rq_controls(1), "three_calls": rq_controls(3)},
            "writer_rq_drift_session_minus_first": drift, "rows": rows, "references": references,
            "incumbent": incumbent(rows, writer_ground),
            "length": {"rho_sp_words_by_configuration": RQ.spearman(
                [r["sp"] for r in rows.values() if r["sp"] is not None and r["words"] is not None],
                [r["words"] for r in rows.values() if r["sp"] is not None and r["words"] is not None])}}


def ranked(rows: dict[str, dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    return sorted(rows.items(), key=lambda kv: -(kv[1]["sp"] if kv[1]["sp"] is not None else -9))


def top_b(n: int, valid: bool | None = None) -> list[str]:
    valid = ground_validation()["valid"] if valid is None else valid
    done = [m for m in PHASE_B if complete(m)]
    scored = [(mean_of(per_paper(sp_values(m, with_grounding=valid))), m) for m in done]
    return [m for s, m in sorted(((s, m) for s, m in scored if s is not None), reverse=True)[:n]]


def finalists(n: int) -> list[str]:
    out = []
    for m in (*PHASE_A, *PHASE_B):
        if m in (WRITER, REFERENCE):
            continue
        p = pair_result(m, WRITER, DEV)
        if p.get("papers") and p["ci95"][0] > 0:
            out.append((p["ci95"][0], m))
    return [m for _, m in sorted(out, reverse=True)[:n]]


def _c(x: dict[str, Any]) -> str:
    if not x or not x.get("papers"):
        return "–"
    holm = f", Holm {x['holm_p']}" if "holm_p" in x else ""
    return f"{x['diff']:+.2f} [{x['ci95'][0]:+.2f}, {x['ci95'][1]:+.2f}] {x['up']}/{x['down']}{holm}"


def _f(x: Any) -> str:
    return "–" if x is None else f"{x:.2f}" if isinstance(x, float) else str(x)


def render(r: dict[str, Any]) -> str:
    gv, rcs = r["grounding_validation"], r["rq_controls_this_session"]
    L = ["# Experiment 46: strong research proposals as the only objective (phases 0-1)", "",
         "Pre-registered in loop.md 27.1. SP = mean of plausibility, testability, usefulness (RQ judge, three DeepSeek "
         "calls) and grounding (one DeepSeek call) minus 1, on 0-4; RQ alone while grounding is not validated. "
         "Pairwise: net preference over the closed-book writer, both orders (a win needs both), paired by paper; "
         "DeepSeek decides, GPT-5.6 confirms, o1 alongside.", "",
         f"**Grounding validation** (G1-G4): valid = {gv['valid']}; {json.dumps(gv['checks'])}. Swap: "
         f"{json.dumps(gv['G1_swap'])}. Removal: {json.dumps(gv['G2_removal'])}. Re-test: {json.dumps(gv['G3_retest'])}. "
         f"Known groups (evidence writer minus closed-book writer): {_c(gv['G4_known_groups'])}.",
         "",
         *[line for view, rc in rcs.items() for line in (
             f"**RQ controls this session** ({view.replace('_', ' ')}): passed = {rc['passed']} ({rc['items']} items); "
             f"gaps {json.dumps(rc['gaps'])}.", "")],
         f"**Writer RQ drift** (this session minus experiment 43): {_c(r['writer_rq_drift_session_minus_first'])}.", "",
         f"**Incumbent** (rule in loop.md 27.1): {json.dumps(r['incumbent'])}", "",
         "## Leaderboard (configurations with complete RQ)", "",
         "| # | Configuration | Exp. | SP | RQ | Plaus. | Test. | Useful. | Grounding | Words | SP vs writer | "
         "Pairwise vs writer: DeepSeek | o1 | GPT-5.6 |",
         "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|"]
    for n, (m, x) in enumerate(ranked({k: v for k, v in r["rows"].items() if v["complete"]}), 1):
        s = x["scales"]
        L.append(f"| {n} | `{m}` | {x['experiment']} | {_f(x['sp'])} | {_f(x['rq'])} | {_f(s['plausibility'])} | "
                 f"{_f(s['testability'])} | {_f(s['usefulness'])} | {_f(x['grounding'])} | {_f(x['words'])} | "
                 f"{_c(x.get('sp_vs_writer', {}))} | {_c(x['pairwise'].get('deepseek', {}))} | "
                 f"{_c(x['pairwise'].get('o1', {}))} | {_c(x['pairwise'].get('gpt56', {}))} |")
    pending = [m for m, v in r["rows"].items() if not v["complete"]]
    L += ["", f"Incomplete (still being judged): {', '.join(pending) if pending else 'none'}.", "",
          "## References (never methods; must_obey.md 5.4)", ""]
    for m, x in r["references"].items():
        L.append(f"- `{m}`: SP {_f(x['sp'])}, RQ {_f(x['rq'])}, grounding {_f(x['grounding'])}; pairwise vs the writer "
                 f"(DeepSeek) {_c(x['pairwise'].get('deepseek', {}))}")
    L += ["", f"Length: Spearman of SP with words across configurations {r['length']['rho_sp_words_by_configuration']}.",
          ""]
    return "\n".join(L)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("list", "controls", "ground_validate", "rq", "ground", "pairwise", "top_b",
                                          "finalists", "report"))
    parser.add_argument("--phase", choices=("a", "a_vs", "b", "diag"))
    parser.add_argument("--method", action="append")
    parser.add_argument("--judge", default=DEV, choices=PAIR_JUDGES)
    parser.add_argument("--rep", type=int, default=1)
    parser.add_argument("--kind", default="runs", choices=("runs", SESSION))
    parser.add_argument("--n", type=int, default=3)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if args.stage == "list":  # for the runners: a = 1a with the writer; a_vs = 1a against the writer, and the reference
        print(" ".join({"a": PHASE_A, "a_vs": tuple(m for m in PHASE_A if m != WRITER) + (REFERENCE,), "b": PHASE_B,
                        "diag": DIAGNOSTICS}[args.phase]))
    elif args.stage == "controls":
        items = [("controls_s46", n, i, d) for _, n, i, d in RQ.control_items()]
        if args.rep > 1:
            items = [(RQ.rep_kind(k, args.rep), n, i, d) for k, n, i, d in items]
        print(RQ.run_stage(items, DEV, args.workers))
    elif args.stage == "ground_validate":
        print(ground_stage(validation_items(), DEV, args.workers))
    elif args.stage == "rq":
        items = [(args.kind, n, i, d) for _, n, i, d in RQ.run_items(args.method or [])]
        if args.rep > 1:
            items = [(RQ.rep_kind(k, args.rep), n, i, d) for k, n, i, d in items]
        print(RQ.run_stage(items, DEV, args.workers))
    elif args.stage == "ground":
        print(ground_stage(ground_items(args.method or []), DEV, args.workers))
    elif args.stage == "pairwise":
        print(pairwise_stage(args.method or [], args.judge, args.workers))
    elif args.stage == "top_b":
        print(" ".join(top_b(args.n)))
    elif args.stage == "finalists":
        print(" ".join(finalists(args.n)))
    else:
        result = report()
        atomic_json(OUT / "analysis_quality.json", result)
        (OUT / "analysis_quality.md").write_text(render(result))
        print(render(result))


if __name__ == "__main__":
    main()
