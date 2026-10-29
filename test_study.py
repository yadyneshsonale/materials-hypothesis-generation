"""Tests for the complete-study writer (experiment 41, loop.md 22.1)."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import hypo_loop as H
import loop_methods as LM
from temporal_hypothesis_benchmark import RetrievalRecord

CASE = {"paper_id": "PMCT", "publication_date": "2024-06-01", "split": "validation",
        "queries": {lvl: {"text": "Improve the oxidation resistance of cast HfNbTaTiZr at 1000 C."}
                    for lvl in ("broad", "problem_constrained", "expert_context")},
        "hidden_target": {"intervention": "Ink-extrusion three-dimensional printing followed by a slurry silicide coating"}}


def pool(kind: str) -> list[RetrievalRecord]:
    return [RetrievalRecord(f"P{i}::web::{j:03d}::results", f"P{i}", "2020-01-01", "web:Results",
                            "oxidation resistance alloy coating " * 60, {"source": "web"}) for i in range(6) for j in range(8)]


def run(method: str) -> tuple[H.Harness, list[tuple[str, str, dict]]]:
    calls: list[tuple[str, str, dict]] = []

    def ask(self, role, model, system, payload, max_out=None):
        calls.append((role, system, payload))
        return {"hypothesis": "A coating protects the alloy.", "intervention": "coating", "supporting_evidence_ids": [],
                "conflicting_evidence_ids": []}

    h = H.Harness(CASE, "broad", 1)
    with patch.object(h, "pool", side_effect=pool), patch.object(H.Harness, "ask", autospec=True, side_effect=ask):
        H.METHODS[method](h)
    return h, calls


class StudyWriterTests(unittest.TestCase):
    def test_registered_and_prompts_compose(self) -> None:
        for method in LM.STUDY_CONFIGS:
            self.assertIn(method, H.METHODS)
        self.assertTrue(LM.WRITER_STUDY.startswith(LM.WRITER_B.split(LM._RETURN)[0]))
        self.assertIn(LM.STUDY_TYPES_GUIDE, LM.WRITER_STUDY)
        self.assertIn(LM.STUDY_DESIGN_GUIDE, LM.WRITER_STUDY)
        self.assertIn(LM.STUDY_TYPES_GUIDE, LM.WRITER_TYPES)
        self.assertNotIn(LM.STUDY_DESIGN_GUIDE, LM.WRITER_TYPES)
        self.assertIn(LM.STUDY_DESIGN_GUIDE, LM.WRITER_DESIGN)
        self.assertNotIn(LM.STUDY_TYPES_GUIDE, LM.WRITER_DESIGN)
        for prompt in (LM.WRITER_STUDY, LM.WRITER_TYPES, LM.WRITER_DESIGN):
            self.assertEqual(prompt.count(LM._RETURN), 1)
            self.assertTrue(prompt.endswith(LM.WRITER_B.split(LM._RETURN)[1]))  # the schema is unchanged

    def test_closed_book_variants_use_their_prompt_and_no_evidence(self) -> None:
        for method, prompt in (("writer_study_b_o3mini", LM.WRITER_STUDY), ("writer_types_b_o3mini", LM.WRITER_TYPES),
                               ("writer_design_b_o3mini", LM.WRITER_DESIGN)):
            _, calls = run(method)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][1], prompt)
            self.assertEqual(calls[0][2]["eligible_evidence"], [])

    def test_web_study_uses_the_64k_pack_and_the_study_writer(self) -> None:
        h, calls = run("web_study_64k_b_o3mini")
        self.assertEqual(h.source, "web")
        self.assertEqual(calls[0][1], LM.WRITER_STUDY)
        self.assertLessEqual(h.notes["evidence"]["chars"], 64000)
        self.assertGreater(h.notes["evidence"]["records"], 24)  # more than the standard 16,000-character pack
        self.assertEqual(len(calls[0][2]["eligible_evidence"]), h.notes["evidence"]["records"])


if __name__ == "__main__":
    unittest.main()
