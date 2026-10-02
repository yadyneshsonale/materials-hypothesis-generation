from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evaluate_reader_questions import evaluate


class EvaluateReaderQuestionsTests(unittest.TestCase):
    def test_reports_grounded_question_dimensions(self) -> None:
        source = "The alloy was oxidized at 900 C in air."
        question = {
            "question_id": "paper-1::reader_question::abc",
            "question": "Why was the alloy oxidized at 900 C?",
            "question_type": "rationale",
            "reading_step": "inspect_choice",
            "reader_intent": "understand",
            "relevance": "direct",
            "rationale": "The temperature defines the tested regime.",
            "source_section": "Methods",
            "evidence_spans": [source],
            "confidence": 0.9,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_dir = root / "text"
            question_dir = root / "questions"
            source_dir.mkdir()
            question_dir.mkdir()
            (source_dir / "paper-1.txt").write_text(source)
            (question_dir / "paper-1.json").write_text(json.dumps({
                "paper_id": "paper-1",
                "questions": [question],
            }))

            export_path = root / "questions.jsonl"
            result = evaluate(question_dir, source_dir, export_path)
            exported = [
                json.loads(line) for line in export_path.read_text().splitlines()
            ]

        self.assertEqual(result["total_questions"], 1)
        self.assertEqual(result["exact_grounding_rate"], 1)
        self.assertEqual(result["reading_step_counts"], {"inspect_choice": 1})
        self.assertEqual(result["invalid_item_count"], 0)
        self.assertEqual(exported[0]["paper_id"], "paper-1")


if __name__ == "__main__":
    unittest.main()
