from __future__ import annotations

import unittest
from unittest.mock import patch

import failure_rubric as fr
import rubric_eval as rx


class FailureRubricTests(unittest.TestCase):
    def test_fidelity_sample_is_deterministic_and_balanced(self) -> None:
        first = fr.fidelity_sample()
        second = fr.fidelity_sample()
        self.assertEqual([r[2]["record_id"] for r in first], [r[2]["record_id"] for r in second])
        counts = {rubric: sum(1 for r in first if r[0] == rubric) for rubric in rx.RUBRICS}
        self.assertTrue(all(n == fr.FIDELITY_SAMPLE for n in counts.values()), counts)

    def test_source_window_picks_the_record_part(self) -> None:
        text = "\n".join(f"para {i} " + "x" * 900 for i in range(120))
        with patch.object(fr.rx, "strip_back_matter", return_value=text), \
                patch.object(fr.rx, "windows", side_effect=lambda t: ["w1", "w2", "w3"]), \
                patch("pathlib.Path.read_text", return_value=text):
            self.assertEqual(fr.source_window("P", "2/3"), "w2")
            self.assertEqual(fr.source_window("P", "1/1a"), "w1")
            self.assertEqual(fr.source_window("P", "9/3"), "w3")
            self.assertEqual(fr.source_window("P", "bogus"), "w1")

    def test_mean_ignores_missing(self) -> None:
        self.assertEqual(fr.mean([1.0, None, 2.0]), 1.5)
        self.assertIsNone(fr.mean([None]))


if __name__ == "__main__":
    unittest.main()
