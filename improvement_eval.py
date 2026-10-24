"""Improvements targeted at the failures found in experiment 15, compared against the experiment-14 baselines.

Failure (experiment 15)                                  -> improved arm
- closed-book prompt says "use only supplied evidence"   -> closed_book_fixed: closed-book with its own prompt that
  with none supplied (refusals, evidence caveats)           allows the model's own pre-cutoff knowledge
- evidence pulls in other systems' mechanisms; citing     -> text_systemmatch / card_systemmatch: before the hypothesis,
  relevant prior work hurts on specific queries              the model appraises every record it may use (system,
                                                            conditions, difference from the target system, whether it
                                                            transfers) and may only use mechanisms that transfer
- mechanisms from the model's own reasoning fail least    -> knowledge_first: draft from own knowledge first (the
                                                            closed_book_fixed run of the same sample), then revise with
                                                            raw-text evidence used only to correct and test the draft
- no arm wins most units                                  -> ensemble_select: the local model picks one of six blinded
                                                            candidates per unit and sample (target-free selector)

Baselines are the experiment-14 runs and judgments (same generator, settings, evidence budget, samples and judges):
closed_book, text_chunks, card, v2_units.

Stages: generate (system-match arms and closed_book_fixed) -> refine (knowledge_first) -> select (ensemble) ->
judge (GPT-5.6) / cross-judge (DeepSeek-V4-Pro) / audit (target-free GPT-5.6) -> report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import llm_client as lc
import rubric_eval as rx
from hypothesis_evidence_v2 import atomic_json
from stage_metrics import AUDIT_SYSTEM, CROSS_JUDGE, HEDGE, _validated_audit, assert_target_free
from temporal_eval_v3 import (
    ALL_DIMENSIONS,
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    CITED_TEXT_CHARS,
    EXPERIMENT_DIR,
    HYPOTHESIS_FIELDS,
    RUN_ROOT,
    PRIMARY_DIMENSIONS,
    QUERY_LEVELS,
    _blind_candidate,
    _generator_identity,
    cluster_bootstrap,
    exact_sign_test,
    holm_adjust,
    judge_absolute,
)
from temporal_hypothesis_benchmark import (
    _SCORE_SYSTEM,
    _read_json,
    _validate_generation,
    _validate_score,
    compact_evidence_payload,
)

OUT = RUN_ROOT / "improvements"
BASE = rx.OUT
SAMPLES = rx.SAMPLES
BASELINE_ARMS = ("closed_book", "text_chunks", "card", "v2_units")
NEW_ARMS = ("closed_book_fixed", "text_systemmatch", "card_systemmatch", "knowledge_first", "ensemble_select")
GENERATED_ARMS = ("closed_book_fixed", "text_systemmatch", "card_systemmatch", "knowledge_first")
ENSEMBLE_POOL = ("closed_book_fixed", "text_chunks", "card", "text_systemmatch", "card_systemmatch", "knowledge_first")
PRIMARY_BASELINE = "text_chunks"
GEN_MAX_TOKENS = 7000

SCHEMA = """{
  "hypothesis": "",
  "material_initial_state": "",
  "intervention": "",
  "conditions": "",
  "structural_mediator": "",
  "mechanism": "",
  "predicted_outcome": "",
  "baseline": "",
  "boundary": "",
  "uncertainty": "",
  "supporting_evidence_ids": [],
  "conflicting_evidence_ids": [],
  "falsification_experiment": {"design": "", "measurements": [], "falsification_rule": ""}
}"""

CLOSED_BOOK_FIXED_SYSTEM = (
    "You are a materials-science hypothesis agent. No literature records are supplied for this task: use your own "
    "knowledge of materials science published before the knowledge cutoff given in the input. Do not claim knowledge "
    "of work published after the cutoff. Always propose one specific, falsifiable hypothesis for the system the query "
    "describes, even if you are unsure; put any doubt in the uncertainty field. Leave both evidence ID lists empty. "
    "Return JSON:\n" + SCHEMA
)
SYSTEMMATCH_SYSTEM = (
    "You are a materials-science hypothesis agent in a chronological benchmark. Use only the supplied temporally "
    "eligible evidence records and general materials-science principles; do not claim knowledge of the paper being "
    "predicted. Work in two steps inside one JSON object.\n"
    "Step 1, appraise the evidence. State the target system the query is about (composition or alloy family, "
    "processing state, test conditions). For each record you might use, give its alloy system and conditions, how it "
    "differs from the target system, and a transfer verdict: transfers, partially, or does_not_transfer, with the "
    "reason (for example a different crystal structure, composition class, temperature regime or processing route).\n"
    "Step 2, write the hypothesis for the target system. Use a record's mechanism only if you judged it to transfer; "
    "otherwise derive the mechanism for the target system from materials-science principles and say so in the "
    "mechanism field. Cite only records judged transfers or partially. Give specific compositions, conditions and "
    "quantified predictions; put doubt only in the uncertainty field.\n"
    "Return JSON with \"target_system\": str, \"evidence_appraisal\": [{\"record_id\": str, \"record_system\": str, "
    "\"difference_from_target\": str, \"transfer\": str, \"reason\": str}], followed by all fields of:\n" + SCHEMA +
    "\nEvidence IDs must be copied exactly from the supplied records."
)
KNOWLEDGE_FIRST_SYSTEM = (
    "You are a materials-science hypothesis agent in a chronological benchmark. The input has a query, a knowledge "
    "cutoff, your own draft hypothesis written from your own knowledge, and earlier literature records published "
    "before the cutoff. Revise the draft into the final hypothesis. Keep the draft's target system, intervention and "
    "mechanism unless a record about the same or a closely similar system contradicts them. Use the records to "
    "correct numbers, processing conditions, baselines and the falsification test. Do not replace the mechanism with "
    "one shown for a different alloy system. Keep the hypothesis specific; put doubt only in the uncertainty field. "
    "Cite only records that support specific statements, copying their IDs exactly. Return JSON:\n" + SCHEMA
)
SELECT_SYSTEM = (
    "You choose the best of several candidate hypotheses written for the same materials-science query. You do not "
    "know the true answer and must not guess which paper the query comes from. Prefer the candidate that: addresses "
    "the exact system and problem the query describes; proposes a concrete intervention; gives a mechanism that is "
    "specific to that system and physically consistent; makes quantified predictions; and has a decisive falsification "
    "test. Penalise internal contradictions, mechanisms borrowed from a different alloy system without justification, "
    "and vague or hedged claims. Return JSON {\"choice\": \"C<number>\", \"reason\": str}."
)


# ---------------------------------------------------------------- helpers

def run_jobs(stage: str, jobs: list[tuple[str, tuple[Any, ...]]], fn: Any, workers: int) -> dict[str, int]:
    errors = OUT / "errors" / stage
    errors.mkdir(parents=True, exist_ok=True)
    counts: Counter[str] = Counter()

    def safe(name: str, args: tuple[Any, ...]) -> str:
        try:
            fn(*args)
        except Exception as error:  # noqa: BLE001 - logged and retried on resume
            atomic_json(errors / f"{name}.json", {"job": name, "error": f"{type(error).__name__}: {str(error)[:600]}"})
            return "failed"
        (errors / f"{name}.json").unlink(missing_ok=True)
        return "done"

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for future in as_completed([pool.submit(safe, name, args) for name, args in jobs]):
            counts[future.result()] += 1
    return {"jobs": len(jobs), **dict(counts)}


def run_id(paper_id: str, level: str, arm: str, sample: int) -> str:
    return rx.run_id(paper_id, level, arm, sample)


def generate_validated(system: str, payload: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
    """One generation call, plus one repair call if the hypothesis is missing or cites unavailable IDs."""
    raw = lc.chat_json(system, json.dumps(payload, ensure_ascii=False), max_tokens=GEN_MAX_TOKENS, retries=3)
    try:
        validated = _validate_generation(raw, allowed)
        validated["citation_validation"] = {"status": "valid", "removed_unknown_ids": []}
        return validated
    except ValueError as first_error:
        repair = {**payload, "validation_error": str(first_error), "allowed_evidence_ids": sorted(allowed),
                  "repair_instruction": "Regenerate the complete JSON. The hypothesis field must be a non-empty "
                                        "statement, and evidence ID arrays may contain only exact IDs from "
                                        "allowed_evidence_ids."}
        raw = lc.chat_json(system, json.dumps(repair, ensure_ascii=False), max_tokens=GEN_MAX_TOKENS, retries=3)
        validated = _validate_generation(raw, allowed)
        validated["citation_validation"] = {"status": "valid_after_regeneration", "removed_unknown_ids": [],
                                            "initial_error": str(first_error)}
        return validated


def save_run(case: dict[str, Any], level: str, arm: str, sample: int, status: str, error: str | None,
             generation: dict[str, Any] | None, packed: list[Any], started: float, extra: dict[str, Any]) -> None:
    lookup = {r.record_id: r for r in packed}
    cited = sorted(set((generation or {}).get("supporting_evidence_ids", [])
                       + (generation or {}).get("conflicting_evidence_ids", [])))
    audit = rx.leakage_audit(packed, case)
    audit["invalid_citations"] = len(set(cited) - set(lookup))
    rid = run_id(case["paper_id"], level, arm, sample)
    atomic_json(OUT / "runs" / f"{rid}.json", {
        "run_id": rid, "paper_id": case["paper_id"], "query_level": level, "arm": arm, "sample": sample,
        "query": case["queries"][level]["text"], "publication_date": case["publication_date"],
        "generator": _generator_identity(), "status": status, "error": error, "generation": generation,
        "packed_ids": [r.record_id for r in packed], "packed_chars": sum(min(len(r.text), rx.record_cap(
            "card" if arm.startswith("card") else "text_chunks")) for r in packed),
        "packed_papers": len({r.paper_id for r in packed}), "cited_ids": cited,
        "cited_evidence": [{"record_id": rid_, "paper_id": lookup[rid_].paper_id,
                            "publication_date": lookup[rid_].publication_date, "kind": lookup[rid_].kind,
                            "text": lookup[rid_].text[:CITED_TEXT_CHARS]} for rid_ in cited if rid_ in lookup],
        "audit": audit, "elapsed_seconds": round(time.time() - started, 2), **extra,
    })


def evidence_for(case: dict[str, Any], level: str, representation: str) -> list[Any]:
    """Same pool, ranking and budget as the experiment-14 arm of that representation."""
    _, pool = rx.case_pool(case, representation)
    return rx.pack(case["queries"][level]["text"], pool, rx.record_cap(representation))


# ---------------------------------------------------------------- stage: generate

def generate_one(case: dict[str, Any], level: str, arm: str, sample: int) -> None:
    query = case["queries"][level]["text"]
    cutoff = case["publication_date"]
    started = time.time()
    status, error, generation, packed, extra = "ok", None, None, [], {}
    try:
        if arm == "closed_book_fixed":
            generation = generate_validated(CLOSED_BOOK_FIXED_SYSTEM, {"query": query, "knowledge_cutoff": cutoff},
                                            set())
        elif arm in ("text_systemmatch", "card_systemmatch"):
            representation = "text_chunks" if arm == "text_systemmatch" else "card"
            packed = evidence_for(case, level, representation)
            payload = {"query": query, "knowledge_cutoff": cutoff,
                       "eligible_evidence": compact_evidence_payload(packed,
                                                                     max_text_chars=rx.record_cap(representation))}
            generation = generate_validated(SYSTEMMATCH_SYSTEM, payload, {r.record_id for r in packed})
            extra = {"target_system": generation.get("target_system", ""),
                     "evidence_appraisal": generation.get("evidence_appraisal", [])}
        elif arm == "knowledge_first":
            draft_run = _read_json(OUT / "runs" / f"{run_id(case['paper_id'], level, 'closed_book_fixed', sample)}.json")
            if draft_run["status"] != "ok":
                raise ValueError("closed_book_fixed draft for this sample failed; nothing to refine")
            draft = {k: draft_run["generation"].get(k) for k in HYPOTHESIS_FIELDS
                     if k not in ("supporting_evidence_ids", "conflicting_evidence_ids")}
            packed = evidence_for(case, level, "text_chunks")
            payload = {"query": query, "knowledge_cutoff": cutoff, "draft_hypothesis": draft,
                       "eligible_evidence": compact_evidence_payload(packed, max_text_chars=rx.RECORD_MAX_CHARS)}
            generation = generate_validated(KNOWLEDGE_FIRST_SYSTEM, payload, {r.record_id for r in packed})
            extra = {"draft_run_id": draft_run["run_id"]}
        else:
            raise ValueError(f"unknown generated arm {arm}")
    except Exception as caught:  # noqa: BLE001 - failed runs are recorded, never dropped
        status, error = "failed", f"{type(caught).__name__}: {caught}"
    save_run(case, level, arm, sample, status, error, generation, packed, started, extra)


def generate_stage(workers: int, resume: bool, arms: tuple[str, ...]) -> dict[str, int]:
    jobs = []
    for case in rx.cases().values():
        for level in QUERY_LEVELS:
            for arm in arms:
                for sample in SAMPLES:
                    path = OUT / "runs" / f"{run_id(case['paper_id'], level, arm, sample)}.json"
                    if resume and path.exists() and _read_json(path)["status"] == "ok":
                        continue
                    jobs.append((path.stem, (case, level, arm, sample)))
    return run_jobs(f"generate_{'_'.join(arms)}"[:60], jobs, generate_one, workers)


# ---------------------------------------------------------------- stage: ensemble selection

def all_runs() -> dict[str, dict[str, Any]]:
    """Baseline runs from experiment 14 plus the new runs."""
    runs = {rid: r for rid, r in rx.load_runs().items() if r["arm"] in BASELINE_ARMS}
    runs.update({p.stem: _read_json(p) for p in sorted((OUT / "runs").glob("PMC*.json"))})
    return runs


def candidate_order(paper_id: str, level: str, sample: int, arms: list[str]) -> list[str]:
    seed = int(hashlib.sha1(f"{paper_id}|{level}|{sample}".encode()).hexdigest()[:8], 16)
    order = list(arms)
    random.Random(seed).shuffle(order)
    return order


def select_one(case: dict[str, Any], level: str, sample: int, runs: dict[str, dict[str, Any]]) -> None:
    available = [arm for arm in ENSEMBLE_POOL
                 if runs.get(run_id(case["paper_id"], level, arm, sample), {}).get("status") == "ok"]
    order = candidate_order(case["paper_id"], level, sample, available)
    labels = {f"C{i + 1}": arm for i, arm in enumerate(order)}
    candidates = []
    for label, arm in labels.items():
        generation = runs[run_id(case["paper_id"], level, arm, sample)]["generation"]
        candidates.append({"label": label, **{k: generation.get(k) for k in HYPOTHESIS_FIELDS
                                              if k not in ("supporting_evidence_ids", "conflicting_evidence_ids")}})
    payload = {"query": case["queries"][level]["text"], "candidates": candidates}
    assert_target_free(payload)
    # Only the distinctive arm identifiers are checked; "card" alone also occurs in ordinary words ("discarded").
    if any(arm in json.dumps(payload) for arm in ENSEMBLE_POOL if "_" in arm):
        raise ValueError("arm names leaked into the selector payload")
    raw = lc.chat_json(SELECT_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=2000, retries=3)
    choice = str(raw.get("choice", "")).strip().upper() if isinstance(raw, dict) else ""
    fallback = choice not in labels
    if fallback:
        choice = "C1"
    atomic_json(OUT / "selections" / f"{run_id(case['paper_id'], level, 'ensemble_select', sample)}.json", {
        "run_id": run_id(case["paper_id"], level, "ensemble_select", sample), "paper_id": case["paper_id"],
        "query_level": level, "sample": sample, "selector": _generator_identity(), "labels": labels,
        "choice": choice, "chosen_arm": labels[choice], "fallback": fallback,
        "reason": str(raw.get("reason", ""))[:800] if isinstance(raw, dict) else "",
    })


def select_stage(workers: int, resume: bool) -> dict[str, int]:
    runs = all_runs()
    jobs = []
    for case in rx.cases().values():
        for level in QUERY_LEVELS:
            for sample in SAMPLES:
                rid = run_id(case["paper_id"], level, "ensemble_select", sample)
                if not (resume and (OUT / "selections" / f"{rid}.json").exists()):
                    jobs.append((rid, (case, level, sample, runs)))
    return run_jobs("select", jobs, select_one, workers)


# ---------------------------------------------------------------- stages: judge, cross-judge, audit (new runs only)

def new_runs() -> dict[str, dict[str, Any]]:
    return {p.stem: _read_json(p) for p in sorted((OUT / "runs").glob("PMC*.json"))}


def judge_stage(workers: int, resume: bool) -> dict[str, int]:
    out = OUT / "judgments" / "gpt56"
    jobs = [(rid, (run,)) for rid, run in new_runs().items()
            if run["status"] == "ok" and not (resume and (out / f"{rid}.json").exists())]

    def job(run: dict[str, Any]) -> None:
        atomic_json(out / f"{run['run_id']}.json", judge_absolute(run, rx.cases()[run["paper_id"]]))

    return run_jobs("judge", jobs, job, workers)


def cross_judge_stage(workers: int, resume: bool) -> dict[str, int]:
    out = OUT / "judgments" / "deepseek"
    jobs = [(rid, (run,)) for rid, run in new_runs().items()
            if run["status"] == "ok" and not (resume and (out / f"{rid}.json").exists())]

    def job(run: dict[str, Any]) -> None:
        generation, evidence = _blind_candidate(run)
        payload = {"query": run["query"], "hidden_target": rx.cases()[run["paper_id"]]["hidden_target"],
                   "generated_hypothesis": generation, "cited_evidence": evidence}
        raw = lc.trapi_chat_json(CROSS_JUDGE["deployment"], _SCORE_SYSTEM, json.dumps(payload, ensure_ascii=False),
                                 max_tokens=8000, token_field=CROSS_JUDGE["token_field"],
                                 temperature=CROSS_JUDGE["temperature"], retries=6)
        score = _validate_score(raw)
        atomic_json(out / f"{run['run_id']}.json", {"run_id": run["run_id"], "judge": f"trapi:{CROSS_JUDGE['deployment']}",
                                                    "scores": score["scores"],
                                                    "classification": score.get("classification", "")})

    return run_jobs("cross_judge", jobs, job, workers)


def audit_stage(workers: int, resume: bool) -> dict[str, int]:
    out = OUT / "audit"
    jobs = [(rid, (run,)) for rid, run in new_runs().items()
            if run["status"] == "ok" and not (resume and (out / f"{rid}.json").exists())]

    def job(run: dict[str, Any]) -> None:
        payload = {"query": run["query"],
                   "hypothesis": {k: run["generation"].get(k) for k in HYPOTHESIS_FIELDS if k in run["generation"]},
                   "cited_evidence": [{"record_id": c["record_id"], "text": c["text"]} for c in run["cited_evidence"]]}
        assert_target_free(payload)
        raw = lc.judge_chat_json(AUDIT_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=16000)
        atomic_json(out / f"{run['run_id']}.json", {"run_id": run["run_id"], "auditor": lc.judge_info(),
                                                    **_validated_audit(raw)})

    return run_jobs("audit", jobs, job, workers)


# ---------------------------------------------------------------- report

CAVEAT = __import__("re").compile(
    r"(evidence (list |provided |supplied )?(is )?empty|no (eligible |supplied )?evidence|insufficient evidence|"
    r"supplied (records|evidence)|without (any )?(supplied|eligible) evidence)", __import__("re").IGNORECASE)


def mean(values: list[Any]) -> float | None:
    values = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return round(statistics.fmean(values), 3) if values else None


def recon(scores: dict[str, int]) -> float:
    return statistics.fmean(scores[d] for d in PRIMARY_DIMENSIONS)


def load_records() -> dict[tuple[str, str, str, int], dict[str, Any]]:
    """One record per (paper, level, arm, sample) with its run, both judgments and its audit."""
    sources = {
        "base": (rx.OUT, {rid: r for rid, r in rx.load_runs().items() if r["arm"] in BASELINE_ARMS}),
        "new": (OUT, new_runs()),
    }
    records: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    for root, runs in sources.values():
        for rid, run in runs.items():
            gpt = root / "judgments" / "gpt56" / f"{rid}.json"
            deep = root / "judgments" / "deepseek" / f"{rid}.json"
            audit = root / "audit" / f"{rid}.json"
            records[(run["paper_id"], run["query_level"], run["arm"], run["sample"])] = {
                "run": run, "gpt": _read_json(gpt) if gpt.exists() else None,
                "deep": _read_json(deep) if deep.exists() else None,
                "audit": _read_json(audit) if audit.exists() else None, "chosen_arm": None}
    for path in sorted((OUT / "selections").glob("PMC*.json")):
        sel = _read_json(path)
        chosen = records.get((sel["paper_id"], sel["query_level"], sel["chosen_arm"], sel["sample"]))
        if chosen:
            records[(sel["paper_id"], sel["query_level"], "ensemble_select", sel["sample"])] = {
                **chosen, "chosen_arm": sel["chosen_arm"], "selection": sel}
    return records


def unit_scores(records: dict, arm: str, judge: str, levels: tuple[str, ...] = QUERY_LEVELS
                ) -> dict[tuple[str, str], float]:
    per: dict[tuple[str, str], list[float]] = defaultdict(list)
    for (paper, level, a, _), rec in records.items():
        if a == arm and level in levels and rec.get(judge):
            per[(paper, level)].append(recon(rec[judge]["scores"]))
    return {k: statistics.fmean(v) for k, v in per.items()}


def paired(a: dict, b: dict, name_a: str, name_b: str) -> dict[str, Any]:
    common = sorted(set(a) & set(b))
    per_paper: dict[str, list[float]] = defaultdict(list)
    for key in common:
        per_paper[key[0]].append(a[key] - b[key])
    if not per_paper:
        return {"a": name_a, "b": name_b, "units": 0}
    point, low, high = cluster_bootstrap(per_paper)
    p_value, positive, negative = exact_sign_test([statistics.fmean(v) for v in per_paper.values()])
    return {"a": name_a, "b": name_b, "units": len(common), "papers": len(per_paper),
            "mean_difference": round(point, 3), "ci95": [round(low, 3), round(high, 3)],
            "papers_a_higher": positive, "papers_b_higher": negative, "sign_test_p": round(p_value, 4)}


def supportive_sets() -> dict[str, dict[str, set[str]]]:
    out = {}
    for rep in ("text_chunks", "card"):
        out[rep] = {}
        for path in sorted((rx.OUT / "ceiling" / rep).glob("PMC*.json")):
            c = _read_json(path)
            out[rep][c["paper_id"]] = {r["record_id"] for r in c["records"]
                                       if r["intervention_support"] >= 1 or r["mechanism_support"] >= 1}
    return out


def representation_of(arm: str) -> str | None:
    if arm in ("text_chunks", "text_systemmatch", "knowledge_first"):
        return "text_chunks"
    if arm in ("card", "card_systemmatch"):
        return "card"
    return None


def report() -> dict[str, Any]:
    records = load_records()
    support = supportive_sets()
    arms = BASELINE_ARMS + NEW_ARMS
    by_arm: dict[str, Any] = {}
    for arm in arms:
        recs = [r for (p, lvl, a, s), r in records.items() if a == arm]
        judged = [r for r in recs if r["gpt"]]
        audits = [r["audit"] for r in judged if r["audit"]]
        units_g = unit_scores(records, arm, "gpt")
        units_d = unit_scores(records, arm, "deep")
        nonbroad = unit_scores(records, arm, "gpt", ("problem_constrained", "expert_context"))
        sup_share, cited_total, sup_cited = [], 0, 0
        for r in judged:
            arm_for_rep = r["chosen_arm"] or arm
            rep = representation_of(arm_for_rep)
            if rep and r["run"]["cited_ids"]:
                s = support[rep].get(r["run"]["paper_id"], set())
                cited_total += len(r["run"]["cited_ids"])
                sup_cited += len(set(r["run"]["cited_ids"]) & s)
        sources = Counter(a["mechanism_source"] for a in audits)
        by_arm[arm] = {
            "runs": len(recs) if arm != "ensemble_select" else len(recs),
            "failed": sum(1 for r in recs if r["run"]["status"] != "ok") if arm != "ensemble_select" else 0,
            "judged": len(judged),
            "reconstruction_gpt56": mean(list(units_g.values())),
            "reconstruction_deepseek": mean(list(units_d.values())),
            "reconstruction_gpt56_non_broad": mean(list(nonbroad.values())),
            "by_level": {lvl: mean([v for k, v in units_g.items() if k[1] == lvl]) for lvl in QUERY_LEVELS},
            "failure_rate_by_level": {lvl: mean([1.0 if recon(r["gpt"]["scores"]) <= 1.0 else 0.0 for r in judged
                                                 if r["run"]["query_level"] == lvl]) for lvl in QUERY_LEVELS},
            "intervention": mean([r["gpt"]["scores"]["intervention_reconstruction"] for r in judged]),
            "mechanism": mean([r["gpt"]["scores"]["mechanism_agreement"] for r in judged]),
            "outcome": mean([r["gpt"]["scores"]["outcome_agreement"] for r in judged]),
            "evidence_validity": mean([r["gpt"]["scores"]["evidence_validity"] for r in judged]),
            "novelty": mean([r["gpt"]["scores"]["novelty"] for r in judged]),
            "mechanism_own_reasoning": round(sources["not_from_evidence"] / max(1, len(audits)), 3),
            "mechanism_transferred_unjustified": round(sources["transferred_without_justification"] / max(1, len(audits)), 3),
            "mechanism_transferred_justified": round(sources["transferred_with_justification"] / max(1, len(audits)), 3),
            "complete_chain_rate": mean([1.0 if all(v == 2 for v in a["chain"].values()) else 0.0 for a in audits]),
            "contradictions_per_hypothesis": mean([len(a["contradictions"]) for a in audits]),
            "specificity": mean([mean([1.0 if v else 0.0 for v in a["specificity"].values()]) for a in audits]),
            "citations_per_hypothesis": mean([len(r["run"]["cited_ids"]) for r in judged]),
            "supportive_share_of_citations": round(sup_cited / cited_total, 3) if cited_total else None,
            "hedges_per_hypothesis": mean([len(HEDGE.findall(f"{r['run']['generation'].get('hypothesis', '')} "
                                                             f"{r['run']['generation'].get('predicted_outcome', '')}"))
                                           for r in judged]),
            "evidence_caveat_rate": mean([1.0 if CAVEAT.search(json.dumps(r["run"]["generation"])) else 0.0
                                          for r in judged]) if arm.startswith("closed_book") else None,
        }

    # system-match appraisal behaviour
    appraisal = {}
    for arm in ("text_systemmatch", "card_systemmatch"):
        recs = [r for (p, lvl, a, s), r in records.items() if a == arm and r["run"]["status"] == "ok"]
        verdicts: Counter[str] = Counter()
        cited_not_transfer = cited_total = appraised = 0
        for r in recs:
            items = [i for i in r["run"].get("evidence_appraisal", []) if isinstance(i, dict)]
            appraised += len(items)
            by_id = {str(i.get("record_id")): str(i.get("transfer", "")).lower() for i in items}
            verdicts.update(by_id.values())
            for cid in r["run"]["cited_ids"]:
                cited_total += 1
                cited_not_transfer += by_id.get(cid) == "does_not_transfer"
        total = sum(verdicts.values())
        appraisal[arm] = {"runs": len(recs), "records_appraised_per_run": round(appraised / max(1, len(recs)), 2),
                          "verdicts": {k: round(v / max(1, total), 3) for k, v in verdicts.most_common(4)},
                          "citations_of_records_judged_not_transferable": cited_not_transfer,
                          "citations": cited_total}

    # knowledge-first: does the final keep the draft's intervention and mechanism?
    def jaccard(a: str, b: str) -> float:
        ta, tb = set(rx.normalise(a).split()), set(rx.normalise(b).split())
        return len(ta & tb) / len(ta | tb) if ta | tb else 0.0
    kf = []
    for (p, lvl, a, s), r in records.items():
        if a == "knowledge_first" and r["run"]["status"] == "ok":
            draft = records.get((p, lvl, "closed_book_fixed", s))
            if draft and draft["run"]["status"] == "ok":
                kf.append({f: jaccard(str(draft["run"]["generation"].get(f, "")), str(r["run"]["generation"].get(f, "")))
                           for f in ("intervention", "mechanism")}
                          | {"delta": recon(r["gpt"]["scores"]) - recon(draft["gpt"]["scores"])
                             if r["gpt"] and draft["gpt"] else None})
    knowledge_first = {"pairs": len(kf), "intervention_word_overlap_with_draft": mean([k["intervention"] for k in kf]),
                       "mechanism_word_overlap_with_draft": mean([k["mechanism"] for k in kf]),
                       "mean_change_vs_draft": mean([k["delta"] for k in kf]),
                       "improved": sum(1 for k in kf if k["delta"] and k["delta"] > 0),
                       "worse": sum(1 for k in kf if k["delta"] and k["delta"] < 0)}

    # ensemble selection
    sels = [r["selection"] for (p, lvl, a, s), r in records.items() if a == "ensemble_select"]
    cand_means, oracle, chosen_scores = [], [], []
    for sel in sels:
        scores = [recon(records[(sel["paper_id"], sel["query_level"], arm, sel["sample"])]["gpt"]["scores"])
                  for arm in sel["labels"].values()
                  if records.get((sel["paper_id"], sel["query_level"], arm, sel["sample"]), {}).get("gpt")]
        chosen = records[(sel["paper_id"], sel["query_level"], sel["chosen_arm"], sel["sample"])]
        if scores and chosen["gpt"]:
            cand_means.append(statistics.fmean(scores))
            oracle.append(max(scores))
            chosen_scores.append(recon(chosen["gpt"]["scores"]))
    ensemble = {"selections": len(sels), "fallbacks": sum(s["fallback"] for s in sels),
                "chosen_arm": dict(Counter(s["chosen_arm"] for s in sels)),
                "chosen_position": dict(Counter(s["choice"] for s in sels)),
                "selected_mean": mean(chosen_scores), "random_pick_mean": mean(cand_means),
                "oracle_best_mean": mean(oracle)}

    comparisons: dict[str, list[dict[str, Any]]] = {}
    for judge in ("gpt", "deep"):
        base = unit_scores(records, PRIMARY_BASELINE, judge)
        primary = [paired(unit_scores(records, a, judge), base, a, PRIMARY_BASELINE) for a in NEW_ARMS]
        for item, adj in zip(primary, holm_adjust([c.get("sign_test_p", 1.0) for c in primary])):
            item.update({"holm_p": round(adj, 4), "role": "primary"})
        secondary = [paired(unit_scores(records, "closed_book_fixed", judge),
                            unit_scores(records, "closed_book", judge), "closed_book_fixed", "closed_book")]
        secondary += [paired(unit_scores(records, a, judge), unit_scores(records, "closed_book", judge), a, "closed_book")
                      for a in NEW_ARMS if a != "closed_book_fixed"]
        secondary += [paired(unit_scores(records, a, judge, ("problem_constrained", "expert_context")),
                             unit_scores(records, PRIMARY_BASELINE, judge, ("problem_constrained", "expert_context")),
                             f"{a} (non-broad)", f"{PRIMARY_BASELINE} (non-broad)") for a in NEW_ARMS]
        for item in secondary:
            item["role"] = "secondary"
        comparisons[judge] = primary + secondary

    new = {rid: r for rid, r in new_runs().items()}
    expected = len(rx.cases()) * len(QUERY_LEVELS) * len(GENERATED_ARMS) * len(SAMPLES)
    integrity = {
        "expected_new_runs": expected, "new_runs": len(new), "ok": sum(r["status"] == "ok" for r in new.values()),
        "judged_gpt56": len(list((OUT / "judgments" / "gpt56").glob("*.json"))),
        "judged_deepseek": len(list((OUT / "judgments" / "deepseek").glob("*.json"))),
        "audited": len(list((OUT / "audit").glob("*.json"))), "selections": len(sels),
        "temporal_violations": sum(r["audit"]["temporal_violations"] for r in new.values()),
        "test_paper_leaks": sum(r["audit"]["test_paper_leaks"] for r in new.values()),
        "family_leaks": sum(r["audit"]["family_leaks"] for r in new.values()),
        "invalid_citations": sum(r["audit"]["invalid_citations"] for r in new.values()),
        "stage_errors": {p.name: len(list(p.glob("*.json"))) for p in sorted((OUT / "errors").glob("*")) if p.is_dir()},
        "generators": sorted({r["generator"] for r in new.values()}),
    }
    ok = integrity["ok"]
    integrity["verified"] = bool(
        integrity["new_runs"] == expected and ok == expected and integrity["judged_gpt56"] == ok
        and integrity["judged_deepseek"] == ok and integrity["audited"] == ok
        and integrity["selections"] == len(rx.cases()) * len(QUERY_LEVELS) * len(SAMPLES)
        and all(integrity[k] == 0 for k in ("temporal_violations", "test_paper_leaks", "family_leaks",
                                             "invalid_citations")) and len(integrity["generators"]) == 1)
    analysis = {"by_arm": by_arm, "appraisal": appraisal, "knowledge_first": knowledge_first, "ensemble": ensemble,
                "comparisons": comparisons, "integrity": integrity,
                "bootstrap": {"resamples": BOOTSTRAP_RESAMPLES, "seed": BOOTSTRAP_SEED}}
    (OUT / "results").mkdir(parents=True, exist_ok=True)
    atomic_json(OUT / "results" / "analysis.json", analysis)
    (OUT / "results" / "tables.md").write_text(render(analysis))
    return analysis


def _f(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, dict):
        return ", ".join(f"{k}: {_f(v)}" for k, v in value.items())
    if isinstance(value, list):
        return ", ".join(_f(v) for v in value)
    return str(value)


def render(a: dict[str, Any]) -> str:
    arms = list(a["by_arm"])
    metrics = list(next(iter(a["by_arm"].values())))
    lines = ["# Improvement experiment", "", f"Integrity: {_f(a['integrity'])}", "",
             "## By arm", "", "| Metric | " + " | ".join(arms) + " |", "|---|" + "---:|" * len(arms)]
    for m in metrics:
        lines.append(f"| {m} | " + " | ".join(_f(a["by_arm"][arm].get(m)) for arm in arms) + " |")
    for judge, items in a["comparisons"].items():
        lines += ["", f"## Paired comparisons ({'GPT-5.6' if judge == 'gpt' else 'DeepSeek-V4-Pro'}; unit = mean of 2 samples)", "",
                  "| A | B | Role | Units | Mean diff | 95% CI | Papers A higher / B higher | Sign p | Holm p |",
                  "|---|---|---|---:|---:|---|---:|---:|---:|"]
        for c in items:
            if c.get("units"):
                lines.append(f"| {c['a']} | {c['b']} | {c['role']} | {c['units']} | {c['mean_difference']:+.3f} | "
                             f"[{c['ci95'][0]:+.3f}, {c['ci95'][1]:+.3f}] | {c['papers_a_higher']} / {c['papers_b_higher']} | "
                             f"{c['sign_test_p']:.3f} | {_f(c.get('holm_p'))} |")
    lines += ["", f"## System-match appraisal\n\n{_f(a['appraisal'])}", "",
              f"## Knowledge-first refinement\n\n{_f(a['knowledge_first'])}", "",
              f"## Ensemble selection\n\n{_f(a['ensemble'])}"]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("generate", "refine", "select", "judge", "cross-judge", "audit"):
        p = sub.add_parser(name)
        p.add_argument("--workers", type=int, default=4)
        p.add_argument("--resume", action="store_true")
        if name == "generate":
            p.add_argument("--arm", action="append", choices=("closed_book_fixed", "text_systemmatch", "card_systemmatch"))
    sub.add_parser("report")
    args = parser.parse_args()
    if args.command == "generate":
        result: Any = generate_stage(args.workers, args.resume,
                                     tuple(args.arm or ("closed_book_fixed", "text_systemmatch", "card_systemmatch")))
    elif args.command == "refine":
        result = generate_stage(args.workers, args.resume, ("knowledge_first",))
    elif args.command == "select":
        result = select_stage(args.workers, args.resume)
    elif args.command == "judge":
        result = judge_stage(args.workers, args.resume)
    elif args.command == "cross-judge":
        result = cross_judge_stage(args.workers, args.resume)
    elif args.command == "audit":
        result = audit_stage(args.workers, args.resume)
    else:
        result = report()["integrity"]
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
