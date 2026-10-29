"""Methods for the loop harness (loop.md). Each method is a code-controlled workflow ("own your control flow"):
the harness decides the steps, the pre-cutoff model fills them, and every call goes through Harness.ask (guarded,
logged). Sources for each idea are cited in loop.md; the implementations here are our own.

Method families (iteration numbers refer to loop.md):
  L0  writer_only         control: the method writer prompt alone, closed-book (isolates the writer prompt)
  L1  frame_decide        problem frame -> family map with cue-based fit -> code picks the family -> write
  L2  breadth_tournament  one candidate per top family (separate contexts) -> both-order pairwise tournament -> winner
  L3  precedent_decide    L1 plus a precedent table from earlier papers (problem -> lever -> outcome) as a prior
  L4  verify_repair       deterministic checks + pre-cutoff verifier on a draft, one repair pass
  L7  decide_then_ground  L1 decision, then retrieval aimed at the chosen lever, then a cited write-up
"""

from __future__ import annotations

import itertools
import json
import re
from typing import Any

import rubric_eval as rx
from hypo_loop import Harness, register

GEN = "llama"  # default query-facing model for this iteration (pre-cutoff); variants override it

SCHEMA = """{
  "hypothesis": "",
  "material_initial_state": "",
  "intervention": "",
  "conditions": "",
  "structural_mediator": "",
  "mechanism": "",
  "predicted_outcome": "",
  "baseline": "",
  "boundary": "",
  "uncertainty": "",
  "supporting_evidence_ids": [],
  "conflicting_evidence_ids": [],
  "falsification_experiment": {"design": "", "measurements": [], "falsification_rule": ""}
}"""
WRITER_SYSTEM = (
    "You are a materials-science hypothesis agent in a chronological benchmark. You receive a research question, a "
    "knowledge cutoff, optionally your own analysis notes from earlier steps, and optionally earlier literature "
    "records published before the cutoff. Write one specific, falsifiable hypothesis that answers the question. If "
    "the notes name a chosen family or lever, the hypothesis must use it. Use materials-science knowledge from before "
    "the cutoff; never claim knowledge of later work. Name the exact material state, the intervention or study with "
    "its key parameters, the structural mediator and the mechanism. Quantify the predicted outcome with units "
    "relative to a named baseline, and give a falsification rule with a numeric threshold. Put doubts only in the "
    "uncertainty field. Cite only supplied record IDs that support specific statements; leave the ID lists empty if "
    "no records are supplied. Return JSON:\n" + SCHEMA
)
# Iteration-1 lesson (loop.md): the quantification demands in WRITER_SYSTEM cost 0.27 outcome agreement, because the
# judge penalises invented exact numbers. WRITER_B keeps the baseline's conservative style and adds the notes.
WRITER_B = (
    "You are a materials-science hypothesis agent in a chronological benchmark. Use the supplied analysis notes "
    "(your own earlier reasoning about this question) and any supplied temporally eligible evidence. Do not claim "
    "knowledge of the held-out paper. If the notes name a chosen family and lever, build the hypothesis on them. "
    "Predict the direction and approximate size of effects only as far as the notes and evidence support; if support "
    "is insufficient, state the uncertainty instead of inventing support or precise values.\n\n"
    "Return one falsifiable hypothesis as JSON:\n" + SCHEMA + "\nEvidence IDs must be copied from the supplied records."
)
FRAME_SYSTEM = (
    "You analyse a materials-science research question before anyone proposes a hypothesis. Use only the question "
    "and general materials-science knowledge from before the knowledge cutoff. Return JSON {\"system\": the material "
    "system and its starting state, \"goal\": the property or understanding goal, \"limitation\": the stated "
    "limitation or open question, \"root_cause_cues\": [phrases from the question that indicate what causes the "
    "limitation or what is unknown], \"constraints\": [every explicit constraint or requirement], \"regime\": "
    "operating or test conditions, \"prior_attempts\": [earlier approaches the question mentions and why they fell "
    "short], \"gap_type\": \"design\" (a property to improve), \"understanding\" (a behaviour or mechanism to "
    "explain) or \"method\" (a better method, model or measurement)}."
)
FAMILIES = {
    "design": ("composition_change", "processing_or_synthesis_route", "thermal_or_thermomechanical_treatment",
               "microstructure_architecture", "surface_or_interface_engineering"),
    "understanding": ("controlled_variable_experiment", "in_situ_or_advanced_characterization",
                      "atomistic_or_mesoscale_simulation", "combined_experiment_and_simulation"),
    "method": ("new_computational_method_or_potential", "new_sampling_or_free_energy_scheme",
               "new_measurement_method", "data_driven_or_machine_learning_model"),
}
FAMILY_SYSTEM = (
    "You map a research problem to the families of answers that could address it. Input: the question, its frame "
    "and the candidate families for its gap type. For each family give the governing physical principle it would act "
    "on, the phrases in the question that point to it and against it, how the earlier attempts mentioned in the "
    "question bear on it, its fit from 0 (contradicted or irrelevant) to 5 (the question's cues point directly to "
    "it), and the most promising specific lever in that family for this exact system. Score fit only from the cues in "
    "the question; do not favour any family by habit (alloying additions are not a default). Return JSON "
    "{\"families\": [{\"family\": str, \"principle\": str, \"cues_for\": [str], \"cues_against\": [str], "
    "\"fit\": int, \"best_lever\": str}]}."
)
TOURNAMENT_SYSTEM = (
    "You are a senior materials scientist comparing two candidate hypotheses written for the same research question. "
    "You do not know which, if either, is correct, and you must not guess which paper the question comes from. "
    "Choose the candidate that a competent research group facing exactly this question would most plausibly pursue "
    "and succeed with: it attacks the limitation or open question the question states (its root cause), satisfies "
    "every stated constraint, uses a mechanism that is physically sound for this specific material system and "
    "regime, builds sensibly on the earlier attempts the question mentions, is feasible with standard methods, and "
    "makes a decisive, quantified prediction. Ignore length and style. Return JSON {\"winner\": \"A\" or \"B\", "
    "\"reason\": str}."
)
PRECEDENT_SYSTEM = (
    "You read summaries of earlier materials-science papers (all published before the knowledge cutoff) to learn how "
    "researchers have attacked problems similar to a new research question. For each summary that addresses a "
    "similar limitation, material class or open question, give the problem it addressed, the family of answer it used "
    "(one of the listed families), the specific lever, and the outcome. Ignore summaries that are not similar. "
    "Return JSON {\"precedents\": [{\"record_id\": str, \"problem\": str, \"family\": str, \"lever\": str, "
    "\"outcome\": str, \"similarity\": 1|2|3}]}."
)
VERIFY_SYSTEM = (
    "You check a draft materials-science hypothesis against the research question it answers, before it is "
    "submitted. You do not know the true answer. List concrete problems: constraints in the question that the draft "
    "ignores or violates; the stated limitation or open question not actually addressed; physically implausible or "
    "internally inconsistent claims for this material system; predictions without units or numbers; a falsification "
    "rule without a numeric threshold or without a control; vague or hedged claims. Return JSON {\"problems\": "
    "[{\"field\": str, \"issue\": str, \"fix\": str}], \"verdict\": \"pass\" or \"revise\"}."
)
REPAIR_SYSTEM = WRITER_SYSTEM + (
    "\nYou are revising your own draft: fix every listed problem that is valid, keep the draft's chosen intervention "
    "or study unless a problem shows it violates the question, and return the complete revised JSON."
)
NUMBER = re.compile(r"\d")


# ---------------------------------------------------------------- shared steps

def frame(h: Harness, model: str = GEN) -> dict[str, Any]:
    raw = h.ask("framer", model, FRAME_SYSTEM, {"question": h.query, "knowledge_cutoff": h.cutoff}, max_out=4000)
    raw = raw if isinstance(raw, dict) else {}
    gap = str(raw.get("gap_type", "design")).lower()
    raw["gap_type"] = gap if gap in FAMILIES else "design"
    h.notes["frame"] = raw
    return raw


def family_map(h: Harness, fr: dict[str, Any], model: str = GEN, precedents: list[dict[str, Any]] | None = None
               ) -> list[dict[str, Any]]:
    payload: dict[str, Any] = {"question": h.query, "knowledge_cutoff": h.cutoff, "frame": fr,
                               "candidate_families": list(FAMILIES[fr["gap_type"]])}
    if precedents is not None:
        payload["precedents_from_earlier_papers"] = precedents
        payload["precedent_instruction"] = ("Earlier papers on similar problems used these families; treat a family "
                                            "with close precedents as more likely, but the question's cues decide.")
    raw = h.ask("family_mapper", model, FAMILY_SYSTEM, payload, max_out=6000)
    items = [f for f in (raw.get("families", []) if isinstance(raw, dict) else []) if isinstance(f, dict)]
    allowed = FAMILIES[fr["gap_type"]]
    ranked = []
    for order, item in enumerate(items):
        if str(item.get("family")) not in allowed:
            continue
        try:
            fit = max(0, min(5, int(item.get("fit", 0))))
        except (TypeError, ValueError):
            fit = 0
        ranked.append({**item, "fit": fit, "order": order})
    if not ranked:
        ranked = [{"family": allowed[0], "fit": 0, "order": 0, "best_lever": "", "principle": ""}]
    ranked.sort(key=lambda f: (-f["fit"], f["order"]))
    h.notes["families"] = ranked
    return ranked


def write(h: Harness, notes: dict[str, Any], model: str = GEN, records: list[Any] | None = None,
          role: str = "writer", system: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"query": h.query, "knowledge_cutoff": h.cutoff, "analysis_notes": notes}
    allowed: set[str] = set()
    if records:
        payload["eligible_evidence"] = h.evidence_payload(records, rx.record_cap("text_chunks"))
        allowed = {r.record_id for r in records}
    else:
        payload["eligible_evidence"] = []
    return h.generate_final(role, model, system or WRITER_SYSTEM, payload, allowed)


def hypothesis_fields(g: dict[str, Any]) -> dict[str, Any]:
    return {k: g.get(k) for k in ("hypothesis", "material_initial_state", "intervention", "conditions",
                                  "structural_mediator", "mechanism", "predicted_outcome", "baseline", "boundary",
                                  "falsification_experiment")}


def chosen(fam: dict[str, Any]) -> dict[str, Any]:
    return {"chosen_family": fam["family"], "lever": fam.get("best_lever", ""), "principle": fam.get("principle", ""),
            "why": fam.get("cues_for", [])}


# ---------------------------------------------------------------- L0: writer prompt alone (control)

@register("writer_only")
def m_writer_only(h: Harness) -> dict[str, Any]:
    return write(h, {})


# ---------------------------------------------------------------- L1: frame -> family map -> decide -> write

@register("frame_decide")
def m_frame_decide(h: Harness, model: str = GEN) -> dict[str, Any]:
    fr = frame(h, model)
    fams = family_map(h, fr, model)
    notes = {"frame": fr, **chosen(fams[0])}
    h.notes["decision"] = notes
    return write(h, notes, model)


# ---------------------------------------------------------------- L2: breadth -> both-order tournament

def tournament(h: Harness, candidates: list[dict[str, Any]], model: str) -> list[float]:
    """Round robin, each pair judged in both orders; a pair point counts only if both orders agree (else 0.5 each)."""
    wins = [0.0] * len(candidates)
    for i, j in itertools.combinations(range(len(candidates)), 2):
        votes = []
        for first, second in ((i, j), (j, i)):
            payload = {"question": h.query, "knowledge_cutoff": h.cutoff,
                       "candidate_A": hypothesis_fields(candidates[first]),
                       "candidate_B": hypothesis_fields(candidates[second])}
            raw = h.ask("tournament_judge", model, TOURNAMENT_SYSTEM, payload, max_out=2500)
            pick = str(raw.get("winner", "")).strip().upper() if isinstance(raw, dict) else ""
            votes.append(first if pick == "A" else second if pick == "B" else None)
        if votes[0] is not None and votes[0] == votes[1]:
            wins[votes[0]] += 1.0
        else:
            wins[i] += 0.5
            wins[j] += 0.5
    return wins


@register("breadth_tournament")
def m_breadth_tournament(h: Harness, model: str = GEN, judge_model: str | None = None, k: int = 4) -> dict[str, Any]:
    fr = frame(h, model)
    fams = family_map(h, fr, model)[:k]
    candidates = []
    for fam in fams:
        candidates.append(write(h, {"frame": fr, **chosen(fam)}, model, role="candidate_writer"))
    wins = tournament(h, candidates, judge_model or model)
    order = sorted(range(len(candidates)), key=lambda c: (-wins[c], -fams[c]["fit"], c))
    h.notes["tournament"] = [{"family": fams[c]["family"], "fit": fams[c]["fit"], "wins": wins[c]} for c in order]
    return candidates[order[0]]


# ---------------------------------------------------------------- L3: precedent prior from earlier papers

