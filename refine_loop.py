"""Experiment 44 (loop.md 25.1): focused retrieval (R), evidence use with a broad-reasoning prompt (U), and a
multi-critic refinement loop with critique-driven re-retrieval (C), as individual and combined arms.

Arms (o3-mini writer; every arm sees at most 64,000 distinct characters of evidence, rendered with titles and
sections as in experiment 42):
  rx_base         the experiment-42 pack (web64k_r2: experiment-36 corpus, BM25 without template words) + WRITER_B
  rx_r            the focused pack (focused_search.py) + WRITER_B
  rx_u            the rx_base pack + a literature map (digest) + the broad-reasoning writer
  rx_ru           the focused pack + digest + broad writer
  rx_c            the rx_base pack (48,000) + K candidates + the critique loop (re-retrieval: BM25 over the same corpus)
  rx_ruc_select   the focused pack (48,000) + digest + K broad candidates + one critique round; no revision
  rx_ruc          the focused pack (48,000) + digest + K broad candidates + the critique loop (re-retrieval: live
                  focused search)
The critique loop: three critics of different families (o1, gpt-4o, Llama-3.3-70B; all pre-cutoff) review every
candidate (seeded shuffled order, neutral labels, the passages each candidate cites). Each critic's mean scores are
turned into ranks; candidates are ordered by being "fine" (at least two critics see no major issue and score no
criterion below 4), then by mean rank, then by mean score. While the best is not fine, a planner (gpt-4o) turns the
reviewers' evidence needs into searches (including searches that could refute the candidates), at most 8,000 new
characters of evidence are retrieved, and the writer revises the set; the previous best stays in the next round
unchanged. Every run revises at least once; after that it stops when the best is fine, when the previous best wins
again, or after three critique rounds.
"""

from __future__ import annotations

import json
import statistics
from typing import Any

import focused_search as FS
import hypo_loop as H
import loop_methods as LM
import rubric_eval as rx
import stage_v2 as S2
from hypo_loop import Harness, register
from temporal_hypothesis_benchmark import _validate_generation

SCHEMA = LM.SCHEMA
K = 4
CRITICS = ("o1", "4o", "llama")
CRITIC_MAX_OUT = {"o1": 20000, "4o": 8000}  # Llama keeps its registered cap (hypo_loop.MODELS)
CRITERIA = ("soundness", "fit", "specificity", "evidence", "significance")
MAX_ROUNDS = 3
MIN_REVISIONS = 1  # the smoke test: lenient critics judged round 1 fine in 4 of 4 runs, so the loop never ran
BUDGET = 64000  # the evidence budget of web_text_64k_b_o3mini and web64k_r2_b_o3mini (= focused_search.BUDGET)
LOOP_START, REVISION_BUDGET = 48000, 8000  # C arms: 48,000 + two revisions x 8,000 <= 64,000 distinct characters
CITED_SHOWN, CITED_PER_CANDIDATE = 700, 4
PLANNER = "4o"

