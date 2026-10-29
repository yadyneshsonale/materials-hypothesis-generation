"""Experiment 39 (loop.md 20.1): why more information does not raise the score. Diagnostics and the report.

Usage (each stage is resumable):
  python diag_analysis.py hints        freeze the oracle hints: each paper's study type (majority of the GPT-5.6 labels)
                                       and its lever in at most 20 words (GPT-5.6, from the answer key)
  python diag_analysis.py packlabels   GPT-5.6 rates every passage of each unit's Q16, Q64 and T16 pack against the key
  python diag_analysis.py corpuslabels GPT-5.6 rates every paper of each unit's web corpus against the key
  python diag_analysis.py classify     gpt-4o-mini study types of the pack papers not yet classified (target-free)
  python diag_analysis.py pairwise     target-free quality judge: Q64 and T16 vs closed-book, both orders, 3 judges
  python diag_analysis.py retest       GPT-5.6 and DeepSeek judge the closed-book writer's sample-1 runs again
  python diag_analysis.py samesession  post hoc: GPT-5.6 judges the Q16 runs and the writer's sample-2 runs again
  python diag_analysis.py report       loop_diag/analysis_diag.json and analysis_diag.md
All labels are analysis only and are never shown to a method.
"""

from __future__ import annotations

import os

_E = os.path.join(os.path.dirname(os.path.abspath(__file__)), "experiments", "high_temperature_hea_qwen35b")
os.environ.setdefault("MATHG_CASES_DIR", os.path.join(_E, "benchmark_v3_1", "cases"))
os.environ.setdefault("MATHG_LOOP_ROOT", os.path.join(_E, "loop_diag"))

import argparse  # noqa: E402
import json  # noqa: E402
import random  # noqa: E402
import re  # noqa: E402
import statistics  # noqa: E402
from collections import Counter, defaultdict  # noqa: E402
from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any, Callable  # noqa: E402

import hypo_loop as H  # noqa: E402
import llm_client as lc  # noqa: E402
import loop_methods as LM  # noqa: E402
import round4_offline as R  # noqa: E402
import web_analysis as W  # noqa: E402
from hypothesis_evidence_v2 import atomic_json  # noqa: E402
from stage_metrics import CROSS_JUDGE  # noqa: E402
from temporal_eval_v3 import _blind_candidate, judge_absolute  # noqa: E402
from temporal_hypothesis_benchmark import _SCORE_SYSTEM, _read_json, _validate_score  # noqa: E402

A, V = W.A, W.V
E = W.E
DIAG = H.OUT  # loop_diag/ unless MATHG_LOOP_ROOT says otherwise
LOOP, WEB = E / "loop", E / "loop_web"
JUDGES = ("gpt", "deep")
WRITER = "writer_only_b_o3mini"
Q16, Q64, T16 = "web_text_chunks_b_o3mini", "web_text_64k_b_o3mini", "oracle_targetpack_b_o3mini"
T16R, Q16R = "oracle_targetpack_read_b_o3mini", "read_web_chunks_b_o3mini"
HINTS = ("oracle_hint_class_b_o3mini", "oracle_hint_lever_b_o3mini", "oracle_hint_full_b_o3mini")
PACKS = {"Q16": Q16, "Q64": Q64, "T16": T16}
O1 = "o1_2024-12-17"
PAIR_JUDGES = ("gpt56", "deepseek", "o1")
PAIRS = {"Q64_vs_closed": Q64, "T16_vs_closed": T16}
INFO_AXIS = (("closed-book", WRITER), ("text 4,000", "web_text_4k_b_o3mini"), ("text 16,000", Q16),
             ("text 64,000", Q64), ("1 paper", "web_papers_n1_b_o3mini"), ("3 papers", "web_papers_n3_b_o3mini"),
             ("10 papers", "web_papers_n10_b_o3mini"), ("30 papers", "web_papers_n30_b_o3mini"),
             ("10 random papers", "web_papers_random10_b_o3mini"))
KEY_FIELDS = ("material_initial_state", "intervention", "structural_mediator", "mechanism")

LEVER_SYSTEM = (
    "You are given the intervention of a published materials-science study and its starting material. Write the "
    "study's lever: the kind of change or study and the specific element, phase, processing route, treatment, "
    "technique or agent involved, in at most 20 words. Leave out every amount, composition ratio, temperature, time, "
    "rate, parameter value and result. Return JSON {\"lever\": str}."
)
ITEM_LABEL_SYSTEM = (
    "You compare items from earlier papers (passages, or titles with abstracts) with the actual study of a later paper "
    "(the target). For each numbered item, rate lever_match against the target's intervention: 0 = the item describes "
    "no intervention or study of the target's kind; 1 = the same kind of intervention or study, but a different "
    "specific lever; 2 = the same lever (element, phase, route, technique or agent) with different specifics "
    "(amounts, parameters or material system); 3 = essentially the target's intervention. Rate what each item "
    "describes as done or proposed, whoever did it. Return JSON {\"items\": [{\"id\": int, \"lever_match\": int}]} "
    "with one entry per item."
)
QUALITY_PAIR_SYSTEM = (
    "You are an experienced materials scientist reviewing two research hypotheses written, before the work is done, "
    "for the same research question on high-temperature high-entropy alloys. Decide which one is the better research "
    "proposal to pursue. Consider: (1) does it address the limitation the question states, within its constraints; "
    "(2) is the mechanism physically sound for this material and regime; (3) is it specific and testable: a clear "
    "intervention, conditions, a measurable predicted outcome against a baseline, and a decisive experiment; (4) is it "
    "well grounded: claims consistent with established knowledge and with any cited evidence, and no invented precise "
    "values presented as fact; (5) is it a substantive, non-trivial contribution. Do not prefer a hypothesis for being "
    "longer or for citing more evidence as such. Return JSON {\"winner\": \"A\" | \"B\" | \"tie\", \"confidence\": "
    "number from 0 to 1, \"reason\": \"one or two sentences\"}."
)


