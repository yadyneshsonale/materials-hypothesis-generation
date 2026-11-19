"""Experiment 49 (loop.md 28.1): per-paper generate -> critique -> narrow.

For a question q with knowledge cutoff t:
  1. retrieve   the N most relevant papers before t: the experiment-44 focused corpus of the question (relevance-
                screened, dated, the case paper and its work family excluded), at most one paper per first author;
  2. per paper  (in parallel) background M_i = teaching-text passages (materials_texts.py, BM25 on q + the paper's
                title) + MatKG co-occurrence facts dated before t;
                generator G(q, p_i, M_i) writes K hypotheses that build on the paper; critic C(p_i, M_i) (never sees
                q) checks each for soundness, testability and going beyond the paper; G revises from the critique;
                the loop stops at the first round with an accepted hypothesis, or after R rounds (the paper is then
                dropped);
  3. narrow     the accepted hypotheses of all papers, near-duplicates merged, enter a tournament on q (both orders;
                a win needs both): a round robin if there are at most 6, else 5 Swiss rounds and a round robin of the
                top 5. The method returns the rank-1 hypothesis; the ranked top 3 is kept in the run's notes.

Every agent is o3-mini (pre-cutoff). No prompt is an evaluating judge's prompt (must_obey.md 6.12).
"""

from __future__ import annotations

import itertools
import json
import math
import os
import re
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import focused_search as FS
import hypo_loop as H
import loop_methods as LM
import materials_texts as MT
import rubric_eval as rx
import stage_v2 as S2
from hypo_loop import Harness, register
from matkg_index import DEFAULT_DB, fact_record_id
from temporal_eval_v3 import kg_excluded_dois
from temporal_hypothesis_benchmark import RetrievalRecord, _validate_generation

MODEL = "o3mini"
N_PAPERS = 10
K = 3
MAX_ROUNDS = 20
TEXT_PASSAGES = 6
KG_FACTS = 8
PAPER_CHARS = 30000
SWISS_ROUNDS = 5
FINAL_POOL = 5
PAPER_WORKERS = int(os.environ.get("MATHG_PERPAPER_WORKERS", "4"))
SKIP_SECTIONS = re.compile(r"reference|acknowledg|funding|author contribution|conflict|data availab|supplementary",
                           re.I)

_CONSERVATIVE = (
    "Predict the direction and approximate size of effects only as far as the paper, the background and your "
    "knowledge support; if support is insufficient, say so in the uncertainty field instead of inventing support or "
    "precise values. Use only knowledge from before the knowledge cutoff; never claim knowledge of later work."
)
_ITEM = LM.SCHEMA[:-2].rstrip() + (
    ',\n  "builds_on": "the finding or mechanism of the paper this hypothesis starts from",\n'
    '  "what_is_new": "what this hypothesis proposes that the paper did not do, report or propose"\n}')
