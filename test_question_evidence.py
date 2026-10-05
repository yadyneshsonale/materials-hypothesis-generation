from __future__ import annotations

import unittest

from question_evidence import ResolvedQuestion, stable_cluster_id


class QuestionEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.evidence = {
            "unit-1": {
                "paper_id": "paper-1",
                "publication_date": "2020-01-01",
                "evidence_spans": ["A protective oxide reduced mass gain."],
            }
        }

    def test_validates_grounded_answer_and_cluster(self) -> None:
        row = {
            "question_id": "q1",
            "paper_id": "paper-1",
            "publication_date": "2020-01-01",
            "question": "Why did mass gain decrease?",
            "question_type": "mechanism",
            "category": "mechanism_gap",
            "resolution_status": "answered_same_paper",
            "resolution_summary": "A protective oxide formed.",
            "facets": {
                "domain": "oxidation_corrosion",
                "subtopic": "protective scale",
                "material_family": "HEA",
                "target_property": "mass gain",
                "design_variable": "oxide chemistry",
                "condition_regime": "high temperature air",
                "mechanism_topic": "diffusion barrier",
                "question_function": "explain_mechanism",
            },
            "answers": [{
                "evidence_unit_id": "unit-1",
                "answer": "A protective scale reduced mass gain.",
                "epistemic_status": "observed",
                "evidence_spans": ["A protective oxide reduced mass gain."],
                "confidence": 0.9,
            }],
            "source_evidence_spans": ["mass gain decrease"],
        }
        question = ResolvedQuestion.from_dict(row, evidence_lookup=self.evidence)
        self.assertEqual(len(question.answers), 1)
        self.assertTrue(question.cluster_id().startswith("question_cluster::oxidation_corrosion"))

    def test_rejects_answer_with_unavailable_span(self) -> None:
        row = {
            "question_id": "q1",
            "paper_id": "paper-1",
            "publication_date": "2020-01-01",
            "question": "Why?",
            "question_type": "mechanism",
            "category": "mechanism_gap",
            "resolution_status": "answered_same_paper",
            "facets": {
                "domain": "oxidation_corrosion",
                "subtopic": "scale",
            },
            "answers": [{
                "evidence_unit_id": "unit-1",
                "answer": "Invented.",
                "epistemic_status": "inferred",
                "evidence_spans": ["Not present."],
            }],
        }
        with self.assertRaisesRegex(ValueError, "exact spans"):
            ResolvedQuestion.from_dict(row, evidence_lookup=self.evidence)

    def test_cluster_id_changes_with_condition_regime(self) -> None:
        base = {
            "domain": "oxidation_corrosion",
            "subtopic": "scale",
            "target_property": "mass gain",
            "design_variable": "Al",
            "condition_regime": "air",
            "question_function": "change_variable",
        }
        vacuum = {**base, "condition_regime": "vacuum"}
        self.assertNotEqual(stable_cluster_id(base), stable_cluster_id(vacuum))


if __name__ == "__main__":
    unittest.main()
