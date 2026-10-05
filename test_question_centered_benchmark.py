from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path

from question_centered_benchmark import audit, build_records


class QuestionCenteredBenchmarkTests(unittest.TestCase):
    def test_grouped_answers_filters_future_and_test_paper(self) -> None:
        cluster = {
            "cluster_id": "c1",
            "canonical_question": "Why does oxidation slow?",
            "facets": {"domain": "oxidation_corrosion"},
            "question_variants": [
                {
                    "question_id": "q-old",
                    "paper_id": "old",
                    "publication_date": "2020-01-01",
                    "question": "Why?",
                },
                {
                    "question_id": "q-test",
                    "paper_id": "test",
                    "publication_date": "2024-01-01",
                    "question": "Why now?",
                },
            ],
            "answers": [
                {
                    "answer_id": "a-old",
                    "paper_id": "old",
                    "publication_date": "2020-01-01",
                    "answer": "Protective scale.",
                },
                {
                    "answer_id": "a-future",
                    "paper_id": "future",
                    "publication_date": "2025-01-01",
                    "answer": "Future result.",
                },
            ],
        }
        records = build_records(
            "grouped_answers",
            test_paper="test",
            cutoff="2024-01-01",
            triage={"questions": []},
            clusters=[cluster],
            v2_dir=Path("/unused"),
            metadata={
                "old": {
                    "earliest_public_date": "2020-01-01",
                    "work_family_id": "old",
                },
                "test": {
                    "earliest_public_date": "2024-01-01",
                    "work_family_id": "test",
                },
                "future": {
                    "earliest_public_date": "2025-01-01",
                    "work_family_id": "future",
                },
            },
            synthesis_cache=Path("/tmp/unused"),
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(
            [row["answer_id"] for row in records[0].structured["answers"]],
            ["a-old"],
        )
        self.assertEqual(
            [row["question_id"] for row in records[0].structured["question_variants"]],
            ["q-old"],
        )

    def test_audit_supports_targeted_query_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = root / "cases"
            runs = root / "runs"
            cases.mkdir()
            runs.mkdir()
            (cases / "test.json").write_text(json.dumps({"paper_id": "test"}))
            (root / "metadata.json").write_text(json.dumps({"papers": []}))
            for variant in (
                "raw_questions",
                "grouped_questions",
                "grouped_answers",
                "grouped_synthesis",
                "grouped_answers_v2",
            ):
                (runs / f"test__broad__{variant}.json").write_text(json.dumps({
                    "paper_id": "test",
                    "query_level": "broad",
                    "variant": variant,
                    "knowledge_cutoff": "2024-01-01",
                    "retrieved_records": [],
                    "generation": {
                        "supporting_evidence_ids": [],
                        "conflicting_evidence_ids": [],
                    },
                }))
            result = audit(
                root / "metadata.json",
                cases,
                runs,
                root / "audit.json",
                query_levels=("broad",),
            )
        self.assertTrue(result["matrix_complete"])


if __name__ == "__main__":
    unittest.main()
