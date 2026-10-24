"""Leak-free benchmark queries (benchmark v3), built the way leakage-safe benchmarks do it.

Why: the experiment-3 builder wrote queries in the same Qwen call that saw the held-out paper's results, and
47% of the answer's content words ended up in expert queries (experiment 19). The published benchmarks keep the
answer out by construction (MOOSE-Chem, ResearchBench, IdeaBench, SCIMON; see RELATED_WORK.md).

Rules implemented here:
1. Source = the held-out paper's Introduction only. Title, abstract, methods, results and conclusions are never
   shown. Sentences that announce this paper's own work ("in this work", "herein", "here we", "we propose ...")
   and everything after the first such sentence are removed (the end of an introduction states the approach).
2. The writer never sees the hidden target. It follows MOOSE-Chem's rule: the background may describe what was
   already tried for this problem, but must not contain the method, material change, structure or mechanism of
   the answer, and the question must not point in the direction of the solution.
3. A separate checker sees the query and the hidden target and reports every phrase that reveals the target's
   intervention (including its class), structural mediator, mechanism or quantified outcome.
4. A lexical gate: content words shared by the query and the target's intervention/mediator/mechanism, after
   removing words that describe the starting material, conditions and baseline (those may be stated).
5. Failed queries are rewritten with the offending phrases (never the target) up to MAX_ROUNDS times. A level
   that still fails is recorded as failed, not silently kept.
The hidden target is copied unchanged from the experiment-3 case, so old and new results share one answer key.
"""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import llm_client as lc
from hypothesis_evidence_v2 import atomic_json
from temporal_eval_v3 import EXPERIMENT_DIR, QUERY_LEVELS
from temporal_hypothesis_benchmark import _read_json

OLD_CASES = EXPERIMENT_DIR / "temporal_v2" / "benchmark_cases"
PAPERS = EXPERIMENT_DIR / "outputs" / "papers"
OUT = EXPERIMENT_DIR / "benchmark_v3"
CASES_OUT = OUT / "cases"
WRITER = "gpt-5.6-sol_2026-07-09"
CHECKER = "gpt-5.6-sol_2026-07-09"
MAX_ROUNDS = 4
MAX_OVERLAP = 0.10
ANSWER_FIELDS = ("intervention", "structural_mediator", "mechanism")
ALLOWED_FIELDS = ("material_initial_state", "conditions", "baseline")
SELF_REFERENCE = re.compile(
    r"\b(in (the )?(present|this|current) (work|study|paper|article|research|investigation|manuscript)|herein|"
    r"this (study|work|paper|article|research) (aimed|was|used|uses|employ|investigat|analy[sz]|examin|"
    r"explor|stud|focus|report|present|propos|demonstrat|develop)|the aim (of this|was)|"
    r"here,? we|this (work|study|paper|article) (aims|reports|presents|proposes|demonstrates|investigates|"
    r"explores|focuses|introduces|develops)|we (have )?(propose|report|present|demonstrate|show|develop|introduce|"
    r"investigate|design|fabricat|prepar|employ|add|systematically|stud|explor|examin|synthesi[sz]|produc|"
    r"successfully|achiev|reveal|use|utili[sz]|appl|select|chose|choose|focus|aim|attempt|perform|conduct|"
    r"combin|exploit|adopt|tailor|engineer))", re.IGNORECASE)
STOP = set("""the and for with from that this into within between than their which while where when what given
propose specify expected must aim using use via based under over also such both each more less can could would should
may might will its not are was were been has have how does one two new study effect role case experiment intervention
regime trade off compared baseline approach mechanism hypothesis""".split())

