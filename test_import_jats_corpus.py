from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET

from import_jats_corpus import jats_to_text, validate_primary_research


PRIMARY_XML = """<article><front><article-meta><title-group><article-title>High-temperature alloy test</article-title></title-group></article-meta></front><body><sec><title>Methods</title><p>We cast the alloy.</p></sec><sec><title>Results</title><p>Strength increased <xref ref-type="bibr" rid="R2">(2)</xref>.</p><table-wrap><label>Table 1</label><caption><p>Creep results [2]</p></caption><table><tr><th>Alloy</th><th>MPa</th></tr><tr><td>A</td><td>900</td></tr></table></table-wrap></sec></body><back><ref-list><ref id="R2"><label>2.</label><element-citation><article-title>Cited alloy study</article-title><pub-id pub-id-type="doi">10.1/test</pub-id></element-citation></ref></ref-list></back></article>"""


class JatsImporterTests(unittest.TestCase):
    def test_preserves_sections_tables_and_numbered_references(self) -> None:
        text = jats_to_text(ET.fromstring(PRIMARY_XML))

        self.assertIn("Methods\n", text)
        self.assertIn("Strength increased [2]", text)
        self.assertIn("Table 1. Creep results [2]", text)
        self.assertIn("Alloy\tMPa", text)
        self.assertIn("[2] Cited alloy study 10.1/test", text)

    def test_rejects_review_publication_type(self) -> None:
        metadata = {"pmcid": "PMC1", "pubTypeList": {"pubType": ["review-article"]}}

        with self.assertRaisesRegex(ValueError, "review publication type"):
            validate_primary_research(ET.fromstring(PRIMARY_XML), metadata)


if __name__ == "__main__":
    unittest.main()