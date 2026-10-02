from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from evaluate_role_questions import evaluate
from role_question_extract import SCHEMA_VERSION
from roles import ROLE_KEYS


class EvaluateRoleQuestionsTests(unittest.TestCase):
    def test_evaluates_and_exports_grounded_roles_and_questions(self) -> None:
        span = "Cr reduced mass gain at 800 C."
        roles = {role: [] for role in ROLE_KEYS}
        roles["evidence_result"] = [{
            "content": "Cr reduced mass gain.",
            "evidence_spans": [span],
            "conflicting": False,
        }]
        question = {
            "question": "At which temperature does the Cr benefit fail?",
            "question_type": "boundary",
            "rationale": "Only 800 C was measured.",
            "decision_use": "Set the service limit.",
            "grounded_role_refs": ["evidence_result:0"],
            "answer_requirements": ["Measure mass gain at higher temperatures."],
            "evidence_spans": [span],
            "confidence": 0.8,
        }
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_dir = root / "source"
            evidence_dir = root / "evidence"
            source_dir.mkdir()
            evidence_dir.mkdir()
            (source_dir / "paper-1.txt").write_text(span)
            (evidence_dir / "paper-1.json").write_text(json.dumps({
                "schema_version": SCHEMA_VERSION,
                "paper_id": "paper-1",
                "reconciled_by_role": roles,
                "questions": [question],
                "rejected_items": [],
            }))
            roles_jsonl = root / "roles.jsonl"
            questions_jsonl = root / "questions.jsonl"

            result = evaluate(
                evidence_dir,
                source_dir,
                roles_jsonl,
                questions_jsonl,
            )

            exported_role = json.loads(roles_jsonl.read_text().strip())
            exported_question = json.loads(questions_jsonl.read_text().strip())

        self.assertEqual(result["total_role_items"], 1)
        self.assertEqual(result["total_questions"], 1)
        self.assertEqual(result["invalid_item_count"], 0)
        self.assertEqual(exported_role["role_id"], "paper-1::evidence_result::0")
        self.assertEqual(exported_question["paper_id"], "paper-1")
        self.assertTrue(exported_question["question_id"].startswith("paper-1::decision_question::"))


if __name__ == "__main__":
    unittest.main()
