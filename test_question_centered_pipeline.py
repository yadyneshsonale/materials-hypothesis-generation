from __future__ import annotations

import unittest
from unittest.mock import patch

from question_centered_pipeline import ADJUDICATION_BATCH_SIZE, adjudicate_questions


class QuestionCenteredPipelineTests(unittest.TestCase):
    @patch("question_centered_pipeline.chat_json")
    def test_adjudication_batches_large_coarse_groups(self, chat_mock) -> None:
        questions = [
            {
                "question_id": f"q-{index}",
                "question": f"Question {index}?",
                "question_type": "mechanism",
                "facets": {},
            }
            for index in range(ADJUDICATION_BATCH_SIZE + 5)
        ]

        def response(_system: str, user: str, **_kwargs: object) -> dict:
            import json
            rows = json.loads(user)["questions"]
            return {
                "groups": [{
                    "label": "one_group",
                    "question_ids": [row["question_id"] for row in rows],
                    "reason": "test",
                }]
            }

        chat_mock.side_effect = response
        groups = adjudicate_questions(questions, {"domain": "general_materials"})
        assigned = [
            question["question_id"]
            for _label, rows in groups
            for question in rows
        ]
        self.assertEqual(sorted(assigned), sorted(row["question_id"] for row in questions))
        self.assertEqual(chat_mock.call_count, 2)


if __name__ == "__main__":
    unittest.main()