CANDIDATES_B = (
    "You are a materials-science hypothesis agent in a chronological benchmark. Use any supplied temporally eligible "
    "evidence. Do not claim knowledge of the held-out paper. Write {k} distinct candidate hypotheses that answer the "
    "question; they must differ in their intervention or in their mechanism. Predict the direction and approximate "
    "size of effects only as far as the evidence and your knowledge support; if support is insufficient, state the "
    "uncertainty instead of inventing support or precise values.\n\n"
    "Return JSON {\"hypotheses\": [...]} with {k} items, each with all fields of:\n" + SCHEMA +
    "\nEvidence IDs must be copied from the supplied records."
)
DIGEST_SYSTEM = (
    "You are a materials scientist preparing to answer a research question. Read the supplied evidence: passages from "
    "earlier papers, all published before the knowledge cutoff, each with its paper's title and section. Write a "
    "literature map for the question; do not write a hypothesis yet.\n"
    "- For each paper that bears on the question: the material system and approach it studied, what it found (with "
    "the conditions), the mechanism it proposes, and the record IDs.\n"
    "- Across papers: (1) established facts the question can build on; (2) approaches already tried for this kind "
    "of limitation, and how well they worked; (3) the mechanisms in play, and where papers disagree; (4) what is "
    "still open or untested; (5) concrete opportunities the evidence suggests (combinations, conditions or systems "
    "not yet tried, and future work the authors propose).\n"
    "Return JSON {\"papers\": [{\"title\": str, \"system\": str, \"approach\": str, \"findings\": str, "
    "\"mechanism\": str, \"record_ids\": [str]}], \"established\": [str], \"approaches_tried\": [{\"approach\": str, "
    "\"outcome\": str, \"record_ids\": [str]}], \"mechanisms\": [str], \"disagreements\": [str], "
    "\"open_questions\": [str], \"opportunities\": [str]}."
)
_BROAD = (
    "You are a materials scientist proposing the next study for a research question. You receive the question, the "
    "knowledge cutoff, your own literature map of earlier papers and the evidence it was built from (all published "
    "before the cutoff). Think broadly before you commit. The evidence informs your choice but does not limit it: "
    "draw on everything you know about materials science from before the cutoff. First consider at least five "
    "distinct directions that could answer the question, across the kinds of intervention or study that make sense "
    "for it (composition design, processing or synthesis route, heat or thermomechanical treatment and "
    "microstructure control, surface or coating, characterisation or mechanism study, modelling or simulation). For "
    "each, judge how directly it attacks the limitation the question states, whether it respects every constraint, "
    "how well known physics and the evidence support it, and how feasible and informative the study would be. "
)
_WRITE = (
    "the material and its starting state, the intervention with its key parameters, the conditions, the structural "
    "mediator, the mechanism, and the predicted outcome relative to a baseline, with approximate magnitudes where "
    "your knowledge or the evidence supports them. Do not present invented measured values as established facts. Do "
    "not claim knowledge of the held-out paper. Cite record IDs that support specific statements.\n\n"
)
BROAD_WRITER = (
    _BROAD + "Then choose the direction a strong research group would pursue, and write it as one specific, "
    "falsifiable hypothesis: " + _WRITE + "Return JSON with \"directions\": [{\"direction\": str, \"type\": str, "
    "\"assessment\": str}], \"choice\": {\"direction\": str, \"why\": str}, and all fields of:\n" + SCHEMA +
    "\nEvidence IDs must be copied from the supplied records."
)
BROAD_CANDIDATES = (
    _BROAD + "Then choose the {k} most promising directions and write each as a distinct, specific, falsifiable "
    "hypothesis: " + _WRITE + "Return JSON {\"directions\": [{\"direction\": str, \"type\": str, \"assessment\": "
    "str}], \"hypotheses\": [...]} with {k} hypotheses, each with all fields of:\n" + SCHEMA +
    "\nEvidence IDs must be copied from the supplied records."
)
CRITIC_SYSTEM = (
    "You are one of several independent expert reviewers of candidate research hypotheses on high-temperature "
    "high-entropy alloys. You receive a research question, a knowledge cutoff, candidate hypotheses labelled A, B, "
    "..., and, for each candidate, the earlier-literature passages it cites (all published before the cutoff). Review "
    "every candidate on its own merits, with the knowledge you had before the cutoff, on five criteria:\n"
    "1. soundness: is the mechanism physically correct for this material system and regime, and are the claims "
    "consistent with established materials science?\n"
    "2. fit: does it attack the limitation or open question the question states, and respect every stated "
    "constraint?\n"
    "3. specificity: are the material, intervention, parameters, conditions and predicted outcome concrete, and "
    "would the proposed experiment decide the hypothesis?\n"
    "4. evidence: are its claims consistent with the cited passages and with prior work you know, and are the "
    "citations used correctly?\n"
    "5. significance: would the result matter to researchers working on this question?\n"
    "Score each criterion from 1 (serious problem) to 5 (excellent). List major issues (errors that would make the "
    "study fail or mislead), minor issues, concrete fixes, and evidence needs: specific facts or earlier results to "
    "look up in the literature that would settle a doubt about the candidate or could refute it. Be rigorous and "
    "specific, and do not reward length. Return JSON {\"reviews\": [{\"id\": \"A\", \"scores\": {\"soundness\": "
    "int, \"fit\": int, \"specificity\": int, \"evidence\": int, \"significance\": int}, \"major_issues\": [str], "
    "\"minor_issues\": [str], \"fixes\": [str], \"evidence_needs\": [str]}]} with one review per candidate."
)
FOLLOWUP_PLAN = (
    "You plan literature searches to settle reviewers' doubts about candidate hypotheses for a materials-science "
    "research question. Use only the inputs and knowledge from before the knowledge cutoff. Write the concepts to "
    "search for as groups of short search phrases (1 to 4 words each, as they would appear in titles or abstracts, "
    "with synonyms): the material systems involved, and the specific properties, mechanisms, phenomena, compositions "
    "or methods the doubts concern. Include searches that could find evidence against the candidates, not only for "
    "them. Then write 3 to 6 searches, each an AND of 2 or 3 of your group names, and a one-sentence purpose. Return "
    "JSON {\"groups\": {group name: [phrases]}, \"searches\": [[group names], ...], \"purpose\": str}, where "
    "each search is a plain list of group names, for example [\"material\", \"phase_stability\"]."
)
REVISE_SYSTEM = (
    "You wrote the candidate hypotheses below for a materials-science research question. Independent reviewers have "
    "critiqued them, and new evidence was retrieved to address their doubts (all evidence is published before the "
    "knowledge cutoff). Revise the candidates: fix every major issue the reviewers raise and adopt the fixes you find "
    "sound; if a reviewer is wrong, keep your position and explain why in the uncertainty field; replace a candidate "
    "that is fundamentally flawed with a new, distinct one. Keep {k} candidates that differ in their intervention or "
    "mechanism. Keep each hypothesis specific and decisive: fixing a problem must not turn it into a vague or hedged "
    "statement. Use the evidence and your knowledge from before the cutoff; never claim knowledge of later work.\n\n"
    "Return JSON {\"hypotheses\": [...]} with {k} items, each with \"revises\": the label of the candidate it "
    "revises or \"new\", \"changes\": what changed and why, and all fields of:\n" + SCHEMA +
    "\nEvidence IDs must be copied from the supplied records."
)


