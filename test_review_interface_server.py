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

    def test_aligns_citation_variant_across_pdf_pages(self) -> None:
        root = Path(__file__).parent / "experiments" / "high_temperature_hea_qwen35b"
        pdf = root / "outputs" / "papers" / "PMC10384371" / "input" / "article.pdf"
        span = (
            "To summarize, the mechanisms of high-temperature oxidation in CrMnFeCoNi system "
            "reported in references [ [13] , [27] , [28] , [29] ] were mainly based upon "
            "surface analysis of the reaction products retained after tests, which is "
            "insufficient because great emphasis has been placed on post-mortem analyses of "
            "reaction products analysed at ambient temperature, or else assumptions made via "
            "the analysis of the temperature dependence of phases at different temperatures. "
            "Clearly, this introduces a degree of uncertainty, since one cannot be completely "
            "sure of the underlying physical mechanisms which are imperative on the critical "
            "scales: that of the activity of elements, transformation temperatures, and vapour "
            "pressure at the same time."
        )

        matches = _find_pdf_matches(pdf, [span])

        self.assertEqual([match["page"] for match in matches], [2, 3])
        self.assertTrue(all(match["highlights"] for match in matches))


if __name__ == "__main__":
    unittest.main()