GENERATOR_SYSTEM = (
    "You are a materials scientist generating research hypotheses. You receive a research question with a knowledge "
    "cutoff, ONE earlier paper (its full text as passages with record IDs), and background knowledge: passages from "
    "materials-science teaching texts and co-occurrence statistics from a materials knowledge graph (also with record "
    "IDs).\n\n"
    "Write {k} distinct hypotheses that answer the research question and are inspired by this paper. Each proposes a "
    "concrete change to the material in the question (its composition, processing route, heat treatment, "
    "microstructure, surface or test condition) and explains it with a physical mechanism.\n"
    "- Build on the paper; do not restate it. Carry its finding or mechanism to the question's material or regime, "
    "combine it with a principle from the background, or test a condition, composition or mechanism the paper left "
    "open, and say why it should work there.\n"
    "- Do not propose what the paper already did or reported, nor what it suggests as future work, and do not "
    "only change a parameter of the paper's own intervention without a new mechanistic reason.\n"
    "- Each hypothesis must stay within the question's constraints, be physically sound and be decidable by a "
    "feasible experiment with a clear falsification rule.\n"
    "- The {k} hypotheses must differ in their intervention or mechanism.\n"
    "- " + _CONSERVATIVE + "\n"
    "- Cite supporting and conflicting record IDs exactly as supplied (paper passages, teaching texts or graph "
    "facts).\n\n"
    "If previous hypotheses and a critique are supplied, revise: fix every problem the critique names, or replace "
    "the hypothesis with a better one. Keep answering the research question.\n\n"
    "Return JSON {\"hypotheses\": [ ... {k} items, each: " + _ITEM + " ]}"
)
CRITIC_SYSTEM = (
    "You are a demanding senior materials scientist reviewing research hypotheses that a colleague derived from one "
    "earlier paper. You receive the paper (full text as passages with record IDs), background knowledge "
    "(teaching-text passages and knowledge-graph statistics, with record IDs) and the hypotheses. Most first drafts "
    "have at least one real flaw; your job is to find it, not to approve.\n\n"
    "First, list what the paper already did (materials, interventions, conditions), what it reported (main results "
    "and mechanisms) and what it proposes as future work.\n"
    "Then judge each hypothesis on three criteria, independently:\n"
    "1. \"sound\": fails if anything contradicts the paper's data or established materials science; if the "
    "mechanism is generic (it would read the same for almost any alloy) rather than specific to this material system "
    "and regime; if the predicted direction or size does not follow from the mechanism; or if a key assumption is "
    "unsupported.\n"
    "2. \"testable\": fails if the experiment lacks a control or baseline, cannot separate the proposed mechanism "
    "from obvious alternatives, is infeasible, or if the falsification rule has no explicit threshold or comparison.\n"
    "3. \"beyond_paper\": fails if the hypothesis matches anything on your list of what the paper did, reported or "
    "proposed; if it only changes a parameter of the paper's own intervention without a new mechanistic reason; or "
    "if it is a standard textbook remedy with no reason drawn from this paper.\n"
    "For every criterion give pass true or false and a one-sentence reason. Pass a criterion only when you can state "
    "concretely why it holds. When a criterion fails, quote the passage of the paper or background that shows the "
    "problem, if there is one, and give one concrete fix.\n"
    "Return JSON {\"paper_did\": [str], \"paper_reported\": [str], \"paper_proposed\": [str], \"reviews\": "
    "[{\"id\": \"H1\", \"sound\": {\"pass\": bool, \"reason\": str}, \"testable\": {\"pass\": bool, "
    "\"reason\": str}, \"beyond_paper\": {\"pass\": bool, \"reason\": str}, \"evidence_quote\": str, "
    "\"fix\": str}]} with one review per hypothesis, in the order given."
)
NARROW_SYSTEM = (
    "You are a senior materials scientist choosing which of two research hypotheses to pursue for the same research "
    "question. Choose the one that a competent research group facing exactly this question should pursue: it "
    "attacks the limitation or open question the question states, satisfies every stated constraint, uses a "
    "mechanism that is physically sound for this material system and regime, goes beyond what earlier work already "
    "did, is feasible with standard methods and makes a decisive prediction. Ignore length and style. Return JSON "
    "{\"winner\": \"A\" or \"B\", \"reason\": str}."
)
CRITERIA = ("sound", "testable", "beyond_paper")
CRITIC_MODEL = "o3mini_high"  # o3-mini with high reasoning effort (pre-cutoff); stricter than the default effort
NARROW_MODEL = "o3mini_high"  # at the default effort the narrowing judge followed position in both orders (smoke test)


# ---------------------------------------------------------------- retrieval and background

def select_papers(h: Harness, n: int = N_PAPERS) -> list[dict[str, Any]]:
    """The n best papers of the question's focused corpus (screen grade, then the corpus order), one per first
    author."""
    manifest = FS.build(h.case["paper_id"], h.level)
    for role, model in manifest["models"].items():
        h.models.setdefault(f"focused_{role}", model)
    order = {p["pmcid"]: i for i, p in enumerate(manifest["papers"])}
    chosen, authors = [], set()
    for paper in sorted(manifest["papers"], key=lambda p: (-int(p.get("grade") or 0), order[p["pmcid"]])):
        author = str(paper.get("first_author") or paper["pmcid"]).lower()
        if author in authors:
            continue
        chosen.append(paper)
        authors.add(author)
        if len(chosen) >= n:
            break
    return chosen


