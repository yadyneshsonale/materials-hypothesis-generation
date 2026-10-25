"""Benchmark v3.1: fix the question-type construction error found in experiment 22.

Experiment 22 found that 4 of 12 hidden targets are studies (simulation or characterization) while every v3
question asks for "a single intervention" to improve a property, because the v3 writer was told to always ask for
an intervention. Those cases were unreachable by construction (no generated hypothesis was even in the right
class). must_obey.md 3.4 allows a new version for a construction error, applied to all cases by one written rule.

Rule (applied to all 12 cases, using only the redacted introduction, never the target or any result):
1. A gap classifier (GPT-5.6, sees only the introduction with the paper's own contribution removed) labels the
   research gap the introduction motivates:
   design        = a property or performance limitation to overcome;
   understanding = a behaviour, mechanism or stability question that is unknown or unclear;
   method        = a limitation of existing methods, models or tools for obtaining some quantity.
2. Cases labelled design keep their v3 queries unchanged (they were written for this gap type).
3. Cases labelled understanding or method get new queries from the v3 writer with a question template for that gap
   type; the v3 leakage checker, lexical gate and rewrite loop are applied unchanged.
Hidden targets stay unchanged (one answer key).
"""

from __future__ import annotations

import argparse
import json
from typing import Any

import llm_client as lc
import query_builder_v3 as v3
from hypothesis_evidence_v2 import atomic_json
from temporal_eval_v3 import EXPERIMENT_DIR, QUERY_LEVELS
from temporal_hypothesis_benchmark import _read_json

V3_CASES = EXPERIMENT_DIR / "benchmark_v3" / "cases"
OUT = EXPERIMENT_DIR / "benchmark_v3_1"
CASES_OUT = OUT / "cases"
GAP_TYPES = ("design", "understanding", "method")

GAP_SYSTEM = (
    "You read the introduction of a materials-science paper, with the paper's own contribution removed. Classify "
    "the research gap that the introduction motivates. design: a property or performance limitation of a material "
    "that needs to be overcome. understanding: a behaviour, mechanism, stability or structure-property question "
    "that the introduction says is unknown, unclear or insufficiently understood. method: a limitation of existing "
    "methods, models, simulations or measurement tools for obtaining some quantity. Use only the text. Return JSON "
    "{\"gap_type\": \"design\"|\"understanding\"|\"method\", \"evidence\": short quote from the text, \"reason\": str}."
)
GAP_TEMPLATES = {
    "understanding": (
        "The introduction motivates an UNDERSTANDING gap. Each question asks for one testable mechanistic "
        "hypothesis about the behaviour that is unclear: what governs it and why, the study or controlled change "
        "(the 'intervention') that would reveal it, the predicted observations relative to a baseline condition, "
        "boundary conditions, supporting prior evidence and a falsification test. Do not ask how to improve a "
        "property. Do not name or hint at the study method or technique (for example do not say 'simulate', "
        "'molecular dynamics', 'in situ microscopy'), the conditions that will be varied, or the mechanism."
    ),
    "method": (
        "The introduction motivates a METHOD gap. Each question asks for one testable hypothesis about a method or "
        "approach (the 'intervention') that would overcome the stated limitation of existing methods, why it would "
        "work (mechanism), the predicted improvement relative to existing methods, boundary conditions, supporting "
        "prior evidence and a decisive benchmark that would falsify it. Do not name or hint at the specific method, "
        "model class or algorithm that could solve it."
    ),
}


def classify_gap(paper_id: str) -> dict[str, Any]:
    source = v3.redacted_introduction(paper_id)
    raw = lc.trapi_chat_json(v3.WRITER, GAP_SYSTEM, json.dumps({"introduction": source["text"]}, ensure_ascii=False),
                             max_tokens=3000)
    gap = str(raw.get("gap_type", "")).strip().lower() if isinstance(raw, dict) else ""
    return {"gap_type": gap if gap in GAP_TYPES else "design",
            "evidence": str(raw.get("evidence", ""))[:400] if isinstance(raw, dict) else "",
            "reason": str(raw.get("reason", ""))[:600] if isinstance(raw, dict) else "", "classifier": v3.WRITER}


def build_case(paper_id: str) -> dict[str, Any]:
    old = _read_json(V3_CASES / f"{paper_id}.json")
    gap = classify_gap(paper_id)
    if gap["gap_type"] == "design":
        case = {**old, "schema_version": "benchmark-v3.1-1.0", "gap": gap,
                "v3_1_change": "none (design gap: v3 queries kept)"}
        atomic_json(CASES_OUT / f"{paper_id}.json", case)
        return case
    target = old["hidden_target"]
    source = v3.redacted_introduction(paper_id)
    system = v3.WRITER_SYSTEM.replace(
        "- The question must stay general about the solution: ask what intervention could solve the problem, never "
        "hint at its direction or class (for example do not say 'via alloying', 'by heat treatment', 'by introducing "
        "a second phase').\n"
        "- Each question asks for one hypothesis with: the proposed intervention, the mechanism, the predicted outcome "
        "relative to a baseline, its boundary conditions, supporting prior evidence and a falsification experiment.\n",
        "- " + GAP_TEMPLATES[gap["gap_type"]] + "\n")
    if system == v3.WRITER_SYSTEM:
        raise RuntimeError("v3 writer prompt changed; template substitution failed")
    payload: dict[str, Any] = {"introduction_without_own_contribution": source["text"]}
    history, queries, results = [], {}, {}
    for round_ in range(1, v3.MAX_ROUNDS + 1):
        raw = lc.trapi_chat_json(v3.WRITER, system, json.dumps(payload, ensure_ascii=False), max_tokens=6000)
        for level in QUERY_LEVELS:
            if level not in queries or not results.get(level, {}).get("passed"):
                text = str(raw.get(level, "")).strip() if isinstance(raw, dict) else ""
                if text:
                    queries[level] = text
        results = {level: v3.check(queries[level], target) for level in QUERY_LEVELS if level in queries}
        history.append({"round": round_, "queries": dict(queries), "checks": results})
        if len(results) == len(QUERY_LEVELS) and all(r["passed"] for r in results.values()):
            break
        payload = {"introduction_without_own_contribution": source["text"], "current_questions": queries,
                   "revision_requests": v3.revision_requests(results)}
    case = {**old, "schema_version": "benchmark-v3.1-1.0", "gap": gap,
            "v3_1_change": f"queries rewritten for a {gap['gap_type']} gap",
            "queries": {level: {"text": queries.get(level, ""), "passed_gate": results.get(level, {}).get("passed", False),
                                "overlap": results.get(level, {}).get("overlap"),
                                "raw_overlap_exp19_metric": round(v3.raw_overlap(queries.get(level, ""), target), 3),
                                "source_role_refs": []} for level in QUERY_LEVELS},
            "rounds": len(history), "v3_queries": {level: old["queries"][level]["text"] for level in QUERY_LEVELS}}
    atomic_json(OUT / "build_log" / f"{paper_id}.json", {"paper_id": paper_id, "gap": gap, "history": history})
    atomic_json(CASES_OUT / f"{paper_id}.json", case)
    return case


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cases", nargs="*")
    args = parser.parse_args()
    ids = args.cases or sorted(p.stem for p in V3_CASES.glob("PMC*.json"))
    for pid in ids:
        case = build_case(pid)
        print(pid, case["gap"]["gap_type"], case["v3_1_change"],
              {l: (q.get("passed_gate"), q.get("raw_overlap_exp19_metric")) for l, q in case["queries"].items()},
              flush=True)


if __name__ == "__main__":
    main()
