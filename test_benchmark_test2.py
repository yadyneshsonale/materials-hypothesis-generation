from __future__ import annotations

import unittest

import benchmark_test2 as B


class Test2BuilderTests(unittest.TestCase):
    def test_earliest_date_takes_the_minimum_valid_date(self) -> None:
        row = {"electronicPublicationDate": "2026-03-10", "firstPublicationDate": "2026-03-12",
               "journalInfo": {"printPublicationDate": "2026-03-01"}}
        self.assertEqual(B.earliest_date(row), ("2026-03-01", "print_publication_date"))
        self.assertEqual(B.earliest_date({"firstPublicationDate": "2026"}), ("", "none"))

    def test_month_back_wraps_years_and_clamps_days(self) -> None:
        self.assertEqual(B._month_back("2026-02-17"), "2026-01-17")
        self.assertEqual(B._month_back("2026-01-31"), "2025-12-28")

    def test_near_duplicate_titles(self) -> None:
        self.assertGreaterEqual(B.jaccard("Creep of a refractory high-entropy alloy",
                                          "Creep of a refractory high entropy alloy"), B.NEAR_DUPLICATE)
        self.assertLess(B.jaccard("Creep of a refractory high-entropy alloy", "Oxidation of CoCrFeNi coatings"),
                        B.NEAR_DUPLICATE)

    def test_gap_template_substitution_matches_the_v3_writer(self) -> None:
        for gap in ("understanding", "method"):
            self.assertIn(B.v31.GAP_TEMPLATES[gap], B.gap_system(gap))


if __name__ == "__main__":
    unittest.main()
