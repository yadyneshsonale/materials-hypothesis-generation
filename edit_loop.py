"""Experiment 45 (loop.md 26.1): keep the writer's lever and fix how the hypothesis is written (E); give the writer
the research programme's domain when the question does not name the alloy class (D).

Why (loop.md 26.1, from the 15,600 judged hypotheses of experiments 21-42):
- Every instruction added to the writer's prompt moved o3-mini off its own best guess and lowered intervention
  agreement (experiments 41, 42). E therefore never touches the writer: a second call edits the finished hypothesis
  and code keeps its lever, its evidence IDs and every field the edit may not change.
- 44 of the 135 questions do not name a high-entropy alloy; on them the score is about 0.25 lower, and hypotheses
  that bring in such an alloy score higher within the same question. D states the programme's domain on those
  questions only, so the writer's prompt is unchanged wherever the question already names the class.

Arms (o3-mini; the 64,000-character packs of experiment 44):
  edit_rx_base         E on the rx_base runs (stage 1 unchanged; one o3-mini editor call)
  edit_rx_r            E on the rx_r runs
  domain_rx_base       rx_base's writer with the domain context, on questions that do not name the alloy class
  domain_rx_r          rx_r's writer with the domain context, on the same questions
  domain_edit_rx_base  E on domain_rx_base
  domain_edit_rx_r     E on domain_rx_r
The combined agent is E on questions that name the alloy class and D+E on the others (edit_experiment.py composes
it); D alone is the base on the former and D on the latter.
"""

from __future__ import annotations

import re
from typing import Any

import hypo_loop as H
import loop_methods as LM
import refine_loop as RL
from hypo_loop import Harness, register
from temporal_hypothesis_benchmark import _read_json, _validate_generation

ALLOY_CLASS = re.compile(r"high[- ]entropy|medium[- ]entropy|multi[- ]?principal|compositionally complex|"
                         r"complex concentrated|\bHEAs?\b|\bMPEAs?\b|\bRHEAs?\b|\bCCAs?\b|\bMEAs?\b|entropy", re.I)
DOMAIN_CONTEXT = ("The research group asking this question works on high-entropy (multi-principal-element) alloys "
                  "for high-temperature applications.")
EDITABLE = ("hypothesis", "intervention", "conditions", "structural_mediator", "mechanism")
ELEMENTS = frozenset("Al Co Cr Cu Fe Hf Mn Mo Nb Ni Re Ru Si Sn Ta Ti Zr V W Y Mg Zn Ga Ge Sc La Ce Pd Pt Ir Rh Os "
                     "Ag Au Li Be Ca Gd Er Nd".split())
ELEMENT_NAMES = {"aluminium": "Al", "aluminum": "Al", "cobalt": "Co", "chromium": "Cr", "copper": "Cu", "iron": "Fe",
                 "hafnium": "Hf", "manganese": "Mn", "molybdenum": "Mo", "niobium": "Nb", "nickel": "Ni",
                 "rhenium": "Re", "ruthenium": "Ru", "silicon": "Si", "tin": "Sn", "tantalum": "Ta",
                 "titanium": "Ti", "zirconium": "Zr", "vanadium": "V", "tungsten": "W", "yttrium": "Y",
                 "magnesium": "Mg", "zinc": "Zn", "scandium": "Sc", "lanthanum": "La", "cerium": "Ce",
                 "palladium": "Pd", "platinum": "Pt", "iridium": "Ir", "silver": "Ag", "gold": "Au",
                 "lithium": "Li", "boron": "B", "carbon": "C", "nitrogen": "N", "oxygen": "O"}
STOP = frozenset("with that this from into than then they their them were been being have such some more most "
                 "less very also only each both other which while where when what will would could should using "
                 "used about after before between under over within without approximately approx around nominal "
                 "minor small large slight slightly moderate controlled specific given level levels amount "
                 "content contents relative compared hour hours minute minutes second seconds degree degrees "
                 "celsius kelvin percent atomic weight volume fraction thick thickness".split())
NUMBER = re.compile(r"\d+(?:\.\d+)?")
MIN_RETENTION = 0.5  # share of the draft intervention's content words the edit must keep (loop.md 26.1)