def _parallel(jobs: list[Any], fn: Callable[[Any], None], workers: int, tag: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    with ThreadPoolExecutor(workers) as pool:
        futures = {pool.submit(fn, j): j for j in jobs}
        for future in as_completed(futures):
            try:
                future.result()
                counts["done"] += 1
            except Exception as error:  # noqa: BLE001 - logged; a rerun resumes
                counts["failed"] += 1
                print(f"[{tag}] {type(error).__name__}: {str(error)[:200]}", flush=True)
    return {"jobs": len(jobs), **counts}


def root_of(method: str) -> Path:
    if method in (Q16, Q64) or method.startswith("web_"):
        return WEB
    if method == WRITER:
        return LOOP
    return DIAG


def runs_of(method: str) -> list[dict[str, Any]]:
    return [r for r in W.runs(root_of(method), method) if r.get("status") == "ok"
            and r.get("benchmark", "v3.1") in R.BENCHMARKS]


def key_of(run: dict[str, Any]) -> tuple[str, str, int]:
    return run["paper_id"], run["query_level"], int(run["sample"])


# ---------------------------------------------------------------- hints (frozen before generation)

def paper_types() -> dict[str, str]:
    """Each paper's study type: the majority of every GPT-5.6 label's target_type, over all configurations."""
    votes: dict[str, Counter[str]] = defaultdict(Counter)
    for root in (LOOP, WEB, E / "loop_pcd", E / "loop_r4"):
        for path in root.glob("*/labels/PMC*.json"):
            t = _read_json(path).get("target_type")
            if t in LM.STUDY_TYPES:
                votes[path.name.split("__")[0]][t] += 1
    return {p: sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] for p, c in sorted(votes.items())}


def hints_stage() -> dict[str, Any]:
    if LM.ORACLE_HINTS.exists():
        return {"frozen": True, "papers": len(json.loads(LM.ORACLE_HINTS.read_text()))}
    cases = H.cases()
    types = paper_types()

    def lever(paper: str) -> tuple[str, str]:
        t = cases[paper]["hidden_target"]
        raw = lc.judge_chat_json(LEVER_SYSTEM, json.dumps({"material_initial_state": t.get("material_initial_state"),
                                                           "intervention": t.get("intervention")},
                                                          ensure_ascii=False), max_tokens=2000)
        return paper, str((raw or {}).get("lever", "")).strip()

    with ThreadPoolExecutor(8) as pool:
        levers = dict(pool.map(lever, sorted(cases)))
    hints = {p: {"class": types[p], "lever": levers[p], "labeller": lc.judge_info()} for p in sorted(cases)}
    missing = [p for p, h in hints.items() if not h["lever"]]
    if missing:
        raise SystemExit(f"no lever for {missing}; rerun")
    atomic_json(LM.ORACLE_HINTS, hints)
    return {"papers": len(hints), "classes": dict(Counter(h["class"] for h in hints.values()))}


# ---------------------------------------------------------------- what the information contains (A1-A3)

def packs() -> dict[str, dict[tuple[str, str], list[str]]]:
    """Per pack type and unit, the record IDs the sample-1 run saw (retrieval is deterministic per unit)."""
    out: dict[str, dict[tuple[str, str], list[str]]] = {}
    for name, method in PACKS.items():
        out[name] = {(r["paper_id"], r["query_level"]): list(r["seen_ids"]) for r in runs_of(method)
                     if int(r["sample"]) == 1}
    return out


def pack_identity() -> dict[str, Any]:
    """Sanity check: both samples of a unit saw the same pack."""
    out = {}
    for name, method in PACKS.items():
        by_unit: dict[tuple[str, str], list[list[str]]] = defaultdict(list)
        for r in runs_of(method):
            by_unit[(r["paper_id"], r["query_level"])].append(sorted(r["seen_ids"]))
        out[name] = {"units": len(by_unit), "identical": sum(1 for v in by_unit.values() if len(v) == 2
                                                             and v[0] == v[1])}
    return out


def target_payload(case: dict[str, Any]) -> dict[str, Any]:
    return {k: case["hidden_target"].get(k) for k in KEY_FIELDS}


def label_items(case: dict[str, Any], items: list[dict[str, Any]]) -> dict[int, int]:
    raw = lc.judge_chat_json(ITEM_LABEL_SYSTEM, json.dumps({"target": target_payload(case), "items": items},
                                                           ensure_ascii=False), max_tokens=12000)
    out: dict[int, int] = {}
    for item in (raw or {}).get("items", []) if isinstance(raw, dict) else []:
        try:
            out[int(item["id"])] = max(0, min(3, int(item["lever_match"])))
        except (KeyError, TypeError, ValueError):
            continue
    missing = [i["id"] for i in items if i["id"] not in out]
    if len(missing) > len(items) // 10:
        raise ValueError(f"{len(missing)} of {len(items)} items unlabelled")
    return out


def packlabels_stage(workers: int) -> dict[str, Any]:
    cases = H.cases()
    evidence = W.Evidence()
    jobs = []
    for name, by_unit in packs().items():
        for (paper, level), ids in sorted(by_unit.items()):
            path = DIAG / "pack_labels" / name / f"{paper}__{level}.json"
            if not path.exists():
                jobs.append((name, paper, level, ids, path))

    def job(j: tuple[str, str, str, list[str], Path]) -> None:
        name, paper, level, ids, path = j
        records = [evidence.web(rid) for rid in ids]
        items = [{"id": n + 1, "text": r.text[:1600]} for n, r in enumerate(records) if r is not None]
        labels = label_items(cases[paper], items)
        atomic_json(path, {"pack": name, "paper_id": paper, "level": level, "labeller": lc.judge_info(),
                           "items": [{"record_id": ids[i["id"] - 1], "lever_match": labels.get(i["id"])}
                                     for i in items]})

    return _parallel(jobs, job, workers, "packlabels")


def corpus_papers(paper: str, level: str) -> list[dict[str, Any]]:
    corpus = _read_json(R.WEB / "corpora" / paper / f"{level}.json")
    return [s for s in corpus["seeds"] + corpus.get("expansion", [])]


