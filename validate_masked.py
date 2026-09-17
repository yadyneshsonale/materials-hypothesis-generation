"""Tier 3 validation: masked-paper recovery.

Withhold one real paper entirely from the graph, derive a goal from ONLY its
problem_motivation (its actual hypothesis/mechanism/results stay hidden), run
the normal agent pipeline against the masked graph, then judge the resulting
candidates against the withheld paper's real hypothesis_statement + mechanism_
principle. This is the concrete version of the "masked-node" eval design from
the framework, run against the actual agent instead of an isolated extractor.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from graph_build import build_graph
from hypothesis_agent import compose, critique, retrieve
from llm_client import LLMError, chat_json

_JUDGE_SYSTEM = """You are scoring whether a candidate hypothesis - generated WITHOUT
ever seeing the withheld paper - recovers what that paper actually found. Score 1-5
(5=excellent recovery) on:
- concept_overlap: same core mechanism/idea?
- specificity_match: does it get close to the withheld paper's actual claim, not just
  a generic plausible-sounding statement?

Return JSON: {"concept_overlap": 1-5, "specificity_match": 1-5, "justification": "..."}"""


def judge_recovery(candidate_hyp: str, candidate_mech: str, gold_hyp: str, gold_mech: str, retries: int = 6) -> dict | None:
    user = (
        f"WITHHELD PAPER'S REAL HYPOTHESIS: {gold_hyp}\nWITHHELD PAPER'S REAL MECHANISM: {gold_mech}\n\n"
        f"CANDIDATE HYPOTHESIS (generated without seeing the above): {candidate_hyp}\n"
        f"CANDIDATE MECHANISM: {candidate_mech}"
    )
    for attempt in range(retries):
        try:
            return chat_json(_JUDGE_SYSTEM, user, max_tokens=400)
        except LLMError as e:
            wait = 2 ** attempt
            print(f"[masked] WARN: judge call failed (attempt {attempt + 1}/{retries}): {e} - retrying in {wait}s")
            time.sleep(wait)
    print(f"[masked] ERROR: judge call failed after {retries} attempts, giving up")
    return None


def run_masked_test(outputs_dir: Path, held_out_paper: str) -> None:
    record = json.loads((outputs_dir / f"{held_out_paper}.json").read_text())
    problem_items = record["reconciled_by_role"].get("problem_motivation", [])
    hyp_items = record["reconciled_by_role"].get("hypothesis_statement", [])
    mech_items = record["reconciled_by_role"].get("mechanism_principle", [])

    if not problem_items or not hyp_items:
        print(f"[masked] {held_out_paper} lacks problem_motivation or hypothesis_statement, skipping")
        return

    goal = problem_items[0]["content"]
    gold_hyp = " ".join(it["content"] for it in hyp_items[:2])
    gold_mech = " ".join(it["content"] for it in mech_items[:2])

    print(f"[masked] held-out paper: {held_out_paper}")
    print(f"[masked] goal (from its problem_motivation, everything else withheld): {goal}")
    print(f"[masked] REAL (withheld) hypothesis: {gold_hyp}")
    print(f"[masked] REAL (withheld) mechanism: {gold_mech}")

    g = build_graph(outputs_dir, exclude={held_out_paper})
    inspirations = retrieve(goal, g)
    print(f"[masked] retrieved {len(inspirations)} nodes from the REMAINING {len({n.paper_id for n in inspirations})} papers (held-out paper excluded)")

    candidates = compose(goal, inspirations, n=2)
    for cand in candidates:
        print(f"\n[masked] CANDIDATE: {cand.get('hypothesis')}")
        result = judge_recovery(cand.get("hypothesis", ""), cand.get("mechanism", ""), gold_hyp, gold_mech)
        print(f"[masked] RECOVERY SCORE: {result}")


if __name__ == "__main__":
    outputs_dir_arg = Path(sys.argv[1])
    paper_arg = sys.argv[2]
    run_masked_test(outputs_dir_arg, paper_arg)