EDIT_SYSTEM = (
    "You are the final editor of a materials-science hypothesis written for a chronological benchmark. You receive "
    "the research question, the knowledge cutoff, the draft hypothesis as JSON and the evidence passages it cites. "
    "You do not know the held-out paper. Return the same JSON with these edits only:\n"
    "1. Keep the draft's chosen intervention: the same lever, the same elements, phases, processing route or "
    "treatment, and the same material system. Never replace it with a different idea, never add a second lever and "
    "never list alternatives.\n"
    "2. Remove numeric values (compositions, temperatures, durations, sizes, fractions, magnitudes) from the "
    "intervention, conditions and structural_mediator fields unless the question or a cited passage states them; "
    "describe such quantities qualitatively instead (for example \"a minor addition\" or \"at the service "
    "temperature the question names\").\n"
    "3. Keep the conditions to the regime the question states (temperature range, atmosphere, loading mode).\n"
    "4. If the draft's mechanism acts through a process that multi-principal-element effects directly control "
    "(diffusion-controlled kinetics: sluggish diffusion; solid-solution strengthening: severe lattice distortion; "
    "ordering: chemical short-range order; phase stability: multicomponent mixing), name that effect in the "
    "mechanism. Otherwise leave the mechanism unchanged.\n"
    "5. If the hypothesis field does not already say how the intervention acts, add the mediator or mechanism to it "
    "in a few words; keep it one readable sentence.\n"
    "Keep every other field, every evidence ID and the falsification experiment exactly as they are. Add no new "
    "claims, citations or numbers. Return the complete JSON:\n" + LM.SCHEMA
)
RETRY_INSTRUCTION = ("Your previous edit changed the draft's intervention ({problem}). Edit again: keep the draft's "
                     "lever, elements, processing route and material exactly, and apply only the listed edits.")


def names_alloy_class(query: str) -> bool:
    return bool(ALLOY_CLASS.search(query))


def elements(text: str) -> set[str]:
    """Element symbols in formula-like tokens (HfMoTaTiZr, Al2O3, Cr) and element names (chromium)."""
    out = set()
    for token in re.findall(r"[A-Za-z0-9.]+", text):
        if re.fullmatch(r"(?:[A-Z][a-z]?(?:\d+(?:\.\d+)?)?)+", token):
            out |= {part for part in re.findall(r"[A-Z][a-z]?", token) if part in ELEMENTS}
    for word in re.findall(r"[a-z]+", text.lower()):
        if word in ELEMENT_NAMES:
            out.add(ELEMENT_NAMES[word])
    return out


def content_words(text: str) -> set[str]:
    return {w[:6] for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in STOP}


def lever_check(draft: dict[str, Any], edited: dict[str, Any], query: str) -> dict[str, Any]:
    """The edit keeps the draft's lever: no element of the draft intervention is dropped, none is added that the
    draft or the question does not name, and most of the intervention's content words stay."""
    before, after = str(draft.get("intervention", "")), str(edited.get("intervention", ""))
    dropped = sorted(elements(before) - elements(after))
    added = sorted(elements(after) - elements(before) - elements(str(draft.get("material_initial_state", "")))
                   - elements(query))
    words = content_words(before)
    retention = len(words & content_words(after)) / len(words) if words else 1.0
    problems = []
    if dropped:
        problems.append(f"dropped {', '.join(dropped)}")
    if added:
        problems.append(f"added {', '.join(added)}")
    if retention < MIN_RETENTION:
        problems.append(f"kept {retention:.0%} of its content words")
    return {"ok": not problems, "problem": "; ".join(problems), "dropped": dropped, "added": added,
            "retention": round(retention, 3)}