def with_k(system: str, k: int = K) -> str:
    return system.replace("{k}", str(k))


# ---------------------------------------------------------------- evidence

def fit_budget(records: list[Any], budget: int) -> list[Any]:
    """A prefix of an ordered pack that fits the budget (sizes as sent, title and section included)."""
    cap = rx.record_cap("text_chunks")
    out, used = [], 0
    for record in records:
        size = LM.v2_item_size(LM.v2_item(record, cap))
        if used + size > budget:
            break
        out.append(record)
        used += size
    return out


def start_pack(h: Harness, focused: bool, budget: int) -> list[Any]:
    h.source = "web"
    if focused:
        records = fit_budget(FS.pack_records(h.case["paper_id"], h.level), budget)
        manifest = FS.build(h.case["paper_id"], h.level)
        for role, model in manifest["models"].items():
            h.models.setdefault(f"focused_{role}", model)
    else:
        records = LM.r2_pack(h, budget)
    for record in records:
        h.seen[record.record_id] = record
    h.notes["evidence"] = {"source": "focused" if focused else "r2", "records": len(records),
                           "papers": len({r.paper_id for r in records}), "budget": budget}
    return records


def items(h: Harness, records: list[Any]) -> list[dict[str, Any]]:
    return LM.evidence_payload_v2(h, records, rx.record_cap("text_chunks"))


