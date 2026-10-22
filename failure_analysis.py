"""Failure analysis across every hypothesis-generation method evaluated on the 12 held-out HEA cases.

Methods (arms) and their sources:
- closed_book, text_oneshot, v2_oneshot, tool_agent: eval_v3
- tool_agent_kg: eval_v4_matkg
- resample (fresh tool_agent sample), self_revise, critique: eval_critique

Stages
1. code-errors: GPT-5.6 assigns every judge fatal error to one category of a fixed taxonomy.
2. evidence-ceiling: for each case, the 20 eligible (pre-cutoff) records most similar to the hidden target are rated
   by GPT-5.6 for whether they anticipate the target. This separates "evidence absent" from "evidence missed" from
   "evidence used badly". This is analysis only: it reads the hidden target, and nothing it produces feeds back
   into any generation.
3. report: deterministic tables over all units, joined with the two coded outputs.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import statistics
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from hypothesis_evidence_v2 import atomic_json, load_evidence
from llm_client import judge_chat_json, judge_info
from temporal_eval_critique import analyze_trace
from temporal_eval_v3 import ALL_DIMENSIONS, EXPERIMENT_DIR, PRIMARY_DIMENSIONS, QUERY_LEVELS, build_corpus
from temporal_hypothesis_benchmark import _date_map, _read_json, retrieve

OUT = EXPERIMENT_DIR / "failure_analysis"
CASES_DIR = EXPERIMENT_DIR / "temporal_v2" / "benchmark_cases"
METADATA = EXPERIMENT_DIR / "temporal_v2" / "temporal_metadata.json"
V2_DIR = EXPERIMENT_DIR / "temporal_v2" / "materials_evidence_v2"
PAPER_MAPS = EXPERIMENT_DIR / "section_aware" / "paper_maps"
V3 = EXPERIMENT_DIR / "eval_v3"
V4 = EXPERIMENT_DIR / "eval_v4_matkg"
CRIT = EXPERIMENT_DIR / "eval_critique"

ARMS = ("closed_book", "text_oneshot", "v2_oneshot", "tool_agent", "resample", "tool_agent_kg",
        "self_revise", "critique")
HARD_FAILURE = 0.5
ORACLE_K = 20
ORACLE_TEXT_CHARS = 1500

# Hand-coded from each case's hidden-target intervention (see README for the rationale per case).
TARGET_TYPES = {
    "PMC10759803": "composition",
    "PMC11077685": "processing",
    "PMC11087546": "processing",
    "PMC11375712": "processing",
    "PMC12298864": "processing",
    "PMC12806431": "processing",
    "PMC12941549": "processing",
    "PMC11355469": "computational",
    "PMC11375216": "computational",
    "PMC11606917": "computational",
    "PMC12029629": "computational",
    "PMC11775865": "characterization",
}

ERROR_CATEGORIES = {
    "wrong_intervention": "proposes a different intervention, design route, composition change or process than the target",
    "wrong_mechanism": "wrong or missing mechanism or structural mediator (phase, microstructure, defect process)",
    "wrong_outcome": "predicted outcome disagrees with the target in direction, magnitude or property",
    "wrong_baseline": "misidentifies the starting material, baseline alloy, or baseline property values",
    "wrong_conditions": "wrong test or processing conditions, temperature regime, loading mode or scope",
    "physical_error": "physically implausible claim, arithmetic, unit, density, crystallographic or thermodynamic error",
    "evidence_unsupported": "cited evidence is irrelevant or does not support the claim, or claims are asserted without support",
    "evidence_contradicted": "cited evidence contradicts the claim",
    "internal_inconsistency": "the hypothesis contradicts itself across its own fields",
    "untestable_or_vague": "falsification is weak or does not test the claim, thresholds are missing, or claims are vague or hedged",
    "other": "anything that fits none of the above",
}
CODER_SYSTEM = (
    "You classify error statements written by a judge who compared a generated materials-science hypothesis with "
    "the true result of a paper. Assign each error exactly one category, choosing the one that best describes its "
    "main problem. Categories: "
    + "; ".join(f"{name}: {text}" for name, text in ERROR_CATEGORIES.items())
    + ". Return a JSON object {\"labels\": [{\"index\": int, \"category\": str}]} with one entry per input error, "
    "in the same order."
)
CEILING_SYSTEM = (
    "You assess whether earlier literature anticipates a later paper's result. The input has the later paper's "
    "result (its starting material, intervention, structural mediator, mechanism and outcome), its date, and "
    "records from papers published before that date, labelled R1, R2, and so on. For each record, rate "
    "intervention_support: 2 if it describes the same intervention (or nearly the same) for this or a closely "
    "similar alloy system, 1 if it describes a related intervention or the same intervention on a different "
    "system, 0 otherwise; and mechanism_support: 2 if it describes the same mechanism or structural mediator in a "
    "similar system, 1 if related, 0 otherwise. Then rate the whole set: reconstructibility 2 if an expert reading "
    "only these records could plausibly propose the later paper's intervention and mechanism, 1 if the records "
    "point in the right direction but the specific intervention would need a substantial new idea, 0 if they do "
    "not point toward it. Return JSON {\"records\": [{\"label\": str, \"intervention_support\": int, "
    "\"mechanism_support\": int}], \"reconstructibility\": int, \"reason\": str}."
)
HEDGE = re.compile(r"\b(may|might|could|potentially|possibly|uncertain|unclear|further investigation|"
                   r"requires? further|likely|perhaps|suggests?)\b", re.IGNORECASE)


# ---------------------------------------------------------------- loading

def _judgment_scores(judgment: dict[str, Any]) -> dict[str, Any]:
    scores = judgment["scores"]
    return {
        "scores": scores,
        "reconstruction": statistics.fmean(scores[d] for d in PRIMARY_DIMENSIONS),
        "overall": statistics.fmean(scores[d] for d in ALL_DIMENSIONS),
        "classification": judgment.get("classification", ""),
        "fatal_errors": [str(e) for e in judgment.get("fatal_errors", [])],
        "explanation": judgment.get("explanation", ""),
    }


def _read_ids_from_trace(trace: list[dict[str, Any]]) -> list[str]:
    return sorted({step["args"]["record_id"] for step in trace
                   if step.get("tool") == "read_record" and isinstance(step.get("args"), dict)
                   and "record_id" in step["args"]})


def load_units() -> list[dict[str, Any]]:
    cases = {c["paper_id"]: c for c in (_read_json(p) for p in sorted(CASES_DIR.glob("PMC*.json")))}
    units: list[dict[str, Any]] = []

    def add(arm: str, paper_id: str, level: str, run: dict[str, Any] | None, generation: dict[str, Any] | None,
            judgment_path: Path, read_ids: list[str], cited_ids: list[str], extra: dict[str, Any]) -> None:
        unit = {
            "arm": arm, "paper_id": paper_id, "query_level": level,
            "date": cases[paper_id]["publication_date"], "target_type": TARGET_TYPES[paper_id],
            "status": (run or {}).get("status", "ok") if run is not None else "ok",
            "judged": judgment_path.exists(), "read_ids": read_ids, "cited_ids": cited_ids,
            "generation": generation or {}, **extra,
        }
        if unit["judged"]:
            unit.update(_judgment_scores(_read_json(judgment_path)))
        units.append(unit)

    for setting in ("closed_book", "text_oneshot", "v2_oneshot", "tool_agent"):
        for run_path in sorted((V3 / "runs").glob(f"PMC*__{setting}.json")):
            run = _read_json(run_path)
            reads = _read_ids_from_trace(run["tool_trace"]) if setting == "tool_agent" else run["accessed_record_ids"]
            add(setting, run["paper_id"], run["query_level"], run, run.get("generation"),
                V3 / "judgments" / "absolute" / run_path.name, reads, run["cited_evidence_ids"],
                {"trace": analyze_trace(run) if setting == "tool_agent" else None,
                 "citation_status": (run.get("generation") or {}).get("citation_validation", {}).get("status", "")})
    for run_path in sorted((V4 / "runs").glob("PMC*__tool_agent_kg.json")):
        run = _read_json(run_path)
        add("tool_agent_kg", run["paper_id"], run["query_level"], run, run.get("generation"),
            V4 / "judgments" / "absolute" / run_path.name, _read_ids_from_trace(run["tool_trace"]),
            run["cited_evidence_ids"],
            {"trace": analyze_trace(run),
             "kg_cited": sum(1 for rid in run["cited_evidence_ids"] if rid.startswith("KG::")),
             "citation_status": (run.get("generation") or {}).get("citation_validation", {}).get("status", "")})
    for run_path in sorted((CRIT / "baseline_resample" / "runs").glob("PMC*__tool_agent.json")):
        run = _read_json(run_path)
        add("resample", run["paper_id"], run["query_level"], run, run.get("generation"),
            CRIT / "baseline_resample" / "judgments" / "absolute" / run_path.name,
            _read_ids_from_trace(run["tool_trace"]), run["cited_evidence_ids"],
            {"trace": analyze_trace(run),
             "citation_status": (run.get("generation") or {}).get("citation_validation", {}).get("status", "")})
    for arm in ("self_revise", "critique"):
        for rec_path in sorted((CRIT / "revisions" / arm).glob("PMC*.json")):
            rec = _read_json(rec_path)
            base = _read_json(V3 / "runs" / rec_path.name)
            findings = sum(len(c.get("findings", [])) for c in rec.get("critics", []))
            add(arm, rec["paper_id"], rec["query_level"], {"status": rec.get("status", "")},
                rec.get("revised_generation"), CRIT / "judgments" / arm / rec_path.name,
                _read_ids_from_trace(base["tool_trace"]), rec.get("revised_cited_evidence_ids", []),
                {"critic_findings": findings,
                 "citation_set_changed": set(rec.get("revised_cited_evidence_ids", []))
                 != set(rec.get("original_cited_evidence_ids", []))})
    return units


# ---------------------------------------------------------------- stage 1: error coding

def _unit_key(unit: dict[str, Any]) -> str:
    return f"{unit['arm']}__{unit['paper_id']}__{unit['query_level']}"


def code_errors(units: list[dict[str, Any]], workers: int, resume: bool) -> dict[str, int]:
    out_dir = OUT / "error_codes"
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = [u for u in units if u["judged"] and u["fatal_errors"]
            and not (resume and (out_dir / f"{_unit_key(u)}.json").exists())]

    def job(unit: dict[str, Any]) -> None:
        errors = unit["fatal_errors"]
        payload = {"errors": [{"index": i, "text": text} for i, text in enumerate(errors)]}
        raw = judge_chat_json(CODER_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=6000)
        labels = validate_labels(raw, len(errors))
        atomic_json(out_dir / f"{_unit_key(unit)}.json", {
            "unit": _unit_key(unit), "coder": judge_info(),
            "errors": [{"text": text, "category": labels[i]} for i, text in enumerate(errors)],
        })

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for future in as_completed([pool.submit(job, u) for u in jobs]):
            future.result()
    return {"coded_units": len(jobs)}


def validate_labels(raw: Any, count: int) -> list[str]:
    labels = ["other"] * count
    items = raw.get("labels", []) if isinstance(raw, dict) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            index = int(item.get("index"))
        except (TypeError, ValueError):
            continue
        category = str(item.get("category", "")).strip()
        if 0 <= index < count and category in ERROR_CATEGORIES:
            labels[index] = category
    return labels


# ---------------------------------------------------------------- stage 2: evidence ceiling

def target_text(hidden: dict[str, Any]) -> str:
    return " ".join(str(hidden.get(key, "")) for key in
                    ("material_initial_state", "intervention", "structural_mediator", "mechanism"))


def evidence_ceiling(resume: bool, workers: int) -> dict[str, int]:
    out_dir = OUT / "evidence_ceiling"
    out_dir.mkdir(parents=True, exist_ok=True)
    metadata = _date_map(METADATA)
    v2_units = load_evidence(V2_DIR)
    cases = [_read_json(p) for p in sorted(CASES_DIR.glob("PMC*.json"))]
    jobs = [c for c in cases if not (resume and (out_dir / f"{c['paper_id']}.json").exists())]

    def job(case: dict[str, Any]) -> None:
        _, chunks, units = build_corpus(case["paper_id"], case["publication_date"], metadata, v2_units, PAPER_MAPS)
        top = retrieve(target_text(case["hidden_target"]), [*chunks, *units], limit=ORACLE_K)
        for record in top:
            if record.publication_date >= case["publication_date"] or record.paper_id == case["paper_id"]:
                raise ValueError(f"oracle retrieval returned an ineligible record {record.record_id}")
        labelled = {f"R{i + 1}": record for i, record in enumerate(top)}
        payload = {
            "later_paper_date": case["publication_date"],
            "later_paper_result": {k: case["hidden_target"].get(k) for k in (
                "material_initial_state", "intervention", "structural_mediator", "mechanism", "predicted_outcome")},
            "earlier_records": [{"label": label, "date": r.publication_date, "text": r.text[:ORACLE_TEXT_CHARS]}
                                for label, r in labelled.items()],
        }
        raw = judge_chat_json(CEILING_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=12000)
        ratings = {}
        for item in (raw.get("records", []) if isinstance(raw, dict) else []):
            label = str(item.get("label", ""))
            if label in labelled:
                ratings[labelled[label].record_id] = {
                    "intervention_support": _clamp(item.get("intervention_support")),
                    "mechanism_support": _clamp(item.get("mechanism_support")),
                }
        atomic_json(out_dir / f"{case['paper_id']}.json", {
            "paper_id": case["paper_id"], "coder": judge_info(), "oracle_k": ORACLE_K,
            "eligible_records": len(chunks) + len(units),
            "records": [{"record_id": r.record_id, "paper_id": r.paper_id, "date": r.publication_date,
                         **ratings.get(r.record_id, {"intervention_support": 0, "mechanism_support": 0})}
                        for r in top],
            "reconstructibility": _clamp(raw.get("reconstructibility") if isinstance(raw, dict) else 0),
            "reason": str(raw.get("reason", ""))[:1500] if isinstance(raw, dict) else "",
        })

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for future in as_completed([pool.submit(job, c) for c in jobs]):
            future.result()
    return {"cases_rated": len(jobs)}


def _clamp(value: Any) -> int:
    try:
        return max(0, min(2, int(value)))
    except (TypeError, ValueError):
        return 0


# ---------------------------------------------------------------- stage 3: report

def mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else float("nan")


def spearman(x: list[float], y: list[float]) -> float:
    def ranks(values: list[float]) -> list[float]:
        order = sorted(range(len(values)), key=lambda i: values[i])
        result = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            for k in range(i, j + 1):
                result[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return result
    if len(x) < 3:
        return float("nan")
    rx, ry = ranks(x), ranks(y)
    mx, my = mean(rx), mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def hedge_count(generation: dict[str, Any]) -> int:
    text = f"{generation.get('hypothesis', '')} {generation.get('predicted_outcome', '')}"
    return len(HEDGE.findall(text))


def report() -> dict[str, Any]:
    (OUT / "results").mkdir(parents=True, exist_ok=True)
    units = load_units()
    by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for u in units:
        by_arm[u["arm"]].append(u)
    judged = {arm: [u for u in by_arm[arm] if u["judged"]] for arm in ARMS}

    # error codes
    codes: dict[str, list[dict[str, str]]] = {}
    for path in sorted((OUT / "error_codes").glob("*.json")):
        payload = _read_json(path)
        codes[payload["unit"]] = payload["errors"]
    ceiling = {p.stem: _read_json(p) for p in sorted((OUT / "evidence_ceiling").glob("PMC*.json"))}

    overview = {}
    for arm in ARMS:
        rows = judged[arm]
        classes = Counter(u["classification"] for u in rows)
        overview[arm] = {
            "units": len(by_arm[arm]), "judged": len(rows),
            "failed_generation": sum(1 for u in by_arm[arm] if not u["judged"]),
            "reconstruction": round(mean([u["reconstruction"] for u in rows]), 3),
            "overall": round(mean([u["overall"] for u in rows]), 3),
            "hard_failure_rate": round(sum(u["reconstruction"] <= HARD_FAILURE for u in rows) / max(1, len(rows)), 3),
            "classifications": dict(classes),
            "zero_rate": {d: round(sum(u["scores"][d] == 0 for u in rows) / max(1, len(rows)), 3)
                          for d in ALL_DIMENSIONS},
            "dimension_mean": {d: round(mean([u["scores"][d] for u in rows]), 3) for d in ALL_DIMENSIONS},
            "hedges_per_hypothesis": round(mean([hedge_count(u["generation"]) for u in rows]), 2),
        }

    # error categories per arm
    error_mix = {}
    for arm in ARMS:
        counter: Counter[str] = Counter()
        units_with: Counter[str] = Counter()
        for u in judged[arm]:
            labels = [e["category"] for e in codes.get(_unit_key(u), [])]
            counter.update(labels)
            units_with.update(set(labels))
        total = sum(counter.values())
        error_mix[arm] = {
            "errors": total,
            "errors_per_unit": round(total / max(1, len(judged[arm])), 2),
            "share": {c: round(counter[c] / max(1, total), 3) for c in ERROR_CATEGORIES},
            "units_with_category": {c: round(units_with[c] / max(1, len(judged[arm])), 3) for c in ERROR_CATEGORIES},
        }

    # difficulty by paper, target type, level, date
    papers = sorted(TARGET_TYPES)
    paper_matrix = {p: {arm: round(mean([u["reconstruction"] for u in judged[arm] if u["paper_id"] == p]), 2)
                        for arm in ARMS} for p in papers}
    by_type = {t: {arm: round(mean([u["reconstruction"] for u in judged[arm] if u["target_type"] == t]), 2)
                   for arm in ARMS}
               for t in ("composition", "processing", "computational", "characterization")}
    type_counts = Counter(TARGET_TYPES.values())
    by_level = {lvl: {arm: round(mean([u["reconstruction"] for u in judged[arm] if u["query_level"] == lvl]), 2)
                      for arm in ARMS} for lvl in QUERY_LEVELS}
    all_fail_units = []
    for p in papers:
        for lvl in QUERY_LEVELS:
            scores = [u["reconstruction"] for arm in ARMS for u in judged[arm]
                      if u["paper_id"] == p and u["query_level"] == lvl]
            if scores and max(scores) <= HARD_FAILURE:
                all_fail_units.append({"paper_id": p, "query_level": lvl, "target_type": TARGET_TYPES[p],
                                       "best_reconstruction": max(scores)})
    date_effect = {}
    for arm in ARMS:
        rows = judged[arm]
        early = [u["reconstruction"] for u in rows if u["date"] < "2025-01-01"]
        late = [u["reconstruction"] for u in rows if u["date"] >= "2025-01-01"]
        date_effect[arm] = {
            "2024_cases": round(mean(early), 2), "2025_2026_cases": round(mean(late), 2),
            "spearman_date_vs_score": round(spearman([float(u["date"].replace("-", "")) for u in rows],
                                                    [u["reconstruction"] for u in rows]), 3),
        }

    # evidence ceiling joined with method access
    ceiling_rows = {}
    for p, c in ceiling.items():
        support = {r["record_id"]: r for r in c["records"]}
        strong = {rid for rid, r in support.items() if r["intervention_support"] == 2 or r["mechanism_support"] == 2}
        any_support = {rid for rid, r in support.items() if r["intervention_support"] >= 1 or r["mechanism_support"] >= 1}
        ceiling_rows[p] = {"reconstructibility": c["reconstructibility"], "strong": strong, "any": any_support,
                           "reason": c["reason"], "eligible_records": c["eligible_records"]}
    access = {}
    for arm in ARMS:
        if arm == "closed_book":
            continue
        rows = [u for u in judged[arm] if u["paper_id"] in ceiling_rows]
        read_any = [bool(set(u["read_ids"]) & ceiling_rows[u["paper_id"]]["any"]) for u in rows]
        read_strong = [bool(set(u["read_ids"]) & ceiling_rows[u["paper_id"]]["strong"]) for u in rows]
        cited_any = [bool(set(u["cited_ids"]) & ceiling_rows[u["paper_id"]]["any"]) for u in rows]
        with_ev = [u["reconstruction"] for u, flag in zip(rows, read_any) if flag]
        without_ev = [u["reconstruction"] for u, flag in zip(rows, read_any) if not flag]
        access[arm] = {
            "units": len(rows),
            "read_any_supportive": round(sum(read_any) / max(1, len(rows)), 3),
            "read_strong_supportive": round(sum(read_strong) / max(1, len(rows)), 3),
            "cited_any_supportive": round(sum(cited_any) / max(1, len(rows)), 3),
            "recon_when_read_supportive": round(mean(with_ev), 2) if with_ev else None,
            "recon_when_not": round(mean(without_ev), 2) if without_ev else None,
        }
    reconstructibility = {p: r["reconstructibility"] for p, r in ceiling_rows.items()}
    by_reconstructibility = {}
    for level_value in (0, 1, 2):
        ps = {p for p, v in reconstructibility.items() if v == level_value}
        by_reconstructibility[str(level_value)] = {
            "cases": sorted(ps),
            **{arm: round(mean([u["reconstruction"] for u in judged[arm] if u["paper_id"] in ps]), 2) if ps else None
               for arm in ARMS},
        }

    # tool-agent process
    process = {}
    for arm in ("tool_agent", "resample", "tool_agent_kg"):
        rows = [u for u in judged[arm] if u.get("trace")]
        traces = [u["trace"] for u in rows]
        pages = []
        for u in rows:
            pages.append(u["trace"]["reads"] - u["trace"]["distinct_records_read"])
        process[arm] = {
            "runs": len(rows),
            "budget_exhausted": round(sum(t["tool_calls"] >= 12 for t in traces) / max(1, len(traces)), 3),
            "mean_searches": round(mean([t["searches"] for t in traces]), 2),
            "mean_reads": round(mean([t["reads"] for t in traces]), 2),
            "mean_distinct_records_read": round(mean([t["distinct_records_read"] for t in traces]), 2),
            "mean_paging_reads": round(mean(pages), 2),
            "mean_repeated_searches": round(mean([t["repeated_searches"] for t in traces]), 2),
            "runs_with_rejected_submit": sum(t["rejected_submissions"] > 0 for t in traces),
            "mean_cited": round(mean([t["cited_records"] for t in traces]), 2),
            "mean_read_but_uncited": round(mean([t["read_but_uncited"] for t in traces]), 2),
            "spearman_distinct_reads_vs_score": round(spearman(
                [t["distinct_records_read"] for t in traces], [u["reconstruction"] for u in rows]), 3),
            "spearman_searches_vs_score": round(spearman(
                [t["searches"] for t in traces], [u["reconstruction"] for u in rows]), 3),
        }
        if arm == "tool_agent_kg":
            cited = [u["reconstruction"] for u in rows if u.get("kg_cited")]
            not_cited = [u["reconstruction"] for u in rows if not u.get("kg_cited")]
            process[arm]["recon_when_kg_cited"] = round(mean(cited), 2) if cited else None
            process[arm]["recon_when_kg_not_cited"] = round(mean(not_cited), 2) if not_cited else None
            process[arm]["runs_citing_kg"] = len(cited)

    # one-shot citation repair and generation failures
    generation_health = {}
    for arm in ("closed_book", "text_oneshot", "v2_oneshot", "tool_agent", "resample", "tool_agent_kg"):
        generation_health[arm] = {
            "failed": [f"{u['paper_id']}__{u['query_level']}" for u in by_arm[arm] if not u["judged"]],
            "citation_status": dict(Counter(u.get("citation_status", "") for u in by_arm[arm] if u["judged"])),
        }

    # run-to-run noise: original tool_agent vs fresh resample on the same units
    original = {(u["paper_id"], u["query_level"]): u for u in judged["tool_agent"]}
    resample = {(u["paper_id"], u["query_level"]): u for u in judged["resample"]}
    common = sorted(set(original) & set(resample))
    diffs = [resample[k]["reconstruction"] - original[k]["reconstruction"] for k in common]
    noise = {
        "units": len(common),
        "mean_difference": round(mean(diffs), 3),
        "sd_of_unit_differences": round(statistics.pstdev(diffs), 3) if diffs else None,
        "mean_absolute_difference": round(mean([abs(d) for d in diffs]), 3),
        "units_changing_by_1_or_more": sum(abs(d) >= 1 for d in diffs),
        "classification_changed": sum(original[k]["classification"] != resample[k]["classification"] for k in common),
    }

    # pairwise position bias
    position = {}
    for name, directory in (("eval_v3", V3), ("eval_v4_matkg", V4)):
        pairs = [_read_json(p) for p in sorted((directory / "judgments" / "pairwise").glob("*.json"))]
        position[name] = {
            "pairs": len(pairs),
            "position_inconsistent": sum(p["consistency"] != "consistent" for p in pairs),
            "rate": round(sum(p["consistency"] != "consistent" for p in pairs) / max(1, len(pairs)), 3),
        }

    # critique: does the number of findings predict a bigger drop?
    critique_detail = {}
    base_by_key = {(u["paper_id"], u["query_level"]): u for u in judged["tool_agent"]}
    for arm in ("critique", "self_revise"):
        rows = [u for u in judged[arm] if (u["paper_id"], u["query_level"]) in base_by_key]
        deltas = [u["reconstruction"] - base_by_key[(u["paper_id"], u["query_level"])]["reconstruction"] for u in rows]
        detail = {
            "units": len(rows),
            "improved": sum(d > 0 for d in deltas), "worse": sum(d < 0 for d in deltas),
            "unchanged": sum(d == 0 for d in deltas),
            "delta_when_citations_changed": round(mean([d for u, d in zip(rows, deltas) if u.get("citation_set_changed")]), 2)
            if any(u.get("citation_set_changed") for u in rows) else None,
            "delta_when_citations_kept": round(mean([d for u, d in zip(rows, deltas) if not u.get("citation_set_changed")]), 2),
            "spearman_hedges_vs_delta": round(spearman([hedge_count(u["generation"]) for u in rows], deltas), 3),
        }
        if arm == "critique":
            detail["spearman_findings_vs_delta"] = round(spearman([u["critic_findings"] for u in rows], deltas), 3)
        originals = [base_by_key[(u["paper_id"], u["query_level"])]["reconstruction"] for u in rows]
        detail["spearman_original_vs_delta"] = round(spearman(originals, deltas), 3)
        detail["delta_when_original_low"] = round(mean([d for o, d in zip(originals, deltas) if o < 1.5]), 2)
        detail["delta_when_original_high"] = round(mean([d for o, d in zip(originals, deltas) if o >= 1.5]), 2)
        critique_detail[arm] = detail
    rows = [u for u in judged["resample"] if (u["paper_id"], u["query_level"]) in base_by_key]
    originals = [base_by_key[(u["paper_id"], u["query_level"])]["reconstruction"] for u in rows]
    deltas = [u["reconstruction"] - o for u, o in zip(rows, originals)]
    critique_detail["resample"] = {
        "units": len(rows), "improved": sum(d > 0 for d in deltas), "worse": sum(d < 0 for d in deltas),
        "unchanged": sum(d == 0 for d in deltas),
        "spearman_original_vs_delta": round(spearman(originals, deltas), 3),
        "delta_when_original_low": round(mean([d for o, d in zip(originals, deltas) if o < 1.5]), 2),
        "delta_when_original_high": round(mean([d for o, d in zip(originals, deltas) if o >= 1.5]), 2),
    }

    analysis = {
        "overview": overview, "error_mix": error_mix, "paper_matrix": paper_matrix,
        "by_target_type": by_type, "target_type_counts": dict(type_counts), "by_level": by_level,
        "all_methods_fail": all_fail_units, "date_effect": date_effect,
        "evidence_ceiling": {p: {k: (sorted(v) if isinstance(v, set) else v) for k, v in r.items()}
                             for p, r in ceiling_rows.items()},
        "evidence_access": access, "by_reconstructibility": by_reconstructibility,
        "stratified": stratified(units, codes, ceiling_rows),
        "tool_process": process, "generation_health": generation_health, "noise": noise,
        "position_bias": position, "revision_detail": critique_detail,
        "coded_errors_total": sum(len(v) for v in codes.values()),
    }
    atomic_json(OUT / "results" / "analysis.json", analysis)
    (OUT / "results" / "tables.md").write_text(render_tables(analysis))
    write_spot_check(codes)
    return analysis


TOOL_ARMS = ("tool_agent", "resample", "tool_agent_kg")


def stratified(units: list[dict[str, Any]], codes: dict[str, list[dict[str, str]]],
               ceiling_rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Confound checks: query level drives scores, so evidence and difficulty effects are compared within level."""
    judged = [u for u in units if u["judged"] and u["paper_id"] in ceiling_rows]

    def read_support(u: dict[str, Any]) -> bool:
        return bool(set(u["read_ids"]) & ceiling_rows[u["paper_id"]]["any"])

    def error_share(rows: list[dict[str, Any]]) -> dict[str, float]:
        counter: Counter[str] = Counter()
        for u in rows:
            counter.update(e["category"] for e in codes.get(_unit_key(u), []))
        total = sum(counter.values())
        return {c: round(counter[c] / max(1, total), 3) for c in ERROR_CATEGORIES}

    access_by_level = {}
    anchoring = {}
    for lvl in QUERY_LEVELS:
        rows = [u for u in judged if u["arm"] in TOOL_ARMS and u["query_level"] == lvl]
        yes = [u for u in rows if read_support(u)]
        no = [u for u in rows if not read_support(u)]
        access_by_level[lvl] = {
            "read_supportive_rate": round(len(yes) / max(1, len(rows)), 3),
            "n_read": len(yes), "recon_read": round(mean([u["reconstruction"] for u in yes]), 2) if yes else None,
            "n_not": len(no), "recon_not": round(mean([u["reconstruction"] for u in no]), 2) if no else None,
        }
        anchoring[lvl] = {
            flag: {
                "units": len(group),
                "errors_per_unit": round(sum(len(codes.get(_unit_key(u), [])) for u in group) / max(1, len(group)), 2),
                "dimension_mean": {d: round(mean([u["scores"][d] for u in group]), 2) for d in PRIMARY_DIMENSIONS}
                if group else {},
                "error_share": error_share(group),
            }
            for flag, group in (("read_supportive", yes), ("not_read", no))
        }
    within_paper = []
    for p in sorted(ceiling_rows):
        rows = [u for u in judged if u["arm"] in TOOL_ARMS and u["paper_id"] == p]
        yes = [u["reconstruction"] for u in rows if read_support(u)]
        no = [u["reconstruction"] for u in rows if not read_support(u)]
        if yes and no:
            within_paper.append({"paper_id": p, "difference": round(mean(yes) - mean(no), 2),
                                 "n_read": len(yes), "n_not": len(no)})
    reconstructibility_by_level = {
        lvl: {str(r): round(mean([u["reconstruction"] for u in judged if u["query_level"] == lvl
                                  and ceiling_rows[u["paper_id"]]["reconstructibility"] == r]), 2)
              for r in (1, 2)}
        for lvl in QUERY_LEVELS
    }
    return {
        "evidence_access_by_level": access_by_level,
        "evidence_access_within_paper": within_paper,
        "evidence_access_within_paper_mean": round(mean([w["difference"] for w in within_paper]), 2),
        "anchoring_by_level": anchoring,
        "reconstructibility_by_level": reconstructibility_by_level,
        "error_share_by_level": {lvl: error_share([u for u in judged if u["query_level"] == lvl]) for lvl in QUERY_LEVELS},
        "error_share_by_paper": {p: error_share([u for u in judged if u["paper_id"] == p]) for p in sorted(ceiling_rows)},
    }