def precedents(h: Harness, fr: dict[str, Any], model: str = GEN) -> list[dict[str, Any]]:
    search = " ".join([h.query, str(fr.get("system", "")), str(fr.get("limitation", ""))])
    records = h.pack(search, "card", cap=1600)[:10]
    payload = {"question": h.query, "knowledge_cutoff": h.cutoff, "families": list(FAMILIES[fr["gap_type"]]),
               "earlier_paper_summaries": h.evidence_payload(records, 1600)}
    raw = h.ask("precedent_reader", model, PRECEDENT_SYSTEM, payload, max_out=6000)
    items = [p for p in (raw.get("precedents", []) if isinstance(raw, dict) else []) if isinstance(p, dict)
             and str(p.get("record_id")) in {r.record_id for r in records}]
    h.notes["precedents"] = items
    return items


@register("precedent_decide")
def m_precedent_decide(h: Harness, model: str = GEN) -> dict[str, Any]:
    fr = frame(h, model)
    prec = precedents(h, fr, model)
    fams = family_map(h, fr, model, precedents=[{k: p.get(k) for k in ("problem", "family", "lever", "outcome",
                                                                         "similarity")} for p in prec])
    notes = {"frame": fr, **chosen(fams[0])}
    h.notes["decision"] = notes
    return write(h, notes, model)


# ---------------------------------------------------------------- L4: deterministic checks + verifier + repair

def deterministic_problems(g: dict[str, Any], fr: dict[str, Any]) -> list[dict[str, str]]:
    problems = []
    if not NUMBER.search(str(g.get("predicted_outcome", ""))):
        problems.append({"field": "predicted_outcome", "issue": "no number or unit", "fix": "quantify with units"})
    rule = str((g.get("falsification_experiment") or {}).get("falsification_rule", ""))
    if not NUMBER.search(rule):
        problems.append({"field": "falsification_experiment", "issue": "falsification rule has no numeric threshold",
                         "fix": "state a numeric threshold"})
    if not str(g.get("baseline", "")).strip():
        problems.append({"field": "baseline", "issue": "no named baseline", "fix": "name the baseline condition"})
    return problems


def verify_and_repair(h: Harness, draft: dict[str, Any], fr: dict[str, Any], model: str = GEN,
                      records: list[Any] | None = None) -> dict[str, Any]:
    problems = deterministic_problems(draft, fr)
    raw = h.ask("verifier", model, VERIFY_SYSTEM, {"question": h.query, "knowledge_cutoff": h.cutoff,
                                                    "frame": fr, "draft": hypothesis_fields(draft)}, max_out=4000)
    problems += [p for p in (raw.get("problems", []) if isinstance(raw, dict) else []) if isinstance(p, dict)]
    h.notes["verification"] = {"problems": problems[:12],
                               "verdict": raw.get("verdict") if isinstance(raw, dict) else None}
    if not problems:
        return draft
    payload: dict[str, Any] = {"query": h.query, "knowledge_cutoff": h.cutoff,
                               "analysis_notes": h.notes.get("decision", {}), "draft": hypothesis_fields(draft),
                               "problems": problems[:12]}
    allowed: set[str] = set()
    if records:
        payload["eligible_evidence"] = h.evidence_payload(records, rx.record_cap("text_chunks"))
        allowed = {r.record_id for r in records}
    return h.generate_final("repairer", model, REPAIR_SYSTEM, payload, allowed)


@register("frame_decide_verify")
def m_frame_decide_verify(h: Harness, model: str = GEN) -> dict[str, Any]:
    draft = m_frame_decide(h, model)
    return verify_and_repair(h, draft, h.notes["frame"], model)


# ---------------------------------------------------------------- L7: decide first, then ground the chosen lever

@register("decide_then_ground")
def m_decide_then_ground(h: Harness, model: str = GEN) -> dict[str, Any]:
    fr = frame(h, model)
    fams = family_map(h, fr, model)
    notes = {"frame": fr, **chosen(fams[0])}
    h.notes["decision"] = notes
    search = " ".join([h.query, notes["chosen_family"].replace("_", " "), str(notes.get("lever", "")),
                       str(notes.get("principle", ""))])
    records = h.pack(search, "text_chunks")
    h.notes["grounding_query"] = search[:600]
    return write(h, notes, model, records=records)


# ================================================================ iteration 2

TREND_SYSTEM = (
    "You study how research on a problem has developed, to forecast what a research group would most plausibly do "
    "next. Input: a research question, its frame, the candidate families of answers, and summaries of earlier papers "
    "(all published before the knowledge cutoff) in chronological order. (1) Pick the earlier papers that address the "
    "same material class, limitation or open question. (2) Describe the trend: what was tried, in what order, with "
    "what success, and what remains unsolved. (3) Forecast the single most plausible next step for exactly this "
    "question: the family (one of the candidate families), the specific lever with key parameters, and why it follows "
    "from the trend and the question's cues. Do not default to alloying additions. Return JSON {\"relevant\": "
    "[record_id], \"trend\": str, \"unsolved\": str, \"next_step\": {\"family\": str, \"lever\": str, \"why\": str}}."
)
LEVERS_SYSTEM = (
    "Within one family of answers, list distinct specific levers for this exact research question. Input: the "
    "question, its frame and the chosen family. Give 4 levers that differ in substance (not wording), each with its key "
    "parameters (amounts, temperatures, times, routes or settings) and the principle by which it acts on the stated "
    "limitation or open question. Return JSON {\"levers\": [{\"lever\": str, \"principle\": str}]}."
)
SCORE_SYSTEM = (
    "You score ONE candidate answer to a materials-science research question; you never see other candidates. You do "
    "not know the true answer. Score 1 (poor) to 5 (excellent) on each criterion: root_cause = it acts directly on the "
    "limitation or open question the question states; constraints = it satisfies every stated constraint; physics = "
    "its mechanism is physically sound for this specific material system and regime; next_step = it is what a "
    "competent group would most plausibly pursue next given the earlier attempts the question mentions. Return JSON "
    "{\"root_cause\": int, \"constraints\": int, \"physics\": int, \"next_step\": int, \"reason\": str}."
)
CRITERIA = ("root_cause", "constraints", "physics", "next_step")


def _clip(value: Any) -> int:
    try:
        return max(1, min(5, int(value)))
    except (TypeError, ValueError):
        return 1


def independent_score(h: Harness, candidate: dict[str, Any], model: str, samples: int = 3) -> float:
    """Absolute scoring in isolated calls (no position bias); trimmed mean over samples (Halawi et al.)."""
    values = []
    for _ in range(samples):
        raw = h.ask("scorer", model, SCORE_SYSTEM, {"question": h.query, "knowledge_cutoff": h.cutoff,
                                                     "candidate": candidate}, max_out=1500)
        raw = raw if isinstance(raw, dict) else {}
        values.append(sum(_clip(raw.get(c)) for c in CRITERIA) / len(CRITERIA))
    values.sort()
    trimmed = values[1:-1] if len(values) >= 3 else values
    return sum(trimmed) / len(trimmed)


@register("trend_chain")
def m_trend_chain(h: Harness, model: str = GEN) -> dict[str, Any]:
    fr = frame(h, model)
    search = " ".join([h.query, str(fr.get("system", "")), str(fr.get("limitation", ""))])
    records = h.pack(search, "card", cap=1600)[:10]
    records.sort(key=lambda r: (r.publication_date, r.record_id))
    payload = {"question": h.query, "knowledge_cutoff": h.cutoff, "frame": fr,
               "candidate_families": list(FAMILIES[fr["gap_type"]]),
               "earlier_papers_chronological": h.evidence_payload(records, 1600)}
    raw = h.ask("trend_forecaster", model, TREND_SYSTEM, payload, max_out=5000)
    raw = raw if isinstance(raw, dict) else {}
    nxt = raw.get("next_step") if isinstance(raw.get("next_step"), dict) else {}
    notes = {"frame": fr, "trend": raw.get("trend", ""), "unsolved": raw.get("unsolved", ""),
             "chosen_family": nxt.get("family", ""), "lever": nxt.get("lever", ""), "why": nxt.get("why", "")}
    h.notes["decision"] = notes
    return write(h, notes, model, system=WRITER_B)


@register("coarse_to_fine")
def m_coarse_to_fine(h: Harness, model: str = GEN, scorer: str | None = None) -> dict[str, Any]:
    fr = frame(h, model)
    fam = family_map(h, fr, model)[0]
    raw = h.ask("lever_lister", model, LEVERS_SYSTEM, {"question": h.query, "knowledge_cutoff": h.cutoff,
                                                       "frame": fr, "family": fam["family"]}, max_out=3000)
    levers = [l for l in (raw.get("levers", []) if isinstance(raw, dict) else []) if isinstance(l, dict)
              and str(l.get("lever", "")).strip()][:4]
    if not levers:
        levers = [{"lever": fam.get("best_lever", ""), "principle": fam.get("principle", "")}]
    scored = []
    for lever in levers:
        candidate = {"family": fam["family"], "lever": lever.get("lever"), "principle": lever.get("principle")}
        scored.append((independent_score(h, candidate, scorer or model), candidate))
    scored.sort(key=lambda s: -s[0])
    h.notes["levers"] = [{"score": round(s, 3), **c} for s, c in scored]
    best = scored[0][1]
    notes = {"frame": fr, "chosen_family": fam["family"], "lever": best["lever"], "principle": best["principle"]}
    h.notes["decision"] = notes
    return write(h, notes, model, system=WRITER_B)


@register("family_scored")
def m_family_scored(h: Harness, model: str = GEN, scorer: str | None = None, k: int = 4) -> dict[str, Any]:
    fr = frame(h, model)
    fams = family_map(h, fr, model)[:k]
    candidates = [write(h, {"frame": fr, **chosen(f)}, model, role="candidate_writer", system=WRITER_B) for f in fams]
    scores = [independent_score(h, hypothesis_fields(c), scorer or model) for c in candidates]
    order = sorted(range(len(candidates)), key=lambda i: (-scores[i], -fams[i]["fit"], i))
    h.notes["selection"] = [{"family": fams[i]["family"], "fit": fams[i]["fit"], "score": round(scores[i], 3)}
                            for i in order]
    return candidates[order[0]]


@register("writer_only_b")
def m_writer_only_b(h: Harness, model: str = GEN) -> dict[str, Any]:
    return write(h, {}, model, system=WRITER_B)


@register("frame_decide_b")
def m_frame_decide_b(h: Harness, model: str = GEN) -> dict[str, Any]:
    fr = frame(h, model)
    fams = family_map(h, fr, model)
    notes = {"frame": fr, **chosen(fams[0])}
    h.notes["decision"] = notes
    return write(h, notes, model, system=WRITER_B)


# ---------------------------------------------------------------- model variants (iteration 3)

def _closed_book_with(model: str) -> Any:
    from temporal_hypothesis_benchmark import _GENERATE_SYSTEM

    def method(h: Harness) -> dict[str, Any]:
        payload = {"query": h.query, "knowledge_cutoff": h.cutoff, "eligible_evidence": []}
        return h.generate_final("generator", model, _GENERATE_SYSTEM, payload, set())
    return method


for _model in ("o3mini", "4omini"):
    register(f"closed_book_{_model}")(_closed_book_with(_model))
    register(f"writer_only_b_{_model}")(lambda h, _m=_model: m_writer_only_b(h, _m))
    register(f"frame_decide_b_{_model}")(lambda h, _m=_model: m_frame_decide_b(h, _m))
    register(f"coarse_to_fine_{_model}")(lambda h, _m=_model: m_coarse_to_fine(h, _m))
    register(f"trend_chain_{_model}")(lambda h, _m=_model: m_trend_chain(h, _m))


# ================================================================ iteration 4: combinations

def _ground(h: Harness, notes: dict[str, Any]) -> list[Any]:
    search = " ".join([h.query, str(notes.get("chosen_family", "")).replace("_", " "), str(notes.get("lever", "")),
                       str(notes.get("principle", notes.get("why", "")))])
    h.notes["grounding_query"] = search[:600]
    return h.pack(search, "text_chunks")


@register("decide_then_ground_b")
def m_decide_then_ground_b(h: Harness, model: str = GEN) -> dict[str, Any]:
    fr = frame(h, model)
    fams = family_map(h, fr, model)
    notes = {"frame": fr, **chosen(fams[0])}
    h.notes["decision"] = notes
    return write(h, notes, model, records=_ground(h, notes), system=WRITER_B)


