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
    key = f"{h.case['paper_id']}:{representation}"
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
