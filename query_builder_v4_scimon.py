"""Benchmark v4: SciMON-style user input (experiment 31; design pre-registered in loop.md section 14.1).

SciMON (Wang, Downey, Ji and Hope, ACL 2024, https://aclanthology.org/2024.acl-long.18.pdf) builds the model input from
the paper's abstract: the Background sentences (a scientific sentence classifier) form the context M, and a seed term
v is one entity of a [method, used-for, task] relation extracted from the remaining sentences, while the other entity
stays hidden. The prompt is "Consider the following context: M In that context, which p can be used for v, and why?".

Our variant, for all 36 case papers:
  1. o3-mini (pre-cutoff) labels the abstract sentences (Background / Objective / Method / Result / Other).
     M = the Background sentences, verbatim, minus any sentence that announces the paper's own work (v3 sensor).
  2. o3-mini extracts [head used-for tail] relations from the non-background sentences, ranked by salience. The seed v
     is the tail (task) entity; p is the head's type (method or material); the head stays hidden. Spans are verified
     verbatim, and the head may not occur in the seed.
  3. The composed input is checked by the v3 leakage checker and lexical gate. If it fails, the next relation is tried
     (up to 3); text is never rewritten. Cases with no Background sentence or failing all tries are flagged.
Hidden targets, splits and dates are copied unchanged. Output: benchmark_v4_scimon/{cases, build_log}.
"""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import hypo_loop as H
import llm_client as lc
import query_builder_v3 as v3
from hypothesis_evidence_v2 import atomic_json
from temporal_hypothesis_benchmark import _read_json

OUT = H.EXPERIMENT_DIR / "benchmark_v4_scimon"
CASES_OUT = OUT / "cases"
LEVEL = "scimon"
VERSION = "v4_scimon"
LABELLER = "o3-mini_2025-01-31"
MAX_TRIES = 3
LABELS = ("Background", "Objective", "Method", "Result", "Other")
TEMPLATE = "Consider the following context: {context} In that context, which {p} can be used for {seed}, and why?"
NO_CONTEXT_TEMPLATE = "Which {p} can be used for {seed}, and why?"
CLASSIFY_SYSTEM = (
    "You label each sentence of a scientific abstract with its rhetorical role, as in the CSAbstruct and PubMed RCT "
    "schemes. Background: context, prior work, the problem, motivation or gap. Objective: what this paper aims to do. "
    "Method: what this paper does (materials, processing, simulations, measurements). Result: what this paper finds or "
    "concludes. Other: anything else. Return JSON {\"labels\": [{\"index\": int, \"label\": \"Background\"|"
    "\"Objective\"|\"Method\"|\"Result\"|\"Other\"}]} with one entry per sentence."
)
RELATION_SYSTEM = (
    "You extract scientific relations of the form [head, used-for, tail] (the SciERC scheme) from sentences of a "
    "materials-science abstract. The head is a Method or a Material: what is used (a process, treatment, composition "
    "change, technique, simulation or modelling method, alloy, coating or other material). The tail is a Task: what it "
    "is used for (a goal, a problem, a property to improve, or a behaviour or quantity to understand or predict). Copy "
    "both entities as exact, contiguous spans from the sentences. The tail must not name or contain the head. Rank the "
    "relations by how central they are to the paper's main contribution, most central first, and return at most 5. "
    "Return JSON {\"relations\": [{\"head\": str, \"head_type\": \"Method\"|\"Material\", \"tail\": str}]}."
)


def _xml_path(pid: str) -> Path:
    for path in (H.EXPERIMENT_DIR / "outputs" / "papers" / pid / "input" / "article.xml",
                 H.EXPERIMENT_DIR / "benchmark_test2" / "papers" / pid / "input" / "article.xml",
                 H.EXPERIMENT_DIR / "benchmark_test3" / "papers" / pid / "input" / "article.xml"):
        if path.exists():
            return path
    raise FileNotFoundError(f"no article XML for {pid}")


