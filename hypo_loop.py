"""Loop harness for agentic hypothesis-reconstruction methods (experiments 23+, see loop.md).

Every method runs inside the same harness, which enforces must_obey.md in code:
- benchmark v3.1 queries only (frozen; dev cases for development, test cases only for runs marked final);
- every query-facing LLM call goes through `Harness.ask`, which allows only pre-cutoff models, checks the payload
  against a per-case target guard (no target field values, no target key), and logs role, model, size and time;
- evidence comes from the same temporally filtered pools as the baselines (rubric_eval.case_pool + rx.pack);
- runs record every model used per role, the evidence seen, leakage counters and `target_free_asserted`;
- judging: GPT-5.6 absolute judge, DeepSeek-V4-Pro cross-judge, GPT-5.6 target-free audit, and a GPT-5.6 lever label
  (target-aware analysis only, never shown to any method).

Usage: python hypo_loop.py generate --method closed_book --split dev
       python hypo_loop.py judge|cross_judge|audit|label
       python hypo_loop.py report
"""

from __future__ import annotations

import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("MATHG_CASES_DIR", os.path.join(
    ROOT_DIR, "experiments", "high_temperature_hea_qwen35b", "benchmark_v3_1", "cases"))
os.environ.setdefault("MATHG_PROVIDER", "trapi")
os.environ.setdefault("TRAPI_DEPLOYMENT", "Llama-3.3-70B-Instruct_5")
os.environ.setdefault("MATHG_TEMPERATURE", "0.2")
os.environ.setdefault("JUDGE_PROVIDER", "trapi")
os.environ.setdefault("JUDGE_TRAPI_DEPLOYMENT", "gpt-5.6-sol_2026-07-09")

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import random  # noqa: E402
import statistics  # noqa: E402
import time  # noqa: E402
from collections import Counter, defaultdict  # noqa: E402
from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any, Callable  # noqa: E402

import llm_client as lc  # noqa: E402
import rubric_eval as rx  # noqa: E402
from failure_clean import LABEL_SYSTEM  # noqa: E402
from hypothesis_evidence_v2 import atomic_json  # noqa: E402
from must_obey_check import MODEL_CUTOFFS  # noqa: E402
from stage_metrics import AUDIT_SYSTEM, CROSS_JUDGE, HEDGE, _validated_audit  # noqa: E402
from temporal_eval_v3 import (ALL_DIMENSIONS, CITED_TEXT_CHARS, EXPERIMENT_DIR, HYPOTHESIS_FIELDS,  # noqa: E402
                              PRIMARY_DIMENSIONS, QUERY_LEVELS, _blind_candidate, cluster_bootstrap,
                              exact_sign_test, holm_adjust, judge_absolute)
from temporal_hypothesis_benchmark import (_SCORE_SYSTEM, RetrievalRecord, _read_json,  # noqa: E402
                                           _validate_generation, _validate_score, compact_evidence_payload,
                                           generate_with_citation_repair)

CASES_DIR = Path(os.environ["MATHG_CASES_DIR"])
OUT = Path(os.environ.get("MATHG_LOOP_ROOT", str(EXPERIMENT_DIR / "loop")))
SAMPLES = (1, 2)
BASELINES = ("closed_book", "text_chunks")
GENERATOR = os.environ["TRAPI_DEPLOYMENT"]
MODELS = {  # query-facing deployments (all pre-cutoff, see must_obey.md section 2)
    "llama": {"deployment": "Llama-3.3-70B-Instruct_5", "token_field": "max_tokens", "temperature": 0.2,
              "max_out": 6000},
    "4omini": {"deployment": "gpt-4o-mini_2024-07-18", "token_field": "max_completion_tokens", "temperature": 0.2,
               "max_out": 8000},
    "o3mini": {"deployment": "o3-mini_2025-01-31", "token_field": "max_completion_tokens", "temperature": None,
               "max_out": 20000},
    "o1": {"deployment": "o1_2024-12-17", "token_field": "max_completion_tokens", "temperature": None,
           "max_out": 20000},
}
for _spec in MODELS.values():
    assert _spec["deployment"] in MODEL_CUTOFFS, _spec["deployment"]


