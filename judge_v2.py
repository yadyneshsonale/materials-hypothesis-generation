"""Measurement v2 (experiment 42, loop.md 23.1): an anchored, evidence-blind judge for the four reconstruction
dimensions. A secondary measurement, validated before use (sanity controls, monotonic partial credit, test-retest);
the original judge (temporal_hypothesis_benchmark._SCORE_SYSTEM) stays the primary metric.

Why: the original prompt gives no per-dimension anchors, and a hypothesis with the paper's kind of intervention but a
different lever scored lower on intervention (0.149) than one with a different kind (0.173). The cited evidence is
also visible while the reconstruction dimensions are scored.
"""

from __future__ import annotations

import json
from typing import Any

import llm_client as lc
from stage_metrics import CROSS_JUDGE

DIMENSIONS = ("intervention_reconstruction", "condition_agreement", "mechanism_agreement", "outcome_agreement")
ANCHORED_SYSTEM = """You evaluate how closely a generated materials-science hypothesis reconstructs the study that a \
hidden paper actually carried out. You see the research question, the paper's actual study (hidden target) and the \
hypothesis. Judge scientific agreement only: do not reward wording overlap, length, hedging or citations. For each \
dimension, first write one sentence comparing the hypothesis with the target, then give an integer score using \
these anchors.

intervention_reconstruction (what is changed or studied):
0 = a different kind of intervention or study (for example a composition change when the paper used a coating, a \
processing route or a simulation);
1 = the same kind of intervention or study, but a different specific lever (for example a different element, coating \
type, processing route or simulation method);
2 = the same lever with different specifics (amount, route details, parameters or material system);
3 = the same lever with mostly the same specifics; only minor differences;
4 = essentially the paper's intervention.

condition_agreement (processing settings and test or operating conditions):
0 = no conditions, or conditions that contradict the paper's regime;
1 = the same broad regime (for example high-temperature oxidation in air, or mechanical testing at elevated \
temperature) without the paper's specifics;
2 = the paper's main regime, approximately (temperature range, atmosphere or environment, loading mode, or the main \
processing step);
3 = most of the paper's specific conditions;
4 = essentially the paper's conditions.

mechanism_agreement:
0 = a different or contradictory mechanism, or none;
1 = the same general class of mechanism (for example protective oxide formation, solid-solution strengthening or phase \
stabilisation) without the paper's specific pathway;
2 = the paper's main mechanism, with different or missing intermediate steps or structural mediators;
3 = the paper's mechanism with minor differences;
4 = essentially the paper's mechanism, including its structural mediator.

outcome_agreement (the predicted result):
0 = no prediction about the property the paper measured, or the opposite direction;
1 = the right property and direction in general terms only;
2 = the right property and direction, with an approximately right size or the right comparison;
3 = the paper's outcomes with minor differences;
4 = essentially the paper's result.

Return JSON {"rationale": {"intervention_reconstruction": str, "condition_agreement": str, "mechanism_agreement": str, \
"outcome_agreement": str}, "scores": {"intervention_reconstruction": int, "condition_agreement": int, \
"mechanism_agreement": int, "outcome_agreement": int}}."""
HIDDEN_FIELDS = ("supporting_evidence_ids", "conflicting_evidence_ids", "citation_validation")


def blind_hypothesis(generation: dict[str, Any]) -> dict[str, Any]:
    """The hypothesis without citation lists or citation bookkeeping (evidence-blind reconstruction)."""
    return {k: v for k, v in generation.items() if k not in HIDDEN_FIELDS}


def validate(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or not isinstance(raw.get("scores"), dict):
        raise ValueError("v2 judgment without scores")
    scores = {}
    for dim in DIMENSIONS:
        value = raw["scores"].get(dim)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value or not 0 <= value <= 4:
            raise ValueError(f"v2 judgment: invalid {dim} = {value!r}")
        scores[dim] = int(value)
    rationale = raw.get("rationale") if isinstance(raw.get("rationale"), dict) else {}
    return {"scores": scores, "rationale": {d: str(rationale.get(d, ""))[:500] for d in DIMENSIONS}}


def payload(query: str, target: dict[str, Any], generation: dict[str, Any]) -> str:
    return json.dumps({"research_question": query, "hidden_target": target,
                       "generated_hypothesis": blind_hypothesis(generation)}, ensure_ascii=False)


def judge(judge_name: str, query: str, target: dict[str, Any], generation: dict[str, Any]) -> dict[str, Any]:
    """judge_name: "gpt56" (GPT-5.6; JUDGE_TRAPI_ENDPOINT selects the instance) or "deepseek"."""
    user = payload(query, target, generation)
    last: Exception | None = None
    for _ in range(3):  # an invalid score is re-asked, never filled in
        if judge_name == "gpt56":
            raw = lc.judge_chat_json(ANCHORED_SYSTEM, user, max_tokens=8000)
            identity = lc.judge_info()
        else:
            raw = lc.trapi_chat_json(CROSS_JUDGE["deployment"], ANCHORED_SYSTEM, user, max_tokens=6000,
                                     token_field=CROSS_JUDGE["token_field"], temperature=CROSS_JUDGE["temperature"],
                                     retries=8)
            identity = f"trapi:{CROSS_JUDGE['deployment']}"
        try:
            return {"judge": identity, "rubric": "v2-anchored-evidence-blind", **validate(raw)}
        except ValueError as error:
            last = error
    raise ValueError(f"no valid v2 judgment after 3 attempts: {last}")


def recon(scores: dict[str, int]) -> float:
    return sum(scores[d] for d in DIMENSIONS) / len(DIMENSIONS)
