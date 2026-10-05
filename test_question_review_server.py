from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from question_review_server import cluster_summaries


class QuestionReviewServerTests(unittest.TestCase):
    def test_cluster_summaries_expose_review_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "question_cluster__one.json").write_text(json.dumps({
                "cluster_id": "one",
                "canonical_question": "Why?",
                "facets": {"domain": "phase_stability", "subtopic": "precipitation"},
                "question_count": 3,
                "paper_count": 2,
                "answers": [{"answer_id": "a1"}],
            }))
            rows = cluster_summaries(root)
        self.assertEqual(rows[0]["paper_count"], 2)
        self.assertEqual(rows[0]["answer_count"], 1)
        self.assertEqual(rows[0]["domain"], "phase_stability")


if __name__ == "__main__":
    unittest.main()