# ---------------------------------------------------------------- cases and splits

def cases() -> dict[str, dict[str, Any]]:
    return rx.cases()


def split_of(case: dict[str, Any]) -> str:
    return "test" if case["split"] == "test" else "dev"


def units(split: str) -> list[tuple[dict[str, Any], str]]:
    return [(c, lvl) for c in cases().values() if split in ("all", split_of(c)) for lvl in QUERY_LEVELS]


def run_id(paper: str, level: str, method: str, sample: int) -> str:
    return f"{paper}__{level}__{method}__s{sample}"


# ---------------------------------------------------------------- the harness

class TargetLeak(RuntimeError):
    pass


class Harness:
    """Per-run context: query, cutoff, evidence access, guarded and logged LLM calls."""

    def __init__(self, case: dict[str, Any], level: str, sample: int):
        self.case = case
        self.level = level
        self.sample = sample
        self.query = case["queries"][level]["text"]
        self.cutoff = case["publication_date"]
        self.trace: list[dict[str, Any]] = []
        self.models: dict[str, str] = {}
        self.seen: dict[str, RetrievalRecord] = {}
        self.notes: dict[str, Any] = {}  # the run's notebook: intermediate state, derived from the query only
        target = case["hidden_target"]
        # Long target values must never appear in a query-facing payload (the query itself is allowed).
        self._forbidden = [str(v).strip().lower() for v in target.values()
                           if isinstance(v, str) and len(str(v).strip()) >= 40
                           and str(v).strip().lower() not in self.query.lower()]
        self.rng = random.Random(int(hashlib.sha1(f"{case['paper_id']}|{level}|{sample}".encode()).hexdigest()[:8],
                                     16))

    # -- guard ------------------------------------------------------------------------------------------------
    def guard(self, payload: Any) -> None:
        text = json.dumps(payload, ensure_ascii=False)
        if "hidden_target" in text:
            raise TargetLeak("payload contains a hidden_target key")
        low = text.lower()
        for value in self._forbidden:
            if value in low:
                raise TargetLeak(f"payload contains a target field value: {value[:60]!r}")

    # -- LLM calls --------------------------------------------------------------------------------------------
    def ask(self, role: str, model: str, system: str, payload: dict[str, Any], max_out: int | None = None) -> Any:
        spec = MODELS[model]
        self.guard({"system": system, "payload": payload})
        user = json.dumps(payload, ensure_ascii=False)
        started = time.time()
        cap = max_out or spec["max_out"]
        if spec["temperature"] is None:  # o-series: hidden reasoning tokens count against the output cap
            cap = max(cap, 12000)
        try:
            raw = lc.trapi_chat_json(spec["deployment"], system, user, max_tokens=cap, token_field=spec["token_field"],
                                     temperature=spec["temperature"], retries=8)
        except lc.TruncatedError:
            # A truncated JSON answer is retried once with double the cap (the ratchet: a seen failure becomes a rule).
            self.trace.append({"role": role, "model": spec["deployment"], "event": "truncated", "cap": cap})
            raw = lc.trapi_chat_json(spec["deployment"], system, user, max_tokens=cap * 2,
                                     token_field=spec["token_field"], temperature=spec["temperature"], retries=8)
        self.models.setdefault(role, f"trapi:{spec['deployment']}")
        self.trace.append({"role": role, "model": spec["deployment"], "chars_in": len(system) + len(user),
                           "chars_out": len(json.dumps(raw, ensure_ascii=False)),
                           "seconds": round(time.time() - started, 2)})
        return raw

    def generate_final(self, role: str, model: str, system: str, payload: dict[str, Any],
                       allowed: set[str]) -> dict[str, Any]:
        """Final hypothesis with the same validation and one repair call as the baselines."""
        raw = self.ask(role, model, system, payload)
        try:
            out = _validate_generation(raw, allowed)
            out["citation_validation"] = {"status": "valid", "removed_unknown_ids": []}
            return out
        except ValueError as error:
            repair = {**payload, "validation_error": str(error), "allowed_evidence_ids": sorted(allowed),
                      "repair_instruction": "Regenerate the complete JSON. The hypothesis field must be a non-empty "
                                            "statement, and evidence ID arrays may contain only exact IDs from "
                                            "allowed_evidence_ids."}
            raw = self.ask(f"{role}_repair", model, system, repair)
            out = _validate_generation(raw, allowed)
            out["citation_validation"] = {"status": "valid_after_regeneration", "initial_error": str(error)}
            return out

    # -- evidence ---------------------------------------------------------------------------------------------
    def pool(self, representation: str) -> list[RetrievalRecord]:
        _, pool = rx.case_pool(self.case, representation)
        return pool

    def pack(self, query: str, representation: str, cap: int | None = None) -> list[RetrievalRecord]:
        packed = rx.pack(query, self.pool(representation), cap or rx.record_cap(representation))
        for r in packed:
            self.seen[r.record_id] = r
        return packed

    def evidence_payload(self, records: list[RetrievalRecord], cap: int) -> list[dict[str, Any]]:
        for r in records:
            self.seen[r.record_id] = r
        return compact_evidence_payload(records, max_text_chars=cap)


