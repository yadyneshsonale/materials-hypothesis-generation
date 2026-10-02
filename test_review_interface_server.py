from __future__ import annotations

import unittest
from pathlib import Path

from review_interface_server import (
    _compact_normalized,
    _evidence_context,
    _find_pdf_page,
    _find_pdf_matches,
)


class ReviewInterfaceTests(unittest.TestCase):
    def test_evidence_context_marks_exact_span(self) -> None:
        source = "Before text. Mass gain fell to 1.2 mg. After text."
        span = "Mass gain fell to 1.2 mg."

        context = _evidence_context(source, span, padding=20)

        self.assertTrue(context["grounded"])
        self.assertEqual(context["highlight"], span)
        self.assertIn("Before", context["before"])
        self.assertIn("After", context["after"])

    def test_normalization_handles_formula_spacing(self) -> None:
        self.assertEqual(_compact_normalized("Cr 2 O 3"), _compact_normalized("Cr₂O₃"))

    def test_finds_evidence_page_in_real_pdf(self) -> None:
        root = Path(__file__).parent / "experiments" / "high_temperature_hea_qwen35b"
        pdf = root / "outputs" / "papers" / "PMC10384371" / "input" / "article.pdf"

        page = _find_pdf_page(pdf, ["Mn is the major oxide-forming element"])

        self.assertIsNotNone(page)

    def test_finds_highlight_rectangles_in_real_pdf(self) -> None:
        root = Path(__file__).parent / "experiments" / "high_temperature_hea_qwen35b"
        pdf = root / "outputs" / "papers" / "PMC10384371" / "input" / "article.pdf"

        matches = _find_pdf_matches(
            pdf,
            ["oxygen abundance promotes the formation of Mn2O3 instead of MnO"],
        )

        self.assertTrue(matches)
        self.assertGreater(len(matches[0]["highlights"]), 0)
        self.assertGreater(matches[0]["page_width"], 0)
        self.assertGreater(matches[0]["page_height"], 0)


if __name__ == "__main__":
    unittest.main()
