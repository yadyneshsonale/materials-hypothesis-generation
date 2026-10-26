from __future__ import annotations

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import expert_eval_analysis as A
import expert_eval_builder as B


class SelectionTests(unittest.TestCase):
    def test_selection_is_deterministic_balanced_and_matches_the_committed_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.object(B, "INTERNAL", Path(tmp)):
            key = B.select()
        committed = json.loads((B.H.EXPERIMENT_DIR / "expert_eval" / "key.json").read_text())
        self.assertEqual(key, committed)
        qs = key["questions"]
        self.assertEqual(Counter(q["set"] for q in qs), {"original12": 10, "test2": 5, "test3": 5})
        self.assertEqual(len({q["paper_id"] for q in qs}), 20)
        positions = Counter((lab, q["labels"][lab]["source"]) for q in qs for lab in "ABC")
        self.assertTrue(all(5 <= n <= 8 for n in positions.values()))
        orders = Counter(tuple(q["labels"][lab]["source"] for lab in "ABC") for q in qs)
        self.assertEqual(len(orders), 6)
        self.assertTrue(all(3 <= n <= 4 for n in orders.values()))


class PackageTests(unittest.TestCase):
    def test_package_is_blind(self) -> None:
        self.assertEqual(B.check_package()["problems"], [])

    def test_rendering_shows_every_field_and_nests_the_falsification_test(self) -> None:
        lines = B.render_hypothesis("A", {"hypothesis": "Add 5 at.% Cr * x", "falsification_experiment": {
            "design": "Compare", "measurements": ["hardness", {"m": "XRD"}], "falsification_rule": "if < 10%"}})
        text = "\n".join(lines)
        self.assertIn("- **Main hypothesis:** Add 5 at.% Cr \\* x", text)
        self.assertIn("- **Starting material:** —", text)
        self.assertIn("  - *Measurements:* hardness; XRD", text)
        self.assertIn("  - *Falsified if:* if &lt; 10%", text)
        self.assertIsNone(B.SOURCE_WORDS.search(text))


def _synthetic(key: dict, scores: dict, upto: int = 20) -> dict:
    """An expert who agrees exactly with the GPT-5.6 judge and always finds the reference, for questions Q01..upto."""
    ratings = {"rater": "TEST", "Part 1 – hypotheses": {}, "Part 1 – questions": {}, "Part 2 – hypotheses": {},
               "Part 2 – questions": {}}
    for q in key["questions"][:upto]:
        ref = next(lab for lab in "ABC" if q["labels"][lab]["source"] == "reference")
        ratings["Part 1 – questions"][q["qid"]] = {"question_sense": 4, "closest": ref, "comment": None}
        ratings["Part 2 – questions"][q["qid"]] = {"key_accuracy": 4, "hint": "No", "comment": None}
        for lab in "ABC":
            item = f"{q['qid']}-{lab}"
            s = scores[item]["gpt56"]["scores"]
            ratings["Part 1 – hypotheses"][item] = {"plausibility": 3, "testability": 3, "usefulness": 3,
                                                    "comment": None}
            ratings["Part 2 – hypotheses"][item] = {"intervention": s["intervention_reconstruction"],
                                                    "conditions": s["condition_agreement"],
                                                    "mechanism": s["mechanism_agreement"],
                                                    "outcome": s["outcome_agreement"], "comment": None}
    return ratings


class AnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.key = json.loads((A.INTERNAL / "key.json").read_text())
        self.scores = json.loads((A.INTERNAL / "judge_scores.json").read_text())

    def test_an_expert_matching_the_judge_gives_rho_one_and_full_identification(self) -> None:
        with patch.object(A, "BOOTSTRAP", 200):
            result = A.analyse(_synthetic(self.key, self.scores), self.key, self.scores)
        self.assertEqual(result["primary"]["n_items"], 40)
        self.assertEqual(result["primary"]["rho"], 1.0)
        self.assertEqual(result["primary"]["interpretation"], "tracks the expert")
        self.assertEqual(result["reference_identification"]["rate"], 1.0)
        self.assertEqual(result["question_hints"], {"No": 20, "Slightly": 0, "Strongly": 0})

    def test_partial_completion_uses_only_completed_questions(self) -> None:
        with patch.object(A, "BOOTSTRAP", 200):
            result = A.analyse(_synthetic(self.key, self.scores, upto=10), self.key, self.scores)
        self.assertEqual(result["completed"], {"part1_items": 30, "part2_items": 30})
        self.assertEqual(result["primary"]["n_items"], 20)
        self.assertEqual(result["primary"]["n_questions"], 10)

    def test_workbook_round_trip(self) -> None:
        from openpyxl import load_workbook
        qids = [q["qid"] for q in self.key["questions"]]
        with tempfile.TemporaryDirectory() as tmp, patch.object(B, "SHEET", Path(tmp)):
            B.write_sheets(qids)
            path = Path(tmp) / "expert_ratings.xlsx"
            wb = load_workbook(path)
            wb["START HERE"]["B3"] = "XY"
            wb["Part 2 – hypotheses"]["C2"] = 3
            wb["Part 2 – hypotheses"]["D2"] = "2"
            wb["Part 1 – questions"]["C2"] = "Can't tell"
            wb.save(path)
            ratings = A.read_ratings(path)
        self.assertEqual(ratings["rater"], "XY")
        self.assertEqual(ratings["Part 2 – hypotheses"][f"{qids[0]}-A"]["intervention"], 3)
        self.assertEqual(ratings["Part 2 – hypotheses"][f"{qids[0]}-A"]["conditions"], 2)
        self.assertEqual(ratings["Part 1 – questions"][qids[0]]["closest"], "Can't tell")
        self.assertEqual(len(ratings["Part 1 – hypotheses"]), 60)

    def test_statistics_helpers(self) -> None:
        self.assertAlmostEqual(A.spearman([1, 2, 3, 4], [2, 4, 6, 8]), 1.0)
        self.assertAlmostEqual(A.binomial_greater(0, 5, 1 / 3), 1.0)
        diff = A.paired_by_question({"Q1": 3, "Q2": 4, "Q3": 2}, {"Q1": 1, "Q2": 1, "Q3": 1})
        self.assertEqual((diff["up"], diff["down"]), (3, 0))


if __name__ == "__main__":
    unittest.main()