def corpuslabels_stage(workers: int) -> dict[str, Any]:
    cases = H.cases()
    jobs = [(p, lvl) for p in sorted(cases) for lvl in A.V31_LEVELS
            if (R.WEB / "corpora" / p / f"{lvl}.json").exists()
            and not (DIAG / "corpus_labels" / f"{p}__{lvl}.json").exists()]

    def job(j: tuple[str, str]) -> None:
        paper, level = j
        items, ids = [], []
        for s in corpus_papers(paper, level):
            path = R.WEB / "papers" / f"{s['pmcid']}.json"
            if not path.exists():
                continue
            d = _read_json(path)
            ids.append(s["pmcid"])
            items.append({"id": len(ids), "text": f"{d.get('title', '')}. {(d.get('abstract') or '')[:600]}"})
        labels = label_items(cases[paper], items)
        atomic_json(DIAG / "corpus_labels" / f"{paper}__{level}.json",
                    {"paper_id": paper, "level": level, "labeller": lc.judge_info(),
                     "items": [{"pmcid": ids[i["id"] - 1], "lever_match": labels.get(i["id"])} for i in items]})

    return _parallel(jobs, job, workers, "corpuslabels")


def classify_stage(workers: int) -> dict[str, Any]:
    """gpt-4o-mini study types (target-free) of pack papers that experiment 38's classification did not cover."""
    cache_path = R.OUT / "paper_classes.json"
    cache = _read_json(cache_path)
    wanted = sorted({rid.split("::")[0] for by_unit in packs().values() for ids in by_unit.values() for rid in ids}
                    - set(cache))

    def job(pmcid: str) -> None:
        d = _read_json(R.WEB / "papers" / f"{pmcid}.json")
        raw = lc.trapi_chat_json(R.CLASSIFIER, R.CLASSIFY_SYSTEM,
                                 json.dumps({"title": d.get("title", ""), "abstract": (d.get("abstract") or "")[:2500]},
                                            ensure_ascii=False), max_tokens=300, temperature=0.0, retries=8)
        cls = (raw or {}).get("class") if isinstance(raw, dict) else None
        cache[pmcid] = {"class": cls if cls in R.TARGET_TYPES else "other", "study": str((raw or {}).get("study", ""))}

    result = _parallel(wanted, job, workers, "classify")
    atomic_json(cache_path, {k: cache[k] for k in sorted(cache)})
    return result


# ---------------------------------------------------------------- target-free quality judge (C2)

def pair_call(judge: str, user: str) -> Any:
    if judge == "gpt56":
        return lc.judge_chat_json(QUALITY_PAIR_SYSTEM, user, max_tokens=8000)
    if judge == "deepseek":
        return lc.trapi_chat_json(CROSS_JUDGE["deployment"], QUALITY_PAIR_SYSTEM, user, max_tokens=4000,
                                  token_field=CROSS_JUDGE["token_field"], temperature=CROSS_JUDGE["temperature"],
                                  retries=8)
    return lc.trapi_chat_json(O1, QUALITY_PAIR_SYSTEM, user, max_tokens=16000, token_field="max_completion_tokens",
                              temperature=None, retries=8)


def pairwise_stage(workers: int, judges: tuple[str, ...] = PAIR_JUDGES) -> dict[str, Any]:
    closed = {key_of(r): r for r in runs_of(WRITER)}
    jobs = []
    for comparison, method in PAIRS.items():
        for r in runs_of(method):
            k = key_of(r)
            if k not in closed:
                continue
            for judge in judges:
                for order in ("closed_first", "info_first"):
                    path = DIAG / "pairwise" / comparison / judge / f"{k[0]}__{k[1]}__s{k[2]}__{order}.json"
                    if not path.exists():
                        jobs.append((comparison, judge, order, closed[k], r, path))

    def job(j: tuple[Any, ...]) -> None:
        comparison, judge, order, x, y, path = j
        first, second = (x, y) if order == "closed_first" else (y, x)
        ga, ea = _blind_candidate(first)
        gb, eb = _blind_candidate(second)
        user = json.dumps({"research_question": x["query"],
                           "candidate_A": {"hypothesis": ga, "cited_evidence": ea},
                           "candidate_B": {"hypothesis": gb, "cited_evidence": eb}}, ensure_ascii=False)
        raw = pair_call(judge, user)
        raw = raw if isinstance(raw, dict) else {}
        winner = str(raw.get("winner", "tie")).strip().upper()
        winner = winner if winner in ("A", "B", "TIE") else "TIE"
        info_side = "B" if order == "closed_first" else "A"
        atomic_json(path, {"comparison": comparison, "judge": judge, "order": order, "winner": winner,
                           "info_won": winner == info_side, "closed_won": winner not in (info_side, "TIE"),
                           "confidence": raw.get("confidence"), "reason": str(raw.get("reason", ""))[:600],
                           "closed_run": x["run_id"], "info_run": y["run_id"]})

    rng = random.Random(int(os.environ.get("MATHG_PENDING_SHUFFLE", "0") or 0))
    if os.environ.get("MATHG_PENDING_SHUFFLE"):
        rng.shuffle(jobs)
    return _parallel(jobs, lambda j: None if j[5].exists() else job(j), workers, "pairwise")


# ---------------------------------------------------------------- judge test-retest (C4)

def retest_stage(workers: int) -> dict[str, Any]:
    cases = H.cases()
    jobs = []
    for r in runs_of(WRITER):
        if int(r["sample"]) != 1:
            continue
        for judge in ("gpt56", "deepseek"):
            path = DIAG / "retest" / judge / f"{r['run_id']}.json"
            if not path.exists():
                jobs.append((judge, r, path))

    def job(j: tuple[str, dict[str, Any], Path]) -> None:
        judge, run, path = j
        case = cases[run["paper_id"]]
        if judge == "gpt56":
            atomic_json(path, judge_absolute(run, case))
            return
        generation, evidence = _blind_candidate(run)
        payload = {"query": run["query"], "hidden_target": case["hidden_target"],
                   "generated_hypothesis": generation, "cited_evidence": evidence}
        raw = lc.trapi_chat_json(CROSS_JUDGE["deployment"], _SCORE_SYSTEM, json.dumps(payload, ensure_ascii=False),
                                 max_tokens=8000, token_field=CROSS_JUDGE["token_field"],
                                 temperature=CROSS_JUDGE["temperature"], retries=8)
        score = _validate_score(raw)
        atomic_json(path, {"run_id": run["run_id"], "judge": f"trapi:{CROSS_JUDGE['deployment']}",
                           "scores": score["scores"], "classification": score.get("classification", "")})

    return _parallel(jobs, job, workers, "retest")


