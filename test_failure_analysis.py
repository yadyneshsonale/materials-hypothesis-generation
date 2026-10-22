from __future__ import annotations

import json
import unittest
from pathlib import Path

from failure_analysis import (
    CASES_DIR,
    ERROR_CATEGORIES,
    TARGET_TYPES,
    hedge_count,
    spearman,
    target_text,
    validate_labels,
)


class FailureAnalysisHelperTests(unittest.TestCase):
    def test_spearman_perfect_inverse_and_ties(self) -> None:
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)
        self.assertAlmostEqual(spearman([1, 1, 2, 2], [1, 1, 2, 2]), 1.0)
        self.assertNotEqual(spearman([1, 2], [1, 2]), spearman([1, 2], [1, 2]))  # nan for n < 3

    def test_validate_labels_keeps_order_and_rejects_unknown_categories(self) -> None:
        raw = {"labels": [{"index": 1, "category": "wrong_baseline"}, {"index": 0, "category": "made_up"},
                          {"index": 7, "category": "wrong_mechanism"}, "junk"]}
        self.assertEqual(validate_labels(raw, 3), ["other", "wrong_baseline", "other"])
        self.assertEqual(validate_labels(None, 2), ["other", "other"])
        self.assertIn("other", ERROR_CATEGORIES)

    def test_hedge_count_reads_hypothesis_and_outcome_only(self) -> None:
        generation = {"hypothesis": "Cr may raise strength and could form Laves.",
                      "predicted_outcome": "Yield likely rises.", "mechanism": "might not count"}
        self.assertEqual(hedge_count(generation), 3)
        self.assertEqual(hedge_count({}), 0)

    def test_every_case_has_a_target_type(self) -> None:
        papers = {p.stem for p in Path(CASES_DIR).glob("PMC*.json")}
        self.assertEqual(papers, set(TARGET_TYPES))
        self.assertEqual(set(TARGET_TYPES.values()), {"composition", "processing", "computational", "characterization"})

    def test_target_text_uses_design_fields_not_outcome(self) -> None:
        hidden = {"material_initial_state": "A", "intervention": "B", "structural_mediator": "C", "mechanism": "D",
                  "predicted_outcome": "SHOULD_NOT_APPEAR"}
        self.assertEqual(target_text(hidden), "A B C D")


if __name__ == "__main__":
    unittest.main()