LEVEL_RULES = {
    "broad": "State only the material family or application and the property goal. Do not name a specific "
             "starting composition.",
    "problem_constrained": "Add the specific starting material and its state, the failure or limitation to "
                           "overcome, and the operating or test regime.",
    "expert_context": "Add a short background survey from the introduction: what earlier work tried for this problem "
                      "and why it fell short, and any stated design constraints.",
}
WRITER_SYSTEM = (
    "You write evaluation questions for a materials-science hypothesis-generation benchmark. You receive the "
    "introduction of a research paper with the paper's own contribution removed. Write three research questions "
    "for a scientist who has not read the paper, at three levels of context: broad, problem_constrained and "
    "expert_context. Each level adds context to the previous one.\n"
    "Rules (from the MOOSE-Chem benchmark guideline):\n"
    "- Use only information in the supplied introduction text. Do not add anything you may know about this or "
    "any other paper.\n"
    "- The question and background must not contain any information or method that could be the paper's answer: "
    "no proposed material change, added element, processing route, treatment, microstructure, phase, defect "
    "structure, mechanism or predicted value. Methods that the introduction describes as earlier work on this "
    "problem may be mentioned as background, with their limitations.\n"
    "- The question must stay general about the solution: ask what intervention could solve the problem, never "
    "hint at its direction or class (for example do not say 'via alloying', 'by heat treatment', 'by introducing "
    "a second phase').\n"
    "- Each question asks for one hypothesis with: the proposed intervention, the mechanism, the predicted outcome "
    "relative to a baseline, its boundary conditions, supporting prior evidence and a falsification experiment.\n"
    "Level rules: " + " ".join(f"{k}: {v}" for k, v in LEVEL_RULES.items()) + "\n"
    "If revision_requests are supplied, rewrite the listed levels so that none of the listed phrases or ideas "
    "remains, in any wording; keep the other levels unchanged.\n"
    "Return JSON {\"broad\": str, \"problem_constrained\": str, \"expert_context\": str}."
)
CHECKER_SYSTEM = (
    "You audit a benchmark question for answer leakage. The input has the question and the hidden answer (the "
    "paper's intervention, structural mediator, mechanism and outcome). Stating the starting material, its "
    "problem, the property goal, the test conditions and earlier work that the answer does not use is allowed. "
    "Report every phrase in the question that reveals or points to: the intervention or its class (for example "
    "'alloying addition', 'thermomechanical treatment', 'second phase'), the structural mediator, the mechanism, or "
    "a quantified outcome of the answer. Also judge whether a materials scientist reading only the question would "
    "be steered toward the answer's intervention class. Return JSON {\"leaks\": [{\"phrase\": exact text from the "
    "question, \"reveals\": one of intervention|structural_mediator|mechanism|outcome, \"why\": str}], "
    "\"steers_to_answer\": true|false}."
)


# ---------------------------------------------------------------- source text

def _text(element: ET.Element) -> str:
    return re.sub(r"\s+", " ", "".join(element.itertext())).strip()


def _strip_citations(text: str) -> str:
    text = re.sub(r"\[\s*[\d,\s–-]+\]", "", text)
    return re.sub(r"\s+([,.;])", r"\1", re.sub(r"\s{2,}", " ", text))


def redacted_introduction(paper_id: str) -> dict[str, Any]:
    """Introduction paragraphs up to (not including) the first sentence that announces the paper's own work."""
    root = ET.parse(PAPERS / paper_id / "input" / "article.xml").getroot()
    sections = root.find(".//body").findall("sec")
    intro = next((s for s in sections if s.find("title") is not None
                  and "introduction" in _text(s.find("title")).lower()), sections[0])
    kept: list[str] = []
    removed: list[str] = []
    stopped = False
    for paragraph in intro.iter("p"):
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", _strip_citations(_text(paragraph)))
        keep = []
        for sentence in sentences:
            if stopped or SELF_REFERENCE.search(sentence):
                stopped = True
                removed.append(sentence)
            else:
                keep.append(sentence)
        if keep:
            kept.append(" ".join(keep))
    return {"text": "\n\n".join(kept), "kept_chars": sum(map(len, kept)),
            "removed_sentences": len(removed), "removed_preview": [r[:200] for r in removed[:3]]}


# ---------------------------------------------------------------- gates

def content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9][a-z0-9\-\.]*", str(text).lower()) if len(w) > 2 and w not in STOP}


def answer_overlap(query: str, target: dict[str, Any]) -> tuple[float, list[str]]:
    """Share of the answer's content words in the query, ignoring words that describe the allowed context."""
    allowed = content_words(" ".join(str(target.get(k, "")) for k in ALLOWED_FIELDS))
    answer = content_words(" ".join(str(target.get(k, "")) for k in ANSWER_FIELDS)) - allowed
    shared = sorted(answer & content_words(query))
    return (len(shared) / len(answer) if answer else 0.0), shared


def raw_overlap(query: str, target: dict[str, Any]) -> float:
    """Experiment-19 metric (no allowed-word removal), for comparison with the old queries."""
    answer = content_words(" ".join(str(target.get(k, "")) for k in ANSWER_FIELDS))
    return len(answer & content_words(query)) / len(answer) if answer else 0.0