def samesession_stage(workers: int) -> dict[str, Any]:
    """Post hoc (loop.md 20.2): C4 found GPT-5.6 scoring the same runs higher on re-judging, so the baselines that were
    judged days earlier are judged again now. The closed-book writer's sample-1 runs reuse the C4 retest judgments."""
    cases = H.cases()
    jobs = []
    for method in (Q16, WRITER):
        for r in runs_of(method):
            if method == WRITER and int(r["sample"]) == 1:
                continue
            path = DIAG / "same_session" / method / f"{r['run_id']}.json"
            if not path.exists():
                jobs.append((r, path))
    if os.environ.get("MATHG_PENDING_SHUFFLE"):  # a second process takes the jobs in another order
        random.Random(int(os.environ["MATHG_PENDING_SHUFFLE"])).shuffle(jobs)

    def job(j: tuple[dict[str, Any], Path]) -> None:
        if not j[1].exists():  # written by another process after the job list was made
            atomic_json(j[1], judge_absolute(j[0], cases[j[0]["paper_id"]]))

    return _parallel(jobs, job, workers, "samesession")


def same_session_scores(method: str) -> dict[str, float]:
    """Per-paper GPT-5.6 reconstruction from the same-session judgments of a baseline."""
    data: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    paths = list((DIAG / "same_session" / method).glob("PMC*.json"))
    if method == WRITER:
        paths += list((DIAG / "retest" / "gpt56").glob("PMC*.json"))
    for path in paths:
        paper, level = path.name.split("__")[:2]
        data[paper][level].append(R.recon(_read_json(path)["scores"]))
    return A.per_paper(data)


def same_session() -> dict[str, Any]:
    pairs = [(T16, Q16), (Q16R, Q16)] + [(m, WRITER) for m in HINTS]
    items = []
    for a, b in pairs:
        base = same_session_scores(b)
        items.append({"config": a, "vs": f"{b} (re-judged)", "baseline_runs_rejudged": len(
            list((DIAG / "same_session" / b).glob("*.json"))) + (135 if b == WRITER else 0),
                      **A.paired(scores(a, "gpt"), base)})
    return {"gpt": items, "baseline_means": {b: W.A_mean(list(same_session_scores(b).values())) for b in (Q16, WRITER)},
            "baseline_means_original": {b: W.A_mean(list(scores(b, "gpt").values())) for b in (Q16, WRITER)}}


# ---------------------------------------------------------------- copying (B2), lexical

ELEMENTS = set(("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb "
                "Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu "
                "Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi").split())
FORMULA = re.compile(r"\b(?:[A-Z][a-z]?(?:\d+(?:\.\d+)?)?){2,}\b")
NUMBER = re.compile(r"(\d+(?:\.\d+)?)\s*(°C|°\s*C|K\b|h\b|min\b|MPa|GPa|wt\.?\s?%|at\.?\s?%|%|µm|μm|nm\b|mm\b)")
WORD = re.compile(r"[a-z][a-z\-]{5,}")
HYP_FIELDS = ("intervention", "conditions", "structural_mediator", "mechanism", "predicted_outcome")


def formulas(text: str) -> set[str]:
    out = set()
    for m in FORMULA.finditer(text):
        token = m.group(0)
        parts = re.findall(r"([A-Z][a-z]?)(\d+(?:\.\d+)?)?", token)
        if all(p[0] in ELEMENTS for p in parts) and any(c.islower() or c.isdigit() for c in token):
            out.add(token)
    return out


def numbers(text: str) -> set[str]:
    return {a + re.sub(r"[\s.]", "", b) for a, b in NUMBER.findall(text)}


def words(text: str) -> set[str]:
    return set(WORD.findall(text.lower()))


def terms(generation: dict[str, Any], question: str) -> dict[str, set[str]]:
    text = " ".join(str(generation.get(f) or "") for f in HYP_FIELDS)
    qf, qn, qw = formulas(question), numbers(question), words(question)
    return {"formulas": formulas(text) - qf, "numbers": numbers(text) - qn, "words": words(text) - qw}


def found(t: dict[str, set[str]], evidence: str) -> dict[str, float | None]:
    ef, en, ew = formulas(evidence), numbers(evidence), words(evidence)
    return {"formulas": len(t["formulas"] & ef) / len(t["formulas"]) if t["formulas"] else None,
            "numbers": len(t["numbers"] & en) / len(t["numbers"]) if t["numbers"] else None,
            "words": len(t["words"] & ew) / len(t["words"]) if t["words"] else None}


def copying(method: str) -> dict[str, Any]:
    """Share of the hypothesis's specific terms found in the evidence it saw, against the closed-book writer's
    hypothesis of the same unit and sample measured against the same evidence (the control)."""
    evidence = W.Evidence()
    closed = {key_of(r): r for r in runs_of(WRITER)}
    per: dict[str, dict[str, list[float]]] = {k: defaultdict(list) for k in ("formulas", "numbers", "words")}
    raw: dict[str, list[tuple[float, float]]] = {k: [] for k in ("formulas", "numbers", "words")}
    for r in runs_of(method):
        c = closed.get(key_of(r))
        if c is None or not r["seen_ids"]:
            continue
        text = " ".join(rec.text for rec in (evidence.web(rid) for rid in r["seen_ids"]) if rec is not None)
        mine = found(terms(r["generation"], r["query"]), text)
        ctrl = found(terms(c["generation"], c["query"]), text)
        for k in per:
            if mine[k] is not None and ctrl[k] is not None:
                per[k][r["paper_id"]].append(mine[k] - ctrl[k])
                raw[k].append((mine[k], ctrl[k]))
    out: dict[str, Any] = {}
    for k in per:
        if not raw[k]:
            out[k] = None
            continue
        out[k] = {"runs": len(raw[k]), "with_evidence": round(statistics.fmean(a for a, _ in raw[k]), 3),
                  "control": round(statistics.fmean(b for _, b in raw[k]), 3),
                  "difference": R.bootstrap({p: v for p, v in per[k].items()})}
    return out