def paper_text(paper: dict[str, Any], budget: int = PAPER_CHARS) -> list[RetrievalRecord]:
    """The paper's passages in reading order, without reference-like sections, up to the character budget."""
    out, used = [], 0
    for record in FS.paper_records(paper):
        if SKIP_SECTIONS.search(str(record.kind)):
            continue
        if used + len(record.text) > budget:
            break
        out.append(record)
        used += len(record.text)
    return out


class _TextIndex:
    """BM25 over the teaching-text passages, built once per process."""

    _lock = threading.Lock()
    _inst: _TextIndex | None = None

    def __init__(self) -> None:
        self.recs = MT.load()
        self.docs = [Counter(S2.clean_terms(f"{r['title']} {r['section']} {r['text']}")) for r in self.recs]
        self.lens = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lens) / max(1, len(self.lens))
        self.df = Counter(t for d in self.docs for t in d)

    @classmethod
    def get(cls) -> _TextIndex:
        with cls._lock:
            if cls._inst is None:
                cls._inst = cls()
            return cls._inst

    def top(self, text: str, n: int, k1: float = 1.2, b: float = 0.75) -> list[dict[str, Any]]:
        terms = set(S2.clean_terms(text))
        total = len(self.docs)
        idf = {t: math.log(1 + (total - self.df[t] + 0.5) / (self.df[t] + 0.5)) for t in terms if self.df[t]}
        scored = []
        for i, doc in enumerate(self.docs):
            s = sum(idf[t] * doc[t] * (k1 + 1) / (doc[t] + k1 * (1 - b + b * self.lens[i] / self.avg))
                    for t in idf if t in doc)
            if s > 0:
                scored.append((s, i))
        scored.sort(reverse=True)
        out, docs_used = [], Counter()
        for _, i in scored:  # at most two passages from one document, for breadth
            r = self.recs[i]
            if docs_used[r["doc"]] >= 2:
                continue
            out.append(r)
            docs_used[r["doc"]] += 1
            if len(out) >= n:
                break
        return out


def text_records(question: str, paper: dict[str, Any], n: int = TEXT_PASSAGES) -> list[RetrievalRecord]:
    hits = _TextIndex.get().top(f"{question} {paper.get('title', '')}", n)
    out = []
    for r in hits:
        if MT.HEA.search(r["text"]):  # the build-time rule, re-checked at use (loop.md 28.1)
            continue
        out.append(RetrievalRecord(r["record_id"], f"TXT::{r['source']}::{r['doc']}", r.get("date") or "",
                                   f"text:{r['source']}", r["text"],
                                   {"source": "materials_text", "title": f"{r['title']} ({r['source']})",
                                    "section": r["section"], "licence": r["licence"], "url": r["url"]}))
    return out


_KG_CACHE: dict[tuple[str, str], list[RetrievalRecord]] = {}
_KG_LOCK = threading.Lock()
KG_TYPES = ("CHM", "PRO", "SMT", "SPL", "DSC")  # chemistry, property, synthesis, phase, descriptor (no methods)
KG_ANCHOR_SINGLE = ("CHM", "SPL")  # any established chemical or phase may be a one-word anchor
KG_SINGLE_MAX = 50_000  # other one-word anchors (property, process, descriptor) must not be ultra-generic
KG_DOMAIN = ("alloy", "alloys", "superalloy", "superalloys", "steel", "steels", "intermetallic", "intermetallics")
KG_MIN_PAPERS, KG_TYPE_SHARE, KG_ANCHORS, KG_DOIS = 30, 0.6, 4, 3000
KG_PAPERS_EST, KG_DF_CAP = 5_000_000, 200_000  # MatKG covers about 5M abstracts; document counts are capped for speed
_DF_CACHE: dict[tuple[str, int], int] = {}
KG_STOP = set(S2.clean_terms("")) | {
    "but", "has", "have", "had", "its", "the", "and", "for", "with", "this", "that", "these", "those", "which", "what",
    "from", "into", "than", "then", "also", "such", "can", "could", "would", "should", "may", "might", "will", "one",
    "two", "single", "evidence", "room", "state", "study", "studies", "effect", "effects", "result", "results",
    "property", "properties", "performance", "material", "materials", "alloy", "alloys", "intervention",
    "hypothesis", "mechanism", "experiment", "condition", "conditions", "prior", "proposed", "relative", "baseline",
    "improve", "improvement", "under", "while", "high", "low", "temperature", "strength", "new", "using", "based",
    "surface", "microstructure", "microstructures", "composition", "compositions", "mechanical", "mechanical property",
    "mechanical properties", "structure", "doped", "density", "phase", "phases", "sample", "samples", "process",
    "method", "film", "films", "particles", "resistance", "resistance r", "entropy", "high entropy", "hea", "heas"}