def write_spot_check(codes: dict[str, list[dict[str, str]]], n: int = 40) -> None:
    flat = [(unit, e["category"], e["text"]) for unit, errors in sorted(codes.items()) for e in errors]
    rng = random.Random(20261022)
    sample = rng.sample(flat, min(n, len(flat)))
    lines = ["| # | Unit | Category | Error text |", "|---:|---|---|---|"]
    for i, (unit, category, text) in enumerate(sample, 1):
        lines.append(f"| {i} | {unit} | {category} | {text.replace('|', '/')[:300]} |")
    (OUT / "results" / "spot_check_sample.md").write_text("\n".join(lines) + "\n")


def _fmt(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return f"{value:.2f}" if isinstance(value, float) else str(value)


def render_tables(a: dict[str, Any]) -> str:
    lines = ["## Overview", "", "| Method | Judged | Failed gen. | Reconstruction | Overall | Hard failure (≤0.5) | Exact / partial / plausible / unsupported | Hedges per hypothesis |",
             "|---|---:|---:|---:|---:|---:|---|---:|"]
    for arm, o in a["overview"].items():
        c = o["classifications"]
        lines.append(f"| {arm} | {o['judged']} | {o['failed_generation']} | {o['reconstruction']:.2f} | {o['overall']:.2f} | "
                     f"{o['hard_failure_rate']:.0%} | {c.get('exact_reconstruction', 0)} / {c.get('partial_reconstruction', 0)} / "
                     f"{c.get('plausible_alternative', 0)} / {c.get('unsupported', 0)} | {o['hedges_per_hypothesis']:.2f} |")
    lines += ["", "## Zero-score rate by dimension", "", "| Dimension | " + " | ".join(ARMS) + " |",
              "|---|" + "---:|" * len(ARMS)]
    for d in ALL_DIMENSIONS:
        lines.append(f"| {d} | " + " | ".join(f"{a['overview'][arm]['zero_rate'][d]:.0%}" for arm in ARMS) + " |")
    lines += ["", "## Fatal-error categories (share of each method's errors)", "",
              "| Category | " + " | ".join(ARMS) + " |", "|---|" + "---:|" * len(ARMS)]
    for c in ERROR_CATEGORIES:
        lines.append(f"| {c} | " + " | ".join(f"{a['error_mix'][arm]['share'][c]:.0%}" for arm in ARMS) + " |")
    lines.append("| errors per unit | " + " | ".join(f"{a['error_mix'][arm]['errors_per_unit']:.2f}" for arm in ARMS) + " |")
    lines += ["", "## Reconstruction by target type", "", "| Target type (cases) | " + " | ".join(ARMS) + " |",
              "|---|" + "---:|" * len(ARMS)]
    for t, row in a["by_target_type"].items():
        lines.append(f"| {t} ({a['target_type_counts'].get(t, 0)}) | " + " | ".join(_fmt(row[arm]) for arm in ARMS) + " |")
    lines += ["", "## Reconstruction by query level", "", "| Level | " + " | ".join(ARMS) + " |", "|---|" + "---:|" * len(ARMS)]
    for lvl, row in a["by_level"].items():
        lines.append(f"| {lvl} | " + " | ".join(_fmt(row[arm]) for arm in ARMS) + " |")
    lines += ["", "## Reconstruction by paper", "", "| Paper | Type | " + " | ".join(ARMS) + " |", "|---|---|" + "---:|" * len(ARMS)]
    for p, row in a["paper_matrix"].items():
        lines.append(f"| {p} | {TARGET_TYPES[p]} | " + " | ".join(_fmt(row[arm]) for arm in ARMS) + " |")
    lines += ["", "## Date effect (possible memorisation)", "", "| Method | 2024 cases | 2025–2026 cases | Spearman (date vs score) |", "|---|---:|---:|---:|"]
    for arm, row in a["date_effect"].items():
        lines.append(f"| {arm} | {_fmt(row['2024_cases'])} | {_fmt(row['2025_2026_cases'])} | {_fmt(row['spearman_date_vs_score'])} |")
    lines += ["", "## Evidence ceiling", "", "| Paper | Type | Reconstructibility (0–2) | Supportive records in oracle top-20 (any / strong) |", "|---|---|---:|---|"]
    for p, row in a["evidence_ceiling"].items():
        lines.append(f"| {p} | {TARGET_TYPES[p]} | {row['reconstructibility']} | {len(row['any'])} / {len(row['strong'])} |")
    lines += ["", "| Reconstructibility | Cases | " + " | ".join(ARMS) + " |", "|---|---:|" + "---:|" * len(ARMS)]
    for level_value, row in a["by_reconstructibility"].items():
        lines.append(f"| {level_value} | {len(row['cases'])} | " + " | ".join(_fmt(row[arm]) for arm in ARMS) + " |")
    lines += ["", "| Method | Read any supportive record | Read a strongly supportive record | Cited any supportive record | Reconstruction when read supportive | when not |",
              "|---|---:|---:|---:|---:|---:|"]
    for arm, row in a["evidence_access"].items():
        lines.append(f"| {arm} | {row['read_any_supportive']:.0%} | {row['read_strong_supportive']:.0%} | {row['cited_any_supportive']:.0%} | "
                     f"{_fmt(row['recon_when_read_supportive'])} | {_fmt(row['recon_when_not'])} |")
    lines += ["", "## Tool-agent process", "", "| Measure | " + " | ".join(a["tool_process"]) + " |", "|---|" + "---:|" * len(a["tool_process"])]
    keys = [k for k in next(iter(a["tool_process"].values())) if k != "runs"]
    for k in keys:
        lines.append(f"| {k} | " + " | ".join(_fmt(a["tool_process"][arm].get(k)) for arm in a["tool_process"]) + " |")
    for k in ("recon_when_kg_cited", "recon_when_kg_not_cited", "runs_citing_kg"):
        if k in a["tool_process"].get("tool_agent_kg", {}):
            lines.append(f"| {k} | " + " | ".join(_fmt(a["tool_process"][arm].get(k)) for arm in a["tool_process"]) + " |")
    n = a["noise"]
    lines += ["", "## Run-to-run noise (tool_agent vs fresh resample, same units)", "",
              f"Units {n['units']}; mean difference {n['mean_difference']:+.3f}; SD of unit differences {n['sd_of_unit_differences']}; "
              f"mean absolute difference {n['mean_absolute_difference']}; units changing by ≥1 point {n['units_changing_by_1_or_more']}; "
              f"classification changed {n['classification_changed']}.",
              "", "## Pairwise position bias", ""]
    for name, row in a["position_bias"].items():
        lines.append(f"- {name}: {row['position_inconsistent']} of {row['pairs']} pairs flip with presentation order ({row['rate']:.0%}).")
    lines += ["", "## Revision arms vs original (same units)", "",
              "resample is a fresh tool_agent sample with no revision, so its rows show how much change regression to "
              "the mean alone produces.", "",
              "| Measure | critique | self_revise | resample |", "|---|---:|---:|---:|"]
    detail = a["revision_detail"]
    keys = list(dict.fromkeys([*detail["critique"], *detail["self_revise"], *detail["resample"]]))
    for k in keys:
        lines.append(f"| {k} | {_fmt(detail['critique'].get(k))} | {_fmt(detail['self_revise'].get(k))} | "
                     f"{_fmt(detail['resample'].get(k))} |")
    s = a["stratified"]
    lines += ["", "## Confound checks (within query level)", "",
              "Tool arms pooled (tool_agent, resample, tool_agent_kg). 'Read supportive' means the run read at least one "
              "oracle record rated as supporting the target's intervention or mechanism.", "",
              "| Level | Read-supportive rate | n read | Reconstruction (read) | n not | Reconstruction (not) |",
              "|---|---:|---:|---:|---:|---:|"]
    for lvl, row in s["evidence_access_by_level"].items():
        lines.append(f"| {lvl} | {row['read_supportive_rate']:.0%} | {row['n_read']} | {_fmt(row['recon_read'])} | "
                     f"{row['n_not']} | {_fmt(row['recon_not'])} |")
    lines += ["", f"Within-paper difference (read minus not), mean over papers with both groups: "
              f"{s['evidence_access_within_paper_mean']:+.2f}; per paper: "
              + ", ".join(f"{w['paper_id']} {w['difference']:+.2f} ({w['n_read']}/{w['n_not']})"
                          for w in s["evidence_access_within_paper"]) + ".",
              "", "| Level | Group | Units | Errors per unit | Intervention | Condition | Mechanism | Outcome |",
              "|---|---|---:|---:|---:|---:|---:|---:|"]
    for lvl, groups in s["anchoring_by_level"].items():
        for flag, g in groups.items():
            dm = g["dimension_mean"]
            lines.append(f"| {lvl} | {flag} | {g['units']} | {g['errors_per_unit']:.2f} | "
                         + " | ".join(_fmt(dm.get(d)) for d in PRIMARY_DIMENSIONS) + " |")
    lines += ["", "| Level | Reconstructibility 1 | Reconstructibility 2 |", "|---|---:|---:|"]
    for lvl, row in s["reconstructibility_by_level"].items():
        lines.append(f"| {lvl} | {_fmt(row['1'])} | {_fmt(row['2'])} |")
    lines += ["", "| Level | " + " | ".join(ERROR_CATEGORIES) + " |", "|---|" + "---:|" * len(ERROR_CATEGORIES)]
    for lvl, share in s["error_share_by_level"].items():
        lines.append(f"| {lvl} | " + " | ".join(f"{share[c]:.0%}" for c in ERROR_CATEGORIES) + " |")
    lines += ["", "| Paper | Type | " + " | ".join(ERROR_CATEGORIES) + " |", "|---|---|" + "---:|" * len(ERROR_CATEGORIES)]
    for p, share in s["error_share_by_paper"].items():
        lines.append(f"| {p} | {TARGET_TYPES[p]} | " + " | ".join(f"{share[c]:.0%}" for c in ERROR_CATEGORIES) + " |")
    lines += ["", "## Generation health", ""]
    for arm, row in a["generation_health"].items():
        lines.append(f"- {arm}: failed {row['failed'] or 'none'}; citation status {row['citation_status']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    ce = sub.add_parser("code-errors")
    ce.add_argument("--workers", type=int, default=8)
    ce.add_argument("--resume", action="store_true")
    ev = sub.add_parser("evidence-ceiling")
    ev.add_argument("--workers", type=int, default=4)
    ev.add_argument("--resume", action="store_true")
    sub.add_parser("report")
    args = parser.parse_args()
    if args.command == "code-errors":
        result: Any = code_errors(load_units(), args.workers, args.resume)
    elif args.command == "evidence-ceiling":
        result = evidence_ceiling(args.resume, args.workers)
    else:
        a = report()
        result = {"coded_errors_total": a["coded_errors_total"], "units": sum(o["units"] for o in a["overview"].values())}
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