def abstract_sentences(pid: str) -> list[str]:
    root = ET.parse(_xml_path(pid)).getroot()
    abstracts = root.findall(".//abstract")
    main = next((a for a in abstracts if not a.get("abstract-type")), abstracts[0] if abstracts else None)
    if main is None:
        return []
    paragraphs = [v3._strip_citations(v3._text(p)) for p in main.iter("p")] or [v3._strip_citations(v3._text(main))]
    sentences: list[str] = []
    for paragraph in paragraphs:
        sentences += [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z(\[])", paragraph) if s.strip()]
    return sentences


def _norm(text: str) -> str:
    return " ".join(str(text).casefold().split())


def _o3(system: str, payload: dict[str, Any]) -> Any:
    return lc.trapi_chat_json(LABELLER, system, json.dumps(payload, ensure_ascii=False), max_tokens=12000,
                              token_field="max_completion_tokens", temperature=None, retries=12)


def classify(sentences: list[str]) -> list[str]:
    raw = _o3(CLASSIFY_SYSTEM, {"sentences": [{"index": i, "text": s} for i, s in enumerate(sentences)]})
    labels = ["Other"] * len(sentences)
    for item in raw.get("labels", []) if isinstance(raw, dict) else []:
        try:
            i = int(item["index"])
        except (KeyError, TypeError, ValueError):
            continue
        if 0 <= i < len(sentences) and item.get("label") in LABELS:
            labels[i] = item["label"]
    return labels


def relations(target_text: str) -> list[dict[str, str]]:
    raw = _o3(RELATION_SYSTEM, {"sentences": target_text})
    kept = []
    for item in raw.get("relations", []) if isinstance(raw, dict) else []:
        if not isinstance(item, dict):
            continue
        head, tail, kind = str(item.get("head", "")).strip(), str(item.get("tail", "")).strip(), item.get("head_type")
        # Computational sensors: exact spans, a known head type, and the hidden head never inside the seed.
        if (head and tail and kind in ("Method", "Material") and _norm(tail) in _norm(target_text)
                and _norm(head) in _norm(target_text) and _norm(head) not in _norm(tail) and _norm(tail) != _norm(head)):
            kept.append({"head": head, "head_type": kind, "tail": tail})
    return kept[:5]


def compose(background: list[str], relation: dict[str, str]) -> str:
    p = relation["head_type"].lower()
    seed = relation["tail"].rstrip(" .")
    if background:
        return TEMPLATE.format(context=" ".join(background), p=p, seed=seed)
    return NO_CONTEXT_TEMPLATE.format(p=p, seed=seed)


def build_case(case: dict[str, Any]) -> dict[str, Any]:
    pid = case["paper_id"]
    path = CASES_OUT / f"{pid}.json"
    if path.exists():
        return _read_json(path)
    sentences = abstract_sentences(pid)
    labels = classify(sentences)
    background, dropped = [], []
    for sentence, label in zip(sentences, labels):
        if label != "Background":
            continue
        (dropped if v3.SELF_REFERENCE.search(sentence) else background).append(sentence)
    target_text = " ".join(s for s, label in zip(sentences, labels) if label != "Background")
    rels = relations(target_text)
    flags: list[str] = [] if background else ["no_background"]
    tries: list[dict[str, Any]] = []
    chosen = None
    for relation in rels[:MAX_TRIES]:
        text = compose(background, relation)
        result = v3.check(text, case["hidden_target"])
        tries.append({"relation": relation, "query": text, "check": result})
        if result["passed"]:
            chosen = len(tries) - 1
            break
    if not rels:
        flags.append("no_relation")
        text = (TEMPLATE.format(context=" ".join(background), p="method", seed="the stated problem") if background
                else NO_CONTEXT_TEMPLATE.format(p="method", seed="the stated problem"))
        result = v3.check(text, case["hidden_target"])
        tries.append({"relation": None, "query": text, "check": result})
        if result["passed"]:
            chosen = len(tries) - 1
    if chosen is None:
        chosen = 0
        flags.append("failed_gate")
    pick = tries[chosen]
    out = {
        "schema_version": "benchmark-v4-scimon-1.0", "benchmark_version": VERSION, "paper_id": pid,
        "publication_date": case["publication_date"], "split": case["split"],
        "benchmark_claim": "retrospective_temporal_reconstruction",
        "query_source": "SciMON-style: abstract Background sentences + task-side seed term (loop.md 14.1)",
        "query_writer": f"trapi:{LABELLER} (sentence labels, relations; verbatim spans only)",
        "leakage_checker": f"trapi:{v3.CHECKER}",
        "queries": {LEVEL: {"text": pick["query"], "passed_gate": pick["check"]["passed"],
                            "overlap": pick["check"]["overlap"],
                            "raw_overlap_exp19_metric": round(v3.raw_overlap(pick["query"], case["hidden_target"]), 3),
                            "steers_to_answer": pick["check"]["steers_to_answer"], "source_role_refs": []}},
        "hidden_target": case["hidden_target"],
        "hidden_target_source": case.get("hidden_target_source", "unchanged from the v3.1/test2/test3 case"),
        "flags": flags,
        "scimon": {"background_sentences": background, "dropped_self_reference": dropped,
                   "seed": pick["relation"]["tail"] if pick["relation"] else None,
                   "target_type": pick["relation"]["head_type"] if pick["relation"] else None,
                   "tries_used": len(tries), "relation_rank": chosen + 1},
    }
    atomic_json(OUT / "build_log" / f"{pid}.json", {"paper_id": pid, "sentences": sentences, "labels": labels,
                                                     "relations": rels, "tries": tries})
    atomic_json(path, out)
    return out


def summarise(built: list[dict[str, Any]]) -> dict[str, Any]:
    flags: dict[str, int] = {}
    for case in built:
        for flag in case["flags"]:
            flags[flag] = flags.get(flag, 0) + 1
    gate = [c["queries"][LEVEL] for c in built]
    return {"cases": len(built), "unflagged": sum(not c["flags"] for c in built),
            "passed_gate": sum(q["passed_gate"] for q in gate), "flags": flags,
            "steers_to_answer": sum(bool(q["steers_to_answer"]) for q in gate),
            "mean_overlap": round(sum(q["overlap"] for q in gate) / len(gate), 3),
            "background_sentences": [len(c["scimon"]["background_sentences"]) for c in built],
            "relation_rank_used": [c["scimon"]["relation_rank"] for c in built],
            "target_type": {t: sum(c["scimon"]["target_type"] == t for c in built) for t in ("Method", "Material")}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--summary-only", action="store_true", help="recompute summary.json from the frozen cases")
    args = parser.parse_args()
    if args.summary_only:
        built = [json.loads(p.read_text()) for p in sorted((OUT / "cases").glob("PMC*.json"))]
    else:
        cases = [c for _, c in sorted(H.cases().items())]
        with ThreadPoolExecutor(args.workers) as pool:
            built = list(pool.map(build_case, cases))
    summary = summarise(built)
    atomic_json(OUT / "summary.json", summary)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
