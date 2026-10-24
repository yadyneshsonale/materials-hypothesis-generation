"""Experiment 19: audit of answer leakage in the temporal benchmark queries.

For every case and query level it measures (1) which extracted roles the query was written from (the case builder
records them in source_role_refs) and whether any are result roles of the held-out paper, and (2) the share of the
hidden target's intervention, structural-mediator and mechanism content words that appear in the query text. It then
correlates that overlap with the GPT-5.6 reconstruction score of each method per unit.
"""

from __future__ import annotations

import json
import re
import statistics
from typing import Any

import citegraph as cg
import rubric_eval as rx
from failure_analysis import spearman
from hypothesis_evidence_v2 import atomic_json
from temporal_eval_v3 import EXPERIMENT_DIR, QUERY_LEVELS
from temporal_hypothesis_benchmark import QUERY_ROLE_TYPES

OUT = EXPERIMENT_DIR / "query_leakage"
ANSWER_FIELDS = ("intervention", "structural_mediator", "mechanism")
ARMS = ("closed_book", "text_chunks", "card", "card_systemmatch", "graph_profiles", "graph_profiles_systemmatch",
        "graph_tool_agent")
STOP = set("""the and for with from that this into within between than their which while where when what given
propose specify expected must aim using use via based under over also such both each more less can could would should
may might will its not are was were been has have how does one two new study effect role case experiment intervention
regime trade off compared baseline approach mechanism hypothesis""".split())


def content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9][a-z0-9\-\.]*", str(text).lower()) if len(w) > 2 and w not in STOP}


def answer_overlap(query: str, target: dict[str, Any]) -> float:
    answer = content_words(" ".join(str(target.get(k, "")) for k in ANSWER_FIELDS))
    return len(answer & content_words(query)) / len(answer) if answer else 0.0


def result_roles(refs: list[str]) -> list[str]:
    roles = [r.split(":")[1] if r.count(":") >= 2 else r for r in refs]
    return sorted({r for r in roles if r not in QUERY_ROLE_TYPES})


def audit() -> dict[str, Any]:
    units = {}
    for case in rx.cases().values():
        for level in QUERY_LEVELS:
            query = case["queries"][level]
            units[(case["paper_id"], level)] = {
                "overlap": round(answer_overlap(query["text"], case["hidden_target"]), 3),
                "result_roles_used": result_roles(query.get("source_role_refs", [])),
                "builder_flagged_risks": len(case.get("leakage_audit", {}).get("remaining_risks", [])),
            }
    by_level = {level: {
        "overlap_mean": round(statistics.fmean(u["overlap"] for k, u in units.items() if k[1] == level), 3),
        "overlap_max": max(u["overlap"] for k, u in units.items() if k[1] == level),
        "queries_using_result_roles": sum(bool(u["result_roles_used"]) for k, u in units.items() if k[1] == level),
        "queries": sum(1 for k in units if k[1] == level)} for level in QUERY_LEVELS}
    records = cg.load_records()
    correlation = {}
    for arm in ARMS:
        scores = cg.unit_scores(records, arm, "gpt")
        keys = sorted(set(scores) & set(units))
        correlation[arm] = {
            "units": len(keys),
            "spearman_all": round(spearman([units[k]["overlap"] for k in keys], [scores[k] for k in keys]), 3),
            **{f"spearman_{level}": round(spearman([units[k]["overlap"] for k in keys if k[1] == level],
                                                   [scores[k] for k in keys if k[1] == level]), 3)
               for level in QUERY_LEVELS}}
    result = {"by_level": by_level, "score_correlation_gpt56": correlation,
              "units": {f"{p}__{lvl}": u for (p, lvl), u in sorted(units.items())}}
    atomic_json(OUT / "analysis.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps({k: v for k, v in audit().items() if k != "units"}, indent=1))
