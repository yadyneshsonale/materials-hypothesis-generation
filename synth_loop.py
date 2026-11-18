"""Experiment 48 (loop.md 27.7): writers that combine or extend several papers instead of restating one.

Experiment 47 found that the focused-retrieval writer (rx_r) mostly restates one retrieved paper's result (non-copying
1.89 of 5; the overall idea of 237 of 270 hypotheses traced to the passages). Two new writers use rx_r's evidence pack
(focused retrieval, 64,000 characters) unchanged and change only how the hypothesis is written:

  synth_a   one call: WRITER_B's conservative rules plus synthesis rules (build on at least two papers, or carry a
            result to a new material or regime with a reason; never restate a passage's result, repeat what a paper
            already did, or propose what a paper already proposes)
  synth_b   two calls: o3-mini first maps what the passages already establish, what has already been done or proposed,
            and the gaps and conflicts between papers; the writer then proposes a hypothesis that is not on the
            "already done or proposed" list, targets a gap or conflict, and combines several papers.

No prompt is an evaluating judge's prompt (must_obey.md 6.12): the wording is the writer's own, and no judge model is
called during generation.
"""

from __future__ import annotations

from typing import Any

import loop_methods as LM
import refine_loop as RL
from hypo_loop import Harness, register

_SYNTH_RULES = (
    "Build a hypothesis that goes beyond the supplied evidence rather than repeating it:\n"
    "- Build it from findings of at least two different papers in the evidence, or carry a result reported for one "
    "material or regime to a different one, and say why it should hold there.\n"
    "- Do not restate a result a passage already reports as if it were a prediction, do not propose the study a "
    "paper already carried out on the same or a very similar material, and do not propose what a paper already "
    "suggests as future work.\n"
    "- Do not fall back on a textbook or generic approach; the proposal should be specific to this question.\n"
    "- The hypothesis must still answer the question within its constraints and be physically sound.\n"
    "In the uncertainty field, name the passages you combined or extended and what is new in your proposal.\n"
)
SYNTH_A = (
    "You are a materials-science hypothesis agent in a chronological benchmark. Use the supplied temporally eligible "
    "evidence. Do not claim knowledge of the held-out paper. Predict the direction and approximate size of effects "
    "only as far as the evidence and your knowledge support; if support is insufficient, state the uncertainty "
    "instead of inventing support or precise values.\n\n" + _SYNTH_RULES +
    "\nReturn one falsifiable hypothesis as JSON:\n" + LM.SCHEMA + "\nEvidence IDs must be copied from the supplied "
    "records."
)
MAP_SYSTEM = (
    "You are a materials scientist preparing to propose a new study for a research question. Read the supplied "
    "evidence: passages from earlier papers, each with a record ID, its paper's title and section. Do not write a "
    "hypothesis yet. Map what is already known, so that the next study can go beyond it:\n"
    "- \"done\": every study or approach the passages report for this kind of problem: the material, what was changed "
    "or studied, the result, and the record IDs;\n"
    "- \"proposed\": studies the passages themselves suggest as next steps or future work, with record IDs;\n"
    "- \"gaps\": questions the passages leave open that bear on the research question (untested materials, regimes, "
    "combinations or mechanisms);\n"
    "- \"conflicts\": places where passages disagree or where one paper's finding would change another's conclusion, "
    "with record IDs.\n"
    "Return JSON {\"done\": [{\"material\": str, \"study\": str, \"result\": str, \"record_ids\": [str]}], "
    "\"proposed\": [{\"study\": str, \"record_ids\": [str]}], \"gaps\": [str], \"conflicts\": [{\"conflict\": str, "
    "\"record_ids\": [str]}]}."
)
SYNTH_B = (
    "You are a materials-science hypothesis agent in a chronological benchmark. You receive the research question, "
    "the knowledge cutoff, your own map of what the earlier papers already did, proposed, left open and disagree on, "
    "and the evidence the map was built from. Do not claim knowledge of the held-out paper. Predict the direction and "
    "approximate size of effects only as far as the evidence and your knowledge support; if support is insufficient, "
    "state the uncertainty instead of inventing support or precise values.\n\n"
    "Propose a study that is not on the map's \"done\" or \"proposed\" lists, and that targets one of its gaps or "
    "conflicts.\n" + _SYNTH_RULES +
    "\nReturn one falsifiable hypothesis as JSON:\n" + LM.SCHEMA + "\nEvidence IDs must be copied from the supplied "
    "records."
)


def literature_map(h: Harness, records: list[Any]) -> dict[str, Any]:
    raw = h.ask("map", "o3mini", MAP_SYSTEM, {"query": h.query, "knowledge_cutoff": h.cutoff,
                                               "eligible_evidence": RL.items(h, records)})
    raw = raw if isinstance(raw, dict) else {}
    out = {k: raw.get(k) if isinstance(raw.get(k), list) else [] for k in ("done", "proposed", "gaps", "conflicts")}
    h.notes["literature_map"] = {k: len(v) for k, v in out.items()}
    return out


def m_synth(h: Harness, mapped: bool) -> dict[str, Any]:
    records = RL.start_pack(h, True, RL.BUDGET)
    allowed = {r.record_id for r in records}
    payload: dict[str, Any] = {"query": h.query, "knowledge_cutoff": h.cutoff}
    if mapped:
        payload["literature_map"] = literature_map(h, records)
    payload["eligible_evidence"] = RL.items(h, records)
    return h.generate_final("writer", "o3mini", SYNTH_B if mapped else SYNTH_A, payload, allowed,
                            citation_repair="filter")


register("synth_a")(lambda h: m_synth(h, mapped=False))
register("synth_b")(lambda h: m_synth(h, mapped=True))
SYNTH_ARMS = ("synth_a", "synth_b")