# ---------------------------------------------------------------- baselines (identical to experiment 21)

def m_closed_book(h: Harness) -> dict[str, Any]:
    payload = {"query": h.query, "knowledge_cutoff": h.cutoff, "eligible_evidence": []}
    h.guard(payload)
    h.models["generator"] = f"trapi:{GENERATOR}"
    h.trace.append({"role": "generator", "model": GENERATOR, "chars_in": len(json.dumps(payload)), "chars_out": 0,
                    "seconds": 0})
    return generate_with_citation_repair(payload, set())


def m_text_chunks(h: Harness) -> dict[str, Any]:
    packed = h.pack(h.query, "text_chunks")
    payload = {"query": h.query, "knowledge_cutoff": h.cutoff,
               "eligible_evidence": h.evidence_payload(packed, rx.record_cap("text_chunks"))}
    h.guard(payload)
    h.models["generator"] = f"trapi:{GENERATOR}"
    h.trace.append({"role": "generator", "model": GENERATOR, "chars_in": len(json.dumps(payload)), "chars_out": 0,
                    "seconds": 0})
    return generate_with_citation_repair(payload, {r.record_id for r in packed})


METHODS: dict[str, Callable[[Harness], dict[str, Any]]] = {
    "closed_book": m_closed_book,
    "text_chunks": m_text_chunks,
}


def register(name: str) -> Callable[[Callable[[Harness], dict[str, Any]]], Callable[[Harness], dict[str, Any]]]:
    def wrap(fn: Callable[[Harness], dict[str, Any]]) -> Callable[[Harness], dict[str, Any]]:
        METHODS[name] = fn
        return fn
    return wrap


# Methods live in loop_methods.py and register themselves on import.
try:
    import loop_methods  # noqa: F401,E402
except ModuleNotFoundError as missing:
    if missing.name != "loop_methods":
        raise


# ---------------------------------------------------------------- generation stage

def leakage_audit(h: Harness, cited: list[str]) -> dict[str, int]:
    records = list(h.seen.values())
    audit = rx.leakage_audit(records, h.case)
    audit["invalid_citations"] = len(set(cited) - set(h.seen))
    return audit


