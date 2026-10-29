"""Tests for the evidence-choosing agent (experiment 40, loop.md 21.1)."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import hypo_loop as H
import loop_methods as LM
from temporal_hypothesis_benchmark import RetrievalRecord

CASE = {"paper_id": "PMCT", "publication_date": "2024-06-01", "split": "validation",
        "queries": {lvl: {"text": "Improve the oxidation resistance of cast HfNbTaTiZr at 1000 C without losing ductility."}
                    for lvl in ("broad", "problem_constrained", "expert_context")},
        "hidden_target": {"intervention": "Ink-extrusion three-dimensional printing followed by a slurry silicide coating",
                          "mechanism": "a self-healing mixed oxide grown from the silicide coating blocks oxygen"}}
TOPICS = ("silicide coating oxygen barrier", "aluminium addition alumina scale", "chromium addition chromia scale",
          "grain refinement creep", "zirconia thermal barrier")


def pool(kind: str) -> list[RetrievalRecord]:
    return [RetrievalRecord(f"P{i}::web::{j:03d}::results", f"P{i}", "2020-01-01", "web:Results", f"{t} " * 80,
                            {"source": "web"}) for i, t in enumerate(TOPICS) for j in range(8)]


class Responder:
    def __init__(self, groups: list[dict] | None = None) -> None:
        self.calls: list[tuple[str, str, dict]] = []
        self.groups = groups

    def __call__(self, role, model, system, payload, max_out=None):
        self.calls.append((role, model, payload))
        if role == "chooser":
            return {"groups": self.groups if self.groups is not None else [
                {"approach": "aluminium addition", "passage_ids": [1, 2, 3], "addresses_question": 2},
                {"approach": "silicide coating", "passage_ids": [4, 5], "addresses_question": 3},
                {"approach": "zirconia barrier", "passage_ids": [6], "addresses_question": 3}]}
        return {"hypothesis": "A coating protects the alloy.", "intervention": "silicide coating applied by slurry",
                "structural_mediator": "silica-rich scale", "mechanism": "oxide scale blocks oxygen",
                "supporting_evidence_ids": [], "conflicting_evidence_ids": []}


def run(method: str, responder: Responder) -> H.Harness:
    h = H.Harness(CASE, "broad", 1)
    with patch.object(h, "pool", side_effect=pool), \
            patch.object(H.Harness, "ask", autospec=True, side_effect=lambda self, *a, **k: responder(*a, **k)):
        H.METHODS[method](h)
    return h


class ParsingTests(unittest.TestCase):
    def test_parse_groups_keeps_valid_unique_passages(self) -> None:
        records = pool("text_chunks")[:5]
        raw = {"groups": [{"approach": "A", "passage_ids": [1, 2, 9, "x"], "addresses_question": "3"},
                          {"approach": "B", "passage_ids": [2, 3], "addresses_question": 7},
                          {"approach": " ", "passage_ids": [4]}, {"approach": "C", "passage_ids": []}]}
        groups = LM.parse_groups(raw, records)
        self.assertEqual([g["approach"] for g in groups], ["A", "B"])
        self.assertEqual([r.record_id for r in groups[0]["records"]], [records[0].record_id, records[1].record_id])
        self.assertEqual([r.record_id for r in groups[1]["records"]], [records[2].record_id])  # 2 already used
        self.assertEqual(groups[0]["addresses"], 3)
        self.assertEqual(groups[1]["addresses"], 3)  # clipped to the scale
        self.assertEqual(LM.parse_groups("not json", records), [])

    def test_choice_rule_is_directness_then_papers_then_passages_then_first(self) -> None:
        recs = pool("text_chunks")
        g = lambda a, ids, addr: {"approach": a, "records": [recs[i] for i in ids],  # noqa: E731
                                  "papers": len({recs[i].paper_id for i in ids}), "addresses": addr}
        self.assertEqual(LM.choose_group([g("big", [0, 1, 2, 3], 2), g("direct", [8], 3)])["approach"], "direct")
        self.assertEqual(LM.choose_group([g("one paper", [0, 1, 2], 3), g("two papers", [0, 8], 3)])["approach"],
                         "two papers")
        self.assertEqual(LM.choose_group([g("first", [0], 3), g("second", [8], 3)])["approach"], "first")
        self.assertIsNone(LM.choose_group([]))


class AgentTests(unittest.TestCase):
    def test_registered(self) -> None:
        for method in LM.AGENT_CONFIGS:
            self.assertIn(method, H.METHODS)

    def test_choose_and_ground(self) -> None:
        responder = Responder()
        h = run("agent_choose_ground_b_o3mini", responder)
        self.assertEqual([c[0] for c in responder.calls], ["chooser", "writer"])
        self.assertEqual({c[1] for c in responder.calls}, {"o3mini"})
        self.assertEqual(h.source, "web")
        chosen = h.notes["choice"]["chosen"]
        self.assertEqual(chosen["addresses"], 3)  # the "aluminium addition" group is larger but less direct
        self.assertIn(chosen["approach"], ("silicide coating", "zirconia barrier"))
        writer = responder.calls[1][2]
        self.assertEqual(writer["analysis_notes"]["lever"], chosen["approach"])
        evidence = writer["eligible_evidence"]
        chooser_ids = [p["id"] for p in responder.calls[0][2]["passages"]]
        self.assertTrue(evidence)
        self.assertLessEqual(len(evidence), 24)
        self.assertLessEqual(h.notes["focused_pack"]["chars"], LM.AGENT_WRITE_BUDGET)
        self.assertGreaterEqual(h.notes["focused_pack"]["from_chosen_group"], 1)
        self.assertEqual(len(chooser_ids), h.notes["choice"]["pool_records"])

    def test_group_passages_come_first_and_the_rest_is_on_topic(self) -> None:
        groups = [{"approach": "silicide coating oxygen barrier", "passage_ids": [1], "addresses_question": 3}]
        responder = Responder(groups)
        h = run("agent_choose_ground_b_o3mini", responder)
        chooser_passages = responder.calls[0][2]["passages"]
        first_text = chooser_passages[0]["text"]
        evidence = responder.calls[1][2]["eligible_evidence"]
        self.assertEqual(evidence[0]["evidence"][:40], first_text[:40])
        self.assertTrue(all("silicide" in e["evidence"] for e in evidence[1:6]))  # BM25 on the chosen approach
        self.assertEqual(h.notes["focused_pack"]["from_chosen_group"], 1)

    def test_choose_only_writes_without_evidence(self) -> None:
        responder = Responder()
        h = run("agent_choose_only_b_o3mini", responder)
        writer = responder.calls[1][2]
        self.assertEqual(writer["eligible_evidence"], [])
        self.assertIn("lever", writer["analysis_notes"])
        self.assertNotIn("focused_pack", h.notes)

    def test_draft_ground_uses_the_models_own_choice(self) -> None:
        responder = Responder()
        h = run("agent_draft_ground_b_o3mini", responder)
        self.assertEqual([c[0] for c in responder.calls], ["draft", "writer"])
        self.assertEqual(responder.calls[0][2]["eligible_evidence"], [])
        writer = responder.calls[1][2]
        self.assertEqual(writer["analysis_notes"]["lever"], "silicide coating applied by slurry")
        self.assertTrue(all("silicide" in e["evidence"] for e in writer["eligible_evidence"][:6]))
        self.assertNotIn("choice", h.notes)

    def test_fallback_without_a_valid_group(self) -> None:
        responder = Responder(groups=[])
        h = run("agent_choose_ground_b_o3mini", responder)
        self.assertEqual(h.notes["fallback"], "no valid group")
        self.assertEqual(responder.calls[1][2]["eligible_evidence"], [])
        self.assertEqual(responder.calls[1][2]["analysis_notes"], {})


if __name__ == "__main__":
    unittest.main()