# ---------------------------------------------------------------- report helpers

def labels_of(method: str) -> dict[tuple[str, str, int], dict[str, Any]]:
    root = root_of(method)
    out = {}
    for r in runs_of(method):
        path = root / method / "labels" / f"{r['run_id']}.json"
        if path.exists():
            out[key_of(r)] = _read_json(path)
    return out


def pack_levers() -> dict[str, dict[tuple[str, str], int]]:
    out: dict[str, dict[tuple[str, str], int]] = {}
    for name in PACKS:
        out[name] = {}
        for path in sorted((DIAG / "pack_labels" / name).glob("*.json")):
            d = _read_json(path)
            values = [i["lever_match"] for i in d["items"] if i["lever_match"] is not None]
            out[name][(d["paper_id"], d["level"])] = max(values) if values else 0
    return out


def corpus_levers() -> dict[tuple[str, str], int]:
    out = {}
    for path in sorted((DIAG / "corpus_labels").glob("*.json")):
        d = _read_json(path)
        values = [i["lever_match"] for i in d["items"] if i["lever_match"] is not None]
        out[(d["paper_id"], d["level"])] = max(values) if values else 0
    return out


def share(values: list[bool]) -> float | None:
    return round(statistics.fmean(values), 3) if values else None


def uptake(method: str, pack: dict[tuple[str, str], int]) -> dict[str, Any]:
    """B1: lever >= 2 with the pack minus the closed-book writer's, on the same units, split by whether the pack
    contains the paper's lever."""
    mine, ctrl = labels_of(method), labels_of(WRITER)
    out: dict[str, Any] = {}
    for group, test in (("pack_has_lever", lambda v: v >= 2), ("pack_lacks_lever", lambda v: v < 2)):
        diffs: dict[str, list[float]] = defaultdict(list)
        a_all, b_all = [], []
        for (paper, level, sample), lab in mine.items():
            if (paper, level) not in pack or not test(pack[(paper, level)]):
                continue
            c = ctrl.get((paper, level, sample))
            if c is None:
                continue
            a, b = float(lab["lever_match"] >= 2), float(c["lever_match"] >= 2)
            a_all.append(a)
            b_all.append(b)
            diffs[paper].append(a - b)
        out[group] = {"runs": len(a_all), "lever_ge2_with_pack": share(a_all), "lever_ge2_closed_book": share(b_all),
                      "uptake": R.bootstrap(diffs) if diffs else None}
    return out


def anchoring(method: str, pack_ids: dict[tuple[str, str], list[str]]) -> dict[str, Any]:
    """Whether the hypothesis's study type equals the modal study type of the pack's papers, with the pack vs the
    closed-book writer on the same unit."""
    classes = _read_json(R.OUT / "paper_classes.json")
    mine, ctrl = labels_of(method), labels_of(WRITER)
    a_all, b_all = [], []
    diffs: dict[str, list[float]] = defaultdict(list)
    for (paper, level, sample), lab in mine.items():
        ids = pack_ids.get((paper, level))
        c = ctrl.get((paper, level, sample))
        if not ids or c is None:
            continue
        counts = Counter(classes[rid.split("::")[0]]["class"] for rid in ids if rid.split("::")[0] in classes)
        if not counts:
            continue
        modal = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        a, b = float(lab["intervention_class"] == modal), float(c["intervention_class"] == modal)
        a_all.append(a)
        b_all.append(b)
        diffs[paper].append(a - b)
    return {"runs": len(a_all), "matches_pack_modal_type_with_pack": share(a_all),
            "matches_pack_modal_type_closed_book": share(b_all), "difference": R.bootstrap(diffs) if diffs else None}


_SCORES: dict[tuple[str, str], dict[str, float]] = {}


def scores(method: str, judge: str) -> dict[str, float]:
    if (method, judge) not in _SCORES:
        _SCORES[(method, judge)] = W.per_paper(root_of(method), method, judge)
    return _SCORES[(method, judge)]