def _trend_notes(h: Harness, model: str) -> dict[str, Any]:
    fr = frame(h, model)
    search = " ".join([h.query, str(fr.get("system", "")), str(fr.get("limitation", ""))])
    records = h.pack(search, "card", cap=1600)[:10]
    records.sort(key=lambda r: (r.publication_date, r.record_id))
    payload = {"question": h.query, "knowledge_cutoff": h.cutoff, "frame": fr,
               "candidate_families": list(FAMILIES[fr["gap_type"]]),
               "earlier_papers_chronological": h.evidence_payload(records, 1600)}
    raw = h.ask("trend_forecaster", model, TREND_SYSTEM, payload, max_out=5000)
    raw = raw if isinstance(raw, dict) else {}
    nxt = raw.get("next_step") if isinstance(raw.get("next_step"), dict) else {}
    notes = {"frame": fr, "trend": raw.get("trend", ""), "unsolved": raw.get("unsolved", ""),
             "chosen_family": nxt.get("family", ""), "lever": nxt.get("lever", ""), "why": nxt.get("why", "")}
    h.notes["decision"] = notes
    return notes


@register("trend_ground_b")
def m_trend_ground_b(h: Harness, model: str = GEN) -> dict[str, Any]:
    notes = _trend_notes(h, model)
    return write(h, notes, model, records=_ground(h, notes), system=WRITER_B)


@register("scaffold_ensemble")
def m_scaffold_ensemble(h: Harness, model: str = GEN, scorer: str | None = None) -> dict[str, Any]:
    """Candidates from distinct reasoning scaffolds, selected by independent absolute scoring (trimmed mean)."""
    from temporal_hypothesis_benchmark import _GENERATE_SYSTEM
    candidates = {}
    candidates["closed_book"] = h.generate_final("candidate_closed_book", model, _GENERATE_SYSTEM,
                                                 {"query": h.query, "knowledge_cutoff": h.cutoff,
                                                  "eligible_evidence": []}, set())
    fr = frame(h, model)
    fams = family_map(h, fr, model)
    decision = {"frame": fr, **chosen(fams[0])}
    candidates["frame_decide"] = write(h, decision, model, role="candidate_frame", system=WRITER_B)
    trend = _trend_notes(h, model)
    candidates["trend_chain"] = write(h, trend, model, role="candidate_trend", system=WRITER_B)
    h.notes["decision"] = trend
    names = list(candidates)
    order = list(range(len(names)))
    h.rng.shuffle(order)  # scoring is independent per candidate, but keep call order neutral too
    scores = {}
    for i in order:
        scores[names[i]] = independent_score(h, hypothesis_fields(candidates[names[i]]), scorer or model)
    best = max(names, key=lambda n: (scores[n], -names.index(n)))
    h.notes["selection"] = [{"scaffold": n, "score": round(scores[n], 3)} for n in names]
    h.notes["selected_scaffold"] = best
    return candidates[best]


for _model in ("o3mini",):
    register(f"decide_then_ground_b_{_model}")(lambda h, _m=_model: m_decide_then_ground_b(h, _m))
    register(f"trend_ground_b_{_model}")(lambda h, _m=_model: m_trend_ground_b(h, _m))
    register(f"scaffold_ensemble_{_model}")(lambda h, _m=_model: m_scaffold_ensemble(h, _m))


# ================================================================ iteration 5: ratchet rules from iteration-4 failures

# Dev-only failure (loop.md iteration 5): for understanding gaps whose question says the mechanism is hard to observe,
# the planner chose ordinary controlled experiments 11/12 (target: simulation) and 8/12 (target: in situ microscopy).
FAMILY_SYSTEM_V2 = FAMILY_SYSTEM + (
    " Cue rule: if the question says that a behaviour or mechanism is hard to observe or measure experimentally, is "
    "atomic-scale or transient, or occurs under conditions that are hard to reach in a laboratory, then simulation "
    "or in situ characterization families fit better than ordinary controlled experiments."
)


def family_map_v2(h: Harness, fr: dict[str, Any], model: str) -> list[dict[str, Any]]:
    payload: dict[str, Any] = {"question": h.query, "knowledge_cutoff": h.cutoff, "frame": fr,
                               "candidate_families": list(FAMILIES[fr["gap_type"]])}
    raw = h.ask("family_mapper", model, FAMILY_SYSTEM_V2, payload, max_out=6000)
    items = [f for f in (raw.get("families", []) if isinstance(raw, dict) else []) if isinstance(f, dict)]
    allowed = FAMILIES[fr["gap_type"]]
    ranked = []
    for order, item in enumerate(items):
        if str(item.get("family")) not in allowed:
            continue
        try:
            fit = max(0, min(5, int(item.get("fit", 0))))
        except (TypeError, ValueError):
            fit = 0
        ranked.append({**item, "fit": fit, "order": order})
    if not ranked:
        ranked = [{"family": allowed[0], "fit": 0, "order": 0, "best_lever": "", "principle": ""}]
    ranked.sort(key=lambda f: (-f["fit"], f["order"]))
    h.notes["families"] = ranked
    return ranked


@register("decide_then_ground_v2_o3mini")
def m_decide_then_ground_v2(h: Harness, model: str = "o3mini") -> dict[str, Any]:
    fr = frame(h, model)
    fams = family_map_v2(h, fr, model)
    notes = {"frame": fr, **chosen(fams[0])}
    h.notes["decision"] = notes
    return write(h, notes, model, records=_ground(h, notes), system=WRITER_B)


@register("multi_decision_ground_o3mini")
def m_multi_decision_ground(h: Harness, model: str = "o3mini") -> dict[str, Any]:
    """Coverage then selection: trend forecast + top-2 families (v2 map), each grounded and written, then picked by
    independent trimmed-mean scoring."""
    trend = _trend_notes(h, model)
    fr = trend["frame"]
    fams = family_map_v2(h, fr, model)
    decisions = [("trend", trend)]
    seen_families = {str(trend.get("chosen_family"))}
    for fam in fams:
        if fam["family"] not in seen_families and len(decisions) < 3:
            decisions.append((f"family:{fam['family']}", {"frame": fr, **chosen(fam)}))
            seen_families.add(fam["family"])
    candidates = []
    for name, notes in decisions:
        candidates.append((name, notes, write(h, notes, model, records=_ground(h, notes), role="candidate_writer",
                                              system=WRITER_B)))
    scores = [independent_score(h, hypothesis_fields(c), model) for _, _, c in candidates]
    best = max(range(len(candidates)), key=lambda i: (scores[i], -i))
    h.notes["decision"] = candidates[best][1]
    h.notes["selection"] = [{"decision": n, "family": d.get("chosen_family"), "score": round(s, 3)}
                            for (n, d, _), s in zip(candidates, scores)]
    return candidates[best][2]


# ================================================================ iteration 6: niche occupation (CARS) and o1

# Dev failure analysis (loop.md iteration 6): decision errors are systematic, not random. Four of eight dev cases have
# almost no class hits among 60 o3-mini hypotheses, so voting cannot fix them. The questions state niches (untested
# conditions, model assumptions, failed earlier routes) that the forecaster ignores. Swales' CARS model: an
# introduction establishes a territory (move 1) and a niche (move 2); the removed move 3 occupies the niche.
ALL_FAMILIES = tuple(dict.fromkeys(f for fams in FAMILIES.values() for f in fams))
NICHE_KINDS = ("untested_condition", "method_limitation", "unexplained_behaviour", "performance_limitation",
               "conflicting_results", "open_question")