def kg_anchors(con: Any, topic: str, cutoff_year: int) -> list[tuple[str, int]]:
    """Established entities named in the topic: at least KG_MIN_PAPERS abstracts before the cutoff year and one
    dominant entity type; multi-word phrases first."""
    from matkg_index import candidate_phrases
    found = []
    for phrase in dict.fromkeys(candidate_phrases(topic)):
        words = phrase.split()
        if len(phrase) < 2 or phrase.isdigit() or all(w in KG_STOP for w in words) or words[0] in KG_STOP \
                or words[-1] in KG_STOP:
            continue
        rows = con.execute("SELECT ner, COUNT(DISTINCT doi) FROM ent WHERE entity = ? AND year < ? GROUP BY ner",
                           (phrase, cutoff_year)).fetchall()
        total = sum(n for _, n in rows)
        if total < KG_MIN_PAPERS:
            continue
        ner, top = max(rows, key=lambda r: r[1])
        if len(words) == 1 and ner not in KG_ANCHOR_SINGLE and total > KG_SINGLE_MAX:
            continue
        if ner in KG_TYPES and top / total >= KG_TYPE_SHARE and phrase not in KG_STOP:
            found.append((phrase, total))
    found.sort(key=lambda x: (-len(x[0].split()), x[1]))
    return found[:KG_ANCHORS]


def _df(con: Any, entity: str, year: int) -> int:
    key = (entity, year)
    with _KG_LOCK:
        if key in _DF_CACHE:
            return _DF_CACHE[key]
    n = con.execute("SELECT COUNT(*) FROM (SELECT 1 FROM ent WHERE entity = ? AND year < ? LIMIT ?)",
                    (entity, year, KG_DF_CAP)).fetchone()[0]
    with _KG_LOCK:
        _DF_CACHE[key] = n
    return n


