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