def digest(h: Harness, records: list[Any]) -> dict[str, Any]:
    raw = h.ask("digest", "o3mini", DIGEST_SYSTEM, {"query": h.query, "knowledge_cutoff": h.cutoff,
                                                    "eligible_evidence": items(h, records)})
    raw = raw if isinstance(raw, dict) else {}
    h.notes["literature_map"] = raw
    return raw


# ---------------------------------------------------------------- candidates

def parse_candidates(raw: Any, allowed: set[str]) -> list[dict[str, Any]]:
    """Valid full-schema candidates; unknown citation IDs are removed and recorded (experiment 42 repair)."""
    out = []
    for item in (raw.get("hypotheses") if isinstance(raw, dict) else None) or []:
        if not isinstance(item, dict) or not str(item.get("hypothesis", "")).strip():
            continue
        filtered, removed = H._filter_citations(item, allowed)
        try:
            candidate = H._schema_only(_validate_generation(filtered, allowed))
        except ValueError:
            continue
        candidate["citation_validation"] = {"status": "filtered_unknown_ids" if removed else "valid",
                                            "removed_unknown_ids": removed}
        out.append({"fields": candidate, "revises": str(item.get("revises", "")), "changes": str(item.get("changes",
                                                                                                       ""))[:600]})
    return out


def initial_candidates(h: Harness, records: list[Any], broad: bool, literature_map: dict[str, Any] | None
                       ) -> list[dict[str, Any]]:
    payload: dict[str, Any] = {"query": h.query, "knowledge_cutoff": h.cutoff}
    if broad:
        payload["literature_map"] = literature_map or {}
    payload["eligible_evidence"] = items(h, records)
    allowed = {r.record_id for r in records}
    system = with_k(BROAD_CANDIDATES if broad else CANDIDATES_B)
    raw = h.ask("candidates", "o3mini", system, payload)
    candidates = parse_candidates(raw, allowed)
    if len(candidates) < 2:
        retry = {**payload, "validation_error": f"Return {K} complete hypotheses; each needs a non-empty hypothesis "
                                                f"field and evidence IDs copied from the supplied records."}
        raw = h.ask("candidates_retry", "o3mini", system, retry)
        candidates = parse_candidates(raw, allowed)
    if not candidates:
        raise ValueError("no valid candidate hypotheses")
    if broad and isinstance(raw, dict):
        h.notes["directions"] = raw.get("directions")
    return candidates[:K]


# ---------------------------------------------------------------- critique

def shown_candidate(h: Harness, candidate: dict[str, Any]) -> dict[str, Any]:
    """A candidate as a critic sees it: its fields without record IDs, and the text of the passages it cites."""
    fields = {k: v for k, v in candidate["fields"].items()
              if k not in ("supporting_evidence_ids", "conflicting_evidence_ids", "citation_validation")}
    cited = (candidate["fields"].get("supporting_evidence_ids") or []) + \
        (candidate["fields"].get("conflicting_evidence_ids") or [])
    passages = []
    for rid in cited[:CITED_PER_CANDIDATE]:
        record = h.seen.get(rid)
        if record is not None:
            passages.append({"paper_title": str((record.structured or {}).get("title", ""))[:150],
                             "text": " ".join(record.text.split())[:CITED_SHOWN]})
    return {**fields, "cited_passages": passages}