def kg_facts(topic: str, cutoff: str, excluded: set[str], n: int) -> list[dict[str, Any]]:
    import sqlite3
    from matkg_index import normalize_doi
    year = int(cutoff[:4])
    blocked = {normalize_doi(d) for d in excluded if d}
    con = sqlite3.connect(f"file:{DEFAULT_DB}?mode=ro", uri=True)
    try:
        facts = []
        anchors = kg_anchors(con, topic, year)
        names = {a for a, _ in anchors}
        for anchor, _ in anchors:
            # metallurgy only: abstracts that mention the anchor and an alloy (MatKG is dominated by chemistry)
            dois = [d for (d,) in con.execute(
                "SELECT DISTINCT e1.doi FROM ent e1 JOIN ent e2 ON e2.doi = e1.doi WHERE e1.entity = ? AND e1.year < ? "
                f"AND e2.entity IN ({','.join('?' * len(KG_DOMAIN))}) ORDER BY e1.year DESC LIMIT ?",
                (anchor, year, *KG_DOMAIN, KG_DOIS)) if normalize_doi(d) not in blocked]
            if not dois:
                continue
            marks = ",".join("?" * len(dois))
            rows = con.execute(
                f"SELECT entity, COUNT(DISTINCT doi), MAX(year) FROM ent WHERE doi IN ({marks}) AND year < ? "
                f"AND ner IN ({','.join('?' * len(KG_TYPES))}) GROUP BY entity ORDER BY 2 DESC LIMIT 60",
                (*dois, year, *KG_TYPES)).fetchall()
            for entity, papers, latest in rows:
                words = entity.split()
                if entity in names or entity in KG_STOP or len(entity) < 3 or entity.isdigit() \
                        or all(w in KG_STOP for w in words) or papers < 5 or MT.HEA.search(entity):
                    continue
                df = _df(con, entity, year)
                share = papers / len(dois)
                facts.append({"anchor": anchor, "neighbor": entity, "papers": int(papers), "of": len(dois),
                              "latest_year": int(latest), "share": round(share, 3),
                              "score": round(share * math.log(KG_PAPERS_EST / max(1, df)), 4)})
        facts.sort(key=lambda f: -f["score"])
        out, per_anchor = [], Counter()
        for f in facts:  # breadth: at most n // 2 facts per anchor
            if per_anchor[f["anchor"]] >= max(2, n // 2):
                continue
            out.append(f)
            per_anchor[f["anchor"]] += 1
            if len(out) >= n:
                break
        return out
    finally:
        con.close()


def kg_records(h: Harness, paper: dict[str, Any], n: int = KG_FACTS) -> list[RetrievalRecord]:
    title = re.sub(r"<[^>]+>", "", str(paper.get("title", "")))
    key = (h.case["paper_id"], paper["pmcid"])
    with _KG_LOCK:
        if key in _KG_CACHE:
            return _KG_CACHE[key]
    facts = kg_facts(title, h.cutoff, kg_excluded_dois(h.case["paper_id"], rx.metadata()), n)
    out = [RetrievalRecord(
        fact_record_id([f["anchor"]], f["neighbor"]), "KG", f"{f['latest_year']}-12-31", "kg:cooccurrence",
        f"Materials knowledge graph (MatKG, alloy abstracts before {h.cutoff[:4]}): of the {f['of']} most recent "
        f"abstracts mentioning '{f['anchor']}' and an alloy, {f['papers']} ({f['share']:.0%}) also mention '{f['neighbor']}' (latest "
        f"{f['latest_year']}).", {"source": "matkg", "title": "MatKG co-occurrence"}) for f in facts]
    with _KG_LOCK:
        _KG_CACHE[key] = out
    return out


def item(record: RetrievalRecord) -> dict[str, Any]:
    s = record.structured or {}
    return {"record_id": record.record_id, "source": s.get("title", ""), "section": s.get("section") or
            str(record.kind).split(":", 1)[-1][:60], "text": " ".join(record.text.split())}


# ---------------------------------------------------------------- generate and critique

def parse_hypotheses(raw: Any, allowed: set[str]) -> list[dict[str, Any]]:
    out = []
    for entry in (raw.get("hypotheses") if isinstance(raw, dict) else None) or []:
        if not isinstance(entry, dict) or not str(entry.get("hypothesis", "")).strip():
            continue
        filtered, removed = H._filter_citations(entry, allowed)
        try:
            fields = H._schema_only(_validate_generation(filtered, allowed))
        except ValueError:
            continue
        fields["citation_validation"] = {"status": "filtered_unknown_ids" if removed else "valid",
                                         "removed_unknown_ids": removed}
        out.append({"fields": fields, "builds_on": str(entry.get("builds_on", ""))[:600],
                    "what_is_new": str(entry.get("what_is_new", ""))[:600]})
    return out


def shown(hyps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"id": f"H{i + 1}", **{k: v for k, v in hy["fields"].items() if k != "citation_validation"},
             "builds_on": hy["builds_on"], "what_is_new": hy["what_is_new"]} for i, hy in enumerate(hyps)]


def generate(h: Harness, paper_items: list[dict[str, Any]], background: list[dict[str, Any]], allowed: set[str],
             previous: list[dict[str, Any]] | None = None, critique: list[dict[str, Any]] | None = None
             ) -> list[dict[str, Any]]:
    payload: dict[str, Any] = {"research_question": h.query, "knowledge_cutoff": h.cutoff,
                               "paper": paper_items, "background": background}
    if previous:
        payload["previous_hypotheses"] = shown(previous)
        payload["critique"] = critique
    system = GENERATOR_SYSTEM.replace("{k}", str(K))
    for attempt in range(2):
        hyps = parse_hypotheses(h.ask("generator" if not previous else "generator_revise", MODEL, system, payload),
                                allowed)
        if hyps:
            return hyps[:K]
        payload = {**payload, "validation_error": f"Return {K} complete hypotheses as JSON; each needs a non-empty "
                                                  "hypothesis field and record IDs copied from the supplied records."}
    return []