NICHE_EXTRACT_SYSTEM = (
    "You analyse the rhetoric of a research question that was written from the introduction of an unpublished "
    "materials-science paper, with the paper's own contribution removed. Research introductions follow the "
    "Create-A-Research-Space pattern: move 1 establishes the territory (what is known) and move 2 establishes a niche "
    "(a gap, a limitation or simplifying assumption of earlier work, a condition or regime earlier work did not cover, "
    "an unexplained behaviour, a property that falls short, or conflicting results). List the niche statements of the "
    "question. Copy each one verbatim: an exact, contiguous quote of 5 to 40 words from the question. Do not "
    "paraphrase and do not add niches the question does not state. If the question states no explicit niche, quote "
    "its central open problem and use the kind open_question. Kinds: " + ", ".join(NICHE_KINDS) + ". Return JSON "
    "{\"niches\": [{\"quote\": str, \"kind\": str}]}."
)
NICHE_MOVE_SYSTEM = (
    "You reconstruct move 3 of a materials-science introduction: the contribution that occupies the niche. Input: the "
    "research question and its niche statements (verified quotes). Use only these and materials-science knowledge "
    "from before the knowledge cutoff. (1) For each niche, give the occupying move: the contribution that fills "
    "exactly that niche, found by inverting it (if earlier work covered only some conditions, cover the missing ones; "
    "if earlier models or measurements relied on a simplification, remove it; if a property is limited by a cause, "
    "act on that cause; if a behaviour is unexplained, make the measurement or simulation that resolves its "
    "mechanism). Give its contribution_type (material_or_process_intervention, experimental_study, simulation_study, "
    "combined_study, new_method), the lever or controlled variable, the technique and the conditions. (2) Choose the "
    "single move a research group most plausibly published: prefer the niche the question establishes most "
    "specifically, and the move that fills it most directly with standard techniques of the field. Words such as "
    "'intervention' or 'controlled change' in the question may mean a change of material, processing, test condition "
    "or simulation setting; decide from the niche, not from that wording. The family must be one of the candidate "
    "families. Return JSON {\"occupying_moves\": [{\"niche\": int, \"contribution_type\": str, \"lever\": str, "
    "\"technique\": str, \"conditions\": str}], \"chosen\": {\"niche\": int, \"contribution_type\": str, \"family\": "
    "str, \"lever\": str, \"technique\": str, \"conditions\": str, \"why\": str}}."
)
TREND_NICHE_SYSTEM = TREND_SYSTEM + (
    " You also receive the question's niche statements (verified quotes) and the move that would occupy each. The "
    "next step must occupy one of these niches; use the trend of the earlier papers to decide which niche and how "
    "(lever, technique and conditions)."
)
_QUOTE_NORMALISE = str.maketrans({"\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-",
                                  "\u2212": "-", "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'})


def _norm(text: str) -> str:
    return " ".join(str(text).translate(_QUOTE_NORMALISE).casefold().split()).strip(" .,;:")


def verified_niches(question: str, raw: Any) -> list[dict[str, str]]:
    """Computational sensor between steps: keep only niches quoted verbatim from the question."""
    q = _norm(question)
    kept: list[dict[str, str]] = []
    for item in raw.get("niches", []) if isinstance(raw, dict) else []:
        if not isinstance(item, dict):
            continue
        quote = _norm(item.get("quote", ""))
        if len(quote.split()) >= 4 and quote in q and quote not in {k["quote"] for k in kept}:
            kind = str(item.get("kind", ""))
            kept.append({"quote": quote, "kind": kind if kind in NICHE_KINDS else "open_question"})
    return kept[:8] or [{"quote": _norm(question), "kind": "open_question"}]


def _niche_notes(h: Harness, model: str) -> dict[str, Any]:
    raw = h.ask("niche_extractor", model, NICHE_EXTRACT_SYSTEM, {"question": h.query}, max_out=4000)
    niches = verified_niches(h.query, raw)
    moves = h.ask("niche_mover", model, NICHE_MOVE_SYSTEM, {"question": h.query, "knowledge_cutoff": h.cutoff,
                                                            "niches": niches,
                                                            "candidate_families": list(ALL_FAMILIES)}, max_out=6000)
    moves = moves if isinstance(moves, dict) else {}
    ch = moves.get("chosen") if isinstance(moves.get("chosen"), dict) else {}
    family = str(ch.get("family", ""))
    notes = {"niches": niches,
             "occupying_moves": [m for m in moves.get("occupying_moves", []) if isinstance(m, dict)][:8]
             if isinstance(moves.get("occupying_moves"), list) else [],
             "contribution_type": str(ch.get("contribution_type", "")),
             "chosen_family": family if family in ALL_FAMILIES else "",
             "lever": "; ".join(str(ch[k]) for k in ("lever", "technique", "conditions") if ch.get(k)),
             "why": str(ch.get("why", ""))}
    h.notes["niche"] = {"extracted": raw, "verified": niches, "moves": moves}
    h.notes["decision"] = notes
    return notes


@register("niche_ground_b_o3mini")
def m_niche_ground_b(h: Harness, model: str = "o3mini") -> dict[str, Any]:
    notes = _niche_notes(h, model)
    return write(h, notes, model, records=_ground(h, notes), system=WRITER_B)


def _trend_niche_notes(h: Harness, model: str) -> dict[str, Any]:
    niche = _niche_notes(h, model)
    fr = frame(h, model)
    search = " ".join([h.query, str(fr.get("system", "")), str(fr.get("limitation", ""))])
    records = h.pack(search, "card", cap=1600)[:10]
    records.sort(key=lambda r: (r.publication_date, r.record_id))
    payload = {"question": h.query, "knowledge_cutoff": h.cutoff, "frame": fr,
               "candidate_families": list(FAMILIES[fr["gap_type"]]),
               "niche_analysis": {"niches": niche["niches"], "occupying_moves": niche["occupying_moves"]},
               "earlier_papers_chronological": h.evidence_payload(records, 1600)}
    raw = h.ask("trend_forecaster", model, TREND_NICHE_SYSTEM, payload, max_out=5000)
    raw = raw if isinstance(raw, dict) else {}
    nxt = raw.get("next_step") if isinstance(raw.get("next_step"), dict) else {}
    notes = {"frame": fr, "niches": niche["niches"], "trend": raw.get("trend", ""), "unsolved": raw.get("unsolved", ""),
             "chosen_family": nxt.get("family", ""), "lever": nxt.get("lever", ""), "why": nxt.get("why", "")}
    h.notes["decision"] = notes
    return notes


@register("trend_niche_ground_b_o3mini")
def m_trend_niche_ground_b(h: Harness, model: str = "o3mini") -> dict[str, Any]:
    notes = _trend_niche_notes(h, model)
    return write(h, notes, model, records=_ground(h, notes), system=WRITER_B)


for _model in ("o1",):
    register(f"writer_only_b_{_model}")(lambda h, _m=_model: m_writer_only_b(h, _m))
    register(f"trend_ground_b_{_model}")(lambda h, _m=_model: m_trend_ground_b(h, _m))
    register(f"niche_ground_b_{_model}")(lambda h, _m=_model: m_niche_ground_b(h, _m))


# ================================================================ iteration 7: retrieval quality, combinations

# The shared retriever (temporal_hypothesis_benchmark.retrieve) scores raw token overlap without IDF, so frequent
# domain words ("alloy", "temperature", "entropy") decide what is retrieved. BM25 (Robertson and Zaragoza 2009)
# weights distinctive terms. Same pool, budget and record cap as rx.pack; only the ranking differs.
from citegraph import bm25, content_terms  # noqa: E402

_BM25_DOCS: dict[str, dict[str, list[str]]] = {}


def pack_bm25(h: Harness, query: str, representation: str = "text_chunks") -> list[Any]:
    pool = h.pool(representation)
    # Web pools differ by question level (one web corpus per paper and level, loop.md 17.1).
    key = f"{h.source}:{h.case['paper_id']}:{h.level if h.source == 'web' else '*'}:{representation}"
    if key not in _BM25_DOCS:
        _BM25_DOCS[key] = {r.record_id: content_terms(r.text) for r in pool}
    scores = bm25(content_terms(query), _BM25_DOCS[key])
    ranked = sorted(pool, key=lambda r: (-scores.get(r.record_id, 0.0), r.publication_date, r.record_id))
    cap = rx.record_cap(representation)
    packed: list[Any] = []
    used = 0
    for record in ranked:
        if scores.get(record.record_id, 0.0) <= 0:
            break
        size = min(len(record.text), cap)
        if used + size > rx.EVIDENCE_BUDGET_CHARS:
            continue
        packed.append(record)
        used += size
        if len(packed) >= rx.MAX_RECORDS or used >= rx.EVIDENCE_BUDGET_CHARS - 200:
            break
    for record in packed:
        h.seen[record.record_id] = record
    return packed


def _ground_bm25(h: Harness, notes: dict[str, Any]) -> list[Any]:
    search = " ".join([h.query, str(notes.get("chosen_family", "")).replace("_", " "), str(notes.get("lever", "")),
                       str(notes.get("principle", notes.get("why", "")))])
    h.notes["grounding_query"] = search[:600]
    h.notes["retriever"] = "bm25"
    return pack_bm25(h, search)


@register("trend_ground_bm25_b_o3mini")
def m_trend_ground_bm25_b(h: Harness, model: str = "o3mini") -> dict[str, Any]:
    notes = _trend_notes(h, model)
    return write(h, notes, model, records=_ground_bm25(h, notes), system=WRITER_B)


# Iteration 7b. (1) A fresh-sample replicate of the round-1 best: its dev score is the maximum of 29 configurations
# (winner's curse), so new variants are compared with an unbiased estimate of the same code.
register("trend_ground_b_o3mini_r2")(lambda h: m_trend_ground_b(h, "o3mini"))


# (2) Planner/executor split (H2: split the planner from the executor). Iteration 6 on dev: o1 decided better
# (intervention 0.42 vs 0.38) but wrote worse outcomes (0.79 vs 0.94); o3-mini writes better. o1 frames and forecasts,
# o3-mini grounds and writes.
@register("trend_o1_ground_b_o3mini")
def m_trend_o1_ground_b_o3mini(h: Harness) -> dict[str, Any]:
    notes = _trend_notes(h, "o1")
    return write(h, notes, "o3mini", records=_ground(h, notes), system=WRITER_B)


# Iteration 7c. Iterative retrieval-generation (ITER-RETGEN, Shao et al. 2023): the draft hypothesis is a better
# retrieval query for its own mechanism and conditions than the question. Grounding is where round 1 gained
# (mechanism 0.62 -> 0.81), so a second, draft-aimed retrieval targets mechanism, conditions and outcome. Declared
# difference: two retrievals (each payload within the 16,000-character budget).
REVISE_B = WRITER_B + (
    "\nThe notes also contain your earlier draft. The supplied evidence was retrieved for that draft's mechanism and "
    "conditions. Revise the draft only where this evidence supports a change (mechanism, conditions, predicted "
    "direction and size, boundary); keep the decided intervention unless the evidence contradicts it."
)


@register("trend_ground_iter_b_o3mini")
def m_trend_ground_iter_b(h: Harness, model: str = "o3mini") -> dict[str, Any]:
    notes = _trend_notes(h, model)
    draft = write(h, notes, model, records=_ground(h, notes), role="drafter", system=WRITER_B)
    search = " ".join([h.query] + [str(draft.get(k, "")) for k in ("intervention", "structural_mediator", "mechanism",
                                                                   "conditions")])
    h.notes["second_retrieval_query"] = search[:600]
    return write(h, {**notes, "draft": hypothesis_fields(draft)}, model, records=h.pack(search, "text_chunks"),
                 system=REVISE_B)


# Iteration 8 (exploratory, dev only; after the round-2 finals were fixed). The trend forecaster already judges which
# earlier papers address the same problem ("relevant"), but grounding ignored that and searched the whole pool
# lexically. Corrective RAG (Yan et al. 2024): evaluate relevance before generating. Grounding fills the budget first
# from the papers the forecaster judged relevant, then tops up from the usual ranking. Same budget and record cap.
from temporal_hypothesis_benchmark import retrieve  # noqa: E402


def _trend_notes_relevant(h: Harness, model: str) -> dict[str, Any]:
    fr = frame(h, model)
    search = " ".join([h.query, str(fr.get("system", "")), str(fr.get("limitation", ""))])
    records = h.pack(search, "card", cap=1600)[:10]
    records.sort(key=lambda r: (r.publication_date, r.record_id))
    payload = {"question": h.query, "knowledge_cutoff": h.cutoff, "frame": fr,
               "candidate_families": list(FAMILIES[fr["gap_type"]]),
               "earlier_papers_chronological": h.evidence_payload(records, 1600)}
    raw = h.ask("trend_forecaster", model, TREND_SYSTEM, payload, max_out=5000)
    raw = raw if isinstance(raw, dict) else {}
    nxt = raw.get("next_step") if isinstance(raw.get("next_step"), dict) else {}
    by_id = {r.record_id: r.paper_id for r in records}
    relevant = sorted({by_id[str(i)] for i in (raw.get("relevant") or []) if str(i) in by_id})
    notes = {"frame": fr, "trend": raw.get("trend", ""), "unsolved": raw.get("unsolved", ""),
             "chosen_family": nxt.get("family", ""), "lever": nxt.get("lever", ""), "why": nxt.get("why", ""),
             "relevant_papers": relevant}
    h.notes["decision"] = notes
    return notes


def _ground_focused(h: Harness, notes: dict[str, Any]) -> list[Any]:
    search = " ".join([h.query, str(notes.get("chosen_family", "")).replace("_", " "), str(notes.get("lever", "")),
                       str(notes.get("principle", notes.get("why", "")))])
    h.notes["grounding_query"] = search[:600]
    pool = h.pool("text_chunks")
    focus = set(notes.get("relevant_papers") or [])
    ordered = (retrieve(search, [r for r in pool if r.paper_id in focus], limit=len(pool))
               + retrieve(search, [r for r in pool if r.paper_id not in focus], limit=len(pool)))
    cap = rx.record_cap("text_chunks")
    packed: list[Any] = []
    used = 0
    for record in ordered:
        size = min(len(record.text), cap)
        if used + size > rx.EVIDENCE_BUDGET_CHARS:
            continue
        packed.append(record)
        used += size
        if len(packed) >= rx.MAX_RECORDS or used >= rx.EVIDENCE_BUDGET_CHARS - 200:
            break
    for record in packed:
        h.seen[record.record_id] = record
    h.notes["focused_records"] = sum(r.paper_id in focus for r in packed)
    return packed


@register("trend_focus_ground_b_o3mini")
def m_trend_focus_ground_b(h: Harness, model: str = "o3mini") -> dict[str, Any]:
    notes = _trend_notes_relevant(h, model)
    return write(h, notes, model, records=_ground_focused(h, notes), system=WRITER_B)


# ================================================================ round 3 (loop.md section 11): writer-level methods
# Round 2 on fresh papers: only the model and the writer generalised; the dev-selected harness steps did not. Round 3
# therefore varies the single writer call of the incumbent (`writer_only_b_o3mini`) and is developed on dev3 (24
# papers). Each final hypothesis keeps only the shared schema fields (Harness.generate_final).

register("writer_only_b_o3mini_r3")(lambda h: m_writer_only_b(h, "o3mini"))  # fresh-sample replicate (11.1)

# R1. Forecasting framing (Luo et al. 2024, BrainBench; Halawi et al. 2024): the task is to predict a result that
# already exists, so ask for the study the authors most plausibly ran with standard methods, not the most novel idea.
WRITER_FORECAST = WRITER_B + (
    "\nThe question was written from the introduction of a paper you have not seen; its result already exists. "
    "Forecast it: write the hypothesis the authors most plausibly tested and supported, that is the study or "
    "intervention a competent group in this field would most likely carry out next to address exactly the stated gap "
    "with standard methods, and the result they most likely observed. Prefer the most probable over the most novel."
)


@register("forecast_writer_b_o3mini")
def m_forecast_writer_b(h: Harness, model: str = "o3mini") -> dict[str, Any]:
    return write(h, {}, model, system=WRITER_FORECAST)


# R2. Self-generated analogies (Yasunaga et al. 2024, C10): strong models benefit from recalling their own relevant
# exemplars before solving. Two calls, so the recalled studies never enter the judged hypothesis.
RECALL_SYSTEM = (
    "Before anyone answers a materials-science research question, recall up to three earlier published studies "
    "(before the knowledge cutoff) that addressed the same kind of gap in the same or closely related materials: "
    "what they studied or changed, how (technique, conditions), and what they found. Include only studies you are "
    "confident exist; if unsure, describe the general approach the field used instead of naming a study. Return JSON "
    "{\"precedents\": [{\"study\": str, \"approach\": str, \"finding\": str}]}."
)


@register("analogy_writer_b_o3mini")
def m_analogy_writer_b(h: Harness, model: str = "o3mini") -> dict[str, Any]:
    raw = h.ask("recaller", model, RECALL_SYSTEM, {"question": h.query, "knowledge_cutoff": h.cutoff}, max_out=4000)
    precedents = [p for p in (raw.get("precedents", []) if isinstance(raw, dict) else []) if isinstance(p, dict)][:3]
    h.notes["recalled_precedents"] = precedents
    return write(h, {"recalled_precedents": precedents}, model, system=WRITER_B)


# R3. More test-time reasoning (OpenAI o3-mini reasoning_effort="high"; Snell et al. 2024): same writer, same model.
register("writer_only_b_o3mini_high")(lambda h: m_writer_only_b(h, "o3mini_high"))


# R4. Minimum-Bayes-risk selection (S9) among five independent writer samples: keep the medoid by content-word
# Jaccard similarity of the core fields. Target-free and model-free selection.
_STOP_R3 = set("the and for with from that this into within between than their which while where when what given are "
               "was were been has have how does one two new also such both each more less can could would should may "
               "might will its not via based under over using use".split())


def _core_words(g: dict[str, Any]) -> set[str]:
    text = " ".join(str(g.get(k, "")) for k in ("hypothesis", "intervention", "mechanism", "conditions",
                                                "predicted_outcome"))
    return {w for w in re.findall(r"[a-z0-9][a-z0-9\-]+", text.lower()) if len(w) > 2 and w not in _STOP_R3}


def medoid(candidates: list[dict[str, Any]]) -> int:
    words = [_core_words(c) for c in candidates]
    sims = [sum(len(words[i] & words[j]) / max(1, len(words[i] | words[j])) for j in range(len(words)) if j != i)
            for i in range(len(words))]
    return max(range(len(candidates)), key=lambda i: (sims[i], -i))


@register("writer_mbr_b_o3mini")
def m_writer_mbr_b(h: Harness, model: str = "o3mini", k: int = 5) -> dict[str, Any]:
    candidates = [write(h, {}, model, role="candidate_writer", system=WRITER_B) for _ in range(k)]
    best = medoid(candidates)
    h.notes["mbr"] = {"k": k, "selected": best}
    return candidates[best]


# R5. Evidence without a forecast: question-retrieved text chunks with the incumbent's writer and model. Isolates the
# evidence effect for o3-mini (round 1 only had it with a decision or forecast step).
@register("text_chunks_b_o3mini")
def m_text_chunks_b(h: Harness, model: str = "o3mini") -> dict[str, Any]:
    return write(h, {}, model, records=h.pack(h.query, "text_chunks"), system=WRITER_B)


# R6 (combination, loop.md 11.5): R5's question-retrieved evidence and R4's medoid of five samples address different
# failures (F17 conditions and unsupported claims; sample variance). Same evidence pack for all five samples.
@register("text_chunks_mbr_b_o3mini")
def m_text_chunks_mbr_b(h: Harness, model: str = "o3mini", k: int = 5) -> dict[str, Any]:
    records = h.pack(h.query, "text_chunks")
    candidates = [write(h, {}, model, records=records, role="candidate_writer", system=WRITER_B) for _ in range(k)]
    best = medoid(candidates)
    h.notes["mbr"] = {"k": k, "selected": best}
    return candidates[best]


# ================================================================ experiment 29 (loop.md section 12): sensitivity
# One input varies at a time around the recommended configuration (o3-mini, WRITER_B). The evidence or reasoning
# budget is the declared variable (must_obey.md 6.1).
import hashlib  # noqa: E402
import random  # noqa: E402


def _ranked_pool(h: Harness, query: str, representation: str) -> list[Any]:
    """The whole eligible pool: records that share words with the query first (shared retriever order), then the
    rest in a fixed order, so that N can exceed the number of overlapping records."""
    pool = h.pool(representation)
    ranked = retrieve(query, pool, limit=len(pool))
    seen = {r.record_id for r in ranked}
    return ranked + sorted((r for r in pool if r.record_id not in seen), key=lambda r: r.record_id)


def top_papers(h: Harness, query: str, n: int, representation: str = "card", seed: int | None = None) -> list[Any]:
    """One record per paper: the n most relevant papers, or n random eligible papers when a seed is given."""
    order = _ranked_pool(h, query, representation)
    if seed is not None:
        order = sorted(order, key=lambda r: r.record_id)
        random.Random(seed).shuffle(order)
    chosen: list[Any] = []
    papers: set[str] = set()
    for record in order:
        if record.paper_id in papers:
            continue
        chosen.append(record)
        papers.add(record.paper_id)
        if len(chosen) >= n:
            break
    for record in chosen:
        h.seen[record.record_id] = record
    return chosen


def top_text(h: Harness, query: str, budget: int, representation: str = "text_chunks") -> list[Any]:
    """rx.pack with a different character budget; the record limit scales with the budget."""
    cap = rx.record_cap(representation)
    max_records = max(1, round(rx.MAX_RECORDS * budget / rx.EVIDENCE_BUDGET_CHARS))
    packed: list[Any] = []
    used = 0
    for record in _ranked_pool(h, query, representation):
        size = min(len(record.text), cap)
        if used + size > budget:
            continue
        packed.append(record)
        used += size
        if len(packed) >= max_records or used >= budget - 200:
            break
    for record in packed:
        h.seen[record.record_id] = record
    return packed


def write_capped(h: Harness, records: list[Any], cap: int, model: str = "o3mini") -> dict[str, Any]:
    payload = {"query": h.query, "knowledge_cutoff": h.cutoff, "analysis_notes": {},
               "eligible_evidence": h.evidence_payload(records, cap)}
    h.notes["evidence"] = {"records": len(records), "papers": len({r.paper_id for r in records}),
                           "chars": sum(min(len(r.text), cap) for r in records)}
    return h.generate_final("writer", model, WRITER_B, payload, {r.record_id for r in records})


def _paper_seed(paper_id: str) -> int:
    return int(hashlib.sha256(paper_id.encode("utf-8")).hexdigest()[:8], 16)


for _n in (1, 3, 10, 30):
    register(f"papers_n{_n}_b_o3mini")(
        lambda h, _k=_n: write_capped(h, top_papers(h, h.query, _k), rx.record_cap("card")))
register("papers_random10_b_o3mini")(
    lambda h: write_capped(h, top_papers(h, h.query, 10, seed=_paper_seed(h.case["paper_id"])),
                           rx.record_cap("card")))
for _budget, _name in ((4000, "4k"), (64000, "64k")):
    register(f"text_{_name}_b_o3mini")(
        lambda h, _b=_budget: write_capped(h, top_text(h, h.query, _b), rx.record_cap("text_chunks")))
register("writer_only_b_o3mini_low")(lambda h: m_writer_only_b(h, "o3mini_low"))


# ---------------------------------------------------------------- round 4 (loop.md 16.1, experiment 34)
# Changes suggested by two model reviews:
# - B1: a stronger backbone;
# - B2: few-shot worked examples, picked by similarity or for diversity;
# - B3: a router with a specialist writer instruction per question type.
# B0 is a fresh-sample replicate of the incumbent, the comparison anchor.

import hypo_loop as _H  # noqa: E402
from answer_render import render as _render_key  # noqa: E402

register("writer_only_b_o3mini_r4")(lambda h: m_writer_only_b(h, "o3mini"))  # B0
# B1: the incumbent's single writer call on a stronger model. o3 and gpt-5 were also run, but failed the memorisation
# probe (loop.md 16.3); their runs are kept unanalysed in loop/excluded_by_probe/.
for _key in ("4o", "o4mini", "41"):
    register(f"writer_only_b_{_key}")(lambda h, _k=_key: m_writer_only_b(h, _k))
    if _key != "4o":
        _H.METHOD_MODELS[f"writer_only_b_{_key}"] = (_key,)

# B2: worked examples come only from the 36 spent held-out papers, never from an unspent test set. Each example is
# an earlier paper's problem-constrained question and its answer key, rendered into the schema by code.
_EXEMPLAR_DIRS = tuple(_H.EXPERIMENT_DIR / d / "cases" for d in ("benchmark_v3_1", "benchmark_test2",
                                                                 "benchmark_test3"))
_EXEMPLARS: list[dict[str, Any]] = []
FEWSHOT_K = 3
FEWSHOT_NOTE = (
    "\n\nThe worked_examples answer earlier, different questions; each answer is that earlier paper's actual study "
    "written in this schema. Use them only to calibrate how specific and complete a hypothesis should be. Do not "
    "copy their content unless it genuinely fits this question."
)


def exemplar_pool() -> list[dict[str, Any]]:
    if not _EXEMPLARS:
        for directory in _EXEMPLAR_DIRS:
            for path in sorted(directory.glob("PMC*.json")):
                case = json.loads(path.read_text())
                gap = case.get("gap")
                answer = _render_key(case["hidden_target"])
                _EXEMPLARS.append({
                    "paper_id": case["paper_id"], "date": case["publication_date"],
                    "gap_type": gap.get("gap_type") if isinstance(gap, dict) else None,
                    "question": case["queries"]["problem_constrained"]["text"],
                    "answer": {k: v for k, v in answer.items()
                               if k not in ("uncertainty", "supporting_evidence_ids", "conflicting_evidence_ids")}})
    return _EXEMPLARS


def pick_exemplars(query: str, case: dict[str, Any], mode: str, k: int = FEWSHOT_K) -> list[dict[str, Any]]:
    """Only papers published strictly before the case. similar: highest BM25 to the question. diverse: the least
    similar paper of each gap type, then the least similar overall."""
    pool = [e for e in exemplar_pool() if e["date"] < case["publication_date"] and e["paper_id"] != case["paper_id"]]
    if not pool:
        return []
    docs = {e["paper_id"]: content_terms(e["question"] + " " + json.dumps(e["answer"], ensure_ascii=False))
            for e in pool}
    scores = bm25(content_terms(query), docs)
    if mode == "similar":
        return sorted(pool, key=lambda e: (-scores[e["paper_id"]], e["paper_id"]))[:k]
    ranked = sorted(pool, key=lambda e: (scores[e["paper_id"]], e["paper_id"]))
    chosen: list[dict[str, Any]] = []
    for gap in ("design", "understanding", "method"):
        pick = next((e for e in ranked if e["gap_type"] == gap and e not in chosen), None)
        if pick is not None and len(chosen) < k:
            chosen.append(pick)
    for e in ranked:
        if len(chosen) >= k:
            break
        if e not in chosen:
            chosen.append(e)
    return chosen


def m_fewshot_b(h: Harness, mode: str, model: str = "o3mini") -> dict[str, Any]:
    examples = pick_exemplars(h.query, h.case, mode)
    h.notes["exemplars"] = [e["paper_id"] for e in examples]
    payload = {"query": h.query, "knowledge_cutoff": h.cutoff, "analysis_notes": {},
               "worked_examples": [{"question": e["question"], "hypothesis": e["answer"]} for e in examples],
               "eligible_evidence": []}
    return h.generate_final("writer", model, WRITER_B + FEWSHOT_NOTE, payload, set())


register("fewshot_similar_b_o3mini")(lambda h: m_fewshot_b(h, "similar"))
register("fewshot_diverse_b_o3mini")(lambda h: m_fewshot_b(h, "diverse"))

# B3: a short call types the question from the question alone, then the writer gets that type's instruction
# (aimed at F15-F18: design gets the class but not the lever; understanding loses on conditions; method is weakest).
ROUTER_SYSTEM = (
    "You classify a materials-science research question before anyone answers it. Use only the question. design: it "
    "asks how to improve a property or make a better material; understanding: it asks to explain a behaviour, "
    "mechanism or effect; method: it asks for a better method, model, process route or measurement. Return JSON "
    "{\"question_type\": \"design|understanding|method\", \"reason\": str}."
)
ROUTE_GUIDE = {
    "design": "Design question: commit to one concrete lever (a specific composition change, processing route or "
              "treatment) with its key parameters, name the structural mediator it creates, and give the mechanism "
              "that links it to the property under the stated operating conditions.",
    "understanding": "Understanding question: name the controlling variable and the mechanism that would explain the "
                     "behaviour, state the test conditions (temperature, atmosphere, time, stress) under which it "
                     "operates, and name the measurement that would reveal it.",
    "method": "Method question: propose the specific technique, model or protocol with its key settings, say what it "
              "measures or predicts, and how it would be validated against a baseline method.",
}


def m_router_b(h: Harness, model: str = "o3mini") -> dict[str, Any]:
    raw = h.ask("router", model, ROUTER_SYSTEM, {"question": h.query})
    kind = str(raw.get("question_type", "")).strip().lower() if isinstance(raw, dict) else ""
    kind = kind if kind in ROUTE_GUIDE else "design"
    h.notes["route"] = kind
    return write(h, {"question_type": kind, "guidance": ROUTE_GUIDE[kind]}, model, system=WRITER_B)


register("router_b_o3mini")(m_router_b)


# ---------------------------------------------------------------- experiment 36 (loop.md 17.1): web search
# Every analysed configuration that uses evidence is re-run with the run's web corpus in place of the fixed corpus:
# the first N = 50 papers of a live web search (Europe PMC), strictly filtered by date, plus their co-cited references
# (websearch.py). Retrieval, budgets and prompts are unchanged. Three agents search the web themselves.

import websearch as _web  # noqa: E402
from temporal_hypothesis_benchmark import _GENERATE_SYSTEM as _BASELINE_SYSTEM  # noqa: E402
from temporal_hypothesis_benchmark import generate_with_citation_repair as _baseline_generate  # noqa: E402

WEB_CONFIGS = (
    "text_chunks", "text_chunks_b_o3mini", "text_chunks_mbr_b_o3mini", "text_4k_b_o3mini", "text_64k_b_o3mini",
    "papers_n1_b_o3mini", "papers_n3_b_o3mini", "papers_n10_b_o3mini", "papers_n30_b_o3mini",
    "papers_random10_b_o3mini", "precedent_decide", "decide_then_ground", "decide_then_ground_b",
    "decide_then_ground_b_o3mini", "decide_then_ground_v2_o3mini", "multi_decision_ground_o3mini", "trend_chain",
    "trend_chain_o3mini", "trend_ground_b", "trend_ground_b_o1", "trend_ground_b_o3mini", "trend_ground_bm25_b_o3mini",
    "trend_ground_iter_b_o3mini", "trend_focus_ground_b_o3mini", "trend_niche_ground_b_o3mini",
    "trend_o1_ground_b_o3mini", "niche_ground_b_o1", "niche_ground_b_o3mini", "scaffold_ensemble",
    "scaffold_ensemble_o3mini",
)


def _on_web(base: str) -> Any:
    def method(h: Harness) -> dict[str, Any]:
        h.source = "web"
        return _H.METHODS[base](h)
    return method


for _base in WEB_CONFIGS:
    register(f"web_{_base}")(_on_web(_base))
    if _base in _H.METHOD_MODELS:
        _H.METHOD_MODELS[f"web_{_base}"] = _H.METHOD_MODELS[_base]

WEB_AGENT_CALLS = 10
WEB_AGENT_SYSTEM = (
    "You search the scientific literature for a materials-science research question before a hypothesis is written. "
    "The tools return only open-access papers published before the knowledge cutoff. Find what a researcher would "
    "read before answering: work on the same material system and property, the earlier attempts and limitations the "
    "question mentions, and mechanisms, compositions or processing routes that could address them. Use short keyword "
    "queries. Read the pages most likely to hold results, mechanisms or data; results usually come after the first "
    "pages. Each step, return JSON {\"thought\": one sentence, \"action\": \"web_search\" | \"read_paper\" | "
    "\"references\" | \"finish\", \"arguments\": {...}}. Finish when you have read enough: the pages you read are the "
    "only evidence the hypothesis writer will see."
)


def web_agent_pages(h: Harness, model: str) -> list[Any]:
    """The search loop: up to WEB_AGENT_CALLS tool calls chosen by the model; returns the pages it read."""
    h.source = "web"
    tools = _web.WebTools(h.case["paper_id"], h.level)
    history: list[dict[str, Any]] = []
    calls = 0
    while calls < WEB_AGENT_CALLS:
        payload = {"question": h.query, "knowledge_cutoff": h.cutoff, "tools": _web.TOOL_DOC,
                   "tool_calls_left": WEB_AGENT_CALLS - calls, "pages_left": _web.MAX_READS - len(tools.pages),
                   "history": history}
        raw = h.ask("searcher", model, WEB_AGENT_SYSTEM, payload, max_out=3000)
        raw = raw if isinstance(raw, dict) else {}
        action = str(raw.get("action", "")).strip().lower()
        if action == "finish":
            break
        arguments = raw.get("arguments") if isinstance(raw.get("arguments"), dict) else {
            k: raw[k] for k in ("query", "paper_id", "page") if k in raw}
        calls += 1
        history.append({"step": calls, "action": action, "arguments": arguments,
                        "result": tools.call(action, arguments)})
    for record in [*tools.listed.values(), *tools.pages.values()]:
        h.seen[record.record_id] = record
    h.notes["web_agent"] = {"tool_calls": calls, "pages": sorted(tools.pages), "listed": len(tools.listed),
                            "log": tools.log}
    return sorted(tools.pages.values(), key=lambda r: r.record_id)


@register("web_agent")
def m_web_agent(h: Harness) -> dict[str, Any]:
    """The Llama baseline (experiment-21 prompt and generator call) with the web search tool."""
    pages = web_agent_pages(h, "llama")
    payload = {"query": h.query, "knowledge_cutoff": h.cutoff,
               "eligible_evidence": h.evidence_payload(pages, _web.PAGE_CHARS)}
    h.guard(payload)
    h.models["generator"] = f"trapi:{_H.GENERATOR}"
    h.trace.append({"role": "generator", "model": _H.GENERATOR, "chars_in": len(json.dumps(payload)), "chars_out": 0,
                    "seconds": 0})
    return _baseline_generate(payload, {r.record_id for r in pages})


@register("web_agent_o3mini")
def m_web_agent_o3mini(h: Harness) -> dict[str, Any]:
    """The o3-mini baseline (closed_book_o3mini's prompt) with the web search tool."""
    pages = web_agent_pages(h, "o3mini")
    payload = {"query": h.query, "knowledge_cutoff": h.cutoff,
               "eligible_evidence": h.evidence_payload(pages, _web.PAGE_CHARS)}
    return h.generate_final("generator", "o3mini", _BASELINE_SYSTEM, payload, {r.record_id for r in pages})


@register("web_agent_b_o3mini")
def m_web_agent_b(h: Harness) -> dict[str, Any]:
    """The best method's writer (writer_only_b_o3mini) with the web search tool."""
    pages = web_agent_pages(h, "o3mini")
    payload = {"query": h.query, "knowledge_cutoff": h.cutoff, "analysis_notes": {},
               "eligible_evidence": h.evidence_payload(pages, _web.PAGE_CHARS)}
    return h.generate_final("writer", "o3mini", WRITER_B, payload, {r.record_id for r in pages})


# ---------------------------------------------------------------- experiment 37 (loop.md 18.1): propose, critique, decide
# Three agent roles (C1 co-scientist: generation, reflection, meta-review; C5 ResearchAgent: criterion-based review).
# Each role can get web evidence from the question's experiment-36 corpus. The proposer widens coverage on purpose
# (F10); the critic and the decider replace self-scored selection. The critic's and decider's evidence is retrieved
# with each proposed idea instead of the question (C11 HyDE): experiment 36 showed the question retrieves background.

import threading  # noqa: E402
from collections import OrderedDict  # noqa: E402

from temporal_hypothesis_benchmark import _validate_generation  # noqa: E402

PCD_K = 4
IDEA_FIELDS = ("material_system", "intervention", "conditions", "structural_mediator", "mechanism",
               "predicted_outcome", "why_it_addresses_the_question")
SEARCH_FIELDS = ("material_system", "intervention", "conditions", "structural_mediator", "mechanism")
CRITIQUE_FIELDS = ("addresses_problem", "constraints", "physical_soundness", "feasibility", "evidence", "main_risk",
                   "fix")
VERDICT_RANK = {"strong": 2, "viable_with_changes": 1, "weak": 0}
IDEA_JSON = ("{\"material_system\": str, \"intervention\": str, \"conditions\": str, \"structural_mediator\": str, "
             "\"mechanism\": str, \"predicted_outcome\": str, \"why_it_addresses_the_question\": str, "
             "\"supporting_record_ids\": [IDs copied from the supplied records, or empty]}")


def proposer_system(k: int) -> str:
    task = ("Propose the single most promising research direction that could answer the question. It must"
            if k == 1 else
            f"Propose {k} candidate research directions that could answer the question. Each must")
    differ = "" if k == 1 else (
        ", and differ from the others in its lever (for example composition, processing or synthesis route, heat or "
        "thermomechanical treatment, microstructure architecture, surface or coating, or a measurement, simulation or "
        "modelling approach) or in its mechanism")
    return (
        "You are the proposer in a team of materials scientists. You receive a research question, a knowledge cutoff "
        "and, optionally, summaries of earlier papers (all published before the cutoff). " + task + " attack the "
        "limitation or open question the question states and respect every explicit constraint" + differ + ". Use only "
        "materials-science knowledge from before the cutoff and the supplied records; never claim knowledge of later "
        "work. Be specific: name the material system and starting state, the intervention or study with its key "
        "parameters, the conditions, the expected structural change, the mechanism, and the predicted outcome "
        "relative to the baseline the question implies. Return JSON {\"ideas\": [" + IDEA_JSON + "]}."
    )


CRITIC_SYSTEM = (
    "You are the critic in a team of materials scientists. You receive a research question, a knowledge cutoff, "
    "candidate research directions proposed by a colleague and, optionally, earlier literature records retrieved for "
    "each direction (all published before the cutoff). Review every direction rigorously and fairly against these "
    "criteria: (1) does it address the limitation or open question the question states, at its root cause; (2) does it "
    "respect every explicit constraint, such as the material system, the operating conditions and the properties that "
    "must not be sacrificed; (3) is its mechanism physically sound for this specific material system and regime; (4) is "
    "it feasible with established methods; (5) do the supplied records support it, contradict it, or show it was "
    "already tried (cite their record IDs); (6) what is its main risk. Then give a verdict, strong, viable_with_changes "
    "or weak, and one concrete fix for its main weakness. Judge each direction on its merits and do not propose new "
    "directions. Return JSON {\"critiques\": [{\"id\": str, \"addresses_problem\": str, \"constraints\": str, "
    "\"physical_soundness\": str, \"feasibility\": str, \"evidence\": str, \"evidence_ids\": [record IDs], "
    "\"main_risk\": str, \"verdict\": str, \"fix\": str}]} with one entry per direction."
)
DECIDER_SYSTEM = (
    "You lead a team of materials scientists and decide the research direction. You receive a research question, a "
    "knowledge cutoff, candidate directions from the proposer, the critic's review of each direction when one is "
    "supplied and, optionally, earlier literature records (all published before the cutoff). Decide which direction the "
    "team pursues: weigh how directly each attacks the limitation or open question the question states, whether the "
    "critic's objections are fatal or fixable, and the evidence. You may adopt one direction, adopt it with the "
    "critic's fix, or merge compatible elements of several directions into one coherent study; do not switch to a "
    "direction nobody proposed. Then write the final hypothesis for the chosen direction. Do not claim knowledge of the "
    "held-out paper. Predict the direction and approximate size of effects only as far as the reasoning and evidence "
    "support; if support is insufficient, state the uncertainty instead of inventing support or precise values.\n\n"
    "Return JSON with \"decision\": {\"chosen_ids\": [direction IDs], \"mode\": \"adopt\" | \"adopt_with_fix\" | "
    "\"merge\", \"rationale\": str}, followed by all fields of:\n" + SCHEMA +
    "\nEvidence IDs must be copied from the supplied records."
)

_PCD_DOCS: OrderedDict[str, dict[str, list[str]]] = OrderedDict()
_PCD_DOCS_LOCK = threading.Lock()


def _pcd_ranked(h: Harness, search: str, representation: str) -> list[Any]:
    """The pool ranked by BM25 against the search text (content words only); records sharing no word are dropped."""
    pool = h.pool(representation)
    key = f"{h.source}:{h.case['paper_id']}:{h.level if h.source == 'web' else '*'}:{representation}"
    with _PCD_DOCS_LOCK:
        docs = _PCD_DOCS.get(key)
    if docs is None:
        docs = {r.record_id: content_terms(r.text) for r in pool}
        with _PCD_DOCS_LOCK:
            _PCD_DOCS[key] = docs
            while len(_PCD_DOCS) > 12:
                _PCD_DOCS.popitem(last=False)
    scores = bm25(content_terms(search), docs)
    return sorted((r for r in pool if scores.get(r.record_id, 0.0) > 0),
                  key=lambda r: (-scores[r.record_id], r.publication_date, r.record_id))


def pcd_evidence(h: Harness, search: str, representation: str, budget: int, cap: int,
                 one_per_paper: bool = False, exclude: frozenset[str] = frozenset()) -> list[Any]:
    """Top-ranked records within a character budget; the record limit scales with the budget (24 per 16,000)."""
    max_records = max(1, round(rx.MAX_RECORDS * budget / rx.EVIDENCE_BUDGET_CHARS))
    packed: list[Any] = []
    used = 0
    papers: set[str] = set()
    for record in _pcd_ranked(h, search, representation):
        if record.record_id in exclude or (one_per_paper and record.paper_id in papers):
            continue
        size = min(len(record.text), cap)
        if used + size > budget:
            continue
        packed.append(record)
        used += size
        papers.add(record.paper_id)
        if len(packed) >= max_records or used >= budget - 200:
            break
    for record in packed:
        h.seen[record.record_id] = record
    return packed


def idea_search_text(idea: dict[str, Any]) -> str:
    return " ".join(str(idea.get(f, "")) for f in SEARCH_FIELDS)


def present(h: Harness, ideas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The ideas in a seeded random order with neutral labels A, B, ... (must_obey.md 5.2: selectors see shuffled
    candidates with neutral labels), so the proposer's order cannot steer the critic or the decider."""
    order = list(range(len(ideas)))
    h.rng.shuffle(order)
    shown = [{**ideas[n], "label": chr(ord("A") + pos)} for pos, n in enumerate(order)]
    h.notes["presentation"] = {i["label"]: i["id"] for i in shown}
    return shown


def public_idea(idea: dict[str, Any]) -> dict[str, Any]:
    """An idea as the critic and decider see it: its neutral label, no record IDs (they may not see those records)."""
    return {"id": idea["label"], **{f: idea[f] for f in IDEA_FIELDS}}


def parse_ideas(raw: Any, k: int, allowed: set[str]) -> list[dict[str, Any]]:
    items = raw.get("ideas") if isinstance(raw, dict) else None
    ideas: list[dict[str, Any]] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        fields = {f: str(item.get(f) or "").strip() for f in IDEA_FIELDS}
        if not fields["intervention"] or not fields["mechanism"]:
            continue
        cited = item.get("supporting_record_ids")
        ideas.append({"id": f"I{len(ideas) + 1}", **fields,
                      "supporting_record_ids": [c for c in cited if c in allowed] if isinstance(cited, list) else []})
        if len(ideas) == k:
            break
    if not ideas:
        raise ValueError("proposer returned no usable idea")
    return ideas


def parse_critiques(raw: Any, ideas: list[dict[str, Any]], allowed: set[str]) -> list[dict[str, Any]]:
    items = raw.get("critiques") if isinstance(raw, dict) else None
    ids = [i["label"] for i in ideas]
    found: dict[str, dict[str, Any]] = {}
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        iid = str(item.get("id") or "").strip()
        if iid not in ids or iid in found:
            continue
        verdict = str(item.get("verdict") or "").strip().lower().replace(" ", "_").replace("-", "_")
        cited = item.get("evidence_ids")
        found[iid] = {"id": iid, **{f: str(item.get(f) or "").strip()[:1500] for f in CRITIQUE_FIELDS},
                      "evidence_ids": [c for c in cited if c in allowed] if isinstance(cited, list) else [],
                      "verdict": verdict if verdict in VERDICT_RANK else "not_stated"}
    if not found:
        raise ValueError("critic returned no usable critique")
    return [found.get(i, {"id": i, "verdict": "not_reviewed"}) for i in ids]


def rule_choice(ideas: list[dict[str, Any]], critiques: list[dict[str, Any]]) -> dict[str, Any]:
    """No-decider ablation: the idea with the best verdict; ties go to the proposer's earlier idea."""
    rank = {c["id"]: VERDICT_RANK.get(c.get("verdict", ""), -1) for c in critiques}
    return max(ideas, key=lambda i: (rank.get(i["label"], -1), -int(i["id"][1:])))


def pcd_propose(h: Harness, model: str, k: int, web: bool) -> list[dict[str, Any]]:
    payload: dict[str, Any] = {"question": h.query, "knowledge_cutoff": h.cutoff}
    records: list[Any] = []
    if web:
        records = pcd_evidence(h, h.query, "card", rx.EVIDENCE_BUDGET_CHARS, rx.RECORD_MAX_CHARS, one_per_paper=True)
        payload["earlier_papers"] = h.evidence_payload(records, rx.RECORD_MAX_CHARS)
    raw = h.ask("proposer", model, proposer_system(k), payload)
    ideas = parse_ideas(raw, k, {r.record_id for r in records})
    h.notes["proposals"] = ideas
    h.notes["proposer_evidence"] = [r.record_id for r in records]
    return ideas


def pcd_idea_evidence(h: Harness, ideas: list[dict[str, Any]]) -> dict[str, list[Any]]:
    """Passages retrieved with each idea's own text (C11), an equal share of the 16,000-character budget each."""
    budget = rx.EVIDENCE_BUDGET_CHARS // len(ideas)
    out: dict[str, list[Any]] = {}
    taken: set[str] = set()
    for idea in ideas:
        out[idea["label"]] = pcd_evidence(h, idea_search_text(idea), "text_chunks", budget, rx.RECORD_MAX_CHARS,
                                          exclude=frozenset(taken))
        taken |= {r.record_id for r in out[idea["label"]]}
    h.notes["idea_evidence"] = {iid: [r.record_id for r in recs] for iid, recs in out.items()}
    return out


def pcd_critique(h: Harness, model: str, ideas: list[dict[str, Any]],
                 evidence: dict[str, list[Any]] | None) -> list[dict[str, Any]]:
    payload: dict[str, Any] = {"question": h.query, "knowledge_cutoff": h.cutoff,
                               "directions": [public_idea(i) for i in ideas]}
    allowed: set[str] = set()
    if evidence is not None:
        payload["evidence_by_direction"] = {iid: h.evidence_payload(recs, rx.RECORD_MAX_CHARS)
                                            for iid, recs in evidence.items()}
        allowed = {r.record_id for recs in evidence.values() for r in recs}
    raw = h.ask("critic", model, CRITIC_SYSTEM, payload)
    critiques = parse_critiques(raw, ideas, allowed)
    h.notes["critiques"] = critiques
    return critiques


def final_with_decision(h: Harness, model: str, payload: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
    """The decider's call: the decision is kept in the notes, and the hypothesis is validated like every final
    hypothesis (schema fields only, citations only from the supplied records, one repair call)."""
    raw = h.ask("decider", model, DECIDER_SYSTEM, payload)
    decision = raw.get("decision") if isinstance(raw, dict) else None
    try:
        out = _H._schema_only(_validate_generation(raw, allowed))
        out["citation_validation"] = {"status": "valid", "removed_unknown_ids": []}
    except ValueError as error:
        repair = {**payload, "validation_error": str(error), "allowed_evidence_ids": sorted(allowed),
                  "repair_instruction": "Regenerate the complete JSON, including the decision. The hypothesis field must "
                                        "be a non-empty statement, and evidence ID arrays may contain only exact IDs "
                                        "from allowed_evidence_ids."}
        raw = h.ask("decider_repair", model, DECIDER_SYSTEM, repair)
        decision = raw.get("decision") if isinstance(raw, dict) else decision
        out = _H._schema_only(_validate_generation(raw, allowed))
        out["citation_validation"] = {"status": "valid_after_regeneration", "initial_error": str(error)}
    decision = decision if isinstance(decision, dict) else {"unparsed": str(decision)[:500]}
    labels = decision.get("chosen_ids") if isinstance(decision.get("chosen_ids"), list) else []
    decision["chosen_labels"] = labels
    decision["chosen_ids"] = [h.notes.get("presentation", {}).get(str(x), str(x)) for x in labels]
    h.notes["decision"] = decision
    return out


def m_pcd(h: Harness, model: str = "o3mini", web: str = "", k: int = PCD_K, critic: bool = True,
          decider: bool = True) -> dict[str, Any]:
    """Propose -> critique -> decide. `web` lists the roles given web evidence: P (proposer), C (critic), D (decider;
    the writer in the no-decider ablation)."""
    if web:
        h.source = "web"
    h.notes["pcd"] = {"model": model, "web": web or "none", "k": k, "critic": critic, "decider": decider}
    ideas = present(h, pcd_propose(h, model, k, "P" in web))
    needs = ("C" in web and critic) or "D" in web
    evidence = pcd_idea_evidence(h, ideas) if needs else None
    critiques = pcd_critique(h, model, ideas, evidence if "C" in web else None) if critic else None
    final_records = [r for recs in evidence.values() for r in recs] if evidence is not None and "D" in web else None
    if critiques is not None and final_records is None:
        # The decider (or writer) has no records to cite, so the critic's record IDs are not passed on.
        critiques = [{k_: v for k_, v in c.items() if k_ != "evidence_ids"} for c in critiques]
    if not decider:
        chosen = rule_choice(ideas, critiques or [])
        h.notes["decision"] = {"chosen_labels": [chosen["label"]], "chosen_ids": [chosen["id"]],
                               "mode": "rule_best_verdict"}
        notes = {"chosen_direction": public_idea(chosen),
                 "critique": next(c for c in critiques or [] if c["id"] == chosen["label"])}
        return write(h, notes, model, records=final_records, system=WRITER_B)
    payload: dict[str, Any] = {"query": h.query, "knowledge_cutoff": h.cutoff,
                               "directions": [public_idea(i) for i in ideas]}
    if critiques is not None:
        payload["critiques"] = critiques
    payload["eligible_evidence"] = h.evidence_payload(final_records, rx.RECORD_MAX_CHARS) if final_records else []
    return final_with_decision(h, model, payload, {r.record_id for r in final_records or []})


PCD_WEB = {"none": "", "P": "P", "C": "C", "D": "D", "PC": "PC", "PD": "PD", "CD": "CD", "PCD": "PCD"}
for _flags, _web in PCD_WEB.items():
    register(f"pcd_{_flags}_o3mini")(lambda h, _w=_web: m_pcd(h, "o3mini", _w))
for _flags in ("none", "PCD"):
    _web = PCD_WEB[_flags]
    register(f"pcd_nocritic_{_flags}_o3mini")(lambda h, _w=_web: m_pcd(h, "o3mini", _w, critic=False))
    register(f"pcd_nodecider_{_flags}_o3mini")(lambda h, _w=_web: m_pcd(h, "o3mini", _w, decider=False))
    register(f"pcd_k1_{_flags}_o3mini")(lambda h, _w=_web: m_pcd(h, "o3mini", _w, k=1))
    register(f"pcd_{_flags}_llama")(lambda h, _w=_web: m_pcd(h, "llama", _w))
PCD_CONFIGS = tuple(m for m in _H.METHODS if m.startswith("pcd_"))


# ================================================================ experiment 38 (loop.md 19.1): synthesis
# Several independent drafts, then one final hypothesis that keeps what the drafts agree on (Mixture-of-Agents; the
# wisdom of the silicon crowd). Selection (MBR, voting, likelihood) keeps one whole candidate with its idiosyncratic
# details; a synthesis drops the details only one draft states. Drafts are the incumbent's writer (WRITER_B).

SYNTH_SYSTEM = (
    "You are a materials-science hypothesis agent in a chronological benchmark. You receive several independent draft "
    "hypotheses written for the same research question (labels A, B, ...; their order means nothing). Write one final "
    "hypothesis that keeps what the drafts agree on. (1) Intervention: use the intervention that most drafts share. If "
    "no intervention is shared by two or more drafts, keep the single draft intervention that most directly addresses "
    "the limitation the question states. Never combine different interventions into one. (2) Conditions, structural "
    "mediator, mechanism, predicted outcome, baseline and boundary: keep the elements that two or more drafts state "
    "consistently, and drop specifics (numbers, compositions, phases, parameters) that only one draft states, unless "
    "the chosen intervention needs them. (3) Do not claim knowledge of the held-out paper. Predict the direction and "
    "approximate size of effects only as far as the drafts agree and any supplied evidence supports; if support is "
    "insufficient, state the uncertainty instead of inventing support or precise values.\n\n"
    "Return one falsifiable hypothesis as JSON:\n" + SCHEMA + "\nEvidence IDs must be copied from the supplied records."
)
DRAFT_FIELDS = ("hypothesis", "material_initial_state", "intervention", "conditions", "structural_mediator",
                "mechanism", "predicted_outcome", "baseline", "boundary", "falsification_experiment")
SYNTH_WEB_BUDGET = 64000  # the best web method's evidence (web_text_64k_b_o3mini)
CROWD = ("o3mini", "o1", "4o", "4omini", "llama")  # every allowed generator with a 2023 cutoff (must_obey.md 2)


def synth_draft(h: Harness, model: str, records: list[Any], n: int) -> dict[str, Any]:
    """One draft from the incumbent's writer, closed-book or with the evidence pack."""
    if not records:
        return write(h, {}, model, role=f"draft_{n}", system=WRITER_B)
    payload = {"query": h.query, "knowledge_cutoff": h.cutoff, "analysis_notes": {},
               "eligible_evidence": h.evidence_payload(records, rx.record_cap("text_chunks"))}
    return h.generate_final(f"draft_{n}", model, WRITER_B, payload, {r.record_id for r in records})


def m_synth(h: Harness, drafts_spec: list[tuple[str, bool]], model: str = "o3mini") -> dict[str, Any]:
    """drafts_spec: (model, with web evidence) per draft. A draft that fails even after its repair call is recorded
    in the notes and the synthesis uses the others."""
    records: list[Any] = []
    if any(web for _, web in drafts_spec):
        h.source = "web"
        records = top_text(h, h.query, SYNTH_WEB_BUDGET)
        h.notes["evidence"] = {"records": len(records), "papers": len({r.paper_id for r in records}),
                               "chars": sum(min(len(r.text), rx.record_cap("text_chunks")) for r in records)}
    drafts: list[dict[str, Any]] = []
    for n, (draft_model, web) in enumerate(drafts_spec, 1):
        try:
            g = synth_draft(h, draft_model, records if web else [], n)
        except Exception as error:  # noqa: BLE001 - recorded; the synthesis uses the other drafts
            h.notes.setdefault("draft_failures", []).append(
                {"draft": n, "model": draft_model, "error": f"{type(error).__name__}: {str(error)[:200]}"})
            continue
        drafts.append({"id": f"D{n}", "model": draft_model, "web": web, **{f: g.get(f) for f in DRAFT_FIELDS},
                       "supporting_evidence_ids": list(g.get("supporting_evidence_ids") or []) if web else []})
    if not drafts:
        raise ValueError("every draft failed")
    order = list(range(len(drafts)))
    h.rng.shuffle(order)  # must_obey.md 5.2: shuffled, neutral labels, no model names
    shown = []
    for pos, i in enumerate(order):
        item = {"label": chr(ord("A") + pos), **{f: drafts[i][f] for f in DRAFT_FIELDS}}
        if records:
            item["supporting_evidence_ids"] = drafts[i]["supporting_evidence_ids"]
        shown.append(item)
    h.notes["drafts"] = drafts
    h.notes["presentation"] = {s["label"]: drafts[i]["id"] for s, i in zip(shown, order)}
    payload = {"query": h.query, "knowledge_cutoff": h.cutoff, "drafts": shown,
               "eligible_evidence": h.evidence_payload(records, rx.record_cap("text_chunks")) if records else []}
    return h.generate_final("writer", model, SYNTH_SYSTEM, payload, {r.record_id for r in records})


register("synth_k4_b_o3mini")(lambda h: m_synth(h, [("o3mini", False)] * 4))
register("synth_crowd_b_o3mini")(lambda h: m_synth(h, [(m, False) for m in CROWD]))
register("synth_mixed_b_o3mini")(lambda h: m_synth(h, [("o3mini", False)] * 2 + [("o3mini", True)] * 2))
register("synth_k1_b_o3mini")(lambda h: m_synth(h, [("o3mini", False)]))
register("writer_only_b_o3mini_r5")(lambda h: m_writer_only_b(h, "o3mini"))  # fresh-sample replicate (19.1)
SYNTH_CONFIGS = ("synth_k4_b_o3mini", "synth_crowd_b_o3mini", "synth_mixed_b_o3mini", "synth_k1_b_o3mini",
                 "writer_only_b_o3mini_r5")


# ================================================================ experiment 39 (loop.md 20.1): why information does
# not raise the score. Oracle configurations deliberately use the answer key to measure what information is worth.
# They are diagnostics, never methods: each run records oracle_diagnostic, target_free_asserted is false, and they live
# only in loop_diag/oracle_* (must_obey_check.py --oracle). read_web_chunks_b_o3mini is an ordinary target-free method.

ORACLE_HINTS = _H.EXPERIMENT_DIR / "loop_diag" / "oracle_hints.json"  # frozen before any generation (loop.md 20.1)
STUDY_TYPES = {
    "composition_change": "changing the alloy composition or adding elements",
    "processing_route": "the synthesis or manufacturing route, e.g. additive manufacturing, powder metallurgy, casting "
                        "or deposition",
    "heat_or_thermomechanical_treatment": "annealing, ageing, rolling, forging or another treatment after processing",
    "microstructure_architecture": "a designed microstructure, e.g. heterogeneous, lamellar, gradient or precipitate "
                                   "architecture",
    "surface_or_coating": "coatings, cladding or surface treatment",
    "computational_method_development": "a new machine-learning or computational method or tool",
    "simulation_study": "a DFT, molecular-dynamics, CALPHAD or phase-field study of a material",
    "experimental_characterization_study": "characterising the behaviour or mechanisms of a material without a "
                                           "designed change",
    "other": "another kind of study",
}
READER_SYSTEM = (
    "You read evidence passages from earlier papers before a materials-science hypothesis is written. Use only the "
    "passages and general materials-science knowledge from before the knowledge cutoff. (1) List the distinct "
    "approaches the passages report (interventions, processing routes, treatments, coatings, compositions, "
    "simulations or measurements): for each, what was done, to which material, what it achieved, its limitation, and "
    "the record IDs. (2) Choose the approach, or a combination of approaches from different passages, that most "
    "directly addresses the limitation the research question states for its own material system and conditions. "
    "Prefer an approach the passages show working on a related system that has not yet been applied to this system. "
    "Return JSON {\"approaches\": [{\"approach\": str, \"material\": str, \"result\": str, \"limitation\": str, "
    "\"record_ids\": [str]}], \"chosen_family\": one of " + ", ".join(t for t in STUDY_TYPES if t != "other")
    + ", \"lever\": \"the chosen approach in at most 25 words\", \"why\": \"one sentence\"}."
)


def oracle_hint(h: Harness) -> dict[str, Any]:
    return json.loads(ORACLE_HINTS.read_text())[h.case["paper_id"]]


def target_query(h: Harness) -> str:
    """The answer key's intervention, mediator and mechanism: the query of the oracle evidence selection."""
    t = h.case["hidden_target"]
    return " ".join(str(t.get(k) or "") for k in ("intervention", "structural_mediator", "mechanism"))


def read_then_write(h: Harness, records: list[Any], model: str = "o3mini") -> dict[str, Any]:
    """B3: a reader lists the approaches the passages report and chooses one; the incumbent writer builds on it."""
    payload = {"query": h.query, "knowledge_cutoff": h.cutoff,
               "eligible_evidence": h.evidence_payload(records, rx.record_cap("text_chunks"))}
    raw = h.ask("reader", model, READER_SYSTEM, payload)
    raw = raw if isinstance(raw, dict) else {}
    family = str(raw.get("chosen_family", "")).strip()
    h.notes["reading"] = {"approaches": len(raw.get("approaches") or []), "chosen_family": family,
                          "lever": str(raw.get("lever", ""))[:300], "why": str(raw.get("why", ""))[:400]}
    notes = {"chosen_family": family, "lever": str(raw.get("lever", ""))[:300], "why": str(raw.get("why", ""))[:400]}
    return write(h, notes, model, records=records, system=WRITER_B)


@register("oracle_targetpack_b_o3mini")
def m_oracle_targetpack(h: Harness) -> dict[str, Any]:
    """A4: the question-retrieved pack's retriever, corpus and budget, queried with the answer key. Every passage is
    still dated before the paper, and the payload guard stays on: only the selection is target-aware."""
    h.notes["oracle_diagnostic"] = "target_selected_evidence"
    h.source = "web"
    return write(h, {}, "o3mini", records=h.pack(target_query(h), "text_chunks"), system=WRITER_B)


@register("oracle_targetpack_read_b_o3mini")
def m_oracle_targetpack_read(h: Harness) -> dict[str, Any]:
    h.notes["oracle_diagnostic"] = "target_selected_evidence_with_reader"
    h.source = "web"
    return read_then_write(h, h.pack(target_query(h), "text_chunks"))


@register("read_web_chunks_b_o3mini")
def m_read_web_chunks(h: Harness) -> dict[str, Any]:
    """B3 on the ordinary question-retrieved pack (target-free)."""
    h.source = "web"
    return read_then_write(h, h.pack(h.query, "text_chunks"))


@register("oracle_hint_class_b_o3mini")
def m_oracle_hint_class(h: Harness) -> dict[str, Any]:
    h.notes["oracle_diagnostic"] = "hint_study_type"
    hint = oracle_hint(h)
    notes = {"chosen_family": hint["class"], "family_definition": STUDY_TYPES[hint["class"]]}
    return write(h, notes, "o3mini", system=WRITER_B)


@register("oracle_hint_lever_b_o3mini")
def m_oracle_hint_lever(h: Harness) -> dict[str, Any]:
    h.notes["oracle_diagnostic"] = "hint_lever"
    hint = oracle_hint(h)
    notes = {"chosen_family": hint["class"], "family_definition": STUDY_TYPES[hint["class"]], "lever": hint["lever"]}
    return write(h, notes, "o3mini", system=WRITER_B)


@register("oracle_hint_full_b_o3mini")
def m_oracle_hint_full(h: Harness) -> dict[str, Any]:
    h.notes["oracle_diagnostic"] = "hint_full_answer_key"
    h._forbidden = []  # the guard would (rightly) block the answer key; this is the declared exception (loop.md 20.1)
    return write(h, {"collaborator_plan": _render_key(h.case["hidden_target"])}, "o3mini", system=WRITER_B)


DIAG_CONFIGS = ("oracle_targetpack_b_o3mini", "oracle_targetpack_read_b_o3mini", "read_web_chunks_b_o3mini",
                "oracle_hint_class_b_o3mini", "oracle_hint_lever_b_o3mini", "oracle_hint_full_b_o3mini")


# ================================================================ experiment 40 (loop.md 21.1): a better agent.
# Experiment 39: the model copies details from evidence but not the decision, and the paper's approach is in most
# evidence packs but diluted. The agent chooses its approach from the evidence (the group of passages that most
# directly addresses the question's limitation; offline 35.6% match vs 18.9% for the model's own choice), then focuses
# the writing evidence on that approach (the practical counterpart of the oracle pack, which gained +0.13).

GROUP_SYSTEM = (
    "You read numbered passages from earlier materials-science papers retrieved for a research question. Group the "
    "passages by the main approach they report or discuss: a specific intervention (an element addition, processing "
    "route, heat treatment, coating or microstructure design) or a specific study design (a simulation method or a "
    "characterization study). Each passage belongs to at most one group; passages that report no approach go in no "
    "group. For each group, rate how directly the approach addresses the limitation the research question states "
    "(0 = not at all, 3 = directly). Return JSON {\"groups\": [{\"approach\": \"the specific approach in at most 12 "
    "words\", \"passage_ids\": [int], \"addresses_question\": int}]}."
)  # the offline prompt, verbatim (agent_offline.py)
AGENT_POOL_BUDGET = 64000
AGENT_WRITE_BUDGET = rx.EVIDENCE_BUDGET_CHARS


def agent_int(value: Any) -> int:
    try:
        return max(0, min(3, int(value)))
    except (TypeError, ValueError):
        return 0


def parse_groups(raw: Any, records: list[Any]) -> list[dict[str, Any]]:
    """Valid groups only: passage IDs that exist, each passage in at most one group, a non-empty approach."""
    groups, used = [], set()
    for g in (raw.get("groups") or []) if isinstance(raw, dict) else []:
        if not isinstance(g, dict) or not str(g.get("approach", "")).strip():
            continue
        ids = []
        for i in g.get("passage_ids") or []:
            if isinstance(i, int) and 1 <= i <= len(records) and i not in used:
                ids.append(i)
                used.add(i)
        if ids:
            members = [records[i - 1] for i in ids]
            groups.append({"approach": str(g["approach"]).strip()[:200], "records": members,
                           "papers": len({r.paper_id for r in members}), "addresses": agent_int(g.get("addresses_question"))})
    return groups


def choose_group(groups: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The pre-registered rule: most direct, then more papers, then more passages, then first listed."""
    if not groups:
        return None
    return max(groups, key=lambda g: (g["addresses"], g["papers"], len(g["records"])))


def choose_from_evidence(h: Harness, model: str = "o3mini") -> dict[str, Any] | None:
    pool = top_text(h, h.query, AGENT_POOL_BUDGET)
    payload = {"research_question": h.query,
               "passages": [{"id": n + 1, "text": r.text[:rx.record_cap("text_chunks")]} for n, r in enumerate(pool)]}
    groups = parse_groups(h.ask("chooser", model, GROUP_SYSTEM, payload), pool)
    chosen = choose_group(groups)
    h.notes["choice"] = {"pool_records": len(pool), "groups": len(groups),
                         "chosen": None if chosen is None else {"approach": chosen["approach"],
                                                               "addresses": chosen["addresses"],
                                                               "papers": chosen["papers"],
                                                               "passages": len(chosen["records"])}}
    return chosen


def focused_pack(h: Harness, search: str, first: list[Any], budget: int = AGENT_WRITE_BUDGET) -> list[Any]:
    """The given records first, then the whole corpus ranked by BM25 against the search text, within the budget."""
    cap = rx.record_cap("text_chunks")
    max_records = max(1, round(rx.MAX_RECORDS * budget / rx.EVIDENCE_BUDGET_CHARS))
    packed: list[Any] = []
    used = 0
    for record in list(first) + _pcd_ranked(h, search, "text_chunks"):
        if any(record.record_id == p.record_id for p in packed):
            continue
        size = min(len(record.text), cap)
        if used + size > budget:
            continue
        packed.append(record)
        used += size
        if len(packed) >= max_records or used >= budget - 200:
            break
    for record in packed:
        h.seen[record.record_id] = record
    h.notes["focused_pack"] = {"records": len(packed), "papers": len({r.paper_id for r in packed}), "chars": used,
                               "from_chosen_group": sum(1 for r in packed if r in first)}
    return packed


def m_agent(h: Harness, choose: bool, ground: bool, model: str = "o3mini") -> dict[str, Any]:
    h.source = "web"
    if choose:
        chosen = choose_from_evidence(h, model)
        if chosen is None:  # recorded fallback: the incumbent writer, closed-book
            h.notes["fallback"] = "no valid group"
            return write(h, {}, model, system=WRITER_B)
        notes = {"lever": chosen["approach"],
                 "why": f"the approach that the earlier literature reports most directly for the stated limitation "
                        f"({len(chosen['records'])} passages from {chosen['papers']} papers)"}
        search, first = f"{chosen['approach']} {h.query}", chosen["records"]
    else:
        draft = write(h, {}, model, role="draft", system=WRITER_B)
        notes = {"lever": str(draft.get("intervention", ""))[:300]}
        search = " ".join(str(draft.get(f) or "") for f in ("intervention", "structural_mediator", "mechanism"))
        first = []
    records = focused_pack(h, search, first) if ground else None
    return write(h, notes, model, records=records, system=WRITER_B)


register("agent_choose_ground_b_o3mini")(lambda h: m_agent(h, choose=True, ground=True))
register("agent_choose_only_b_o3mini")(lambda h: m_agent(h, choose=True, ground=False))
register("agent_draft_ground_b_o3mini")(lambda h: m_agent(h, choose=False, ground=True))
AGENT_CONFIGS = ("agent_choose_ground_b_o3mini", "agent_choose_only_b_o3mini", "agent_draft_ground_b_o3mini")
