from __future__ import annotations

import unittest

from chunking import Chunk
from section_aware_extraction import (
    _validate_trigger,
    build_paper_map,
    retrieve_chunks,
)


class SectionAwareExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.unit = {
            "unit_id": "paper::unit::1",
            "source_section": "Results",
            "claim_ownership": "current_paper",
            "sample": {
                "sample_id": "sample_aged",
                "material_name": "Alloy A",
                "nominal_composition": "AlCoCrFeNi",
            },
            "process_steps": [{"action": "aging"}],
            "structure_observations": [{"feature": "precipitates"}],
            "test_conditions": {"temperature": "800 C"},
            "measurements": [{"property": "yield strength"}],
            "comparison": {"baseline_description": "as-cast"},
            "mechanisms": [],
            "boundaries": [],
            "limitations": [],
            "evidence_spans": [
                "Figure 2 shows higher yield strength for the aged Alloy A."
            ],
        }
        text = """Methods
The sample_aged Alloy A was aged at 800 C for 10 h before tensile testing.

Results
Figure 2 shows higher yield strength for the aged Alloy A.

Discussion
The precipitates may explain the higher strength of Alloy A."""
        self.paper_map = build_paper_map("paper", text)

    def test_retrieval_finds_other_sections(self) -> None:
        anchors, retrieved = retrieve_chunks(self.unit, self.paper_map["chunks"])
        self.assertEqual(len(anchors), 1)
        self.assertTrue(any(row["section"] == "Methods" for row in retrieved))
        self.assertTrue(any(row["section"] == "Discussion" for row in retrieved))

    def test_validation_rejects_non_verbatim_link(self) -> None:
        anchors, retrieved = retrieve_chunks(self.unit, self.paper_map["chunks"])
        supplied = [
            row for row in self.paper_map["chunks"]
            if row["chunk_id"] in set(anchors)
        ] + retrieved
        generated = {
            "evidence_unit_id": self.unit["unit_id"],
            "validated_links": [{
                "chunk_id": retrieved[0]["chunk_id"],
                "relation": "method",
                "evidence_spans": ["not in the paper"],
                "reason": "method",
            }],
            "questions": [],
            "research_thread": {},
        }
        row, rejected = _validate_trigger(
            "paper", self.unit, anchors, supplied, generated
        )
        self.assertEqual(row["validated_links"], [])
        self.assertEqual(len(rejected), 1)

    def test_validation_keeps_grounded_question(self) -> None:
        anchors, retrieved = retrieve_chunks(self.unit, self.paper_map["chunks"])
        supplied = [
            row for row in self.paper_map["chunks"]
            if row["chunk_id"] in set(anchors)
        ] + retrieved
        method = next(row for row in retrieved if row["section"] == "Methods")
        generated = {
            "evidence_unit_id": self.unit["unit_id"],
            "validated_links": [{
                "chunk_id": method["chunk_id"],
                "relation": "method",
                "evidence_spans": [
                    "The sample_aged Alloy A was aged at 800 C for 10 h before tensile testing."
                ],
                "reason": "same sample",
            }],
            "questions": [{
                "question": "Is the strength increase caused by the 800 C aging treatment?",
                "question_function": "explain_mechanism",
                "why_it_matters": "Separates processing from structure.",
                "known_context": "Aging and strength are reported.",
                "unresolved_information": "Causal mechanism.",
                "source_chunk_ids": anchors + [method["chunk_id"]],
                "evidence_spans": self.unit["evidence_spans"],
                "confidence": 0.9,
            }],
            "research_thread": {},
        }
        row, rejected = _validate_trigger(
            "paper", self.unit, anchors, supplied, generated
        )
        self.assertFalse(rejected)
        self.assertEqual(len(row["validated_links"]), 1)
        self.assertEqual(len(row["questions"]), 1)
        self.assertEqual(
            row["questions"][0]["question_function"],
            "explain_mechanism",
        )
        self.assertEqual(
            row["research_thread"]["provenance"]["trigger_evidence_unit_id"],
            self.unit["unit_id"],
        )
        self.assertIn(
            method["chunk_id"],
            row["research_thread"]["provenance"]["supporting_chunk_ids"],
        )


if __name__ == "__main__":
    unittest.main()