def parse_reviews(raw: Any, n: int) -> list[dict[str, Any]]:
    reviews = [r for r in ((raw.get("reviews") if isinstance(raw, dict) else None) or []) if isinstance(r, dict)]
    by_id = {str(r.get("id", "")).strip().upper(): r for r in reviews}
    out = []
    for i in range(n):
        r = by_id.get(f"H{i + 1}") or (reviews[i] if i < len(reviews) else {})
        verdict = {}
        for c in CRITERIA:
            v = r.get(c) if isinstance(r.get(c), dict) else {}
            verdict[c] = {"pass": v.get("pass") is True, "reason": str(v.get("reason", ""))[:400]}
        out.append({"id": f"H{i + 1}", **verdict, "evidence_quote": str(r.get("evidence_quote", ""))[:500],
                    "fix": str(r.get("fix", ""))[:500],
                    "accepted": all(verdict[c]["pass"] for c in CRITERIA)})
    return out


def critique(h: Harness, paper_items: list[dict[str, Any]], background: list[dict[str, Any]],
             hyps: list[dict[str, Any]], summary: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """The critic's reviews; with a summary dict, also its list of what the paper did, reported and proposed."""
    payload = {"paper": paper_items, "background": background, "hypotheses": shown(hyps)}  # never the question
    raw = h.ask("critic", CRITIC_MODEL, CRITIC_SYSTEM, payload)
    if summary is not None and isinstance(raw, dict):
        for key in ("paper_did", "paper_reported", "paper_proposed"):
            summary[key] = [str(x)[:400] for x in (raw.get(key) or []) if isinstance(raw.get(key), list)][:12]
    return parse_reviews(raw, len(hyps))


def per_paper(h: Harness, paper: dict[str, Any], max_rounds: int = MAX_ROUNDS) -> dict[str, Any]:
    text = paper_text(paper)
    background = text_records(h.query, paper) + kg_records(h, paper)
    records = text + background
    with _seen_lock(h):
        for r in records:
            h.seen[r.record_id] = r
    allowed = {r.record_id for r in records}
    paper_items, bg_items = [item(r) for r in text], [item(r) for r in background]
    log: dict[str, Any] = {"paper": paper["pmcid"], "title": re.sub(r"<[^>]+>", "", str(paper.get("title", "")))[:200],
                           "grade": paper.get("grade"), "paper_chars": sum(len(r.text) for r in text),
                           "background": {"texts": sum(1 for r in background if r.paper_id.startswith("TXT")),
                                          "kg_facts": sum(1 for r in background if r.paper_id == "KG")},
                           "rounds": [], "accepted": []}
    full = getattr(h, "full_log", False)
    if full:
        log["background_items"] = [{"record_id": b["record_id"], "source": b["source"], "section": b["section"],
                                    "text": b["text"][:400]} for b in bg_items]
    hyps = generate(h, paper_items, bg_items, allowed)
    for round_no in range(1, max_rounds + 1):
        if not hyps:
            log["rounds"].append({"round": round_no, "error": "no valid hypotheses"})
            break
        summary: dict[str, Any] = {}
        reviews = critique(h, paper_items, bg_items, hyps, summary if full else None)
        log["rounds"].append({"round": round_no, "verdicts": [
            {"intervention": str(hy["fields"].get("intervention", ""))[:160],
             **{c: rv[c]["pass"] for c in CRITERIA}, "fix": rv["fix"][:300]} for hy, rv in zip(hyps, reviews)]})
        if full:
            log["rounds"][-1].update({"critic_summary": summary, "hypotheses": shown(hyps), "reviews": reviews})
        accepted = [{**hy, "paper": paper["pmcid"], "round": round_no} for hy, rv in zip(hyps, reviews)
                    if rv["accepted"]]
        if accepted:
            log["accepted"] = accepted
            break
        if round_no < max_rounds:
            hyps = generate(h, paper_items, bg_items, allowed, previous=hyps, critique=reviews)
    log["n_rounds"] = len(log["rounds"])
    return log


_SEEN_LOCKS: dict[int, threading.Lock] = {}


def _seen_lock(h: Harness) -> threading.Lock:
    return _SEEN_LOCKS.setdefault(id(h), threading.Lock())


# ---------------------------------------------------------------- narrowing

def _key_words(hy: dict[str, Any]) -> set[str]:
    f = hy["fields"]
    return set(S2.clean_terms(f"{f.get('intervention', '')} {f.get('structural_mediator', '')}"))


def dedupe(pool: list[dict[str, Any]], threshold: float = 0.6) -> list[dict[str, Any]]:
    """Near-duplicates (word Jaccard of intervention + structural mediator >= threshold) keep the first."""
    out: list[dict[str, Any]] = []
    for hy in pool:
        words = _key_words(hy)
        if any(len(words & _key_words(o)) / max(1, len(words | _key_words(o))) >= threshold for o in out):
            continue
        out.append(hy)
    return out


def match(h: Harness, a: dict[str, Any], b: dict[str, Any]) -> float:
    """1.0 if a wins in both orders, 0.0 if b does, else 0.5."""
    picks: list[Any] = []
    reasons: list[dict[str, Any]] = []
    for first, second in ((a, b), (b, a)):
        payload = {"research_question": h.query, "knowledge_cutoff": h.cutoff,
                   "candidate_A": LM.hypothesis_fields(first["fields"]),
                   "candidate_B": LM.hypothesis_fields(second["fields"])}
        raw = h.ask("narrow", NARROW_MODEL, NARROW_SYSTEM, payload, max_out=2500)
        pick = str(raw.get("winner", "")).strip().upper() if isinstance(raw, dict) else ""
        reasons.append({"a_first": first is a, "winner": pick,
                        "reason": str(raw.get("reason", ""))[:500] if isinstance(raw, dict) else ""})
        picks.append(first if pick == "A" else second if pick == "B" else None)
    result = 1.0 if picks[0] is not None and picks[0] is picks[1] and picks[0] is a else \
        0.0 if picks[0] is not None and picks[0] is picks[1] else 0.5
    if getattr(h, "full_log", False):
        with _seen_lock(h):
            h.notes.setdefault("matches", []).append({"a": a.get("label"), "b": b.get("label"), "result": result,
                                                      "reasons": reasons})
    return result


def round_robin(h: Harness, pool: list[dict[str, Any]]) -> list[float]:
    points = [0.0] * len(pool)
    pairs = list(itertools.combinations(range(len(pool)), 2))
    with ThreadPoolExecutor(PAPER_WORKERS) as ex:
        results = list(ex.map(lambda ij: match(h, pool[ij[0]], pool[ij[1]]), pairs))
    for (i, j), r in zip(pairs, results):
        points[i] += r
        points[j] += 1 - r
    return points


def swiss(h: Harness, pool: list[dict[str, Any]], rounds: int = SWISS_ROUNDS) -> list[float]:
    points = [0.0] * len(pool)
    played: set[tuple[int, int]] = set()
    for _ in range(rounds):
        order = sorted(range(len(pool)), key=lambda i: (-points[i], i))
        pairs, free = [], list(order)
        while len(free) > 1:
            i = free.pop(0)
            j = next((j for j in free if (min(i, j), max(i, j)) not in played), free[0])
            free.remove(j)
            pairs.append((i, j))
            played.add((min(i, j), max(i, j)))
        with ThreadPoolExecutor(PAPER_WORKERS) as ex:
            results = list(ex.map(lambda ij: match(h, pool[ij[0]], pool[ij[1]]), pairs))
        for (i, j), r in zip(pairs, results):
            points[i] += r
            points[j] += 1 - r
    return points


def narrow(h: Harness, pool: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if len(pool) == 1:
        return pool, {"format": "single"}
    if len(pool) <= 6:
        points = round_robin(h, pool)
        order = sorted(range(len(pool)), key=lambda i: (-points[i], i))
        return [pool[i] for i in order], {"format": "round_robin", "points": [points[i] for i in order]}
    sw = swiss(h, pool)
    top = sorted(range(len(pool)), key=lambda i: (-sw[i], i))[:FINAL_POOL]
    rr = round_robin(h, [pool[i] for i in top])
    order = sorted(range(len(top)), key=lambda k: (-rr[k], -sw[top[k]], k))
    return [pool[top[k]] for k in order], {"format": "swiss+round_robin", "swiss_points": sw,
                                          "final_points": [rr[k] for k in order]}


# ---------------------------------------------------------------- the method

def m_perpaper(h: Harness, n_papers: int = N_PAPERS, max_rounds: int = MAX_ROUNDS) -> dict[str, Any]:
    h.source = "web"
    papers = select_papers(h, n_papers)
    if not papers:
        raise ValueError("no eligible papers")
    def safe(paper: dict[str, Any]) -> dict[str, Any]:
        try:
            return per_paper(h, paper, max_rounds)
        except H.TargetLeak:
            raise
        except Exception as error:  # noqa: BLE001 - one paper's failure drops that paper, recorded in the notes
            return {"paper": paper["pmcid"], "error": f"{type(error).__name__}: {str(error)[:300]}", "rounds": [],
                    "n_rounds": 0, "accepted": []}

    with ThreadPoolExecutor(min(PAPER_WORKERS, len(papers))) as ex:
        logs = list(ex.map(safe, papers))
    pool = dedupe([hy for log in logs for hy in log["accepted"]])
    h.notes["papers"] = [{k: v for k, v in log.items() if k != "accepted"} | {"n_accepted": len(log["accepted"])}
                         for log in logs]
    h.notes["summary"] = {"papers": len(papers), "papers_with_accepted": sum(bool(lg["accepted"]) for lg in logs),
                          "accepted": sum(len(lg["accepted"]) for lg in logs), "pool_after_dedupe": len(pool),
                          "rounds": [lg["n_rounds"] for lg in logs],
                          "accepted_round_1": sum(bool(lg["accepted"]) and lg["n_rounds"] == 1 for lg in logs)}
    if not pool:
        raise ValueError(f"no hypothesis was accepted for any of {len(papers)} papers")
    for n, hy in enumerate(pool):
        hy["label"] = f"C{n + 1}"
    if getattr(h, "full_log", False):
        h.notes["selected_papers"] = [{"pmcid": p["pmcid"], "title": re.sub(r"<[^>]+>", "", str(p.get("title", ""))),
                                       "doi": p.get("doi"), "date": p.get("date"), "grade": p.get("grade"),
                                       "why_relevant": p.get("why")} for p in papers]
        h.notes["pool"] = [{"label": hy["label"], "paper": hy["paper"], "round": hy["round"],
                            "builds_on": hy["builds_on"], "what_is_new": hy["what_is_new"], "fields": hy["fields"]}
                           for hy in pool]
        h.notes["accepted_before_dedupe"] = sum(len(lg["accepted"]) for lg in logs)
    ranked, tournament = narrow(h, pool)
    points = tournament.get("final_points") or tournament.get("points") or []
    tournament["rank1_tied"] = len(points) > 1 and points[0] == points[1]
    h.notes["tournament"] = tournament
    h.notes["ranking"] = [hy["label"] for hy in ranked]
    h.notes["top3"] = [{"label": hy["label"], "paper": hy["paper"], "round": hy["round"], "builds_on": hy["builds_on"],
                        "what_is_new": hy["what_is_new"], "fields": hy["fields"]} for hy in ranked[:3]]
    return ranked[0]["fields"]


def m_perpaper_full(h: Harness) -> dict[str, Any]:
    """perpaper with every intermediate step kept in the run's notes (loop.md 28.3); the method is unchanged."""
    h.full_log = True
    return m_perpaper(h)


register("perpaper")(m_perpaper)
register("perpaper_full")(m_perpaper_full)
ARMS = ("perpaper", "perpaper_full")
