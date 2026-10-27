"""Critique-augmented revision of tool-agent hypotheses, with leakage controls.

For every baseline tool-agent run (eval_v3), three critics review the hypothesis against the evidence the agent
read, and a reviser writes a revised hypothesis. A self-revise control runs the same reviser with no critiques,
so the effect of critique is separated from the effect of an extra revision pass. Revised hypotheses are judged
by the same blinded GPT-5.6 judge as the baseline. A fresh baseline sample measures run-to-run noise.

Leakage controls
- Critic and reviser payloads contain only the query, the knowledge cutoff, the hypothesis, and evidence the
  agent read. The held-out hidden target is never sent (checked in code on every call and in tests).
- Every critic and reviser model has a documented training cutoff before the earliest held-out paper date,
  checked at run time, so none of them can have learned the held-out papers during training.
- No record from the held-out paper or its work family may appear in any payload (checked on every call).
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from hypothesis_evidence_v2 import atomic_json, load_evidence
from llm_client import LLMError, trapi_chat_json
from temporal_eval_v3 import (
    CASES_DIR,
    RUN_ROOT,
    ALL_DIMENSIONS,
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    CITED_TEXT_CHARS,
    EXPERIMENT_DIR,
    HYPOTHESIS_FIELDS,
    PRIMARY_DIMENSIONS,
    QUERY_LEVELS,
    SCHEMA_VERSION,
    build_corpus,
    cluster_bootstrap,
    exact_sign_test,
    generate_all,
    holm_adjust,
    judge_absolute,
    judge_all,
    load_cases,
    mean,
)
from temporal_hypothesis_benchmark import _date_map, _read_json, _validate_generation

METADATA = EXPERIMENT_DIR / "temporal_v2" / "temporal_metadata.json"
V2_DIR = EXPERIMENT_DIR / "temporal_v2" / "materials_evidence_v2"
PAPER_MAPS = EXPERIMENT_DIR / "section_aware" / "paper_maps"
BASE_DIR = RUN_ROOT / "eval_v3"
OUT_DIR = RUN_ROOT / "eval_critique"

CRITIC_SCHEMA = "temporal-eval-critique-1.0"
CRITIC_MAX_TOKENS = 3000
REVISION_MAX_TOKENS = 8000
CRITIC_MAX_FINDINGS = 8
EVIDENCE_TEXT_CHARS = 3000
FINDING_TYPES = {"unsupported", "miscited", "inconsistent", "implausible", "untestable", "other"}
CRITIC_PAYLOAD_KEYS = {"query", "knowledge_cutoff", "hypothesis", "evidence"}
REVISER_PAYLOAD_KEYS = {"query", "knowledge_cutoff", "hypothesis", "evidence", "critiques", "review_mode",
                        "validation_error"}
ARMS = ("critique", "self_revise")

# Knowledge cutoffs were checked against the official model pages on 2026-10-22 (see the eval README).
# Candidates whose cutoff falls after 2023-12-31 were excluded: gpt-oss-120b (June 2024), Mistral Large 3
# (October 2024) and DeepSeek-V3.2 (May 2025). Each critic and reviser must predate the earliest held-out paper.
CRITICS = (
    {"role": "evidence", "deployment": "Llama-3.3-70B-Instruct_5", "token_field": "max_tokens",
     "temperature": 0.0, "max_tokens": 6000, "model": "Meta Llama 3.3 70B Instruct", "knowledge_cutoff": "2023-12-31",
     "cutoff_source": "Meta model card, knowledge cutoff December 2023 "
                      "(github.com/meta-llama/llama-models/blob/main/models/llama3_3/MODEL_CARD.md)"},
    {"role": "consistency", "deployment": "o1_2024-12-17", "token_field": "max_completion_tokens",
     "temperature": None, "max_tokens": 12000, "model": "OpenAI o1", "knowledge_cutoff": "2023-10-01",
     "cutoff_source": "OpenAI model page, Oct 01, 2023 knowledge cutoff (developers.openai.com/api/docs/models/o1)"},
    {"role": "falsifiability", "deployment": "gpt-4o_2024-11-20", "token_field": "max_completion_tokens",
     "temperature": 0.0, "model": "OpenAI GPT-4o", "knowledge_cutoff": "2023-10-01",
     "cutoff_source": "OpenAI model page, Oct 01, 2023 knowledge cutoff "
                      "(developers.openai.com/api/docs/models/gpt-4o)"},
)
REVISER = {"deployment": "Llama-3.3-70B-Instruct_5", "token_field": "max_tokens", "temperature": 0.0,
           "model": "Meta Llama 3.3 70B Instruct", "knowledge_cutoff": "2023-12-31",
           "cutoff_source": CRITICS[0]["cutoff_source"]}

ROLE_INSTRUCTIONS = {
    "evidence": ("Check that each supporting claim is backed by the text of the record it cites, and that "
                 "conflicting or supporting labels say what the claim needs. Flag unsupported claims and miscited labels."),
    "consistency": ("Check arithmetic, composition and physical plausibility: the direction of property changes "
                    "when an element is added or replaced, phase stability, whether the mechanism fits the conditions, "
                    "and whether the baseline values are internally consistent. Flag inconsistencies."),
    "falsifiability": ("Check whether the falsification experiment is concrete and would really test the claim, "
                       "whether the predicted outcome has measurable thresholds, and whether the boundary and "
                       "uncertainty fields are specific. Flag untestable parts."),
}
CRITIC_SYSTEM = (
    "You review one materials-science hypothesis for a single role. The input has the query, the knowledge cutoff, "
    "the hypothesis (citations are labels such as E3) and the evidence records the author read, each with a label "
    "and text. Judge only against that evidence and general materials-science reasoning. Do not use knowledge of "
    "any specific paper. Return a JSON object: {\"findings\": [{\"claim\": str, \"issue_type\": one of "
    "unsupported|miscited|inconsistent|implausible|untestable|other, \"severity\": 1|2|3, \"evidence_ids\": [labels], "
    "\"explanation\": str, \"suggested_fix\": str}]}. Report at most 8 real problems. If the hypothesis is sound for "
    "your role, return an empty list. Your role: "
)
REVISER_SYSTEM = (
    "You revise a materials-science hypothesis. The input has the query, the knowledge cutoff, the current "
    "hypothesis (citations are record_ids), the evidence records the author read (record_id, label, text), and "
    "critiques. When review_mode is 'critique', fix the problems the critiques identify when they are correct, and "
    "ignore critiques that are wrong. When review_mode is 'self', first check the hypothesis yourself for unsupported "
    "claims, inconsistencies and untestable parts, then revise it. Keep the same fields. Cite only record_ids that "
    "appear in the evidence list. If the evidence is insufficient, state the uncertainty instead of inventing support. "
    "Return a JSON object: {\"hypothesis\": {<the same fields as the input hypothesis>}}."
)


def check_model_cutoffs(first_held_out_date: str) -> None:
    for model in (*CRITICS, REVISER):
        if not model["knowledge_cutoff"] < first_held_out_date:
            raise ValueError(
                f"{model['deployment']} knowledge cutoff {model['knowledge_cutoff']} is not before the earliest "
                f"held-out paper date {first_held_out_date}")


def assert_payload(payload: dict[str, Any], allowed_keys: set[str]) -> None:
    extra = set(payload) - allowed_keys
    if extra:
        raise ValueError(f"payload contains unexpected keys: {sorted(extra)}")
    if "hidden_target" in json.dumps(payload, ensure_ascii=False):
        raise ValueError("hidden target must never be sent to critics or revisers")


def assert_no_target_records(record_ids: list[str], lookup: dict[str, Any], case: dict[str, Any],
                             metadata: dict[str, dict[str, Any]]) -> None:
    target_family = str(metadata[case["paper_id"]].get("work_family_id") or "")
    for record_id in record_ids:
        record = lookup.get(record_id)
        if record is None:
            raise ValueError(f"record {record_id} is not in the eligible corpus")
        if record.paper_id == case["paper_id"]:
            raise ValueError(f"target paper record {record_id} reached a critique payload")
        family = str(metadata.get(record.paper_id, {}).get("work_family_id") or "")
        if target_family and family == target_family:
            raise ValueError(f"same-family record {record_id} reached a critique payload")
        if (record.structured or {}).get("source") == "web":
            import websearch
            if any(websearch.audit_records([record], case["paper_id"]).values()):
                raise ValueError(f"web record {record_id} failed the web leakage audit")


def analyze_trace(run: dict[str, Any]) -> dict[str, Any]:
    trace = run["tool_trace"]
    searches = [step for step in trace if step.get("tool") == "search_corpus"]
    reads = [step["args"]["record_id"] for step in trace
             if step.get("tool") == "read_record" and isinstance(step.get("args"), dict)
             and "record_id" in step["args"]]
    submits = [step for step in trace if step.get("tool") == "submit_hypothesis"]
    search_keys = [json.dumps(step.get("args"), sort_keys=True) for step in searches]
    distinct_reads = set(reads)
    cited = set(run["cited_evidence_ids"])
    return {
        "tool_calls": run["tool_calls"],
        "searches": len(searches),
        "reads": len(reads),
        "distinct_records_read": len(distinct_reads),
        "repeated_searches": len(search_keys) - len(set(search_keys)),
        "submit_attempts": len(submits),
        "rejected_submissions": sum(1 for step in submits if step.get("accepted") is False),
        "refused_calls": sum(1 for step in trace if step.get("refused")),
        "cited_records": len(cited),
        "cited_but_unread": len(cited - distinct_reads),
        "read_but_uncited": len(distinct_reads - cited),
    }


def case_context(case: dict[str, Any], metadata: dict[str, dict[str, Any]], v2_units: list[Any],
                 paper_maps_dir: Path) -> dict[str, Any]:
    from temporal_eval_v3 import evidence_mode
    if evidence_mode() == "web":  # experiment 36: the records the web tool agent saw (its corpora and searches)
        import websearch
        lookup = websearch.WebLookup()
        for level, query in case["queries"].items():
            for record in websearch.case_records(case["paper_id"], level, "text_chunks", question=query["text"]):
                lookup[record.record_id] = record
        return {"lookup": lookup}
    _, chunk_records, unit_records = build_corpus(
        case["paper_id"], case["publication_date"], metadata, v2_units, paper_maps_dir)
    return {"lookup": {record.record_id: record for record in [*chunk_records, *unit_records]}}


def blind_for_critics(generation: dict[str, Any], accessed_ids: list[str], lookup: dict[str, Any]
                      ) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str]]:
    labels = {record_id: f"E{index + 1}" for index, record_id in enumerate(accessed_ids)}
    hypothesis = {key: value for key, value in generation.items() if key in HYPOTHESIS_FIELDS}
    for field in ("supporting_evidence_ids", "conflicting_evidence_ids"):
        hypothesis[field] = [labels[rid] for rid in hypothesis.get(field, []) if rid in labels]
    evidence = [{
        "evidence_id": labels[record_id],
        "publication_date": lookup[record_id].publication_date,
        "text": lookup[record_id].text[:EVIDENCE_TEXT_CHARS],
    } for record_id in accessed_ids if record_id in lookup]
    return hypothesis, evidence, labels


def validate_findings(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("findings"), list):
        raise ValueError("critic response must contain a findings list")
    findings = []
    for item in payload["findings"][:CRITIC_MAX_FINDINGS]:
        if not isinstance(item, dict):
            continue
        issue = str(item.get("issue_type", "other")).strip().lower()
        if issue not in FINDING_TYPES:
            issue = "other"
        try:
            severity = min(3, max(1, int(item.get("severity", 2))))
        except (TypeError, ValueError):
            severity = 2
        findings.append({
            "claim": str(item.get("claim", ""))[:400],
            "issue_type": issue,
            "severity": severity,
            "evidence_labels": [str(label) for label in item.get("evidence_ids", []) if str(label).startswith("E")][:6],
            "explanation": str(item.get("explanation", ""))[:800],
            "suggested_fix": str(item.get("suggested_fix", ""))[:800],
        })
    return findings


def run_critic(model: dict[str, Any], query: str, cutoff: str, hypothesis: dict[str, Any],
               evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payload = {"query": query, "knowledge_cutoff": cutoff, "hypothesis": hypothesis, "evidence": evidence}
    assert_payload(payload, CRITIC_PAYLOAD_KEYS)
    raw = trapi_chat_json(
        model["deployment"], CRITIC_SYSTEM + ROLE_INSTRUCTIONS[model["role"]],
        json.dumps(payload, ensure_ascii=False), max_tokens=model.get("max_tokens", CRITIC_MAX_TOKENS),
        token_field=model["token_field"], temperature=model["temperature"], retries=4)
    return validate_findings(raw)


def run_reviser(query: str, cutoff: str, generation: dict[str, Any], accessed_ids: list[str],
                lookup: dict[str, Any], critiques: list[dict[str, Any]], review_mode: str
                ) -> dict[str, Any]:
    original = {key: generation.get(key) for key in HYPOTHESIS_FIELDS}
    evidence = [{
        "record_id": record_id,
        "label": f"E{index + 1}",
        "publication_date": lookup[record_id].publication_date,
        "text": lookup[record_id].text[:EVIDENCE_TEXT_CHARS],
    } for index, record_id in enumerate(accessed_ids) if record_id in lookup]
    payload: dict[str, Any] = {"query": query, "knowledge_cutoff": cutoff, "hypothesis": original,
                               "evidence": evidence, "critiques": critiques, "review_mode": review_mode}
    allowed = set(accessed_ids)
    last_error = ""
    for attempt in range(2):
        assert_payload(payload, REVISER_PAYLOAD_KEYS)
        raw = trapi_chat_json(
            REVISER["deployment"], REVISER_SYSTEM, json.dumps(payload, ensure_ascii=False),
            max_tokens=REVISION_MAX_TOKENS, token_field=REVISER["token_field"],
            temperature=REVISER["temperature"], retries=4)
        candidate = raw.get("hypothesis") if isinstance(raw, dict) else None
        if isinstance(candidate, dict):
            merged = {field: candidate.get(field, original[field]) for field in HYPOTHESIS_FIELDS}
            try:
                validated = _validate_generation(merged, allowed)
            except ValueError as error:
                last_error = str(error)
            else:
                validated["citation_validation"] = {
                    "status": "valid" if attempt == 0 else "valid_after_repair", "removed_unknown_ids": []}
                return {"status": "revised" if attempt == 0 else "revised_after_repair",
                        "generation": {key: validated.get(key) for key in (*HYPOTHESIS_FIELDS, "citation_validation")},
                        "error": ""}
        else:
            last_error = "response has no hypothesis object"
        payload = {**payload, "validation_error": last_error}
    return {"status": "fallback_original", "generation": {**original, "citation_validation": {
        "status": "fallback_original", "removed_unknown_ids": []}}, "error": last_error}


def revise_run(base: dict[str, Any], arm: str, case: dict[str, Any], context: dict[str, Any],
               metadata: dict[str, dict[str, Any]]) -> dict[str, Any]:
    run_id = base["run_id"]
    accessed = sorted(base["accessed_record_ids"])
    lookup = context["lookup"]
    assert_no_target_records(accessed, lookup, case, metadata)
    hypothesis, evidence, labels = blind_for_critics(base["generation"], accessed, lookup)
    inverse = {label: record_id for record_id, label in labels.items()}
    record: dict[str, Any] = {
        "schema_version": CRITIC_SCHEMA, "run_id": run_id, "arm": arm, "paper_id": base["paper_id"],
        "query_level": base["query_level"], "query": base["query"], "publication_date": base["publication_date"],
        "trace_analysis": analyze_trace(base),
        "payload_audit": {"hidden_target_sent": False, "target_family_records": 0,
                          "evidence_records_sent": len(evidence)},
        "original_cited_evidence_ids": base["cited_evidence_ids"],
    }
    critiques: list[dict[str, Any]] = []
    if arm == "critique":
        critic_results = []
        for model in CRITICS:
            try:
                findings = run_critic(model, base["query"], base["publication_date"], hypothesis, evidence)
                critic_results.append({"role": model["role"], "deployment": model["deployment"],
                                       "status": "ok", "findings": findings, "error": ""})
                for finding in findings:
                    critiques.append({
                        "role": model["role"], "issue_type": finding["issue_type"],
                        "severity": finding["severity"], "claim": finding["claim"],
                        "explanation": finding["explanation"], "suggested_fix": finding["suggested_fix"],
                        "evidence_record_ids": [inverse[label] for label in finding["evidence_labels"]
                                                if label in inverse],
                    })
            except LLMError as error:
                critic_results.append({"role": model["role"], "deployment": model["deployment"],
                                       "status": "error", "findings": [], "error": str(error)[:300]})
        record["critics"] = critic_results
        if any(result["status"] != "ok" for result in critic_results):
            record["status"] = "critic_incomplete"
            return record
    try:
        revised = run_reviser(base["query"], base["publication_date"], base["generation"], accessed,
                              lookup, critiques, "critique" if arm == "critique" else "self")
    except LLMError as error:
        record["status"] = "reviser_error"
        record["reviser_error"] = str(error)[:300]
        return record
    record["reviser"] = {"deployment": REVISER["deployment"], "status": revised["status"],
                         "error": revised["error"]}
    record["status"] = "fallback_original" if revised["status"] == "fallback_original" else "ok"
    record["revised_generation"] = revised["generation"]
    revised_ids = sorted(set(revised["generation"]["supporting_evidence_ids"]
                             + revised["generation"]["conflicting_evidence_ids"]))
    record["revised_cited_evidence_ids"] = revised_ids
    record["invalid_revised_citations"] = len(set(revised_ids) - set(accessed))
    record["cited_evidence"] = [{
        "record_id": rid, "paper_id": lookup[rid].paper_id, "publication_date": lookup[rid].publication_date,
        "kind": lookup[rid].kind, "text": lookup[rid].text[:CITED_TEXT_CHARS],
    } for rid in revised_ids if rid in lookup]
    return record


def revision_path(out: Path, arm: str, run_id: str) -> Path:
    return out / "revisions" / arm / f"{run_id}.json"


def revise_all(*, out: Path, metadata_path: Path, v2_dir: Path, paper_maps_dir: Path, workers: int,
               resume: bool, case_ids: list[str] | None, arms: tuple[str, ...]) -> dict[str, int]:
    metadata = _date_map(metadata_path)
    v2_units = load_evidence(v2_dir)
    cases = {case["paper_id"]: case for case in load_cases(CASES_DIR, case_ids)}
    check_model_cutoffs(min(case["publication_date"] for case in cases.values()))
    contexts = {pid: case_context(case, metadata, v2_units, paper_maps_dir) for pid, case in cases.items()}
    bases = [_read_json(path) for path in sorted((BASE_DIR / "runs").glob("PMC*__tool_agent.json"))
             if _read_json(path)["paper_id"] in cases]
    # A failed base run has no hypothesis to revise; it stays recorded as failed in eval_v3 and is not revised.
    bases = [base for base in bases if base.get("status") == "ok" and base.get("generation")]
    jobs = []
    for base in bases:
        for arm in arms:
            target = revision_path(out, arm, base["run_id"])
            if resume and target.exists() and _read_json(target).get("status") in ("ok", "fallback_original"):
                continue
            jobs.append((base, arm))

    def job(base: dict[str, Any], arm: str) -> str:
        case = cases[base["paper_id"]]
        record = revise_run(base, arm, case, contexts[base["paper_id"]], metadata)
        atomic_json(revision_path(out, arm, base["run_id"]), record)
        return record["status"]

    counts: dict[str, int] = defaultdict(int)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(job, base, arm) for base, arm in jobs]
        for future in as_completed(futures):
            counts[future.result()] += 1
    return {"jobs": len(jobs), **dict(counts)}


def judge_revisions(*, out: Path, workers: int, resume: bool, arms: tuple[str, ...]) -> dict[str, int]:
    cases = {case["paper_id"]: case for case in load_cases(CASES_DIR, None)}
    counts: dict[str, int] = defaultdict(int)
    jobs = []
    for arm in arms:
        for path in sorted((out / "revisions" / arm).glob("PMC*.json")):
            record = _read_json(path)
            if record.get("status") not in ("ok", "fallback_original"):
                continue
            target = out / "judgments" / arm / path.name
            if resume and target.exists():
                continue
            jobs.append((arm, record))

    def job(arm: str, record: dict[str, Any]) -> None:
        run_like = {"run_id": f"{record['run_id']}__{arm}", "query": record["query"],
                    "generation": record["revised_generation"], "cited_evidence": record["cited_evidence"]}
        judgment = judge_absolute(run_like, cases[record["paper_id"]])
        judgment["arm"] = arm
        atomic_json(out / "judgments" / arm / f"{record['run_id']}.json", judgment)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(job, arm, record): (arm, record) for arm, record in jobs}
        for future in as_completed(futures):
            future.result()
            counts[futures[future][0]] += 1
    return dict(counts)


def _unit_scores(judgment_dir: Path, setting: str) -> dict[tuple[str, str], dict[str, Any]]:
    scores: dict[tuple[str, str], dict[str, Any]] = {}
    if not judgment_dir.exists():
        return scores
    for path in sorted(judgment_dir.glob("*.json")):
        if not path.stem.endswith(f"__{setting}"):
            continue
        judgment = _read_json(path)
        paper_id, level, _ = path.stem.split("__")
        values = judgment["scores"]
        scores[(paper_id, level)] = {
            "reconstruction": mean([values[dim] for dim in PRIMARY_DIMENSIONS]),
            "overall": mean([values[dim] for dim in ALL_DIMENSIONS]),
            "classification": judgment["classification"],
        }
    return scores


def _paired(a: dict[tuple[str, str], dict[str, Any]], b: dict[tuple[str, str], dict[str, Any]],
            name_a: str, name_b: str, role: str) -> dict[str, Any]:
    common = sorted(set(a) & set(b))
    per_paper: dict[str, list[float]] = defaultdict(list)
    for key in common:
        per_paper[key[0]].append(a[key]["reconstruction"] - b[key]["reconstruction"])
    paper_diffs = [mean(values) for values in per_paper.values()]
    point, low, high = cluster_bootstrap(per_paper) if per_paper else (float("nan"),) * 3
    p_value, positive, negative = exact_sign_test(paper_diffs) if paper_diffs else (1.0, 0, 0)
    return {"a": name_a, "b": name_b, "role": role, "units": len(common), "papers": len(per_paper),
            "mean_difference": round(point, 4), "ci95_cluster_bootstrap": [round(low, 4), round(high, 4)],
            "papers_a_higher": positive, "papers_b_higher": negative, "sign_test_p_two_sided": round(p_value, 4)}


def analyze_critique(*, out: Path) -> dict[str, Any]:
    arms = {
        "original": _unit_scores(BASE_DIR / "judgments" / "absolute", "tool_agent"),
        "resample": _unit_scores(out / "baseline_resample" / "judgments" / "absolute", "tool_agent"),
        "critique": _unit_scores(out / "judgments" / "critique", "tool_agent"),
        "self_revise": _unit_scores(out / "judgments" / "self_revise", "tool_agent"),
    }
    expected_units = len(QUERY_LEVELS) * len(load_cases(CASES_DIR, None))
    by_arm: dict[str, Any] = {}
    for name, scores in arms.items():
        values = list(scores.values())
        classes: dict[str, int] = defaultdict(int)
        for value in values:
            classes[value["classification"]] += 1
        by_arm[name] = {
            "units_judged": len(values), "units_expected": expected_units,
            "reconstruction_mean": round(mean([v["reconstruction"] for v in values]), 4),
            "overall_mean": round(mean([v["overall"] for v in values]), 4),
            "classifications": dict(classes),
        }

    primary = [
        _paired(arms["critique"], arms["original"], "critique", "original", "primary"),
        _paired(arms["self_revise"], arms["original"], "self_revise", "original", "primary"),
        _paired(arms["critique"], arms["self_revise"], "critique", "self_revise", "primary"),
    ]
    for item, adjusted in zip(primary, holm_adjust([item["sign_test_p_two_sided"] for item in primary])):
        item["holm_adjusted_p"] = round(adjusted, 4)
    noise = _paired(arms["resample"], arms["original"], "resample", "original", "noise")

    revisions = {arm: [_read_json(p) for p in sorted((out / "revisions" / arm).glob("PMC*.json"))] for arm in ARMS}
    revision_summary: dict[str, Any] = {}
    for arm, records in revisions.items():
        statuses: dict[str, int] = defaultdict(int)
        findings: dict[str, int] = defaultdict(int)
        for record in records:
            statuses[record.get("status", "missing")] += 1
            for critic in record.get("critics", []):
                for finding in critic.get("findings", []):
                    findings[finding["issue_type"]] += 1
        changed_citations = sum(
            1 for record in records if record.get("status") == "ok"
            and set(record["revised_cited_evidence_ids"]) != set(record["original_cited_evidence_ids"]))
        revision_summary[arm] = {
            "records": len(records), "statuses": dict(statuses),
            "findings_by_type": dict(findings),
            "citation_set_changed": changed_citations,
            "invalid_revised_citations": sum(record.get("invalid_revised_citations", 0) for record in records),
            "payload_hidden_target_sent": sum(1 for record in records
                                              if record.get("payload_audit", {}).get("hidden_target_sent")),
            "payload_target_family_records": sum(record.get("payload_audit", {}).get("target_family_records", 0)
                                                 for record in records),
        }

    judge_errors = len(list((out / "judgments" / "errors").glob("*.json"))) if (out / "judgments" / "errors").exists() else 0
    integrity = {
        "schema_version": SCHEMA_VERSION,
        "expected_units_per_arm": expected_units,
        "judged_per_arm": {name: len(scores) for name, scores in arms.items()},
        "judge_errors": judge_errors,
        "critic_incomplete": sum(1 for records in revisions.values() for r in records
                                 if r.get("status") == "critic_incomplete"),
        "invalid_revised_citations": sum(s["invalid_revised_citations"] for s in revision_summary.values()),
        "payload_hidden_target_sent": sum(s["payload_hidden_target_sent"] for s in revision_summary.values()),
        "payload_target_family_records": sum(s["payload_target_family_records"] for s in revision_summary.values()),
        "model_cutoffs": {model["deployment"]: model["knowledge_cutoff"] for model in (*CRITICS, REVISER)},
    }
    integrity["verified"] = bool(
        all(count == expected_units for count in integrity["judged_per_arm"].values())
        and integrity["judge_errors"] == 0
        and integrity["critic_incomplete"] == 0
        and integrity["invalid_revised_citations"] == 0
        and integrity["payload_hidden_target_sent"] == 0
        and integrity["payload_target_family_records"] == 0
    )
    analysis = {
        "schema_version": SCHEMA_VERSION,
        "bootstrap": {"resamples": BOOTSTRAP_RESAMPLES, "seed": BOOTSTRAP_SEED},
        "by_arm": by_arm, "primary_comparisons": primary, "noise_comparison": noise,
        "revisions": revision_summary, "integrity": integrity,
    }
    results = out / "results"
    results.mkdir(parents=True, exist_ok=True)
    atomic_json(results / "analysis_critique.json", analysis)
    atomic_json(results / "integrity_critique.json", integrity)
    (results / "summary_critique.md").write_text(render_summary(analysis))
    return analysis


def render_summary(analysis: dict[str, Any]) -> str:
    integrity = analysis["integrity"]
    lines = [
        f"Integrity verified: {integrity['verified']}. Judged per arm: {integrity['judged_per_arm']} "
        f"(expected {integrity['expected_units_per_arm']}); judge errors {integrity['judge_errors']}; "
        f"critic-incomplete {integrity['critic_incomplete']}; invalid revised citations "
        f"{integrity['invalid_revised_citations']}; hidden target sent {integrity['payload_hidden_target_sent']}; "
        f"target-family records in payloads {integrity['payload_target_family_records']}.",
        "",
        "| Arm | Units judged | Reconstruction (0-4) | Overall (0-4) |",
        "|---|---:|---:|---:|",
    ]
    for name, row in analysis["by_arm"].items():
        lines.append(f"| {name} | {row['units_judged']}/{row['units_expected']} | "
                     f"{row['reconstruction_mean']:.2f} | {row['overall_mean']:.2f} |")
    lines += ["", "| A | B | Role | Units | Mean difference (A-B) | 95% CI (papers bootstrap) | Papers A higher / B higher | Sign-test p | Holm p |",
              "|---|---|---|---:|---:|---|---:|---:|---:|"]
    for item in [*analysis["primary_comparisons"], analysis["noise_comparison"]]:
        low, high = item["ci95_cluster_bootstrap"]
        holm = f"{item['holm_adjusted_p']:.3f}" if "holm_adjusted_p" in item else "n/a (noise)"
        lines.append(f"| {item['a']} | {item['b']} | {item['role']} | {item['units']} | "
                     f"{item['mean_difference']:+.3f} | [{low:+.3f}, {high:+.3f}] | "
                     f"{item['papers_a_higher']} / {item['papers_b_higher']} | "
                     f"{item['sign_test_p_two_sided']:.3f} | {holm} |")
    lines += ["", "| Arm | Records | Statuses | Findings by type | Citation set changed |", "|---|---:|---|---|---:|"]
    for name, row in analysis["revisions"].items():
        statuses = ", ".join(f"{k}: {v}" for k, v in row["statuses"].items())
        findings = ", ".join(f"{k}: {v}" for k, v in row["findings_by_type"].items()) or "none"
        lines.append(f"| {name} | {row['records']} | {statuses} | {findings} | {row['citation_set_changed']} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    rs = sub.add_parser("resample-generate")
    rs.add_argument("--workers", type=int, default=4)
    rs.add_argument("--resume", action="store_true")
    rj = sub.add_parser("resample-judge")
    rj.add_argument("--workers", type=int, default=4)
    rj.add_argument("--resume", action="store_true")
    rev = sub.add_parser("revise")
    rev.add_argument("--workers", type=int, default=4)
    rev.add_argument("--resume", action="store_true")
    rev.add_argument("--case", action="append")
    rev.add_argument("--arm", action="append", choices=ARMS)
    jud = sub.add_parser("judge")
    jud.add_argument("--workers", type=int, default=4)
    jud.add_argument("--resume", action="store_true")
    jud.add_argument("--arm", action="append", choices=ARMS)
    sub.add_parser("analyze")
    args = parser.parse_args()
    if args.command == "resample-generate":
        result: Any = generate_all(
            cases_dir=CASES_DIR, metadata_path=METADATA, v2_dir=V2_DIR, paper_maps_dir=PAPER_MAPS,
            output_dir=OUT_DIR / "baseline_resample", settings=("tool_agent",), levels=QUERY_LEVELS,
            case_ids=None, workers=args.workers, resume=args.resume)
    elif args.command == "resample-judge":
        result = judge_all(cases_dir=CASES_DIR, output_dir=OUT_DIR / "baseline_resample", workers=args.workers,
                           resume=args.resume, pairs=())
    elif args.command == "revise":
        result = revise_all(out=OUT_DIR, metadata_path=METADATA, v2_dir=V2_DIR, paper_maps_dir=PAPER_MAPS,
                            workers=args.workers, resume=args.resume, case_ids=args.case,
                            arms=tuple(args.arm or ARMS))
    elif args.command == "judge":
        result = judge_revisions(out=OUT_DIR, workers=args.workers, resume=args.resume,
                                 arms=tuple(args.arm or ARMS))
    else:
        result = analyze_critique(out=OUT_DIR)["integrity"]
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
