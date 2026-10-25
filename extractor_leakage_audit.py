"""Extractor leakage audit (experiment 21 supplement): do LLM-made extractions of earlier papers carry content from
the later held-out papers?

The rerun uses a pre-cutoff generator, but the evidence it reads includes records that the post-cutoff Qwen
extracted from pre-cutoff papers (v2 evidence units, rubric records, citation-graph cards and citer statements).
The extractor never saw a query or a target, so the only way it could leak is by writing knowledge of a later paper
into the record of an earlier one. This audit measures that directly:

  injected(record, case) = answer-specific word stems of the case that appear in the record but nowhere in the
                           record's own source text (the earlier paper, or for a citer statement the citing paper).

Answer-specific stems: stems of the hidden target's intervention, structural mediator, mechanism and predicted
outcome, minus stems of its starting material, conditions and baseline, minus stems of the case's v3 query (the
generator sees those anyway), minus stems found in more than 20% of the corpus papers (generic vocabulary).

A memorising extractor would inject the true case's answer stems more often than other cases' answer stems. The
control applies the vocabulary of each of the other 11 cases to the same records. Records that are raw text (text
chunks) and MatKG facts (database rows, filtered by year) are not LLM-written and are not audited.
"""

from __future__ import annotations

import json
import os
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import rubric_eval as rx
from hypothesis_evidence_v2 import atomic_json
from temporal_eval_v3 import EXPERIMENT_DIR
from temporal_hypothesis_benchmark import _read_json

CASES_DIR = EXPERIMENT_DIR / "benchmark_v3" / "cases"
GRAPHS = EXPERIMENT_DIR / "rerun_v3" / "citegraph" / "cases"
PAPERS = EXPERIMENT_DIR / "citegraph" / "papers"
OUT = EXPERIMENT_DIR / "rerun_v3" / "extractor_leakage"
REPRESENTATIONS = ("v2_units", "card", "effects", "mechanisms", "gaps")
ANSWER_FIELDS = ("intervention", "structural_mediator", "mechanism", "predicted_outcome")
CONTEXT_FIELDS = ("material_initial_state", "conditions", "baseline")
MAX_DOC_FREQ = 0.20
ELEMENTS = set("""h he li be b c n o f ne na mg al si p s cl ar k ca sc ti v cr mn fe co ni cu zn ga ge as se br kr rb sr y
zr nb mo tc ru rh pd ag cd in sn sb te i xe cs ba la ce pr nd pm sm eu gd tb dy ho er tm yb lu hf ta w re os ir pt au
hg tl pb bi""".split())
STOP = set("""the and for with from that this into within between than their which while where when what given
propose specify expected must aim using use via based under over also such both each more less can could would should
may might will its not are was were been has have how does one two new study effect role case experiment intervention
regime trade off compared baseline approach mechanism hypothesis increase increased decrease decreased high higher low
lower improve improved improvement enhance enhanced due result results resulting leading leads lead while thus
significant significantly approximately about after before during through without""".split())
# Ordered longest-first so derivational variants converge (reticulated / reticulation / reticulate -> reticul,
# stabilized / stabilization / stabilize -> stabil, sintered / sintering -> sinter).
SUFFIXES = ("izations", "ization", "isations", "isation", "ations", "ation", "ators", "ator", "atives", "ative",
            "ating", "ated", "ates", "ate", "izes", "ized", "izing", "ize", "ises", "ised", "ising", "ingly", "ings", "ing",
            "ities", "ity", "nesses", "ness", "ments", "ment", "ically", "ical", "ally", "edly", "ed", "es", "s", "al",
            "ly")


def stem(word: str) -> str:
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def stems(text: str) -> set[str]:
    out = set()
    for token in re.findall(r"[a-z0-9]+", str(text).lower()):
        if token in STOP:
            continue
        if len(token) >= 3 or token in ELEMENTS:
            out.add(stem(token))
    return out


LABELS = sorted({label for fields in rx.RENDER_FIELDS.values() for label, _ in fields}
                | set(rx.RUBRIC_LABEL.values()) | {"Quote"}, key=len, reverse=True)


def strip_labels(text: str) -> str:
    """Remove the rubric's own rendering labels ("Gap and lever.", "Lever:", ...), which are not extracted content."""
    for label in LABELS:
        text = re.sub(rf"\b{re.escape(label)}\s*[:.]", " ", text)
    return text


def answer_vocabulary(case: dict[str, Any], doc_freq: Counter[str], n_docs: int) -> set[str]:
    target = case["hidden_target"]
    answer = stems(" ".join(str(target.get(k, "")) for k in ANSWER_FIELDS))
    allowed = stems(" ".join(str(target.get(k, "")) for k in CONTEXT_FIELDS))
    allowed |= stems(" ".join(q["text"] for q in case["queries"].values()))
    return {s for s in answer - allowed if doc_freq[s] / n_docs <= MAX_DOC_FREQ and not s.isdigit()}


