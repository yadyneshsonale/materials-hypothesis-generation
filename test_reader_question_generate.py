from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reader_question_generate import (
    SCHEMA_VERSION,
    _generate_chunk,
    _target_range,
    _validate_chunk_questions,
    generate_paper,
)
from roles import ROLE_KEYS


class ReaderQuestionGenerateTests(unittest.TestCase):
    def test_target_range_scales_for_dense_passages(self) -> None:
        short = _target_range(90)
        dense = _target_range(450)

        self.assertGreaterEqual(short[0], 3)
        self.assertGreater(dense[0], short[0])
        self.assertGreaterEqual(dense[1], dense[0])

    def test_accepts_grounded_question_with_reading_metadata(self) -> None:
        passage = "The alloy was oxidized at 900 C in air for 100 hours."
        payload = {"questions": [{
            "question": "Why did the authors choose 900 C rather than another temperature?",
            "question_type": "rationale",
            "reading_step": "inspect_choice",
            "reader_intent": "understand",
            "relevance": "direct",
            "rationale": "The selected temperature controls the oxidation regime.",
            "evidence_span": passage,
            "confidence": 0.9,
        }]}

        questions, rejected = _validate_chunk_questions(
            payload, "paper-1", "Methods", 2, passage
        )

        self.assertEqual(rejected, [])
        self.assertEqual(questions[0]["reading_step"], "inspect_choice")
        self.assertEqual(questions[0]["relevance"], "direct")
        self.assertEqual(questions[0]["evidence_spans"], [passage])

    def test_rejects_question_not_grounded_in_current_passage(self) -> None:
        payload = {"questions": [{
            "question": "Would chromium improve oxidation resistance?",
            "question_type": "counterfactual",
            "reading_step": "change_variable",
            "reader_intent": "apply",
            "relevance": "adjacent",
            "rationale": "Composition may change oxide formation.",
            "evidence_span": "Chromium formed a protective oxide.",
            "confidence": 0.8,
        }]}

        questions, rejected = _validate_chunk_questions(
            payload,
            "paper-1",
            "Results",
            0,
            "Manganese-rich oxide formed in air.",
        )

        self.assertEqual(questions, [])
        self.assertRegex(rejected[0]["reason"], "non-verbatim")

    @patch("reader_question_generate.chat_json", return_value={"questions": []})
    def test_generation_prompt_formats_and_calls_model(self, chat_json_mock) -> None:
        from chunking import Chunk

        questions, rejected, calls = _generate_chunk(
            "paper-1",
            "Test title",
            Chunk("Results", "The alloy retained strength at 1000 C.", 0),
            1,
            "",
            [],
        )

        self.assertEqual(questions, [])
        self.assertEqual(rejected, [])
        self.assertEqual(calls, 1)
        self.assertIn("CURRENT PASSAGE", chat_json_mock.call_args.args[1])

    def test_resume_uses_completed_chunk_without_model_call(self) -> None:
        source = (
            "Introduction\n"
            "The alloy was oxidized at 900 C in air for 100 hours.\n"
            "Methods\n"
            "X-ray diffraction was used to identify oxide phases."
        )
        roles = {role: [] for role in ROLE_KEYS}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_dir = root / "text"
            papers_dir = root / "papers"
            checkpoint_dir = root / "checkpoints"
            source_dir.mkdir()
            paper_output = papers_dir / "paper-1" / "output"
            paper_output.mkdir(parents=True)
            (source_dir / "paper-1.txt").write_text(source)
            (papers_dir / "paper-1" / "metadata.json").write_text(
                '{"title": "Test paper"}'
            )
            (paper_output / "roles.json").write_text(
                __import__("json").dumps({"reconciled_by_role": roles})
            )
            from role_question_extract import _reading_chunks
            chunks = _reading_chunks(source)
            completed = {
                str(index): {
                    "chunk_sha256": __import__("hashlib").sha256(
                        chunk.text.encode()
                    ).hexdigest(),
                    "section": chunk.section,
                    "questions": [],
                    "rejected_items": [],
                }
                for index, chunk in enumerate(chunks)
            }
            checkpoint_dir.mkdir()
            (checkpoint_dir / "paper-1.json").write_text(__import__("json").dumps({
                "schema_version": SCHEMA_VERSION,
                "paper_id": "paper-1",
                "source_sha256": __import__("hashlib").sha256(source.encode()).hexdigest(),
                "completed_chunks": completed,
            }))

            result = generate_paper(
                source_dir / "paper-1.txt", papers_dir, checkpoint_dir
            )

        self.assertEqual(result.model_calls, 0)
        self.assertEqual(result.resumed_chunks, len(chunks))


if __name__ == "__main__":
    unittest.main()