def generate_one(method: str, case: dict[str, Any], level: str, sample: int, final: bool) -> None:
    h = Harness(case, level, sample)
    started = time.time()
    status, error, generation = "ok", None, None
    try:
        generation = METHODS[method](h)
    except Exception as caught:  # noqa: BLE001 - failed runs are recorded, never dropped
        status, error = "failed", f"{type(caught).__name__}: {str(caught)[:800]}"
    cited = sorted(set((generation or {}).get("supporting_evidence_ids", [])
                       + (generation or {}).get("conflicting_evidence_ids", [])))
    rid = run_id(case["paper_id"], level, method, sample)
    path = OUT / method / "runs" / f"{rid}.json"
    atomic_json(path, {
        "run_id": rid, "paper_id": case["paper_id"], "query_level": level, "method": method, "sample": sample,
        "split": split_of(case), "final": final, "benchmark": "v3.1", "query": h.query,
        "publication_date": h.cutoff, "models": h.models, "status": status, "error": error,
        "generation": generation, "seen_ids": sorted(h.seen), "cited_ids": cited,
        "cited_evidence": [{"record_id": c, "paper_id": h.seen[c].paper_id,
                            "publication_date": h.seen[c].publication_date, "kind": h.seen[c].kind,
                            "text": h.seen[c].text[:CITED_TEXT_CHARS]} for c in cited if c in h.seen],
        "audit": leakage_audit(h, cited), "target_free_asserted": not (error or "").startswith("TargetLeak"),
        "trace": h.trace, "llm_calls": sum(1 for t in h.trace if "event" not in t), "notes": h.notes,
        "chars_in": sum(t.get("chars_in", 0) for t in h.trace), "elapsed_seconds": round(time.time() - started, 2),
    })


def generate_stage(method: str, split: str, workers: int, final: bool) -> dict[str, int]:
    if split in ("test", "all") and not final:
        raise SystemExit("test-split runs must be pre-registered finals: pass --final (must_obey.md 6.5)")
    jobs = []
    for case, level in units(split):
        for sample in SAMPLES:
            path = OUT / method / "runs" / f"{run_id(case['paper_id'], level, method, sample)}.json"
            if path.exists() and _read_json(path)["status"] == "ok":
                continue
            if path.exists():
                kept = OUT / method / "failed_attempts" / path.name
                kept.parent.mkdir(parents=True, exist_ok=True)
                kept.write_text(path.read_text())
            jobs.append((method, case, level, sample, final))
    counts: Counter[str] = Counter()
    with ThreadPoolExecutor(workers) as pool:
        futures = [pool.submit(generate_one, *job) for job in jobs]
        for future in as_completed(futures):
            future.result()
            counts["done"] += 1
    return {"jobs": len(jobs), **counts}


# ---------------------------------------------------------------- evaluation stages

def all_runs(methods: list[str] | None = None) -> list[dict[str, Any]]:
    out = []
    for method_dir in sorted(p for p in OUT.iterdir() if p.is_dir() and (p / "runs").exists()):
        if methods and method_dir.name not in methods:
            continue
        out += [_read_json(p) for p in sorted((method_dir / "runs").glob("PMC*.json"))]
    return out


def _parallel(jobs: list[tuple[Any, ...]], fn: Callable[..., None], workers: int) -> dict[str, int]:
    counts: Counter[str] = Counter()
    with ThreadPoolExecutor(workers) as pool:
        futures = [pool.submit(fn, *job) for job in jobs]
        for future in as_completed(futures):
            try:
                future.result()
                counts["done"] += 1
            except Exception as error:  # noqa: BLE001 - logged, retried on the next call
                counts["failed"] += 1
                print(f"[loop] evaluation job failed: {type(error).__name__}: {str(error)[:200]}", flush=True)
    return {"jobs": len(jobs), **counts}


def judge_stage(workers: int, methods: list[str] | None = None) -> dict[str, int]:
    all_cases = cases()

    def job(run: dict[str, Any]) -> None:
        atomic_json(OUT / run["method"] / "judgments" / "gpt56" / f"{run['run_id']}.json",
                    judge_absolute(run, all_cases[run["paper_id"]]))

    jobs = [(r,) for r in all_runs(methods) if r["status"] == "ok"
            and not (OUT / r["method"] / "judgments" / "gpt56" / f"{r['run_id']}.json").exists()]
    return _parallel(jobs, job, workers)