def apply_edit(draft: dict[str, Any], raw: Any, query: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """The draft with only the editable fields replaced; every other field and the evidence IDs stay the draft's."""
    edited = dict(draft)
    if isinstance(raw, dict) and isinstance(raw.get("draft_hypothesis"), dict):
        raw = raw["draft_hypothesis"]
    if isinstance(raw, dict):
        for field in EDITABLE:
            value = raw.get(field)
            if isinstance(value, str) and value.strip():
                edited[field] = value.strip()
    check = lever_check(draft, edited, query)
    # An unchanged answer is accepted: the draft needed none of the edits.
    return edited, {**check, "changed": [f for f in EDITABLE if edited.get(f) != draft.get(f)]}


def numbers_outside(text: str, sources: str) -> int:
    allowed = set(NUMBER.findall(sources))
    return len(set(NUMBER.findall(text)) - allowed)


def stage1_run(h: Harness, stage1: str) -> dict[str, Any]:
    path = H.OUT / stage1 / "runs" / f"{H.run_id(h.case['paper_id'], h.level, stage1, h.sample)}.json"
    run = _read_json(path)
    if run.get("status") != "ok" or run.get("query") != h.query:
        raise RuntimeError(f"stage-1 run {run.get('run_id')} is not usable")
    return run


def m_edit(h: Harness, stage1: str, focused: bool) -> dict[str, Any]:
    base = stage1_run(h, stage1)
    records = RL.start_pack(h, focused, RL.BUDGET)  # the same pack as stage 1, so the run records what shaped it
    if sorted(h.seen) != base["seen_ids"]:
        raise RuntimeError("the rebuilt pack differs from stage 1")
    for role, model in base["models"].items():
        h.models.setdefault(role, model)
    draft = {k: v for k, v in base["generation"].items() if k != "citation_validation"}
    cited_ids = sorted(set(draft.get("supporting_evidence_ids", []) + draft.get("conflicting_evidence_ids", [])))
    cited = [h.seen[i] for i in cited_ids if i in h.seen]
    shown = RL.items(h, cited)
    payload: dict[str, Any] = {"query": h.query, "knowledge_cutoff": h.cutoff, "draft_hypothesis": draft,
                               "cited_evidence": shown}
    h.notes["stage1"] = {"method": stage1, "run_id": base["run_id"], "llm_calls": base.get("llm_calls"),
                         "chars_in": base.get("chars_in")}
    attempts = []
    final = dict(draft)
    for attempt in range(2):
        raw = h.ask("editor" if attempt == 0 else "editor_retry", "o3mini", EDIT_SYSTEM, payload)
        edited, check = apply_edit(draft, raw, h.query)
        attempts.append(check)
        if check["ok"]:
            final = edited
            break
        payload = {**payload, "instruction": RETRY_INSTRUCTION.format(problem=check["problem"])}
    sources = " ".join([h.query] + [str(i["evidence"]) for i in shown])
    h.notes["edit"] = {
        "applied": attempts[-1]["ok"], "attempts": attempts,
        "invented_numbers_before": {f: numbers_outside(str(draft.get(f, "")), sources)
                                    for f in ("intervention", "conditions", "structural_mediator")},
        "invented_numbers_after": {f: numbers_outside(str(final.get(f, "")), sources)
                                   for f in ("intervention", "conditions", "structural_mediator")},
    }
    allowed = {r.record_id for r in records}
    out = H._schema_only(_validate_generation(final, allowed))
    out["citation_validation"] = base["generation"].get("citation_validation", {"status": "valid",
                                                                                 "removed_unknown_ids": []})
    return out


def m_domain(h: Harness, focused: bool) -> dict[str, Any]:
    """WRITER_B on the experiment-44 pack, with the programme's domain stated beside the question."""
    if names_alloy_class(h.query):
        raise RuntimeError("the domain arms run only on questions that do not name the alloy class")
    records = RL.start_pack(h, focused, RL.BUDGET)
    allowed = {r.record_id for r in records}
    payload = {"query": h.query, "knowledge_cutoff": h.cutoff, "research_context": DOMAIN_CONTEXT,
               "analysis_notes": {}, "eligible_evidence": RL.items(h, records)}
    h.notes["research_context"] = DOMAIN_CONTEXT
    return h.generate_final("writer", "o3mini", LM.WRITER_B, payload, allowed, citation_repair="filter")


DOMAIN = {"domain_rx_base": False, "domain_rx_r": True}
STAGE1 = {"edit_rx_base": ("rx_base", False), "edit_rx_r": ("rx_r", True),
          "domain_edit_rx_base": ("domain_rx_base", False), "domain_edit_rx_r": ("domain_rx_r", True)}
for _name, _focused in DOMAIN.items():
    register(_name)(lambda h, _f=_focused: m_domain(h, _f))
for _name, (_stage1, _focused) in STAGE1.items():
    register(_name)(lambda h, _s=_stage1, _f=_focused: m_edit(h, _s, _f))
EDIT_ARMS = tuple(DOMAIN) + tuple(STAGE1)
