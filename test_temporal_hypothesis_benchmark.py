from __future__ import annotations

import unittest

from temporal_hypothesis_benchmark import (
    RetrievalRecord,
    _eligible,
    chronological_split,
    retrieve,
)


class TemporalHypothesisBenchmarkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.metadata = {
            "old": {
                "earliest_public_date": "2020-01-01",
                "work_family_id": "doi:old",
            },
            "validation": {
                "earliest_public_date": "2024-03-01",
                "work_family_id": "doi:validation",
            },
            "test": {
                "earliest_public_date": "2025-04-01",
                "work_family_id": "doi:test",
            },
            "companion": {
                "earliest_public_date": "2023-01-01",
                "work_family_id": "doi:test",
            },
        }

    def test_chronological_split_is_paper_level(self) -> None:
        split = chronological_split(
            self.metadata,
            train_through=2023,
            validation_year=2024,
        )
        self.assertEqual(split["old"], "train")
        self.assertEqual(split["validation"], "validation")
        self.assertEqual(split["test"], "test")

    def test_temporal_filter_excludes_future_and_work_family(self) -> None:
        self.assertTrue(_eligible("old", "test", "2025-04-01", self.metadata))
        self.assertFalse(_eligible("validation", "validation", "2024-03-01", self.metadata))
        self.assertFalse(_eligible("companion", "test", "2025-04-01", self.metadata))

    def test_retrieval_ranks_query_overlap(self) -> None:
        records = [
            RetrievalRecord("1", "old", "2020-01-01", "evidence", "oxidation mass gain", {}),
            RetrievalRecord("2", "old", "2020-01-01", "evidence", "creep rupture strength", {}),
        ]
        selected = retrieve("improve oxidation resistance and reduce mass gain", records)
        self.assertEqual(selected[0].record_id, "1")


if __name__ == "__main__":
    unittest.main()