def family(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    out: dict[str, Any] = {j: V.holm_family([{"config": a, "vs": b, **A.paired(scores(a, j), scores(b, j))}
                                             for a, b in pairs]) for j in JUDGES}
    decision = {}
    for g, d in zip(out["gpt"], out["deep"]):
        key = f"{g['config']} vs {g['vs']}"
        if not g.get("papers"):
            decision[key] = "no data"
        elif g["ci95"][0] > 0 and d.get("diff", 0) > 0:
            decision[key] = "higher"
        elif g["ci95"][1] < 0 and d.get("diff", 0) < 0:
            decision[key] = "lower"
        else:
            decision[key] = "no detectable difference"
    out["decision"] = decision
    return out


def run_profile(method: str) -> dict[str, Any]:
    root = root_of(method)
    judged = {j: [] for j in JUDGES}
    for r in runs_of(method):
        for j, folder in (("gpt", "gpt56"), ("deep", "deepseek")):
            path = root / method / "judgments" / folder / f"{r['run_id']}.json"
            if path.exists():
                judged[j].append(_read_json(path))
    labs = labels_of(method)
    out: dict[str, Any] = {"runs": len(runs_of(method)), "papers": len(scores(method, "gpt")),
                           "gpt": W.A_mean(list(scores(method, "gpt").values())),
                           "deep": W.A_mean(list(scores(method, "deep").values())),
                           "lever_ge2": share([lb["lever_match"] >= 2 for lb in labs.values()])}
    for j in JUDGES:
        out[f"dims_{j}"] = {d: W.A_mean([x["scores"][d] for x in judged[j]]) for d in H.ALL_DIMENSIONS}
        n = len(judged[j]) or 1
        out[f"classes_{j}"] = {c: round(v / n, 3) for c, v in sorted(Counter(x.get("classification", "")
                                                                               for x in judged[j]).items())}
    return out


def info_axis() -> list[dict[str, Any]]:
    """C3: along the amount of information, paired against the closed-book writer on common papers."""
    rows = []
    for label, method in INFO_AXIS:
        p = run_profile(method)
        row = {"label": label, "method": method, **{k: p[k] for k in ("runs", "papers", "gpt", "deep", "lever_ge2")},
               "unsupported_gpt": p["classes_gpt"].get("unsupported"),
               "plausible_alternative_gpt": p["classes_gpt"].get("plausible_alternative"),
               "partial_or_exact_gpt": round(p["classes_gpt"].get("partial_reconstruction", 0)
                                             + p["classes_gpt"].get("exact_reconstruction", 0), 3),
               "unsupported_deep": p["classes_deep"].get("unsupported"),
               **{f"gpt_{d}": p["dims_gpt"][d] for d in ("evidence_validity", "novelty", "baseline_quality",
                                                          "boundary_quality", "experiment_discriminability",
                                                          "problem_alignment", "intervention_reconstruction")}}
        if method != WRITER:
            row["vs_closed_gpt"] = A.paired(scores(method, "gpt"), scores(WRITER, "gpt"))
            row["vs_closed_deep"] = A.paired(scores(method, "deep"), scores(WRITER, "deep"))
        rows.append(row)
    return rows


def pairwise_results() -> dict[str, Any]:
    out: dict[str, Any] = {}
    items = []
    for comparison in PAIRS:
        out[comparison] = {}
        for judge in PAIR_JUDGES:
            folder = DIAG / "pairwise" / comparison / judge
            by_pair: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
            for path in sorted(folder.glob("*.json")):
                stem, order = path.stem.rsplit("__", 1)
                by_pair[stem][order] = _read_json(path)
            per_paper: dict[str, list[float]] = defaultdict(list)
            first_pos = []
            complete = 0
            for stem, orders in by_pair.items():
                if len(orders) < 2:
                    continue
                complete += 1
                info_both = all(o["info_won"] for o in orders.values())
                closed_both = all(o["closed_won"] for o in orders.values())
                per_paper[stem.split("__")[0]].append(1.0 if info_both else -1.0 if closed_both else 0.0)
                first_pos += [o["winner"] == "A" for o in orders.values()]
            if not per_paper:
                out[comparison][judge] = {"pairs": 0}
                continue
            vals = [v for vs in per_paper.values() for v in vs]
            result = {"pairs": complete, "info_wins_both_orders": share([v == 1.0 for v in vals]),
                      "closed_wins_both_orders": share([v == -1.0 for v in vals]),
                      "inconsistent_or_tie": share([v == 0.0 for v in vals]),
                      "first_position_wins": share(first_pos)}
            paired = A.paired({p: statistics.fmean(v) for p, v in per_paper.items()}, {p: 0.0 for p in per_paper})
            result["net_preference_for_info"] = paired
            out[comparison][judge] = result
            items.append({"config": f"{comparison}:{judge}", **paired})
    holm = V.holm_family(items)
    for item in holm:
        comparison, judge = item["config"].split(":")
        out[comparison][judge]["net_preference_for_info"]["holm_p"] = item["holm_p"]
    return out


def retest_results() -> dict[str, Any]:
    out = {}
    for judge, folder in (("gpt56", "gpt56"), ("deepseek", "deepseek")):
        pairs, per_paper_a, per_paper_b = [], defaultdict(list), defaultdict(list)
        for path in sorted((DIAG / "retest" / judge).glob("*.json")):
            again = _read_json(path)
            first = LOOP / WRITER / "judgments" / folder / path.name
            if not first.exists() or "scores" not in again:
                continue
            a, b = R.recon(_read_json(first)["scores"]), R.recon(again["scores"])
            pairs.append((a, b))
            per_paper_a[path.name.split("__")[0]].append(a)
            per_paper_b[path.name.split("__")[0]].append(b)
        if not pairs:
            out[judge] = {"runs": 0}
            continue
        xa = [statistics.fmean(v) for _, v in sorted(per_paper_a.items())]
        xb = [statistics.fmean(v) for _, v in sorted(per_paper_b.items())]
        rho_runs = R.spearman([a for a, _ in pairs], [b for _, b in pairs])
        rho_papers = R.spearman(xa, xb)
        out[judge] = {"runs": len(pairs), "rho_runs": round(rho_runs, 3) if rho_runs is not None else None,
                      "mean_abs_diff_runs": round(statistics.fmean(abs(a - b) for a, b in pairs), 3),
                      "identical_runs": share([a == b for a, b in pairs]),
                      "first_mean": round(statistics.fmean(a for a, _ in pairs), 3),
                      "second_mean": round(statistics.fmean(b for _, b in pairs), 3),
                      "rho_papers": round(rho_papers, 3) if rho_papers is not None else None, "papers": len(xa)}
    return out


def leakage() -> dict[str, Any]:
    cases = H.cases()
    evidence = W.Evidence()
    violations, checked, unresolved = [], 0, 0
    for method in LM.DIAG_CONFIGS:
        for run in W.runs(DIAG, method):
            cutoff = cases[run["paper_id"]]["publication_date"]
            for rid in run["seen_ids"]:
                record = evidence.web(rid)
                if record is None:
                    unresolved += 1
                    continue
                checked += 1
                dates = [x for x in (record.structured or {}).get("dates", {}).values() if x]
                if any(x >= cutoff for x in dates + [record.publication_date]):
                    violations.append(f"{run['run_id']}: {rid}")
    return {"counters": W.counters(DIAG), "web_records_rechecked": checked, "unresolved": unresolved,
            "date_violations": len(violations), "examples": violations[:10]}


def report() -> dict[str, Any]:
    pl, ids = pack_levers(), packs()
    corpus = corpus_levers()
    contains = {name: {"units": len(v), "lever_ge2": share([x >= 2 for x in v.values()]),
                       "lever_ge1": share([x >= 1 for x in v.values()])} for name, v in pl.items()}
    contains["corpus"] = {"units": len(corpus), "lever_ge2": share([x >= 2 for x in corpus.values()]),
                          "lever_ge1": share([x >= 1 for x in corpus.values()])}
    r: dict[str, Any] = {
        "pack_identity": pack_identity(),
        "A_contains_lever": contains,
        "A4_oracle_selection": family([(T16, Q16)]),
        "B1_uptake": {name: uptake(method, pl[name]) for name, method in PACKS.items()},
        "B1_uptake_reader": {"T16_read": uptake(T16R, pl["T16"]), "Q16_read": uptake(Q16R, pl["Q16"])},
        "B2_copying": {name: copying(method) for name, method in PACKS.items()},
        "B2_anchoring": {name: anchoring(method, ids[name]) for name, method in PACKS.items()},
        "B3_reader": family([(T16R, T16), (Q16R, Q16)]),
        "C1_hints": family([(m, WRITER) for m in HINTS]),
        "C2_pairwise": pairwise_results(),
        "C3_info_axis": info_axis(),
        "C4_retest": retest_results(),
        "profiles": {m: run_profile(m) for m in (WRITER, Q16, Q64) + LM.DIAG_CONFIGS},
        "D_same_session_post_hoc": same_session(),
        "leakage": leakage(),
    }
    r["decisions"] = decide(r)
    return r


def decide(r: dict[str, Any]) -> dict[str, str]:
    """The pre-registered rules of loop.md 20.1."""
    out = {}
    a = r["A_contains_lever"]
    g = r["A4_oracle_selection"]["gpt"][0]
    d = r["A4_oracle_selection"]["deep"][0]
    t16_better = bool(g.get("papers")) and g["ci95"][0] > 0 and d.get("diff", 0) > 0
    out["A_bad_information"] = ("supported" if (a["Q16"]["lever_ge2"] or 0) <= 0.25 and t16_better else
                                "not supported")
    up = (r["B1_uptake"]["T16"]["pack_has_lever"] or {}).get("uptake") or {}
    low_uptake = (up.get("diff") if up else 1.0) < 0.15 and (a["T16"]["lever_ge2"] or 0) >= 0.25
    copy = (r["B2_copying"]["T16"] or {}).get("words") or {}
    copied = ((copy.get("difference") or {}).get("diff") or 0) >= 0.20
    out["B_not_using_information"] = "supported" if low_uptake else "not supported"
    out["B_repeating_instead_of_reasoning"] = "supported" if low_uptake and copied else "not supported"
    c2 = r["C2_pairwise"]
    unfair = []
    for comparison, method in PAIRS.items():
        prefs = {j: (c2[comparison].get(j) or {}).get("net_preference_for_info") or {} for j in PAIR_JUDGES}
        o1_pref = (prefs["o1"].get("ci95") or [0, 0])[0] > 0
        other = any((prefs[j].get("ci95") or [0, 0])[0] > 0 for j in ("gpt56", "deepseek"))
        recon = A.paired(scores(method, "gpt"), scores(WRITER, "gpt"))
        not_higher = not (recon.get("ci95") and recon["ci95"][0] > 0)
        unfair.append(o1_pref and other and not_higher)
    out["C_unfair_to_information"] = "supported" if any(unfair) else "not supported"
    lever = next(i for i in r["C1_hints"]["gpt"] if i["config"] == "oracle_hint_lever_b_o3mini")
    out["C_little_credit_for_the_right_idea"] = ("supported" if (lever.get("a_mean") or 0) < 1.5 else "not supported")
    return out


# ---------------------------------------------------------------- markdown

def _cell(i: dict[str, Any] | None) -> str:
    if not i or not i.get("papers"):
        return "-"
    holm = f", Holm p {i['holm_p']}" if "holm_p" in i else ""
    return f"{i['diff']:+.3f} {V._ci(i)} ({i['papers']} papers, {i.get('up')}/{i.get('down')}{holm})"


def render(r: dict[str, Any]) -> str:
    L = ["# Experiment 39: why more information does not raise the score", "",
         "Pre-registered in loop.md 20.1. Oracle configurations use the answer key on purpose: diagnostics, not methods.",
         "", "## Decisions (pre-registered rules)", ""]
    L += [f"- {k}: **{v}**" for k, v in r["decisions"].items()]
    L += ["", "## A. Does the information contain the paper's lever?", "",
          "| information | units | lever ≥ 2 (same lever) | lever ≥ 1 (same kind) |", "|---|---:|---:|---:|"]
    names = {"Q16": "question-retrieved 16,000 characters", "Q64": "question-retrieved 64,000 characters",
             "T16": "oracle-selected 16,000 characters", "corpus": "whole web corpus (titles and abstracts)"}
    for k, v in r["A_contains_lever"].items():
        L.append(f"| {names[k]} | {v['units']} | {v['lever_ge2']} | {v['lever_ge1']} |")
    L += ["", f"Pack identity across samples: {json.dumps(r['pack_identity'])}", ""]
    g, d = r["A4_oracle_selection"]["gpt"][0], r["A4_oracle_selection"]["deep"][0]
    L += ["**A4. Oracle-selected vs question-retrieved evidence** (same retriever, corpus, budget and writer): "
          f"GPT-5.6 {g.get('a_mean')} vs {g.get('b_mean')}, {_cell(g)}; DeepSeek {d.get('a_mean')} vs "
          f"{d.get('b_mean')}, {_cell(d)}.", ""]
    L += ["## B. Does the model use the information?", "", "**B1. Uptake** (lever ≥ 2 with the pack minus closed-book, "
          "same units)", "", "| pack | group | runs | with pack | closed-book | uptake [CI] |", "|---|---|---:|---:|---:|---|"]
    for name, res in list(r["B1_uptake"].items()) + list(r["B1_uptake_reader"].items()):
        for group, v in res.items():
            L.append(f"| {name} | {group} | {v['runs']} | {v['lever_ge2_with_pack']} | {v['lever_ge2_closed_book']} | "
                     f"{_cell(v['uptake'])} |")
    L += ["", "**B2. Copying** (share of the hypothesis's specific terms found in the evidence it saw; control: the "
          "closed-book hypothesis against the same evidence)", "",
          "| pack | term | runs | with evidence | control | difference [CI] |", "|---|---|---:|---:|---:|---|"]
    for name, res in r["B2_copying"].items():
        for term, v in (res or {}).items():
            if v:
                L.append(f"| {name} | {term} | {v['runs']} | {v['with_evidence']} | {v['control']} | "
                         f"{_cell(v['difference'])} |")
    L += ["", "**Study-type anchoring** (the hypothesis has the pack papers' modal study type)", "",
          "| pack | runs | with pack | closed-book | difference [CI] |", "|---|---:|---:|---:|---|"]
    for name, v in r["B2_anchoring"].items():
        L.append(f"| {name} | {v['runs']} | {v['matches_pack_modal_type_with_pack']} | "
                 f"{v['matches_pack_modal_type_closed_book']} | {_cell(v['difference'])} |")
    L += ["", "**B3. Reading step**", "", "| comparison | GPT-5.6 | DeepSeek |", "|---|---|---|"]
    for gi, di in zip(r["B3_reader"]["gpt"], r["B3_reader"]["deep"]):
        L.append(f"| {gi['config']} vs {gi['vs']} | {_cell(gi)} | {_cell(di)} |")
    L += ["", "## C. Is the judging fair?", "", "**C1. Oracle hints** (vs the closed-book writer)", "",
          "| hint | GPT-5.6 | difference [CI] | DeepSeek | difference [CI] | lever ≥ 2 |", "|---|---:|---|---:|---|---:|"]
    for gi, di in zip(r["C1_hints"]["gpt"], r["C1_hints"]["deep"]):
        L.append(f"| {gi['config']} | {gi.get('a_mean')} | {_cell(gi)} | {di.get('a_mean')} | {_cell(di)} | "
                 f"{r['profiles'][gi['config']]['lever_ge2']} |")
    L += ["", "**C2. Target-free quality judge** (pairwise, both orders; +1 when the information-rich hypothesis wins "
          "both orders, −1 when the closed-book one does)", "",
          "| comparison | judge | pairs | info wins | closed-book wins | tie or inconsistent | first position wins | "
          "net preference for information [CI] |", "|---|---|---:|---:|---:|---:|---:|---|"]
    for comparison, by_judge in r["C2_pairwise"].items():
        for judge, v in by_judge.items():
            if not v.get("pairs"):
                L.append(f"| {comparison} | {judge} | 0 | | | | | |")
                continue
            L.append(f"| {comparison} | {judge} | {v['pairs']} | {v['info_wins_both_orders']} | "
                     f"{v['closed_wins_both_orders']} | {v['inconsistent_or_tie']} | {v['first_position_wins']} | "
                     f"{_cell(v['net_preference_for_info'])} |")
    L += ["", "**C3. Along the amount of information** (existing runs; GPT-5.6 classification and dimensions)", "",
          "| information | papers | GPT-5.6 | vs closed-book [CI] | DeepSeek | vs closed-book [CI] | unsupported | "
          "plausible alternative | partial or exact | evidence validity | novelty | intervention |",
          "|---|---:|---:|---|---:|---|---:|---:|---:|---:|---:|---:|"]
    for row in r["C3_info_axis"]:
        L.append(f"| {row['label']} | {row['papers']} | {row['gpt']} | {_cell(row.get('vs_closed_gpt'))} | "
                 f"{row['deep']} | {_cell(row.get('vs_closed_deep'))} | {row['unsupported_gpt']} | "
                 f"{row['plausible_alternative_gpt']} | {row['partial_or_exact_gpt']} | "
                 f"{row['gpt_evidence_validity']} | {row['gpt_novelty']} | {row['gpt_intervention_reconstruction']} |")
    L += ["", f"**C4. Test-retest:** {json.dumps(r['C4_retest'])}", ""]
    ss = r["D_same_session_post_hoc"]
    L += ["## D. Post hoc: baselines re-judged in the same session (GPT-5.6)", "",
          f"Baseline means, original vs re-judged: {json.dumps(ss['baseline_means_original'])} vs "
          f"{json.dumps(ss['baseline_means'])}", "", "| comparison | GPT-5.6 difference [CI] |", "|---|---|"]
    for i in ss["gpt"]:
        L.append(f"| {i['config']} vs {i['vs']} | {_cell(i)} |")
    L.append("")
    L += ["## Profiles", "", "| configuration | runs | GPT-5.6 | DeepSeek | lever ≥ 2 | intervention | conditions | "
          "mechanism | outcome | novelty | unsupported |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for m, p in r["profiles"].items():
        dg = p["dims_gpt"]
        L.append(f"| {m} | {p['runs']} | {p['gpt']} | {p['deep']} | {p['lever_ge2']} | "
                 f"{dg['intervention_reconstruction']} | {dg['condition_agreement']} | {dg['mechanism_agreement']} | "
                 f"{dg['outcome_agreement']} | {dg['novelty']} | {p['classes_gpt'].get('unsupported')} |")
    lk = r["leakage"]
    L += ["", "## Leakage", "", f"Counters over {lk['counters']['runs_checked']} runs: "
          f"{json.dumps(lk['counters']['totals'])}; web records re-checked: {lk['web_records_rechecked']}, date "
          f"violations: {lk['date_violations']}, unresolved: {lk['unresolved']}.", ""]
    return "\n".join(L)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("hints", "packlabels", "corpuslabels", "classify", "pairwise", "retest",
                                          "samesession", "report"))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--judge", action="append", choices=PAIR_JUDGES)
    args = parser.parse_args()
    if args.stage == "report":
        r = report()
        atomic_json(DIAG / "analysis_diag.json", r)
        (DIAG / "analysis_diag.md").write_text(render(r))
        print(render(r))
        return
    stage = {"hints": lambda: hints_stage(), "packlabels": lambda: packlabels_stage(args.workers),
             "corpuslabels": lambda: corpuslabels_stage(args.workers), "classify": lambda: classify_stage(args.workers),
             "pairwise": lambda: pairwise_stage(args.workers, tuple(args.judge or PAIR_JUDGES)),
             "retest": lambda: retest_stage(args.workers),
             "samesession": lambda: samesession_stage(args.workers)}[args.stage]
    print(stage())


if __name__ == "__main__":
    main()