def cross_judge_stage(workers: int, methods: list[str] | None = None) -> dict[str, int]:
    all_cases = cases()

    def job(run: dict[str, Any]) -> None:
        generation, evidence = _blind_candidate(run)
        payload = {"query": run["query"], "hidden_target": all_cases[run["paper_id"]]["hidden_target"],
                   "generated_hypothesis": generation, "cited_evidence": evidence}
        raw = lc.trapi_chat_json(CROSS_JUDGE["deployment"], _SCORE_SYSTEM, json.dumps(payload, ensure_ascii=False),
                                 max_tokens=8000, token_field=CROSS_JUDGE["token_field"],
                                 temperature=CROSS_JUDGE["temperature"], retries=6)
        score = _validate_score(raw)
        atomic_json(OUT / run["method"] / "judgments" / "deepseek" / f"{run['run_id']}.json",
                    {"run_id": run["run_id"], "judge": f"trapi:{CROSS_JUDGE['deployment']}", "scores": score["scores"],
                     "classification": score.get("classification", "")})

    jobs = [(r,) for r in all_runs(methods) if r["status"] == "ok"
            and not (OUT / r["method"] / "judgments" / "deepseek" / f"{r['run_id']}.json").exists()]
    return _parallel(jobs, job, workers)


def audit_stage(workers: int, methods: list[str] | None = None) -> dict[str, int]:
    def job(run: dict[str, Any]) -> None:
        payload = {"query": run["query"],
                   "hypothesis": {k: run["generation"].get(k) for k in HYPOTHESIS_FIELDS if k in run["generation"]},
                   "cited_evidence": [{"record_id": c["record_id"], "text": c["text"]} for c in run["cited_evidence"]]}
        if "hidden_target" in json.dumps(payload):
            raise TargetLeak("audit payload contains the target")
        raw = lc.judge_chat_json(AUDIT_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=16000)
        atomic_json(OUT / run["method"] / "audit" / f"{run['run_id']}.json",
                    {"run_id": run["run_id"], "auditor": lc.judge_info(), **_validated_audit(raw)})

    jobs = [(r,) for r in all_runs(methods) if r["status"] == "ok"
            and not (OUT / r["method"] / "audit" / f"{r['run_id']}.json").exists()]
    return _parallel(jobs, job, workers)


def label_stage(workers: int, methods: list[str] | None = None) -> dict[str, int]:
    """Target-aware analysis label (lever match); stored apart from the runs and never shown to a method."""
    all_cases = cases()

    def job(run: dict[str, Any]) -> None:
        case = all_cases[run["paper_id"]]
        g = run["generation"]
        payload = {"research_question": run["query"],
                   "hidden_target": {k: case["hidden_target"].get(k) for k in (
                       "material_initial_state", "intervention", "structural_mediator", "mechanism",
                       "predicted_outcome")},
                   "hypotheses": [{"id": 0, "text": " | ".join(f"{k}: {str(g.get(k, ''))[:400]}" for k in (
                       "hypothesis", "intervention", "mechanism"))}]}
        raw = lc.judge_chat_json(LABEL_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=4000)
        item = (raw.get("hypotheses") or [{}])[0] if isinstance(raw, dict) else {}
        try:
            lever = max(0, min(3, int(item.get("lever_match", 0))))
        except (TypeError, ValueError):
            lever = 0
        atomic_json(OUT / run["method"] / "labels" / f"{run['run_id']}.json",
                    {"run_id": run["run_id"], "labeller": lc.judge_info(), "lever_match": lever,
                     "intervention_class": str(item.get("intervention_class", "other")),
                     "target_type": raw.get("target_type") if isinstance(raw, dict) else None})

    jobs = [(r,) for r in all_runs(methods) if r["status"] == "ok"
            and not (OUT / r["method"] / "labels" / f"{r['run_id']}.json").exists()]
    return _parallel(jobs, job, workers)


# ---------------------------------------------------------------- report

def recon(scores: dict[str, int]) -> float:
    return statistics.fmean(scores[d] for d in PRIMARY_DIMENSIONS)


CORE_DIMENSIONS = ("intervention_reconstruction", "mechanism_agreement")


def core(scores: dict[str, int]) -> float:
    """Scientific core: intervention and mechanism agreement; hedged outcome wording cannot raise it."""
    return statistics.fmean(scores[d] for d in CORE_DIMENSIONS)


def mean(values: list[Any]) -> float | None:
    values = [v for v in values if v is not None]
    return round(statistics.fmean(values), 3) if values else None


