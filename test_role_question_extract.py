from __future__ import annotations

import unittest

from role_question_extract import (
    _validate_questions,
    _validate_reconciled,
    _validate_reconciled_with_ref_map,
)
from roles import ROLE_KEYS


class RoleQuestionValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (
            "Cr addition reduced mass gain from 10.4 to 5.1 mg/cm2 at 800 C. "
            "The authors attributed this reduction to a dense chromium-rich oxide."
        )
        self.roles = {role: [] for role in ROLE_KEYS}
        self.roles["evidence_result"] = [{
            "content": "Cr reduced oxidation mass gain at 800 C.",
            "evidence_spans": [
                "Cr addition reduced mass gain from 10.4 to 5.1 mg/cm2 at 800 C."
            ],
            "conflicting": False,
        }]
        self.roles["mechanism_principle"] = [{
            "content": "A dense chromium-rich oxide limited oxidation.",
            "evidence_spans": [
                "The authors attributed this reduction to a dense chromium-rich oxide."
            ],
            "conflicting": False,
        }]

    def test_accepts_all_roles_and_grounded_decision_question(self) -> None:
        reconciled, rejected = _validate_reconciled(self.roles, self.source)
        rows = [{
            "question": (
                "At which temperature does the chromium-rich oxide stop reducing mass gain?"
            ),
            "question_type": "boundary",
            "rationale": "The result is reported only at 800 C.",
            "decision_use": "Sets the maximum service temperature for Cr addition.",
            "grounded_role_refs": ["evidence_result:0", "mechanism_principle:0"],
            "answer_requirements": [
                "Mass-gain curves and oxide phase measurements above 800 C."
            ],
            "evidence_spans": [
                "Cr addition reduced mass gain from 10.4 to 5.1 mg/cm2 at 800 C."
            ],
            "confidence": 0.9,
        }]

        questions, question_rejected = _validate_questions(
            rows,
            "paper-1",
            self.source,
            reconciled,
        )

        self.assertEqual(rejected, [])
        self.assertEqual(question_rejected, [])
        self.assertEqual(set(reconciled), set(ROLE_KEYS))
        self.assertEqual(questions[0]["question_type"], "boundary")
        self.assertTrue(questions[0]["question_id"].startswith("paper-1::decision_question::"))

    def test_rejects_non_verbatim_role_span(self) -> None:
        self.roles["evidence_result"][0]["evidence_spans"] = ["Paraphrased evidence."]

        reconciled, rejected = _validate_reconciled(self.roles, self.source)

        self.assertEqual(reconciled["evidence_result"], [])
        self.assertRegex(rejected[0]["reason"], "non-verbatim")

    def test_rejects_question_without_valid_role_reference(self) -> None:
        reconciled, _ = _validate_reconciled(self.roles, self.source)
        rows = [{
            "question": "Does Cr improve oxidation?",
            "question_type": "intervention",
            "rationale": "A decision is needed.",
            "decision_use": "Select Cr content.",
            "grounded_role_refs": ["causal_claim:9"],
            "answer_requirements": ["A controlled comparison."],
            "evidence_spans": [
                "Cr addition reduced mass gain from 10.4 to 5.1 mg/cm2 at 800 C."
            ],
            "confidence": 0.8,
        }]

        questions, rejected = _validate_questions(
            rows,
            "paper-1",
            self.source,
            reconciled,
        )

        self.assertEqual(questions, [])
        self.assertRegex(rejected[0]["reason"], "invalid grounded_role_ref")

    def test_rejects_overlong_compound_question(self) -> None:
        reconciled, _ = _validate_reconciled(self.roles, self.source)
        rows = [{
            "question": " ".join(["Which"] + ["measurement"] * 50) + "?",
            "question_type": "discrimination",
            "rationale": "The mechanism is uncertain.",
            "decision_use": "Select a mechanism.",
            "grounded_role_refs": ["mechanism_principle:0"],
            "answer_requirements": ["A controlled measurement."],
            "evidence_spans": [
                "The authors attributed this reduction to a dense chromium-rich oxide."
            ],
            "confidence": 0.8,
        }]

        questions, rejected = _validate_questions(
            rows,
            "paper-1",
            self.source,
            reconciled,
        )

        self.assertEqual(questions, [])
        self.assertRegex(rejected[0]["reason"], "at most 50 words")

    def test_remaps_question_reference_after_reconciled_rejection(self) -> None:
        roles = {role: [] for role in ROLE_KEYS}
        roles["evidence_result"] = [
            {
                "content": "Invalid first item.",
                "evidence_spans": ["Not in source."],
                "conflicting": False,
            },
            self.roles["evidence_result"][0],
        ]
        reconciled, _, reference_map = _validate_reconciled_with_ref_map(
            roles,
            self.source,
        )
        row = {
            "question": "At which temperature does the Cr benefit fail?",
            "question_type": "boundary",
            "rationale": "Only 800 C was measured.",
            "decision_use": "Set the service limit.",
            "grounded_role_refs": ["evidence_result:1"],
            "answer_requirements": ["Measure mass gain at higher temperatures."],
            "evidence_spans": [
                "Cr addition reduced mass gain from 10.4 to 5.1 mg/cm2 at 800 C."
            ],
            "confidence": 0.8,
        }

        questions, rejected = _validate_questions(
            [row],
            "paper-1",
            self.source,
            reconciled,
            reference_map,
        )

        self.assertEqual(rejected, [])
        self.assertEqual(questions[0]["grounded_role_refs"], ["evidence_result:0"])


if __name__ == "__main__":
    unittest.main()