def check(query: str, target: dict[str, Any]) -> dict[str, Any]:
    payload = {"question": query, "hidden_answer": {k: target.get(k) for k in (
        "intervention", "structural_mediator", "mechanism", "predicted_outcome")}}
    raw = lc.trapi_chat_json(CHECKER, CHECKER_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=6000)
    leaks = [l for l in (raw.get("leaks", []) if isinstance(raw, dict) else []) if isinstance(l, dict)
             and str(l.get("phrase", "")).strip()]
    overlap, shared = answer_overlap(query, target)
    passed = not leaks and not bool(raw.get("steers_to_answer")) and overlap <= MAX_OVERLAP
    return {"passed": passed, "leaks": leaks, "steers_to_answer": bool(raw.get("steers_to_answer")),
            "overlap": round(overlap, 3), "shared_words": shared}


def revision_requests(results: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    requests_: dict[str, list[str]] = {}
    for level, result in results.items():
        if result["passed"]:
            continue
        items = [f"{l['phrase']} (reveals the answer's {l.get('reveals', 'content')})" for l in result["leaks"]]
        if result["steers_to_answer"] and not items:
            items.append("the question as a whole points toward one specific kind of solution; make it neutral")
        if result["overlap"] > MAX_OVERLAP:
            items.append("avoid these words, which describe the solution rather than the problem: "
                         + ", ".join(result["shared_words"]))
        requests_[level] = items
    return requests_


# ---------------------------------------------------------------- build

def build_case(paper_id: str) -> dict[str, Any]:
    old = _read_json(OLD_CASES / f"{paper_id}.json")
    target = old["hidden_target"]
    source = redacted_introduction(paper_id)
    payload: dict[str, Any] = {"introduction_without_own_contribution": source["text"]}
    history = []
    queries: dict[str, str] = {}
    results: dict[str, dict[str, Any]] = {}
    for round_ in range(1, MAX_ROUNDS + 1):
        raw = lc.trapi_chat_json(WRITER, WRITER_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=6000)
        for level in QUERY_LEVELS:
            if level not in queries or not results.get(level, {}).get("passed"):
                text = str(raw.get(level, "")).strip() if isinstance(raw, dict) else ""
                if text:
                    queries[level] = text
        results = {level: check(queries[level], target) for level in QUERY_LEVELS if level in queries}
        history.append({"round": round_, "queries": dict(queries), "checks": results})
        if len(results) == len(QUERY_LEVELS) and all(r["passed"] for r in results.values()):
            break
        payload = {"introduction_without_own_contribution": source["text"], "current_questions": queries,
                   "revision_requests": revision_requests(results)}
    case = {
        "schema_version": "benchmark-v3-1.0", "paper_id": paper_id, "publication_date": old["publication_date"],
        "split": old["split"], "benchmark_claim": "retrospective_temporal_reconstruction",
        "query_source": "introduction_without_own_contribution", "query_writer": f"trapi:{WRITER}",
        "leakage_checker": f"trapi:{CHECKER}",
        "queries": {level: {"text": queries.get(level, ""), "passed_gate": results.get(level, {}).get("passed", False),
                            "overlap": results.get(level, {}).get("overlap"),
                            "raw_overlap_exp19_metric": round(raw_overlap(queries.get(level, ""), target), 3),
                            "source_role_refs": []} for level in QUERY_LEVELS},
        "hidden_target": target, "hidden_target_source": "copied from the experiment-3 case (unchanged answer key)",
        "rounds": len(history), "source": {k: v for k, v in source.items() if k != "text"},
        "old_queries": {level: old["queries"][level]["text"] for level in QUERY_LEVELS},
    }
    atomic_json(OUT / "build_log" / f"{paper_id}.json", {"paper_id": paper_id, "source_text": source["text"],
                                                          "history": history})
    atomic_json(CASES_OUT / f"{paper_id}.json", case)
    return case


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cases", nargs="*")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--show-source", action="store_true")
    args = parser.parse_args()
    ids = args.cases or sorted(p.stem for p in OLD_CASES.glob("PMC*.json"))
    if args.show_source:
        for pid in ids:
            src = redacted_introduction(pid)
            print(pid, src["kept_chars"], src["removed_sentences"], src["removed_preview"][:1])
        return
    for pid in ids:
        if args.resume and (CASES_OUT / f"{pid}.json").exists():
            continue
        case = build_case(pid)
        print(pid, case["rounds"], {l: (q["passed_gate"], q["overlap"]) for l, q in case["queries"].items()},
              flush=True)


if __name__ == "__main__":
    main()