def parse_reviews(raw: Any, labels: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in (raw.get("reviews") if isinstance(raw, dict) else None) or []:
        if not isinstance(item, dict) or str(item.get("id", "")).strip().upper() not in labels:
            continue
        scores_raw = item.get("scores") if isinstance(item.get("scores"), dict) else {}
        scores = {}
        for criterion in CRITERIA:
            try:
                value = int(scores_raw.get(criterion))
            except (TypeError, ValueError):
                value = None
            if value is not None and 1 <= value <= 5:
                scores[criterion] = value
        if len(scores) != len(CRITERIA):
            continue
        lists = {k: [str(x)[:400] for x in (item.get(k) or []) if str(x).strip()][:6]
                 for k in ("major_issues", "minor_issues", "fixes", "evidence_needs")}
        out[str(item["id"]).strip().upper()] = {"scores": scores, **lists}
    return out


def critique(h: Harness, candidates: list[dict[str, Any]], round_no: int) -> dict[str, dict[str, dict[str, Any]]]:
    """critic -> candidate index (as str) -> review. Each critic sees its own seeded order with labels A, B, ..."""
    reviews: dict[str, dict[str, dict[str, Any]]] = {}
    shown = [shown_candidate(h, c) for c in candidates]
    for critic in CRITICS:
        order = list(range(len(candidates)))
        h.rng.shuffle(order)
        labels = [chr(ord("A") + pos) for pos in range(len(order))]
        payload = {"question": h.query, "knowledge_cutoff": h.cutoff,
                   "candidates": [{"id": labels[pos], **shown[n]} for pos, n in enumerate(order)]}
        parsed = parse_reviews(h.ask(f"critic_{critic}_r{round_no}", critic, CRITIC_SYSTEM, payload,
                                     max_out=CRITIC_MAX_OUT.get(critic)), labels)
        reviews[critic] = {str(order[pos]): parsed[labels[pos]] for pos in range(len(order)) if labels[pos] in parsed}
    return reviews


def _ranks(values: dict[str, float]) -> dict[str, float]:
    """1 = best; ties get their mean rank."""
    ordered = sorted(values, key=lambda k: -values[k])
    out: dict[str, float] = {}
    i = 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and values[ordered[j + 1]] == values[ordered[i]]:
            j += 1
        for k in ordered[i:j + 1]:
            out[k] = (i + j) / 2 + 1
        i = j + 1
    return out


def aggregate(reviews: dict[str, dict[str, dict[str, Any]]], n: int) -> list[dict[str, Any]]:
    """Per candidate: mean rank over critics (each critic ranks by its own mean score), mean score, fine (at least
    two critics see no major issue and no criterion below 4); sorted best first."""
    keys = [str(i) for i in range(n)]
    ranks: dict[str, list[float]] = {k: [] for k in keys}
    means: dict[str, list[float]] = {k: [] for k in keys}
    clean: dict[str, int] = {k: 0 for k in keys}
    for critic, by_key in reviews.items():
        critic_means = {k: statistics.fmean(r["scores"].values()) for k, r in by_key.items()}
        for k, rank in _ranks(critic_means).items():
            ranks[k].append(rank)
            means[k].append(critic_means[k])
            review = by_key[k]
            clean[k] += int(not review["major_issues"] and min(review["scores"].values()) >= 4)
    out = [{"index": int(k), "mean_rank": statistics.fmean(ranks[k]) if ranks[k] else float(n + 1),
            "mean_score": statistics.fmean(means[k]) if means[k] else 0.0, "critics": len(ranks[k]),
            "fine": clean[k] >= 2} for k in keys]
    out.sort(key=lambda a: (not a["fine"], a["mean_rank"], -a["mean_score"], a["index"]))
    return out


def feedback(reviews: dict[str, dict[str, dict[str, Any]]], index: int, h: Harness) -> list[dict[str, Any]]:
    """The reviews of one candidate, anonymised as Reviewer 1-3 in a seeded order."""
    critics = [c for c in reviews if str(index) in reviews[c]]
    h.rng.shuffle(critics)
    return [{"reviewer": f"Reviewer {n + 1}", **reviews[c][str(index)]} for n, c in enumerate(critics)]


# ---------------------------------------------------------------- re-retrieval and revision

def needs_text(reviews: dict[str, dict[str, dict[str, Any]]], ranked: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for entry in ranked[:2]:
        for critic in reviews:
            review = reviews[critic].get(str(entry["index"]))
            if review:
                out += review["evidence_needs"] + review["major_issues"]
    return list(dict.fromkeys(out))[:16]


def re_retrieve(h: Harness, candidates: list[dict[str, Any]], needs: list[str], focused: bool, round_no: int
                ) -> list[Any]:
    payload = {"question": h.query, "knowledge_cutoff": h.cutoff,
               "candidates": [{"hypothesis": c["fields"].get("hypothesis"), "intervention":
                               c["fields"].get("intervention"), "mechanism": c["fields"].get("mechanism")}
                              for c in candidates],
               "reviewer_doubts": needs}
    raw = h.ask(f"followup_planner_r{round_no}", PLANNER, FOLLOWUP_PLAN, payload, max_out=3000)
    plan = FS.parse_plan(raw)
    purpose = str((raw or {}).get("purpose", "") if isinstance(raw, dict) else "")[:300]
    log: dict[str, Any] = {"round": round_no, "plan": plan, "purpose": purpose, "needs": needs}
    if focused:
        records: list[Any] = []
        if plan["searches"]:
            records, search_log = FS.followup(h, plan, purpose, {r.paper_id for r in h.seen.values()}, set(h.seen),
                                              REVISION_BUDGET, max_papers=6)
            log["search"] = search_log
        else:
            log["search"] = {"backend": "focused", "error": "no usable search in the plan"}
    else:
        terms = FS.plan_terms(plan["groups"]) + S2.clean_terms(" ".join([purpose] + needs))
        pool = [r for r in h.pool("text_chunks") if r.record_id not in h.seen]
        scores = S2.bm25_scores(terms, {r.record_id: S2.clean_terms(r.text) for r in pool})
        ranked = sorted((r for r in pool if scores.get(r.record_id, 0.0) > 0),
                        key=lambda r: (-scores[r.record_id], r.record_id))
        records = fit_budget(ranked, REVISION_BUDGET)
        log["search"] = {"backend": "bm25_experiment36_corpus", "candidates": len(ranked)}
    for record in records:
        h.seen[record.record_id] = record
    log["added"] = [r.record_id for r in records]
    h.notes.setdefault("re_retrieval", []).append(log)
    return records


def revise(h: Harness, candidates: list[dict[str, Any]], reviews: dict[str, dict[str, dict[str, Any]]],
           records: list[Any], new_records: list[Any], literature_map: dict[str, Any] | None, round_no: int
           ) -> list[dict[str, Any]]:
    order = list(range(len(candidates)))
    h.rng.shuffle(order)
    labels = [chr(ord("A") + pos) for pos in range(len(order))]
    payload: dict[str, Any] = {"query": h.query, "knowledge_cutoff": h.cutoff}
    if literature_map is not None:
        payload["literature_map"] = literature_map
    payload["eligible_evidence"] = items(h, records)
    payload["new_evidence_ids"] = [r.record_id for r in new_records]
    payload["candidates"] = [{"label": labels[pos], **{k: v for k, v in candidates[n]["fields"].items()
                                                         if k != "citation_validation"},
                              "reviews": feedback(reviews, n, h)} for pos, n in enumerate(order)]
    allowed = {r.record_id for r in records}
    revised = parse_candidates(h.ask(f"reviser_r{round_no}", "o3mini", with_k(REVISE_SYSTEM), payload), allowed)
    for c in revised:
        if c["revises"].upper() in labels:
            c["revises"] = f"r{round_no - 1}:{order[labels.index(c['revises'].upper())]}"
    return revised[:K]


def summary(candidate: dict[str, Any]) -> dict[str, Any]:
    f = candidate["fields"]
    return {"hypothesis": f.get("hypothesis"), "intervention": f.get("intervention"),
            "revises": candidate.get("revises", ""), "changes": candidate.get("changes", "")}


def critique_loop(h: Harness, records: list[Any], candidates: list[dict[str, Any]], focused: bool,
                  literature_map: dict[str, Any] | None, revise_rounds: bool) -> dict[str, Any]:
    rounds: list[dict[str, Any]] = []
    stop = "max_rounds"
    best: dict[str, Any] | None = None
    for round_no in range(1, MAX_ROUNDS + 1):
        reviews = critique(h, candidates, round_no)
        ranked = aggregate(reviews, len(candidates))
        winner = candidates[ranked[0]["index"]]
        rounds.append({"round": round_no, "candidates": [summary(c) for c in candidates], "reviews": reviews,
                       "ranking": ranked})
        parent_won = best is not None and winner is best
        best = winner
        if not revise_rounds:
            stop = "select_only"
            break
        if round_no > MIN_REVISIONS:  # every loop run revises at least MIN_REVISIONS times (loop.md 25.1)
            if ranked[0]["fine"]:
                stop = "fine"
                break
            if parent_won:
                stop = "no_improvement"
                break
        if round_no == MAX_ROUNDS:
            break
        new_records = re_retrieve(h, candidates, needs_text(reviews, ranked), focused, round_no)
        records = records + new_records
        revised = revise(h, candidates, reviews, records, new_records, literature_map, round_no + 1)
        if not revised:
            stop = "revision_failed"
            break
        # The previous best stays eligible, unchanged, and first: it wins ties, so the loop moves on only when a
        # revision is ranked strictly better.
        candidates = [best] + revised
    h.notes["loop"] = {"rounds": rounds, "stop": stop, "critique_rounds": len(rounds),
                       "final_fine": bool(rounds[-1]["ranking"][0]["fine"])}
    return dict(best["fields"])


def write_final(h: Harness, system: str, payload: dict[str, Any], allowed: set[str], keep: tuple[str, ...]
                ) -> dict[str, Any]:
    """Harness.generate_final, keeping the listed non-schema fields of the answer in the run's notes."""
    raw = h.ask("writer", "o3mini", system, payload)
    if isinstance(raw, dict):
        for key in keep:
            if key in raw:
                h.notes[key] = raw[key]
    try:
        filtered, removed = H._filter_citations(raw, allowed)
        out = H._schema_only(_validate_generation(filtered, allowed))
        out["citation_validation"] = {"status": "filtered_unknown_ids" if removed else "valid",
                                      "removed_unknown_ids": removed}
        return out
    except (ValueError, AttributeError, TypeError):
        return h.generate_final("writer_retry", "o3mini", system, payload, allowed, citation_repair="filter")


# ---------------------------------------------------------------- the arms

def m_rx(h: Harness, focused: bool, broad: bool, loop: str) -> dict[str, Any]:
    """loop: "none", "select" (one critique round, no revision) or "full"."""
    if loop == "none":
        records = start_pack(h, focused, BUDGET)
        allowed = {r.record_id for r in records}
        if broad:
            literature_map = digest(h, records)
            payload = {"query": h.query, "knowledge_cutoff": h.cutoff, "literature_map": literature_map,
                       "eligible_evidence": items(h, records)}
            out = write_final(h, BROAD_WRITER, payload, allowed, ("directions", "choice"))
        else:
            payload = {"query": h.query, "knowledge_cutoff": h.cutoff, "analysis_notes": {},
                       "eligible_evidence": items(h, records)}
            out = h.generate_final("writer", "o3mini", LM.WRITER_B, payload, allowed, citation_repair="filter")
        return out
    records = start_pack(h, focused, LOOP_START)
    literature_map = digest(h, records) if broad else None
    candidates = initial_candidates(h, records, broad, literature_map)
    return critique_loop(h, records, candidates, focused, literature_map, revise_rounds=loop == "full")


ARMS = {"rx_base": (False, False, "none"), "rx_r": (True, False, "none"), "rx_u": (False, True, "none"),
        "rx_ru": (True, True, "none"), "rx_c": (False, False, "full"), "rx_ruc_select": (True, True, "select"),
        "rx_ruc": (True, True, "full")}
for _name, (_focused, _broad, _loop) in ARMS.items():
    register(_name)(lambda h, _f=_focused, _b=_broad, _l=_loop: m_rx(h, _f, _b, _l))
RX_ARMS = tuple(ARMS)


def describe() -> str:
    return json.dumps({name: {"focused": f, "broad": b, "loop": lp} for name, (f, b, lp) in ARMS.items()})
