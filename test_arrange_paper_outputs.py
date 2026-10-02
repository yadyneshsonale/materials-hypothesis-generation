from __future__ import annotations

import unittest

from arrange_paper_outputs import _https_s3_url


class ArrangePaperOutputsTests(unittest.TestCase):
    def test_converts_checksum_qualified_s3_url_to_https(self) -> None:
        url = _https_s3_url(
            "s3://pmc-oa-opendata/PMC1.1/PMC1.1.pdf?md5=abc123"
        )

        self.assertEqual(
            url,
            "https://pmc-oa-opendata.s3.amazonaws.com/"
            "PMC1.1/PMC1.1.pdf?md5=abc123",
        )

    def test_rejects_non_s3_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported PDF URL"):
            _https_s3_url("https://example.com/article.pdf")


if __name__ == "__main__":
    unittest.main()