def corpus_stems() -> tuple[dict[str, set[str]], Counter[str]]:
    texts = {p.stem: stems(p.read_text()) for p in sorted(rx.TEXT_DIR.glob("PMC*.txt"))}
    doc_freq: Counter[str] = Counter(s for words in texts.values() for s in words)
    return texts, doc_freq


def records_for(case: dict[str, Any], corpus: dict[str, set[str]]) -> list[dict[str, Any]]:
    """Every LLM-written record the rerun generator could read for this case, with its source stems."""
    records = []
    for rep in REPRESENTATIONS:
        _, pool = rx.case_pool(case, rep)
        for r in pool:
            text = r.text
            if rep == "v2_units":
                # the v2 record text starts with its own identifiers; only the extracted content is audited
                text = text.replace(r.record_id, " ").replace(r.paper_id, " ")
            text = strip_labels(text)
            records.append({"representation": rep, "record_id": r.record_id, "paper_id": r.paper_id,
                            "stems": stems(text), "source": corpus[r.paper_id], "text": text})
    graph_path = GRAPHS / case["paper_id"] / "graph.json"
    if graph_path.exists():
        graph = _read_json(graph_path)
        source_cache: dict[str, set[str]] = {}

        def source(pmcid: str) -> set[str]:
            if pmcid not in source_cache:
                parsed = _read_json(PAPERS / pmcid / "parsed.json")
                titles = " ".join(str(w.get("title", "")) for w in parsed.get("ref_works", {}).values())
                source_cache[pmcid] = stems(parsed["text"] + " " + titles)
            return source_cache[pmcid]

        for node in graph["nodes"].values():
            if node["card"] and node["pmcid"]:
                text = strip_labels(" ".join(node["card"]))
                records.append({"representation": "graph_card", "record_id": f"card::{node['pmcid']}",
                                "paper_id": node["pmcid"], "stems": stems(text), "source": source(node["pmcid"]),
                                "text": text})
            for st in node["statements"]:
                citer = graph["nodes"].get(st["citer"], {})
                if not citer.get("pmcid"):
                    continue
                text = " ".join(str(st.get(k, "")) for k in ("attributed", "cited_system", "applied_to", "numbers"))
                records.append({"representation": "citer_statement",
                                "record_id": f"stmt::{citer['pmcid']}::{st['ctx']}::{st['rid']}",
                                "paper_id": citer["pmcid"], "stems": stems(text), "source": source(citer["pmcid"]),
                                "text": text})
    return records


def audit() -> dict[str, Any]:
    cases = {c["paper_id"]: c for c in (_read_json(p) for p in sorted(CASES_DIR.glob("PMC*.json")))}
    corpus, doc_freq = corpus_stems()
    n_docs = len(corpus)
    vocab = {pid: answer_vocabulary(case, doc_freq, n_docs) for pid, case in cases.items()}
    per_rep: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"true": [], "control": []})
    examples: list[dict[str, Any]] = []
    injected_words: Counter[str] = Counter()
    record_counts: Counter[str] = Counter()
    for pid, case in cases.items():
        records = records_for(case, corpus)
        unsupported = [(r, r["stems"] - r["source"]) for r in records]
        for rep in sorted({r["representation"] for r in records}):
            rows = [(r, extra) for r, extra in unsupported if r["representation"] == rep]
            record_counts[rep] += len(rows)
            true_hits = [extra & vocab[pid] for _, extra in rows]
            per_rep[rep]["true"].append(sum(bool(h) for h in true_hits) / len(rows))
            controls = [sum(bool(extra & vocab[other]) for _, extra in rows) / len(rows)
                        for other in cases if other != pid]
            per_rep[rep]["control"].append(statistics.fmean(controls))
            for (r, _), hits in zip(rows, true_hits):
                if hits:
                    injected_words.update(hits)
                    examples.append({"case": pid, "representation": rep, "record_id": r["record_id"],
                                     "injected_stems": sorted(hits), "record_text": r["text"][:500]})
    summary = {rep: {"case_record_pairs": record_counts[rep],
                     "share_with_injected_true_answer_stem": round(statistics.fmean(v["true"]), 4),
                     "share_with_injected_other_case_stem_control": round(statistics.fmean(v["control"]), 4),
                     "ratio_true_to_control": round(statistics.fmean(v["true"]) / statistics.fmean(v["control"]), 2)
                     if statistics.fmean(v["control"]) else None}
               for rep, v in sorted(per_rep.items())}
    result = {"method": __doc__.split("\n\n")[1].strip(), "answer_vocabulary_size": {k: len(v) for k, v in vocab.items()},
              "summary": summary, "most_injected_stems": injected_words.most_common(25),
              "examples": examples, "examples_total": len(examples)}
    atomic_json(OUT / "analysis.json", result)
    return result


if __name__ == "__main__":
    os.environ.setdefault("MATHG_CASES_DIR", str(CASES_DIR))
    out = audit()
    print(json.dumps({k: out[k] for k in ("answer_vocabulary_size", "summary", "most_injected_stems",
                                          "examples_total")}, indent=1))