def load_scored() -> list[dict[str, Any]]:
    rows = []
    for run in all_runs():
        base = OUT / run["method"]
        paths = {"gpt": base / "judgments" / "gpt56", "deep": base / "judgments" / "deepseek", "audit": base / "audit",
                 "label": base / "labels"}
        row = {"run": run}
        for key, folder in paths.items():
            p = folder / f"{run['run_id']}.json"
            row[key] = _read_json(p) if p.exists() else None
        rows.append(row)
    return rows


def unit_scores(rows: list[dict[str, Any]], method: str, judge: str, split: str,
                metric: Callable[[dict[str, int]], float] = recon) -> dict[tuple[str, str], float]:
    per: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in rows:
        run = r["run"]
        if run["method"] == method and r.get(judge) and (split == "all" or run["split"] == split):
            per[(run["paper_id"], run["query_level"])].append(metric(r[judge]["scores"]))
    return {k: statistics.fmean(v) for k, v in sorted(per.items())}


def paired(a: dict, b: dict) -> dict[str, Any]:
    per_paper: dict[str, list[float]] = defaultdict(list)
    for key in sorted(set(a) & set(b)):
        per_paper[key[0]].append(a[key] - b[key])
    if not per_paper:
        return {"units": 0}
    point, low, high = cluster_bootstrap(dict(sorted(per_paper.items())))
    p, pos, neg = exact_sign_test([statistics.fmean(v) for _, v in sorted(per_paper.items())])
    return {"units": sum(len(v) for v in per_paper.values()), "diff": round(point, 3),
            "ci95": [round(low, 3), round(high, 3)], "papers_up": pos, "papers_down": neg, "p": round(p, 4)}


def summarise(rows: list[dict[str, Any]], method: str, split: str) -> dict[str, Any]:
    rs = [r for r in rows if r["run"]["method"] == method and (split == "all" or r["run"]["split"] == split)]
    ok = [r for r in rs if r["run"]["status"] == "ok"]
    judged = [r for r in ok if r["gpt"]]
    gpt = unit_scores(rows, method, "gpt", split)
    deep = unit_scores(rows, method, "deep", split)
    audits = [r["audit"] for r in judged if r["audit"]]
    return {
        "runs": len(rs), "failed": len(rs) - len(ok), "judged": len(judged),
        "recon_gpt56": mean(list(gpt.values())), "recon_deepseek": mean(list(deep.values())),
        "core_gpt56": mean(list(unit_scores(rows, method, "gpt", split, core).values())),
        "core_deepseek": mean(list(unit_scores(rows, method, "deep", split, core).values())),
        "by_level": {lvl: mean([v for k, v in gpt.items() if k[1] == lvl]) for lvl in QUERY_LEVELS},
        **{d: mean([r["gpt"]["scores"][d] for r in judged]) for d in ALL_DIMENSIONS},
        "lever_ge2": mean([1.0 if r["label"]["lever_match"] >= 2 else 0.0 for r in judged if r["label"]]),
        "same_class": mean([1.0 if r["label"]["lever_match"] >= 1 else 0.0 for r in judged if r["label"]]),
        "complete_chain": mean([1.0 if all(v == 2 for v in a["chain"].values()) else 0.0 for a in audits]),
        "specificity": mean([mean([1.0 if v else 0.0 for v in a["specificity"].values()]) for a in audits]),
        "hedges": mean([len(HEDGE.findall(f"{r['run']['generation'].get('hypothesis', '')} "
                                          f"{r['run']['generation'].get('predicted_outcome', '')}")) for r in judged]),
        "llm_calls": mean([r["run"]["llm_calls"] for r in ok]), "chars_in": mean([r["run"]["chars_in"] for r in ok]),
        "seconds": mean([r["run"]["elapsed_seconds"] for r in ok]),
        "models": sorted({f"{k}={v}" for r in ok for k, v in r["run"]["models"].items()}),
    }


