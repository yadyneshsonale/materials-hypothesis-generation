"""Experiment 42 (loop.md 23): stage improvements suggested by six independent reviews (rubber-duck agents).

Shared, target-free helpers used by both the offline checks (v2_offline.py) and the methods (loop_methods.py):
- retrieval v2: BM25 on the question's content words without the benchmark's task-schema words, weighted by section
  (results, discussion, conclusions and abstracts up; introductions down) and by whether a passage reports a study
  action;
- gap analogs: earlier papers whose introduction states a gap similar to the question, and the study each then did.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Iterable

import citegraph as cg
from citegraph import content_terms

# Words of the benchmark's question template, not of the scientific problem: 132 of 135 questions contain
# "hypothesis" and 125 "evidence" (retrieval review). They pull generic prose into the ranking.
SCHEMA_STOP = frozenset("""hypothesis hypotheses evidence supporting support supported single state states statement
predict predicts predicted prediction predictions outcome outcomes mechanism mechanisms explain explains explained
define defines defined identify identifies identified intervention interventions condition conditions improvement improve
improves improved relative untreated question questions research propose proposes proposing work works should would
could which what how whether alloy alloys high entropy heas hea""".split())

SECTION_UP = re.compile(r"abstract|result|discussion|conclu|summary|finding", re.IGNORECASE)
SECTION_DOWN = re.compile(r"introduc|background|motivation|literature|overview", re.IGNORECASE)
ACTION = re.compile(
    r"\b(we|was|were|is|are|been|being|has|have|had)\s+(?:\w+\s+){0,2}?"
    r"(add|alloy|dop|coat|deposit|anneal|sinter|fabricat|prepar|produc|print|melt|cast|treat|age|aged|roll|forg|"
    r"spray|sputter|simulat|calculat|comput|modif|substitut|introduc|design|synthes|process|consolidat|homogeni|"
    r"irradiat|oxidi|test|measur|characteri)\w*", re.IGNORECASE)
WEIGHT_UP, WEIGHT_DOWN, WEIGHT_ACTION = 1.2, 0.8, 1.5


def clean_terms(text: str) -> list[str]:
    return [t for t in content_terms(text) if t not in SCHEMA_STOP]


def bm25_scores(query: Iterable[str], docs: dict[str, list[str]], k1: float = 1.2, b: float = 0.75
                ) -> dict[str, float]:
    n = len(docs) or 1
    avg = sum(len(d) for d in docs.values()) / n if docs else 1.0
    df = Counter(t for d in docs.values() for t in set(d))
    out = {}
    q = set(query)
    for key, doc in docs.items():
        tf = Counter(doc)
        s = 0.0
        for t in q:
            if t in tf:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * len(doc) / max(avg, 1.0)))
        out[key] = s
    return out


def section_weight(kind: str) -> float:
    section = str(kind).split(":", 1)[-1]
    if SECTION_UP.search(section):
        return WEIGHT_UP
    if SECTION_DOWN.search(section):
        return WEIGHT_DOWN
    return 1.0


def salience(text: str, kind: str, bm25: float) -> float:
    return bm25 * section_weight(kind) * (WEIGHT_ACTION if ACTION.search(text) else 1.0)


def salience_order(question: str, records: list[Any]) -> list[Any]:
    """Records ordered by retrieval-v2 salience; records sharing no cleaned word with the question come last, in a
    fixed order."""
    docs = {r.record_id: clean_terms(r.text) for r in records}
    scores = bm25_scores(clean_terms(question), docs)
    keyed = {r.record_id: salience(r.text, r.kind, scores.get(r.record_id, 0.0)) for r in records}
    return sorted(records, key=lambda r: (-keyed[r.record_id], r.record_id))


# ---------------------------------------------------------------- gap analogs

OWN = re.compile(
    r"\b(in this (work|study|paper|article|research|investigation|contribution)|in the present (work|study|paper)|"
    r"here,? we|herein|this (work|study|paper|article) (aims|reports|presents|investigates|proposes|demonstrates|"
    r"explores|focuses|examines|addresses)|the (aim|purpose|objective|goal)s? of (this|the present) "
    r"(work|study|paper)|we (report|present|propose|demonstrate|investigate|develop|introduce|explore|systematically))\b",
    re.IGNORECASE)
INTRO = re.compile(r"introduc|background", re.IGNORECASE)
GAP_SENTENCES = 6
STUDY_CHARS = 700


def gap_and_study(sections: list[tuple[str, str]]) -> dict[str, str] | None:
    """The introduction's final gap (up to 6 sentences before the first own-work sentence) and the own-work
    statement that follows it. Papers without an explicit introduction or own-work sentence are skipped."""
    intro = [p for s, p in sections if INTRO.search(s)]
    if not intro:
        return None
    sentences = [x.strip() for p in intro for x in cg.split_sentences(p) if x.strip()]
    first_own = next((i for i, x in enumerate(sentences) if OWN.search(x)), None)
    if first_own is None or first_own < 2:
        return None
    gap = " ".join(sentences[max(0, first_own - GAP_SENTENCES):first_own])
    study = " ".join(sentences[first_own:])[:STUDY_CHARS]
    if len(gap) < 200 or len(study) < 60:
        return None
    return {"gap": gap, "study": study}


def rank_analogs(question: str, analogs: dict[str, dict[str, str]]) -> list[str]:
    """Analog IDs by BM25 similarity of the question to each analog's gap (ties: ID order)."""
    docs = {k: clean_terms(v["gap"]) for k, v in analogs.items()}
    scores = bm25_scores(clean_terms(question), docs)
    return sorted(analogs, key=lambda k: (-scores.get(k, 0.0), k))


def classify_removed(removed: list[str], seen: list[str]) -> Counter:
    """Kinds of citation slip: a pack record with its section suffix rewritten or dropped, another record of a paper in
    the pack, or a paper not in the pack (record IDs are paper::web::index::section)."""
    records = {"::".join(s.split("::")[:3]) for s in seen}
    papers = {s.split("::")[0] for s in seen}
    out: Counter = Counter()
    for rid in removed:
        if "::".join(rid.split("::")[:3]) in records:
            out["pack record, section suffix rewritten"] += 1
        elif rid.split("::")[0] in papers:
            out["pack paper, record not in pack"] += 1
        else:
            out["paper not in pack"] += 1
    return out