def report(split: str = "dev") -> dict[str, Any]:
    rows = load_scored()
    needed = {"dev", "test"} if split == "all" else {split}
    splits_by_method: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        splits_by_method[r["run"]["method"]].add(r["run"]["split"])
    # Only methods run on every split the report covers (dev-only methods are not part of a test or all-12 report).
    methods = sorted(m for m, s in splits_by_method.items() if needed <= s)
    table = {m: summarise(rows, m, split) for m in methods}
    comparisons: dict[str, Any] = {}
    for judge in ("gpt", "deep"):
        for metric_name, metric in (("recon", recon), ("core", core)):
            key = judge if metric_name == "recon" else f"{judge}_core"
            comparisons[key] = {}
            for base in BASELINES:
                b = unit_scores(rows, base, judge, split, metric)
                items = [{"method": m, "vs": base, **paired(unit_scores(rows, m, judge, split, metric), b)}
                         for m in methods if m != base]
                for item, adj in zip(items, holm_adjust([i.get("p", 1.0) for i in items])):
                    item["holm_p"] = round(adj, 4)
                comparisons[key][base] = items
    analysis = {"split": split, "table": table, "comparisons": comparisons}
    atomic_json(OUT / f"report_{split}.json", analysis)
    (OUT / f"report_{split}.md").write_text(render(analysis))
    return analysis


def _f(x: Any) -> str:
    return "-" if x is None else (f"{x:.2f}" if isinstance(x, float) else str(x))


def render(a: dict[str, Any]) -> str:
    lines = [f"# Loop results ({a['split']})", "",
             "| method | runs | failed | GPT-5.6 | DeepSeek | core GPT | core DS | broad / problem / expert | intervention | "
             "mechanism | outcome | problem align | lever>=2 | same class | specificity | hedges | novelty | calls/run |",
             "|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for m, s in a["table"].items():
        lines.append(f"| {m} | {s['runs']} | {s['failed']} | {_f(s['recon_gpt56'])} | {_f(s['recon_deepseek'])} | "
                     f"{_f(s['core_gpt56'])} | {_f(s['core_deepseek'])} | "
                     + " / ".join(_f(s["by_level"][l]) for l in QUERY_LEVELS)
                     + f" | {_f(s['intervention_reconstruction'])} | {_f(s['mechanism_agreement'])} | "
                     f"{_f(s['outcome_agreement'])} | {_f(s['problem_alignment'])} | {_f(s['lever_ge2'])} | "
                     f"{_f(s['same_class'])} | {_f(s['specificity'])} | {_f(s['hedges'])} | {_f(s['novelty'])} | "
                     f"{_f(s['llm_calls'])} |")
    for judge, label in (("gpt", "GPT-5.6"), ("deep", "DeepSeek"), ("gpt_core", "GPT-5.6, core"),
                         ("deep_core", "DeepSeek, core")):
        for base, items in a["comparisons"][judge].items():
            lines += ["", f"## vs {base} ({label})", "", "| method | units | diff | 95% CI | up | down | p | Holm p |",
                      "|---|---:|---:|---|---:|---:|---:|---:|"]
            for i in items:
                if i.get("units"):
                    lines.append(f"| {i['method']} | {i['units']} | {_f(i['diff'])} | {i['ci95']} | {i['papers_up']} | "
                                 f"{i['papers_down']} | {_f(i['p'])} | {_f(i['holm_p'])} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("generate", "judge", "cross_judge", "audit", "label", "evaluate", "report"))
    parser.add_argument("--method", action="append")
    parser.add_argument("--split", default="dev", choices=("dev", "test", "all"))
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if args.stage == "generate":
        for method in args.method or []:
            print(method, generate_stage(method, args.split, args.workers, args.final), flush=True)
    elif args.stage == "evaluate":
        for fn in (judge_stage, cross_judge_stage, audit_stage, label_stage):
            print(fn.__name__, fn(args.workers, args.method), flush=True)
    elif args.stage == "report":
        print(render(report(args.split)))
    else:
        fn = {"judge": judge_stage, "cross_judge": cross_judge_stage, "audit": audit_stage,
              "label": label_stage}[args.stage]
        print(fn(args.workers, args.method))


if __name__ == "__main__":
    # Run through the importable module so that methods registered by loop_methods are visible.
    import hypo_loop as _module

    _module.main()
